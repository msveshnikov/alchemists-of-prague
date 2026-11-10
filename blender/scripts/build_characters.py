"""Build all Old Town Square characters: models, rigs, animations, glTF export, previews.

blender -b --factory-startup -P build_characters.py [-- --only vaclav,golem] [--no-render]
Outputs: blender/characters.blend, assets/characters/*.gltf, renders/previews/char_*.png
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import lib_geo as G  # noqa: E402
import lib_char as C  # noqa: E402
from lib_char import add, loft, seq  # noqa: E402
from lib_geo import MB  # noqa: E402

OUT = os.path.join(G.PROJECT, "assets", "characters")
PI = math.pi
V = Vector
INFO = {}   # name -> dict for characters_list / report


# ============================================================================= rig helpers
def posed_to_rest(arm, bone):
    """Matrix mapping a point given in the CURRENT POSE (world) to the rest pose of `bone`."""
    pb = arm.pose.bones[bone]
    return pb.bone.matrix_local @ pb.matrix.inverted()


def posed_points(arm, bone):
    pb = arm.pose.bones[bone]
    return pb.matrix @ V((0, 0, 0)), pb.matrix @ V((0, pb.bone.length, 0))


def start(name, H, over=None, width=1.0, bones=None, joints=None):
    root, col = G.new_asset(name, "characters")
    j = joints or C.human_joints(H, over, width)
    arm = C.make_armature(name, j, bones or C.HUMAN_BONES, root, col)
    return root, col, arm, j


def set_base(arm, base):
    C.apply_pose(arm, base)
    bpy.context.view_layer.update()


# ============================================================================= body parts (humanoid)
def legs(B, j, s, mat, r=1.0, boots=None, boot_top=0.45, bare_feet=None):
    for X in ("L", "R"):
        hip, knee, ank, toe = j[f"hip.{X}"], j[f"knee.{X}"], j[f"ankle.{X}"], j[f"toe.{X}"]
        mb = B.part(["hips", f"thigh.{X}", f"shin.{X}"], 5)
        loft(mb, [hip + V((0, 0, 0.05 * s)), hip.lerp(knee, 0.5), knee, knee.lerp(ank, 0.45), ank + V((0, 0, 0.02 * s))],
             [0.088 * s * r, 0.074 * s * r, 0.053 * s * r, 0.058 * s * r, 0.04 * s * r], mat, segs=10)
        fm = boots or bare_feet
        mb = B.part([f"shin.{X}", f"foot.{X}"], 5)
        if boots:
            loft(mb, [knee.lerp(ank, boot_top), knee.lerp(ank, 0.8), ank + V((0, 0, 0.0))],
                 [(0.066 * s * r, 0.064 * s * r), (0.054 * s * r, 0.054 * s * r), (0.05 * s * r, 0.055 * s * r)], boots, segs=10)
        heel = V((ank.x, ank.y + 0.05 * s, 0.045 * s))
        tip = V((toe.x, toe.y - 0.03 * s, 0.035 * s))
        loft(mb, [heel, heel.lerp(tip, 0.4) + V((0, 0, 0.01 * s)), tip],
             [(0.045 * s * r, 0.045 * s), (0.05 * s * r, 0.04 * s), (0.04 * s * r, 0.028 * s)], fm, segs=10)


TORSO = [  # (joint-relative z offset fraction, rx, ry, y offset)  for H=1.8
    (0.88, 0.155, 0.10, 0.0), (1.00, 0.165, 0.112, 0.0), (1.10, 0.15, 0.102, 0.005), (1.28, 0.175, 0.118, 0.0),
    (1.40, 0.19, 0.118, 0.0), (1.46, 0.16, 0.10, 0.01), (1.515, 0.07, 0.065, 0.0)]


def torso(B, s, mat, w=1.0, d=1.0, grow=0.0, z_from=0.88, z_to=1.515, cap=True, jag=0.0, belly=0.0):
    pts, radii = [], []
    for z, rx, ry, y in TORSO:
        if z < z_from - 1e-3 or z > z_to + 1e-3:
            continue
        b = belly if 1.0 <= z <= 1.2 else 0.0
        pts.append(V((0, y * s - b * 0.5 * s, z * s)))
        radii.append(((rx * w + grow) * s, (ry * d + grow + b) * s))
    mb = B.part(["hips", "spine", "chest", "neck"], 3)
    loft(mb, pts, radii, mat, segs=14, cap0=cap, cap1=cap, jag=jag)
    return mb


def skirt(B, s, mat, z_top, z_hem, r_top, r_hem, jag=0.0, rings=5, seed=0, y_off=0.0):
    pts = [V((0, y_off * s, (z_top + (z_hem - z_top) * k / (rings - 1)) * s)) for k in range(rings)]
    radii = [tuple(((a + (b - a) * (k / (rings - 1)) ** 0.8) * s) for a, b in zip(r_top, r_hem)) for k in range(rings)]
    mb = B.part(["hips", "thigh.L", "thigh.R", "shin.L", "shin.R"], 2.5)
    loft(mb, pts, radii, mat, segs=16, cap0=False, cap1=False, jag=jag * s, seed=seed)


def band(B, s, z, rx, ry, mat, h=0.05, bones=("hips", "spine"), y=0.0):
    mb = B.part(list(bones), 3)
    loft(mb, [V((0, y * s, (z - h / 2) * s)), V((0, y * s, (z + h / 2) * s))], [(rx * s, ry * s)] * 2, mat, segs=16,
         cap0=False, cap1=False)


def arms(B, j, s, sleeve, hand_mat, r=1.0, forearm_mat=None, cuff=None, fist=True):
    for X in ("L", "R"):
        a, e, w, he = j[f"arm.{X}"], j[f"elbow.{X}"], j[f"wrist.{X}"], j[f"hand_end.{X}"]
        mb = B.part([f"shoulder.{X}", f"upper_arm.{X}", f"forearm.{X}"], 5)
        loft(mb, [a + V((0, 0, 0.02 * s)), a.lerp(e, 0.5), e], [0.056 * s * r, 0.05 * s * r, 0.045 * s * r], sleeve, segs=10)
        mb.sphere(a + V((-0.012 * s if X == "L" else 0.012 * s, 0, 0.0)), 0.054 * s * r, sleeve, segs=10, rings=6)
        mb = B.part([f"upper_arm.{X}", f"forearm.{X}", f"hand.{X}"], 5)
        loft(mb, [e, e.lerp(w, 0.45), w], [0.046 * s * r, 0.044 * s * r, 0.034 * s * r], forearm_mat or sleeve, segs=10)
        if cuff:
            loft(mb, [e.lerp(w, 0.62), w + (w - e).normalized() * 0.01 * s], [0.05 * s * r, 0.047 * s * r], cuff, segs=10)
        mb = B.part([f"hand.{X}"], 5)
        c = w.lerp(he, 0.45)
        sx = 1 if X == "L" else -1
        mb.sphere(c, (0.032 * s * r, 0.045 * s * r, 0.055 * s * r), hand_mat, segs=10, rings=6)
        loft(mb, [c + V((sx * -0.02 * s, -0.03 * s, 0.02 * s)), c + V((sx * -0.03 * s, -0.05 * s, -0.01 * s))],
             [0.013 * s * r, 0.011 * s * r], hand_mat, segs=6)


def head(B, j, s, skin, hair=None, beard=None, hair_style="short", scale=1.0, brows=True, nose=1.0, ears=True):
    hs = s * scale
    hc = j["head"] + V((0, -0.012 * s, 0.1 * hs))
    mb = B.part(["chest", "neck", "head"], 5)
    loft(mb, [j["neck"] - V((0, 0, 0.02 * s)), j["head"] + V((0, 0, 0.03 * s))], [0.055 * s, 0.05 * s], skin, segs=10)
    mb = B.part(["head"], 4)
    mb.sphere(hc, (0.086 * hs, 0.098 * hs, 0.112 * hs), skin, segs=14, rings=10)
    mb.sphere(hc + V((0, -0.035 * hs, -0.06 * hs)), (0.062 * hs, 0.07 * hs, 0.05 * hs), skin, segs=10, rings=6)  # jaw
    for sx in (-1, 1):
        mb.sphere(hc + V((sx * 0.032 * hs, -0.079 * hs, 0.018 * hs)), (0.011 * hs, 0.007 * hs, 0.0065 * hs), "M_EyeWhite", segs=8, rings=5)
        mb.sphere(hc + V((sx * 0.032 * hs, -0.0845 * hs, 0.018 * hs)), 0.0045 * hs, "M_EyeDark", segs=6, rings=4)
        if brows:
            bx0 = hc.x + sx * 0.013 * hs
            bx1 = hc.x + sx * 0.052 * hs
            mb.box(V((min(bx0, bx1), hc.y - 0.094 * hs, hc.z + 0.03 * hs)), V((max(bx0, bx1), hc.y - 0.08 * hs, hc.z + 0.043 * hs)),
                   hair or "M_HairDark")
        if ears:
            mb.sphere(hc + V((sx * 0.085 * hs, 0.0, 0.0)), (0.014 * hs, 0.026 * hs, 0.034 * hs), skin, segs=8, rings=5)
    loft(mb, [hc + V((0, -0.092 * hs, 0.02 * hs)), hc + V((0, -0.118 * hs * nose, -0.022 * hs))],
         [0.011 * hs, 0.019 * hs * nose], skin, segs=8)
    mb.box(hc + V((-0.022 * hs, -0.094 * hs, -0.052 * hs)), hc + V((0.022 * hs, -0.084 * hs, -0.044 * hs)), "M_Lips")
    if hair:
        if hair_style == "short":
            keep = lambda x, y, z: not (z > 0.15 or (y > -0.2 and z > -0.55))  # noqa: E731
        elif hair_style == "long":
            keep = lambda x, y, z: not (z > 0.1 or (y > -0.25 and z > -0.95))  # noqa: E731
        else:  # messy / child
            keep = lambda x, y, z: not (z > 0.25 or (y > -0.1 and z > -0.45))  # noqa: E731
        mb.sphere(hc + V((0, 0.004 * hs, 0.008 * hs)), (0.095 * hs, 0.106 * hs, 0.121 * hs), hair, segs=14, rings=10,
                  skip=keep, noise=0.04, seed=3)
        if hair_style == "long":
            loft(mb, [hc + V((0, 0.03 * hs, -0.05 * hs)), hc + V((0, 0.04 * hs, -0.17 * hs))],
                 [(0.09 * hs, 0.07 * hs), (0.08 * hs, 0.04 * hs)], hair, segs=10, cap0=False)
    if beard:
        mb.sphere(hc + V((0, -0.018 * hs, -0.045 * hs)), (0.083 * hs, 0.09 * hs, 0.088 * hs), beard, segs=14, rings=8,
                  skip=lambda x, y, z: not (y < 0.15 and z < -0.05 and not (abs(x) < 0.35 and z > -0.55 and y < -0.6)),
                  noise=0.05, seed=5)
    return hc


def hood(B, hc, s, mat, scale=1.0, drape=True):
    hs = s * scale
    mb = B.part(["head", "neck"], 4)
    mb.sphere(hc + V((0, 0.012 * hs, 0.012 * hs)), (0.112 * hs, 0.124 * hs, 0.138 * hs), mat, segs=16, rings=10,
              skip=lambda x, y, z: (y < -0.3 and -0.75 < z < 0.75 and abs(x) < 0.8) or z < -0.8, noise=0.03, seed=9)
    if drape:
        mb = B.part(["neck", "chest", "head"], 3)
        loft(mb, [hc + V((0, 0.03 * hs, -0.08 * hs)), hc + V((0, 0.03 * hs, -0.2 * hs)), hc + V((0, 0.02 * hs, -0.3 * hs))],
             [(0.12 * hs, 0.1 * hs), (0.17 * hs, 0.13 * hs), (0.23 * hs, 0.15 * hs)], mat, segs=14, cap0=False, cap1=False)


def cape(B, s, mat, z_top, z_bot, r_top, r_bot, jag=0.04, seed=1):
    mb = B.part(["chest", "neck", "upper_arm.L", "upper_arm.R", "spine"], 3)
    loft(mb, [V((0, 0.005 * s, z_top * s)), V((0, 0.0, (z_top + z_bot) / 2 * s)), V((0, 0, z_bot * s))],
         [(r_top[0] * s, r_top[1] * s), ((r_top[0] + r_bot[0]) / 2 * s, (r_top[1] + r_bot[1]) / 2 * s), (r_bot[0] * s, r_bot[1] * s)],
         mat, segs=16, cap0=False, cap1=False, jag=jag * s, seed=seed)


def decal(B, s, z0, z1, w, y, mat, bones=("spine", "chest"), back=False):
    mb = B.part(list(bones), 3)
    ys = y * s
    if not back:
        mb.face([(-w * s, ys, z0 * s), (w * s, ys, z0 * s), (w * s, ys, z1 * s), (-w * s, ys, z1 * s)], mat, uv="fit")
    else:
        mb.face([(w * s, ys, z0 * s), (-w * s, ys, z0 * s), (-w * s, ys, z1 * s), (w * s, ys, z1 * s)], mat, uv="fit")


# ============================================================================= held items (built in posed space)
def sword_mesh(mb, length=0.95, blade="M_Steel", grip="M_LeatherC", guard="M_Iron", notch=False):
    """Sword along local -Z from the grip centre (hilt up at +Z)."""
    L = length
    pts = [(-0.024, 0.0), (0.024, 0.0), (0.02, -L * 0.85), (0.0, -L), (-0.02, -L * 0.85)]
    if notch:
        pts = [(-0.026, 0.0), (0.026, 0.0), (0.022, -L * 0.3), (0.012, -L * 0.33), (0.022, -L * 0.36), (0.02, -L * 0.85),
               (0.0, -L), (-0.02, -L * 0.85), (-0.024, -L * 0.6), (-0.012, -L * 0.63), (-0.024, -L * 0.66)]
    mb.prism([(x, z - 0.07) for x, z in pts], -0.006, 0.006, blade)
    mb.box((-0.11, -0.022, -0.09), (0.11, 0.022, -0.06), guard)
    mb.rod((0, 0, -0.06), (0, 0, 0.1), 0.017, grip, segs=6)
    mb.sphere((0, 0, 0.12), 0.03, guard, segs=8, rings=5)


def held(B, arm, bone, name, build_fn, grip_world, axis_rot):
    """Build an item in posed world space around `grip_world` with rotation matrix `axis_rot`, skin to `bone`."""
    mb = B.separate(name, [bone], 6)
    mb.push(C_rest(arm, bone) @ Matrix.Translation(grip_world) @ axis_rot)
    build_fn(mb)
    mb.pop()
    return mb


def C_rest(arm, bone):
    return posed_to_rest(arm, bone)


def grip_of(arm, X):
    h, t = posed_points(arm, f"hand.{X}")
    return h.lerp(t, 0.5)


def rot_to(direction, roll_hint=V((1, 0, 0))):
    """Rotation matrix taking local -Z to `direction` (so items built hanging along -Z point there)."""
    d = V(direction).normalized()
    q = (-d).to_track_quat("Z", "Y")
    return q.to_matrix().to_4x4()


# ============================================================================= characters
def base_human_actions(arm, base, H, extra=None, attack=None, gait=None, heavy=0.0, flail=True, girth=1.0):
    spec = {"scale": H / 1.8, "girth": girth, "heavy": heavy, "flail": flail, "gait": gait or {}}
    if attack:
        spec["attack"] = attack
    if extra:
        spec["extra"] = extra
    return C.human_actions(arm, base, spec)


def sword_attack(base, T=0.9):
    wind = add(base, {"upper_arm.R": (-130, 30, 0), "forearm.R": (-40, 0, 0), "hand.R": (-20, 0, 0), "chest": (0, 0, -25),
                      "spine": (-5, 0, 0), "hips": (0, 0, -10), "thigh.R": (10, 0, 0), "thigh.L": (-10, 0, 0)})
    strike = add(base, {"upper_arm.R": (-55, -25, 0), "forearm.R": (25, 0, 0), "hand.R": (25, 0, 0), "chest": (10, 0, 30),
                        "spine": (12, 0, 0), "hips": (0, 0, 10), "thigh.L": (-30, 0, 0), "shin.L": (25, 0, 0),
                        "thigh.R": (15, 0, 0), "_loc": {"hips": (0, -0.08, -0.05)}})
    follow = add(base, {"upper_arm.R": (-25, -30, 0), "forearm.R": (10, 0, 0), "hand.R": (15, 0, 0), "chest": (8, 0, 35),
                        "spine": (10, 0, 0), "thigh.L": (-25, 0, 0), "shin.L": (20, 0, 0), "_loc": {"hips": (0, -0.06, -0.04)}})
    return [(0, base), (0.3, wind), (0.45, strike), (0.62, follow), (1, base)], T


# ----------------------------------------------------------------------------- hero detail helpers (run 2)
def belt_ring(B, s, z, rx, ry, mat, h=0.05, tilt=0.0, bones=("hips", "spine"), y=0.0, segs=18):
    """Belt ring; `tilt` lowers the +X (character's left) side by tilt*x metres per metre (a hanging sword belt)."""
    mb = B.part(list(bones), 3)
    top, bot = [], []
    for k in range(segs):
        a = 2 * PI * k / segs
        x, yy = rx * s * math.cos(a), ry * s * math.sin(a) + y * s
        zz = z * s - tilt * x
        bot.append(mb._v((x, yy, zz - h * s / 2)))
        top.append(mb._v((x, yy, zz + h * s / 2)))
    for k in range(segs):
        q = (k + 1) % segs
        mb._quad_idx([bot[k], bot[q], top[q], top[k]], mat, "world", True, False)
    return mb


def skirt_panels(B, s, mat, z_top, z_hem, r_top, r_hem, slits=(), jag=0.0, seed=0, rings=6, segs=28, bones=None,
                 inner=None, thick=0.008):
    """Two-sided skirt (outer + inner shell) open at the given slits [(angle_deg, half_width_deg)], jagged hem.
    Angle 0 = character's left (+X), -90 = front (-Y)."""
    rnd = random.Random(seed)
    mb = B.part(bones or ["hips", "thigh.L", "thigh.R", "shin.L", "shin.R"], 2.5)

    def cut(a_deg):
        for c, w in slits:
            d = (a_deg - c + 180) % 360 - 180
            if abs(d) < w:
                return True
        return False
    hem_off = [rnd.uniform(-jag, jag * 0.35) for _ in range(segs + 1)]
    hem_off[-1] = hem_off[0]
    for layer in (0, 1):
        grid = []
        for r in range(rings):
            t = r / (rings - 1)
            z = (z_top + (z_hem - z_top) * t) * s
            rx = (r_top[0] + (r_hem[0] - r_top[0]) * t ** 0.8) * s - layer * thick
            ry = (r_top[1] + (r_hem[1] - r_top[1]) * t ** 0.8) * s - layer * thick
            row = []
            for k in range(segs + 1):
                a = 2 * PI * k / segs
                zz = z + (hem_off[k] * s if r == rings - 1 else 0.0)
                row.append(mb._v((rx * math.cos(a), ry * math.sin(a), zz)))
            grid.append(row)
        for r in range(rings - 1):
            for k in range(segs):
                am = math.degrees(2 * PI * (k + 0.5) / segs)
                if cut(am):
                    continue
                q = [grid[r][k], grid[r + 1][k], grid[r + 1][k + 1], grid[r][k + 1]]
                if layer:
                    q = list(reversed(q))
                mb._quad_idx(q, inner if (inner and layer) else mat, "world", True, False)
    return mb


def hero_head(B, j, s):
    """Vaclav's head after concept/characters/vaclav.png: lean face, cheekbones, strong brow, short dark beard and
    moustache, loose shoulder-length dark hair."""
    hc = j["head"] + V((0, -0.012 * s, 0.1 * s))
    mb = B.part(["chest", "neck", "head"], 5)
    loft(mb, [j["neck"] - V((0, 0, 0.03 * s)), j["head"] + V((0, 0, 0.03 * s))], [0.058 * s, 0.052 * s], "M_Skin", segs=12)
    mb = B.part(["head"], 4)
    mb.sphere(hc + V((0, 0.004, 0.006)), (0.084 * s, 0.097 * s, 0.11 * s), "M_Skin", segs=18, rings=12)        # cranium
    mb.sphere(hc + V((0, -0.03 * s, -0.058 * s)), (0.06 * s, 0.072 * s, 0.056 * s), "M_Skin", segs=14, rings=8)  # jaw
    mb.sphere(hc + V((0, -0.058 * s, -0.098 * s)), (0.026 * s, 0.03 * s, 0.022 * s), "M_Skin", segs=10, rings=6)  # chin
    for sx in (-1, 1):
        mb.sphere(hc + V((sx * 0.045 * s, -0.06 * s, -0.004 * s)), (0.021 * s, 0.022 * s, 0.017 * s), "M_Skin", segs=10, rings=6)
        mb.sphere(hc + V((sx * 0.0315 * s, -0.08 * s, 0.017 * s)), (0.0125 * s, 0.007 * s, 0.0068 * s), "M_EyeWhite", segs=10, rings=6)
        mb.sphere(hc + V((sx * 0.0315 * s, -0.0858 * s, 0.017 * s)), (0.0055 * s, 0.003 * s, 0.0055 * s), "M_EyeDark", segs=8, rings=5)
        mb.sphere(hc + V((sx * 0.0315 * s, -0.0805 * s, 0.0245 * s)), (0.0135 * s, 0.0075 * s, 0.004 * s), "M_Skin", segs=8, rings=4)
        loft(mb, [hc + V((sx * 0.012 * s, -0.0905 * s, 0.031 * s)), hc + V((sx * 0.033 * s, -0.093 * s, 0.036 * s)),
                  hc + V((sx * 0.054 * s, -0.082 * s, 0.035 * s))], [0.0055 * s, 0.0065 * s, 0.004 * s], "M_HairDark", segs=6)
        mb.sphere(hc + V((sx * 0.084 * s, 0.002, -0.004 * s)), (0.012 * s, 0.022 * s, 0.03 * s), "M_Skin", segs=8, rings=5)
    loft(mb, [hc + V((0, -0.083 * s, 0.03 * s)), hc + V((0, -0.093 * s, 0.03 * s))], [0.028 * s, 0.03 * s], "M_Skin", segs=10)
    loft(mb, [hc + V((0, -0.093 * s, 0.022 * s)), hc + V((0, -0.111 * s, -0.012 * s)), hc + V((0, -0.115 * s, -0.026 * s))],
         [0.009 * s, 0.013 * s, 0.014 * s], "M_Skin", segs=8)
    mb.sphere(hc + V((0, -0.108 * s, -0.03 * s)), (0.017 * s, 0.013 * s, 0.011 * s), "M_Skin", segs=8, rings=5)
    mb.box(hc + V((-0.019 * s, -0.096 * s, -0.056 * s)), hc + V((0.019 * s, -0.087 * s, -0.05 * s)), "M_Lips")

    def beard_keep(x, y, z):
        jaw = z < -0.18 and y < 0.45 and (z < -0.5 or abs(x) > 0.55 or y > -0.3)
        mouth = abs(x) < 0.3 and -0.62 < z < -0.18 and y < -0.55
        return not (jaw and not mouth)
    mb.sphere(hc + V((0, -0.024 * s, -0.05 * s)), (0.066 * s, 0.081 * s, 0.072 * s), "M_HairDark", segs=40, rings=22,
              skip=beard_keep, noise=0.015, seed=7)
    mb.sphere(hc + V((0, -0.06 * s, -0.1 * s)), (0.031 * s, 0.033 * s, 0.026 * s), "M_HairDark", segs=12, rings=8, noise=0.06, seed=8)
    for sx in (-1, 1):
        loft(mb, [hc + V((0, -0.101 * s, -0.041 * s)), hc + V((sx * 0.018 * s, -0.098 * s, -0.045 * s)),
                  hc + V((sx * 0.027 * s, -0.09 * s, -0.062 * s))], [0.006 * s, 0.006 * s, 0.004 * s], "M_HairDark", segs=6)
    mb.sphere(hc + V((0, 0.008 * s, 0.012 * s)), (0.093 * s, 0.106 * s, 0.12 * s), "M_HairDark", segs=18, rings=12,
              skip=lambda x, y, z: not (z > 0.55 or (y > -0.3 and z > -0.45) or (y > 0.15 and z > -0.98)), noise=0.04, seed=11)
    rnd = random.Random(23)
    for k in range(16):
        a = -PI * 0.95 + k * (PI * 1.9 / 15)
        r0 = V((math.sin(a) * 0.08 * s, -math.cos(a) * 0.09 * s, 0.07 * s)) + hc
        out = V((math.sin(a), -math.cos(a), 0)).normalized()
        front = abs(a) < 0.75
        if front:
            r0 = r0 + V((0, 0.012 * s, 0.035 * s))
        L = (0.045 if front else 0.13 + 0.03 * rnd.random()) * s
        if abs(a) < 1.5 and not front:
            L *= 0.6                                              # shorter over the temples, ears stay free
        r1 = r0 + out * 0.03 * s + V((0, 0, -L * 0.45))
        r2 = r0 + out * (0.038 if not front else 0.025) * s + V((0, 0.0, -L))
        if front:
            r2 = r2 + V((0.04 * s * (1 if a > 0 else -1), 0.0, 0.0))
        loft(mb, [r0, r1, r2], [0.024 * s, 0.019 * s, 0.005 * s], "M_HairDark", segs=6, noise=0.1, seed=k)
    return hc


def hero_hood(B, hc, s):
    """Lowered hood: thick cowl bunched around the neck and spread over the shoulders + the hood bag at the back."""
    mb = B.part(["neck", "chest", "head", "shoulder.L", "shoulder.R"], 3)
    loft(mb, [V((0, 0.012 * s, 1.6 * s)), V((0, 0.01 * s, 1.53 * s)), V((0, 0.01 * s, 1.45 * s)), V((0, 0.01 * s, 1.36 * s))],
         [(0.072 * s, 0.07 * s), (0.118 * s, 0.1 * s), (0.205 * s, 0.145 * s), (0.25 * s, 0.17 * s)], "M_RobeBrown", segs=18,
         cap0=False, cap1=False, noise=0.05, seed=31)
    loft(mb, [V((0, 0.0, 1.6 * s)), V((0, -0.005 * s, 1.53 * s))], [(0.082 * s, 0.08 * s), (0.125 * s, 0.11 * s)],
         "M_RobeBrown", segs=18, cap0=False, cap1=False, noise=0.08, seed=32)
    mb = B.part(["chest", "neck"], 3)
    mb.sphere(V((0, 0.13 * s, 1.47 * s)), (0.12 * s, 0.07 * s, 0.11 * s), "M_RobeBrown", segs=12, rings=8, noise=0.08, seed=33)
    mb.sphere(V((0, 0.16 * s, 1.36 * s)), (0.09 * s, 0.05 * s, 0.08 * s), "M_RobeBrown", segs=10, rings=6, noise=0.1, seed=34)
    mb = B.part(["neck", "chest"], 3)
    loft(mb, [V((0, -0.002 * s, 1.53 * s)), V((0, -0.002 * s, 1.47 * s))], [(0.07 * s, 0.068 * s), (0.1 * s, 0.09 * s)],
         "M_Chainmail", segs=16, cap0=False, cap1=False)


def longsword(mb, length=0.98):
    """Longsword along local -Z from the grip centre: fullered blade, drooping guard, wrapped grip, wheel pommel."""
    L = length
    blade = [(-0.026, 0.0), (0.026, 0.0), (0.021, -L * 0.8), (0.0, -L), (-0.021, -L * 0.8)]
    mb.prism([(x, z - 0.075) for x, z in blade], -0.0055, 0.0055, "M_Steel")
    for yy in (-0.0062, 0.0062):
        f = [(-0.0065, -0.09), (0.0065, -0.09), (0.004, -L * 0.62), (-0.004, -L * 0.62)]
        mb.face([(x, yy, z) for x, z in (f if yy > 0 else list(reversed(f)))], "M_Iron")
    mb.box((-0.03, -0.012, -0.085), (0.03, 0.012, -0.065), "M_Iron")
    for sx in (-1, 1):
        mb.rod((0, 0, -0.075), (sx * 0.12, 0, -0.088), 0.012, "M_Iron", segs=6, r1=0.009)
        mb.sphere((sx * 0.122, 0, -0.089), 0.014, "M_Iron", segs=6, rings=4)
    mb.rod((0, 0, -0.065), (0, 0, 0.1), 0.0165, "M_LeatherDark", segs=8)
    for k in range(5):
        z = -0.05 + k * 0.032
        mb.rod((0, 0, z), (0, 0, z + 0.012), 0.0185, "M_LeatherC", segs=8)
    with mb.at((0, 0, 0.125), rot_x=PI / 2):
        mb.cyl((0, 0, -0.012), 0.034, 0.024, "M_Iron", segs=14)
    mb.sphere((0, 0, 0.125), (0.014, 0.02, 0.014), "M_Brass", segs=8, rings=4)


def round_shield(mb, r=0.36):
    mb.cyl((0, 0, -0.016), r, 0.032, "M_WoodDark", segs=32, cap=True, smooth=False)
    mb.face([(r * 0.985 * math.cos(2 * PI * k / 32), r * 0.985 * math.sin(2 * PI * k / 32), 0.0175) for k in range(32)], "M_Shield", uv="fit")
    mb.torus(r, 0.017, "M_Iron", segs=32, tsegs=6)
    for k in range(16):
        a = 2 * PI * (k + 0.5) / 16
        mb.sphere((r * 0.93 * math.cos(a), r * 0.93 * math.sin(a), 0.02), 0.009, "M_Iron", segs=6, rings=3)
    mb.sphere((0, 0, 0.018), (0.085, 0.085, 0.06), "M_Steel", segs=16, rings=6, z_cut=0.016)
    mb.torus(0.088, 0.008, "M_Iron", segs=16, tsegs=4)
    mb.rod((-0.1, 0, -0.03), (0.1, 0, -0.03), 0.014, "M_LeatherC", segs=6)
    mb.rod((0, -0.12, -0.03), (0, 0.12, -0.03), 0.012, "M_LeatherC", segs=6)


def build_vaclav():
    H = 1.8
    s = H / 1.8
    root, col, arm, j = start("vaclav", H, width=1.05)
    base = {"upper_arm.R": (-8, 4, 0), "forearm.R": (-38, 0, 0), "hand.R": (5, 0, 0),
            "upper_arm.L": (-18, -8, 0), "forearm.L": (-55, 0, -20)}
    set_base(arm, base)
    B = C.Body("vaclav", arm, col)
    held(B, arm, "hand.R", "WEAPON_sword", lambda mb: longsword(mb, 0.98), grip_of(arm, "R"), rot_to((-0.05, -0.55, -0.83)))
    fh, ft = posed_points(arm, "forearm.L")
    sc = fh.lerp(ft, 0.55) + V((0.1, -0.035, 0))
    mb = B.separate("WEAPON_shield", ["forearm.L"], 6)
    mb.push(posed_to_rest(arm, "forearm.L") @ Matrix.Translation(sc) @ (V((0.75, -0.66, 0.0))).to_track_quat("Z", "Y").to_matrix().to_4x4())
    round_shield(mb)
    mb.pop()
    # legs: dark wool hose, tall riding boots with a turned-down cuff
    legs(B, j, s, "M_RobeDark", boots="M_LeatherC", boot_top=0.04)
    for k, X in enumerate(("L", "R")):
        knee, ank = j[f"knee.{X}"], j[f"ankle.{X}"]
        mb = B.part([f"thigh.{X}", f"shin.{X}"], 5)
        loft(mb, [knee.lerp(ank, -0.04), knee.lerp(ank, 0.12)], [(0.07 * s, 0.069 * s), (0.068 * s, 0.067 * s)], "M_LeatherDark",
             segs=12, cap0=False, cap1=False, noise=0.05, seed=40 + k)
    # mail hauberk, padded tunic hem below it
    torso(B, s, "M_Chainmail", w=1.06)
    skirt_panels(B, s, "M_Chainmail", 1.02, 0.5, (0.17, 0.12), (0.205, 0.165), slits=((-90, 9), (90, 9)), jag=0.015, seed=2)
    skirt_panels(B, s, "M_WoolBrown", 0.62, 0.42, (0.198, 0.158), (0.215, 0.175), slits=((-90, 7),), jag=0.03, seed=4)
    # surcoat: sleeveless, split front and back, ragged hem
    torso(B, s, "M_ClothRed", w=1.06, grow=0.013, z_from=1.0, z_to=1.46, cap=False)
    skirt_panels(B, s, "M_ClothRed", 1.02, 0.47, (0.185, 0.135), (0.245, 0.2), slits=((-90, 14), (90, 12)), jag=0.07, seed=3,
                 inner="M_WoolBrown")
    decal(B, s, 1.1, 1.43, 0.12, -0.144, "M_Tabard")
    decal(B, s, 1.1, 1.43, 0.12, 0.144, "M_Tabard", back=True)
    # belts: broad waist belt with brass buckle, sword belt slung low to the left hip, pouch
    belt_ring(B, s, 1.045, 0.186, 0.137, "M_LeatherC", 0.055)
    mb = B.part(["hips", "spine"], 3)
    mb.box(V((-0.032 * s, -0.152 * s, 1.02 * s)), V((0.032 * s, -0.138 * s, 1.07 * s)), "M_Brass")
    belt_ring(B, s, 0.98, 0.19, 0.145, "M_LeatherDark", 0.04, tilt=0.25)
    mb = B.part(["hips", "thigh.R"], 4)
    mb.sphere(V((-0.17 * s, -0.06 * s, 0.94 * s)), (0.035 * s, 0.05 * s, 0.06 * s), "M_LeatherC", segs=10, rings=6, noise=0.06, seed=5)
    # arms: mail half-sleeves to the elbow over padded sleeves, long leather gauntlets
    arms(B, j, s, "M_Chainmail", "M_LeatherC", r=1.08, forearm_mat="M_WoolBrown", cuff="M_LeatherC")
    for X in ("L", "R"):
        a, e, w = j[f"arm.{X}"], j[f"elbow.{X}"], j[f"wrist.{X}"]
        mb = B.part([f"upper_arm.{X}", f"forearm.{X}"], 5)
        loft(mb, [e + (a - e).normalized() * 0.03 * s, e + (w - e).normalized() * 0.03 * s], [0.06 * s, 0.056 * s], "M_Chainmail",
             segs=12, cap0=False, cap1=False, jag=0.012)
        mb = B.part([f"forearm.{X}", f"hand.{X}"], 5)
        loft(mb, [e.lerp(w, 0.5), w + (w - e).normalized() * 0.005 * s], [0.052 * s, 0.06 * s], "M_LeatherC",
             segs=12, cap0=False, cap1=False)
    hc = hero_head(B, j, s)
    hero_hood(B, hc, s)
    # scabbard on the left hip, hanging from the sword belt
    mb = B.part(["hips", "thigh.L"], 4)
    loft(mb, [V((0.2, 0.03, 0.96)), V((0.235, 0.09, 0.62)), V((0.25, 0.13, 0.42))], [0.032, 0.026, 0.02], "M_LeatherDark", segs=8)
    mb.box(V((0.19, 0.0, 0.93)), V((0.215, 0.06, 0.96)), "M_Iron")
    B.build()
    crouch = add(base, {"thigh.L": (-45, 0, 0), "thigh.R": (-40, 0, 0), "shin.L": (80, 0, 0), "shin.R": (75, 0, 0),
                        "foot.L": (-30, 0, 0), "foot.R": (-30, 0, 0), "spine": (18, 0, 0), "upper_arm.R": (-30, 10, 0),
                        "_loc": {"hips": (0, 0, -0.22)}})
    air = add(base, {"thigh.L": (-55, 0, 0), "thigh.R": (-20, 0, 0), "shin.L": (70, 0, 0), "shin.R": (45, 0, 0),
                     "spine": (5, 0, 0), "upper_arm.R": (-40, 20, 0), "upper_arm.L": (-40, -25, 0), "_loc": {"hips": (0, 0, 0.02)}})
    tuck = add(base, {"thigh.L": (-80, 0, 0), "thigh.R": (-75, 0, 0), "shin.L": (110, 0, 0), "shin.R": (105, 0, 0),
                      "spine": (40, 0, 0), "chest": (15, 0, 0), "head": (25, 0, 0), "upper_arm.R": (-60, 15, 0),
                      "upper_arm.L": (-70, -15, 0), "forearm.L": (-30, 0, -40), "_loc": {"hips": (0, -0.1, -0.45)}})
    lunge = add(base, {"thigh.L": (-50, 0, 0), "shin.L": (60, 0, 0), "thigh.R": (25, 0, 0), "shin.R": (20, 0, 0),
                       "spine": (30, 0, 0), "chest": (10, 0, 0), "upper_arm.L": (-60, -10, 0), "forearm.L": (-30, 0, -30),
                       "_loc": {"hips": (0, -0.12, -0.25)}})
    bwind = add(base, {"upper_arm.R": (-95, -50, 0), "forearm.R": (-70, 0, 0), "hand.R": (0, 0, 40), "chest": (0, 0, 35),
                       "spine": (-4, 0, 0), "hips": (0, 0, 12), "thigh.L": (8, 0, 0), "thigh.R": (-12, 0, 0)})
    bstrike = add(base, {"upper_arm.R": (-75, 45, 0), "forearm.R": (-10, 0, 0), "hand.R": (0, 0, -30), "chest": (8, 0, -35),
                         "spine": (10, 0, 0), "hips": (0, 0, -12), "thigh.R": (-30, 0, 0), "shin.R": (25, 0, 0),
                         "_loc": {"hips": (0, -0.06, -0.05)}})
    acts = base_human_actions(arm, base, H, attack=sword_attack(base), extra={
        "block": (lambda t: add(base, {"upper_arm.L": (-55, -15, 0), "forearm.L": (-35, 0, -35), "spine": (8 + math.sin(2 * PI * t), 0, 0),
                                       "thigh.L": (-10, 0, 0), "thigh.R": (-6, 0, 0), "shin.L": (16, 0, 0), "shin.R": (12, 0, 0),
                                       "upper_arm.R": (-10, 12, 0), "_loc": {"hips": (0, 0, -0.04)}}), 1.0),
        "throw": (seq([
            (0, base),
            (0.2, add(base, {"upper_arm.L": (-75, 8, 0), "upper_arm.R": (-75, -8, 0), "forearm.L": (20, 0, 20), "forearm.R": (15, 0, 0),
                             "spine": (25, 0, 0), "thigh.L": (-25, 0, 0), "thigh.R": (-20, 0, 0), "shin.L": (40, 0, 0), "shin.R": (35, 0, 0),
                             "_loc": {"hips": (0, 0, -0.12)}})),
            (0.45, add(base, {"upper_arm.L": (-150, 10, 0), "upper_arm.R": (-150, -10, 0), "forearm.L": (25, 0, 20), "forearm.R": (8, 0, 0),
                              "spine": (-15, 0, 0), "chest": (-10, 0, 0), "head": (-10, 0, 0)})),
            (0.65, add(base, {"upper_arm.L": (-70, 0, 0), "upper_arm.R": (-70, 0, 0), "forearm.L": (50, 0, 20), "forearm.R": (38, 0, 0),
                              "spine": (30, 0, 0), "thigh.L": (-35, 0, 0), "shin.L": (25, 0, 0), "thigh.R": (20, 0, 0),
                              "_loc": {"hips": (0, -0.1, -0.05)}})),
            (1, base)]), 1.5),
        "jump": (seq([(0, base), (0.18, crouch), (0.4, air), (0.8, air), (1, base)]), 0.9),
        "dodge": (seq([(0, base), (0.2, lunge), (0.55, tuck), (0.85, lunge), (1, base)]), 0.5),
        "attack2": (seq([(0, base), (0.3, bwind), (0.5, bstrike), (0.7, add(bstrike, {"chest": (0, 0, -8)})), (1, base)]), 0.85),
    })
    INFO["vaclav"] = dict(h=H, acts=acts, desc="Рыцарь Вацлав из Вышеграда (по vaclav.png): худощавое лицо со скулами, короткая тёмная "
                          "борода и усы, тёмные волосы до плеч; опущенный капюшон-оплечье и кольчужный воротник; кольчуга с "
                          "полурукавами поверх стёганых рукавов; красное сюрко без рукавов с разрезами и рваным подолом, белый "
                          "коронованный лев с двумя хвостами; широкий ремень с латунной пряжкой и низкая перевязь меча; "
                          "длинные кожаные перчатки с раструбами; высокие сапоги с отворотами; круглый щит из досок со львом, "
                          "железным ободом, заклёпками и умбоном; длинный меч с долом и дисковым навершием.",
                          parts="WEAPON_sword (hand.R), WEAPON_shield (forearm.L); jump, dodge, attack2 (второй удар комбо)")
    return root


def build_alchemist():
    H = 1.8
    s = 1.0
    root, col, arm, j = start("alchemist", H, width=0.97)
    base = {"upper_arm.R": (-12, 6, 0), "forearm.R": (-62, 0, 0), "upper_arm.L": (-5, -4, 0), "forearm.L": (-25, 0, 0),
            "spine": (6, 0, 0), "head": (6, 0, 0)}
    set_base(arm, base)
    B = C.Body("alchemist", arm, col)

    def staff(mb):
        mb.rod((0, 0, -1.05), (0, 0, 0.75), 0.022, "M_Timber", segs=8)
        for z in (-0.9, -0.5, 0.0, 0.35, 0.55):
            mb.cyl((0, 0, z), 0.03, 0.04, "M_Brass", segs=8)
        mb.cyl((0, 0, 0.7), 0.04, 0.08, "M_Brass", segs=8, r_top=0.06)
        mb.sphere((0, 0, 0.9), 0.1, "M_VialGreen", segs=12, rings=8)
        for k in range(4):
            a = 2 * PI * k / 4
            mb.rod((0.06 * math.cos(a), 0.06 * math.sin(a), 0.76), (0.105 * math.cos(a), 0.105 * math.sin(a), 0.9), 0.008, "M_Brass", segs=4)
            mb.rod((0.105 * math.cos(a), 0.105 * math.sin(a), 0.9), (0.02 * math.cos(a), 0.02 * math.sin(a), 1.02), 0.008, "M_Brass", segs=4)
        mb.sphere((0, 0, 1.04), 0.03, "M_Brass", segs=8, rings=5)
    g = grip_of(arm, "R")
    mb = B.separate("WEAPON_staff", ["hand.R"], 6)
    mb.push(posed_to_rest(arm, "hand.R") @ Matrix.Translation(g))
    staff(mb)
    mb.pop()
    legs(B, j, s, "M_WoolBrown", boots="M_LeatherDark", boot_top=0.7)
    torso(B, s, "M_RobeDark", w=1.02)
    skirt(B, s, "M_RobeDark", 1.04, 0.07, (0.175, 0.125), (0.27, 0.24), jag=0.08, rings=7, seed=4)
    arms(B, j, s, "M_RobeDark", "M_LeatherDark", r=1.15)
    cape(B, s, "M_MantleRed", 1.56, 1.2, (0.09, 0.08), (0.27, 0.19), jag=0.06, seed=5)
    hc = head(B, j, s, "M_SkinPale", hair="M_HairDark", beard="M_HairDark", hair_style="long", nose=1.15)
    hood(B, hc, s, "M_RobeDark")
    band(B, s, 1.04, 0.18, 0.13, "M_LeatherC", 0.06)
    band(B, s, 0.97, 0.2, 0.15, "M_LeatherC", 0.045)
    # belt vials and pouch
    mb = B.part(["hips", "spine"], 3)
    rnd = random.Random(7)
    for k, ang in enumerate((-0.9, -0.5, 0.45, 0.85, 1.3, -1.35)):
        x, y = 0.2 * math.sin(ang), -0.15 * math.cos(ang)
        mat = "M_VialGreen" if k % 2 == 0 else "M_VialPurple"
        mb.rod((x, y, 1.02), (x, y, 0.95), 0.008, "M_Brass", segs=4)
        mb.sphere((x, y, 0.91), (0.035, 0.035, 0.04), mat, segs=10, rings=6)
        mb.cyl((x, y, 0.945), 0.012, 0.03, "M_Brass", segs=6)
    mb.box((0.08, -0.2, 0.86), (0.22, -0.13, 1.0), "M_LeatherC")
    mb.box((0.08, -0.205, 0.94), (0.22, -0.135, 1.0), "M_LeatherDark")
    # amulet
    mb = B.part(["chest"], 3)
    with mb.at((0, -0.128, 1.31), rot_x=PI / 2):
        mb.cyl((0, 0, -0.004), 0.034, 0.008, "M_Brass", segs=12, smooth=False)
    B.build()
    attack = [(0, base),
              (0.35, add(base, {"upper_arm.L": (-160, -20, 0), "forearm.L": (-60, 0, 0), "chest": (0, 0, 22), "spine": (-6, 0, 0),
                                "thigh.L": (12, 0, 0), "thigh.R": (-10, 0, 0)})),
              (0.55, add(base, {"upper_arm.L": (-75, 5, 0), "forearm.L": (20, 0, 0), "chest": (6, 0, -20), "spine": (12, 0, 0),
                                "thigh.L": (-22, 0, 0), "shin.L": (15, 0, 0), "_loc": {"hips": (0, -0.05, -0.03)}})),
              (1, base)]
    acts = base_human_actions(arm, base, H, attack=(attack, 1.1), extra={
        "cast": (seq([(0, base), (0.4, add(base, {"upper_arm.R": (-60, 0, 0), "forearm.R": (-20, 0, 0), "upper_arm.L": (-90, -25, 0),
                                                  "forearm.L": (-30, 0, 0), "spine": (-8, 0, 0), "head": (-15, 0, 0)})),
                      (0.7, add(base, {"upper_arm.R": (-70, 0, 0), "forearm.R": (-15, 0, 0), "upper_arm.L": (-100, -30, 0),
                                       "forearm.L": (-20, 0, 0), "spine": (-10, 0, 0), "head": (-18, 0, 0)})), (1, base)]), 1.6)})
    INFO["alchemist"] = dict(h=H, acts=acts, desc="Злой алхимик: тёмная рваная ряса с прожогами, красно-бурый оплечник, капюшон, "
                             "бледное лицо с бородкой, пояса с флаконами (светятся зелёным и фиолетовым), сумка, амулет, "
                             "посох с латунным аппаратом и светящейся колбой.",
                             parts="WEAPON_staff (hand.R); attack = бросок зелья левой рукой, cast = колдовство посохом")
    return root


def build_golem():
    H = 4.0
    s = H / 1.8
    over = {"pelvis": (0, 0, 0.85), "spine": (0, 0, 0.98), "chest": (0, 0.02, 1.18), "neck": (0, -0.02, 1.47),
            "head": (0, -0.06, 1.5), "head_top": (0, -0.08, 1.7),
            "shoulder.L": (0.08, 0, 1.4), "arm.L": (0.33, 0.02, 1.38), "elbow.L": (0.41, 0.0, 1.06), "wrist.L": (0.44, -0.04, 0.76),
            "hand_end.L": (0.45, -0.06, 0.58),
            "hip.L": (0.14, 0, 0.83), "knee.L": (0.16, -0.02, 0.46), "ankle.L": (0.17, 0.02, 0.1), "toe.L": (0.17, -0.18, 0.03)}
    root, col, arm, j = start("golem", H, over)
    base = {"spine": (10, 0, 0), "chest": (6, 0, 0), "head": (-12, 0, 0), "upper_arm.L": (-6, -6, 0), "upper_arm.R": (-6, 6, 0),
            "forearm.L": (-15, 0, 0), "forearm.R": (-15, 0, 0), "thigh.L": (-6, 0, 0), "thigh.R": (-6, 0, 0),
            "shin.L": (10, 0, 0), "shin.R": (10, 0, 0), "foot.L": (-4, 0, 0), "foot.R": (-4, 0, 0)}
    set_base(arm, base)
    B = C.Body("golem", arm, col)
    M = "M_Clay"
    nz = 0.07
    for X in ("L", "R"):
        hip, knee, ank, toe = j[f"hip.{X}"], j[f"knee.{X}"], j[f"ankle.{X}"], j[f"toe.{X}"]
        mb = B.part(["hips", f"thigh.{X}", f"shin.{X}"], 5)
        loft(mb, [hip + V((0, 0, 0.1)), hip.lerp(knee, 0.5), knee, knee.lerp(ank, 0.5), ank + V((0, 0, 0.05))],
             [0.36, 0.33, 0.27, 0.3, 0.24], M, segs=12, noise=nz, seed=1 if X == "L" else 2)
        mb = B.part([f"shin.{X}", f"foot.{X}"], 5)
        heel = V((ank.x, ank.y + 0.12, 0.12))
        tip = V((toe.x, toe.y - 0.05, 0.1))
        loft(mb, [heel, heel.lerp(tip, 0.5) + V((0, 0, 0.04)), tip], [(0.22, 0.13), (0.25, 0.14), (0.2, 0.1)], M, segs=12,
             noise=nz, seed=3)
        a, e, w, he = j[f"arm.{X}"], j[f"elbow.{X}"], j[f"wrist.{X}"], j[f"hand_end.{X}"]
        mb = B.part([f"shoulder.{X}", f"upper_arm.{X}", f"forearm.{X}"], 5)
        loft(mb, [a + V((0, 0, 0.08)), a.lerp(e, 0.5), e], [0.3, 0.26, 0.23], M, segs=12, noise=nz, seed=4)
        mb.sphere(a + V((0, 0, 0.03)), 0.34, M, segs=12, rings=8, noise=nz, seed=5)
        mb = B.part([f"upper_arm.{X}", f"forearm.{X}", f"hand.{X}"], 5)
        loft(mb, [e, e.lerp(w, 0.5), w], [0.24, 0.27, 0.21], M, segs=12, noise=nz, seed=6)
        mb = B.part([f"hand.{X}"], 5)
        c = w.lerp(he, 0.5)
        mb.sphere(c, (0.17, 0.2, 0.24), M, segs=12, rings=8, noise=0.08, seed=7)
        sx = 1 if X == "L" else -1
        for k in range(3):
            loft(mb, [c + V((sx * 0.02 * k - 0.02 * sx, -0.12, -0.1)), c + V((sx * 0.03 * k - 0.03 * sx, -0.16, -0.3))],
                 [0.06, 0.05], M, segs=8)
    pts = [(0.82, 0.32, 0.25), (0.95, 0.36, 0.27), (1.05, 0.34, 0.27), (1.2, 0.42, 0.3), (1.33, 0.5, 0.33), (1.42, 0.46, 0.3),
           (1.5, 0.22, 0.2)]
    mb = B.part(["hips", "spine", "chest", "neck"], 3)
    loft(mb, [V((0, 0.02 * s, z * s)) for z, _, _ in pts], [(rx * s * 0.5, ry * s * 0.5) for _, rx, ry in pts], M, segs=16,
         noise=nz, seed=8)
    mb.sphere(V((0.0, -0.18, 1.3 * s)), (0.42, 0.25, 0.32), M, segs=12, rings=8, noise=nz, seed=9)  # pecs
    mb = B.part(["head", "neck"], 4)
    hc = j["head"] + V((0, -0.04, 0.2))
    mb.sphere(hc, (0.2, 0.23, 0.27), M, segs=14, rings=10, noise=0.03, seed=10)
    # glowing letters on the forehead: curved strip of quads facing forward
    n = 6
    for k in range(n):
        a0, a1 = -0.55 + 1.1 * k / n, -0.55 + 1.1 * (k + 1) / n
        q = []
        for a, z in ((a0, -0.02), (a1, -0.02), (a1, 0.13), (a0, 0.13)):
            q.append(hc + V((0.205 * math.sin(a), -0.235 * math.cos(a) - 0.012, z)))
        mb.face(q, "M_GolemLetters", uv="world")
    B.build()
    # UV for the letter strip: map it as one decal (fit across all strip quads)
    body = bpy.data.objects["golem_body"]
    me = body.data
    uv = me.uv_layers.active.data
    idx = [i for i, m in enumerate(me.materials) if m.name == "M_GolemLetters"][0]
    polys = [p for p in me.polygons if p.material_index == idx]
    xs = [me.vertices[me.loops[li].vertex_index].co.x for p in polys for li in p.loop_indices]
    zs = [me.vertices[me.loops[li].vertex_index].co.z for p in polys for li in p.loop_indices]
    for p in polys:
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv[li].uv = ((co.x - min(xs)) / (max(xs) - min(xs)), (co.z - min(zs)) / (max(zs) - min(zs)))
    slam = add(base, {"upper_arm.L": (-50, -10, 0), "upper_arm.R": (-50, 10, 0), "forearm.L": (-10, 0, 0), "forearm.R": (-10, 0, 0),
                      "spine": (30, 0, 0), "chest": (12, 0, 0), "thigh.L": (-22, 0, 0), "thigh.R": (-18, 0, 0),
                      "shin.L": (35, 0, 0), "shin.R": (30, 0, 0), "_loc": {"hips": (0, -0.1, -0.3)}})
    attack = [(0, base),
              (0.4, add(base, {"upper_arm.L": (-165, -15, 0), "upper_arm.R": (-165, 15, 0), "forearm.L": (-30, 0, 0),
                               "forearm.R": (-30, 0, 0), "spine": (-18, 0, 0), "chest": (-10, 0, 0), "head": (-10, 0, 0)})),
              (0.55, slam), (0.75, slam), (1, base)]
    gait = {"walk_T": 1.7, "walk": dict(A=17, K=28, arm=12, bob=0.07, lean=3, sway=7, elbow=10),
            "run_T": 1.15, "run": dict(A=25, K=50, arm=22, bob=0.1, lean=10, sway=9, elbow=30)}
    acts = base_human_actions(arm, base, H, attack=(attack, 1.7), gait=gait, heavy=1.0, flail=False, girth=2.3)
    INFO["golem"] = dict(h=H, acts=acts, desc="Глиняный голем из пражской легенды: массивное тело из потрескавшейся серо-коричневой "
                         "глины, длинные руки, маленькая голова, на лбу светятся буквы אמת (emet).",
                         parts="attack = удар двумя руками сверху; бросать в окно нельзя (нет flail)")
    return root


def build_skeleton():
    H = 1.85
    s = H / 1.8
    root, col, arm, j = start("skeleton", H, width=0.95)
    base = {"upper_arm.R": (-8, 4, 0), "forearm.R": (-35, 0, 0), "upper_arm.L": (-15, -8, 0), "forearm.L": (-50, 0, -15),
            "spine": (8, 0, 0), "head": (-6, 0, 0)}
    set_base(arm, base)
    B = C.Body("skeleton", arm, col)
    held(B, arm, "hand.R", "WEAPON_sword", lambda mb: sword_mesh(mb, 0.95, "M_RustyIron", "M_LeatherDark", "M_RustyIron", True),
         grip_of(arm, "R"), rot_to((-0.05, -0.5, -0.86)))
    fh, ft = posed_points(arm, "forearm.L")
    sc = fh.lerp(ft, 0.55) + V((0.08, -0.03, 0))
    mb = B.separate("WEAPON_shield", ["forearm.L"], 6)
    mb.push(posed_to_rest(arm, "forearm.L") @ Matrix.Translation(sc) @ (V((0.75, -0.66, 0))).to_track_quat("Z", "Y").to_matrix().to_4x4())
    pts = [(-0.24, 0.3), (0.24, 0.3), (0.24, 0.05)] + [(0.24 * math.cos(t), -0.05 - 0.38 * math.sin(t)) for t in
                                                         [k * PI / 2 / 6 for k in range(1, 6)]] + [(0, -0.43)] + \
          [(-0.24 * math.sin(t), -0.05 - 0.38 * math.cos(t)) for t in [k * PI / 2 / 6 for k in range(1, 6)]] + [(-0.24, 0.05)]
    with mb.at(rot_x=-PI / 2):
        mb.prism(pts, -0.02, 0.02, "M_RustyIron", plane="xz")
    mb.pop()
    M = "M_Bone"
    for X in ("L", "R"):
        hip, knee, ank, toe = j[f"hip.{X}"], j[f"knee.{X}"], j[f"ankle.{X}"], j[f"toe.{X}"]
        mb = B.part([f"thigh.{X}"], 6)
        loft(mb, [hip, hip.lerp(knee, 0.5), knee], [0.03, 0.022, 0.03], M, segs=8)
        mb.sphere(knee, 0.04, M, segs=8, rings=5)
        mb = B.part([f"shin.{X}"], 6)
        loft(mb, [knee, knee.lerp(ank, 0.5), ank], [0.028, 0.02, 0.024], M, segs=8)
        mb.sphere(knee + V((0, -0.035, 0)), 0.025, M, segs=6, rings=4)
        # rusty greaves / boots (as on concept)
        loft(mb, [knee.lerp(ank, 0.45), ank + V((0, 0, 0.02))], [0.05, 0.048], "M_LeatherDark", segs=10, jag=0.02)
        mb = B.part([f"foot.{X}"], 6)
        heel = V((ank.x, ank.y + 0.04, 0.04))
        loft(mb, [heel, V((toe.x, toe.y, 0.03))], [(0.045, 0.04), (0.045, 0.03)], "M_LeatherDark", segs=8)
        a, e, w, he = j[f"arm.{X}"], j[f"elbow.{X}"], j[f"wrist.{X}"], j[f"hand_end.{X}"]
        mb = B.part([f"upper_arm.{X}"], 6)
        loft(mb, [a, a.lerp(e, 0.5), e], [0.032, 0.02, 0.026], M, segs=8)
        mb.sphere(a, 0.04, M, segs=8, rings=5)
        mb = B.part([f"forearm.{X}"], 6)
        for dx in (-0.012, 0.012):
            loft(mb, [e + V((dx, 0, 0)), w + V((dx, 0, 0))], [0.016, 0.013], M, segs=6)
        loft(mb, [e.lerp(w, 0.3), w], [0.045, 0.042], "M_LeatherDark", segs=10, jag=0.02)  # bracers
        mb = B.part([f"hand.{X}"], 6)
        c = w.lerp(he, 0.3)
        mb.sphere(c, (0.02, 0.03, 0.035), M, segs=8, rings=5)
        for k in range(4):
            off = V(((k - 1.5) * 0.008 * (1 if X == "L" else -1), -0.012 + 0.01 * k - 0.015, 0))
            loft(mb, [c + off, c + off + V((0, -0.02, -0.07))], [0.007, 0.005], M, segs=5)
    # pelvis, spine, ribcage, skull
    mb = B.part(["hips"], 6)
    with mb.at((0, 0, j["pelvis"].z - 0.02), scale=(1.0, 0.65, 0.6)):
        mb.torus(0.11, 0.035, M, segs=14, tsegs=6)
    mb = B.part(["hips", "spine", "chest", "neck"], 3)
    loft(mb, [j["pelvis"] + V((0, 0.04, 0)), j["spine"] + V((0, 0.05, 0)), j["chest"] + V((0, 0.06, 0)), j["neck"] + V((0, 0.03, 0.05))],
         [0.024, 0.022, 0.022, 0.02], M, segs=8)
    mb = B.part(["chest", "spine"], 4)
    for k in range(6):
        z = j["chest"].z - 0.1 + k * 0.045
        rx = 0.13 + 0.025 * math.sin(PI * (k + 1) / 7)
        with mb.at((0, -0.005, z), rot_x=-0.25, scale=(1.0, 0.75, 1.0)):
            mb.torus(rx, 0.011, M, segs=16, tsegs=4)
    mb.box((-0.012, -0.11, j["chest"].z - 0.08), (0.012, -0.095, j["chest"].z + 0.16), M)  # sternum
    for X, sx in (("L", 1), ("R", -1)):
        mb.rod(j["neck"] + V((0, -0.06, -0.04)), j[f"arm.{X}"] + V((0, -0.02, 0.02)), 0.012, M, segs=5)  # clavicle
    hc = j["head"] + V((0, -0.012, 0.1 * s))
    mb = B.part(["head"], 4)
    mb.sphere(hc + V((0, 0.01, 0.01)), (0.08, 0.095, 0.095), M, segs=14, rings=10)
    mb.sphere(hc + V((0, -0.04, -0.06)), (0.055, 0.055, 0.045), M, segs=10, rings=6)
    for sx in (-1, 1):
        mb.sphere(hc + V((sx * 0.032, -0.072, 0.012)), (0.024, 0.016, 0.022), "M_EyeDark", segs=8, rings=5)
        mb.sphere(hc + V((sx * 0.032, -0.08, 0.012)), 0.011, "M_EyeGlow", segs=8, rings=5)
    mb.box(hc + V((-0.03, -0.095, -0.075)), hc + V((0.03, -0.088, -0.06)), "M_EyeWhite")  # teeth
    mb.box(hc + V((-0.008, -0.1, -0.02)), hc + V((0.008, -0.09, 0.0)), "M_EyeDark")      # nose hole
    mb = B.part(["neck", "head"], 4)
    loft(mb, [j["neck"], j["head"]], [0.018, 0.018], M, segs=6)
    # rusty helmet with nasal, chainmail scraps, pauldron, red loincloth, belt
    mb = B.part(["head"], 4)
    mb.sphere(hc + V((0, 0.005, 0.03)), (0.098, 0.112, 0.105), "M_RustyIron", segs=14, rings=9,
              skip=lambda x, y, z: z < -0.05 and not (y > 0.2 and z > -0.5))
    loft(mb, [hc + V((0, -0.005, 0.035)), hc + V((0, -0.005, 0.0))], [(0.105, 0.118), (0.104, 0.117)], "M_RustyIron", segs=16,
         cap0=False, cap1=False)
    mb.box(hc + V((-0.012, -0.12, -0.04)), hc + V((0.012, -0.105, 0.05)), "M_RustyIron")
    torso(B, s, "M_ChainmailRust", w=0.95, grow=0.0, z_from=1.1, z_to=1.46, cap=False, jag=0.04)
    mb = B.part(["chest", "shoulder.L", "upper_arm.L"], 4)
    mb.sphere(j["arm.L"] + V((0, 0, 0.03)), (0.09, 0.09, 0.07), "M_RustyIron", segs=10, rings=6, z_cut=j["arm.L"].z - 0.02)
    skirt(B, s, "M_MantleRed", 1.0, 0.62, (0.15, 0.11), (0.2, 0.16), jag=0.1, seed=11)
    band(B, s, 1.0, 0.16, 0.12, "M_LeatherDark", 0.05)
    B.build()
    acts = base_human_actions(arm, base, H, attack=sword_attack(base, 1.0))
    INFO["skeleton"] = dict(h=H, acts=acts, desc="Скелет-воин, поднятый алхимией: жёлтые кости, ржавый шлем с наносником, "
                            "обрывки ржавой кольчуги, наплечник, рваная красная набедренная ткань, ржавые наручи и обмотки, "
                            "зазубренный ржавый меч, ржавый щит; глазницы светятся зелёным.",
                            parts="WEAPON_sword (hand.R), WEAPON_shield (forearm.L)")
    return root


# ----------------------------------------------------------------------------- townsfolk
def talk_fn(base):
    def f(t):
        ph = 2 * PI * t
        return add(base, {"upper_arm.R": (-35 - 12 * math.sin(ph), 12, 0), "forearm.R": (-55 + 20 * math.sin(2 * ph), 0, 10),
                          "head": (4 * math.sin(2 * ph), 0, 6 * math.sin(ph)), "chest": (0, 0, 4 * math.sin(ph))})
    return f


def build_butcher():
    H = 1.78
    s = H / 1.8
    root, col, arm, j = start("butcher", H, width=1.08)
    base = {"forearm.L": (-12, 0, 0), "forearm.R": (-40, 0, 0), "upper_arm.R": (-5, 5, 0)}
    set_base(arm, base)
    B = C.Body("butcher", arm, col)

    def knife(mb):
        mb.prism([(-0.02, -0.06), (0.03, -0.06), (0.035, -0.32), (-0.02, -0.3)], -0.004, 0.004, "M_Steel")
        mb.rod((0, 0, -0.06), (0, 0, 0.07), 0.016, "M_Timber", segs=6)
    held(B, arm, "hand.R", "HELD_cleaver", knife, grip_of(arm, "R"), rot_to((0, -0.7, -0.7)))
    legs(B, j, s, "M_WoolBrown", r=1.1, boots="M_LeatherC", boot_top=0.55)
    torso(B, s, "M_Linen", w=1.08, belly=0.03)
    torso(B, s, "M_LeatherC", w=1.08, grow=0.012, z_from=1.1, z_to=1.46, cap=False, belly=0.03)
    skirt(B, s, "M_Linen", 1.02, 0.78, (0.18, 0.13), (0.2, 0.15))
    mb = B.part(["hips", "spine", "chest", "thigh.L", "thigh.R"], 3)  # apron
    loft(mb, [V((0, -0.155 * s, 1.36 * s)), V((0, -0.17 * s, 1.1 * s)), V((0, -0.2 * s, 0.85 * s)), V((0, -0.21 * s, 0.55 * s))],
         [(0.13 * s, 0.012 * s), (0.16 * s, 0.012 * s), (0.2 * s, 0.012 * s), (0.2 * s, 0.012 * s)], "M_Apron", segs=8)
    band(B, s, 1.08, 0.19, 0.15, "M_LeatherDark", 0.04)
    arms(B, j, s, "M_Linen", "M_Skin", r=1.12, forearm_mat="M_Skin")
    hc = head(B, j, s, "M_Skin", hair="M_HairDark", beard="M_HairDark", hair_style="short")
    mb = B.part(["head"], 4)
    mb.sphere(hc + V((0, 0.01, 0.035 * s)), (0.096 * s, 0.106 * s, 0.1 * s), "M_ClothRed", segs=14, rings=8,
              skip=lambda x, y, z: z < 0.05)
    B.build()
    chop = seq([(0, base), (0.25, add(base, {"upper_arm.R": (-140, 20, 0), "forearm.R": (-30, 0, 0), "spine": (-5, 0, 0)})),
                (0.4, add(base, {"upper_arm.R": (-60, 5, 0), "forearm.R": (0, 0, 0), "spine": (15, 0, 0)})),
                (0.6, add(base, {"upper_arm.R": (-140, 20, 0), "forearm.R": (-30, 0, 0), "spine": (-5, 0, 0)})),
                (0.75, add(base, {"upper_arm.R": (-60, 5, 0), "forearm.R": (0, 0, 0), "spine": (15, 0, 0)})), (1, base)])
    acts = base_human_actions(arm, base, H, extra={"work": (chop, 1.6), "talk": (talk_fn(base), 2.0)})
    INFO["butcher"] = dict(h=H, acts=acts, desc="Мясник: крепкий, красная шапочка, борода, льняная рубаха с закатанными рукавами, "
                           "кожаный жилет, фартук в крови, сапоги, тесак.", parts="HELD_cleaver (hand.R); work = рубит мясо")
    return root


def build_market_woman():
    H = 1.66
    s = H / 1.8
    root, col, arm, j = start("market_woman", H, width=0.92)
    base = {"upper_arm.L": (-25, 6, 0), "upper_arm.R": (-25, -6, 0), "forearm.L": (-70, 0, -35), "forearm.R": (-70, 0, 35)}
    set_base(arm, base)
    B = C.Body("market_woman", arm, col)
    gl, gr = grip_of(arm, "L"), grip_of(arm, "R")
    bc = gl.lerp(gr, 0.5) + V((0, -0.08, -0.05))

    def basket(mb):
        mb.lathe([(0.12, -0.18), (0.16, -0.06), (0.19, 0.05)], "M_WoodLight", segs=14, cap_top=False)
        with mb.at((0, 0, 0.05)):
            mb.torus(0.19, 0.014, "M_Timber", segs=16, tsegs=4)
        rnd = random.Random(3)
        for k in range(7):
            a = 2 * PI * k / 7
            mb.sphere((0.08 * math.cos(a), 0.08 * math.sin(a), 0.05), 0.045, ["M_Apple", "M_Carrot", "M_Cabbage"][k % 3], segs=8, rings=5)
        mb.sphere((0, 0, 0.08), 0.06, "M_Cabbage", segs=8, rings=5)
    mb = B.separate("HELD_basket", ["hand.L"], 6)
    mb.push(posed_to_rest(arm, "hand.L") @ Matrix.Translation(bc))
    basket(mb)
    mb.pop()
    legs(B, j, s, "M_WoolBrown", r=0.95, boots="M_LeatherC", boot_top=0.7)
    torso(B, s, "M_ClothGreen", w=0.95, z_from=1.05)
    torso(B, s, "M_Linen", w=0.95, z_from=1.4, grow=0.004)
    skirt(B, s, "M_ClothRed", 1.06, 0.06, (0.16, 0.12), (0.27, 0.25), jag=0.02, rings=6, seed=21)
    mb = B.part(["hips", "spine", "thigh.L", "thigh.R", "shin.L", "shin.R"], 3)  # apron
    loft(mb, [V((0, -0.13 * s, 1.08 * s)), V((0, -0.18 * s, 0.7 * s)), V((0, -0.24 * s, 0.25 * s))],
         [(0.14 * s, 0.01 * s), (0.17 * s, 0.01 * s), (0.18 * s, 0.01 * s)], "M_Linen", segs=8)
    band(B, s, 1.07, 0.165, 0.125, "M_LeatherC", 0.035)
    arms(B, j, s, "M_ClothRed", "M_Skin", r=0.92, forearm_mat="M_Linen")
    hc = head(B, j, s, "M_Skin", hair="M_HairBrown", hair_style="short", nose=0.85)
    hood(B, hc, s, "M_Linen", scale=0.95)
    B.build()
    acts = base_human_actions(arm, base, H, extra={"talk": (talk_fn(base), 2.0)})
    INFO["market_woman"] = dict(h=H, acts=acts, desc="Рыночная торговка: белый платок, зелёный корсаж, красные рукава и юбка, "
                                "льняной фартук, корзина с яблоками, морковью и капустой в руках.", parts="HELD_basket (hand.L)")
    return root


def build_merchant():
    H = 1.8
    s = 1.0
    root, col, arm, j = start("merchant", H, width=1.12)
    base = {"upper_arm.R": (-15, 8, 0), "forearm.R": (-55, 0, 0), "upper_arm.L": (-6, -4, 0), "forearm.L": (-20, 0, 0)}
    set_base(arm, base)
    B = C.Body("merchant", arm, col)

    def purse(mb):
        with mb.at((0, 0, -0.1)):
            mb.sphere((0, 0, 0), (0.06, 0.06, 0.075), "M_LeatherC", segs=10, rings=6, noise=0.08, seed=2)
        mb.rod((0, 0, -0.04), (0, 0, 0.03), 0.008, "M_Rope", segs=4)
    held(B, arm, "hand.R", "HELD_purse", purse, grip_of(arm, "R"), Matrix.Identity(4))
    legs(B, j, s, "M_WoolBlue", r=1.05, boots="M_LeatherC", boot_top=0.6)
    torso(B, s, "M_MerchantCoat", w=1.12, belly=0.05)
    skirt(B, s, "M_MerchantCoat", 1.04, 0.12, (0.2, 0.17), (0.3, 0.27), rings=6, seed=31)
    mb = B.part(["hips", "thigh.L", "thigh.R", "shin.L", "shin.R"], 2.5)  # fur hem
    loft(mb, [V((0, 0.0, 0.2)), V((0, 0, 0.12))], [(0.295, 0.265), (0.31, 0.28)], "M_Fur", segs=16, cap0=False, cap1=False)
    mb = B.part(["chest", "spine", "neck"], 3)  # fur collar
    loft(mb, [V((0, 0.0, 1.38)), V((0, 0.0, 1.52))], [(0.24, 0.17), (0.12, 0.11)], "M_Fur", segs=16, cap0=False, cap1=False,
         noise=0.06)
    band(B, s, 1.05, 0.215, 0.18, "M_LeatherDark", 0.05)
    arms(B, j, s, "M_MerchantCoat", "M_Skin", r=1.15, cuff="M_Fur")
    hc = head(B, j, s, "M_Skin", hair="M_HairDark", beard="M_HairDark", hair_style="short")
    mb = B.part(["head"], 4)
    loft(mb, [hc + V((0, 0.005, 0.05)), hc + V((0, 0.005, 0.13)), hc + V((0, 0.005, 0.16))],
         [(0.115, 0.125), (0.12, 0.13), (0.1, 0.11)], "M_Fur", segs=16, noise=0.05)
    B.build()
    acts = base_human_actions(arm, base, H, extra={"talk": (talk_fn(base), 2.0)})
    INFO["merchant"] = dict(h=H, acts=acts, desc="Купец: меховая шапка, борода, длинный красный кафтан с меховым воротником и "
                            "оторочкой, синие шоссы, кошель с монетами в руке.", parts="HELD_purse (hand.R)")
    return root


def build_guard():
    H = 1.82
    s = H / 1.8
    root, col, arm, j = start("guard", H)
    base = {"upper_arm.R": (-14, 8, 0), "forearm.R": (-72, 0, 0), "upper_arm.L": (-5, -4, 0), "forearm.L": (-15, 0, 0)}
    set_base(arm, base)
    B = C.Body("guard", arm, col)

    def halberd(mb):
        mb.rod((0, 0, -1.0), (0, 0, 1.25), 0.02, "M_Timber", segs=8)
        mb.prism([(-0.03, 1.25), (0.03, 1.25), (0.0, 1.55)], -0.006, 0.006, "M_Steel")
        mb.prism([(0.0, 1.05), (0.24, 0.98), (0.27, 1.12), (0.25, 1.26), (0.0, 1.2)], -0.006, 0.006, "M_Steel")
        mb.prism([(0.0, 1.08), (-0.14, 1.12), (0.0, 1.17)], -0.006, 0.006, "M_Steel")
    g = grip_of(arm, "R")
    mb = B.separate("WEAPON_halberd", ["hand.R"], 6)
    mb.push(posed_to_rest(arm, "hand.R") @ Matrix.Translation(g) @ Matrix.Rotation(PI / 2 - 0.25, 4, "Z"))
    halberd(mb)
    mb.pop()
    legs(B, j, s, "M_WoolBrown", boots="M_LeatherC", boot_top=0.1)
    torso(B, s, "M_Chainmail")
    skirt(B, s, "M_Chainmail", 1.02, 0.6, (0.165, 0.115), (0.19, 0.15), jag=0.02)
    torso(B, s, "M_ClothRed", grow=0.012, z_from=1.0, z_to=1.46, cap=False)
    skirt(B, s, "M_ClothRed", 1.02, 0.55, (0.18, 0.13), (0.2, 0.17), jag=0.03, seed=41)
    decal(B, s, 1.13, 1.42, 0.11, -0.142, "M_Tabard")
    decal(B, s, 1.13, 1.42, 0.11, 0.142, "M_Tabard", back=True)
    band(B, s, 1.04, 0.178, 0.13, "M_LeatherC", 0.05)
    arms(B, j, s, "M_Chainmail", "M_LeatherC", cuff="M_LeatherC")
    hc = head(B, j, s, "M_Skin", hair="M_HairBrown", beard="M_HairBrown", hair_style="short")
    mb = B.part(["head"], 4)  # kettle hat
    mb.sphere(hc + V((0, 0.005, 0.03 * s)), (0.1 * s, 0.11 * s, 0.11 * s), "M_Steel", segs=14, rings=8, skip=lambda x, y, z: z < 0.1)
    loft(mb, [hc + V((0, 0.005, 0.035 * s)), hc + V((0, 0.005, 0.02 * s))], [(0.17 * s, 0.18 * s), (0.18 * s, 0.19 * s)],
         "M_Steel", segs=18)
    mb = B.part(["hips", "thigh.L"], 4)  # sword at hip
    loft(mb, [V((0.2, 0.03, 1.0)), V((0.24, 0.1, 0.45))], [0.028, 0.02], "M_LeatherDark", segs=6)
    B.build()
    attack = [(0, base),
              (0.3, add(base, {"upper_arm.R": (10, 0, 0), "hand.R": (-60, 0, 0), "upper_arm.L": (-40, -10, 0), "forearm.L": (-50, 0, -20),
                               "chest": (0, 0, -18), "thigh.R": (10, 0, 0)})),
              (0.5, add(base, {"upper_arm.R": (-45, -10, 0), "forearm.R": (50, 0, 0), "hand.R": (-70, 0, 0), "upper_arm.L": (-60, -10, 0),
                               "forearm.L": (-40, 0, -30), "chest": (0, 0, 15), "spine": (14, 0, 0), "thigh.L": (-30, 0, 0),
                               "shin.L": (25, 0, 0), "thigh.R": (18, 0, 0), "_loc": {"hips": (0, -0.12, -0.05)}})),
              (0.7, add(base, {"upper_arm.R": (-40, -10, 0), "forearm.R": (45, 0, 0), "hand.R": (-70, 0, 0), "spine": (10, 0, 0),
                               "thigh.L": (-25, 0, 0), "shin.L": (20, 0, 0), "_loc": {"hips": (0, -0.1, -0.04)}})),
              (1, base)]
    acts = base_human_actions(arm, base, H, attack=(attack, 1.1), extra={"talk": (talk_fn(base), 2.0)})
    INFO["guard"] = dict(h=H, acts=acts, desc="Городской стражник: шляпа-шапель (kettle hat), кольчуга, красная котта с белым львом, "
                         "сапоги, меч на поясе, алебарда.", parts="WEAPON_halberd (hand.R); attack = выпад алебардой")
    return root


def build_beggar():
    H = 1.72
    s = H / 1.8
    root, col, arm, j = start("beggar", H, width=0.95)
    base = {"spine": (18, 0, 0), "chest": (8, 0, 0), "head": (-14, 0, 0), "upper_arm.R": (-35, 6, 0), "forearm.R": (-55, 0, 0),
            "upper_arm.L": (-10, -4, 0), "forearm.L": (-30, 0, 0), "thigh.L": (-6, 0, 0), "thigh.R": (-6, 0, 0),
            "shin.L": (12, 0, 0), "shin.R": (12, 0, 0), "_loc": {"hips": (0, 0, -0.03)}}
    set_base(arm, base)
    B = C.Body("beggar", arm, col)

    def bowl(mb):
        with mb.at((0, -0.08, 0.02)):
            mb.lathe([(0.04, 0.0), (0.09, 0.03), (0.1, 0.06), (0.095, 0.06), (0.085, 0.03), (0.035, 0.012)], "M_WoodLight",
                     segs=14, cap_bottom=True, cap_top=False)
    held(B, arm, "hand.R", "HELD_bowl", bowl, grip_of(arm, "R"), Matrix.Identity(4))
    legs(B, j, s, "M_Skin", r=0.85, bare_feet="M_Skin")
    torso(B, s, "M_Rags", w=0.95)
    skirt(B, s, "M_Rags", 1.04, 0.3, (0.17, 0.125), (0.25, 0.22), jag=0.12, rings=6, seed=51)
    arms(B, j, s, "M_Rags", "M_Skin", r=0.95)
    hc = head(B, j, s, "M_Skin", hair="M_HairGrey", beard="M_HairGrey", hair_style="long")
    hood(B, hc, s, "M_Rags")
    cape(B, s, "M_Rags", 1.5, 1.15, (0.12, 0.1), (0.26, 0.2), jag=0.08, seed=52)
    band(B, s, 1.04, 0.17, 0.125, "M_Rope", 0.025)
    B.build()
    beg = lambda t: add(base, {"upper_arm.R": (-10 * math.sin(2 * PI * t) - 8, 0, 0), "forearm.R": (-8 * math.sin(2 * PI * t), 0, 0),  # noqa
                               "head": (-6 * math.sin(2 * PI * t), 0, 0)})
    acts = base_human_actions(arm, base, H, extra={"beg": (beg, 2.0), "talk": (talk_fn(base), 2.0)})
    INFO["beggar"] = dict(h=H, acts=acts, desc="Нищий: сгорбленный, рваный капюшон и лохмотья, седая борода, босой, деревянная миска.",
                          parts="HELD_bowl (hand.R); beg = протягивает миску")
    return root


def build_child(name, girl):
    H = 1.28 if girl else 1.32
    s = H / 1.8
    over = {"head": (0, -0.005, 1.56), "head_top": (0, -0.01, 1.82), "neck": (0, 0, 1.48)}
    root, col, arm, j = start(name, H, over, width=0.92)
    base = {"forearm.L": (-15, 0, 0), "forearm.R": (-15, 0, 0)}
    if girl:
        base = {"upper_arm.L": (-20, 10, 0), "upper_arm.R": (-20, -10, 0), "forearm.L": (-60, 0, -40), "forearm.R": (-60, 0, 40)}
    set_base(arm, base)
    B = C.Body(name, arm, col)
    legs(B, j, s, "M_WoolBrown", boots="M_LeatherC", boot_top=0.6)
    if girl:
        torso(B, s, "M_WoolBlue", w=0.95)
        skirt(B, s, "M_WoolBlue", 1.04, 0.1, (0.16, 0.12), (0.24, 0.22), rings=5, seed=61)
        mb = B.part(["hips", "spine", "thigh.L", "thigh.R"], 3)
        loft(mb, [V((0, -0.13 * s, 1.1 * s)), V((0, -0.2 * s, 0.4 * s))], [(0.13 * s, 0.01 * s), (0.16 * s, 0.01 * s)], "M_Linen", segs=8)
        arms(B, j, s, "M_WoolBlue", "M_SkinChild")
        hc = head(B, j, s, "M_SkinChild", hair="M_HairBrown", hair_style="short", scale=1.28, nose=0.7)
        hood(B, hc, s, "M_Linen", scale=1.24, drape=False)
        # rag doll held to chest (as on the concept)
        gl, gr = grip_of(arm, "L"), grip_of(arm, "R")
        mb = B.separate("HELD_doll", ["hand.L"], 6)
        mb.push(posed_to_rest(arm, "hand.L") @ Matrix.Translation(gl.lerp(gr, 0.5) + V((0, -0.03, 0.04))))
        mb.sphere((0, 0, 0.0), (0.05, 0.035, 0.08), "M_ClothRed", segs=8, rings=5)
        mb.sphere((0, 0, 0.1), 0.04, "M_Linen", segs=8, rings=5)
        mb.pop()
    else:
        torso(B, s, "M_WoolBrown", w=0.95)
        skirt(B, s, "M_WoolBrown", 1.04, 0.72, (0.165, 0.12), (0.19, 0.15), jag=0.02, seed=62)
        band(B, s, 1.04, 0.17, 0.125, "M_LeatherC", 0.05)
        arms(B, j, s, "M_WoolBrown", "M_SkinChild")
        head(B, j, s, "M_SkinChild", hair="M_HairBrown", hair_style="messy", scale=1.28, nose=0.7)
    B.build()
    acts = base_human_actions(arm, base, H, extra={"talk": (talk_fn(base), 2.0)})
    INFO[name] = dict(h=H, acts=acts, desc=("Девочка: голубое платье, льняной фартук и платок, тряпичная кукла в руках." if girl else
                                            "Мальчик: коричневая туника с поясом, растрёпанные волосы, сапожки."),
                      parts="HELD_doll (hand.L)" if girl else "")
    return root


# ============================================================================= run 2: Vysehrad / river characters
def build_knight():
    """Knight of the Vysehrad garrison: mail coif + nasal helm, red lion surcoat, sword and round shield."""
    H = 1.82
    s = H / 1.8
    root, col, arm, j = start("knight", H, width=1.04)
    base = {"upper_arm.R": (-8, 4, 0), "forearm.R": (-38, 0, 0), "hand.R": (5, 0, 0),
            "upper_arm.L": (-18, -8, 0), "forearm.L": (-55, 0, -20)}
    set_base(arm, base)
    B = C.Body("knight", arm, col)
    held(B, arm, "hand.R", "WEAPON_sword", lambda mb: longsword(mb, 0.92), grip_of(arm, "R"), rot_to((-0.05, -0.55, -0.83)))
    fh, ft = posed_points(arm, "forearm.L")
    sc = fh.lerp(ft, 0.55) + V((0.1, -0.035, 0))
    mb = B.separate("WEAPON_shield", ["forearm.L"], 6)
    mb.push(posed_to_rest(arm, "forearm.L") @ Matrix.Translation(sc) @ (V((0.75, -0.66, 0.0))).to_track_quat("Z", "Y").to_matrix().to_4x4())
    round_shield(mb, 0.33)
    mb.pop()
    legs(B, j, s, "M_Chainmail", boots="M_LeatherDark", boot_top=0.45)
    torso(B, s, "M_Chainmail", w=1.05)
    skirt_panels(B, s, "M_Chainmail", 1.02, 0.5, (0.17, 0.12), (0.205, 0.165), slits=((-90, 9),), jag=0.015, seed=72)
    torso(B, s, "M_ClothRed", w=1.05, grow=0.013, z_from=1.0, z_to=1.46, cap=False)
    skirt_panels(B, s, "M_ClothRed", 1.02, 0.52, (0.185, 0.135), (0.23, 0.19), slits=((-90, 12), (90, 10)), jag=0.03, seed=73,
                 inner="M_WoolBrown")
    decal(B, s, 1.1, 1.43, 0.12, -0.144, "M_Tabard")
    decal(B, s, 1.1, 1.43, 0.12, 0.144, "M_Tabard", back=True)
    belt_ring(B, s, 1.045, 0.186, 0.137, "M_LeatherDark", 0.05)
    belt_ring(B, s, 0.98, 0.19, 0.145, "M_LeatherDark", 0.035, tilt=0.25)
    arms(B, j, s, "M_Chainmail", "M_LeatherDark", r=1.06, cuff="M_LeatherDark")
    hc = head(B, j, s, "M_Skin", hair=None, beard="M_HairBrown", hair_style="short")
    mb = B.part(["head", "neck"], 4)          # mail coif framing the face
    mb.sphere(hc + V((0, 0.01 * s, 0.0)), (0.1 * s, 0.112 * s, 0.128 * s), "M_Chainmail", segs=18, rings=12,
              skip=lambda x, y, z: (y < -0.45 and -0.62 < z < 0.4 and abs(x) < 0.62) or z < -0.85, noise=0.01, seed=3)
    mb = B.part(["neck", "chest"], 3)
    loft(mb, [V((0, 0.005 * s, 1.6 * s)), V((0, 0.005 * s, 1.5 * s)), V((0, 0.005 * s, 1.42 * s))],
         [(0.09 * s, 0.085 * s), (0.17 * s, 0.13 * s), (0.22 * s, 0.15 * s)], "M_Chainmail", segs=16, cap0=False, cap1=False)
    mb = B.part(["head"], 4)                 # conical nasal helm
    loft(mb, [hc + V((0, 0.008 * s, 0.025 * s)), hc + V((0, 0.008 * s, 0.09 * s)), hc + V((0, 0.0, 0.17 * s))],
         [(0.106 * s, 0.118 * s), (0.094 * s, 0.104 * s), (0.008 * s, 0.008 * s)], "M_Steel", segs=16)
    loft(mb, [hc + V((0, 0.008 * s, 0.02 * s)), hc + V((0, 0.008 * s, 0.04 * s))], [(0.11 * s, 0.122 * s)] * 2, "M_Iron",
         segs=16, cap0=False, cap1=False)
    mb.box(hc + V((-0.009 * s, -0.128 * s, -0.035 * s)), hc + V((0.009 * s, -0.112 * s, 0.035 * s)), "M_Iron")
    mb = B.part(["hips", "thigh.L"], 4)
    loft(mb, [V((0.2, 0.03, 0.96)), V((0.235, 0.09, 0.62)), V((0.25, 0.13, 0.45))], [0.03, 0.025, 0.02], "M_LeatherDark", segs=8)
    B.build()
    guard_up = add(base, {"upper_arm.L": (-55, -15, 0), "forearm.L": (-35, 0, -35), "thigh.L": (-14, 0, 0), "shin.L": (18, 0, 0),
                          "thigh.R": (8, 0, 0), "upper_arm.R": (-60, 20, 0), "forearm.R": (-60, 0, 0), "_loc": {"hips": (0, 0, -0.05)}})
    keys, T = sword_attack(base)
    cut = keys[2][1]
    spar = seq([(0, guard_up), (0.25, keys[1][1]), (0.38, cut), (0.5, guard_up), (0.62, add(guard_up, {"spine": (6, 0, 0)})),
                (0.75, add(guard_up, {"upper_arm.L": (-75, -25, 0), "chest": (0, 0, 15), "_loc": {"hips": (0, 0.06, -0.06)}})),
                (1, guard_up)])
    acts = base_human_actions(arm, base, H, attack=(keys, T), extra={
        "talk": (talk_fn(base), 2.0), "spar": (spar, 2.4),
        "block": (lambda t: add(guard_up, {"spine": (math.sin(2 * PI * t) * 2, 0, 0)}), 1.0)})
    INFO["knight"] = dict(h=H, acts=acts, desc="Рыцарь гарнизона Вышеграда: кольчужный капюшон и конический шлем с наносником, "
                          "кольчуга с ног до головы, красное сюрко со львом, меч и круглый щит.",
                          parts="WEAPON_sword (hand.R), WEAPON_shield (forearm.L); spar = учебный поединок (цикл)")
    return root


def build_monk():
    """Canon of the Vysehrad chapter: brown habit with hood down, tonsure, rope belt, book held to the chest."""
    H = 1.76
    s = H / 1.8
    root, col, arm, j = start("monk", H, width=0.98)
    base = {"upper_arm.L": (-22, 6, 0), "upper_arm.R": (-22, -6, 0), "forearm.L": (-80, 0, -40), "forearm.R": (-80, 0, 40),
            "head": (6, 0, 0)}
    set_base(arm, base)
    B = C.Body("monk", arm, col)
    gl, gr = grip_of(arm, "L"), grip_of(arm, "R")
    mb = B.separate("HELD_book", ["hand.L"], 6)
    mb.push(posed_to_rest(arm, "hand.L") @ Matrix.Translation(gl.lerp(gr, 0.5) + V((0, -0.05, 0.04))))
    mb.box((-0.11, -0.03, -0.14), (0.11, 0.03, 0.14), {"-y": "M_ClothRed", "+y": "M_ClothRed", "-x": "M_Linen", "+x": "M_ClothRed",
                                                        "-z": "M_Linen", "+z": "M_Linen"})
    mb.box((-0.115, -0.035, -0.02), (-0.09, 0.035, 0.02), "M_Brass")
    mb.pop()
    legs(B, j, s, "M_RobeBrown", r=0.95, bare_feet="M_LeatherC")
    torso(B, s, "M_RobeBrown", w=1.0, belly=0.02)
    skirt(B, s, "M_RobeBrown", 1.04, 0.05, (0.18, 0.14), (0.28, 0.25), jag=0.015, rings=6, seed=81)
    arms(B, j, s, "M_RobeBrown", "M_Skin", r=1.15)
    for X in ("L", "R"):                                        # wide sleeves
        e, w = j[f"elbow.{X}"], j[f"wrist.{X}"]
        mb = B.part([f"forearm.{X}"], 5)
        loft(mb, [e, w + (w - e).normalized() * 0.02 * s], [0.06 * s, 0.085 * s], "M_RobeBrown", segs=12, cap0=False, cap1=False)
    belt_ring(B, s, 1.04, 0.19, 0.155, "M_Rope", 0.022)
    mb = B.part(["hips", "thigh.R"], 3)
    loft(mb, [V((-0.12, -0.13, 1.03)), V((-0.13, -0.15, 0.75)), V((-0.12, -0.15, 0.55))], [0.012, 0.011, 0.01], "M_Rope", segs=5)
    hc = head(B, j, s, "M_Skin", hair="M_HairGrey", hair_style="short")
    mb = B.part(["head"], 4)                                     # tonsure: bare crown over the hair cap
    mb.sphere(hc + V((0, 0.004 * s, 0.03 * s)), (0.088 * s, 0.1 * s, 0.11 * s), "M_Skin", segs=14, rings=10,
              skip=lambda x, y, z: z < 0.72)
    mb = B.part(["neck", "chest", "head"], 3)                    # hood lying on the shoulders
    loft(mb, [V((0, 0.02 * s, 1.56 * s)), V((0, 0.04 * s, 1.48 * s)), V((0, 0.05 * s, 1.38 * s))],
         [(0.1 * s, 0.09 * s), (0.18 * s, 0.14 * s), (0.22 * s, 0.16 * s)], "M_RobeBrown", segs=16, cap0=False, cap1=False, noise=0.04)
    mb.sphere(V((0, 0.15 * s, 1.42 * s)), (0.12 * s, 0.06 * s, 0.13 * s), "M_RobeBrown", segs=12, rings=8, noise=0.06, seed=2)
    B.build()

    def pray(t):
        ph = 2 * PI * t
        return add(base, {"head": (10 + 4 * math.sin(ph), 0, 0), "spine": (4 + 2 * math.sin(ph), 0, 0)})
    acts = base_human_actions(arm, base, H, extra={"talk": (talk_fn(base), 2.0), "pray": (pray, 4.0)})
    INFO["monk"] = dict(h=H, acts=acts, desc="Монах-каноник Вышеграда: коричневая ряса с опущенным капюшоном, тонзура, седина, "
                        "верёвочный пояс, широкие рукава, книга в красном переплёте у груди.", parts="HELD_book (hand.L); pray (цикл)")
    return root


def build_boatman():
    """Vltava boatman: linen shirt, rolled sleeves, leather jerkin, straw hat, punting pole."""
    H = 1.76
    s = H / 1.8
    root, col, arm, j = start("boatman", H, width=1.04)
    base = {"upper_arm.R": (-40, 10, 0), "forearm.R": (-60, 0, 0), "upper_arm.L": (-60, -15, 0), "forearm.L": (-35, 0, 0)}
    set_base(arm, base)
    B = C.Body("boatman", arm, col)
    g = grip_of(arm, "R")
    mb = B.separate("HELD_pole", ["hand.R"], 6)
    mb.push(posed_to_rest(arm, "hand.R") @ Matrix.Translation(g) @ rot_to((0.08, 0.25, -1.0)))
    mb.rod((0, 0, -2.6), (0, 0, 1.2), 0.022, "M_WoodLight", segs=8)
    mb.pop()
    legs(B, j, s, "M_WoolBrown", r=1.02, boots="M_LeatherC", boot_top=0.55)
    torso(B, s, "M_Linen", w=1.04)
    torso(B, s, "M_LeatherC", w=1.04, grow=0.012, z_from=1.06, z_to=1.44, cap=False)
    skirt(B, s, "M_Linen", 1.02, 0.82, (0.18, 0.13), (0.2, 0.15))
    belt_ring(B, s, 1.04, 0.187, 0.14, "M_Rope", 0.025)
    arms(B, j, s, "M_Linen", "M_Skin", r=1.08, forearm_mat="M_Skin")
    hc = head(B, j, s, "M_Skin", hair="M_HairBrown", beard="M_HairBrown", hair_style="short")
    mb = B.part(["head"], 4)                                     # straw hat
    loft(mb, [hc + V((0, 0.0, 0.05 * s)), hc + V((0, 0.0, 0.065 * s))], [(0.2 * s, 0.21 * s), (0.19 * s, 0.2 * s)], "M_Burlap", segs=18)
    loft(mb, [hc + V((0, 0.0, 0.06 * s)), hc + V((0, 0.0, 0.15 * s)), hc + V((0, 0.0, 0.17 * s))],
         [(0.1 * s, 0.11 * s), (0.08 * s, 0.085 * s), (0.02 * s, 0.02 * s)], "M_Burlap", segs=14)
    B.build()

    def punt(t):
        ph = 2 * PI * t
        k = 0.5 - 0.5 * math.cos(ph)
        return add(base, {"upper_arm.R": (-40 + 35 * k, 0, 0), "upper_arm.L": (-60 + 40 * k, 0, 0), "forearm.R": (-60 + 30 * k, 0, 0),
                          "spine": (8 + 18 * k, 0, 0), "thigh.L": (-15 * k, 0, 0), "shin.L": (20 * k, 0, 0), "thigh.R": (10 * k, 0, 0),
                          "_loc": {"hips": (0, 0.03 * k, -0.04 * k)}})
    acts = base_human_actions(arm, base, H, extra={"talk": (talk_fn(base), 2.0), "work": (punt, 3.0)})
    INFO["boatman"] = dict(h=H, acts=acts, desc="Лодочник с Влтавы: соломенная шляпа, льняная рубаха с закатанными рукавами, "
                           "кожаный жилет, верёвочный пояс, шест.", parts="HELD_pole (hand.R); work = отталкивается шестом (цикл)")
    return root


# ============================================================================= horse
HORSE_J = {
    "pelvis": (0, 0.75, 1.33), "chest_b": (0, 0.05, 1.36), "withers": (0, -0.62, 1.45),
    "neck1": (0, -0.66, 1.5), "neck2": (0, -0.96, 1.86), "poll": (0, -1.12, 2.08), "muzzle": (0, -1.52, 1.72),
    "tail0": (0, 0.88, 1.38), "tail1": (0, 1.02, 1.12), "tail2": (0, 1.06, 0.7),
}
for _x, _s in ((0.24, "L"), (-0.24, "R")):
    HORSE_J.update({
        f"f_sh.{_s}": (_x, -0.52, 1.18), f"f_el.{_s}": (_x, -0.56, 0.78), f"f_kn.{_s}": (_x, -0.53, 0.42),
        f"f_fe.{_s}": (_x, -0.54, 0.14), f"f_ho.{_s}": (_x, -0.6, 0.0),
        f"h_hp.{_s}": (_x * 1.08, 0.62, 1.2), f"h_st.{_s}": (_x * 1.08, 0.44, 0.78), f"h_hk.{_s}": (_x * 1.08, 0.66, 0.48),
        f"h_fe.{_s}": (_x * 1.08, 0.62, 0.14), f"h_ho.{_s}": (_x * 1.08, 0.56, 0.0),
    })
HORSE_BONES = [("root", None, None, None), ("pelvis", "pelvis", "chest_b", "root"), ("chest", "chest_b", "withers", "pelvis"),
               ("neck1", "neck1", "neck2", "chest"), ("neck2", "neck2", "poll", "neck1"), ("head", "poll", "muzzle", "neck2"),
               ("tail1", "tail0", "tail1", "pelvis"), ("tail2", "tail1", "tail2", "tail1")]
for _s in ("L", "R"):
    HORSE_BONES += [(f"f_upper.{_s}", f"f_sh.{_s}", f"f_el.{_s}", "chest"), (f"f_lower.{_s}", f"f_el.{_s}", f"f_kn.{_s}", f"f_upper.{_s}"),
                    (f"f_cannon.{_s}", f"f_kn.{_s}", f"f_fe.{_s}", f"f_lower.{_s}"), (f"f_hoof.{_s}", f"f_fe.{_s}", f"f_ho.{_s}", f"f_cannon.{_s}"),
                    (f"h_thigh.{_s}", f"h_hp.{_s}", f"h_st.{_s}", "pelvis"), (f"h_gaskin.{_s}", f"h_st.{_s}", f"h_hk.{_s}", f"h_thigh.{_s}"),
                    (f"h_cannon.{_s}", f"h_hk.{_s}", f"h_fe.{_s}", f"h_gaskin.{_s}"), (f"h_hoof.{_s}", f"h_fe.{_s}", f"h_ho.{_s}", f"h_cannon.{_s}")]


def horse_leg_pose(phase, A, lift, front):
    """One leg; phase in [0,1). Returns {bone: pose} deltas. Swing during first 40% of the cycle."""
    ph = 2 * PI * phase
    sw = math.sin(ph)
    swing = max(0.0, math.cos(ph))
    if front:
        return {"f_upper": (-A * sw, 0, 0), "f_lower": (lift * 0.4 * swing, 0, 0), "f_cannon": (lift * swing, 0, 0),
                "f_hoof": (-lift * 0.6 * swing + A * 0.3 * sw, 0, 0)}
    return {"h_thigh": (-A * sw, 0, 0), "h_gaskin": (-lift * 0.5 * swing, 0, 0), "h_cannon": (lift * 0.9 * swing, 0, 0),
            "h_hoof": (-lift * 0.4 * swing + A * 0.3 * sw, 0, 0)}


def horse_walk(t, A=16, lift=55, head_low=0.0, lean=0.0, nod=6):
    pose = {}
    for leg, off, front in (("L", 0.0, False), ("L", 0.25, True), ("R", 0.5, False), ("R", 0.75, True)):
        for b, v in horse_leg_pose((t + off) % 1.0, A, lift, front).items():
            pose[f"{b}.{leg}"] = v
    ph = 2 * PI * t
    pose["neck1"] = (head_low * 0.6 + nod * math.sin(2 * ph), 0, 0)
    pose["neck2"] = (head_low * 0.4, 0, 0)
    pose["head"] = (-head_low * 0.5 - nod * 0.5 * math.sin(2 * ph), 0, 0)
    pose["pelvis"] = (lean, 0, 2 * math.sin(ph))
    pose["tail1"] = (0, 0, 8 * math.sin(ph))
    pose["tail2"] = (0, 0, 10 * math.sin(ph - 0.6))
    pose["_loc"] = {"pelvis": (0, 0, -0.015 * abs(math.sin(2 * ph)) - 0.03 * abs(lean) / 10)}
    return pose


def build_horse():
    root, col = G.new_asset("horse", "characters")
    j = {k: V(v) for k, v in HORSE_J.items()}
    arm = C.make_armature("horse", j, HORSE_BONES, root, col)
    B = C.Body("horse", arm, col)
    M, D, H_ = "M_HorseCoat", "M_HorseHair", "M_Hoof"
    mb = B.part(["pelvis", "chest", "tail1"], 3)
    body = [(1.0, 0.0, 1.32, 0.15, 0.18), (0.9, 0.0, 1.32, 0.27, 0.3), (0.65, 0.0, 1.3, 0.34, 0.38), (0.2, 0.0, 1.26, 0.35, 0.42),
            (-0.25, 0.0, 1.26, 0.33, 0.42), (-0.55, 0.0, 1.3, 0.3, 0.4), (-0.72, 0.0, 1.36, 0.22, 0.32)]
    loft(mb, [V((x, y, z)) for y, x, z, _, _ in body], [(rx, rz) for *_, rx, rz in body], M, segs=18)
    mb = B.part(["chest", "neck1", "neck2"], 3)
    loft(mb, [V((0, -0.62, 1.46)), V((0, -0.82, 1.68)), V((0, -0.98, 1.9)), V((0, -1.1, 2.06))],
         [(0.19, 0.3), (0.15, 0.24), (0.12, 0.17), (0.105, 0.13)], M, segs=14, side_ref=(1, 0, 0))
    mb = B.part(["neck1", "neck2", "chest"], 3)  # mane
    loft(mb, [V((0, -0.58, 1.68)), V((0, -0.8, 1.88)), V((0, -0.98, 2.06)), V((0, -1.1, 2.18))],
         [(0.035, 0.09), (0.04, 0.1), (0.035, 0.09), (0.03, 0.07)], D, segs=8, noise=0.15, seed=4)
    mb = B.part(["head"], 4)
    loft(mb, [V((0, -1.1, 2.1)), V((0, -1.25, 1.98)), V((0, -1.42, 1.82)), V((0, -1.54, 1.7))],
         [(0.1, 0.12), (0.095, 0.11), (0.08, 0.085), (0.075, 0.075)], M, segs=12)
    mb.sphere(V((0, -1.52, 1.69)), (0.08, 0.08, 0.075), M, segs=10, rings=6)
    for sx in (-1, 1):
        mb.sphere(V((sx * 0.09, -1.2, 2.02)), (0.022, 0.03, 0.022), "M_EyeDark", segs=8, rings=5)
        loft(mb, [V((sx * 0.06, -1.08, 2.15)), V((sx * 0.08, -1.07, 2.3))], [(0.035, 0.02), (0.005, 0.005)], M, segs=6)
        mb.sphere(V((sx * 0.04, -1.6, 1.71)), 0.015, "M_EyeDark", segs=6, rings=4)
    loft(mb, [V((0, -1.1, 2.18)), V((0, -1.18, 2.08))], [(0.04, 0.02), (0.05, 0.015)], D, segs=6, noise=0.2)  # forelock
    mb = B.part(["tail1", "tail2"], 4)
    loft(mb, [j["tail0"], j["tail1"], j["tail1"].lerp(j["tail2"], 0.5), j["tail2"] + V((0, 0.02, -0.1))],
         [0.06, 0.08, 0.1, 0.05], D, segs=10, noise=0.2, seed=6)
    for X in ("L", "R"):
        sx = 1 if X == "L" else -1
        mb = B.part([f"f_upper.{X}", f"f_lower.{X}", "chest"], 5)
        loft(mb, [j[f"f_sh.{X}"] + V((0, 0, 0.08)), j[f"f_el.{X}"], j[f"f_el.{X}"].lerp(j[f"f_kn.{X}"], 0.5), j[f"f_kn.{X}"]],
             [(0.12, 0.16), (0.09, 0.11), (0.065, 0.075), (0.055, 0.065)], M, segs=10)
        mb = B.part([f"f_lower.{X}", f"f_cannon.{X}", f"f_hoof.{X}"], 5)
        loft(mb, [j[f"f_kn.{X}"], j[f"f_fe.{X}"] + V((0, 0, 0.05)), j[f"f_fe.{X}"]], [(0.05, 0.06), (0.042, 0.05), (0.05, 0.06)],
             M, segs=10)
        mb = B.part([f"f_cannon.{X}", f"f_hoof.{X}"], 5)  # feathering + hoof
        loft(mb, [j[f"f_fe.{X}"] + V((0, 0, 0.12)), j[f"f_fe.{X}"], j[f"f_ho.{X}"] + V((0, 0, 0.06))],
             [(0.05, 0.06), (0.075, 0.08), (0.08, 0.085)], D, segs=10, noise=0.15, seed=7, cap0=False)
        mb.cyl(j[f"f_ho.{X}"] + V((0, -0.01, 0)), 0.075, 0.07, H_, segs=10, r_top=0.065)
        mb = B.part([f"h_thigh.{X}", f"h_gaskin.{X}", "pelvis"], 5)
        loft(mb, [j[f"h_hp.{X}"] + V((0, 0.0, 0.12)), j[f"h_st.{X}"].lerp(j[f"h_hp.{X}"], 0.4), j[f"h_st.{X}"], j[f"h_hk.{X}"]],
             [(0.15, 0.22), (0.13, 0.17), (0.08, 0.1), (0.055, 0.07)], M, segs=10)
        mb = B.part([f"h_gaskin.{X}", f"h_cannon.{X}", f"h_hoof.{X}"], 5)
        loft(mb, [j[f"h_hk.{X}"], j[f"h_fe.{X}"] + V((0, 0, 0.05)), j[f"h_fe.{X}"]], [(0.05, 0.065), (0.042, 0.05), (0.05, 0.06)],
             M, segs=10)
        mb = B.part([f"h_cannon.{X}", f"h_hoof.{X}"], 5)
        loft(mb, [j[f"h_fe.{X}"] + V((0, 0, 0.12)), j[f"h_fe.{X}"], j[f"h_ho.{X}"] + V((0, 0, 0.06))],
             [(0.05, 0.06), (0.075, 0.08), (0.08, 0.085)], D, segs=10, noise=0.15, seed=8, cap0=False)
        mb.cyl(j[f"h_ho.{X}"] + V((0, -0.01, 0)), 0.075, 0.07, H_, segs=10, r_top=0.065)
    # harness: collar (hames), belly band, breeching strap, bridle
    mb = B.part(["chest", "neck1"], 3)
    loft(mb, [V((0, -0.6, 1.5)), V((0, -0.72, 1.62))], [(0.23, 0.36), (0.21, 0.32)], "M_LeatherC", segs=16, cap0=False, cap1=False)
    loft(mb, [V((0, -0.58, 1.48)), V((0, -0.6, 1.5))], [(0.25, 0.38), (0.25, 0.38)], "M_Brass", segs=16, cap0=False, cap1=False)
    mb = B.part(["chest", "pelvis"], 3)
    loft(mb, [V((0, -0.32, 1.26)), V((0, -0.24, 1.26))], [(0.345, 0.43), (0.348, 0.433)], "M_LeatherC", segs=18, cap0=False, cap1=False)
    for sx in (-1, 1):
        loft(mb, [V((sx * 0.3, -0.62, 1.33)), V((sx * 0.345, -0.1, 1.2)), V((sx * 0.3, 0.75, 1.15))], [0.022, 0.022, 0.022],
             "M_LeatherC", segs=5)
    mb = B.part(["pelvis"], 3)
    loft(mb, [V((0, 0.8, 1.22)), V((0, 0.86, 1.22))], [(0.29, 0.31), (0.25, 0.27)], "M_LeatherC", segs=16, cap0=False, cap1=False)
    mb = B.part(["head"], 4)
    for y, z, rx, rz in ((-1.2, 1.98, 0.105, 0.12), (-1.45, 1.77, 0.085, 0.09)):
        loft(mb, [V((0, y - 0.015, z + 0.012)), V((0, y + 0.015, z - 0.012))], [(rx, rz), (rx, rz)], "M_LeatherC", segs=14,
             cap0=False, cap1=False)
    for sx in (-1, 1):
        loft(mb, [V((sx * 0.105, -1.2, 1.98)), V((sx * 0.085, -1.45, 1.77))], [0.012, 0.012], "M_LeatherC", segs=5)
        with mb.at((sx * 0.085, -1.5, 1.72), rot_y=PI / 2):
            mb.torus(0.03, 0.007, "M_Iron", segs=10, tsegs=4)
    B.build()
    C.apply_pose(arm, {})
    acts = {}
    idle = lambda t: {"neck1": (3 * math.sin(2 * PI * t), 0, 0), "head": (-2 * math.sin(2 * PI * t), 0, 3 * math.sin(PI * t)),  # noqa
                      "tail1": (0, 0, 12 * math.sin(2 * PI * t)), "tail2": (0, 0, 15 * math.sin(2 * PI * t - 0.8)),
                      "chest": (0.6 * math.sin(2 * PI * t), 0, 0), "h_thigh.R": (-3, 0, 0), "h_cannon.R": (12, 0, 0),
                      "h_hoof.R": (-12, 0, 0)}
    C.make_action(arm, "idle", 3.0, idle); acts["idle"] = 3.0
    C.make_action(arm, "walk", 1.2, lambda t: horse_walk(t)); acts["walk"] = 1.2
    C.make_action(arm, "pull", 1.5, lambda t: horse_walk(t, A=14, lift=45, head_low=22, lean=4, nod=8)); acts["pull"] = 1.5
    INFO["horse"] = dict(h=1.7, acts=acts, desc="Рабочая (тяжеловозная) лошадь: гнедая, тёмные грива, хвост и щётки на ногах, "
                         "хомут с латунной обкладкой, подпруга, постромки, уздечка с кольцами.",
                         parts="высота в холке ≈1.7 м, до ушей ≈2.3 м; pull = тянет телегу (опущенная голова, наклон)")
    return root


# ============================================================================= previews
def _solo(arm, name):
    for t in arm.animation_data.nla_tracks:
        t.mute = t.name != name


def _tight_camera(root, fov=32.0, view=(0.5, -1.0, 0.12), pad=1.25):
    import lib_render as R
    sc = bpy.context.scene
    cam = R._get("_preview_cam", "CAM")
    sc.camera = cam
    cam.data.lens_unit = "FOV"
    cam.data.angle = math.radians(fov)
    mn, mx = R.bounds(root)
    size = max(mx.z - mn.z, (mx.y - mn.y) * 0.9, (mx.x - mn.x) * 0.9)
    c = V((0, (mn.y + mx.y) / 2, size * 0.48))
    d = V(view).normalized()
    dist = size * pad / 2 / math.tan(math.radians(fov) / 2)
    cam.location = c + d * dist
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()


def render_char_previews(root, arm, actions, n=5):
    import lib_render as R
    sc = bpy.context.scene
    _solo(arm, "idle")
    sc.frame_set(0)
    R.render_asset(root, out_name=f"char_{root.name}", view=(0.45, -1.0, 0.18), fov=30)
    vl = bpy.context.view_layer
    for c in vl.layer_collection.children:
        c.exclude = c.name != root.users_collection[0].name
    sc.render.resolution_x = sc.render.resolution_y = 400
    try:
        sc.eevee.taa_render_samples = 16
    except Exception:
        pass
    _tight_camera(root)
    files = []
    for an in actions:
        tr = arm.animation_data.nla_tracks.get(an)
        if not tr:
            continue
        _solo(arm, an)
        strip = tr.strips[0]
        length = strip.frame_end - strip.frame_start
        for k in range(n):
            sc.frame_set(int(round(strip.frame_start + length * k / n)))
            p = os.path.join(R.PREVIEW_DIR, "_frames", f"{root.name}_{an}_{k}.png")
            sc.render.filepath = p
            bpy.ops.render.render(write_still=True)
            files.append(p)
    for t in arm.animation_data.nla_tracks:
        t.mute = False
    for c in vl.layer_collection.children:
        c.exclude = False
    sc.frame_set(0)
    return files


CHARS = {
    "vaclav": build_vaclav, "alchemist": build_alchemist, "golem": build_golem, "skeleton": build_skeleton,
    "butcher": build_butcher, "market_woman": build_market_woman, "merchant": build_merchant, "guard": build_guard,
    "beggar": build_beggar, "child_boy": lambda: build_child("child_boy", False), "child_girl": lambda: build_child("child_girl", True),
    "horse": build_horse, "knight": build_knight, "monk": build_monk, "boatman": build_boatman,
}
STRIPS = {"vaclav": ["walk", "run", "attack", "attack2", "block", "dodge", "jump", "throw", "death"], "alchemist": ["walk", "attack"],
          "golem": ["walk", "attack"], "skeleton": ["walk", "attack"], "guard": ["walk", "attack"], "horse": ["walk", "pull"],
          "butcher": ["work"], "market_woman": ["walk"], "merchant": ["talk"], "beggar": ["beg"], "child_boy": ["run"],
          "child_girl": ["walk"], "knight": ["spar", "attack"], "monk": ["pray", "walk"], "boatman": ["work"]}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only = argv[argv.index("--only") + 1].split(",") if "--only" in argv else None
    render = "--no-render" not in argv
    G.reset_scene()
    bpy.context.scene.render.fps = C.FPS
    roots = []
    for name, fn in CHARS.items():
        if only and name not in only:
            continue
        print("BUILD", name)
        roots.append(fn())
    bpy.context.view_layer.update()
    anim_kw = dict(export_animations=True, export_animation_mode="NLA_TRACKS", export_skins=True, export_force_sampling=True,
                   export_morph=False)
    for r in roots:
        G.export_asset(r, OUT, anim_kw)
    import json
    with open(os.path.join(G.BLENDER_DIR, "characters_info.json" if not only else "characters_info_partial.json"), "w",
              encoding="utf-8") as f:
        json.dump(INFO, f, ensure_ascii=False, indent=1)
    if render:
        import glob
        for r in roots:
            arm = next(o for o in G.descendants(r) if o.type == "ARMATURE")
            files = render_char_previews(r, arm, STRIPS.get(r.name, []))
            if files:
                out = os.path.join(G.PROJECT, "renders", "previews", f"char_{r.name}_anim.png")
                make_sheet(out, files, 5)
        for f in glob.glob(os.path.join(G.PROJECT, "renders", "previews", "_frames", "*.png")):
            os.remove(f)
        for n in ("_preview_ground", "_preview_cam", "_preview_sun"):
            ob = bpy.data.objects.get(n)
            if ob:
                bpy.data.objects.remove(ob)
    if not only:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(G.BLENDER_DIR, "characters.blend"))
    print("DONE characters")


def make_sheet(out, files, cols, cell=240):
    import numpy as np
    rows = (len(files) + cols - 1) // cols
    sheet = np.zeros((rows * cell, cols * cell, 4), np.float32)
    sheet[..., 3] = 1
    for k, f in enumerate(files):
        img = bpy.data.images.load(f)
        w, h = img.size
        px = np.array(img.pixels[:], np.float32).reshape(h, w, 4)
        ys = (np.arange(cell) * h / cell).astype(int)
        xs = (np.arange(cell) * w / cell).astype(int)
        r, c = divmod(k, cols)
        sheet[(rows - 1 - r) * cell:(rows - r) * cell, c * cell:(c + 1) * cell] = px[ys][:, xs]
        bpy.data.images.remove(img)
    o = bpy.data.images.new("sheet", cols * cell, rows * cell, alpha=True)
    o.pixels.foreach_set(sheet.ravel())
    o.filepath_raw = out
    o.file_format = "PNG"
    o.save()
    bpy.data.images.remove(o)


if __name__ == "__main__":
    main()
