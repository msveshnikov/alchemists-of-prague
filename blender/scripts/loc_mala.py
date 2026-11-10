"""Mala Strana assets (run 2): half-timbered houses, tavern, castle stairs, retaining / garden walls, planter, St Nicholas.

Houses keep the Task 1 contract so the Godot interior / defenestration code works unchanged:
INT_door_<name> (pivot on hinge), INT_window_<name>_<i> (+ _shutter_L/R) on the first upper floor, MARK_door, MARK_interior,
MARK_window_<i>. Facade faces -Y. Upper floor height and depth are listed in HOUSE_DIMS in scripts/world.gd.
"""
import math
import random

from mathutils import Vector

import build_architecture as BA
import lib_geo as G
from lib_geo import MB, wall_with_openings
from loc_common import PI

TIMBER_D = 11.0
TIMBER_HG = 3.8
TIMBER_HS = 3.1


def defen_window(name, i, o, off, root, col, y_glass, mat_frame="M_Timber"):
    """Interactive window (glass + mullions node) with hinged shutters and the MARK_window under it."""
    wm = MB()
    with wm.at(off):
        BA.glass(wm, o, y_glass)
        BA.mullions(wm, o, y_glass - 0.04, y_glass + 0.02, mat_frame)
    wob = wm.build(f"INT_window_{name}_{i}", root, col)
    wob["interactive"] = "window"
    xc = (o["xa"] + o["xb"]) / 2
    G.set_origin(wob, Vector(off) + Vector((xc, y_glass, o["za"])))
    top = BA.opening_top(o)
    for side, hx in (("L", o["xa"] - 0.17), ("R", o["xb"] + 0.17)):
        sm = MB()
        sw = 0.47
        x0, x1 = (hx - sw, hx) if side == "L" else (hx, hx + sw)
        with sm.at(off):
            sm.box((x0, -0.14, o["za"] - 0.05), (x1, -0.09, top), "M_WoodDark")
            for zz in (o["za"] + 0.25, top - 0.35):
                sm.box((x0 + 0.03, -0.155, zz), (x1 - 0.03, -0.14, zz + 0.06), "M_Iron")
        so = sm.build(f"INT_window_{name}_{i}_shutter_{side}", root, col)
        G.set_origin(so, Vector(off) + Vector((hx, -0.115, o["za"])))
        so.parent = wob
        so.location = so.location - wob.location
        so["interactive"] = "shutter"
    G.marker(f"MARK_window_{i}", Vector(off) + Vector((xc, -1.2, 0)), root, col)
    return wob


def timber_frame(mb, x0, x1, z0, z1, ops, y=-0.07, seed=0):
    """Dark timber framing on a plastered storey: sill & head beams, posts beside windows, braces in the blank panels."""
    rnd = random.Random(seed)
    T = "M_Timber"
    mb.box((x0, y, z0), (x1, 0.0, z0 + 0.22), T)
    mb.box((x0, y, z1 - 0.2), (x1, 0.0, z1), T)
    posts = [x0 + 0.1, x1 - 0.1]
    for o in ops:
        posts += [o["xa"] - 0.25, o["xb"] + 0.25]
    posts = sorted(set(round(p, 2) for p in posts))
    for p in posts:
        mb.box((p - 0.1, y, z0 + 0.2), (p + 0.1, 0.0, z1 - 0.2), T)
    for o in ops:                                                        # rails under / over the window
        mb.box((o["xa"] - 0.25, y, o["za"] - 0.18), (o["xb"] + 0.25, 0.0, o["za"] - 0.04), T)
    for a, b in zip(posts[:-1], posts[1:]):
        inside = any(o["xa"] - 0.3 <= (a + b) / 2 <= o["xb"] + 0.3 for o in ops)
        if inside or b - a < 0.6:
            continue
        zc0, zc1 = z0 + 0.22, z1 - 0.2
        L = math.hypot(b - a, zc1 - zc0)
        ang = math.atan2(zc1 - zc0, b - a)
        if rnd.random() < 0.5:
            ang = -ang
        with mb.at(((a + b) / 2, 0, (zc0 + zc1) / 2), rot_y=-ang):
            mb.box((-L / 2 + 0.1, y + 0.005, -0.09), (L / 2 - 0.1, 0.0, 0.09), T)


def build_timber_house(name, W, n_up, plaster, roof="M_RoofTiles", style="gable", seed=1, ground="M_StoneRough",
                       tavern=False):
    rnd = random.Random(seed)
    root, col = G.new_asset(name, "architecture")
    D, Hg, Hs = TIMBER_D, TIMBER_HG, TIMBER_HS
    Hw = Hg + n_up * Hs
    off = (-W / 2, -D / 2, 0.0)
    mb, mc = MB(), MB()
    with mb.at(off), mc.at(off):
        # ---- ground floor: rubble stone / plaster, real door + windows, vestibule behind the door
        xd = W / 2 + (rnd.choice([-1, 1]) * min(1.4, W / 2 - 1.6) if not tavern else 0.0)
        door = dict(xa=xd - 0.7, xb=xd + 0.7, za=0.0, zs=2.25, kind="round")
        wins = []
        for xc in ([xd - 2.4, xd + 2.4] if not tavern else [xd - 3.4, xd - 1.9, xd + 1.9, xd + 3.4]):
            if 0.7 < xc - 0.6 and xc + 0.6 < W - 0.7:
                wins.append(dict(xa=xc - 0.6, xb=xc + 0.6, za=0.95, zs=2.3, kind="segment"))
        wall_with_openings(mb, 0, W, 0, Hg, 0.0, 0.5, [door] + wins, ground)
        wall_with_openings(mb, door["xa"] - 0.25, door["xb"] + 0.25, 0.0, BA.opening_top(door) + 0.25, -0.12, 0.0, [door], "M_Trim")
        for o in wins:
            BA.window_frame(mb, o)
            BA.glass(mb, o, 0.3)
            BA.mullions(mb, o, 0.26, 0.32, "M_Iron")
        BA.door_leaf(f"INT_door_{name}", door, 0.3, 0.4, door["xa"] + 0.05, root, col, off)
        mb.box((-0.05, -0.12, 0), (W + 0.05, 0.0, 0.5), "M_Ashlar")                                      # plinth
        vx0, vx1, vy0, vy1, vz = xd - 1.4, xd + 1.4, 0.5, 3.6, 3.2
        mb.box((vx0, vy0, 0.0), (vx1, vy1, 0.08), "M_WoodDark")
        mb.box((vx0 - 0.2, vy0, 0), (vx0, vy1, vz), "M_Plaster_beige")
        mb.box((vx1, vy0, 0), (vx1 + 0.2, vy1, vz), "M_Plaster_beige")
        mb.box((vx0 - 0.2, vy1, 0), (vx1 + 0.2, vy1 + 0.2, vz), "M_Plaster_beige")
        mb.box((vx0 - 0.2, vy0, vz), (vx1 + 0.2, vy1 + 0.2, vz + 0.2), "M_Timber")
        mc.box((0, 0, 0), (door["xa"], 0.5, Hg), "M_Trim")
        mc.box((door["xb"], 0, 0), (W, 0.5, Hg), "M_Trim")
        mc.box((door["xa"], 0, BA.opening_top(door)), (door["xb"], 0.5, Hg), "M_Trim")
        mc.box((0, 0.5, 0), (vx0, D, Hg), "M_Trim")
        mc.box((vx1, 0.5, 0), (W, D, Hg), "M_Trim")
        mc.box((vx0, vy1, 0), (vx1, D, Hg), "M_Trim")
        mc.box((vx0, 0.5, vz), (vx1, vy1, Hg), "M_Trim")
        mb.box((-0.04, -0.14, Hg - 0.12), (W + 0.04, 0.0, Hg + 0.12), "M_Timber")                     # jetty beam
        for k in range(int(W / 0.9) + 1):                                                             # joist ends
            x = 0.2 + k * (W - 0.4) / max(1, int(W / 0.9))
            mb.box((x - 0.08, -0.26, Hg - 0.32), (x + 0.08, 0.0, Hg - 0.12), "M_Timber")
        # ---- upper storeys: plaster in timber framing
        nw = max(2, int((W - 0.6) / 2.4))
        for s in range(n_up):
            zb, zt = Hg + s * Hs, Hg + (s + 1) * Hs
            ops = [dict(xa=(i + 0.5) * W / nw - 0.5, xb=(i + 0.5) * W / nw + 0.5, za=zb + 0.9, zs=zb + 2.35, kind="flat")
                   for i in range(nw)]
            wall_with_openings(mb, 0, W, zb, zt, 0.0, 0.45, ops, plaster)
            timber_frame(mb, 0, W, zb, zt, ops, seed=seed * 7 + s)
            for i, o in enumerate(ops):
                if s == 0:
                    defen_window(name, i, o, off, root, col, 0.27)
                else:
                    BA.glass(mb, o, 0.27)
                    BA.mullions(mb, o, 0.23, 0.29, "M_Timber")
                if rnd.random() < 0.6:
                    BA.flower_box(mb, o["xa"] + 0.02, o["xb"] - 0.02, o["za"] - 0.1, -0.08, seed * 31 + s * 7 + i)
        mb.box((0, 0.5, 0), (0.4, D, Hw), plaster)
        mb.box((W - 0.4, 0.5, 0), (W, D, Hw), plaster)
        mb.box((0, D - 0.4, 0), (W, D, Hw), plaster)
        mb.box((0.4, 3.8, Hg - 0.4), (W - 0.4, D - 0.4, Hg - 0.35), "M_Timber")
        mc.box((0, 0, Hg - 0.35), (W, D, Hw), "M_Trim")
        for s in range(n_up):                                                                         # rear windows
            for i in range(nw):
                with mb.at(((i + 0.5) * W / nw, D, Hg + s * Hs + 0.9), rot_z=PI):
                    BA.window_unit(mb, 0.9, 1.4)
        # ---- roof
        mb.box((-0.1, -0.3, Hw - 0.05), (W + 0.1, D + 0.3, Hw + 0.15), "M_Timber")
        if style == "gable":          # gable to the street (ridge along Y), framed gable wall
            zr = Hw + 0.15 + W / 2 * 1.45
            mb.prism([(0, Hw + 0.15), (W, Hw + 0.15), (W / 2, zr - 0.1)], 0.0, 0.4, plaster)
            for k in range(1, 4):
                z = Hw + 0.15 + (zr - Hw) * k / 4
                half = W / 2 * (1 - k / 4)
                mb.box((W / 2 - half, -0.07, z - 0.09), (W / 2 + half, 0.0, z + 0.09), "M_Timber")
            mb.box((W / 2 - 0.1, -0.07, Hw + 0.15), (W / 2 + 0.1, 0.0, zr - 0.3), "M_Timber")
            with mb.at((W / 2 - (1.0 if W > 7 else 0), 0.0, Hw + 0.9)):
                BA.window_unit(mb, 0.8, 1.2, "flat", "M_Timber")
            if W > 7:
                with mb.at((W / 2 + 1.0, 0.0, Hw + 0.9)):
                    BA.window_unit(mb, 0.8, 1.2, "flat", "M_Timber")
            mb.gable_roof(0, W, -0.45, D + 0.3, Hw + 0.15, zr, roof, over=0.45)
            mb.prism([(0, Hw), (W, Hw), (W / 2, zr - 0.2)], D - 0.4, D, plaster)
        else:                         # eaves to the street (ridge along X) with a dormer
            zr = Hw + 0.15 + D / 2 * 1.15
            with mb.at((W, 0, 0), rot_z=PI / 2):
                mb.gable_roof(-0.45, D + 0.45, 0.0, W, Hw + 0.15, zr, roof, over=0.5)
            with mb.at((0.0, 0, 0), rot_z=PI / 2):
                mb.prism([(0, Hw + 0.15), (D, Hw + 0.15), (D / 2, zr - 0.2)], -0.4, 0.0, plaster)
                mb.prism([(0, Hw + 0.15), (D, Hw + 0.15), (D / 2, zr - 0.2)], -W, -W + 0.4, plaster)
            xdm = W / 2
            zd = Hw + 1.2
            mb.box((xdm - 0.8, 1.0, zd - 0.6), (xdm + 0.8, 3.2, zd + 1.3), plaster)
            with mb.at((xdm, 1.0, zd - 0.3)):
                BA.window_unit(mb, 0.8, 1.1, "flat", "M_Timber")
            with mb.at((xdm, 0, 0)):
                mb.gable_roof(-1.0, 1.0, 0.8, 3.4, zd + 1.3, zd + 2.3, roof, over=0.15)
        # chimney
        cx = W * (0.7 if rnd.random() < 0.5 else 0.3)
        mb.box((cx - 0.35, D * 0.6 - 0.35, Hw), (cx + 0.35, D * 0.6 + 0.35, zr + 0.6), "M_StoneRough")
        mb.box((cx - 0.45, D * 0.6 - 0.45, zr + 0.6), (cx + 0.45, D * 0.6 + 0.45, zr + 0.75), "M_Trim")
        # ---- tavern extras: striped awning on posts, hanging sign, lanterns
        if tavern:
            aw_y = -2.8
            pts = [(0.3, 0.0, 3.3), (W - 0.3, 0.0, 3.3), (W - 0.3, aw_y, 2.55), (0.3, aw_y, 2.55)]
            mb.face(pts, "M_CanvasStriped")
            mb.face(list(reversed(pts)), "M_CanvasStriped")
            for k in range(int((W - 0.6) / 0.5)):                                                 # scalloped valance
                x = 0.3 + k * 0.5
                mb.face([(x, aw_y, 2.55), (x + 0.5, aw_y, 2.55), (x + 0.25, aw_y, 2.25)], "M_ClothRed")
                mb.face([(x + 0.25, aw_y, 2.25), (x + 0.5, aw_y, 2.55), (x, aw_y, 2.55)], "M_ClothRed")
            for x in (0.4, W / 2, W - 0.4):
                mb.cyl((x, aw_y + 0.05, 0), 0.07, 2.55, "M_Timber", segs=8)
            mb.rod((0.3, aw_y, 2.55), (W - 0.3, aw_y, 2.55), 0.05, "M_Timber", segs=6)
            sx = -0.0
            mb.rod((sx + 0.2, -0.05, 3.9), (sx + 0.2, -1.35, 3.9), 0.035, "M_Iron", segs=6)            # sign bracket at the corner
            mb.rod((sx + 0.2, -0.05, 3.5), (sx + 0.2, -0.95, 3.9), 0.025, "M_Iron", segs=6)
            with mb.at((sx + 0.2, -0.95, 3.25)):
                mb.box((-0.04, -0.4, -0.45), (0.04, 0.4, 0.45), {"-x": "M_TavernSign", "+x": "M_TavernSign", "-y": "M_WoodDark",
                                                                "+y": "M_WoodDark", "-z": "M_WoodDark", "+z": "M_WoodDark"})
            for x in (door["xa"] - 0.5, door["xb"] + 0.5):
                mb.rod((x, 0.0, 2.6), (x, -0.4, 2.6), 0.02, "M_Iron", segs=5)
                mb.cyl((x, -0.4, 2.2), 0.1, 0.36, "M_LanternGlass", segs=6)
                mb.pyramid(x, -0.4, 2.56, 0.24, 0.24, 0.16, "M_Iron")
    mb.build(name + "_mesh", root, col)
    G.finish_collision(mc, name, root, col)
    G.marker("MARK_door", Vector(off) + Vector((xd, -1.2, 0)), root, col)
    G.marker("MARK_interior", Vector(off) + Vector((xd, 2.2, 0.08)), root, col, rot_z=PI)
    if tavern:
        for i, x in enumerate((door["xa"] - 0.5, door["xb"] + 0.5)):
            G.point_light(f"LIGHT_tavern_lantern_{i}", Vector(off) + Vector((x, -0.5, 2.3)), root, col, energy=60, distance=9)
        G.marker("MARK_innkeeper", Vector(off) + Vector((xd + 1.6, -1.0, 0)), root, col)
        G.marker("MARK_inn", Vector(off) + Vector((xd, -1.4, 0)), root, col)
    root["size"] = [W, D, zr]
    return root


# ----------------------------------------------------------------------------- castle stairs
def build_castle_stairs():
    """Monumental stone stairs (Zamecke schody): 5 m wide, two flights + landing, rising 8 m along local +Y.
    Bottom at y=-14 (z=0), top at y=+14 (z=8), so the front faces -Y like everything else."""
    root, col = G.new_asset("castle_stairs", "architecture")
    mb, mc = MB(), MB()
    Wd = 5.0
    flights = [(-14.0, -2.0, 0.0, 4.0), (2.0, 14.0, 4.0, 8.0)]
    n = 16
    for (y0, y1, z0, z1) in flights:
        run = (y1 - y0) / n
        rise = (z1 - z0) / n
        for k in range(n):
            ya = y0 + k * run
            mb.box((-Wd / 2, ya, 0.0 if k == 0 else z0), (Wd / 2, y1, z0 + (k + 1) * rise),
                   {"+z": "M_Trim", "-y": "M_Ashlar", "+y": "M_Ashlar", "-x": "M_Ashlar", "+x": "M_Ashlar", "-z": "M_Ashlar"})
        # ramp collider for smooth walking
        with mc.at((0, 0, 0), rot_z=PI / 2):
            mc.prism([(y0, z0 - 0.4), (y1, z1 - 0.4), (y1, z1), (y0, z0)], -Wd / 2, Wd / 2, "M_Trim")
    mb.box((-Wd / 2, -2.0, 0.0), (Wd / 2, 2.0, 4.0), {"+z": "M_Cobble", "-y": "M_Ashlar", "+y": "M_Ashlar", "-x": "M_Ashlar",
                                                       "+x": "M_Ashlar", "-z": "M_Ashlar"})
    mb.box((-Wd / 2, 14.0, 0.0), (Wd / 2, 16.0, 8.0), {"+z": "M_Cobble", "-y": "M_Ashlar", "+y": "M_Ashlar", "-x": "M_Ashlar",
                                                        "+x": "M_Ashlar", "-z": "M_Ashlar"})
    mc.box((-Wd / 2, -2.0, 0.0), (Wd / 2, 2.0, 4.0), "M_Trim")
    mc.box((-Wd / 2, 14.0, 0.0), (Wd / 2, 16.0, 8.0), "M_Trim")
    # side walls following the slope, 1.0 m above the treads, coping on top
    prof = [(-14.0, 0.0), (-2.0, 4.0), (2.0, 4.0), (14.0, 8.0), (16.0, 8.0)]
    for sx in (-1, 1):
        xa, xb = (sx * Wd / 2, sx * (Wd / 2 + 0.6)) if sx > 0 else (sx * (Wd / 2 + 0.6), sx * Wd / 2)
        for (ya, za), (yb, zb) in zip(prof[:-1], prof[1:]):
            with mb.at((0, 0, 0), rot_z=PI / 2):
                mb.prism([(ya, 0.0), (yb, 0.0), (yb, zb + 1.0), (ya, za + 1.0)], -xb, -xa, "M_StoneRough")
                mb.prism([(ya, za + 1.0), (yb, zb + 1.0), (yb, zb + 1.18), (ya, za + 1.18)], -xb - 0.06, -xa + 0.06, "M_Trim")
            with mc.at((0, 0, 0), rot_z=PI / 2):
                mc.prism([(ya, 0.0), (yb, 0.0), (yb, zb + 1.3), (ya, za + 1.3)], -xb, -xa, "M_Trim")
    # newel posts with lanterns at bottom, landing and top
    lights = []
    for (y, z) in ((-14.0, 0.0), (0.0, 4.0), (15.0, 8.0)):
        for sx in (-1, 1):
            x = sx * (Wd / 2 + 0.3)
            mb.box((x - 0.4, y - 0.4, z), (x + 0.4, y + 0.4, z + 1.6), "M_Trim")
            mb.pyramid(x, y, z + 1.6, 0.9, 0.9, 0.35, "M_Trim")
            if sx > 0:
                mb.cyl((x, y, z + 1.95), 0.05, 0.6, "M_Iron", segs=6)
                mb.cyl((x, y, z + 2.55), 0.13, 0.42, "M_LanternGlass", segs=6)
                mb.pyramid(x, y, z + 2.97, 0.32, 0.32, 0.22, "M_Iron")
                lights.append((x, y, z + 2.75))
    mb.build("castle_stairs_mesh", root, col)
    G.finish_collision(mc, "castle_stairs", root, col)
    for i, p in enumerate(lights):
        G.point_light(f"LIGHT_stairs_{i}", p, root, col, energy=70, distance=10)
    G.marker("MARK_stairs_bottom", (0, -15.5, 0), root, col, rot_z=PI)
    G.marker("MARK_stairs_top", (0, 15.5, 8.0), root, col)
    root["size"] = [Wd + 1.2, 30, 9.5]
    return root


def build_retaining_wall(name="retaining_wall", niche=False, H=8.0):
    """16 m wall holding up the upper terrace: face at y=0 looking -Y, top at z=H with a parapet on the terrace side."""
    root, col = G.new_asset(name, "architecture")
    mb, mc = MB(), MB()
    mb.box((-8, 0, 0), (8, 2.0, H), "M_StoneRough")
    mb.box((-8.05, -0.12, 0), (8.05, 0.0, 0.6), "M_Ashlar")
    for x in (-8.0, 0.0, 8.0):                                           # buttresses
        if niche and x == 0.0:
            continue
        with mb.at((x, 0, 0), rot_z=PI / 2):
            mb.prism([(0.0, 0.0), (-0.9, 0.0), (-0.3, H - 1.5), (0.0, H - 1.2)], -0.5, 0.5, "M_Ashlar")
    mb.box((-8.05, -0.15, H - 0.2), (8.05, 2.0, H), "M_Trim")
    mb.box((-8.0, -0.1, H), (8.0, 0.5, H + 1.0), "M_StoneRough")         # parapet
    mb.box((-8.05, -0.16, H + 1.0), (8.05, 0.56, H + 1.15), "M_Trim")
    rnd = random.Random(11 if niche else 12)
    for k in range(5):                                                   # ivy
        x = rnd.uniform(-7, 7)
        mb.box((x - rnd.uniform(0.5, 1.2), -0.08, rnd.uniform(1.5, 4.0)), (x + rnd.uniform(0.5, 1.2), -0.02, H - 0.2), "M_Leaves")
    if niche:
        o = dict(xa=-0.9, xb=0.9, za=1.6, zs=4.2, kind="round")
        wall_with_openings(mb, -1.5, 1.5, 1.2, 5.8, -0.6, 0.0, [o], "M_Trim")              # frame around the recess
        mb.box((-0.9, -0.05, 1.6), (0.9, 0.0, 4.2 + 0.9), "M_StoneDark")                     # back of the niche
        mb.box((-1.0, -0.75, 1.45), (1.0, 0.0, 1.62), "M_Trim")                              # sill / plinth
        mb.prism([(-1.7, 5.8), (1.7, 5.8), (0.0, 6.7)], -0.8, -0.0, "M_RoofTiles")
        G.figure(mb, (0, -0.32, 1.62), 2.1, "M_Statue", pose=0.25)
        mb.rod((1.8, 0.0, 3.0), (1.8, -0.5, 3.0), 0.025, "M_Iron", segs=5)
        mb.cyl((1.8, -0.5, 2.6), 0.11, 0.38, "M_LanternGlass", segs=6)
        mb.pyramid(1.8, -0.5, 2.98, 0.26, 0.26, 0.18, "M_Iron")
    mc.box((-8, -0.15, 0), (8, 2.0, H + 1.3), "M_Trim")
    mb.build(name + "_mesh", root, col)
    G.finish_collision(mc, name, root, col)
    if niche:
        G.point_light("LIGHT_niche", (1.8, -0.6, 2.8), root, col, energy=55, distance=9)
    G.marker("MARK_ledge", (0, 1.1, H), root, col)
    root["size"] = [16, 2.6, H + 1.2]
    return root


def build_garden_wall():
    root, col = G.new_asset("garden_wall", "architecture")
    mb, mc = MB(), MB()
    mb.box((-4, -0.25, 0), (4, 0.25, 2.4), "M_StoneRough")
    with mb.at((0, 0, 0), rot_z=PI / 2):
        mb.prism([(-0.42, 2.4), (0.42, 2.4), (0.0, 2.72)], -4.1, 4.1, "M_RoofTiles")
    rnd = random.Random(21)
    for k in range(3):
        x = rnd.uniform(-3.4, 3.4)
        mb.sphere((x, 0.5, 2.6), (1.0, 0.6, 0.6), "M_Leaves", segs=8, rings=5, noise=0.2, seed=k)
        mb.box((x - 0.5, -0.29, 1.0), (x + 0.5, -0.25, 2.4), "M_Leaves")
    mc.box((-4, -0.3, 0), (4, 0.3, 2.8), "M_Trim")
    mb.build("garden_wall_mesh", root, col)
    G.finish_collision(mc, "garden_wall", root, col)
    root["size"] = [8, 0.8, 2.8]
    return root


def build_planter():
    root, col = G.new_asset("planter", "props")
    mb = MB()
    mb.box((-0.7, -0.25, 0), (0.7, 0.25, 0.5), "M_WoodDark")
    for x in (-0.7, 0.66):
        mb.box((x, -0.27, 0), (x + 0.04, 0.27, 0.55), "M_Timber")
    for k in range(8):
        x = -0.6 + k * 0.17
        mb.sphere((x, 0.0, 0.58), (0.16, 0.18, 0.14), "M_Flowers", segs=7, rings=4, noise=0.2, seed=k)
    mb.build("planter_mesh", root, col)
    G.auto_collision(root, col)
    root["size"] = [1.4, 0.5, 0.75]
    return root


# ----------------------------------------------------------------------------- St Nicholas (baroque landmark)
def build_st_nicholas():
    """Baroque St Nicholas church of Mala Strana (anachronism, but it is on the concept art): green copper dome and
    bell tower. Facade faces -Y. Used as a landmark at the end of the square / on the skyline."""
    root, col = G.new_asset("st_nicholas", "architecture")
    mb, mc = MB(), MB()
    P = "M_Plaster_cream"
    mb.box((-11, 0, 0), (11, 40, 20), P)
    mb.box((-11.1, -0.2, 0), (11.1, 40.2, 1.0), "M_Ashlar")
    mb.box((-11.3, -0.3, 19.4), (11.3, 40.3, 20.3), "M_Trim")
    with mb.at((11, 0, 0), rot_z=PI / 2):
        mb.gable_roof(0, 40, 0, 22, 20.3, 27.0, "M_CopperGreen", over=0.3)
    # facade: pilasters, portal, windows, curved gable with statues
    for x in (-10.0, -6.0, 6.0, 10.0):
        mb.box((x - 0.5, -0.5, 0), (x + 0.5, 0.0, 19.4), "M_Trim")
    portal = dict(xa=-1.6, xb=1.6, za=0.0, zs=4.0, kind="round")
    mb.box((-2.6, -0.6, 0), (2.6, 0.0, 6.4), "M_Trim")
    mb.prism(list(reversed(BA.opening_outline(portal))), -0.65, -0.6, "M_Door")
    for x, z in ((-8.0, 5.0), (8.0, 5.0), (-8.0, 12.0), (8.0, 12.0), (0.0, 10.0)):
        with mb.at((x, 0.0, z)):
            BA.window_unit(mb, 1.6, 3.6, "round")
    span = 9.0
    curve = [(-span, 20.3)] + [(-span + 2 * span * k / 16, 20.3 + 6.0 * math.sin(PI * k / 16) ** 0.7) for k in range(1, 16)] + [(span, 20.3)]
    mb.prism(curve, -0.3, 0.6, P)
    mb.box((-1.2, -0.5, 26.0), (1.2, 0.0, 27.2), "M_Trim")
    for x in (-span, 0.0, span):
        G.figure(mb, (x, -0.2, 20.3 if x else 27.2), 2.2, "M_Statue", pose=0.2)
    # drum + dome + lantern over the crossing
    cy = 26.0
    mb.cyl((0, cy, 20.0), 8.0, 7.0, P, segs=24, smooth=False)
    for k in range(8):
        a = 2 * PI * (k + 0.5) / 8
        with mb.at((8.0 * math.cos(a), cy + 8.0 * math.sin(a), 22.0), rot_z=a + PI / 2):
            BA.window_unit(mb, 1.4, 3.0, "round")
    mb.cyl((0, cy, 26.8), 8.4, 0.6, "M_Trim", segs=24)
    prof = [(8.2, 27.4)] + [(8.2 * math.cos(PI / 2 * k / 8), 27.4 + 11.0 * math.sin(PI / 2 * k / 8)) for k in range(1, 8)] + [(1.6, 38.4)]
    with mb.at((0, cy, 0)):
        mb.lathe(prof, "M_CopperGreen", segs=24, cap_bottom=False, cap_top=True)
        mb.cyl((0, 0, 38.2), 1.5, 3.6, P, segs=12)
        mb.lathe([(1.7, 41.8), (1.4, 42.8), (0.6, 43.8), (0.15, 44.6)], "M_CopperGreen", segs=12, cap_bottom=True)
        mb.rod((0, 0, 44.4), (0, 0, 46.6), 0.08, "M_Gold", segs=6)
        mb.box((-0.6, -0.05, 45.7), (0.6, 0.05, 45.85), "M_Gold")
    # bell tower at the north-east corner
    tx, ty = 14.5, 34.0
    mb.box((tx - 3.5, ty - 3.5, 0), (tx + 3.5, ty + 3.5, 32.0), P)
    for z in (10.0, 20.0, 31.0):
        mb.box((tx - 3.7, ty - 3.7, z), (tx + 3.7, ty + 3.7, z + 0.5), "M_Trim")
    for face in range(4):
        a = face * PI / 2
        with mb.at((tx + 3.5 * math.sin(a), ty - 3.5 * math.cos(a), 24.0), rot_z=a):
            BA.window_unit(mb, 1.6, 4.0, "round")
    with mb.at((tx, ty, 0)):
        mb.lathe([(3.8, 32.5), (3.6, 34.0), (2.2, 36.5), (2.6, 38.0), (1.2, 40.0), (0.2, 42.5)], "M_CopperGreen", segs=16, cap_bottom=True)
        mb.rod((0, 0, 42.0), (0, 0, 44.0), 0.07, "M_Gold", segs=6)
    mc.box((-11, 0, 0), (11, 40, 27), "M_Trim")
    mc.box((tx - 3.5, ty - 3.5, 0), (tx + 3.5, ty + 3.5, 32), "M_Trim")
    mb.build("st_nicholas_mesh", root, col)
    G.finish_collision(mc, "st_nicholas", root, col)
    root["size"] = [36, 40, 46]
    return root


BUILDERS = {
    "house_timber_a": lambda: build_timber_house("house_timber_a", 7.5, 2, "M_Plaster_cream", style="gable", seed=101),
    "house_timber_b": lambda: build_timber_house("house_timber_b", 9.0, 2, "M_Plaster_ochre", style="eaves", seed=102),
    "house_timber_c": lambda: build_timber_house("house_timber_c", 6.5, 3, "M_Plaster_beige", style="gable", seed=103,
                                                  roof="M_RoofTiles", ground="M_Plaster_rose"),
    "house_timber_d": lambda: build_timber_house("house_timber_d", 8.0, 2, "M_Plaster_green", style="eaves", seed=104,
                                                  ground="M_Plaster_cream"),
    "tavern": lambda: build_timber_house("tavern", 12.0, 2, "M_Plaster_cream", style="eaves", seed=110, ground="M_StoneRough",
                                         tavern=True),
    "castle_stairs": build_castle_stairs,
    "retaining_wall": lambda: build_retaining_wall("retaining_wall", False),
    "retaining_wall_niche": lambda: build_retaining_wall("retaining_wall_niche", True),
    "garden_wall": build_garden_wall,
    "planter": build_planter,
    "st_nicholas": build_st_nicholas,
}
