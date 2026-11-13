"""Character toolkit: lofted body parts, humanoid / horse skeletons, distance-based skinning,
pose + action helpers.

Conventions (decisions.md):
  * Characters face Blender -Y (= Godot +Z, the glTF "front"). Character's left = +X.
  * One humanoid skeleton (same bone names) for every human, the skeleton warrior and the golem,
    so animations can be shared/retargeted in Godot.
  * Poses are written as rotations about WORLD axes in the rest pose (pitch=X, roll=Y, yaw=Z, degrees)
    and converted to bone-local quaternions, so bone roll never matters.
      pitch < 0 : limb hanging down swings FORWARD; bone pointing up leans BACK
      pitch > 0 : knee bends (foot goes back), spine leans forward, foot toe down
      roll      : left arm outward = negative, right arm outward = positive
      yaw > 0   : turn to the character's left
  * Each action becomes its own NLA track -> exported as a separately named glTF animation.
"""
import math
import random

import bpy
from mathutils import Quaternion, Vector

import lib_geo as G
from lib_geo import MB

PI = math.pi
FPS = 24

G.MATS.update({
    "M_Chainmail": ("chainmail", 0.35, 0.45, 0.85, {}),
    "M_ChainmailRust": ("chainmail_rust", 0.35, 0.75, 0.4, {}),
    "M_LeatherC": ("leather", 0.5, 0.7, 0.0, {}),
    "M_LeatherDark": ("leather_dark", 0.5, 0.7, 0.0, {}),
    "M_Skin": ("skin", 0.4, 0.65, 0.0, {}),
    "M_SkinPale": ("skin_pale", 0.4, 0.65, 0.0, {}),
    "M_SkinChild": ("skin_child", 0.4, 0.65, 0.0, {}),
    "M_HairDark": ("hair_dark", 0.25, 0.7, 0.0, {}),
    "M_HairBrown": ("hair_brown", 0.25, 0.7, 0.0, {}),
    "M_HairGrey": ("hair_grey", 0.25, 0.7, 0.0, {}),
    "M_Fur": ("fur", 0.3, 0.9, 0.0, {}),
    "M_Clay": ("clay_golem", 1.6, 0.95, 0.0, {}),
    "M_Bone": ("bone", 0.4, 0.75, 0.0, {}),
    "M_RobeDark": ("robe_dark", 1.0, 0.95, 0.0, {}),
    "M_RobeBrown": ("robe_brown", 1.0, 0.95, 0.0, {}),
    "M_Rags": ("rags", 1.0, 0.95, 0.0, {}),
    "M_Linen": ("linen", 0.8, 0.95, 0.0, {}),
    "M_Apron": ("apron_bloody", 0.9, 0.9, 0.0, {}),
    "M_WoolBlue": ("wool_blue", 0.8, 0.95, 0.0, {}),
    "M_WoolBrown": ("wool_brown", 0.8, 0.95, 0.0, {}),
    "M_MantleRed": ("mantle_red", 1.0, 0.95, 0.0, {}),
    "M_MerchantCoat": ("merchant_coat", 1.0, 0.9, 0.0, {}),
    "M_HorseCoat": ("horse_coat", 0.9, 0.7, 0.0, {}),
    "M_HorseHair": ("horse_hair", 0.4, 0.8, 0.0, {}),
    "M_GolemLetters": ("golem_letters", 0.0, 0.9, 0.0, {"fit": True, "emit": "golem_letters_emit", "strength": 4.0}),
    "M_Tabard": ("tabard_lion", 0.0, 0.95, 0.0, {"fit": True}),
    "M_RustyIron": ("iron_rust", 0.5, 0.8, 0.4, {}),
    "M_EyeGlow": (None, 0, 0.4, 0.0, {"color": (0.25, 0.9, 0.2), "emit_color": (0.35, 1.0, 0.25), "strength": 10.0}),
    "M_VialGreen": (None, 0, 0.1, 0.0, {"color": (0.35, 0.8, 0.15), "emit_color": (0.45, 1.0, 0.2), "strength": 3.0}),
    "M_VialPurple": (None, 0, 0.1, 0.0, {"color": (0.45, 0.15, 0.7), "emit_color": (0.6, 0.2, 1.0), "strength": 3.0}),
    "M_EyeWhite": (None, 0, 0.3, 0.0, {"color": (0.78, 0.74, 0.66)}),
    "M_EyeDark": (None, 0, 0.3, 0.0, {"color": (0.04, 0.03, 0.025)}),
    "M_Lips": (None, 0, 0.6, 0.0, {"color": (0.38, 0.18, 0.15)}),
    "M_Hoof": (None, 0, 0.6, 0.0, {"color": (0.1, 0.085, 0.07)}),
})


# ============================================================================= mesh helpers
def loft(mb, pts, radii, mat, segs=12, cap0=True, cap1=True, noise=0.0, seed=0, side_ref=(1, 0, 0), smooth=True,
         jag=0.0, closed=None):
    """Tube through points with per-point (rx, ry) elliptical sections. rx along side_ref."""
    rnd = random.Random(seed)
    pts = [Vector(p) for p in pts]
    n = len(pts)
    rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        ref = Vector(side_ref)
        if abs(ref.dot(t)) > 0.95:
            ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((0, 1, 0))
        side = (ref - ref.dot(t) * t).normalized()
        up = t.cross(side)
        r = radii[i]
        rx, ry = (r, r) if not isinstance(r, (tuple, list)) else r
        ring = []
        for k in range(segs):
            a = 2 * PI * k / segs
            f = 1.0 + (rnd.uniform(-noise, noise) if noise else 0.0)
            q = p + side * (rx * f * math.cos(a)) + up * (ry * f * math.sin(a))
            if jag and i == n - 1:
                q = q + t * rnd.uniform(-jag, jag * 0.3)
            ring.append(mb._v(q))
        rings.append(ring)
    cl = (cap0 and cap1) if closed is None else closed
    for a, b in zip(rings[:-1], rings[1:]):
        for k in range(segs):
            j = (k + 1) % segs
            mb._quad_idx([a[k], a[j], b[j], b[k]], mat, "world", smooth, cl)
    if cap0:
        c = mb._v(pts[0] - (pts[1] - pts[0]).normalized() * 0.0)
        for k in range(segs):
            mb._quad_idx([rings[0][(k + 1) % segs], rings[0][k], c], mat, "world", smooth, cl)
    if cap1:
        c = mb._v(pts[-1])
        for k in range(segs):
            mb._quad_idx([rings[-1][k], rings[-1][(k + 1) % segs], c], mat, "world", smooth, cl)


def lerpv(a, b, t):
    return Vector(a).lerp(Vector(b), t)


# ============================================================================= skeletons
HUMAN_JOINTS = {
    "pelvis": (0, 0, 0.98), "spine": (0, 0, 1.1), "chest": (0, 0, 1.28), "neck": (0, 0.0, 1.49),
    "head": (0, -0.005, 1.6), "head_top": (0, -0.01, 1.82),
    "shoulder.L": (0.05, 0, 1.44), "arm.L": (0.19, 0.0, 1.44), "elbow.L": (0.235, 0.01, 1.165),
    "wrist.L": (0.265, -0.02, 0.925), "hand_end.L": (0.275, -0.03, 0.82),
    "hip.L": (0.1, 0, 0.95), "knee.L": (0.11, -0.01, 0.53), "ankle.L": (0.11, 0.02, 0.09), "toe.L": (0.11, -0.13, 0.02),
}
HUMAN_BONES = [
    # name, head joint, tail joint, parent
    ("root", None, None, None),
    ("hips", "pelvis", "spine", "root"),
    ("spine", "spine", "chest", "hips"),
    ("chest", "chest", "neck", "spine"),
    ("neck", "neck", "head", "chest"),
    ("head", "head", "head_top", "neck"),
]
for _s in ("L", "R"):
    HUMAN_BONES += [
        (f"shoulder.{_s}", f"shoulder.{_s}", f"arm.{_s}", "chest"),
        (f"upper_arm.{_s}", f"arm.{_s}", f"elbow.{_s}", f"shoulder.{_s}"),
        (f"forearm.{_s}", f"elbow.{_s}", f"wrist.{_s}", f"upper_arm.{_s}"),
        (f"hand.{_s}", f"wrist.{_s}", f"hand_end.{_s}", f"forearm.{_s}"),
        (f"thigh.{_s}", f"hip.{_s}", f"knee.{_s}", "hips"),
        (f"shin.{_s}", f"knee.{_s}", f"ankle.{_s}", f"thigh.{_s}"),
        (f"foot.{_s}", f"ankle.{_s}", f"toe.{_s}", f"shin.{_s}"),
    ]


def human_joints(H=1.8, over=None, width=1.0):
    s = H / 1.8
    j = {}
    src = dict(HUMAN_JOINTS)
    src.update(over or {})
    for k, v in src.items():
        if k.endswith(".R"):
            continue
        x, y, z = v
        j[k] = Vector((x * s * width, y * s, z * s))
        if k.endswith(".L"):
            j[k[:-2] + ".R"] = Vector((-x * s * width, y * s, z * s))
    return j


def make_armature(name, joints, bones, parent, col):
    ad = bpy.data.armatures.new(name + "_rig")
    ob = bpy.data.objects.new(name + "_rig", ad)
    col.objects.link(ob)
    ob.parent = parent
    ad.display_type = "STICK"
    vl = bpy.context.view_layer
    for o in vl.objects:
        o.select_set(False)
    vl.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = {}
    for bname, h, t, par in bones:
        b = ad.edit_bones.new(bname)
        if h is None:
            b.head, b.tail = Vector((0, 0, 0)), Vector((0, 0, 0.25 * joints["pelvis"].z / 0.98))
        else:
            b.head, b.tail = joints[h], joints[t]
        b.roll = 0.0
        if par:
            b.parent = eb[par]
            b.use_connect = False
        eb[bname] = b
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in ob.pose.bones:
        pb.rotation_mode = "QUATERNION"
    return ob


# ============================================================================= skinning
def _seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (p - (a + ab * t)).length


def skin(ob, arm, bones, sharp=4.0, top=3):
    """Smooth weights from distance to bone segments (rest pose). `bones` = allowed bone names."""
    rest = {b.name: (b.head_local.copy(), b.tail_local.copy()) for b in arm.data.bones}
    groups = {n: (ob.vertex_groups.get(n) or ob.vertex_groups.new(name=n)) for n in bones}
    for v in ob.data.vertices:
        p = v.co
        ws = sorted(((1.0 / max(_seg_dist(p, *rest[n]), 0.004) ** sharp, n) for n in bones), reverse=True)[:top]
        tot = sum(w for w, _ in ws)
        for w, n in ws:
            if w / tot > 0.01:
                groups[n].add([v.index], w / tot, "REPLACE")


def bind(ob, arm):
    ob.parent = arm
    m = ob.modifiers.new("Armature", "ARMATURE")
    m.object = arm


class Body:
    """Collects mesh parts with their allowed bones; builds, skins and joins them."""

    def __init__(self, name, arm, col):
        self.name, self.arm, self.col = name, arm, col
        self.parts = []
        self.extras = []

    def part(self, bones, sharp=4.0):
        mb = MB()
        self.parts.append((mb, bones if isinstance(bones, (list, tuple)) else [bones], sharp))
        return mb

    def separate(self, obj_name, bones, sharp=4.0):
        """Separate skinned object (weapon / prop held), kept as its own node: WEAPON_* etc."""
        mb = MB()
        self.extras.append((mb, obj_name, bones if isinstance(bones, (list, tuple)) else [bones], sharp))
        return mb

    def build(self):
        objs = []
        for i, (mb, bones, sharp) in enumerate(self.parts):
            if not mb.faces:
                continue
            ob = mb.build(f"{self.name}_part{i}", None, self.col)
            skin(ob, self.arm, bones, sharp)
            objs.append(ob)
        vl = bpy.context.view_layer
        for o in vl.objects:
            o.select_set(False)
        for o in objs:
            o.select_set(True)
        vl.objects.active = objs[0]
        bpy.ops.object.join()
        body = vl.objects.active
        body.name = self.name + "_body"
        body.data.name = self.name + "_body"
        bind(body, self.arm)
        out = [body]
        for mb, oname, bones, sharp in self.extras:
            ob = mb.build(oname, None, self.col)
            skin(ob, self.arm, bones, sharp)
            bind(ob, self.arm)
            out.append(ob)
        return out


# ============================================================================= posing
def qw(p=0.0, r=0.0, y=0.0):
    return Quaternion((0, 0, 1), math.radians(y)) @ Quaternion((0, 1, 0), math.radians(r)) @ \
        Quaternion((1, 0, 0), math.radians(p))


def apply_pose(arm, pose):
    """pose: {bone: (pitch, roll, yaw)} plus optional '_loc': {bone: (x, y, z) world offset}."""
    locs = pose.get("_loc", {})
    for pb in arm.pose.bones:
        B = pb.bone.matrix_local.to_quaternion()
        e = pose.get(pb.name)
        if e:
            pb.rotation_quaternion = B.inverted() @ qw(*e) @ B
        else:
            pb.rotation_quaternion = Quaternion()
        l = locs.get(pb.name)
        pb.location = (B.inverted() @ Vector(l)) if l else Vector((0, 0, 0))


def mix(a, b, t):
    out = {}
    for k in set(a) | set(b):
        if k == "_loc":
            continue
        va, vb = a.get(k, (0, 0, 0)), b.get(k, (0, 0, 0))
        out[k] = tuple(x + (y - x) * t for x, y in zip(va, vb))
    la, lb = a.get("_loc", {}), b.get("_loc", {})
    if la or lb:
        out["_loc"] = {k: tuple(x + (y - x) * t for x, y in zip(la.get(k, (0, 0, 0)), lb.get(k, (0, 0, 0))))
                       for k in set(la) | set(lb)}
    return out


def add(*poses):
    out = {}
    for p in poses:
        for k, v in p.items():
            if k == "_loc":
                d = out.setdefault("_loc", {})
                for b, l in v.items():
                    d[b] = tuple(x + y for x, y in zip(d.get(b, (0, 0, 0)), l))
            else:
                out[k] = tuple(x + y for x, y in zip(out.get(k, (0, 0, 0)), v))
    return out


def seq(keys):
    """keys: [(t, pose), ...] t in [0,1]; smoothstep between keys."""
    def f(t):
        for (t0, p0), (t1, p1) in zip(keys[:-1], keys[1:]):
            if t <= t1:
                u = (t - t0) / max(t1 - t0, 1e-6)
                u = u * u * (3 - 2 * u)
                return mix(p0, p1, u)
        return keys[-1][1]
    return f


def make_action(arm, name, seconds, fn, step=2):
    frames = max(2, int(round(seconds * FPS)))
    act = bpy.data.actions.new(f"{arm.name}_{name}")
    act.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = act
    fs = list(range(0, frames + 1, step))
    if fs[-1] != frames:
        fs.append(frames)
    for f in fs:
        apply_pose(arm, fn(f / frames))
        for pb in arm.pose.bones:
            pb.keyframe_insert("rotation_quaternion", frame=f)
            pb.keyframe_insert("location", frame=f)
    arm.animation_data.action = None
    tr = arm.animation_data.nla_tracks.new()
    tr.name = name
    tr.strips.new(name, 0, act)
    return act


# ============================================================================= humanoid motion library
def walk_pose(t, A=24, K=48, arm=16, bob=0.035, lean=3, sway=5, elbow=12, base=None, heavy=0.0):
    ph = 2 * PI * t
    s, c = math.sin(ph), math.cos(ph)
    kl = K * max(0.0, c) ** 1.5 + 5
    kr = K * max(0.0, -c) ** 1.5 + 5
    p = {
        "thigh.L": (-A * s, 0, 0), "thigh.R": (A * s, 0, 0),
        "shin.L": (kl, 0, 0), "shin.R": (kr, 0, 0),
        "foot.L": (-0.8 * (-A * s + kl), 0, 0), "foot.R": (-0.8 * (A * s + kr), 0, 0),
        "upper_arm.L": (arm * s, 0, 0), "upper_arm.R": (-arm * s, 0, 0),
        "forearm.L": (-elbow - 0.4 * arm * max(0, -s), 0, 0), "forearm.R": (-elbow - 0.4 * arm * max(0, s), 0, 0),
        "hips": (0, heavy * 6 * s, -sway * s), "spine": (lean, 0, 0), "chest": (0, -heavy * 4 * s, sway * 1.4 * s),
        "head": (-lean * 0.6, 0, -sway * 0.6 * s),
        "_loc": {"hips": (heavy * 0.04 * s, 0, -bob * s * s)},
    }
    return add(base or {}, p)


def human_actions(arm, base, spec):
    """Create the standard action set. spec: dict of tuning + which extra actions to make.
    Returns {action: seconds} for documentation."""
    made = {}
    g = spec.get("gait", {})
    heavy = spec.get("heavy", 0.0)
    idle_base = base

    def idle(t):
        ph = 2 * PI * t
        return add(idle_base, {"chest": (1.5 * math.sin(ph), 0, 0), "spine": (0.8 * math.sin(ph), 0, 0),
                               "head": (1.2 * math.sin(ph + 1), 0, 2 * math.sin(ph * 0.5)),
                               "upper_arm.L": (1.5 * math.sin(ph + 0.5), 0, 0), "upper_arm.R": (-1.5 * math.sin(ph + 0.5), 0, 0),
                               "_loc": {"hips": (0, 0, -0.005 * (1 - math.cos(ph)))}})

    T = spec.get("idle_s", 2.5)
    make_action(arm, "idle", T, idle); made["idle"] = T
    if spec.get("loco"):     # foot-planted IK locomotion (lib_gait): {name: (fn, seconds)}, keyed every frame
        for an, (fn, T) in spec["loco"].items():
            make_action(arm, an, T, fn, step=1); made[an] = T
    else:
        T = g.get("walk_T", 1.0)
        make_action(arm, "walk", T, lambda t: walk_pose(t, base=base, heavy=heavy, **g.get("walk", {}))); made["walk"] = T
        T = g.get("run_T", 0.66)
        run = dict(A=38, K=100, arm=38, bob=0.05, lean=12, sway=7, elbow=70)
        run.update(g.get("run", {}))
        make_action(arm, "run", T, lambda t: walk_pose(t, base=base, heavy=heavy, **run)); made["run"] = T

    flinch = add(base, {"spine": (-14, 0, 6), "chest": (-10, 0, 0), "head": (-18, 0, 0), "upper_arm.L": (-20, -10, 0),
                        "upper_arm.R": (-20, 10, 0), "forearm.L": (-40, 0, 0), "forearm.R": (-40, 0, 0),
                        "thigh.R": (12, 0, 0), "shin.R": (10, 0, 0), "_loc": {"hips": (0, 0.05, -0.03)}})
    T = 0.45
    make_action(arm, "hit", T, seq([(0, base), (0.25, flinch), (1, base)])); made["hit"] = T

    buckle = add(base, {"spine": (20, 0, 0), "head": (15, 0, 0), "thigh.L": (-40, 0, 0), "thigh.R": (-30, 0, 0),
                        "shin.L": (75, 0, 0), "shin.R": (65, 0, 0), "foot.L": (-30, 0, 0), "foot.R": (-30, 0, 0),
                        "upper_arm.L": (-10, -15, 0), "upper_arm.R": (-10, 15, 0),
                        "_loc": {"hips": (0, 0, -0.3 * spec.get("scale", 1.0))}})
    lying = {"root": (-90, 0, 0), "spine": (-5, 0, 0), "head": (-10, 0, 20), "thigh.L": (-5, 0, 0), "thigh.R": (-10, 4, 0),
             "shin.L": (8, 0, 0), "shin.R": (15, 0, 0), "upper_arm.L": (-15, -50, 0), "upper_arm.R": (-30, 60, 0),
             "forearm.L": (-30, 0, 0), "forearm.R": (-20, 0, 0),
             "_loc": {"root": (0, 0, 0.13 * spec.get("scale", 1.0) * spec.get("girth", 1.0))}}
    T = 1.3
    make_action(arm, "death", T, seq([(0, base), (0.15, flinch), (0.45, buckle), (0.85, lying), (1, lying)])); made["death"] = T

    if "attack" in spec:
        keys, T = spec["attack"]
        make_action(arm, "attack", T, seq(keys)); made["attack"] = T
    for extra, (fn, T) in spec.get("extra", {}).items():
        make_action(arm, extra, T, fn); made[extra] = T

    # thrown out of a window / tumbling: loop
    def flail(t):
        ph = 2 * PI * t
        return add(base, {"upper_arm.L": (-150 + 30 * math.sin(ph), -30, 0), "upper_arm.R": (-150 - 30 * math.sin(ph), 30, 0),
                          "forearm.L": (-30, 0, 0), "forearm.R": (-30, 0, 0), "spine": (-15, 0, 0), "head": (-20, 0, 0),
                          "thigh.L": (-40 * math.sin(ph), 0, 0), "thigh.R": (40 * math.sin(ph), 0, 0),
                          "shin.L": (40, 0, 0), "shin.R": (40, 0, 0)})
    if spec.get("flail", True):
        make_action(arm, "flail", 0.6, flail); made["flail"] = 0.6
    apply_pose(arm, base)
    return made


def walk_speed(leg_len, A_deg, T):
    """Ground speed (m/s) at which feet don't slide for the sinusoidal gait above."""
    return 4 * leg_len * math.sin(math.radians(A_deg)) / T * 0.8
