"""Vysehrad assets (run 2) + distant backdrops shared by all new locations.

Fortress pieces stand on the plateau (z=0); outer faces look -Y and reach down to z=-8 so they sit into the crag.
Backdrops (castle_hill, city_backdrop, bridge_far) are low-detail scenery without collision, seen from far away.
"""
import math
import random

import build_architecture as BA
import lib_geo as G
from lib_geo import MB, wall_with_openings
from loc_common import PI, far_house, grid_surface, noise2, tree_cluster

STONE = "M_StoneRough"


def _merlons(mb, x0, x1, y0, y1, z, h=0.9, w=0.9, gap=0.7, mat=STONE):
    n = int((x1 - x0 + gap) / (w + gap))
    pad = (x1 - x0 - (n * w + (n - 1) * gap)) / 2
    for k in range(n):
        xa = x0 + pad + k * (w + gap)
        mb.box((xa, y0, z), (xa + w, y1, z + h), mat)


def build_fortress_wall():
    """12 m curtain wall, 8 m above the plateau, crenellated outer edge."""
    root, col = G.new_asset("fortress_wall", "architecture")
    mb, mc = MB(), MB()
    mb.box((-6, 0, -8), (6, 2.4, 8), STONE)
    mb.box((-6.02, -0.15, -8), (6.02, 0.0, -6.5), "M_Ashlar")
    mb.box((-6.02, -0.12, 7.8), (6.02, 0.6, 8.0), "M_Trim")
    _merlons(mb, -6, 6, 0.0, 0.6, 8.0, 1.1)
    for x in (-3.0, 3.0):                                             # arrow slits
        mb.box((x - 0.08, -0.03, 3.0), (x + 0.08, 0.0, 4.6), "M_StoneDark")
        mb.box((x - 0.08, 2.4, 1.5), (x + 0.08, 2.43, 3.1), "M_StoneDark")
    mc.box((-6, 0, -8), (6, 2.4, 9.1), "M_Trim")
    mb.build("fortress_wall_mesh", root, col)
    G.finish_collision(mc, "fortress_wall", root, col)
    root["size"] = [12, 2.4, 17]
    return root


def build_fortress_parapet():
    """12 m low crenellated wall on the cliff edge: the knight can look (and throw enemies) over it."""
    root, col = G.new_asset("fortress_parapet", "architecture")
    mb, mc = MB(), MB()
    mb.box((-6, 0, -9), (6, 1.0, 1.1), STONE)
    mb.box((-6.02, -0.08, 1.0), (6.02, 1.08, 1.15), "M_Trim")
    _merlons(mb, -6, 6, 0.0, 1.0, 1.15, 0.85, 1.0, 0.9)
    mc.box((-6, 0, -9), (6, 1.0, 3.0), "M_Trim")                     # invisible guard up to 3 m: nobody climbs out
    mb.build("fortress_parapet_mesh", root, col)
    G.finish_collision(mc, "fortress_parapet", root, col)
    G.marker("MARK_ledge", (0, 1.8, 0), root, col)
    root["size"] = [12, 1.0, 10]
    return root


def build_fortress_tower(name="fortress_tower", W=8.0, H=16.0):
    root, col = G.new_asset(name, "architecture")
    mb, mc = MB(), MB()
    mb.box((-W / 2, -W / 2, -8), (W / 2, W / 2, H), STONE)
    mb.box((-W / 2 - 0.1, -W / 2 - 0.1, -8), (W / 2 + 0.1, W / 2 + 0.1, -6.8), "M_Ashlar")
    for z in (5.0, 11.0):
        mb.box((-W / 2 - 0.08, -W / 2 - 0.08, z), (W / 2 + 0.08, W / 2 + 0.08, z + 0.25), "M_Trim")
    for face in range(4):
        a = face * PI / 2
        with mb.at((W / 2 * math.sin(a), -W / 2 * math.cos(a), 0), rot_z=a):
            mb.box((-0.09, -0.03, 2.5), (0.09, 0.0, 4.2), "M_StoneDark")
            with mb.at((0, 0, 12.0)):
                BA.window_unit(mb, 0.8, 1.5, "round")
    for face in (0, 1):
        a = face * PI / 2
        with mb.at((W / 2 * math.sin(a), -W / 2 * math.cos(a), 0), rot_z=a):
            BA.banner(mb, 0.0, 0.0, 10.2, 1.3, 3.6)
    mb.box((-W / 2 - 0.3, -W / 2 - 0.3, H), (W / 2 + 0.3, W / 2 + 0.3, H + 0.3), "M_Timber")
    mb.pyramid(0, 0, H + 0.3, W + 1.6, W + 1.6, W * 0.9, "M_RoofTiles")
    mb.rod((0, 0, H + W * 0.9), (0, 0, H + W * 0.9 + 1.4), 0.05, "M_Iron", segs=6)
    mb.sphere((0, 0, H + W * 0.9 + 0.3), 0.15, "M_Gold", segs=8, rings=5)
    mc.box((-W / 2, -W / 2, -8), (W / 2, W / 2, H), "M_Trim")
    mb.build(name + "_mesh", root, col)
    G.finish_collision(mc, name, root, col)
    root["size"] = [W + 1.6, W + 1.6, H + W]
    return root


def build_gate_tower():
    """Vysehrad gate tower: passage along local Y, open oak leaves, red tiled pyramid roof, lion banners, torches."""
    name = "gate_tower"
    root, col = G.new_asset(name, "architecture")
    mb, mc = MB(), MB()
    W, D, H = 10.0, 9.0, 15.0
    gate = dict(xa=-2.2, xb=2.2, za=0.0, zs=4.0, kind="round")
    wall_with_openings(mb, -W / 2, W / 2, -6.0, H, -D / 2, D / 2, [gate], STONE)
    mb.box((gate["xa"], -D / 2, -0.05), (gate["xb"], D / 2, 0.0), "M_Cobble")
    for y0, y1 in ((-D / 2 - 0.15, -D / 2), (D / 2, D / 2 + 0.15)):
        wall_with_openings(mb, gate["xa"] - 0.5, gate["xb"] + 0.5, 0.0, BA.opening_top(gate) + 0.5, y0, y1, [gate], "M_Ashlar")
    for sx in (-1, 1):                                                   # open leaves against the passage walls
        x = sx * (gate["xb"] - 0.08)
        mb.box((x - 0.06, -D / 2 + 0.6, 0.0), (x + 0.06, -D / 2 + 2.8, 4.2), "M_Door")
        for z in (0.6, 2.0, 3.4):
            mb.box((x - 0.08, -D / 2 + 0.6, z), (x + 0.08, -D / 2 + 2.8, z + 0.1), "M_Iron")
    for z in (6.0, 11.0):
        mb.box((-W / 2 - 0.08, -D / 2 - 0.08, z), (W / 2 + 0.08, D / 2 + 0.08, z + 0.25), "M_Trim")
    for face in (-1, 1):
        with mb.at((0, face * D / 2, 0), rot_z=0 if face < 0 else PI):
            with mb.at((0, 0, 8.0)):
                BA.window_unit(mb, 1.0, 1.8, "round")
            for x in (-3.0, 3.0):
                BA.banner(mb, x, 0.0, 12.6, 1.2, 3.6)
            mb.box((-1.1, -0.15, 5.2), (1.1, 0.0, 6.2), "M_ClothRed")
            mb.box((-0.4, -0.17, 5.4), (0.4, -0.15, 6.0), "M_Trim")
    mb.box((-W / 2 - 0.3, -D / 2 - 0.3, H), (W / 2 + 0.3, D / 2 + 0.3, H + 0.3), "M_Timber")
    mb.pyramid(0, 0, H + 0.3, W + 1.8, D + 1.8, 8.5, "M_RoofTiles")
    mb.rod((0, 0, H + 8.7), (0, 0, H + 10.2), 0.05, "M_Iron", segs=6)
    mb.sphere((0, 0, H + 9.0), 0.16, "M_Gold", segs=8, rings=5)
    mc.box((-W / 2, -D / 2, -6), (gate["xa"], D / 2, H), "M_Trim")
    mc.box((gate["xb"], -D / 2, -6), (W / 2, D / 2, H), "M_Trim")
    mc.box((gate["xa"], -D / 2, BA.opening_top(gate)), (gate["xb"], D / 2, H), "M_Trim")
    mb.build(name + "_mesh", root, col)
    G.finish_collision(mc, name, root, col)
    for i, (x, y) in enumerate(((-3.0, -D / 2), (3.0, -D / 2), (-3.0, D / 2), (3.0, D / 2))):
        f = -1 if y < 0 else 1
        if f < 0:
            BA.with_torch(root, col, (x, y, 2.6))
        G.point_light(f"LIGHT_gate_{i}", (x, y + f * 0.6, 3.2), root, col, energy=75)
    G.marker("MARK_gate_front", (0, -D / 2 - 3.0, 0), root, col)
    G.marker("MARK_gate_back", (0, D / 2 + 3.0, 0), root, col, rot_z=PI)
    root["size"] = [W + 1.8, D + 1.8, H + 10]
    return root


def build_rotunda():
    """Romanesque rotunda of St Martin: round nave, conical tiled roof, lantern with cross, apse to +Y."""
    root, col = G.new_asset("rotunda", "architecture")
    mb, mc = MB(), MB()
    R = 4.5
    mb.cyl((0, 0, 0), R, 7.0, STONE, segs=28, smooth=True)
    mb.cyl((0, 0, -0.3), R + 0.2, 0.6, "M_Ashlar", segs=28)
    mb.cyl((0, 0, 6.8), R + 0.25, 0.35, "M_Trim", segs=28)
    for k in range(20):                                                   # Lombard band arcading
        a = 2 * PI * k / 20
        with mb.at((R * math.cos(a), R * math.sin(a), 6.2), rot_z=a + PI / 2):
            mb.box((-0.1, -0.12, 0.0), (0.1, 0.0, 0.5), "M_Trim")
    for k in range(5):
        a = -PI / 2 + (k - 2) * 0.75
        with mb.at((R * math.cos(a), R * math.sin(a), 3.3), rot_z=a + PI / 2):
            BA.window_unit(mb, 0.55, 1.3, "round")
    with mb.at((0, -R, 0)):
        door = dict(xa=-0.8, xb=0.8, za=0.0, zs=2.2, kind="round")
        mb.box((-1.3, -0.5, 0), (1.3, 0.0, 3.6), "M_Ashlar")
        mb.prism([(-1.5, 3.6), (1.5, 3.6), (0, 4.5)], -0.55, 0.0, "M_Ashlar")
        mb.prism(list(reversed(BA.opening_outline(door))), -0.55, -0.5, "M_Door")
    mb.lathe([(R + 0.5, 7.15), (R * 0.5, 9.4), (1.3, 10.6)], "M_RoofTiles", segs=28, cap_bottom=True, cap_top=True)
    mb.cyl((0, 0, 10.5), 1.2, 1.6, STONE, segs=16)
    for k in range(6):
        a = 2 * PI * k / 6
        mb.box((1.2 * math.cos(a) - 0.12, 1.2 * math.sin(a) - 0.12, 10.9), (1.2 * math.cos(a) + 0.12, 1.2 * math.sin(a) + 0.12, 11.6),
               "M_StoneDark")
    mb.cyl((0, 0, 12.1), 1.45, 1.6, "M_RoofTiles", segs=16, r_top=0.0)
    mb.rod((0, 0, 13.6), (0, 0, 15.2), 0.06, "M_Iron", segs=6)
    mb.box((-0.45, -0.04, 14.6), (0.45, 0.04, 14.72), "M_Iron")
    # apse
    mb.cyl((0, R, 0), 2.6, 5.0, STONE, segs=20)
    mb.cyl((0, R, 5.0), 2.85, 1.5, "M_RoofTiles", segs=20, r_top=0.6)
    mc.cyl((0, 0, -0.3), R, 7.4, "M_Trim", segs=12, smooth=False)
    mc.cyl((0, R, 0), 2.6, 5.0, "M_Trim", segs=10, smooth=False)
    mb.build("rotunda_mesh", root, col)
    G.finish_collision(mc, "rotunda", root, col)
    root["size"] = [10, 12, 15]
    return root


def build_basilica():
    """Romanesque chapter church with a square bell tower (behind the rotunda on the concept art)."""
    root, col = G.new_asset("basilica", "architecture")
    mb, mc = MB(), MB()
    mb.box((-5, 0, 0), (5, 26, 11), STONE)
    mb.gable_roof(-5, 5, -0.3, 26.3, 11, 16.5, "M_RoofTiles", over=0.35)
    mb.prism([(-5, 11), (5, 11), (0, 16.3)], 0.0, 0.4, STONE)
    mb.prism([(-5, 11), (5, 11), (0, 16.3)], 25.6, 26.0, STONE)
    for sx in (-1, 1):                                                    # aisles with shed roofs
        xa, xb = (5, 8.5) if sx > 0 else (-8.5, -5)
        mb.box((xa, 1.0, 0), (xb, 25.0, 6.5), STONE)
        with mb.at((0, 0, 0)):
            pts = [(5.0 * sx, 8.4), (8.9 * sx, 6.3), (8.9 * sx, 6.6), (5.0 * sx, 8.7)]
            mb.prism(pts if sx > 0 else list(reversed(pts)), 0.7, 25.3, "M_RoofTiles")
        for k in range(5):
            with mb.at((xb if sx > 0 else xa, 3.5 + k * 4.5, 2.6), rot_z=sx * PI / 2):
                BA.window_unit(mb, 0.6, 1.6, "round")
            with mb.at((5.0 * sx, 3.5 + k * 4.5, 8.7), rot_z=sx * PI / 2):
                BA.window_unit(mb, 0.6, 1.3, "round")
    door = dict(xa=-1.2, xb=1.2, za=0.0, zs=3.0, kind="round")
    for k, e in enumerate((0.0, 0.25, 0.5)):
        wall_with_openings(mb, door["xa"] - e - 0.3, door["xb"] + e + 0.3, 0, BA.opening_top(door) + e + 0.3, -0.15 - 0.15 * k,
                           -0.15 * k, [dict(door, xa=door["xa"] - e, xb=door["xb"] + e)], "M_Ashlar")
    mb.prism(list(reversed(BA.opening_outline(door))), 0.0, 0.05, "M_Door")
    with mb.at((0, -0.02, 7.0), rot_x=PI / 2):
        mb.torus(1.1, 0.15, "M_Ashlar", segs=20, tsegs=6)
    mb.face([(1.0 * math.cos(2 * PI * k / 20), -0.04, 7.0 + 1.0 * math.sin(2 * PI * k / 20)) for k in reversed(range(20))], "M_WindowLit")
    # bell tower
    tx, ty, T = 9.0, 30.0, 26.0
    mb.box((tx - 3, ty - 3, 0), (tx + 3, ty + 3, T), STONE)
    for z in (9.0, 17.0):
        mb.box((tx - 3.08, ty - 3.08, z), (tx + 3.08, ty + 3.08, z + 0.2), "M_Trim")
    for face in range(4):
        a = face * PI / 2
        with mb.at((tx + 3 * math.sin(a), ty - 3 * math.cos(a), 0), rot_z=a):
            for x in (-0.75, 0.75):
                with mb.at((x, 0, 20.0)):
                    BA.window_unit(mb, 0.8, 2.2, "round")
            with mb.at((0, 0, 12.0)):
                BA.window_unit(mb, 0.6, 1.4, "round")
    mb.pyramid(tx, ty, T, 6.8, 6.8, 7.5, "M_Slate")
    mb.rod((tx, ty, T + 7.4), (tx, ty, T + 9.4), 0.06, "M_Iron", segs=6)
    mb.box((tx - 0.5, ty - 0.04, T + 8.6), (tx + 0.5, ty + 0.04, T + 8.72), "M_Iron")
    mc.box((-8.5, 0, 0), (8.5, 26, 12), "M_Trim")
    mc.box((tx - 3, ty - 3, 0), (tx + 3, ty + 3, T), "M_Trim")
    mb.build("basilica_mesh", root, col)
    G.finish_collision(mc, "basilica", root, col)
    root["size"] = [18, 34, T + 9]
    return root


def build_cliff_rock(name="cliff_rock_a", seed=1, W=48.0, drop=42.0):
    """The Vysehrad crag: rock face from the plateau rim (y=0, z=0) falling to the river (-Y, down to z=-drop).
    Grass lip on top, bushes in the ledges. No collision (unreachable; the game kills anything below kill_y)."""
    root, col = G.new_asset(name, "architecture")
    mb = MB()

    def face(u, v):
        x = -W / 2 + W * u
        n1 = noise2(u * 5 + seed * 3.1, v * 6, seed, 4)
        n2 = noise2(u * 14 + seed, v * 16 + 7, seed + 5, 3)
        y = -1.0 - 26.0 * v ** 1.15 + (n1 - 0.5) * 7.0 + (n2 - 0.5) * 2.2
        z = 0.2 - drop * v + (n1 - 0.5) * 3.0
        if u < 0.04 or u > 0.96:                           # ends tuck back so neighbours overlap cleanly
            y += 2.0
        return (x, y, z, "M_Rock")
    grid_surface(mb, 34, 26, face, "M_Rock", smooth=True, flip=True)

    def lip(u, v):
        x = -W / 2 + W * u
        return (x, -1.0 + 5.0 * v + (noise2(u * 9, 1.0, seed + 9) - 0.5) * 0.6 * (1 - v), 0.25 - 0.15 * (1 - v))
    grid_surface(mb, 20, 2, lip, "M_Grass", smooth=True)
    rnd = random.Random(seed * 17)
    for k in range(14):                                     # bushes clinging to the rock
        u, v = rnd.uniform(0.05, 0.95), rnd.uniform(0.05, 0.7)
        p = face(u, v)
        tree_cluster(mb, p[0], p[1] - 1.0, p[2] - 1.0, rnd.uniform(1.0, 2.2), rnd, n=2)
    mb.build(name + "_mesh", root, col)
    root["size"] = [W, 30, drop]
    return root


def build_rock_outcrop():
    root, col = G.new_asset("rock_outcrop", "props")
    mb = MB()
    rnd = random.Random(7)
    for k in range(3):
        mb.sphere((rnd.uniform(-1, 1), rnd.uniform(-0.6, 0.6), 0.3), (rnd.uniform(1.0, 1.6), rnd.uniform(0.8, 1.2), rnd.uniform(0.7, 1.1)),
                  "M_Rock", segs=10, rings=7, noise=0.22, seed=k, z_cut=0.0)
    mb.build("rock_outcrop_mesh", root, col)
    G.auto_collision(root, col, shrink=0.4)
    root["size"] = [3.5, 2.5, 1.5]
    return root


# ----------------------------------------------------------------------------- training ground & cemetery
def build_watchtower_wood():
    root, col = G.new_asset("watchtower_wood", "props")
    mb, mc = MB(), MB()
    b, H = 1.7, 6.0
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.rod((sx * b, sy * b, 0), (sx * (b - 0.35), sy * (b - 0.35), H + 2.6), 0.12, "M_Timber", segs=6)
    for z0, z1 in ((0.4, 3.0), (3.0, 5.8)):                              # X bracing
        for (ax, ay, bx, by) in ((-b, -b, b, -b), (-b, b, b, b), (-b, -b, -b, b), (b, -b, b, b)):
            mb.rod((ax, ay, z0), (bx, by, z1), 0.06, "M_Timber", segs=5)
            mb.rod((bx, by, z0), (ax, ay, z1), 0.06, "M_Timber", segs=5)
    mb.box((-b - 0.2, -b - 0.2, H - 0.15), (b + 0.2, b + 0.2, H), "M_WoodLight")
    for (ax, ay, bx, by) in ((-b, -b, b, -b), (-b, b, b, b), (-b, -b, -b, b), (b, -b, b, b)):
        mb.rod((ax * 1.08, ay * 1.08, H + 1.0), (bx * 1.08, by * 1.08, H + 1.0), 0.05, "M_Timber", segs=5)
    mb.pyramid(0, 0, H + 2.5, 2 * b + 1.4, 2 * b + 1.4, 2.0, "M_Shingle")
    for k in range(8):                                                   # ladder
        z = 0.35 + k * 0.72
        mb.rod((-0.35, -b - 0.25, z), (0.35, -b - 0.25, z), 0.03, "M_WoodLight", segs=4)
    for sx in (-1, 1):
        mb.rod((sx * 0.35, -b - 0.25, 0), (sx * 0.35, -b - 0.15, H), 0.04, "M_WoodLight", segs=5)
    for x in (-1.0, 1.0):                                                # banners hanging from the railing
        mb.box((x - 0.5, -b - 0.42, H - 2.4), (x + 0.5, -b - 0.38, H + 1.0),
               {"-y": "M_Banner", "+y": "M_ClothRed", "-x": "M_ClothRed", "+x": "M_ClothRed", "-z": "M_ClothRed", "+z": "M_ClothRed"})
    mc.box((-b, -b, 0), (b, b, H + 2.6), "M_Trim")
    mb.build("watchtower_wood_mesh", root, col)
    G.finish_collision(mc, "watchtower_wood", root, col)
    root["size"] = [2 * b + 1.4, 2 * b + 1.4, H + 4.5]
    return root


def build_training_dummy():
    root, col = G.new_asset("training_dummy", "props")
    mb = MB()
    mb.cyl((0, 0, 0), 0.25, 0.15, "M_WoodDark", segs=8)
    mb.cyl((0, 0, 0), 0.06, 2.0, "M_Timber", segs=8)
    mb.rod((-0.6, 0, 1.45), (0.6, 0, 1.45), 0.05, "M_Timber", segs=6)
    mb.sphere((0, 0, 1.2), (0.26, 0.2, 0.42), "M_Burlap", segs=10, rings=7, noise=0.06, seed=3)
    mb.sphere((0, 0, 1.8), (0.14, 0.14, 0.16), "M_Burlap", segs=8, rings=6, noise=0.06, seed=4)
    with mb.at((0.0, 0, 1.75), rot_x=PI / 2):
        mb.torus(0.15, 0.015, "M_Rope", segs=10, tsegs=4)
    with mb.at((0.55, -0.12, 1.3), rot_x=PI / 2):
        mb.cyl((0, 0, -0.02), 0.25, 0.04, "M_WoodLight", segs=14)
    mb.build("training_dummy_mesh", root, col)
    G.auto_collision(root, col, shrink=0.15)
    root["size"] = [1.3, 0.5, 2.0]
    return root


def build_archery_target():
    root, col = G.new_asset("archery_target", "props")
    mb = MB()
    for a in (-0.5, 0.5):
        mb.rod((a, 0.2, 0), (a * 0.4, -0.05, 1.7), 0.04, "M_Timber", segs=5)
    mb.rod((0, 0.7, 0), (0, 0.0, 1.6), 0.04, "M_Timber", segs=5)
    with mb.at((0, -0.12, 1.15), rot_x=PI / 2 - 0.15):
        mb.cyl((0, 0, -0.08), 0.62, 0.16, "M_Burlap", segs=24)
        mb.face([(0.6 * math.cos(2 * PI * k / 24), 0.6 * math.sin(2 * PI * k / 24), 0.085) for k in range(24)], "M_Target", uv="fit")
    for k in range(3):                                                    # arrows stuck in it
        x, z = (-0.15 + 0.2 * k, 1.15 + 0.1 * (k - 1))
        mb.rod((x, -0.2, z), (x + 0.05, -0.75, z + 0.1), 0.008, "M_WoodLight", segs=4)
        mb.box((x + 0.03, -0.78, z + 0.08), (x + 0.07, -0.68, z + 0.14), "M_Canvas")
    mb.build("archery_target_mesh", root, col)
    G.auto_collision(root, col, shrink=0.1)
    root["size"] = [1.3, 1.0, 1.8]
    return root


def build_fence_wood():
    root, col = G.new_asset("fence_wood", "props")
    mb, mc = MB(), MB()
    for x in (-2.0, 0.0, 2.0):
        mb.cyl((x, 0, 0), 0.07, 1.15, "M_Timber", segs=6, smooth=False)
    for z in (0.5, 0.95):
        mb.box((-2.05, -0.04, z), (2.05, 0.04, z + 0.1), "M_WoodLight")
    mc.box((-2.0, -0.1, 0), (2.0, 0.1, 1.2), "M_Trim")
    mb.build("fence_wood_mesh", root, col)
    G.finish_collision(mc, "fence_wood", root, col)
    root["size"] = [4.1, 0.2, 1.15]
    return root


def build_gravestone():
    root, col = G.new_asset("gravestone", "props")
    mb = MB()
    with mb.at((0, 0, 0), rot_x=-0.06):
        mb.box((-0.36, -0.08, 0), (0.36, 0.08, 0.85), {"-y": "M_Gravestone", "+y": "M_StoneDark", "-x": "M_StoneDark", "+x": "M_StoneDark",
                                                        "-z": "M_StoneDark", "+z": "M_StoneDark"})
        mb.prism([(-0.36 + 0.72 * (0.5 - 0.5 * math.cos(PI * k / 10)), 0.85 + 0.2 * math.sin(PI * k / 10)) for k in range(11)],
                 -0.08, 0.08, "M_StoneDark")
    mb.box((-0.45, -0.3, -0.05), (0.45, 0.6, 0.06), "M_Grass")
    mb.build("gravestone_mesh", root, col)
    root["size"] = [0.9, 0.9, 1.1]
    return root


def build_grave_cross():
    root, col = G.new_asset("grave_cross", "props")
    mb = MB()
    mb.box((-0.3, -0.2, 0), (0.3, 0.2, 0.25), "M_StoneDark")
    mb.box((-0.08, -0.07, 0.25), (0.08, 0.07, 1.55), "M_StoneDark")
    mb.box((-0.38, -0.07, 1.05), (0.38, 0.07, 1.2), "M_StoneDark")
    with mb.at((0, 0, 1.12), rot_x=PI / 2):
        mb.torus(0.22, 0.035, "M_StoneDark", segs=16, tsegs=4)
    mb.build("grave_cross_mesh", root, col)
    root["size"] = [0.8, 0.4, 1.6]
    return root


def build_pine_tree():
    root, col = G.new_asset("pine_tree", "props")
    mb = MB()
    mb.cyl((0, 0, 0), 0.28, 9.0, "M_Bark", segs=8, r_top=0.08)
    for k, (z, r) in enumerate(((2.6, 2.6), (4.4, 2.2), (6.0, 1.75), (7.4, 1.3), (8.6, 0.85))):
        mb.cyl((0, 0, z), r, 2.4, "M_Pine", segs=10, r_top=0.15, smooth=True)
    mb.build("pine_tree_mesh", root, col)
    mc = MB()
    mc.cyl((0, 0, 0), 0.35, 3.0, "M_Trim", segs=8, smooth=False)
    G.finish_collision(mc, "pine_tree", root, col)
    root["size"] = [5.2, 5.2, 11]
    return root


def build_flag_pole():
    root, col = G.new_asset("flag_pole", "props")
    mb = MB()
    mb.cyl((0, 0, 0), 0.3, 0.4, "M_StoneRough", segs=8)
    mb.cyl((0, 0, 0.4), 0.07, 9.6, "M_Timber", segs=8, r_top=0.05)
    mb.sphere((0, 0, 10.05), 0.12, "M_Gold", segs=8, rings=5)
    mb.build("flag_pole_mesh", root, col)
    fb = MB()
    w, h = 1.3, 3.4
    fb.rod((0, 0, 9.6), (-w - 0.1, 0, 9.6), 0.035, "M_Iron", segs=6)
    fb.box((-w - 0.05, -0.02, 9.6 - h), (-0.05, 0.02, 9.58),
           {"-y": "M_Banner", "+y": "M_Banner", "-x": "M_ClothRed", "+x": "M_ClothRed", "-z": "M_ClothRed", "+z": "M_ClothRed"})
    fb.face([(-w - 0.05, -0.025, 9.6 - h), (-w / 2 - 0.05, -0.025, 9.6 - h), (-w - 0.05, -0.025, 9.6 - h - 0.5)], "M_ClothRed")
    fb.face([(-w / 2 - 0.05, -0.025, 9.6 - h), (-0.05, -0.025, 9.6 - h), (-0.05, -0.025, 9.6 - h - 0.5)], "M_ClothRed")
    ob = fb.build("ANIM_banner", root, col)
    G.set_origin(ob, (0, 0, 9.6))
    mc = MB()
    mc.cyl((0, 0, 0), 0.3, 3.0, "M_Trim", segs=8, smooth=False)
    G.finish_collision(mc, "flag_pole", root, col)
    root["size"] = [1.5, 0.6, 10.2]
    return root


# ----------------------------------------------------------------------------- backdrops
def build_castle_hill():
    """Hradcany: green hill with Prague Castle and the Gothic St Vitus cathedral on top, houses of Mala Strana on the
    lower slope. Front (city side) faces -Y; centre of the hill base at the origin. Backdrop only."""
    root, col = G.new_asset("castle_hill", "architecture")
    mb = MB()
    RX, RY, HT = 280.0, 140.0, 85.0

    def h(x, y):
        r2 = (x / RX) ** 2 + (y / RY) ** 2
        if r2 > 1.0:                                    # skirts fall away below ground so the grid never floats
            return -(r2 - 1.0) * 80.0
        t = max(0.0, min(1.0, (1.0 - r2) / 0.55))
        return HT * (t * t * (3 - 2 * t)) + (noise2(x / 40 + 3, y / 40, 4) - 0.5) * 6.0 * t

    def surf(u, v):
        x, y = -RX + 2 * RX * u, -RY + 2 * RY * v
        return (x, y, h(x, y) - 2.0)
    grid_surface(mb, 44, 22, surf, "M_Grass", smooth=True)
    rnd = random.Random(1300)
    for k in range(150):                                                 # woods and gardens on the slopes
        x, y = rnd.uniform(-RX * 0.9, RX * 0.9), rnd.uniform(-RY * 0.9, RY * 0.2)
        if (x / RX) ** 2 + (y / RY) ** 2 > 0.85 or (abs(x) < 120 and y > -30):
            continue
        tree_cluster(mb, x, y, h(x, y) - 1.0, rnd.uniform(3.0, 6.0), rnd, n=2)
    for k in range(60):                                                  # Mala Strana roofs climbing the slope
        x, y = rnd.uniform(-200, 200), rnd.uniform(-135, -55)
        if (x / RX) ** 2 + (y / RY) ** 2 > 0.95:
            continue
        far_house(mb, x, y, h(x, y), rnd.uniform(8, 14), rnd.uniform(8, 12), rnd.uniform(7, 11), rnd, yaw=rnd.uniform(-0.2, 0.2))
    top = HT - 2.0
    # castle palace wings along the ridge
    for (x0, x1, y0, y1, hh) in ((-130, -20, -12, 4, 18), (-20, 25, -14, 2, 22), (95, 150, -10, 4, 16), (-150, -130, -20, 10, 20)):
        mb.box((x0, y0, top - 6), (x1, y1, top + hh), "M_FarWallB")
        with mb.at((x1, 0, 0), rot_z=PI / 2):
            mb.gable_roof(y0, y1, 0, x1 - x0, top + hh, top + hh + (y1 - y0) * 0.45, "M_FarRoof", under="M_FarRoof", over=0.4)
        for f in range(3):
            for i in range(int((x1 - x0) / 4)):
                xc = x0 + 2 + i * 4
                zc = top + 2.5 + f * (hh - 4) / 3
                mb.box((xc - 0.8, y0 - 0.05, zc), (xc + 0.8, y0, zc + 2.2), "M_FarWindow")
    mb.box((-160, -22, top - 8), (160, -18, top + 4), "M_StoneRough")   # castle ramparts
    # St Vitus cathedral
    cx0, cx1, cy0, cy1 = 30.0, 92.0, -6.0, 10.0
    mb.box((cx0, cy0, top - 4), (cx1, cy1, top + 34), "M_StoneDark")
    with mb.at((cx1, 0, 0), rot_z=PI / 2):
        mb.gable_roof(cy0, cy1, 0, cx1 - cx0, top + 34, top + 50, "M_Slate", under="M_Slate", over=0.6)
    for i in range(10):                                                   # buttresses with pinnacles, tall windows
        x = cx0 + 4 + i * 6
        mb.box((x - 0.9, cy0 - 3.5, top - 4), (x + 0.9, cy0, top + 26), "M_StoneDark")
        G.spire(mb, x, cy0 - 2.6, top + 26, 0.8, 6.0, "M_StoneDark", segs=6, ball=None)
        mb.box((x + 1.8, cy0 - 0.05, top + 6), (x + 3.4, cy0, top + 28), "M_FarWindow")
    mb.box((38, -16, top - 4), (50, -4, top + 58), "M_StoneDark")        # great south tower
    with mb.at((44, -10, 0)):
        mb.lathe([(6.8, top + 58), (5.5, top + 64), (3.0, top + 70), (3.6, top + 72), (0.9, top + 82), (0.1, top + 88)],
                 "M_CopperGreen", segs=12, cap_bottom=True)
    for (x, y) in ((cx1 + 2, cy0 + 1), (cx1 + 2, cy1 - 1)):              # twin west spires
        mb.box((x - 5, y - 4, top - 4), (x + 5, y + 4, top + 44), "M_StoneDark")
        G.spire(mb, x, y, top + 44, 4.6, 34.0, "M_StoneDark", segs=8)
    mb.cyl((-150, -6, top - 4), 6.0, 26, "M_FarWall", segs=12)          # round towers at the ends
    mb.cyl((-150, -6, top + 22), 7.0, 9.0, "M_FarRoof", segs=12, r_top=0.0)
    mb.cyl((160, -2, top - 4), 5.0, 22, "M_StoneRough", segs=12)
    mb.cyl((160, -2, top + 18), 6.0, 8.0, "M_Slate", segs=12, r_top=0.0)
    mb.build("castle_hill_mesh", root, col)
    root["size"] = [2 * RX, 2 * RY, 160]
    return root


def build_city_backdrop():
    """Distant Old Town roofscape with towers (Tyn, Town Hall, bridge towers) for long views from Vysehrad."""
    root, col = G.new_asset("city_backdrop", "architecture")
    mb = MB()
    rnd = random.Random(1357)
    for k in range(170):
        x, y = rnd.uniform(-170, 170), rnd.uniform(-90, 90)
        far_house(mb, x, y, 0.0, rnd.uniform(8, 13), rnd.uniform(9, 13), rnd.uniform(8, 14), rnd, yaw=rnd.choice([0, PI / 2]) + rnd.uniform(-0.15, 0.15),
                  windows=(y < -40))
    for (x, y) in ((-6, 20), (12, 20)):                                  # Tyn spires
        mb.box((x - 4, y - 4, -2), (x + 4, y + 4, 36), "M_StoneDark")
        G.spire(mb, x, y, 36, 3.6, 22, "M_Slate", segs=8)
        for dx, dy in ((-4, -4), (4, -4), (-4, 4), (4, 4)):
            G.spire(mb, x + dx, y + dy, 36, 0.9, 8, "M_Slate", segs=6)
    mb.box((-60, -10, -2), (-52, -2, 42), "M_StoneRough")                # town hall tower
    mb.pyramid(-56, -6, 42, 9, 9, 10, "M_Slate")
    for x, y in ((-150, 70), (120, -60), (40, 80)):                      # church towers
        mb.box((x - 3, y - 3, -2), (x + 3, y + 3, 30), "M_FarWall")
        G.spire(mb, x, y, 30, 3.2, 14, "M_Slate", segs=8)
    mb.build("city_backdrop_mesh", root, col)
    root["size"] = [360, 200, 60]
    return root


def build_bridge_far():
    """Charles Bridge seen from afar: 16 arches across a 480 m river, towers at both ends (deck at z=0)."""
    root, col = G.new_asset("bridge_far", "architecture")
    mb = MB()
    L = 480.0
    ops = []
    n = 16
    for k in range(n):
        x0 = -L / 2 + 6 + k * (L - 12) / n
        ops.append(dict(xa=x0 + 4, xb=x0 + (L - 12) / n - 4, za=-12.0, zs=-5.0, kind="segment"))
    wall_with_openings(mb, -L / 2, L / 2, -12.0, 0.0, -5.5, 5.5, ops, "M_BridgeStone")
    mb.box((-L / 2, -5.5, 0.0), (L / 2, -5.0, 1.1), "M_BridgeStone")
    mb.box((-L / 2, 5.0, 0.0), (L / 2, 5.5, 1.1), "M_BridgeStone")
    for k in range(n + 1):
        x = -L / 2 + 6 + k * (L - 12) / n
        G.figure(mb, (x, -5.2, 1.1), 3.0, "M_StoneDark")
    for x in (-L / 2 - 4, L / 2 + 4):
        mb.box((x - 6, -6, -12), (x + 6, 6, 28), "M_BridgeStone")
        mb.pyramid(x, 0, 28, 12, 12, 14, "M_Slate")
    mb.build("bridge_far_mesh", root, col)
    root["size"] = [L + 20, 12, 42]
    return root


def build_road_ramp(L=16.0, W=10.0, rise=2.5):
    """Packed-earth road climbing `rise` metres over L along local +Y (low end at y=-L/2), stone sides down to -4 m.
    Stacked in a row it carries the road from the Old Town up to the Vysehrad gate."""
    root, col = G.new_asset("road_ramp", "architecture")
    mb, mc = MB(), MB()
    poly = [(-L / 2, -4.0), (L / 2, -4.0), (L / 2, rise), (-L / 2, 0.0)]
    with mb.at((0, 0, 0), rot_z=PI / 2):
        mb.prism(poly, -W / 2, W / 2, STONE, cap=STONE, side_mats=[STONE, STONE, "M_Dirt", STONE])
    for sx in (-1, 1):                                                   # kerb stones
        x = sx * (W / 2 - 0.25)
        with mb.at((0, 0, 0), rot_z=PI / 2):
            mb.prism([(-L / 2, 0.0), (L / 2, rise), (L / 2, rise + 0.25), (-L / 2, 0.25)], -x - 0.25, -x + 0.25, "M_Trim")
    with mc.at((0, 0, 0), rot_z=PI / 2):
        mc.prism(poly, -W / 2, W / 2, "M_Trim")
    mb.build("road_ramp_mesh", root, col)
    G.finish_collision(mc, "road_ramp", root, col)
    root["size"] = [W, L, rise + 4]
    return root


BUILDERS = {
    "fortress_wall": build_fortress_wall,
    "fortress_parapet": build_fortress_parapet,
    "fortress_tower": build_fortress_tower,
    "gate_tower": build_gate_tower,
    "rotunda": build_rotunda,
    "basilica": build_basilica,
    "cliff_rock_a": lambda: build_cliff_rock("cliff_rock_a", 1),
    "cliff_rock_b": lambda: build_cliff_rock("cliff_rock_b", 2),
    "rock_outcrop": build_rock_outcrop,
    "watchtower_wood": build_watchtower_wood,
    "training_dummy": build_training_dummy,
    "archery_target": build_archery_target,
    "fence_wood": build_fence_wood,
    "gravestone": build_gravestone,
    "grave_cross": build_grave_cross,
    "pine_tree": build_pine_tree,
    "flag_pole": build_flag_pole,
    "castle_hill": build_castle_hill,
    "city_backdrop": build_city_backdrop,
    "bridge_far": build_bridge_far,
    "road_ramp": build_road_ramp,
}
