"""Charles Bridge + Vltava assets (run 2): bridge towers, bridge span, statues, guard booth, embankment, jetty, boats.

Conventions as in decisions.md: facade / front faces Blender -Y (Godot +Z), pivot = centre of footprint at ground level.
Bridge pieces run along local X; the deck top is z = 0, the water surface of the Vltava is at z = -6 (WATER_Z).
"""
import math
import random

from mathutils import Vector

import build_architecture as BA
import lib_geo as G
from lib_geo import MB, arch_points, wall_with_openings
from loc_common import PI

WATER_Z = -6.0
S = "M_BridgeStone"


# ----------------------------------------------------------------------------- bridge tower
def build_bridge_tower(name="bridge_tower", lesser=False):
    """Gothic bridge tower with a gate passage along local Y (the bridge runs through it).
    Old Town tower: steep slate hip roof with four corner turrets, sculpture band over the gate (concept art, left).
    Lesser Town tower (lesser=True): taller, plainer, with the low Romanesque Judith tower attached on +X."""
    root, col = G.new_asset(name, "architecture")
    mb, mc = MB(), MB()
    W, D = 11.0, 11.0
    TH = 27.0 if not lesser else 30.0
    gate = dict(xa=-2.6, xb=2.6, za=0.0, zs=4.6, kind="pointed")
    # body with the gate passage (extruded along Y)
    wall_with_openings(mb, -W / 2, W / 2, 0.0, TH, -D / 2, D / 2, [gate], S)
    for y0, y1 in ((-D / 2 - 0.15, -D / 2), (D / 2, D / 2 + 0.15)):
        wall_with_openings(mb, gate["xa"] - 0.45, gate["xb"] + 0.45, 0.0, BA.opening_top(gate) + 0.45, y0, y1, [gate], "M_TrimDark")
    mb.box((gate["xa"], -D / 2, -0.05), (gate["xb"], D / 2, 0.0), "M_Cobble")
    # plinth + string courses + corner buttresses
    # (two halves: the plinth must not run through the gate passage, or the road looks flooded waist-high)
    for x0, x1 in ((-W / 2 - 0.25, gate["xa"] - 0.02), (gate["xb"] + 0.02, W / 2 + 0.25)):
        mb.box((x0, -D / 2 - 0.25, 0), (x1, D / 2 + 0.25, 1.0), {"+z": "M_TrimDark", "-y": S, "+y": S, "-x": S, "+x": S, "-z": S})
    for z in (9.5, 16.0, 22.0):
        mb.box((-W / 2 - 0.12, -D / 2 - 0.15, z), (W / 2 + 0.12, D / 2 + 0.15, z + 0.3), "M_TrimDark")
    for cx in (-W / 2, W / 2):
        for cy in (-D / 2, D / 2):
            mb.box((cx - 0.55, cy - 0.55, 0), (cx + 0.55, cy + 0.55, TH - 3.0), S)
            mb.pyramid(cx, cy, TH - 3.0, 1.1, 1.1, 1.2, S)
    # sculpture band over the gate on both faces (Old Town tower) / coats of arms (Lesser Town)
    for face in (-1, 1):
        y = face * D / 2
        with mb.at((0, y, 0), rot_z=0 if face < 0 else PI):
            if not lesser:
                mb.box((-4.2, -0.6, 10.0), (4.2, 0.0, 10.25), "M_TrimDark")
                for k, x in enumerate((-3.0, -1.0, 1.0, 3.0)):
                    mb.box((x - 0.6, -0.55, 10.25), (x + 0.6, 0.0, 12.6), "M_TrimDark")
                    G.figure(mb, (x, -0.4, 10.3), 2.0 if k in (1, 2) else 1.7, "M_StoneDark", pose=0.2 * (k - 1.5))
                    mb.pyramid(x, -0.3, 12.6, 1.3, 0.7, 1.4, "M_TrimDark")
                # coats of arms row
                for x in (-3.5, -1.75, 0.0, 1.75, 3.5):
                    mb.box((x - 0.4, -0.12, 7.4), (x + 0.4, 0.0, 8.3), "M_ClothRed")
                    mb.box((x - 0.18, -0.14, 7.6), (x + 0.18, -0.12, 8.1), "M_Trim")
            # windows of the upper storeys
            for z, kind in ((14.0, "pointed"), (18.0, "pointed"), (23.0, "pointed")):
                for x in ((-2.3, 2.3) if z < 20 else (0.0,)):
                    with mb.at((x, 0.0, z)):
                        BA.window_unit(mb, 1.0, 2.6, kind, "M_TrimDark")
            BA.banner(mb, 0.0 if lesser else -3.8, 0.0, 9.0 if not lesser else 13.0, 1.3, 3.4)
    for side in (-1, 1):                                                 # side faces: windows
        with mb.at((side * W / 2, 0, 0), rot_z=side * PI / 2):
            for z in (14.0, 20.0):
                BA.window_unit(mb, 1.0, 2.4, "pointed", "M_TrimDark")
    # gallery with parapet on corbels
    mb.box((-W / 2 - 0.8, -D / 2 - 0.8, TH), (W / 2 + 0.8, D / 2 + 0.8, TH + 0.45), "M_TrimDark")
    for k in range(12):
        t = (k + 0.5) / 12
        for (ax, ay, bx, by) in ((-W / 2, -D / 2 - 0.6, W / 2, -D / 2 - 0.6), (-W / 2, D / 2 + 0.6, W / 2, D / 2 + 0.6),
                                 (-W / 2 - 0.6, -D / 2, -W / 2 - 0.6, D / 2), (W / 2 + 0.6, -D / 2, W / 2 + 0.6, D / 2)):
            mb.cbox((ax + (bx - ax) * t, ay + (by - ay) * t, TH - 0.3), (0.3, 0.3, 0.6), "M_TrimDark")
    for (ax, ay, bx, by) in ((-W / 2 - 0.8, -D / 2 - 0.8, W / 2 + 0.8, -D / 2 - 0.5), (-W / 2 - 0.8, D / 2 + 0.5, W / 2 + 0.8, D / 2 + 0.8),
                             (-W / 2 - 0.8, -D / 2 - 0.8, -W / 2 - 0.5, D / 2 + 0.8), (W / 2 + 0.5, -D / 2 - 0.8, W / 2 + 0.8, D / 2 + 0.8)):
        mb.box((ax, ay, TH + 0.45), (bx, by, TH + 1.5), S)
    # roof
    if not lesser:
        mb.pyramid(0, 0, TH + 0.45, W - 0.4, D - 0.4, 15.0, "M_Slate", w_top=0.4, d_top=3.0)
        for cx in (-W / 2 - 0.3, W / 2 + 0.3):
            for cy in (-D / 2 - 0.3, D / 2 + 0.3):
                mb.cyl((cx, cy, TH - 1.5), 0.8, 3.6, S, segs=8, smooth=False)
                G.spire(mb, cx, cy, TH + 2.1, 0.95, 5.5, "M_Slate", segs=8)
        for cx in (-1.2, 1.2):
            G.spire(mb, cx, 0, TH + 14.0, 0.25, 3.5, "M_Slate", segs=6)
        with mb.at((0, -D / 2 + 1.6, TH + 4.0)):
            BA.window_unit(mb, 0.8, 1.3, "pointed", "M_TrimDark")
        mb.gable_roof(-0.7, 0.7, -D / 2 + 1.4, -D / 2 + 3.0, TH + 5.6, TH + 6.6, "M_Slate", over=0.12)
    else:
        mb.pyramid(0, 0, TH + 0.45, W - 0.2, D - 0.2, 16.0, "M_Slate")
        for cx in (-W / 2 - 0.3, W / 2 + 0.3):
            for cy in (-D / 2 - 0.3, D / 2 + 0.3):
                mb.cyl((cx, cy, TH), 0.6, 2.2, S, segs=8, smooth=False)
                G.spire(mb, cx, cy, TH + 2.2, 0.7, 3.6, "M_Slate", segs=8)
        # Judith tower (Romanesque), joined by a crenellated gate wall
        jx = W / 2 + 6.5
        mb.box((jx - 3.5, -3.5, 0), (jx + 3.5, 3.5, 17.0), "M_StoneRough")
        for z in (8.0, 12.5):
            for face in (-1, 1):
                with mb.at((jx, face * 3.5, z), rot_z=0 if face < 0 else PI):
                    BA.window_unit(mb, 0.7, 1.6, "round", "M_Trim")
        mb.pyramid(jx, 0, 17.0, 7.6, 7.6, 6.0, "M_RoofTiles")
        mb.box((W / 2, -2.0, 0), (jx - 3.5, 2.0, 9.0), "M_StoneRough")
        for k in range(3):
            mb.box((W / 2 + 0.3 + k * 1.0, -2.0, 9.0), (W / 2 + 0.8 + k * 1.0, 2.0, 9.8), "M_StoneRough")
        mc.box((W / 2, -3.5, 0), (jx + 3.5, 3.5, 17.0), "M_Trim")
    # gate passage collision: side piers + lintel
    mc.box((-W / 2 - 0.6, -D / 2 - 0.3, 0), (gate["xa"], D / 2 + 0.3, TH + 1.5), "M_Trim")
    mc.box((gate["xb"], -D / 2 - 0.3, 0), (W / 2 + 0.6, D / 2 + 0.3, TH + 1.5), "M_Trim")
    mc.box((gate["xa"], -D / 2 - 0.3, BA.opening_top(gate)), (gate["xb"], D / 2 + 0.3, TH + 1.5), "M_Trim")
    mb.build(name + "_mesh", root, col)
    G.finish_collision(mc, name, root, col)
    for i, (x, y) in enumerate(((-3.6, -D / 2), (3.6, -D / 2), (-3.6, D / 2), (3.6, D / 2))):
        f = -1 if y < 0 else 1
        G.point_light(f"LIGHT_gate_torch_{i}", (x, y + f * 0.6, 3.4), root, col, energy=80)
        tm = MB()
        with tm.at((x, y, 0), rot_z=0 if f < 0 else PI):
            tm.box((-0.06, -0.05, 2.5), (0.06, 0.0, 2.85), "M_Iron")
            tm.rod((0, -0.03, 2.6), (0, -0.42, 3.05), 0.025, "M_Iron", segs=6)
            tm.rod((0, -0.4, 2.95), (0, -0.5, 3.35), 0.05, "M_Timber", segs=6, r1=0.06)
            tm.cyl((0, -0.5, 3.32), 0.08, 0.35, "M_Fire", segs=6, r_top=0.0)
        tm.build(f"{name}_torch_{i}", root, col)
    G.marker("MARK_gate_front", (0, -D / 2 - 3.0, 0), root, col)
    G.marker("MARK_gate_back", (0, D / 2 + 3.0, 0), root, col, rot_z=PI)
    root["size"] = [W + (13 if lesser else 2), D + 2, TH + 16]
    return root


# ----------------------------------------------------------------------------- bridge span (one arch)
def build_bridge_span():
    """One 24 m bay of the Charles Bridge along local X: segmental arch, piers with cutwaters, paved deck, parapets.
    Deck top at z=0, water at z=-6; the piers reach the river bed at z=-11."""
    name = "bridge_span"
    root, col = G.new_asset(name, "architecture")
    mb, mc = MB(), MB()
    L, Wd, P = 24.0, 10.0, 0.55       # bay length, deck width between parapets, parapet thickness
    yo = Wd / 2 + P
    arch = dict(xa=-8.8, xb=8.8, za=-11.0, zs=-4.4, kind="segment")
    wall_with_openings(mb, -L / 2, L / 2, -11.0, -0.35, -yo, yo, [arch], S)
    # deck and pavement
    mb.box((-L / 2, -yo, -0.35), (L / 2, yo, -0.05), S)
    mb.box((-L / 2, -Wd / 2, -0.05), (L / 2, Wd / 2, 0.0), {"+z": "M_Cobble", "-y": S, "+y": S, "-x": S, "+x": S, "-z": S})
    # cornice under the parapet + parapets with coping
    for sy in (-1, 1):
        y0, y1 = (sy * Wd / 2, sy * yo) if sy > 0 else (sy * yo, sy * Wd / 2)
        mb.box((-L / 2, min(y0, y1) - (0.2 if sy < 0 else 0), -0.75), (L / 2, max(y0, y1) + (0.2 if sy > 0 else 0), -0.35), "M_TrimDark")
        mb.box((-L / 2, min(y0, y1), -0.05), (L / 2, max(y0, y1), 1.05), S)
        mb.box((-L / 2, min(y0, y1) - 0.06, 1.05), (L / 2, max(y0, y1) + 0.06, 1.2), "M_TrimDark")
        mc.box((-L / 2, min(y0, y1), -0.05), (L / 2, max(y0, y1), 1.3), "M_Trim")
    # half cutwaters at both ends (two neighbouring bays make one full pier), on both sides of the bridge
    for ex in (-1, 1):
        x_end = ex * L / 2
        for sy in (-1, 1):
            y_face = sy * yo
            tip = y_face + sy * 3.2
            poly_top = [(x_end, y_face), (x_end - ex * 3.2, y_face), (x_end, tip)]
            with mb.at((0, 0, 0)):
                pts = poly_top if (ex * sy) < 0 else list(reversed(poly_top))
                mb.prism(pts, -11.0, -2.2, S, plane="xy")
                cap = [(x, y) for x, y in pts]
                c = Vector((sum(p[0] for p in cap) / 3, sum(p[1] for p in cap) / 3, -2.2))
                for i in range(3):
                    a, b = cap[i], cap[(i + 1) % 3]
                    mb.face([(a[0], a[1], -2.2), (b[0], b[1], -2.2), (c.x, c.y, -0.9)], "M_TrimDark")
    # string course of dark trim along the arch ring (archivolt)
    pts_i = arch_points(arch["xa"], arch["xb"], arch["zs"], "segment")
    pts_o = arch_points(arch["xa"] - 0.5, arch["xb"] + 0.5, arch["zs"] - 0.3, "segment")
    for sy in (-1, 1):
        for k in range(len(pts_i) - 1):
            q = [pts_i[k], pts_o[k], pts_o[k + 1], pts_i[k + 1]]
            if sy > 0:
                mb.prism(q, yo, yo + 0.1, "M_TrimDark")
            else:
                mb.prism(q, -yo - 0.1, -yo, "M_TrimDark")
    mc.box((-L / 2, -yo, -1.0), (L / 2, yo, -0.05), "M_Trim")
    mb.build(name + "_mesh", root, col)
    G.finish_collision(mc, name, root, col)
    # throw points: standing on the deck by the parapet, facing out over the river
    G.marker("MARK_ledge_S", (0, -Wd / 2 + 0.9, 0), root, col)
    G.marker("MARK_ledge_N", (0, Wd / 2 - 0.9, 0), root, col, rot_z=PI)
    G.marker("MARK_pier_S", (L / 2, -yo, 1.2), root, col)
    G.marker("MARK_pier_N", (L / 2, yo, 1.2), root, col, rot_z=PI)
    root["size"] = [L, 2 * yo, 12]
    return root


def build_bridge_statue():
    """Saint on a pedestal; stands on the parapet over a pier (origin = parapet top)."""
    root, col = G.new_asset("bridge_statue", "props")
    mb = MB()
    mb.box((-0.7, -0.6, 0), (0.7, 0.6, 0.3), "M_TrimDark")
    mb.box((-0.55, -0.45, 0.3), (0.55, 0.45, 1.9), "M_StoneDark")
    mb.box((-0.7, -0.6, 1.9), (0.7, 0.6, 2.15), "M_TrimDark")
    mb.box((-0.38, -0.48, 0.75), (0.38, -0.45, 1.45), "M_Brass")                 # inscription plaque
    G.figure(mb, (0, 0, 2.15), 2.6, "M_StoneDark", pose=0.35)
    mb.rod((0.32, -0.2, 3.3), (0.42, -0.25, 5.2), 0.035, "M_Gold", segs=6)       # cross / staff
    mb.box((0.27, -0.27, 4.75), (0.57, -0.23, 4.82), "M_Gold")
    with mb.at((0, 0, 4.75), rot_x=PI / 2):
        mb.torus(0.28, 0.025, "M_Gold", segs=16, tsegs=4)                         # halo
    mb.build("bridge_statue_mesh", root, col)
    G.auto_collision(root, col, shrink=0.15)
    root["size"] = [1.4, 1.2, 5.3]
    return root


def build_guard_booth():
    """Wooden watch booth of the bridge guard (on the deck by the parapet), lion banner, counter window to -Y."""
    root, col = G.new_asset("guard_booth", "props")
    mb = MB()
    w, d, h = 2.4, 2.2, 2.6
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((sx * w / 2 - 0.1, sy * d / 2 - 0.1, 0), (sx * w / 2 + 0.1, sy * d / 2 + 0.1, h), "M_Timber")
    mb.box((-w / 2, -d / 2, 0), (w / 2, d / 2, 0.1), "M_WoodDark")
    mb.box((-w / 2, d / 2 - 0.06, 0), (w / 2, d / 2, h), "M_WoodLight")
    mb.box((-w / 2, -d / 2, 0), (-w / 2 + 0.06, d / 2, h), "M_WoodLight")
    mb.box((w / 2 - 0.06, -d / 2, 0), (w / 2, d / 2, h), "M_WoodLight")
    mb.box((-w / 2, -d / 2, 0), (w / 2, -d / 2 + 0.06, 1.1), "M_WoodLight")
    mb.box((-w / 2 - 0.05, -d / 2 - 0.25, 1.05), (w / 2 + 0.05, -d / 2 + 0.06, 1.15), "M_WoodDark")      # counter
    mb.box((-w / 2, -d / 2, h - 0.5), (w / 2, -d / 2 + 0.06, h), "M_WoodLight")
    mb.pyramid(0, 0, h, w + 0.8, d + 0.8, 2.2, "M_Shingle")
    G.spire(mb, 0, 0, h + 2.1, 0.12, 0.5, "M_Iron", segs=6)
    mb.box((w / 2 + 0.01, -0.45, 0.6), (w / 2 + 0.04, 0.45, 2.2), {"+x": "M_Banner", "-x": "M_ClothRed", "-y": "M_ClothRed",
                                                                   "+y": "M_ClothRed", "-z": "M_ClothRed", "+z": "M_ClothRed"})
    mb.rod((-0.3, -d / 2 + 0.3, 1.15), (-0.3, -d / 2 + 0.3, 1.4), 0.08, "M_Iron", segs=8)              # lantern on counter
    mb.sphere((-0.3, -d / 2 + 0.3, 1.45), 0.09, "M_LanternGlass", segs=8, rings=5)
    mb.build("guard_booth_mesh", root, col)
    G.auto_collision(root, col, shrink=0.05)
    G.point_light("LIGHT_booth", (-0.3, -d / 2 + 0.3, 1.6), root, col, energy=40, distance=7)
    G.marker("MARK_guard_post", (0.6, -d / 2 - 0.9, 0), root, col)
    root["size"] = [w + 0.8, d + 0.8, h + 2.6]
    return root


# ----------------------------------------------------------------------------- river banks
def build_embankment():
    """16 m stone river wall: top at z=0 (street level), face to -Y (water side) down to the river bed."""
    root, col = G.new_asset("embankment", "architecture")
    mb, mc = MB(), MB()
    mb.box((-8, 0, -11.0), (8, 2.0, -0.25), S)
    mb.box((-8.05, -0.25, -0.25), (8.05, 2.2, 0.0), {"+z": "M_TrimDark", "-y": "M_TrimDark", "+y": "M_TrimDark", "-x": "M_TrimDark",
                                                      "+x": "M_TrimDark", "-z": "M_TrimDark"})
    for x in (-6.0, 6.0):                                             # mooring rings
        with mb.at((x, -0.02, -4.0), rot_x=PI / 2):
            mb.torus(0.18, 0.025, "M_Iron", segs=12, tsegs=4)
    rnd = random.Random(5)
    for k in range(6):                                                # algae line at the water
        x = -7.5 + k * 3.0
        mb.box((x, -0.03, WATER_Z - 0.4), (x + 2.8, 0.0, WATER_Z + 0.25 + rnd.uniform(0, 0.2)), "M_Leaves")
    mc.box((-8, 0, -11.0), (8, 2.2, 0.0), "M_Trim")
    mc.box((-8, -0.25, 0.0), (8, 0.15, 1.0), "M_Trim")               # invisible kerb so nobody walks into the river
    mb.build("embankment_mesh", root, col)
    G.finish_collision(mc, "embankment", root, col)
    G.marker("MARK_ledge", (0, 0.9, 0), root, col)
    root["size"] = [16, 2.2, 11]
    return root


def build_jetty():
    """Wooden landing stage on piles; origin at deck level (place it ~0.6 m above the water)."""
    root, col = G.new_asset("jetty", "props")
    mb = MB()
    L, w = 12.0, 3.0
    for k in range(13):
        x = -L / 2 + k * 1.0
        mb.box((x, -w / 2, -0.12), (x + 0.95, w / 2, 0.0), "M_WoodLight")
    for x in (-L / 2 + 0.3, -L / 4, 0.0, L / 4, L / 2 - 0.3):
        for sy in (-1, 1):
            mb.cyl((x, sy * (w / 2 - 0.1), -3.0), 0.13, 3.6, "M_Timber", segs=8)
            mb.cyl((x, sy * (w / 2 - 0.1), 0.6), 0.15, 0.08, "M_Rope", segs=8)
    mb.box((-L / 2, -w / 2 - 0.08, -0.35), (L / 2, -w / 2, -0.12), "M_Timber")
    mb.box((-L / 2, w / 2, -0.35), (L / 2, w / 2 + 0.08, -0.12), "M_Timber")
    mb.build("jetty_mesh", root, col)
    root["size"] = [L, w, 4]
    return root


def _hull(mb, L, B, H, mat="M_WoodDark", rim="M_Timber", seed=1):
    """Open wooden hull along local X, waterline at z=0, keel at z=-H*0.5."""
    n = 12
    rings = []
    for i in range(n + 1):
        t = i / n
        x = -L / 2 + L * t
        w = B / 2 * (math.sin(PI * t) ** 0.55) + 0.02
        zb = -H * 0.5 + H * 0.35 * abs(2 * t - 1) ** 3
        zt = H * 0.5 + H * 0.25 * abs(2 * t - 1) ** 2
        rings.append([(x, -w, zt), (x, -w * 0.92, (zt + zb) / 2), (x, -w * 0.5, zb), (x, 0, zb - 0.03),
                      (x, w * 0.5, zb), (x, w * 0.92, (zt + zb) / 2), (x, w, zt)])
    idx = [[mb._v(p) for p in r] for r in rings]
    for i in range(n):
        for k in range(len(rings[0]) - 1):
            a, b = idx[i][k], idx[i][k + 1]
            c, d = idx[i + 1][k + 1], idx[i + 1][k]
            mb._quad_idx([a, d, c, b], mat, "world", True, False)        # outside
            mb._quad_idx([a, b, c, d], "M_WoodLight", "world", True, False)  # inside
    for i in range(n):
        for side in (0, len(rings[0]) - 1):
            p, q = rings[i][side], rings[i + 1][side]
            mb.rod(p, q, 0.035, rim, segs=5)


def build_boat_row():
    root, col = G.new_asset("boat_row", "props")
    mb = MB()
    _hull(mb, 4.6, 1.4, 0.7)
    for x in (-0.8, 0.6):
        mb.box((x - 0.15, -0.6, 0.1), (x + 0.15, 0.6, 0.16), "M_WoodLight")
    for sy in (-1, 1):
        mb.rod((0.0, sy * 0.66, 0.35), (-1.6, sy * 1.6, -0.25), 0.03, "M_WoodLight", segs=6)        # oars
        mb.box((-1.9, sy * 1.6 - 0.08, -0.3), (-1.3, sy * 1.6 + 0.08, -0.26), "M_WoodLight")
    mb.build("boat_row_mesh", root, col)
    root["size"] = [4.6, 1.4, 0.9]
    return root


def build_boat_barge():
    """Cargo barge with a canvas hoop cover and barrels (as on the concept art)."""
    root, col = G.new_asset("boat_barge", "props")
    mb = MB()
    _hull(mb, 9.0, 2.6, 1.0, seed=3)
    mb.box((-3.8, -1.05, 0.05), (3.8, 1.05, 0.12), "M_WoodLight")
    for k in range(7):                                                  # canvas cover over hoops
        x = -2.4 + k * 0.6
        pts = [(x, 1.1 * math.cos(PI * t / 8), 0.12 + 1.3 * math.sin(PI * t / 8)) for t in range(9)]
        for a, b in zip(pts[:-1], pts[1:]):
            mb.rod(a, b, 0.025, "M_Timber", segs=4)
    ring = [(1.1 * math.cos(PI * t / 10), 0.12 + 1.3 * math.sin(PI * t / 10)) for t in range(11)]
    for a, b in zip(ring[:-1], ring[1:]):
        mb.face([(-2.45, a[0], a[1]), (-2.45, b[0], b[1]), (1.25, b[0], b[1]), (1.25, a[0], a[1])], "M_Canvas")
        mb.face([(1.25, a[0], a[1]), (1.25, b[0], b[1]), (-2.45, b[0], b[1]), (-2.45, a[0], a[1])], "M_Canvas")
    for x, y in ((2.0, -0.5), (2.0, 0.5), (2.8, 0.0)):
        with mb.at((x, y, 0.12)):
            mb.lathe([(0.28 + 0.04 * math.sin(PI * k / 6), 0.8 * k / 6) for k in range(7)], "M_WoodLight", segs=12, cap_mat="M_WoodDark")
    mb.rod((3.9, 0, 0.5), (4.2, 0, 1.6), 0.04, "M_Timber", segs=6)                                   # steering oar
    mb.build("boat_barge_mesh", root, col)
    root["size"] = [9.0, 2.6, 1.6]
    return root


BUILDERS = {
    "bridge_tower": lambda: build_bridge_tower("bridge_tower", False),
    "bridge_tower_lesser": lambda: build_bridge_tower("bridge_tower_lesser", True),
    "bridge_span": build_bridge_span,
    "bridge_statue": build_bridge_statue,
    "guard_booth": build_guard_booth,
    "embankment": build_embankment,
    "jetty": build_jetty,
    "boat_row": build_boat_row,
    "boat_barge": build_boat_barge,
}
