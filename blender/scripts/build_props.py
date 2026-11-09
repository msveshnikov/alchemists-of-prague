"""Build all Old Town Square props (market, smithy, lights, furniture, vegetation).

blender -b --factory-startup -P build_props.py [-- --only barrel,cart] [--no-render]
Outputs: blender/props.blend, assets/props/*.gltf, renders/previews/*.png
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import lib_geo as G  # noqa: E402
from lib_geo import MB  # noqa: E402

OUT = os.path.join(G.PROJECT, "assets", "props")
PI = math.pi


# ----------------------------------------------------------------------------- reusable sub-parts
def barrel_parts(mb, h=0.95, r=0.3, bulge=0.05):
    prof = []
    for k in range(9):
        t = k / 8
        prof.append((r + bulge * math.sin(PI * t), t * h))
    mb.lathe(prof, "M_WoodLight", segs=16, cap_mat="M_WoodDark")
    for t in (0.1, 0.3, 0.7, 0.9):
        rr = r + bulge * math.sin(PI * t) + 0.012
        with mb.at((0, 0, t * h - 0.025)):
            mb.lathe([(rr, 0), (rr, 0.05)], "M_Iron", segs=16, cap_bottom=False, cap_top=False)


def crate_parts(mb, s=(0.7, 0.55, 0.5), open_top=False):
    x, y, z = s
    if open_top:
        t = 0.03
        mb.box((-x / 2, -y / 2, 0), (x / 2, y / 2, t), "M_WoodLight")
        mb.box((-x / 2, -y / 2, 0), (x / 2, -y / 2 + t, z), "M_WoodLight")
        mb.box((-x / 2, y / 2 - t, 0), (x / 2, y / 2, z), "M_WoodLight")
        mb.box((-x / 2, -y / 2, 0), (-x / 2 + t, y / 2, z), "M_WoodLight")
        mb.box((x / 2 - t, -y / 2, 0), (x / 2, y / 2, z), "M_WoodLight")
    else:
        mb.box((-x / 2, -y / 2, 0), (x / 2, y / 2, z), "M_WoodLight")
    e = 0.045
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((sx * x / 2 - e, sy * y / 2 - e, 0), (sx * x / 2 + e, sy * y / 2 + e, z), "M_Timber")
    for zz in (0.0, z - 0.06):
        mb.box((-x / 2 - 0.01, -y / 2 - 0.02, zz), (x / 2 + 0.01, -y / 2 + 0.01, zz + 0.06), "M_Timber")
        mb.box((-x / 2 - 0.01, y / 2 - 0.01, zz), (x / 2 + 0.01, y / 2 + 0.02, zz + 0.06), "M_Timber")


def produce_fill(mb, xr, yr, z, kind, seed=0, layers=1):
    rnd = random.Random(seed)
    spec = {"apple": ("M_Apple", 0.045, 0.085), "cabbage": ("M_Cabbage", 0.1, 0.19), "onion": ("M_Onion", 0.04, 0.08),
            "pumpkin": ("M_Pumpkin", 0.12, 0.22), "carrot": ("M_Carrot", 0.03, 0.07)}[kind]
    mat, rad, step = spec
    nx = max(1, int((xr[1] - xr[0]) / step))
    ny = max(1, int((yr[1] - yr[0]) / step))
    for L in range(layers):
        for i in range(nx):
            for j in range(ny):
                if L and rnd.random() < 0.4:
                    continue
                x = xr[0] + (i + 0.5) * (xr[1] - xr[0]) / nx + rnd.uniform(-0.01, 0.01)
                y = yr[0] + (j + 0.5) * (yr[1] - yr[0]) / ny + rnd.uniform(-0.01, 0.01)
                zz = z + rad * 0.9 + L * rad * 1.3
                if kind == "carrot":
                    mb.rod((x - 0.06, y, zz), (x + 0.08, y + rnd.uniform(-0.03, 0.03), zz), 0.025, mat, segs=5, r1=0.005)
                elif kind == "pumpkin":
                    mb.sphere((x, y, zz), (rad, rad, rad * 0.75), mat, segs=10, rings=6, noise=0.06, seed=i * 7 + j)
                else:
                    mb.sphere((x, y, zz), rad * rnd.uniform(0.9, 1.1), mat, segs=8, rings=5, noise=0.05, seed=i * 7 + j)


def sack_parts(mb, h=0.7, r=0.28, seed=0):
    mb.sphere((0, 0, h * 0.42), (r, r * 0.9, h * 0.45), "M_Burlap", segs=12, rings=8, noise=0.07, seed=seed, z_cut=0.0)
    mb.lathe([(r * 0.3, h * 0.82), (r * 0.18, h * 0.9), (r * 0.25, h * 1.0)], "M_Burlap", segs=10)
    mb.lathe([(r * 0.2, h * 0.86), (r * 0.2, h * 0.9)], "M_Rope", segs=10)


def loaf(mb, x, y, z, s=1.0, ang=0.0, seed=0):
    with mb.at((x, y, z), rot_z=ang):
        mb.sphere((0, 0, 0.05 * s), (0.14 * s, 0.08 * s, 0.07 * s), "M_Bread", segs=10, rings=6, noise=0.04, seed=seed, z_cut=0.0)


def jug(mb, x, y, z, s=1.0, mat="M_Pottery", kind=0):
    with mb.at((x, y, z), scale=s):
        if kind == 0:
            mb.lathe([(0.07, 0), (0.12, 0.08), (0.13, 0.16), (0.09, 0.26), (0.05, 0.32), (0.06, 0.36)], mat, segs=12)
        elif kind == 1:
            mb.lathe([(0.08, 0), (0.15, 0.06), (0.16, 0.14), (0.13, 0.2), (0.14, 0.22)], mat, segs=14)
        else:
            mb.lathe([(0.05, 0), (0.09, 0.05), (0.1, 0.18), (0.04, 0.3), (0.035, 0.42), (0.05, 0.44)], mat, segs=12)


def sword(mb, base, ang=0.0, length=1.0, tilt=0.0):
    with mb.at(base, rot_z=ang, rot_y=tilt):
        mb.prism([(-0.025, 0.0), (0.025, 0.0), (0.02, length * 0.72), (0.0, length * 0.78), (-0.02, length * 0.72)],
                 -0.006, 0.006, "M_Steel")
        mb.box((-0.12, -0.02, -0.02), (0.12, 0.02, 0.02), "M_Iron")
        mb.rod((0, 0, -0.02), (0, 0, -0.2), 0.016, "M_Leather", segs=6)
        mb.sphere((0, 0, -0.22), 0.03, "M_Iron", segs=6, rings=4)


def spear(mb, base, h=2.4, ang=0.0, tilt=0.0, halberd=False):
    with mb.at(base, rot_z=ang, rot_y=tilt):
        mb.rod((0, 0, 0), (0, 0, h), 0.018, "M_Timber", segs=6)
        mb.prism([(-0.035, h), (0.035, h), (0.0, h + 0.3)], -0.006, 0.006, "M_Steel")
        if halberd:
            mb.prism([(0.0, h - 0.25), (0.22, h - 0.32), (0.25, h - 0.1), (0.0, h - 0.05)], -0.006, 0.006, "M_Steel")


def shield(mb, c, ang=0.0, lean=0.0, s=1.0):
    """Heater shield with lion on the front (-Y)."""
    with mb.at(c, rot_z=ang, rot_x=lean, scale=s):
        pts = [(-0.3, 0.35), (0.3, 0.35), (0.3, 0.05)] + \
              [(0.3 * math.cos(t), -0.05 - 0.4 * math.sin(t)) for t in [k * PI / 2 / 6 for k in range(1, 6)]] + [(0, -0.45)] + \
              [(-0.3 * math.sin(t), -0.05 - 0.4 * math.cos(t)) for t in [k * PI / 2 / 6 for k in range(1, 6)]] + [(-0.3, 0.05)]
        mb.prism(pts, -0.025, 0.025, "M_WoodDark", cap="M_WoodDark")
        mb.face([(x, -0.03, z) for x, z in reversed(pts)], "M_Shield", uv="fit")
        mb.sphere((0, -0.035, 0.0), (0.07, 0.04, 0.07), "M_Steel", segs=8, rings=5)


def fire(mb, c, s=1.0, n=5, seed=0):
    rnd = random.Random(seed)
    for i in range(n):
        a = 2 * PI * i / n
        r = 0.12 * s
        x, y = c[0] + r * math.cos(a) * rnd.uniform(0.3, 1), c[1] + r * math.sin(a) * rnd.uniform(0.3, 1)
        mb.cyl((x, y, c[2]), 0.09 * s, rnd.uniform(0.3, 0.55) * s, "M_Fire", segs=6, r_top=0.0, cap=False)
    mb.cyl((c[0], c[1], c[2]), 0.12 * s, 0.7 * s, "M_Fire", segs=6, r_top=0.0, cap=False)


def logs(mb, c, s=1.0, n=4):
    for i in range(n):
        a = PI * i / n
        mb.rod((c[0] - 0.3 * s * math.cos(a), c[1] - 0.3 * s * math.sin(a), c[2] + 0.05),
               (c[0] + 0.3 * s * math.cos(a), c[1] + 0.3 * s * math.sin(a), c[2] + 0.12), 0.05 * s, "M_Bark", segs=6)


def lantern_head(mb, c, s=1.0):
    x, y, z = c
    with mb.at((x, y, z), scale=s):
        mb.cbox((0, 0, 0.02), (0.26, 0.26, 0.04), "M_Iron")
        mb.cbox((0, 0, 0.2), (0.2, 0.2, 0.32), "M_LanternGlass")
        for sx in (-1, 1):
            for sy in (-1, 1):
                mb.cbox((sx * 0.11, sy * 0.11, 0.2), (0.025, 0.025, 0.34), "M_Iron")
        mb.pyramid(0, 0, 0.36, 0.3, 0.3, 0.16, "M_Iron")
        mb.rod((0, 0, 0.5), (0, 0, 0.6), 0.012, "M_Iron", segs=4)


# ----------------------------------------------------------------------------- props
def P(name):
    root, col = G.new_asset(name, "props")
    return root, col, MB()


def finish(root, col, mb, colmode="auto"):
    mb.build(root.name + "_mesh", root, col)
    bpy.context.view_layer.update()
    if colmode == "auto":
        G.auto_collision(root, col)
    return root


def build_barrel():
    root, col, mb = P("barrel")
    barrel_parts(mb)
    return finish(root, col, mb)


def build_barrel_small():
    root, col, mb = P("barrel_small")
    barrel_parts(mb, 0.6, 0.2, 0.035)
    return finish(root, col, mb)


def build_crate():
    root, col, mb = P("crate")
    crate_parts(mb)
    return finish(root, col, mb)


def build_crate_produce():
    root, col, mb = P("crate_produce")
    crate_parts(mb, (0.7, 0.5, 0.32), open_top=True)
    produce_fill(mb, (-0.32, 0.32), (-0.22, 0.22), 0.12, "apple", 1, layers=2)
    return finish(root, col, mb)


def build_sack():
    root, col, mb = P("sack")
    sack_parts(mb)
    return finish(root, col, mb)


def build_basket():
    root, col, mb = P("basket")
    mb.lathe([(0.17, 0.0), (0.22, 0.12), (0.25, 0.25)], "M_WoodLight", segs=16, cap_top=False)
    mb.lathe([(0.24, 0.25), (0.16, 0.0)], "M_Timber", segs=16, cap_bottom=False, cap_top=False)
    with mb.at((0, 0, 0.25)):
        mb.torus(0.25, 0.018, "M_Timber", segs=18, tsegs=5)
    with mb.at((0, 0, 0.25), rot_x=PI / 2):
        mb.torus(0.24, 0.014, "M_Timber", segs=18, tsegs=5)
    produce_fill(mb, (-0.15, 0.15), (-0.15, 0.15), 0.12, "apple", 3)
    return finish(root, col, mb)


def build_cart():
    root, col, mb = P("cart")
    W, L, zb = 1.4, 2.6, 0.75
    mb.box((-W / 2, -L / 2, zb), (W / 2, L / 2, zb + 0.08), "M_WoodLight")
    for sx in (-1, 1):
        mb.box((sx * W / 2 - 0.04, -L / 2, zb + 0.08), (sx * W / 2 + 0.04, L / 2, zb + 0.45), "M_WoodLight")
        for y in (-L / 2 + 0.05, 0, L / 2 - 0.05):
            mb.box((sx * W / 2 - 0.06, y - 0.05, zb - 0.05), (sx * W / 2 + 0.06, y + 0.05, zb + 0.55), "M_Timber")
    mb.box((-W / 2, L / 2 - 0.04, zb + 0.08), (W / 2, L / 2 + 0.04, zb + 0.45), "M_WoodLight")
    mb.box((-W / 2, -L / 2 - 0.04, zb + 0.08), (W / 2, -L / 2 + 0.04, zb + 0.3), "M_WoodLight")
    for sx in (-1, 1):
        mb.box((sx * 0.45 - 0.05, -L / 2 - 2.2, zb - 0.1), (sx * 0.45 + 0.05, L / 2 - 0.3, zb - 0.0), "M_Timber")   # shafts
    mb.rod((-W / 2 - 0.25, 0.2, 0.62), (W / 2 + 0.25, 0.2, 0.62), 0.05, "M_Timber", segs=8)                  # axle
    for sx in (-1, 1):
        x = sx * (W / 2 + 0.15)
        with mb.at((x, 0.2, 0.62), rot_y=PI / 2):
            mb.torus(0.58, 0.045, "M_Timber", segs=24, tsegs=6, smooth=True)
            mb.cyl((0, 0, -0.1), 0.1, 0.2, "M_Timber", segs=10)
            for k in range(8):
                a = 2 * PI * k / 8
                mb.rod((0.08 * math.cos(a), 0.08 * math.sin(a), 0), (0.55 * math.cos(a), 0.55 * math.sin(a), 0), 0.025, "M_Timber", segs=5)
            mb.torus(0.61, 0.02, "M_Iron", segs=24, tsegs=4)
    # load: sacks and pumpkins / cabbages, as on the concept art
    with mb.at((-0.3, 0.6, zb + 0.08)):
        sack_parts(mb, 0.6, 0.24, 1)
    with mb.at((0.3, 0.7, zb + 0.08), rot_z=0.6):
        sack_parts(mb, 0.55, 0.23, 2)
    produce_fill(mb, (-0.6, 0.6), (-1.2, 0.2), zb + 0.08, "pumpkin", 3, layers=2)
    produce_fill(mb, (-0.6, 0.6), (0.95, 1.25), zb + 0.08, "cabbage", 4)
    G.marker("MARK_horse", (0, -L / 2 - 1.7, 0), root, col)
    return finish(root, col, mb)


def build_spit_roast():
    root, col, mb = P("spit_roast")
    mb.box((-0.85, -0.5, 0), (0.85, 0.5, 0.45), "M_StoneRough")
    mb.box((-0.75, -0.4, 0.45), (0.75, 0.4, 0.5), "M_Coals")
    logs(mb, (-0.25, 0, 0.47), 1.0, 3)
    logs(mb, (0.3, 0, 0.47), 0.9, 3)
    fire(mb, (-0.2, 0, 0.5), 0.9, 5, 1)
    fire(mb, (0.3, 0.05, 0.5), 0.8, 4, 2)
    for x in (-0.95, 0.95):
        mb.rod((x, 0, 0), (x, 0, 1.15), 0.035, "M_Iron", segs=6)
        mb.rod((x, 0, 1.0), (x - 0.12, 0, 1.25), 0.025, "M_Iron", segs=5)
        mb.rod((x, 0, 1.0), (x + 0.12, 0, 1.25), 0.025, "M_Iron", segs=5)
    mb.box((-0.9, -0.55, 0.45), (0.9, -0.5, 0.52), "M_Iron")
    root_mesh = finish(root, col, mb, colmode=None)
    # rotating part: rod + pig, origin on the rod axis -> rotate around local X in game
    sp = MB()
    zr = 1.12
    sp.rod((-1.15, 0, zr), (1.15, 0, zr), 0.02, "M_Iron", segs=6)
    sp.rod((1.15, 0, zr), (1.15, 0, zr - 0.25), 0.02, "M_Iron", segs=5)
    sp.rod((1.15, 0, zr - 0.25), (1.25, 0, zr - 0.25), 0.03, "M_Timber", segs=5)
    sp.sphere((0, 0, zr), (0.5, 0.2, 0.21), "M_Meat", segs=14, rings=8, noise=0.03, seed=3)
    sp.sphere((-0.52, 0, zr + 0.02), (0.14, 0.11, 0.12), "M_Meat", segs=10, rings=6)
    sp.rod((-0.62, 0, zr), (-0.72, 0, zr - 0.02), 0.05, "M_Meat", segs=6, r1=0.035)
    for sx, sy in ((-0.3, -1), (-0.3, 1), (0.32, -1), (0.32, 1)):
        sp.rod((sx, sy * 0.1, zr - 0.1), (sx + (0.25 if sx > 0 else -0.25), sy * 0.12, zr - 0.05), 0.04, "M_Meat", segs=6, r1=0.025)
    spob = sp.build("ANIM_spit", root, col)
    G.set_origin(spob, (0, 0, zr))
    spob["anim"] = "rotate_x"
    G.point_light("LIGHT_fire", (0, 0, 0.9), root, col, energy=150, color=(1.0, 0.55, 0.22), distance=10)
    G.marker("MARK_cook", (0, 0.95, 0), root, col)
    mc = MB()
    mc.box((-0.85, -0.5, 0), (0.85, 0.5, 1.2), "M_Trim")
    G.finish_collision(mc, "spit_roast", root, col)
    return root


def build_weapon_rack():
    root, col, mb = P("weapon_rack")
    for x in (-0.9, 0.9):
        mb.box((x - 0.05, -0.25, 0), (x + 0.05, -0.15, 1.6), "M_Timber")
        mb.box((x - 0.05, 0.15, 0), (x + 0.05, 0.25, 1.6), "M_Timber")
        mb.box((x - 0.05, -0.3, 0), (x + 0.05, 0.3, 0.08), "M_Timber")
    mb.box((-0.95, -0.1, 1.3), (0.95, 0.1, 1.38), "M_WoodLight")
    mb.box((-0.95, -0.3, 0.25), (0.95, 0.3, 0.3), "M_WoodLight")
    for k in range(6):
        x = -0.75 + k * 0.3
        sword(mb, (x, 0.0, 0.33), ang=0.0, length=1.0 + 0.05 * (k % 2), tilt=0.0)
    for k in range(4):
        spear(mb, (-0.8 + k * 0.5, 0.15, 0.3), 2.3, tilt=0.05 * (k - 1.5), halberd=k % 2 == 1)
    shield(mb, (0.0, -0.33, 0.8), lean=-0.15)
    return finish(root, col, mb)


def build_anvil():
    root, col, mb = P("anvil")
    mb.cyl((0, 0, 0), 0.32, 0.55, "M_Bark", segs=12, cap_mat="M_WoodLight", smooth=True)
    prof = [(-0.18, 0.55), (0.18, 0.55), (0.14, 0.62), (0.08, 0.66), (0.08, 0.74), (0.22, 0.78), (0.24, 0.86),
            (-0.22, 0.86), (-0.45, 0.84), (-0.24, 0.78), (-0.08, 0.74), (-0.08, 0.66), (-0.14, 0.62)]
    with mb.at((0, 0, 0)):
        mb.prism(prof, -0.11, 0.11, "M_Iron")
    root = finish(root, col, mb)
    for o in root.children:
        if o.name == "anvil_mesh":
            o.name = "INT_anvil"
            o["interactive"] = "smith"
    G.marker("MARK_smith", (0.2, 0.75, 0), root, col)
    return root


def build_forge():
    root, col, mb = P("forge")
    mb.box((-0.75, -0.55, 0), (0.75, 0.55, 0.85), "M_StoneRough")
    mb.box((-0.6, -0.4, 0.85), (0.6, 0.4, 0.9), "M_Coals")
    mb.box((-0.75, 0.4, 0.85), (0.75, 0.55, 1.3), "M_StoneRough")
    mb.pyramid(0, 0.15, 1.9, 1.5, 0.8, 0.9, "M_StoneRough", w_top=0.45, d_top=0.45)
    for sx in (-1, 1):
        mb.box((sx * 0.7 - 0.05, -0.1, 0.85), (sx * 0.7 + 0.05, 0.0, 1.9), "M_Iron")
    mb.box((-0.75, -0.25, 1.8), (0.75, 0.55, 1.9), "M_StoneRough")
    mb.box((-0.22, -0.07, 2.8), (0.22, 0.37, 3.6), "M_StoneRough")
    fire(mb, (0, 0, 0.9), 0.5, 4, 5)
    # bellows
    with mb.at((0.95, 0.0, 0.7), rot_z=PI / 2):
        mb.prism([(-0.35, 0.0), (0.25, -0.12), (0.35, 0.0), (0.25, 0.12)], -0.15, 0.15, "M_Leather", plane="xz")
        mb.rod((0.3, 0, 0), (0.6, 0, -0.05), 0.02, "M_Iron", segs=5)
    G.point_light("LIGHT_forge", (0, -0.2, 1.2), root, col, energy=120, color=(1.0, 0.45, 0.15), distance=8)
    return finish(root, col, mb)


def build_blacksmith_shed():
    root, col, mb = P("blacksmith_shed")
    W, D, hf, hb = 4.6, 3.4, 2.5, 3.3
    for x in (-W / 2, W / 2):
        mb.box((x - 0.1, -D / 2 - 0.1, 0), (x + 0.1, -D / 2 + 0.1, hf), "M_Timber")
        mb.box((x - 0.1, D / 2 - 0.1, 0), (x + 0.1, D / 2 + 0.1, hb), "M_Timber")
    mb.box((0 - 0.1, -D / 2 - 0.1, 0), (0.1, -D / 2 + 0.1, hf), "M_Timber")
    mb.box((-W / 2 - 0.1, -D / 2 - 0.1, hf - 0.2), (W / 2 + 0.1, -D / 2 + 0.1, hf), "M_Timber")
    mb.box((-W / 2 - 0.1, D / 2 - 0.1, hb - 0.2), (W / 2 + 0.1, D / 2 + 0.1, hb), "M_Timber")
    for x in (-W / 2, W / 2):
        mb.box((x - 0.1, -D / 2, hf - 0.2), (x + 0.1, D / 2, hf + (hb - hf) * 0.5), "M_Timber")
    # back + side plank walls
    mb.box((-W / 2, D / 2 - 0.05, 0), (W / 2, D / 2 + 0.05, hb - 0.2), "M_WoodDark")
    with mb.at((W / 2, 0, 0), rot_z=PI / 2):
        mb.prism([(-D / 2 + 0.8, 0), (D / 2, 0), (D / 2, hb - 0.2), (-D / 2 + 0.8, hf + 0.25)], -0.05, 0.05, "M_WoodDark")
    # lean-to shingle roof
    t = 0.1
    o = 0.4
    ang = math.atan2(hb - hf, D)
    zf, zb_ = hf - o * math.tan(ang), hb + o * math.tan(ang)
    with mb.at((0, 0, 0), rot_z=PI / 2):
        mb.prism([(-D / 2 - o, zf), (D / 2 + o, zb_), (D / 2 + o, zb_ + t), (-D / 2 - o, zf + t)], -W / 2 - 0.3, W / 2 + 0.3,
                 "M_Shingle", side_mats=["M_Timber", "M_Timber", "M_Shingle", "M_Timber"])
    # tools hanging on back wall
    for k in range(5):
        x = -1.6 + k * 0.4
        mb.rod((x, D / 2 - 0.1, 1.9), (x, D / 2 - 0.12, 1.3), 0.02, "M_Timber", segs=5)
        mb.box((x - 0.06, D / 2 - 0.16, 1.18), (x + 0.06, D / 2 - 0.08, 1.32), "M_Iron")
    mb.box((1.0, D / 2 - 0.6, 0), (2.1, D / 2 - 0.1, 0.8), "M_WoodLight")   # workbench
    mb.box((1.0, D / 2 - 0.6, 0.8), (2.1, D / 2 - 0.1, 0.86), "M_Timber")
    with mb.at((1.85, -0.9, 0)):
        barrel_parts(mb, 0.7, 0.26, 0.03)
    mb.build("blacksmith_shed_mesh", root, col)
    G.marker("MARK_forge", (-1.2, 0.8, 0), root, col)
    G.marker("MARK_anvil", (0.4, -0.2, 0), root, col)
    G.marker("MARK_smith", (0.4, 0.6, 0), root, col)
    mc = MB()
    for x in (-W / 2, 0.0, W / 2):
        mc.box((x - 0.1, -D / 2 - 0.1, 0), (x + 0.1, -D / 2 + 0.1, hf), "M_Trim")
    mc.box((-W / 2, D / 2 - 0.05, 0), (W / 2, D / 2 + 0.05, hb), "M_Trim")
    mc.box((W / 2 - 0.05, -D / 2, 0), (W / 2 + 0.05, D / 2, hb), "M_Trim")
    mc.box((1.0, D / 2 - 0.6, 0), (2.1, D / 2, 0.86), "M_Trim")
    G.finish_collision(mc, "blacksmith_shed", root, col)
    return root


def build_street_lantern():
    root, col, mb = P("street_lantern")
    mb.cyl((0, 0, 0), 0.16, 0.25, "M_StoneRough", segs=8, smooth=False)
    mb.cyl((0, 0, 0.25), 0.06, 2.9, "M_Iron", segs=8)
    mb.cyl((0, 0, 3.15), 0.09, 0.08, "M_Iron", segs=8)
    mb.rod((0, 0, 3.0), (0, -0.55, 3.0), 0.025, "M_Iron", segs=5)
    mb.rod((0, -0.2, 2.75), (0, -0.55, 3.0), 0.018, "M_Iron", segs=5)
    mb.rod((0, -0.55, 3.0), (0, -0.55, 2.85), 0.01, "M_Iron", segs=4)
    lantern_head(mb, (0, -0.55, 2.4), 1.0)
    mb.pyramid(0, 0, 3.23, 0.12, 0.12, 0.25, "M_Iron")
    G.point_light("LIGHT_lantern", (0, -0.55, 2.6), root, col, energy=90, color=(1.0, 0.68, 0.35), distance=12)
    return finish(root, col, mb)


def build_wall_torch():
    """Origin = wall base (ground, wall plane y=0); torch mounted at 2.2 m, sticking out to -Y."""
    root, col, mb = P("wall_torch")
    mb.push(G.Matrix.Translation((0, 0, 2.2)))
    mb.box((-0.07, 0.0, -0.15), (0.07, 0.05, 0.2), "M_Iron")
    mb.rod((0, 0.02, 0.0), (0, -0.35, 0.3), 0.022, "M_Iron", segs=6)
    with mb.at((0, -0.38, 0.28)):
        mb.lathe([(0.07, 0), (0.09, 0.12), (0.05, 0.12)], "M_Iron", segs=8, cap_top=False)
    mb.rod((0, -0.38, 0.1), (0, -0.38, 0.5), 0.035, "M_Timber", segs=6, r1=0.05)
    mb.sphere((0, -0.38, 0.5), 0.06, "M_Burlap", segs=8, rings=5)
    fire(mb, (0, -0.38, 0.5), 0.55, 3, 7)
    mb.pop()
    G.point_light("LIGHT_torch", (0, -0.45, 3.0), root, col, energy=70, color=(1.0, 0.55, 0.22), distance=9)
    mb.build("wall_torch_mesh", root, col)
    G.marker("MARK_mount", (0, 0, 2.2), root, col)
    return root


def build_hand_lantern():
    root, col, mb = P("hand_lantern")
    lantern_head(mb, (0, 0, 0), 0.75)
    with mb.at((0, 0, 0.42), rot_x=PI / 2):
        mb.torus(0.09, 0.008, "M_Iron", segs=12, tsegs=4)
    G.point_light("LIGHT_hand_lantern", (0, 0, 0.17), root, col, energy=25, color=(1.0, 0.7, 0.4), distance=6)
    mb.build("hand_lantern_mesh", root, col)
    G.marker("MARK_grip", (0, 0, 0.5), root, col)
    return root


def build_banner_lion():
    """Origin = wall base (ground, wall plane y=0); banner rod mounted at 4.2 m."""
    root, col, mb = P("banner_lion")
    w, h = 1.2, 3.0
    mb.push(G.Matrix.Translation((0, 0, 4.2)))
    mb.box((-0.08, 0.0, -0.08), (0.08, 0.04, 0.12), "M_Iron")
    mb.rod((0, 0.02, 0.02), (0, -0.6, 0.02), 0.03, "M_Iron", segs=6)
    mb.rod((-w / 2 - 0.1, -0.55, 0.02), (w / 2 + 0.1, -0.55, 0.02), 0.035, "M_Iron", segs=6)
    for sx in (-1, 1):
        mb.sphere((sx * (w / 2 + 0.12), -0.55, 0.02), 0.05, "M_Gold", segs=6, rings=4)
    mb.box((-w / 2, -0.57, -h), (w / 2, -0.53, 0.0),
           {"-y": "M_Banner", "+y": "M_ClothRed", "-x": "M_ClothRed", "+x": "M_ClothRed", "-z": "M_ClothRed", "+z": "M_ClothRed"})
    mb.face([(-w / 2, -0.575, -h), (0, -0.575, -h), (-w / 2, -0.575, -h - 0.45)], "M_ClothRed")
    mb.face([(0, -0.575, -h), (w / 2, -0.575, -h), (w / 2, -0.575, -h - 0.45)], "M_ClothRed")
    mb.pop()
    ob = mb.build("ANIM_banner", root, col)
    ob["anim"] = "sway"
    G.set_origin(ob, (0, -0.55, 4.22))
    G.marker("MARK_mount", (0, 0, 4.2), root, col)
    return root


def build_bench():
    root, col, mb = P("bench")
    mb.box((-0.9, -0.17, 0.42), (0.9, 0.17, 0.48), "M_WoodLight")
    for x in (-0.7, 0.7):
        mb.box((x - 0.05, -0.15, 0), (x + 0.05, 0.15, 0.42), "M_Timber")
    mb.box((-0.7, -0.03, 0.15), (0.7, 0.03, 0.22), "M_Timber")
    return finish(root, col, mb)


def build_table():
    root, col, mb = P("table")
    mb.box((-0.9, -0.45, 0.74), (0.9, 0.45, 0.8), "M_WoodLight")
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((sx * 0.78 - 0.05, sy * 0.35 - 0.05, 0), (sx * 0.78 + 0.05, sy * 0.35 + 0.05, 0.74), "M_Timber")
    mb.box((-0.78, -0.03, 0.15), (0.78, 0.03, 0.22), "M_Timber")
    jug(mb, 0.4, 0.1, 0.8, 1.0, "M_Pottery", 0)
    loaf(mb, -0.3, -0.1, 0.8, 1.0, 0.4)
    return finish(root, col, mb)


def build_stool():
    root, col, mb = P("stool")
    mb.cyl((0, 0, 0.42), 0.18, 0.05, "M_WoodLight", segs=12, smooth=False)
    for k in range(3):
        a = 2 * PI * k / 3
        mb.rod((0.12 * math.cos(a), 0.12 * math.sin(a), 0.43), (0.18 * math.cos(a), 0.18 * math.sin(a), 0.0), 0.025, "M_Timber", segs=5)
    return finish(root, col, mb)


def build_tree():
    root, col, mb = P("tree")
    rnd = random.Random(42)
    mb.lathe([(0.32, 0), (0.24, 0.4), (0.2, 1.5), (0.17, 2.6), (0.12, 3.4)], "M_Bark", segs=10)
    tips = []
    for k in range(6):
        a = 2 * PI * k / 6 + rnd.uniform(-0.3, 0.3)
        z0 = rnd.uniform(2.0, 3.2)
        L = rnd.uniform(1.0, 1.8)
        tip = (L * math.cos(a), L * math.sin(a), z0 + rnd.uniform(0.8, 1.5))
        mb.rod((0, 0, z0), tip, 0.07, "M_Bark", segs=6, r1=0.03)
        tips.append(tip)
    blobs = tips + [(0, 0, 4.6), (0.4, -0.3, 5.4), (-0.5, 0.4, 5.0), (0.1, 0.2, 6.0)]
    for i, (x, y, z) in enumerate(blobs):
        r = rnd.uniform(0.9, 1.3)
        mb.sphere((x, y, z), (r, r, r * 0.85), "M_Leaves", segs=10, rings=7, noise=0.18, seed=i * 13, smooth=True)
    mb.build("tree_mesh", root, col)
    mc = MB()
    mc.cyl((0, 0, 0), 0.3, 3.0, "M_Trim", segs=8, smooth=False)
    G.finish_collision(mc, "tree", root, col)
    return root


def build_bread_tray():
    root, col, mb = P("bread_tray")
    mb.box((-0.4, -0.25, 0), (0.4, 0.25, 0.04), "M_WoodLight")
    k = 0
    for i in range(4):
        for j in range(3):
            loaf(mb, -0.3 + i * 0.2, -0.15 + j * 0.15, 0.04, 0.75, ang=0.2 * (i - j), seed=k)
            k += 1
    for i in range(3):
        loaf(mb, -0.2 + i * 0.2, 0.0, 0.1, 0.7, ang=1.3, seed=20 + i)
    return finish(root, col, mb)


def build_pottery():
    root, col, mb = P("pottery")
    jug(mb, 0, 0, 0, 1.3, "M_Pottery", 0)
    jug(mb, 0.3, 0.1, 0, 1.2, "M_ClayPale", 1)
    jug(mb, -0.28, 0.12, 0, 1.0, "M_Pottery", 2)
    jug(mb, 0.15, -0.25, 0, 0.9, "M_ClayPale", 0)
    jug(mb, -0.15, -0.22, 0, 1.0, "M_Pottery", 1)
    return finish(root, col, mb)


def build_cooking_pot():
    root, col, mb = P("cooking_pot")
    for k in range(3):
        a = 2 * PI * k / 3
        mb.rod((0.55 * math.cos(a), 0.55 * math.sin(a), 0), (0, 0, 1.4), 0.025, "M_Iron", segs=5)
    mb.rod((0, 0, 1.4), (0, 0, 0.75), 0.008, "M_Iron", segs=4)
    with mb.at((0, 0, 0.35)):
        mb.lathe([(0.12, 0), (0.25, 0.08), (0.28, 0.22), (0.25, 0.36), (0.27, 0.38)], "M_Iron", segs=16)
    with mb.at((0, 0, 0.73), rot_x=PI / 2):
        mb.torus(0.26, 0.01, "M_Iron", segs=14, tsegs=4)
    logs(mb, (0, 0, 0.0), 0.8, 3)
    fire(mb, (0, 0, 0.05), 0.5, 3, 9)
    G.point_light("LIGHT_fire", (0, 0, 0.4), root, col, energy=60, color=(1.0, 0.55, 0.22), distance=7)
    return finish(root, col, mb)


# ----------------------------------------------------------------------------- market stalls
STALLS = ["produce", "bread", "pottery", "cloth", "meat", "weapons"]


def build_market_stall(variant):
    name = f"market_stall_{variant}"
    root, col = G.new_asset(name, "props")
    mb = MB()
    W, D = 2.8, 1.6
    hb, hf = 2.6, 2.2
    cloth = "M_CanvasStriped" if variant in ("cloth", "pottery") else "M_Canvas"
    for sx in (-1, 1):
        mb.box((sx * W / 2 - 0.06, -D / 2 - 0.06, 0), (sx * W / 2 + 0.06, -D / 2 + 0.06, hf), "M_Timber")
        mb.box((sx * W / 2 - 0.06, D / 2 - 0.06, 0), (sx * W / 2 + 0.06, D / 2 + 0.06, hb), "M_Timber")
        mb.box((sx * W / 2 - 0.05, -D / 2, hf - 0.1), (sx * W / 2 + 0.05, D / 2, hf), "M_Timber")
    # counter
    mb.box((-W / 2 + 0.06, -D / 2 + 0.05, 0.85), (W / 2 - 0.06, -D / 2 + 0.75, 0.92), "M_WoodLight")
    mb.box((-W / 2 + 0.06, -D / 2 + 0.03, 0.0), (W / 2 - 0.06, -D / 2 + 0.08, 0.85), "M_WoodLight")
    mb.box((-W / 2 + 0.06, D / 2 - 0.4, 0.5), (W / 2 - 0.06, D / 2 - 0.05, 0.55), "M_WoodLight")  # back shelf
    # sloped awning projecting forward, scalloped valance
    ov = 0.45
    zf = hf - 0.05
    with mb.at((0, 0, 0), rot_z=PI / 2):
        mb.prism([(-D / 2 - ov, zf - 0.05), (D / 2 + 0.1, hb + 0.05), (D / 2 + 0.1, hb + 0.08), (-D / 2 - ov, zf - 0.02)],
                 -W / 2 - 0.2, W / 2 + 0.2, cloth)
    n = 7
    pts = [(-W / 2 - 0.2, zf - 0.02)]
    for k in range(n):
        x0 = -W / 2 - 0.2 + k * (W + 0.4) / n
        x1 = x0 + (W + 0.4) / n
        for t in range(1, 6):
            u = t / 6
            pts.append((x0 + (x1 - x0) * u, zf - 0.3 - 0.12 * math.sin(PI * u)))
        pts.append((x1, zf - 0.3))
    pts.append((W / 2 + 0.2, zf - 0.02))
    mb.prism(list(reversed(pts)), -D / 2 - ov - 0.02, -D / 2 - ov + 0.01, cloth)
    mb.rod((-W / 2 - 0.2, -D / 2 - ov, zf - 0.04), (W / 2 + 0.2, -D / 2 - ov, zf - 0.04), 0.03, "M_Timber", segs=6)
    for sx in (-1, 1):
        mb.rod((sx * (W / 2 + 0.1), -D / 2 - ov, zf - 0.04), (sx * W / 2, -D / 2, 1.2), 0.025, "M_Timber", segs=5)
    # goods
    zc = 0.92
    if variant == "produce":
        for i, kind in enumerate(["apple", "cabbage", "carrot", "onion"]):
            x = -1.0 + i * 0.67
            with mb.at((x, -D / 2 + 0.4, zc)):
                crate_parts(mb, (0.55, 0.45, 0.18), open_top=True)
            produce_fill(mb, (x - 0.23, x + 0.23), (-D / 2 + 0.22, -D / 2 + 0.58), zc + 0.06, kind, i, layers=2)
        for x in (-0.8, 0.6):
            with mb.at((x, D / 2 - 0.2, 0.55)):
                sack_parts(mb, 0.5, 0.2, int(x * 10))
        produce_fill(mb, (-0.9, 0.9), (D / 2 - 0.6, D / 2 - 0.15), 0.0, "pumpkin", 5)
    elif variant == "bread":
        for x in (-0.75, 0.0, 0.75):
            with mb.at((x, -D / 2 + 0.4, zc)):
                mb.box((-0.32, -0.28, 0), (0.32, 0.28, 0.03), "M_WoodLight")
            k = 0
            for i in range(3):
                for j in range(3):
                    loaf(mb, x - 0.2 + i * 0.2, -D / 2 + 0.25 + j * 0.15, zc + 0.03, 0.75, 0.3 * (i - j), seed=k + int(x * 10))
                    k += 1
        for x in (-0.9, -0.3, 0.3, 0.9):
            loaf(mb, x, D / 2 - 0.22, 0.55, 0.9, 1.5, seed=int(x * 30))
        with mb.at((0.9, D / 2 - 0.5, 0)):
            mb.lathe([(0.17, 0.0), (0.22, 0.12), (0.25, 0.25)], "M_WoodLight", segs=14, cap_top=False)
    elif variant == "pottery":
        for i in range(7):
            x = -1.1 + i * 0.36
            jug(mb, x, -D / 2 + 0.4 + (0.12 if i % 2 else -0.08), zc, 0.9 + 0.2 * (i % 3), "M_Pottery" if i % 2 else "M_ClayPale", i % 3)
        for i in range(5):
            jug(mb, -0.9 + i * 0.45, D / 2 - 0.22, 0.55, 1.2, "M_Pottery", (i + 1) % 3)
    elif variant == "cloth":
        for i, m in enumerate(["M_ClothRed", "M_ClothGreen", "M_Canvas", "M_ClothRed", "M_Burlap"]):
            x = -1.0 + i * 0.5
            with mb.at((x, -D / 2 + 0.4, zc + 0.1), rot_x=PI / 2):
                mb.cyl((0, 0, -0.3), 0.1, 0.6, m, segs=12)
        mb.rod((-W / 2, D / 2 - 0.1, 2.0), (W / 2, D / 2 - 0.1, 2.0), 0.02, "M_Timber", segs=5)
        for i, m in enumerate(["M_ClothRed", "M_ClothGreen", "M_CanvasStriped"]):
            x = -0.9 + i * 0.9
            mb.box((x - 0.35, D / 2 - 0.13, 0.9), (x + 0.35, D / 2 - 0.09, 2.0), m)
    elif variant == "meat":
        mb.rod((-W / 2, -D / 2 + 0.3, 2.0), (W / 2, -D / 2 + 0.3, 2.0), 0.025, "M_Iron", segs=5)
        for i in range(5):
            x = -1.0 + i * 0.5
            mb.rod((x, -D / 2 + 0.3, 2.0), (x, -D / 2 + 0.3, 1.8), 0.008, "M_Iron", segs=4)
            mb.sphere((x, -D / 2 + 0.3, 1.55), (0.12, 0.08, 0.26), "M_Meat", segs=10, rings=7, noise=0.08, seed=i)
        mb.box((-1.1, -D / 2 + 0.15, zc), (1.1, -D / 2 + 0.7, zc + 0.08), "M_WoodLight")
        for i in range(4):
            mb.sphere((-0.8 + i * 0.5, -D / 2 + 0.42, zc + 0.12), (0.16, 0.12, 0.06), "M_Meat", segs=10, rings=6, noise=0.06, seed=10 + i)
        with mb.at((0.9, D / 2 - 0.35, 0)):
            barrel_parts(mb, 0.7, 0.24, 0.03)
    elif variant == "weapons":
        for k in range(5):
            sword(mb, (-0.9 + k * 0.45, -D / 2 + 0.45, zc + 0.03), ang=0.0, length=0.95, tilt=PI / 2)
        for k in range(5):
            spear(mb, (-1.1 + k * 0.55, D / 2 - 0.15, 0.0), 2.3, tilt=0.06 * (k - 2), halberd=k % 2 == 0)
        shield(mb, (-0.8, D / 2 - 0.3, 1.35), lean=-0.1)
        shield(mb, (0.8, D / 2 - 0.3, 1.35), lean=-0.1)
        shield(mb, (W / 2 + 0.15, -D / 2 + 0.2, 1.3), ang=-PI / 2 + 0.2, lean=-0.1, s=0.9)
    ob = mb.build(f"INT_stall_{variant}", root, col)
    ob["interactive"] = "merchant"
    G.marker("MARK_merchant", (0, D / 2 - 0.65, 0), root, col)
    G.marker("MARK_customer", (0, -D / 2 - 1.0, 0), root, col, rot_z=PI)
    mc = MB()
    mc.box((-W / 2, -D / 2, 0), (W / 2, -D / 2 + 0.75, 0.92), "M_Trim")
    for sx in (-1, 1):
        for sy in (-1, 1):
            mc.box((sx * W / 2 - 0.06, sy * D / 2 - 0.06, 0), (sx * W / 2 + 0.06, sy * D / 2 + 0.06, hf), "M_Trim")
    G.finish_collision(mc, name, root, col)
    return root


# ----------------------------------------------------------------------------- reusable door / window
def build_door_wood():
    import build_architecture as A
    root, col = G.new_asset("door_wood", "props")
    mb = MB()
    o = dict(xa=-0.7, xb=0.7, za=0.0, zs=2.2, kind="round")
    A.wall_with_openings(mb, -1.0, 1.0, 0.0, A.opening_top(o) + 0.3, -0.12, 0.0, [o], "M_Trim")
    mb.build("door_wood_frame", root, col)
    A.door_leaf("INT_door", o, 0.05, 0.15, o["xa"] + 0.05, root, col, (0, 0, 0))
    G.marker("MARK_outside", (0, -1.0, 0), root, col)
    G.marker("MARK_inside", (0, 1.0, 0), root, col, rot_z=PI)
    return root


def build_window_shutters():
    import build_architecture as A
    root, col = G.new_asset("window_shutters", "props")
    mb = MB()
    o = dict(xa=-0.5, xb=0.5, za=0.0, zs=1.5, kind="segment")
    A.window_frame(mb, o, -0.07, 0.0)
    mb.build("window_shutters_frame", root, col)
    wm = MB()
    A.glass(wm, o, 0.05)
    A.mullions(wm, o, 0.02, 0.07)
    wob = wm.build("INT_window", root, col)
    wob["interactive"] = "window"
    G.set_origin(wob, (0, 0.05, 0))
    top = A.opening_top(o)
    for side, hx in (("L", o["xa"] - 0.17), ("R", o["xb"] + 0.17)):
        sm = MB()
        x0, x1 = (hx - 0.47, hx) if side == "L" else (hx, hx + 0.47)
        sm.box((x0, -0.14, -0.05), (x1, -0.09, top), "M_WoodDark")
        for zz in (0.25, top - 0.35):
            sm.box((x0 + 0.03, -0.155, zz), (x1 - 0.03, -0.14, zz + 0.06), "M_Iron")
        so = sm.build(f"INT_window_shutter_{side}", root, col)
        G.set_origin(so, (hx, -0.115, 0))
        so.parent = wob
        so.location = so.location - wob.location
        so["interactive"] = "shutter"
    return root


BUILDERS = {
    "barrel": build_barrel, "barrel_small": build_barrel_small, "crate": build_crate, "crate_produce": build_crate_produce,
    "sack": build_sack, "basket": build_basket, "cart": build_cart, "spit_roast": build_spit_roast,
    "weapon_rack": build_weapon_rack, "anvil": build_anvil, "forge": build_forge, "blacksmith_shed": build_blacksmith_shed,
    "street_lantern": build_street_lantern, "wall_torch": build_wall_torch, "hand_lantern": build_hand_lantern,
    "banner_lion": build_banner_lion, "bench": build_bench, "table": build_table, "stool": build_stool, "tree": build_tree,
    "bread_tray": build_bread_tray, "pottery": build_pottery, "cooking_pot": build_cooking_pot,
    "door_wood": build_door_wood, "window_shutters": build_window_shutters,
}
for _v in STALLS:
    BUILDERS[f"market_stall_{_v}"] = (lambda v=_v: build_market_stall(v))

NIGHT_PREVIEW = {"spit_roast", "forge", "street_lantern", "wall_torch", "hand_lantern", "cooking_pot", "market_stall_meat"}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only = argv[argv.index("--only") + 1].split(",") if "--only" in argv else None
    render = "--no-render" not in argv
    G.reset_scene()
    roots = []
    for name, fn in BUILDERS.items():
        if only and name not in only:
            continue
        print("BUILD", name)
        roots.append(fn())
    bpy.context.view_layer.update()
    for r in roots:
        G.export_asset(r, OUT)
    if render:
        import lib_render as R
        for r in roots:
            R.render_asset(r)
            if r.name in NIGHT_PREVIEW:
                R.render_asset(r, night=True)
        for n in ("_preview_ground", "_preview_cam", "_preview_sun"):
            ob = bpy.data.objects.get(n)
            if ob:
                bpy.data.objects.remove(ob)
    if not only:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(G.BLENDER_DIR, "props.blend"))
    print("DONE props")


if __name__ == "__main__":
    main()
