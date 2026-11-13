"""Foot-planted procedural locomotion for the shared humanoid skeleton (pure math, no bpy).

Pose conventions are the ones of lib_char (rotations about WORLD axes in the rest pose, degrees,
(pitch, roll, yaw), '_loc' = world-axis offsets). Character faces -Y, up is +Z, character's left is +X.

The old gait (lib_char.walk_pose) swung the legs with sines: the stance foot floated up to ~15 cm off the
ground and slid along it.  Here every foot follows an explicit ground trajectory instead:
  * stance: the foot is planted and moves backwards at exactly the ground speed (in-place animation),
    rolling heel -> flat -> ball (toe-off); hips bob, sway, yaw and tilt like a real gait;
  * swing: the ankle follows a Hermite curve that leaves and lands with ground speed, so nothing skids;
  * legs are solved with analytic two-bone IK, feet are oriented in world space.
"""
import math

PI = math.pi
R2D = 180.0 / PI
D2R = PI / 180.0


# ----------------------------------------------------------------------------- tiny 3D math
def _rx(a):
    c, s = math.cos(a), math.sin(a)
    return ((1, 0, 0), (0, c, -s), (0, s, c))


def _ry(a):
    c, s = math.cos(a), math.sin(a)
    return ((c, 0, s), (0, 1, 0), (-s, 0, c))


def _rz(a):
    c, s = math.cos(a), math.sin(a)
    return ((c, -s, 0), (s, c, 0), (0, 0, 1))


def mm(A, B):
    return tuple(tuple(sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def mv(A, v):
    return tuple(sum(A[i][k] * v[k] for k in range(3)) for i in range(3))


def mt(A):
    return tuple(tuple(A[j][i] for j in range(3)) for i in range(3))


def vadd(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def vsub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vlen(a):
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def eul(e):
    """(pitch, roll, yaw) degrees -> matrix, same as lib_char.qw: Rz(yaw) Ry(roll) Rx(pitch)."""
    p, r, y = e
    return mm(_rz(y * D2R), mm(_ry(r * D2R), _rx(p * D2R)))


def to_eul(R):
    r = math.asin(max(-1.0, min(1.0, -R[2][0])))
    p = math.atan2(R[2][1], R[2][2])
    y = math.atan2(R[1][0], R[0][0])
    return (p * R2D, r * R2D, y * R2D)


def lerp(a, b, t):
    return a + (b - a) * t


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def hermite(p0, p1, m0, m1, t):
    t2, t3 = t * t, t * t * t
    return (2 * t3 - 3 * t2 + 1) * p0 + (t3 - 2 * t2 + t) * m0 + (-2 * t3 + 3 * t2) * p1 + (t3 - t2) * m1


# ----------------------------------------------------------------------------- skeleton / FK
BONES = [  # name, head joint, parent
    ("root", None, None), ("hips", "pelvis", "root"), ("spine", "spine", "hips"), ("chest", "chest", "spine"),
    ("neck", "neck", "chest"), ("head", "head", "neck")]
for _s in ("L", "R"):
    BONES += [(f"shoulder.{_s}", f"shoulder.{_s}", "chest"), (f"upper_arm.{_s}", f"arm.{_s}", f"shoulder.{_s}"),
              (f"forearm.{_s}", f"elbow.{_s}", f"upper_arm.{_s}"), (f"hand.{_s}", f"wrist.{_s}", f"forearm.{_s}"),
              (f"thigh.{_s}", f"hip.{_s}", "hips"), (f"shin.{_s}", f"knee.{_s}", f"thigh.{_s}"),
              (f"foot.{_s}", f"ankle.{_s}", f"shin.{_s}")]
HEAD = {n: h for n, h, _ in BONES}
PARENT = {n: p for n, _, p in BONES}
I3 = ((1, 0, 0), (0, 1, 0), (0, 0, 1))


def joints_tuple(j):
    return {k: (float(v[0]), float(v[1]), float(v[2])) for k, v in j.items()}


def fk(pose, J, upto=None):
    """World transforms {bone: (R, head_world)}; a rest point x of bone b maps to head_w + R (x - head_rest)."""
    out = {}
    locs = pose.get("_loc", {})
    for name, hj, par in BONES:
        hr = J[hj] if hj else (0.0, 0.0, 0.0)
        R = eul(pose[name]) if name in pose else I3
        l = locs.get(name, (0.0, 0.0, 0.0))
        p = vadd(hr, l)
        if par:
            PR, ph = out[par]
            phr = J[HEAD[par]] if HEAD[par] else (0.0, 0.0, 0.0)
            out[name] = (mm(PR, R), vadd(ph, mv(PR, vsub(p, phr))))
        else:
            out[name] = (R, p)
        if upto and name == upto:
            break
    return out


def world_point(T, J, bone, x):
    R, h = T[bone]
    hr = J[HEAD[bone]] if HEAD[bone] else (0.0, 0.0, 0.0)
    return vadd(h, mv(R, vsub(x, hr)))


# ----------------------------------------------------------------------------- leg IK
def _pitch(v):
    return math.atan2(v[1], -v[2])


def leg_ik(pose, J, side, ankle_w, foot_pitch, foot_roll=0.0, iters=3):
    """Solve thigh/shin/foot of `side` so the ankle reaches ankle_w (world) and the foot has world pitch
    foot_pitch (deg, + = toe down).  Needs root/hips already in `pose`.  Returns the reach error (m)."""
    T = fk(pose, J, upto="hips")
    HR, hh = T["hips"]
    hip, knee, ank = J[f"hip.{side}"], J[f"knee.{side}"], J[f"ankle.{side}"]
    t0, s0 = vsub(knee, hip), vsub(ank, knee)
    L1, L2 = vlen(t0), vlen(s0)
    target = ankle_w
    err = 0.0
    for _ in range(iters):
        x = vadd(mv(mt(HR), vsub(target, hh)), J["pelvis"])     # target in the hips rest frame
        d = vsub(x, hip)
        r = math.atan2(-d[0], -d[2])
        d2 = mv(_ry(-r), d)
        D = math.hypot(d2[1], d2[2])
        Dc = max(abs(L1 - L2) + 1e-4, min(L1 + L2 - 1e-4, D))
        phi = _pitch(d2)
        al = math.acos(max(-1, min(1, (L1 * L1 + Dc * Dc - L2 * L2) / (2 * L1 * Dc))))
        be = math.acos(max(-1, min(1, (L2 * L2 + Dc * Dc - L1 * L1) / (2 * L2 * Dc))))
        aT, aS = phi - al, phi + be
        p = aT - _pitch(t0)
        q = aS - _pitch(s0) - p
        pose[f"thigh.{side}"] = (p * R2D, r * R2D, 0.0)
        pose[f"shin.{side}"] = (q * R2D, 0.0, 0.0)
        # where did the ankle actually go?  correct the target for the tiny out-of-plane rest offsets
        Wt = mm(HR, eul(pose[f"thigh.{side}"]))
        kw = vadd(world_point(T, J, "hips", hip), mv(Wt, t0))
        aw = vadd(kw, mv(mm(Wt, eul(pose[f"shin.{side}"])), s0))
        e = vsub(ankle_w, aw)
        err = vlen(e)
        if err < 1e-4:
            break
        target = vadd(target, e)
    Wp = mm(HR, mm(eul(pose[f"thigh.{side}"]), eul(pose[f"shin.{side}"])))
    want = mm(_ry(foot_roll * D2R), _rx(foot_pitch * D2R))
    pose[f"foot.{side}"] = to_eul(mm(mt(Wp), want))
    return err


# ----------------------------------------------------------------------------- foot / ground contact
class Foot:
    """Rest geometry of a foot relative to its ankle: ball and heel contact points on the ground."""

    def __init__(self, J, side, s=1.0):
        a = J[f"ankle.{side}"]
        self.x, self.ay, self.az = a[0], a[1], a[2]
        self.ball = (-0.11 * s, -a[2])     # (dy, dz) from ankle to the ball of the foot on the ground
        self.heel = (0.05 * s, -a[2])

    def ankle(self, y_ref, f, lift=0.0):
        """Ankle position for a foot whose flat-on-ground ankle would be at y_ref, pitched by f degrees
        (f>0 rolls over the ball, f<0 rocks on the heel), raised by `lift`."""
        piv = self.ball if f >= 0 else self.heel
        py, pz = y_ref + piv[0], self.az + piv[1]
        vy, vz = -piv[0], -piv[1]
        c, s = math.cos(f * D2R), math.sin(f * D2R)
        return (self.x, py + vy * c - vz * s, pz + vy * s + vz * c + lift)


# ----------------------------------------------------------------------------- gait
GAITS = {
    # v: ground speed m/s (play at 1x at this speed); T: cycle s; duty: stance fraction; c: stance centre
    # behind the hip; f_td / f_to: foot pitch at touchdown / toe-off; bob: hip bob (+ = high at mid-stance)
    "walk": dict(v=1.5, T=22 / 24, duty=0.6, c=0.06, h0=0.912, bob=0.016, f_td=-10, flat=0.18, heel=0.55, f_to=28,
                 f_sw=-6, lift=0.09, lift_peak=0.4, tan=0.8, sway=0.022, yaw=5, roll=3, tilt=2, lean=3, chest_yaw=7,
                 arm_r=14, arm_l=6, elbow_r=0, elbow_l=0, arm_lag=0.04, width=0.0),
    "run": dict(v=3.4, T=15 / 24, duty=0.32, c=0.12, h0=0.905, bob=-0.03, f_td=-6, flat=0.12, heel=0.38, f_to=38,
                f_sw=25, lift=0.3, lift_peak=0.3, tan=0.25, sway=0.012, yaw=9, roll=3, tilt=8, lean=14,
                chest_yaw=14, arm_r=20, arm_l=12, elbow_r=-14, elbow_l=-18, hand_r=10, arm_lag=0.05, width=-0.02),
    "sprint": dict(v=5.6, T=13 / 24, duty=0.28, c=0.2, h0=0.885, bob=-0.036, f_td=-2, flat=0.08, heel=0.3, f_to=48,
                   f_sw=35, lift=0.42, lift_peak=0.28, tan=0.22, sway=0.008, yaw=12, roll=2, tilt=12, lean=20,
                   chest_yaw=18, arm_r=28, arm_l=16, elbow_r=-20, elbow_l=-22, hand_r=15, arm_lag=0.05, width=-0.03),
}


class Gait:
    def __init__(self, J, base, P, s=1.0):
        self.J, self.base, self.P, self.s = J, base, dict(P), s
        self.S = P["v"] * P["T"]                      # ground distance per full cycle
        self.feet = {X: Foot(J, X, s) for X in ("L", "R")}
        hip = J["hip.L"]
        self.Lmax = vlen(vsub(J["knee.L"], hip)) + vlen(vsub(J["ankle.L"], J["knee.L"]))

    # -- body ---------------------------------------------------------------
    def body(self, t):
        P, s, b = self.P, self.s, self.base
        du = P["duty"]
        ph = 2 * PI * t
        mid = 4 * PI * (t - du / 2)
        z = (P["h0"] - 0.98) * s + P["bob"] * s * math.cos(mid)
        x = P["sway"] * s * math.cos(ph - PI * du)
        yaw = -P["yaw"] * math.cos(ph)
        swing_mid = du + (1 - du) / 2
        roll = P["roll"] * math.cos(2 * PI * (t - swing_mid))
        lag = 2 * PI * P["arm_lag"]
        ca = math.cos(ph - lag)
        pose = {
            "hips": (P["tilt"], roll, yaw),
            "spine": (P["lean"] - P["tilt"] + 1.5 * math.sin(mid), -roll * 0.6, -yaw * 0.4),
            "chest": (0.0, 0.0, -yaw * 0.6 + P["chest_yaw"] * math.cos(ph - lag) * 0.5),
            "neck": (-P["lean"] * 0.4, 0, 0),
            "head": (-P["lean"] * 0.35 - 1.2 * math.sin(mid), 0, -P["chest_yaw"] * 0.5 * math.cos(ph - lag)),
            "upper_arm.R": (-P["arm_r"] * ca, 0, 0),
            "forearm.R": (P["elbow_r"] - 0.5 * P["arm_r"] * max(0.0, ca), 0, 0),
            "hand.R": (P.get("hand_r", 0) * max(0.0, ca), 0, 0),      # keep the blade from lifting like a lance
            "upper_arm.L": (P["arm_l"] * ca, 0, 0),
            "forearm.L": (P["elbow_l"] - 0.4 * P["arm_l"] * max(0.0, -ca), 0, 0),
            "_loc": {"hips": (x, 0.0, z)},
        }
        out = {}
        for k, v in b.items():
            if k != "_loc":
                out[k] = v
        for k, v in pose.items():
            if k == "_loc":
                out["_loc"] = {kk: tuple(vv) for kk, vv in v.items()}
            else:
                out[k] = tuple(a + c for a, c in zip(out.get(k, (0, 0, 0)), v))
        return out

    def hip_world(self, t, X):
        T = fk(self.body(t), self.J, upto="hips")
        return world_point(T, self.J, "hips", self.J[f"hip.{X}"])

    # -- feet ---------------------------------------------------------------
    def stance(self, t, u, X):
        P, s = self.P, self.s
        du = P["duty"]
        w = u / du
        y_ref = P["c"] * s - self.S * du / 2 + self.S * u
        if w < P["flat"]:
            f = lerp(P["f_td"], 0.0, smooth(w / P["flat"]))
        elif w < P["heel"]:
            f = 0.0
        else:
            k = (w - P["heel"]) / (1 - P["heel"])
            f = P["f_to"] * k * k
        foot = self.feet[X]
        hip = self.hip_world(t, X)
        a = foot.ankle(y_ref, f)
        lim = self.Lmax * 0.992
        if vlen(vsub(a, hip)) > lim:              # out of reach: roll further onto the ball
            lo, hi = max(f, 0.0), 80.0
            if vlen(vsub(foot.ankle(y_ref, hi), hip)) <= lim:
                for _ in range(24):
                    m = (lo + hi) / 2
                    if vlen(vsub(foot.ankle(y_ref, m), hip)) > lim:
                        lo = m
                    else:
                        hi = m
                f = hi
            else:
                f = hi
            a = foot.ankle(y_ref, f)
        return a, f

    def foot_state(self, t, X):
        P = self.P
        du = P["duty"]
        off = 0.0 if X == "L" else 0.5
        u = (t - off) % 1.0
        x_in = P["width"] * self.s * (1 if X == "L" else -1)
        if u < du:
            a, f = self.stance(t, u, X)
            return (a[0] + x_in, a[1], a[2]), f, True
        w = (u - du) / (1 - du)
        t_to = (off + du) % 1.0
        t_td = off % 1.0
        a0, f0 = self.stance(t_to, du, X)
        a1, f1 = self.stance(t_td, 0.0, X)
        m = self.S * (1 - du) * P["tan"]           # backwards (= +Y) tangent at both ends, ground speed
        y = hermite(a0[1], a1[1], m, m, w)
        g = math.log(0.5) / math.log(P["lift_peak"])
        z = lerp(a0[2], a1[2], w) + P["lift"] * self.s * math.sin(PI * w ** g)
        if w < 0.5:
            f = lerp(f0, P["f_sw"], smooth(w / 0.5))
        else:
            f = lerp(P["f_sw"], f1, smooth((w - 0.5) / 0.5))
        return (a0[0] + x_in, y, z), f, False

    def pose(self, t):
        pose = self.body(t)
        for X in ("L", "R"):
            a, f, _ = self.foot_state(t, X)
            leg_ik(pose, self.J, X, a, f)
        return pose


# ----------------------------------------------------------------------------- one-shot moves
def blend_poses(a, b, t):
    out = {}
    for k in set(a) | set(b):
        if k == "_loc":
            continue
        va, vb = a.get(k, (0, 0, 0)), b.get(k, (0, 0, 0))
        out[k] = tuple(x + (y - x) * t for x, y in zip(va, vb))
    la, lb = a.get("_loc", {}), b.get("_loc", {})
    out["_loc"] = {k: tuple(x + (y - x) * t for x, y in zip(la.get(k, (0, 0, 0)), lb.get(k, (0, 0, 0))))
                   for k in set(la) | set(lb)}
    return out


def plant(J, body, feet, s=1.0):
    """body pose (no legs) + feet {side: (y_ref, foot_pitch, lift)} -> full pose with IK legs."""
    pose = {k: (dict(v) if k == "_loc" else v) for k, v in body.items()}
    for X, (y_ref, f, lift) in feet.items():
        ft = Foot(J, X, s)
        leg_ik(pose, J, X, ft.ankle(y_ref, f, lift), f)
    return pose


def lowest_point(pose, J, pad=0.07):
    """Lowest world z of the body (joints + a padding radius for flesh/clothes)."""
    T = fk(pose, J)
    zs = [T[n][1][2] for n in T if n != "root"]
    for X in ("L", "R"):
        for tip in (f"toe.{X}", f"hand_end.{X}"):
            bone = "foot." + X if tip.startswith("toe") else "hand." + X
            zs.append(world_point(T, J, bone, J[tip])[2] + pad * 0.3)
    top = world_point(T, J, "head", J["head_top"])
    zs.append(top[2])
    return min(zs) - pad


# ----------------------------------------------------------------------------- hero one-shots
STAND_Y = 0.02     # ankle y of a foot standing in the rest pose


def _keyed(keys, t):
    """keys: [(t, ...)] -> (segment index, smoothstep fraction)."""
    for i in range(len(keys) - 1):
        if t <= keys[i + 1][0]:
            u = (t - keys[i][0]) / max(keys[i + 1][0] - keys[i][0], 1e-6)
            return i, smooth(u)
    return len(keys) - 2, 1.0


def planted_seq(J, keys, s=1.0):
    """keys: [(t, body_pose, feet)] -> fn(t) blending bodies and foot targets, legs by IK (feet stay planted)."""
    def f(t):
        i, u = _keyed(keys, t)
        (_, b0, f0), (_, b1, f1) = keys[i], keys[i + 1]
        body = blend_poses(b0, b1, u)
        feet = {X: tuple(lerp(a, b, u) for a, b in zip(f0[X], f1[X])) for X in ("L", "R")}
        return plant(J, body, feet, s)
    return f


def _with(base, extra):
    out = {k: v for k, v in base.items() if k != "_loc"}
    for k, v in extra.items():
        if k != "_loc":
            out[k] = tuple(a + b for a, b in zip(out.get(k, (0, 0, 0)), v))
    out["_loc"] = dict(extra.get("_loc", {}))
    return out


def hero_moves(J, base, s=1.0):
    """Roll (dodge), backstep (dodge_back) and jump for the hero. Returns {name: (fn, seconds)}."""
    stand_feet = {"L": (STAND_Y, 0, 0), "R": (STAND_Y, 0, 0)}
    stand = _with(base, {})

    # ---------------------------------------------------------------- forward combat roll
    dive_b = _with(base, {"hips": (22, 0, 0), "spine": (22, 0, 0), "chest": (8, 0, 0), "head": (-18, 0, 0),
                          "upper_arm.R": (-40, 18, 0), "forearm.R": (-50, 0, 0),
                          "upper_arm.L": (-45, -10, 0), "forearm.L": (-25, 0, -20),
                          "_loc": {"hips": (0, -0.04 * s, -0.3 * s)}})
    dive_f = {"L": (-0.28 * s, 0, 0), "R": (0.3 * s, 38, 0)}
    tuck_b = _with(base, {"hips": (30, 0, 0), "spine": (38, 0, 0), "chest": (22, 0, 0), "neck": (20, 0, 0), "head": (28, 0, 0),
                          "upper_arm.R": (-55, 25, 0), "forearm.R": (-70, 0, 0), "hand.R": (30, 0, 0),
                          "upper_arm.L": (-60, -10, 0), "forearm.L": (-45, 0, -25),
                          "thigh.L": (-125, 0, 0), "thigh.R": (-115, 0, 0), "shin.L": (140, 0, 0), "shin.R": (135, 0, 0),
                          "foot.L": (35, 0, 0), "foot.R": (35, 0, 0),
                          "_loc": {"hips": (0, 0, -0.3 * s)}})
    land_b = _with(base, {"hips": (18, 0, 0), "spine": (20, 0, 0), "chest": (6, 0, 0), "head": (-12, 0, 0),
                          "upper_arm.R": (-30, 15, 0), "forearm.R": (-45, 0, 0),
                          "upper_arm.L": (-40, -10, 0), "forearm.L": (-30, 0, -20),
                          "_loc": {"hips": (0, 0.02 * s, -0.32 * s)}})
    land_f = {"L": (-0.12 * s, 0, 0), "R": (0.24 * s, 30, 0)}
    rise_b = _with(base, {"hips": (6, 0, 0), "spine": (8, 0, 0), "_loc": {"hips": (0, 0, -0.06 * s)}})
    rise_f = {"L": (-0.06 * s, 0, 0), "R": (0.12 * s, 12, 0)}
    enter = planted_seq(J, [(0, stand, stand_feet), (1, dive_b, dive_f)], s)
    leave = planted_seq(J, [(0, land_b, land_f), (0.55, rise_b, rise_f), (1, stand, stand_feet)], s)
    k_dive = enter(1.0)
    k_land = leave(0.0)
    t_in, t_out = 0.16, 0.74
    z_dive = lowest_point(k_dive, J)
    z_land = lowest_point(k_land, J)

    def roll(t):
        if t <= t_in:
            return enter(t / t_in)
        if t >= t_out:
            return leave((t - t_out) / (1 - t_out))
        w = (t - t_in) / (t_out - t_in)
        a = blend_poses(k_dive, tuck_b, smooth(w / 0.3))
        if w > 0.7:
            a = blend_poses(a, k_land, smooth((w - 0.7) / 0.3))
        ang = 360.0 * (w - math.sin(2 * PI * w) / (2 * PI))      # slow in, fast through the roll, slow out
        # spin the hips (parent of legs and spine) about the lower back: small pivot offsets interpolate cleanly
        a["_loc"] = {k: tuple(v) for k, v in a.get("_loc", {}).items()}
        p0 = world_point(fk(a, J), J, "spine", J["spine"])
        hp, hr, hy = a.get("hips", (0.0, 0.0, 0.0))
        a["hips"] = (hp + ang, hr, hy)
        p1 = world_point(fk(a, J), J, "spine", J["spine"])
        l = a["_loc"].get("hips", (0.0, 0.0, 0.0))
        l = (l[0] + p0[0] - p1[0], l[1] + p0[1] - p1[1], l[2] + p0[2] - p1[2])
        a["_loc"]["hips"] = l
        low = lowest_point(a, J)                 # rest the lowest body point on the ground
        want = lerp(z_dive, z_land, smooth(w))
        a["_loc"]["hips"] = (l[0], l[1], l[2] - (low - want))
        return a

    # ---------------------------------------------------------------- backstep hop (dodge with no direction)
    push_b = _with(base, {"hips": (-4, 0, 0), "spine": (12, 0, 0), "head": (-8, 0, 0),
                          "upper_arm.L": (-45, -12, 0), "forearm.L": (-35, 0, -35), "upper_arm.R": (-15, 15, 0),
                          "_loc": {"hips": (0, 0.03 * s, -0.16 * s)}})
    push_f = {"L": (-0.08 * s, 0, 0), "R": (0.1 * s, 0, 0)}
    air_b = _with(base, {"hips": (-6, 0, 0), "spine": (16, 0, 0), "head": (-10, 0, 0),
                         "upper_arm.L": (-50, -15, 0), "forearm.L": (-35, 0, -35), "upper_arm.R": (-25, 25, 0),
                         "_loc": {"hips": (0, 0.0, 0.05 * s)}})
    air_f = {"L": (-0.1 * s, -10, 0.12 * s), "R": (0.04 * s, 15, 0.08 * s)}
    land2_b = _with(base, {"hips": (4, 0, 0), "spine": (14, 0, 0), "head": (-8, 0, 0),
                           "upper_arm.L": (-45, -12, 0), "forearm.L": (-35, 0, -35), "upper_arm.R": (-20, 20, 0),
                           "_loc": {"hips": (0, 0.02 * s, -0.2 * s)}})
    land2_f = {"L": (-0.12 * s, 0, 0), "R": (0.16 * s, 18, 0)}
    back = planted_seq(J, [(0, stand, stand_feet), (0.16, push_b, push_f), (0.4, air_b, air_f),
                           (0.62, land2_b, land2_f), (1, stand, stand_feet)], s)

    # ---------------------------------------------------------------- jump (crouch, take-off, tuck, land)
    crouch_b = _with(base, {"hips": (14, 0, 0), "spine": (16, 0, 0), "head": (-10, 0, 0), "upper_arm.R": (10, 10, 0),
                            "upper_arm.L": (5, -10, 0), "_loc": {"hips": (0, 0.03 * s, -0.24 * s)}})
    crouch_f = {"L": (STAND_Y - 0.04 * s, 0, 0), "R": (STAND_Y + 0.06 * s, 0, 0)}
    off_b = _with(base, {"hips": (2, 0, 0), "spine": (4, 0, 0), "head": (-4, 0, 0), "upper_arm.R": (-55, 20, 0),
                         "upper_arm.L": (-45, -20, 0)})
    off_f = {"L": (STAND_Y - 0.06 * s, 45, 0), "R": (STAND_Y + 0.06 * s, 50, 0)}
    tuckj_b = _with(base, {"hips": (4, 0, 0), "spine": (6, 0, 0), "upper_arm.R": (-45, 25, 0), "upper_arm.L": (-50, -25, 0),
                           "_loc": {"hips": (0, 0, -0.02 * s)}})
    tuckj_f = {"L": (-0.1 * s, 10, 0.32 * s), "R": (0.12 * s, 30, 0.2 * s)}
    reach_b = _with(base, {"hips": (6, 0, 0), "spine": (8, 0, 0), "upper_arm.R": (-35, 30, 0), "upper_arm.L": (-40, -25, 0),
                           "_loc": {"hips": (0, 0, -0.03 * s)}})
    reach_f = {"L": (-0.06 * s, 18, 0.1 * s), "R": (0.08 * s, 20, 0.06 * s)}
    landj_b = _with(base, {"hips": (16, 0, 0), "spine": (14, 0, 0), "head": (-8, 0, 0), "upper_arm.R": (-20, 20, 0),
                           "upper_arm.L": (-25, -20, 0), "_loc": {"hips": (0, 0.02 * s, -0.2 * s)}})
    landj_f = {"L": (-0.05 * s, 0, 0), "R": (0.08 * s, 0, 0)}
    jump = planted_seq(J, [(0, stand, stand_feet), (0.14, crouch_b, crouch_f), (0.26, off_b, off_f),
                           (0.45, tuckj_b, tuckj_f), (0.72, reach_b, reach_f), (0.84, landj_b, landj_f),
                           (1, stand, stand_feet)], s)
    return {"dodge": (roll, 0.6), "dodge_back": (back, 0.5), "jump": (jump, 0.9)}
