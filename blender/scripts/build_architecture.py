"""Build all Old Town Square architecture assets.

blender -b --factory-startup -P build_architecture.py [-- --only house_burgher_a] [--no-render]
Outputs: blender/architecture.blend, assets/architecture/*.gltf, renders/previews/*.png
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import lib_geo as G  # noqa: E402
from lib_geo import MB, arch_points, wall_with_openings, opening_outline  # noqa: E402

OUT = os.path.join(G.PROJECT, "assets", "architecture")
PI = math.pi


# ----------------------------------------------------------------------------- shared pieces
def glass(mb, o, y, mat="M_WindowLit"):
    """Glass pane filling opening `o` in the XZ plane at depth y, facing -Y."""
    pts = list(reversed(opening_outline(o)))
    mb.face([(x, y, z) for x, z in pts], mat, uv="world")


def opening_top(o):
    return max(p[1] for p in arch_points(o["xa"], o["xb"], o["zs"], o.get("kind", "flat")))


def window_frame(mb, o, y_front=-0.07, y_back=0.0, trim="M_Trim", sill=True, hood=True):
    top = opening_top(o)
    f = 0.16
    wall_with_openings(mb, o["xa"] - f, o["xb"] + f, o["za"] - 0.12, top + f, y_front, y_back, [o], trim)
    if sill:
        mb.box((o["xa"] - 0.24, y_front - 0.12, o["za"] - 0.2), (o["xb"] + 0.24, y_back, o["za"] - 0.08), trim)
    if hood:
        mb.box((o["xa"] - 0.28, y_front - 0.08, top + f), (o["xb"] + 0.28, y_back, top + f + 0.12), trim)


def mullions(mb, o, y0, y1, mat="M_Timber"):
    xm = (o["xa"] + o["xb"]) / 2
    top = opening_top(o)
    mb.box((xm - 0.04, y0, o["za"]), (xm + 0.04, y1, top - 0.05), mat)
    zt = o["za"] + (o["zs"] - o["za"]) * 0.62
    mb.box((o["xa"], y0, zt - 0.04), (o["xb"], y1, zt + 0.04), mat)


def window_unit(mb, w, h, kind="flat", trim="M_Trim"):
    """Surface-mounted window (no hole) centred on x=0, bottom z=0, wall plane y=0, facing -Y."""
    o = dict(xa=-w / 2, xb=w / 2, za=0.0, zs=h - (w / 2 if kind == "round" else w * 0.6 if kind == "pointed" else 0), kind=kind)
    if kind == "flat":
        o["zs"] = h
    window_frame(mb, o, -0.09, 0.0, trim)
    glass(mb, o, -0.035)
    mullions(mb, o, -0.06, -0.03)


def flower_box(mb, xa, xb, z, y_wall, seed):
    rnd = random.Random(seed)
    mb.box((xa, y_wall - 0.42, z - 0.08), (xb, y_wall - 0.12, z + 0.16), "M_WoodDark")
    n = max(3, int((xb - xa) / 0.18))
    for i in range(n):
        x = xa + (i + 0.5) * (xb - xa) / n
        mb.sphere((x, y_wall - 0.27 + rnd.uniform(-0.05, 0.05), z + 0.2 + rnd.uniform(0, 0.06)),
                  (0.13, 0.12, 0.11), "M_Flowers", segs=7, rings=4, noise=0.2, seed=seed + i)


def banner(mb, x, y_wall, z_top, w=1.1, h=2.8):
    mb.rod((x, y_wall, z_top + 0.1), (x, y_wall - 0.55, z_top + 0.1), 0.03, "M_Iron", segs=6)
    mb.rod((x - w / 2 - 0.08, y_wall - 0.5, z_top + 0.1), (x + w / 2 + 0.08, y_wall - 0.5, z_top + 0.1), 0.035, "M_Iron", segs=6)
    mb.box((x - w / 2, y_wall - 0.53, z_top - h), (x + w / 2, y_wall - 0.49, z_top + 0.05),
           {"-y": "M_Banner", "+y": "M_ClothRed", "-x": "M_ClothRed", "+x": "M_ClothRed", "-z": "M_ClothRed", "+z": "M_ClothRed"})
    # swallow-tail bottom
    mb.face([(x - w / 2, y_wall - 0.535, z_top - h), (x, y_wall - 0.535, z_top - h - 0.0), (x - w / 2, y_wall - 0.535, z_top - h - 0.45)],
            "M_ClothRed")
    mb.face([(x, y_wall - 0.535, z_top - h), (x + w / 2, y_wall - 0.535, z_top - h), (x + w / 2, y_wall - 0.535, z_top - h - 0.45)],
            "M_ClothRed")


def door_leaf(name, o, y0, y1, pivot_x, root, col, off, double=None, mat="M_Door"):
    """Door leaf as separate interactive object with origin on the hinge."""
    mb = MB()
    with mb.at(off):
        pts = opening_outline(o)
        inset = [(min(max(x, o["xa"] + 0.03), o["xb"] - 0.03), max(z, o["za"]) - (0.03 if z > o["za"] + 0.1 else 0)) for x, z in pts]
        mb.prism(inset, y0, y1, mat)
        for zz in (0.35, 1.2, 2.0):
            if o["za"] + zz < opening_top(o) - 0.2:
                mb.box((o["xa"] + 0.05, y0 - 0.02, o["za"] + zz), (o["xb"] - 0.05, y0, o["za"] + zz + 0.08), "M_Iron")
        hx = o["xb"] - 0.25 if pivot_x < (o["xa"] + o["xb"]) / 2 else o["xa"] + 0.25
        mb.rod((hx, y0, o["za"] + 1.05), (hx, y0 - 0.08, o["za"] + 1.05), 0.03, "M_Iron", segs=6)
        mb.sphere((hx, y0 - 0.1, o["za"] + 1.0), 0.06, "M_Iron", segs=6, rings=4)
    ob = mb.build(name, root, col)
    G.set_origin(ob, Vector(off) + Vector((pivot_x, (y0 + y1) / 2, o["za"])))
    ob["interactive"] = "door"
    return ob


# ----------------------------------------------------------------------------- burgher house
def build_house(name, W, n_up, plaster, gable, arch="round", seed=1, banners=(), roof="M_RoofTiles",
                door_shift=0.0, ground_mat=None):
    rnd = random.Random(seed)
    root, col = G.new_asset(name, "architecture")
    D = 12.0
    Hg, Hs = 4.6, 3.3
    Hw = Hg + n_up * Hs
    P = plaster
    GM = ground_mat or P
    off = (-W / 2, -D / 2, 0.0)
    mb, mc = MB(), MB()
    ints = []
    with mb.at(off), mc.at(off):
        # --- ground floor arcade -------------------------------------------------
        n = max(1, round((W - 0.7) / 3.3))
        pier = 0.75
        span = (W - (n + 1) * pier) / n
        arches = []
        for i in range(n):
            xa = pier + i * (span + pier)
            arches.append(dict(xa=xa, xb=xa + span, za=0.0, zs=2.7 if arch != "pointed" else 2.4, kind=arch))
        wall_with_openings(mb, 0, W, 0, Hg, 0.0, 0.7, arches, GM)
        prev = 0.0
        for a in arches + [dict(xa=W, xb=W)]:
            if a["xa"] > prev:
                mb.box((prev - 0.03, -0.05, 0), (a["xa"] + 0.03, 0.75, 0.45), "M_Ashlar")       # plinth
                if a["xa"] < W:
                    mb.box((a["xa"] - 0.08, -0.06, a.get("zs", 2.6) - 0.18), (a["xa"] + 0.02, 0.76, a.get("zs", 2.6)), "M_Trim")
                if prev > 0:
                    mb.box((prev - 0.02, -0.06, arches[0]["zs"] - 0.18), (prev + 0.08, 0.76, arches[0]["zs"]), "M_Trim")
                mc.box((prev, 0, 0), (a["xa"], 0.7, Hg), "M_Trim")
            prev = a["xb"]
        # archivolt trim (stone band around each arch)
        for a in arches:
            band = dict(xa=a["xa"], xb=a["xb"], za=a["zs"], zs=a["zs"], kind=a["kind"])
            outer = dict(xa=a["xa"] - 0.18, xb=a["xb"] + 0.18, za=a["zs"], zs=a["zs"], kind=a["kind"])
            pts_o = arch_points(outer["xa"], outer["xb"], outer["zs"], outer["kind"])
            pts_i = arch_points(band["xa"], band["xb"], band["zs"], band["kind"])
            if a["kind"] != "flat":
                for k in range(len(pts_i) - 1):
                    q = [pts_i[k], pts_o[k], pts_o[k + 1], pts_i[k + 1]]
                    mb.prism(q, -0.06, 0.0, "M_Trim")
        # side arcade walls (passage to neighbours)
        for xw, (ly0, ly1) in ((0.0, (-0.5, 0.0)), (W, (-W, -W + 0.5))):
            with mb.at((0, 0, 0), rot_z=PI / 2):
                wall_with_openings(mb, 0.7, 3.4, 0, Hg, ly0, ly1,
                                   [dict(xa=1.05, xb=3.05, za=0, zs=2.4, kind=arch)], GM)
            mc.box((xw - (0.5 if xw else 0), 0.7, 0), (xw + (0 if xw else 0.5), 1.05, Hg), "M_Trim")
            mc.box((xw - (0.5 if xw else 0), 3.05, 0), (xw + (0 if xw else 0.5), 3.4, Hg), "M_Trim")
        # arcade ceiling, beams and floor
        mb.box((0, 0.6, Hg - 0.35), (W, 3.5, Hg), {"-z": "M_Plaster_cream", "+z": P, "-y": P, "+y": P, "-x": P, "+x": P})
        for k in range(int(W / 1.3) + 1):
            x = 0.5 + k * (W - 1.0) / max(1, int(W / 1.3))
            mb.box((x - 0.11, 0.7, Hg - 0.6), (x + 0.11, 3.4, Hg - 0.35), "M_Timber")
        mb.box((0, 0.0, 0), (W, 3.4, 0.1), {"+z": "M_StoneRough", "-y": "M_Trim", "-x": "M_Trim", "+x": "M_Trim",
                                             "+y": "M_Trim", "-z": "M_Trim"})
        # shop facade with real door + windows
        xd = W / 2 + door_shift
        door = dict(xa=xd - 0.7, xb=xd + 0.7, za=0.1, zs=2.3, kind="pointed" if arch == "pointed" else "round")
        shops = []
        for sx in (-1, 1):
            xa = xd + sx * 1.6 - (1.3 if sx < 0 else 0)
            if 0.6 < xa and xa + 1.3 < W - 0.6:
                shops.append(dict(xa=xa, xb=xa + 1.3, za=0.9, zs=2.1, kind="segment"))
        wall_with_openings(mb, 0.0, W, 0, Hg - 0.35, 3.4, 3.9, [door] + shops, P)
        wall_with_openings(mb, door["xa"] - 0.22, door["xb"] + 0.22, 0.1, opening_top(door) + 0.25, 3.28, 3.4,
                           [dict(door, za=0.1)], "M_Trim")
        for s in shops:
            window_frame(mb, s, 3.3, 3.4)
            glass(mb, s, 3.62)
            mullions(mb, s, 3.58, 3.64)
        # door leaf (interactive)
        dl = door_leaf(f"INT_door_{name}", door, 3.62, 3.72, door["xa"] + 0.05, root, col, off)
        ints.append(dl)
        mc.box((0, 3.4, 0), (door["xa"], 3.9, Hg), "M_Trim")
        mc.box((door["xb"], 3.4, 0), (W, 3.9, Hg), "M_Trim")
        mc.box((door["xa"], 3.4, opening_top(door)), (door["xb"], 3.9, Hg), "M_Trim")
        # vestibule interior behind the door (so an open door shows a room, not a void)
        vx0, vx1, vy0, vy1, vz = xd - 1.5, xd + 1.5, 3.9, 7.0, 3.3
        mb.box((vx0, vy0, 0.0), (vx1, vy1, 0.1), "M_WoodDark")
        mb.box((vx0 - 0.2, vy0, 0), (vx0, vy1, vz), "M_Plaster_beige")
        mb.box((vx1, vy0, 0), (vx1 + 0.2, vy1, vz), "M_Plaster_beige")
        mb.box((vx0 - 0.2, vy1, 0), (vx1 + 0.2, vy1 + 0.2, vz), "M_Plaster_beige")
        mb.box((vx0 - 0.2, vy0, vz), (vx1 + 0.2, vy1 + 0.2, vz + 0.2), "M_Timber")
        mb.box((vx1 - 0.9, vy1 - 0.6, 0.1), (vx1 - 0.1, vy1 - 0.05, 0.9), "M_WoodLight")  # chest
        mc.box((0, vy0, 0), (vx0, D, Hg), "M_Trim")
        mc.box((vx1, vy0, 0), (W, D, Hg), "M_Trim")
        mc.box((vx0, vy1, 0), (vx1, D, Hg), "M_Trim")
        mc.box((vx0, vy0, vz), (vx1, vy1, Hg), "M_Trim")
        # --- body walls ------------------------------------------------------------
        mb.box((0, 3.4, 0), (0.4, D, Hg), P)
        mb.box((W - 0.4, 3.4, 0), (W, D, Hg), P)
        mb.box((0, 0.4, Hg), (0.4, D, Hw), P)
        mb.box((W - 0.4, 0.4, Hg), (W, D, Hw), P)
        mb.box((0, D - 0.4, 0), (W, D, Hw), P)
        mb.box((0.4, 3.9, Hg - 0.4), (W - 0.4, D - 0.4, Hg - 0.35), "M_Timber")  # hidden floor slab
        mc.box((0, 0, Hg - 0.35), (W, D, Hw), "M_Trim")
        # --- upper storeys -------------------------------------------------------
        nw = max(2, int((W - 0.6) / 2.3))
        for s in range(n_up):
            zb = Hg + s * Hs
            zt = zb + Hs
            ops = []
            for i in range(nw):
                xc = (i + 0.5) * W / nw
                kind = "segment" if s == 0 else ("pointed" if arch == "pointed" else "flat")
                o = dict(xa=xc - 0.5, xb=xc + 0.5, za=zb + 0.9, zs=zb + 2.55 if kind == "flat" else zb + 2.3, kind=kind)
                ops.append(o)
            wall_with_openings(mb, 0, W, zb, zt, 0.0, 0.5, ops, P)
            mb.box((-0.04, -0.12, zb - 0.1), (W + 0.04, 0.0, zb + (0.12 if s else 0.2)), "M_Trim")  # string course
            for i, o in enumerate(ops):
                window_frame(mb, o)
                if s == 0:
                    # defenestration window: glass+mullions on separate interactive node, shutters on hinges
                    wm = MB()
                    with wm.at(off):
                        glass(wm, o, 0.3)
                        mullions(wm, o, 0.26, 0.32)
                    wob = wm.build(f"INT_window_{name}_{i}", root, col)
                    wob["interactive"] = "window"
                    xc = (o["xa"] + o["xb"]) / 2
                    G.set_origin(wob, Vector(off) + Vector((xc, 0.3, o["za"])))
                    ints.append(wob)
                    top = opening_top(o)
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
                        so.parent = wob  # root is identity and window has no rotation
                        so.location = so.location - wob.location
                        so["interactive"] = "shutter"
                    G.marker(f"MARK_window_{i}", Vector(off) + Vector((xc, -1.2, 0)), root, col)
                else:
                    glass(mb, o, 0.3)
                    mullions(mb, o, 0.26, 0.32)
                    if rnd.random() < 0.55:
                        flower_box(mb, o["xa"] + 0.02, o["xb"] - 0.02, o["za"] - 0.12, -0.08, seed * 31 + s * 7 + i)
        for bx, bz in banners:
            banner(mb, bx * W, -0.12, Hg + bz)
        # --- cornice, gable, roof -----------------------------------------------
        z0 = Hw + 0.25
        mb.box((-0.1, -0.35, Hw - 0.1), (W + 0.1, 0.4, z0), "M_Trim")
        mb.box((-0.06, -0.2, Hw - 0.3), (W + 0.06, 0.0, Hw - 0.1), "M_Trim")
        slope = 1.25 if roof == "M_RoofTiles" else 1.5
        zr = z0 + W / 2 * slope
        if gable == "tri":
            poly = [(0, z0), (W, z0), (W / 2, zr + 0.45)]
        elif gable == "step":
            ns = 4
            sw = (W / 2 - 0.6) / ns
            sh = sw * slope * 1.12
            left = [(0, z0)]
            for i in range(ns):
                left += [(i * sw, z0 + (i + 1) * sh), ((i + 1) * sw, z0 + (i + 1) * sh)]
            ztop = z0 + (ns + 1) * sh
            left += [(ns * sw, ztop)]
            right = [(W - x, z) for x, z in reversed(left)]
            poly = left + right
            for i in range(ns):
                for xx in (i * sw + 0.15, W - i * sw - 0.15):
                    mb.pyramid(xx, 0.2, z0 + (i + 1) * sh, 0.3, 0.3, 0.55, "M_Trim")
            mb.pyramid(W / 2, 0.2, ztop, 0.5, 0.5, 0.9, "M_Trim")
            mb.sphere((W / 2, 0.2, ztop + 1.0), 0.13, "M_Gold", segs=8, rings=5)
        else:  # curved, early-renaissance volutes
            hc = (zr - z0) * 1.15
            span = W / 2 - 0.7
            left = [(0, z0), (0, z0 + 0.5)]
            for k in range(1, 13):
                u = k / 12
                left.append((u * span, z0 + 0.5 + (hc - 0.5) * (u + 0.08 * math.sin(2 * PI * u))))
            topz = z0 + hc
            arc = [(W / 2 + 0.75 * math.cos(PI * (1 - k / 8)), topz + 0.55 * math.sin(PI * (1 - k / 8))) for k in range(9)]
            right = [(W - x, z) for x, z in reversed(left)]
            poly = left + [(W / 2 - 0.75, topz)] + arc[1:-1] + [(W / 2 + 0.75, topz)] + right
            mb.box((W / 2 - 0.9, -0.12, topz - 0.12), (W / 2 + 0.9, 0.0, topz + 0.02), "M_Trim")
            mb.sphere((W / 2, 0.2, topz + 0.75), 0.15, "M_Gold", segs=8, rings=5)
            for xx in (0.2, W - 0.2):
                mb.sphere((xx, 0.2, z0 + 0.65), 0.2, "M_Trim", segs=8, rings=5)
        mb.prism(poly, 0.0, 0.45, P)
        # gable windows (surface-mounted)
        gw = [W / 2] if W < 7.5 else [W / 2 - 1.3, W / 2 + 1.3]
        for x in gw:
            with mb.at((x, 0.0, z0 + 0.9)):
                window_unit(mb, 0.85, 1.4, "segment" if gable != "step" else "pointed")
        with mb.at((W / 2, 0.0, z0 + 3.1)):
            if zr - z0 > 4.2:
                window_unit(mb, 0.6, 0.9, "round")
        mb.gable_roof(0, W, 0.3, D + 0.35, z0, zr, roof)
        mb.prism([(0, Hw), (W, Hw), (W / 2, zr - 0.2)], D - 0.4, D, P)
        # rear windows (simple, surface)
        for s in range(n_up):
            for i in range(nw):
                with mb.at(((i + 0.5) * W / nw, D, Hg + s * Hs + 0.9), rot_z=PI):
                    window_unit(mb, 0.9, 1.5)
        # chimney
        cx = W * (0.72 if rnd.random() < 0.5 else 0.28)
        zroof = zr - (zr - z0) * abs(cx - W / 2) / (W / 2)
        mb.box((cx - 0.35, D * 0.55 - 0.35, zroof - 0.8), (cx + 0.35, D * 0.55 + 0.35, zr + 0.5), "M_StoneRough")
        mb.box((cx - 0.45, D * 0.55 - 0.45, zr + 0.5), (cx + 0.45, D * 0.55 + 0.45, zr + 0.65), "M_Trim")
    mb.build(name + "_mesh", root, col)
    G.finish_collision(mc, name, root, col)
    G.marker("MARK_door", Vector(off) + Vector((xd, 2.2, 0)), root, col, rot_z=0)
    G.marker("MARK_interior", Vector(off) + Vector((xd, 5.6, 0.1)), root, col, rot_z=PI)
    root["size"] = [W, D, zr]
    return root


# ----------------------------------------------------------------------------- old town hall
def build_town_hall():
    root, col = G.new_asset("old_town_hall", "architecture")
    mb, mc = MB(), MB()
    HW, HD = 15.0, 12.0          # hall
    TX0, TX1, TY0, TY1 = 15.0, 24.0, -1.0, 8.0   # tower
    TH = 34.0
    off = (-12.0, -5.5, 0.0)
    S = "M_Ashlar"
    with mb.at(off), mc.at(off):
        # ---------------- hall block -------------
        Hg, Hs, ns = 5.0, 4.0, 2
        Hw = Hg + ns * Hs
        portal = dict(xa=5.6, xb=7.8, za=0.0, zs=3.0, kind="pointed")
        gwin = [dict(xa=1.4, xb=2.6, za=1.3, zs=3.2, kind="pointed"), dict(xa=3.4, xb=4.6, za=1.3, zs=3.2, kind="pointed"),
                dict(xa=9.6, xb=10.8, za=1.3, zs=3.2, kind="pointed"), dict(xa=11.8, xb=13.0, za=1.3, zs=3.2, kind="pointed")]
        wall_with_openings(mb, 0, HW, 0, Hg, 0, 0.8, [portal] + gwin, S)
        for o in gwin:
            window_frame(mb, o, -0.08, 0.0)
            glass(mb, o, 0.45)
            mullions(mb, o, 0.4, 0.47, "M_Iron")
        # gothic portal: stepped jambs + gable with pinnacles
        for k, e in enumerate((0.15, 0.32, 0.5)):
            band = dict(portal, xa=portal["xa"] - e, xb=portal["xb"] + e, za=0, zs=portal["zs"])
            wall_with_openings(mb, band["xa"] - 0.17, band["xb"] + 0.17, 0, opening_top(band) + 0.17, -0.1 - 0.12 * k, -0.12 * k + 0.02,
                               [band], "M_Trim")
        ptop = opening_top(portal) + 0.7
        mb.prism([(portal["xa"] - 0.9, ptop - 0.4), (portal["xb"] + 0.9, ptop - 0.4), ((portal["xa"] + portal["xb"]) / 2, ptop + 1.6)],
                 -0.5, -0.2, "M_Trim")
        for xx in (portal["xa"] - 0.9, portal["xb"] + 0.9):
            mb.box((xx - 0.18, -0.55, 0), (xx + 0.18, -0.2, ptop + 0.2), "M_Trim")
            mb.pyramid(xx, -0.37, ptop + 0.2, 0.4, 0.4, 1.0, "M_Trim")
        dl = door_leaf("INT_door_town_hall_L", dict(portal, xb=(portal["xa"] + portal["xb"]) / 2), 0.35, 0.45, portal["xa"] + 0.05, root, col, off)
        dr = door_leaf("INT_door_town_hall_R", dict(portal, xa=(portal["xa"] + portal["xb"]) / 2), 0.35, 0.45, portal["xb"] - 0.05, root, col, off)
        # interior hall entrance room
        mb.box((portal["xa"] - 1.2, 0.8, 0), (portal["xb"] + 1.2, 4.5, 0.08), "M_StoneRough")
        mb.box((portal["xa"] - 1.4, 0.8, 0), (portal["xa"] - 1.2, 4.5, 4.0), "M_Plaster_cream")
        mb.box((portal["xb"] + 1.2, 0.8, 0), (portal["xb"] + 1.4, 4.5, 4.0), "M_Plaster_cream")
        mb.box((portal["xa"] - 1.4, 4.5, 0), (portal["xb"] + 1.4, 4.7, 4.0), "M_Plaster_cream")
        mb.box((portal["xa"] - 1.4, 0.8, 4.0), (portal["xb"] + 1.4, 4.7, 4.2), "M_Timber")
        mc.box((0, 0, 0), (portal["xa"], 0.8, Hg), "M_Trim")
        mc.box((portal["xb"], 0, 0), (HW, 0.8, Hg), "M_Trim")
        mc.box((portal["xa"], 0, opening_top(portal)), (portal["xb"], 0.8, Hg), "M_Trim")
        mc.box((0, 4.7, 0), (HW, HD, Hg), "M_Trim")
        mc.box((0, 0.8, 0), (portal["xa"] - 1.2, 4.7, Hg), "M_Trim")
        mc.box((portal["xb"] + 1.2, 0.8, 0), (HW, 4.7, Hg), "M_Trim")
        mc.box((0, 0, Hg), (HW, HD, Hw), "M_Trim")
        mb.box((0, 0.8, 0), (0.6, HD, Hw), S)
        mb.box((0, HD - 0.6, 0), (HW, HD, Hw), S)
        mb.box((0.6, 0.8, Hg - 0.3), (HW, HD - 0.6, Hg), "M_Timber")
        for s in range(ns):
            zb = Hg + s * Hs
            ops = []
            for i in range(5):
                xc = 1.6 + i * 2.95
                ops.append(dict(xa=xc - 0.65, xb=xc + 0.65, za=zb + 0.9, zs=zb + 2.9, kind="pointed"))
            wall_with_openings(mb, 0, HW, zb, zb + Hs, 0, 0.8, ops, S)
            mb.box((-0.05, -0.15, zb - 0.12), (HW, 0.0, zb + 0.12), "M_Trim")
            for o in ops:
                window_frame(mb, o, -0.08, 0.0)
                glass(mb, o, 0.45)
                mullions(mb, o, 0.4, 0.47, "M_Iron")
        # small clock on hall facade (as in concept art)
        mb.box((13.0, -0.25, Hg + 2.6), (14.4, 0.0, Hg + 4.0), "M_Trim")
        mb.prism([(13.05 + 0.65 + 0.6 * math.cos(2 * PI * k / 24), Hg + 3.3 + 0.6 * math.sin(2 * PI * k / 24)) for k in range(24)],
                 -0.3, -0.25, "M_DialClock")
        # banners on hall facade (as in concept art)
        banner(mb, 2.9, -0.1, Hw - 0.6, 1.4, 4.2)
        banner(mb, 9.2, -0.1, Hw - 0.6, 1.4, 4.2)
        # cornice with crenellation + roof (ridge parallel to facade)
        mb.box((-0.1, -0.3, Hw - 0.2), (HW, 0.8, Hw + 0.2), "M_Trim")
        for k in range(10):
            x = 0.2 + k * 1.5
            mb.box((x, -0.2, Hw + 0.2), (x + 0.8, 0.5, Hw + 1.0), S)
        zr = Hw + 6.5
        with mb.at((HW, 0, 0), rot_z=PI / 2):
            mb.gable_roof(0.6, HD, 0.0, HW, Hw + 0.4, zr, "M_RoofTiles", over=0.2)
        with mb.at((0.0, 0, 0), rot_z=PI / 2):
            mb.prism([(0.6, Hw + 0.4), (HD, Hw + 0.4), ((0.6 + HD) / 2, zr - 0.2)], -0.4, 0.0, S)
            mb.prism([(0.6, Hw + 0.4), (HD, Hw + 0.4), ((0.6 + HD) / 2, zr - 0.2)], -HW, -HW + 0.4, S)
        mb.box((HW - 0.6, 0.8, 0), (HW, HD, Hw), S)
        for x in (3.5, 7.5, 11.5):  # dormers
            zd = Hw + 1.6
            yd = 2.2
            mb.box((x - 0.8, yd - 0.9, zd - 1.0), (x + 0.8, yd + 1.5, zd + 1.3), S)
            with mb.at((x, yd - 0.9, zd - 0.5)):
                window_unit(mb, 0.8, 1.2, "flat")
            with mb.at((x, 0, 0)):
                mb.gable_roof(-1.0, 1.0, yd - 1.1, yd + 1.5, zd + 1.3, zd + 2.3, "M_RoofTiles", over=0.15)
        # ---------------- tower -------------
        T = "M_StoneRough"
        tw = TX1 - TX0
        mb.box((TX0, TY0, 0), (TX1, TY1, TH), T)
        mb.box((TX0 - 0.15, TY0 - 0.15, 0), (TX1 + 0.15, TY1 + 0.15, 1.0), "M_Ashlar")
        for z in (8.5, 17.5, 26.0):
            mb.box((TX0 - 0.1, TY0 - 0.12, z), (TX1 + 0.1, TY1 + 0.12, z + 0.25), "M_Trim")
        # corner buttresses
        for cx, cy in ((TX0, TY0), (TX1, TY0), (TX0, TY1), (TX1, TY1)):
            mb.box((cx - 0.45, cy - 0.45, 0), (cx + 0.45, cy + 0.45, TH - 4), T)
            mb.pyramid(cx, cy, TH - 4, 0.9, 0.9, 1.0, T)
        # narrow tower windows on 3 visible faces
        for z in (20.0, 27.5):
            for xc in (TX0 + 3.0, TX1 - 3.0):
                with mb.at((xc, TY0, z)):
                    window_unit(mb, 1.0, 2.6, "pointed")
            for yc in (TY0 + 3.0, TY1 - 3.0):
                with mb.at((TX1, yc, z), rot_z=PI / 2):
                    window_unit(mb, 1.0, 2.6, "pointed")
                with mb.at((TX0, yc, z), rot_z=-PI / 2):
                    window_unit(mb, 1.0, 2.6, "pointed")
        # gallery: corbelled walkway, parapet and four bartizans
        mb.box((TX0 - 0.8, TY0 - 0.8, TH), (TX1 + 0.8, TY1 + 0.8, TH + 0.5), "M_Trim")
        for k in range(12):
            t = (k + 0.5) / 12
            for (ax, ay, bx, by) in ((TX0, TY0 - 0.6, TX1, TY0 - 0.6), (TX0, TY1 + 0.6, TX1, TY1 + 0.6),
                                     (TX0 - 0.6, TY0, TX0 - 0.6, TY1), (TX1 + 0.6, TY0, TX1 + 0.6, TY1)):
                x, y = ax + (bx - ax) * t, ay + (by - ay) * t
                mb.cbox((x, y, TH - 0.35), (0.3, 0.3, 0.7), "M_Trim")
        for (ax, ay, bx, by) in ((TX0 - 0.8, TY0 - 0.8, TX1 + 0.8, TY0 - 0.5), (TX0 - 0.8, TY1 + 0.5, TX1 + 0.8, TY1 + 0.8),
                                 (TX0 - 0.8, TY0 - 0.8, TX0 - 0.5, TY1 + 0.8), (TX1 + 0.5, TY0 - 0.8, TX1 + 0.8, TY1 + 0.8)):
            mb.box((ax, ay, TH + 0.5), (bx, by, TH + 1.6), T)
        mb.box((TX0 + 0.5, TY0 + 0.5, TH), (TX1 - 0.5, TY1 - 0.5, TH + 2.5), T)   # lantern storey
        for cx, cy in ((TX0 - 0.5, TY0 - 0.5), (TX1 + 0.5, TY0 - 0.5), (TX0 - 0.5, TY1 + 0.5), (TX1 + 0.5, TY1 + 0.5)):
            mb.cyl((cx, cy, TH - 1.0), 0.9, 4.0, T, segs=10, smooth=False)
            mb.cyl((cx, cy, TH + 3.0), 1.05, 0.25, "M_Trim", segs=10, smooth=False)
            G.spire(mb, cx, cy, TH + 3.25, 1.05, 3.8, "M_Slate", segs=10)
        mb.pyramid((TX0 + TX1) / 2, (TY0 + TY1) / 2, TH + 2.5, tw - 0.6, (TY1 - TY0) - 0.6, 10.0, "M_Slate")
        mb.rod(((TX0 + TX1) / 2, (TY0 + TY1) / 2, TH + 12.4), ((TX0 + TX1) / 2, (TY0 + TY1) / 2, TH + 14.5), 0.06, "M_Iron", segs=6)
        mb.sphere(((TX0 + TX1) / 2, (TY0 + TY1) / 2, TH + 12.6), 0.3, "M_Gold", segs=10, rings=6)
        mc.box((TX0 - 0.5, TY0 - 0.5, 0), (TX1 + 0.5, TY1 + 0.5, TH + 3), "M_Trim")
        # ---------------- astronomical clock on tower front -------------
        cxk = (TX0 + TX1) / 2
        yk = TY0
        mb.box((cxk - 2.4, yk - 0.7, 3.2), (cxk + 2.4, yk, 15.2), "M_Trim")              # frame
        mb.box((cxk - 2.6, yk - 0.8, 3.0), (cxk + 2.6, yk - 0.6, 3.4), "M_Trim")
        for sx in (-1, 1):  # gothic side pilasters with pinnacles
            mb.box((cxk + sx * 2.4 - 0.25, yk - 0.95, 3.2), (cxk + sx * 2.4 + 0.25, yk - 0.6, 15.2), "M_Trim")
            mb.pyramid(cxk + sx * 2.4, yk - 0.78, 15.2, 0.55, 0.4, 1.6, "M_Trim")
        for zc, r, mat in ((11.4, 1.9, "M_DialAstro"), (6.0, 1.65, "M_DialCalendar")):
            ring = [(cxk + (r + 0.18) * math.cos(2 * PI * k / 36), zc + (r + 0.18) * math.sin(2 * PI * k / 36)) for k in range(36)]
            mb.prism(ring, yk - 0.85, yk - 0.7, "M_Gold")
            disc = [(cxk + r * math.cos(2 * PI * k / 36), zc + r * math.sin(2 * PI * k / 36)) for k in range(36)]
            mb.prism(disc, yk - 0.9, yk - 0.85, mat, cap=mat, side_mats=["M_Gold"] * 36)
        # astrolabe hands
        mb.box((cxk - 0.04, yk - 0.97, 11.4), (cxk + 0.04, yk - 0.92, 13.0), "M_Gold")
        mb.sphere((cxk + 0.9, yk - 0.96, 12.2), 0.22, "M_Gold", segs=10, rings=6)
        # figures beside the dials + apostle windows + copper canopy
        for sx in (-1, 1):
            for z in (8.6, 12.4):
                mb.box((cxk + sx * 2.05 - 0.25, yk - 1.1, z - 0.15), (cxk + sx * 2.05 + 0.25, yk - 0.7, z), "M_Trim")
                G.figure(mb, (cxk + sx * 2.05, yk - 0.9, z), 1.3, "M_Statue")
        for sx in (-0.7, 0.7):
            with mb.at((cxk + sx, yk - 0.7, 13.8)):
                window_unit(mb, 0.8, 1.1, "pointed")
        mb.pyramid(cxk, yk - 0.7, 15.2, 5.4, 1.8, 2.2, "M_CopperGreen")
        G.spire(mb, cxk, yk - 0.9, 17.2, 0.35, 1.6, "M_CopperGreen", segs=8)
        mc.box((cxk - 2.6, yk - 1.0, 0), (cxk + 2.6, yk, 15.2), "M_Trim")
        # tower ground passage door
        tdoor = dict(xa=cxk - 0.8, xb=cxk + 0.8, za=0, zs=2.0, kind="pointed")
        with mb.at((0, 0, 0)):
            mb.box((tdoor["xa"] - 0.3, yk - 0.12, 0), (tdoor["xb"] + 0.3, yk, 3.0), "M_Trim")
            mb.prism(list(reversed(opening_outline(tdoor))), yk - 0.14, yk - 0.12, "M_Door")
    mb.build("old_town_hall_mesh", root, col)
    G.finish_collision(mc, "old_town_hall", root, col)
    G.marker("MARK_door", Vector(off) + Vector(((portal["xa"] + portal["xb"]) / 2, -1.2, 0)), root, col)
    G.marker("MARK_interior", Vector(off) + Vector(((portal["xa"] + portal["xb"]) / 2, 2.8, 0.1)), root, col, rot_z=PI)
    G.marker("MARK_clock_view", Vector(off) + Vector((cxk, -9.0, 0)), root, col)
    for i, x in enumerate((2.0, 12.4)):
        G.point_light(f"LIGHT_hall_torch_{i}", Vector(off) + Vector((x, -0.6, 3.2)), root, col, energy=80)
        with_torch(root, col, Vector(off) + Vector((x, 0.0, 2.6)))
    root["size"] = [HW + 9, 13, TH + 15]
    return root


def with_torch(root, col, wall_pt):
    """Small wall torch mesh (emissive flame) attached to a building."""
    mb = MB()
    x, y, z = wall_pt
    mb.box((x - 0.06, y - 0.05, z - 0.1), (x + 0.06, y, z + 0.25), "M_Iron")
    mb.rod((x, y - 0.03, z), (x, y - 0.42, z + 0.45), 0.025, "M_Iron", segs=6)
    mb.rod((x, y - 0.4, z + 0.35), (x, y - 0.5, z + 0.75), 0.05, "M_Timber", segs=6, r1=0.06)
    mb.cyl((x, y - 0.5, z + 0.72), 0.08, 0.35, "M_Fire", segs=6, r_top=0.0, smooth=True)
    mb.build(f"{root.name}_torch_{len(root.children)}", root, col)


# ----------------------------------------------------------------------------- Tyn church
def build_tyn_church():
    root, col = G.new_asset("tyn_church", "architecture")
    mb, mc = MB(), MB()
    S = "M_StoneDark"
    TH = 38.0
    with mb.at((0, -4, 0)), mc.at((0, -4, 0)):
        for tx in (-9.0, 9.0):
            x0, x1, y0, y1 = tx - 4.5, tx + 4.5, 0.0, 9.0
            mb.box((x0, y0, 0), (x1, y1, TH), S)
            for z in (10.0, 20.0, 29.0):
                mb.box((x0 - 0.1, y0 - 0.15, z), (x1 + 0.1, y1, z + 0.3), "M_TrimDark")
            for cx in (x0, x1):
                mb.box((cx - 0.5, y0 - 0.6, 0), (cx + 0.5, y0 + 0.5, TH - 2), S)
                mb.pyramid(cx, y0 - 0.05, TH - 2, 1.0, 1.1, 1.5, S)
            for z in (13.0, 22.5, 31.0):
                with mb.at((tx, y0, z)):
                    window_unit(mb, 1.4, 3.6 if z < 30 else 3.0, "pointed", "M_TrimDark")
            # gallery and spire cluster (the famous Tyn silhouette)
            mb.box((x0 - 0.6, y0 - 0.6, TH), (x1 + 0.6, y1 + 0.6, TH + 1.2), "M_TrimDark")
            for k in range(8):
                ang = 2 * PI * k / 8
                mb.cyl((tx + 3.6 * math.cos(ang), 4.5 + 3.6 * math.sin(ang), TH + 1.2), 0.25, 1.0, "M_TrimDark", segs=6)
            G.spire(mb, tx, 4.5, TH + 1.2, 3.6, 23.0, "M_Slate", segs=8)
            for cx, cy in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
                mb.cyl((cx, cy, TH + 1.2), 1.0, 2.5, "M_TrimDark", segs=8, smooth=False)
                G.spire(mb, cx, cy, TH + 3.7, 1.0, 9.0, "M_Slate", segs=8)
            for cx, cy in ((tx, y0 - 0.2), (tx, y1 + 0.2), (x0 - 0.2, 4.5), (x1 + 0.2, 4.5)):
                G.spire(mb, cx, cy, TH + 6.0, 0.55, 5.5, "M_Slate", segs=6)
            mc.box((x0 - 0.6, y0 - 0.6, 0), (x1 + 0.6, y1 + 0.6, TH + 1.2), "M_Trim")
        # central gable facade between towers
        mb.box((-4.5, 0.5, 0), (4.5, 3.0, 26.0), S)
        mb.prism([(-4.5, 26.0), (4.5, 26.0), (0, 34.0)], 0.5, 3.0, S)
        with mb.at((0, 0.5, 9.0)):
            window_unit(mb, 3.2, 11.0, "pointed", "M_TrimDark")
        with mb.at((0, 0.5, 27.0)):
            window_unit(mb, 1.6, 3.5, "pointed", "M_TrimDark")
        for k in range(5):
            x = -3.0 + k * 1.5
            mb.pyramid(x, 0.8, 26.0 + (8.0 * (1 - abs(x) / 4.5)), 0.4, 0.4, 1.2, "M_TrimDark")
        mb.pyramid(0, 1.0, 34.0, 0.6, 0.6, 2.0, "M_TrimDark")
        mb.rod((0, 1.0, 35.5), (0, 1.0, 37.8), 0.08, "M_Gold", segs=6)
        mb.box((-0.7, 0.95, 36.8), (0.7, 1.05, 36.95), "M_Gold")
        # nave and very steep roof
        mb.box((-13.5, 9.0, 0), (13.5, 46.0, 24.0), S)
        for k in range(6):
            y = 12.0 + k * 6.0
            for sx in (-1, 1):
                bx0, bx1 = (13.5, 14.9) if sx > 0 else (-14.9, -13.5)
                mb.box((bx0, y - 0.6, 0), (bx1, y + 0.6, 20.0), S)
                mb.pyramid((bx0 + bx1) / 2, y, 20.0, 1.4, 1.2, 2.0, S)
                with mb.at((sx * 13.5, y + 3.0, 6.0), rot_z=sx * PI / 2):
                    window_unit(mb, 2.0, 12.0, "pointed", "M_TrimDark")
        mb.gable_roof(-13.5, 13.5, 3.0, 46.5, 24.0, 46.0, "M_Slate", over=0.5, thick=0.4)
        mb.prism([(-13.5, 24.0), (13.5, 24.0), (0, 45.6)], 45.5, 46.0, S)
        mc.box((-13.5, 0.5, 0), (13.5, 46.0, 26.0), "M_Trim")
    mb.build("tyn_church_mesh", root, col)
    G.finish_collision(mc, "tyn_church", root, col)
    root["size"] = [28, 51, 62]
    return root


# ----------------------------------------------------------------------------- Marian column
def build_marian_column():
    root, col = G.new_asset("marian_column", "architecture")
    mb, mc = MB(), MB()
    for k, s in enumerate((4.6, 3.8, 3.0)):
        mb.cbox((0, 0, 0.17 + 0.34 * k), (s, s, 0.34), "M_Trim")
    mb.cbox((0, 0, 1.02 + 1.2), (1.8, 1.8, 2.4), "M_Ashlar")
    mb.cbox((0, 0, 1.02 + 0.15), (2.1, 2.1, 0.3), "M_Trim")
    mb.cbox((0, 0, 3.42 + 0.15), (2.1, 2.1, 0.3), "M_Trim")
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        mb.cbox((sx * 1.55, sy * 1.55, 1.02 + 0.3), (0.55, 0.55, 0.6), "M_Trim")
        G.figure(mb, (sx * 1.55, sy * 1.55, 1.62), 1.5, "M_Statue", pose=0.2)
    mb.cyl((0, 0, 3.72), 0.45, 0.4, "M_Trim", segs=16)
    mb.cyl((0, 0, 4.12), 0.38, 9.0, "M_Trim", segs=16, r_top=0.32)
    mb.cyl((0, 0, 13.1), 0.5, 0.45, "M_Trim", segs=16, r_top=0.65)
    mb.cbox((0, 0, 13.7), (1.1, 1.1, 0.3), "M_Trim")
    G.figure(mb, (0, 0, 13.85), 2.2, "M_Gold", pose=0.4)
    for k in range(12):
        a = 2 * PI * k / 12
        mb.sphere((0.28 * math.cos(a), 0.28 * math.sin(a), 15.95), 0.05, "M_Gold", segs=6, rings=4)
    mc.cbox((0, 0, 0.5), (4.6, 4.6, 1.0), "M_Trim")
    mc.cbox((0, 0, 3.0), (2.4, 2.4, 4.0), "M_Trim")
    mc.cyl((0, 0, 5.0), 0.45, 9.0, "M_Trim", segs=8, smooth=False)
    mb.build("marian_column_mesh", root, col)
    G.finish_collision(mc, "marian_column", root, col)
    root["size"] = [4.6, 4.6, 16]
    return root


# ----------------------------------------------------------------------------- gothic tower house
def build_gothic_tower_house():
    name = "house_gothic_tower"
    root, col = G.new_asset(name, "architecture")
    mb, mc = MB(), MB()
    W, D = 8.0, 9.0
    Hs = 3.6
    n = 4
    Hw = n * Hs + 0.6
    S = "M_StoneRough"
    off = (-W / 2, -D / 2, 0)
    with mb.at(off), mc.at(off):
        door = dict(xa=3.3, xb=4.7, za=0.0, zs=2.3, kind="pointed")
        win0 = [dict(xa=1.0, xb=2.0, za=1.2, zs=2.4, kind="pointed"), dict(xa=6.0, xb=7.0, za=1.2, zs=2.4, kind="pointed")]
        wall_with_openings(mb, 0, W, 0, Hs, 0, 0.6, [door] + win0, S)
        for o in win0:
            window_frame(mb, o)
            glass(mb, o, 0.35)
            mullions(mb, o, 0.31, 0.37, "M_Iron")
        wall_with_openings(mb, door["xa"] - 0.25, door["xb"] + 0.25, 0, opening_top(door) + 0.25, -0.12, 0.0, [door], "M_Trim")
        door_leaf(f"INT_door_{name}", door, 0.3, 0.4, door["xa"] + 0.05, root, col, off)
        mb.box((2.4, 0.6, 0), (5.6, 3.6, 0.06), "M_StoneRough")
        mb.box((2.2, 0.6, 0), (2.4, 3.6, 3.0), "M_Plaster_beige")
        mb.box((5.6, 0.6, 0), (5.8, 3.6, 3.0), "M_Plaster_beige")
        mb.box((2.2, 3.6, 0), (5.8, 3.8, 3.0), "M_Plaster_beige")
        mb.box((2.2, 0.6, 3.0), (5.8, 3.8, 3.2), "M_Timber")
        for s in range(1, n):
            zb = s * Hs
            ops = [dict(xa=xc - 0.55, xb=xc + 0.55, za=zb + 0.9, zs=zb + 2.4, kind="pointed") for xc in (2.0, 6.0)]
            wall_with_openings(mb, 0, W, zb, zb + Hs, 0, 0.6, ops, S)
            mb.box((-0.05, -0.1, zb - 0.1), (W + 0.05, 0.0, zb + 0.1), "M_Trim")
            for i, o in enumerate(ops):
                window_frame(mb, o)
                if s == 1:
                    wm = MB()
                    with wm.at(off):
                        glass(wm, o, 0.35)
                        mullions(wm, o, 0.31, 0.37, "M_Iron")
                    wob = wm.build(f"INT_window_{name}_{i}", root, col)
                    wob["interactive"] = "window"
                    G.set_origin(wob, Vector(off) + Vector(((o["xa"] + o["xb"]) / 2, 0.35, o["za"])))
                    G.marker(f"MARK_window_{i}", Vector(off) + Vector(((o["xa"] + o["xb"]) / 2, -1.2, 0)), root, col)
                else:
                    glass(mb, o, 0.35)
                    mullions(mb, o, 0.31, 0.37, "M_Iron")
        mb.box((0, 0.6, 0), (0.6, D, Hw), S)
        mb.box((W - 0.6, 0.6, 0), (W, D, Hw), S)
        mb.box((0, D - 0.6, 0), (W, D, Hw), S)
        mb.box((0, 0, n * Hs), (W, 0.6, Hw), S)
        mb.box((-0.15, -0.15, Hw - 0.2), (W + 0.15, D + 0.15, Hw + 0.15), "M_Trim")
        for i in range(8):  # corbel table under cornice
            mb.box((0.3 + i * 1.0, -0.12, Hw - 0.5), (0.6 + i * 1.0, 0.0, Hw - 0.2), "M_Trim")
        mb.pyramid(W / 2, D / 2, Hw + 0.15, W + 0.6, D + 0.6, 9.5, "M_Slate", w_top=0.6, d_top=1.6)
        mb.rod((W / 2, D / 2, Hw + 9.6), (W / 2, D / 2, Hw + 11.2), 0.05, "M_Iron", segs=6)
        mb.sphere((W / 2, D / 2, Hw + 10.0), 0.18, "M_Gold", segs=8, rings=5)
        # dormer
        mb.box((W / 2 - 0.7, 0.4, Hw + 1.2), (W / 2 + 0.7, 2.2, Hw + 2.8), S)
        with mb.at((W / 2, 0.4, Hw + 1.45)):
            window_unit(mb, 0.7, 1.0, "flat")
        mb.gable_roof(W / 2 - 0.7, W / 2 + 0.7, 0.25, 2.2, Hw + 2.8, Hw + 3.6, "M_Slate", over=0.15)
        mc.box((0, 0, 0), (door["xa"], 0.6, Hw), "M_Trim")
        mc.box((door["xb"], 0, 0), (W, 0.6, Hw), "M_Trim")
        mc.box((door["xa"], 0, opening_top(door)), (door["xb"], 0.6, Hw), "M_Trim")
        mc.box((0, 3.8, 0), (W, D, Hw), "M_Trim")
        mc.box((0, 0.6, 0), (2.2, 3.8, Hw), "M_Trim")
        mc.box((5.8, 0.6, 0), (W, 3.8, Hw), "M_Trim")
        mc.box((2.2, 0.6, 3.0), (5.8, 3.8, Hw), "M_Trim")
    mb.build(name + "_mesh", root, col)
    G.finish_collision(mc, name, root, col)
    G.marker("MARK_door", Vector(off) + Vector((4.0, -1.2, 0)), root, col)
    G.marker("MARK_interior", Vector(off) + Vector((4.0, 2.2, 0.06)), root, col, rot_z=PI)
    G.point_light("LIGHT_door_torch", Vector(off) + Vector((2.6, -0.7, 3.0)), root, col, energy=70)
    with_torch(root, col, Vector(off) + Vector((2.6, 0.0, 2.4)))
    root["size"] = [W, D, Hw + 11]
    return root


# ----------------------------------------------------------------------------- ground
def build_ground():
    root, col = G.new_asset("ground_cobble", "architecture")
    mb, mc = MB(), MB()
    mb.box((-8, -8, -0.3), (8, 8, 0.0), {"+z": "M_Cobble", "-z": "M_StoneRough", "-x": "M_StoneRough", "+x": "M_StoneRough",
                                          "-y": "M_StoneRough", "+y": "M_StoneRough"})
    mc.box((-8, -8, -0.3), (8, 8, 0.0), "M_Trim")
    mb.build("ground_cobble_mesh", root, col)
    G.finish_collision(mc, "ground_cobble", root, col)
    root["size"] = [16, 16, 0.3]
    return root


# ----------------------------------------------------------------------------- arch passage (Task 3)
def build_arch_passage():
    """Vaulted passage with a room above; fills a 6 m gap between houses (same 12 m depth as a house)."""
    name = "arch_passage"
    root, col = G.new_asset(name, "architecture")
    mb, mc = MB(), MB()
    W, D, Hb, Hw = 6.0, 12.0, 5.6, 9.0
    arch = dict(xa=-2.2, xb=2.2, za=0.0, zs=3.0, kind="round")
    wall_with_openings(mb, -W / 2, W / 2, 0.0, Hb, -D / 2, D / 2, [arch], "M_Ashlar")      # vaulted tunnel block
    for y0, y1 in ((-D / 2 - 0.12, -D / 2), (D / 2, D / 2 + 0.12)):                       # archivolts both sides
        wall_with_openings(mb, arch["xa"] - 0.35, arch["xb"] + 0.35, 0.0, opening_top(arch) + 0.35, y0, y1,
                           [arch], "M_Trim")
    mb.box((-W / 2, -D / 2 - 0.15, Hb - 0.2), (W / 2, D / 2 + 0.15, Hb + 0.05), "M_Trim")
    mb.box((-W / 2, -D / 2, Hb), (W / 2, D / 2, Hw), "M_Plaster_cream")
    for yf, rot in ((-D / 2, 0.0), (D / 2, PI)):
        for x in (-1.4, 1.4):
            with mb.at((x if rot == 0 else -x, yf, Hb + 0.9), rot_z=rot):
                window_unit(mb, 0.9, 1.6, "segment")
    mb.box((-W / 2 - 0.1, -D / 2 - 0.3, Hw - 0.1), (W / 2 + 0.1, D / 2 + 0.3, Hw + 0.2), "M_Trim")
    zr = Hw + 0.2 + W / 2 * 1.25
    mb.gable_roof(-W / 2, W / 2, -D / 2 - 0.3, D / 2 + 0.3, Hw + 0.2, zr, "M_RoofTiles")
    for yf in (-D / 2 - 0.3, D / 2 + 0.3 - 0.4):
        mb.prism([(-W / 2, Hw + 0.2), (W / 2, Hw + 0.2), (0, zr - 0.15)], yf, yf + 0.4, "M_Plaster_cream")
    mc.box((-W / 2, -D / 2, 0), (arch["xa"], D / 2, Hw), "M_Trim")
    mc.box((arch["xb"], -D / 2, 0), (W / 2, D / 2, Hw), "M_Trim")
    mc.box((arch["xa"], -D / 2, opening_top(arch)), (arch["xb"], D / 2, Hw), "M_Trim")
    mb.build(name + "_mesh", root, col)
    G.finish_collision(mc, name, root, col)
    for i, x in enumerate((-2.62, 2.62)):
        with_torch(root, col, (x, -D / 2 - 0.12, 2.4))
        G.point_light(f"LIGHT_passage_torch_{i}", (x, -D / 2 - 0.62, 3.0), root, col, energy=70)
    G.marker("MARK_passage_front", (0, -D / 2 - 1.5, 0), root, col)
    G.marker("MARK_passage_back", (0, D / 2 + 1.5, 0), root, col, rot_z=PI)
    root["size"] = [W, D, zr]
    return root


HOUSES = [
    # name, width, upper storeys, plaster, gable, arch, seed, banners [(x fraction, z above ground floor)]
    ("house_burgher_a", 7.0, 3, "M_Plaster_ochre", "curve", "round", 3, [(0.5, 5.6)]),
    ("house_burgher_b", 6.5, 3, "M_Plaster_green", "curve", "round", 5, []),
    ("house_burgher_c", 7.5, 2, "M_Plaster_red", "step", "pointed", 7, [(0.5, 5.4)]),
    ("house_burgher_d", 8.5, 3, "M_Plaster_cream", "tri", "round", 9, []),
    ("house_burgher_e", 6.0, 2, "M_Plaster_beige", "step", "pointed", 11, []),
    ("house_burgher_f", 9.0, 2, "M_Plaster_rose", "curve", "round", 13, []),
]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only = argv[argv.index("--only") + 1].split(",") if "--only" in argv else None
    render = "--no-render" not in argv
    G.reset_scene()
    builders = {h[0]: (lambda h=h: build_house(h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7])) for h in HOUSES}
    builders.update({
        "old_town_hall": build_town_hall,
        "tyn_church": build_tyn_church,
        "marian_column": build_marian_column,
        "house_gothic_tower": build_gothic_tower_house,
        "ground_cobble": build_ground,
        "arch_passage": build_arch_passage,
    })
    roots = []
    for name, fn in builders.items():
        if only and name not in only:
            continue
        print("BUILD", name)
        roots.append(fn())
    for r in roots:
        G.export_asset(r, OUT)
    if render:
        import lib_render as R
        for r in roots:
            R.render_asset(r)
            if r.name in ("old_town_hall", "house_burgher_a", "house_gothic_tower", "house_burgher_c"):
                R.render_asset(r, night=True)
        for n in ("_preview_ground", "_preview_cam", "_preview_sun"):
            ob = bpy.data.objects.get(n)
            if ob:
                bpy.data.objects.remove(ob)
    if not only:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(G.BLENDER_DIR, "architecture.blend"))
    print("DONE architecture")


if __name__ == "__main__":
    main()
