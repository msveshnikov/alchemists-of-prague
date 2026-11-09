"""Task 3: assemble the empty Old Town level from the Task 1 asset libraries.

blender -b --factory-startup -P build_world.py [-- --no-render]
Outputs:
  blender/world_old_town.blend               (collection instances of the asset library + markers + day/night animation)
  assets/levels/old_town_layout.json         (asset placements + markers + lighting presets, in GODOT coordinates)
  renders/world/*.png                        (day / dusk / night renders, plan view, concept comparisons)
"""
import json
import math
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import lib_geo as G  # noqa: E402

PI = math.pi
V = Vector
OUT_JSON = os.path.join(G.PROJECT, "assets", "levels", "old_town_layout.json")
RENDER_DIR = os.path.join(G.PROJECT, "renders", "world")

COLS = {}        # asset name -> appended collection
CATEGORY = {}    # asset name -> architecture / props
SIZE = {}        # asset name -> [w, d, h]
LAYOUT = []      # placed instances
MARKERS = []     # gameplay markers
WORLD_COL = None
MARK_COL = None
_count = {}


# ============================================================================= library
def append_assets():
    for fname in ("architecture.blend", "props.blend"):
        path = os.path.join(G.BLENDER_DIR, fname)
        with bpy.data.libraries.load(path, link=False) as (src, dst):
            dst.collections = list(src.collections)
        for c in dst.collections:
            COLS[c.name] = c
            root = c.objects.get(c.name) or next((o for o in c.objects if o.parent is None), None)
            CATEGORY[c.name] = root.get("asset_category", "props") if root else "props"
            if root and "size" in root:
                SIZE[c.name] = list(root["size"])
    print("appended", len(COLS), "assets")


def to_godot(p):
    return [round(p.x, 3), round(p.z, 3), round(-p.y, 3)]


def base_name(n):
    return re.sub(r"\.\d{3}$", "", n)


def add_marker(name, kind, loc, yaw=0.0, owner=None, extra=None):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "SINGLE_ARROW" if kind in ("spawn", "player", "exit") else "PLAIN_AXES"
    e.empty_display_size = 1.0
    e.location = loc
    e.rotation_euler = (0, 0, yaw)
    MARK_COL.objects.link(e)
    m = {"name": name, "kind": kind, "pos": to_godot(V(loc)), "yaw_deg": round(math.degrees(yaw) % 360, 1)}
    if owner:
        m["owner"] = owner
    if extra:
        m.update(extra)
    MARKERS.append(m)
    return e


MARK_KIND = [("MARK_door", "door"), ("MARK_interior", "interior"), ("MARK_window", "window"), ("MARK_merchant", "merchant"),
             ("MARK_customer", "customer"), ("MARK_smith", "smith"), ("MARK_cook", "cook"), ("MARK_horse", "horse"),
             ("MARK_clock_view", "poi"), ("MARK_passage", "passage"), ("MARK_forge", "slot"), ("MARK_anvil", "slot"),
             ("MARK_mount", None), ("MARK_grip", None), ("MARK_outside", None), ("MARK_inside", None)]


def inst(asset, x, y, yaw=0.0, z=0.0, group="misc", markers=True):
    global _count
    k = _count.get(asset, 0)
    _count[asset] = k + 1
    iid = f"{asset}#{k:02d}"
    e = bpy.data.objects.new(iid, None)
    e.instance_type = "COLLECTION"
    e.instance_collection = COLS[asset]
    e.location = (x, y, z)
    e.rotation_euler = (0, 0, yaw)
    WORLD_COL.children[group].objects.link(e) if group in WORLD_COL.children else _group(group).objects.link(e)
    M = Matrix.Translation((x, y, z)) @ Matrix.Rotation(yaw, 4, "Z")
    LAYOUT.append({"id": iid, "asset": asset, "path": f"res://assets/{CATEGORY[asset]}/{asset}.gltf", "group": group,
                   "pos": to_godot(V((x, y, z))), "yaw_deg": round(math.degrees(yaw) % 360, 2)})
    out = {}
    if markers:
        for o in COLS[asset].all_objects:
            b = base_name(o.name)
            if not b.startswith("MARK_"):
                continue
            kind = next((kk for pre, kk in MARK_KIND if b.startswith(pre)), "misc")
            mw = M @ o.matrix_world
            loc = mw.to_translation()
            yaw_m = mw.to_euler().z
            out[b] = (loc, yaw_m)
            if kind is None:
                continue
            add_marker(f"{b}@{iid}", kind, loc, yaw_m, owner=iid)
    return e, out


def _group(name):
    c = bpy.data.collections.new(name)
    WORLD_COL.children.link(c)
    return c


def yaw_from_facing(f):
    return math.atan2(f[0], -f[1])


# ============================================================================= rows & streets
HOUSE_POOL = ["house_burgher_a", "house_burgher_b", "house_burgher_c", "house_burgher_d", "house_burgher_e",
              "house_burgher_f"]


def fill_row(start, facing, length, rnd, group, pool=None, torch_every=3, gothic=0.12):
    """Houses along a facade line starting at `start`, facing `facing`, running along the house's local +X."""
    pool = pool or HOUSE_POOL
    th = yaw_from_facing(facing)
    u = V((math.cos(th), math.sin(th), 0))
    f = V((facing[0], facing[1], 0))
    s = V((start[0], start[1], 0))
    t = 0.0
    last = None
    placed = []
    while t < length - 2.5:
        name = rnd.choice([p for p in pool if p != last]) if rnd.random() > gothic else "house_gothic_tower"
        w, d = SIZE[name][0], SIZE[name][1]
        if t + w > length:
            if length - t < 3.0:
                break
            t = length - w
        c = s + u * (t + w / 2) - f * (d / 2)
        _, mk = inst(name, c.x, c.y, th, group=group)
        placed.append((name, mk))
        if torch_every and len(placed) % torch_every == 0 and "MARK_door" in mk and name != "house_gothic_tower":
            dl, _ = mk["MARK_door"]
            p = dl + u * 1.15 - f * 1.2
            inst("wall_torch", p.x, p.y, th, group="lights", markers=False)
        last = name
        t += w
    return placed


def street(name, pts, width, rnd, end_cap=True, exit_name=None, t0=13.0, gaps=None, lantern_every=17.0, arch_at=None):
    gaps = gaps or {}
    pts = [V((p[0], p[1], 0)) for p in pts]
    group = f"street_{name}"
    n = len(pts) - 1
    for i in range(n):
        a, b = pts[i], pts[i + 1]
        d = (b - a).normalized()
        L = (b - a).length + (2.5 if i < n - 1 else 0.0)
        nl = V((-d.y, d.x, 0))
        s0 = t0 if i == 0 else -2.5
        # left side: facade line a+nl*w/2 -> b+nl*w/2, facing -nl, runs along +d
        for side, sgn in (("L", 1), ("R", -1)):
            segs = [(s0, L)]
            for (gi, gs, ga, gb) in gaps.get(side, []):
                if gi == i:
                    segs = [(s0, ga), (gb, L)]
            for (ta, tb) in segs:
                if tb - ta < 3:
                    continue
                if side == "L":
                    st = a + d * ta + nl * (width / 2)
                    fill_row(st, (-nl.x, -nl.y), tb - ta, rnd, group)
                else:
                    st = a + d * tb - nl * (width / 2)
                    fill_row(st, (nl.x, nl.y), tb - ta, rnd, group)
        # lanterns alternating sides
        k = 0
        tt = (t0 if i == 0 else 4.0)
        while tt < (b - a).length - 2:
            sgn = 1 if k % 2 == 0 else -1
            p = a + d * tt + nl * sgn * (width / 2 - 0.7)
            inst("street_lantern", p.x, p.y, yaw_from_facing((-nl.x * sgn, -nl.y * sgn)), group="lights", markers=False)
            tt += lantern_every
            k += 1
    end = pts[-1]
    dl = (pts[-1] - pts[-2]).normalized()
    if end_cap:
        c = end + dl * (6.0 + 0.5)
        inst(rnd.choice(HOUSE_POOL), c.x, c.y, yaw_from_facing((-dl.x, -dl.y)), group=group)
    if exit_name:
        p = end - dl * 2.0
        add_marker(f"MARK_exit_{exit_name}", "exit", p, yaw_from_facing((dl.x, dl.y)) + PI,
                   extra={"leads_to": exit_name})
    if arch_at is not None:
        i, tt = arch_at
        a, b = pts[i], pts[i + 1]
        d = (b - a).normalized()
        p = a + d * tt
        inst("arch_passage", p.x, p.y, math.atan2(-d.x, d.y), group=group)
    return pts


# ============================================================================= layout
SQ = dict(N=34.0, S=-30.0, E=36.0, W=-36.0)


def build_layout():
    rnd = random.Random(1348)  # founding year of Charles University ;)
    # ---- square: four facade rows with street mouths ----------------------------------------
    fill_row((SQ["W"] + 6, SQ["N"]), (0, -1), -1.5 - (SQ["W"] + 6), rnd, "square_north")           # x -30 .. -1.5
    inst("arch_passage", 1.5, SQ["N"] + 6, 0.0, group="square_north")                               # passage to Tyn
    fill_row((4.5, SQ["N"]), (0, -1), SQ["E"] - 4.5, rnd, "square_north")                           # x 4.5 .. 36
    fill_row((SQ["E"], SQ["N"]), (-1, 0), SQ["N"] - (-7.5), rnd, "square_east")                     # y 34 .. -7.5
    fill_row((SQ["E"], -15.0), (-1, 0), -15.0 - SQ["S"], rnd, "square_east")                        # y -15 .. -30
    fill_row((SQ["E"], SQ["S"]), (0, 1), SQ["E"] - 0.0, rnd, "square_south")                        # x 36 .. 0
    fill_row((-6.0, SQ["S"]), (0, 1), -6.0 - SQ["W"], rnd, "square_south")                          # x -6 .. -36
    # west: Old Town Hall (clock tower towards the north end of the hall), houses north of it
    _, hall = inst("old_town_hall", SQ["W"] - 5.5, -6.0, PI / 2, group="square_west")
    fill_row((SQ["W"], -24.0), (1, 0), 6.0, rnd, "square_west", pool=["house_burgher_e"], gothic=0)  # y -24 .. -18
    fill_row((SQ["W"], 6.6), (1, 0), SQ["N"] - 6.6, rnd, "square_west")                             # y 6.6 .. 34
    # ---- Tyn court behind the passage --------------------------------------------------------
    inst("tyn_church", 1.5, 78.0, 0.0, group="tyn_court")
    fill_row((-12.0, 46.0), (1, 0), 26.0, rnd, "tyn_court")            # west side, facing east (runs +y)
    fill_row((16.0, 72.0), (-1, 0), 26.0, rnd, "tyn_court")            # east side, facing west (runs -y)
    # ---- radiating streets -------------------------------------------------------------------
    street("karlova", [(SQ["W"], -27.0), (-58, -25), (-74, -33), (-96, -30)], 6.0, rnd, exit_name="charles_bridge",
           arch_at=(1, 9.0))
    street("melantrichova", [(-3.0, SQ["S"]), (-4, -54), (5, -74), (2, -96)], 6.0, rnd, exit_name="vysehrad")
    street("celetna", [(SQ["E"], -11.25), (60, -12.5), (84, -7), (106, -9)], 7.5, rnd, exit_name="powder_gate",
           gaps={"L": [(0, "L", 19.0, 24.5)]})
    street("celetna_alley", [(58.0, -8.0), (60, 8), (54, 24), (57, 40)], 4.5, rnd, t0=3.0, lantern_every=20.0)
    street("parizska", [(-33.0, SQ["N"]), (-36, 52), (-46, 68)], 6.0, rnd, exit_name="jewish_town", lantern_every=18.0)
    # ---- ground -------------------------------------------------------------------------------
    for ix in range(-8, 9):
        for iy in range(-7, 9):
            inst("ground_cobble", ix * 16.0, iy * 16.0, 0.0, group="ground", markers=False)
    # ---- square furnishing (fixed props) --------------------------------------------------------
    P = lambda a, x, y, yaw=0.0, g="square_props", m=True: inst(a, x, y, yaw, group=g, markers=m)  # noqa: E731
    P("marian_column", 2.0, 14.0)
    for a, x, y, yaw in (("market_stall_meat", -24, -13, PI / 2), ("market_stall_bread", -9, -7, 0.05),
                         ("market_stall_produce", 1, -5, -0.05), ("market_stall_pottery", 12, -3, -0.2),
                         ("market_stall_cloth", -7, 4, 0.15), ("market_stall_produce", 9, 7, -0.1),
                         ("market_stall_weapons", 23, -11, -PI / 2), ("market_stall_bread", -16, 8, 0.3),
                         ("market_stall_produce", -13.5, -17.5, 0.1), ("market_stall_pottery", -4.0, -17.0, -0.1),
                         ("market_stall_cloth", 5.0, -17.5, 0.05), ("market_stall_meat", 17.0, 3.0, -0.3)):
        P(a, x, y, yaw)
    P("spit_roast", -22.5, -21.0, 0.2)
    P("table", -17.5, -19.0, 0.4)
    P("stool", -18.6, -18.2)
    P("stool", -16.4, -19.8)
    P("cooking_pot", -27.0, -4.0)
    _, shed = P("blacksmith_shed", 27.5, -22.5, yaw_from_facing((-0.7, 0.7)))
    for slot, asset in (("MARK_forge", "forge"), ("MARK_anvil", "anvil")):
        loc, yaw = shed[slot]
        P(asset, loc.x, loc.y, yaw + (PI if asset == "forge" else 0.0))
    _, cart = P("cart", 15.0, -16.0, 2.3)
    for tx, ty in ((-27, 24), (27, 27), (-19, 27)):
        P("tree", tx, ty, rnd.uniform(0, 6))
    for bx, by, yaw in ((2, 9.5, 0.0), (-2.5, 14, PI / 2), (6.5, 14, -PI / 2), (2, 18.5, PI)):
        P("bench", bx, by, yaw)
    clutter = [("barrel", -26.5, -18.5), ("barrel", -25.6, -19.4), ("barrel_small", -27.0, -17.4), ("crate", -11.5, -9.5),
               ("sack", -10.6, -10.1), ("crate_produce", 3.6, -7.2), ("basket", 2.6, -7.7), ("crate", 14.5, -5.0),
               ("sack", 15.2, -4.2), ("crate_produce", 11.4, 5.2), ("barrel", 25.2, -14.5), ("weapon_rack", 24.5, -6.5),
               ("crate", -9.0, 2.3), ("basket", -5.3, 2.4), ("barrel_small", -14.5, 6.2), ("sack", 9.8, -14.6),
               ("barrel", -15.6, -19.6), ("crate_produce", -11.6, -18.6), ("basket", -12.2, -15.4), ("sack", -6.4, -18.2),
               ("crate", -2.0, -18.8), ("barrel_small", 2.6, -18.6), ("crate_produce", 7.6, -18.8), ("sack", 3.4, -15.0),
               ("barrel", 19.2, 1.0), ("crate", 15.0, 4.8), ("bread_tray", -9.5, -12.0), ("pottery", -1.5, -14.0)]
    for a, x, y in clutter:
        P(a, x, y, rnd.uniform(0, 2 * PI), m=False)
    # lanterns around the square (inside the arcade line)
    for x, y in ((-24, 29.5), (-8, 29.5), (11, 29.5), (26, 29.5), (-24, -25.5), (-11, -25.5), (12, -25.5), (26, -25.5),
                 (31.5, 20), (31.5, 4), (31.5, -21), (-31.5, 22), (-29.5, -12), (-29.5, 0)):
        inst("street_lantern", x, y, yaw_from_facing((-x, -y)), group="lights", markers=False)
    return hall, cart


def gameplay_markers():
    add_marker("MARK_player_start", "player", V((0, -20, 0)), PI)
    spawns = [("alchemist", (56, 36)), ("alchemist", (-82, -31)), ("alchemist", (-6, 66)), ("alchemist", (12, 64)),
              ("alchemist", (-40, 62)),
              ("skeleton", (0, 58)), ("skeleton", (3, 60)), ("skeleton", (-3, 60)), ("skeleton", (3, -80)),
              ("skeleton", (0, -84)), ("skeleton", (6, -82)),
              ("golem", (96, -8)), ("golem", (1, -92))]
    for i, (t, (x, y)) in enumerate(spawns):
        add_marker(f"MARK_spawn_{t}_{i:02d}", "spawn", V((x, y, 0)), PI, extra={"enemy": t, "time": "night"})
    npcs = [("guard", (-31, -10)), ("guard", (1.5, 28.5)), ("guard", (31, -11)), ("beggar", (6.5, 30.5)), ("beggar", (1.5, 68)),
            ("child_boy", (6, 18)), ("child_girl", (7.2, 17.4)), ("market_woman", (-3, -1)), ("merchant", (16, 10))]
    for i, (t, (x, y)) in enumerate(npcs):
        add_marker(f"MARK_npc_{t}_{i:02d}", "npc", V((x, y, 0)), rnd_yaw(i), extra={"npc": t, "time": "day"})
    patrol = [(-25, -22), (-25, 24), (0, 25), (26, 24), (28, -2), (20, -24), (0, -24)]
    for i, (x, y) in enumerate(patrol):
        add_marker(f"MARK_patrol_square_{i}", "patrol", V((x, y, 0)), 0.0, extra={"route": "square", "index": i})
    wander = [(-14, -14), (-2, -14), (8, -10), (18, 0), (4, 22), (-12, 18), (-20, 0), (22, 14), (-4, 9), (14, 18)]
    for i, (x, y) in enumerate(wander):
        add_marker(f"MARK_wander_{i:02d}", "wander", V((x, y, 0)), 0.0)


def rnd_yaw(i):
    return (i * 2.3) % (2 * PI)


# ============================================================================= lighting & day/night
DN = [  # frame, sun elevation, sun azimuth, sun energy, sun colour, zenith, horizon, sky strength, lamps, windows, moon
    (0, 58, 200, 4.5, (1.0, 0.93, 0.82), (0.32, 0.48, 0.78), (0.78, 0.82, 0.86), 1.0, 0.0, 0.0, 0.0),
    (90, 24, 245, 3.6, (1.0, 0.8, 0.55), (0.3, 0.42, 0.7), (0.95, 0.78, 0.55), 0.9, 0.0, 0.0, 0.0),
    (150, 3, 265, 1.0, (1.0, 0.5, 0.28), (0.14, 0.17, 0.35), (0.85, 0.45, 0.28), 0.6, 1.2, 0.8, 0.2),
    (200, 42, 60, 0.45, (0.55, 0.65, 1.0), (0.02, 0.035, 0.085), (0.06, 0.08, 0.15), 1.2, 2.5, 1.2, 1.0),
    (300, 42, 70, 0.45, (0.55, 0.65, 1.0), (0.02, 0.035, 0.085), (0.06, 0.08, 0.15), 1.2, 2.5, 1.2, 1.0),
    (350, 3, 100, 1.0, (1.0, 0.62, 0.45), (0.16, 0.2, 0.38), (0.9, 0.6, 0.5), 0.6, 0.5, 0.5, 0.2),
    (400, 58, 200, 4.5, (1.0, 0.93, 0.82), (0.32, 0.48, 0.78), (0.78, 0.82, 0.86), 1.0, 0.0, 0.0, 0.0),
]
FRAME_DAY, FRAME_DUSK, FRAME_NIGHT = 0, 150, 250


def setup_lighting():
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 0, 400
    sc.render.fps = 24
    # sky: zenith / horizon gradient driven by view direction
    w = bpy.data.worlds.new("DayNight")
    sc.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    nt = w.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mr = nt.nodes.new("ShaderNodeMapRange")
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = 0.55
    nt.links.new(mr.outputs["Result"], mix.inputs["Factor"])
    rgba = [s for s in mix.inputs if s.type == "RGBA"]
    nt.links.new(mix.outputs[[o.name for o in mix.outputs if o.type == "RGBA"][0]], bg.inputs["Color"])
    horizon, zenith = rgba[0], rgba[1]
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sc.collection.objects.link(sun)
    sun.data.angle = math.radians(1.5)
    # moon disc far away (visible at night)
    mb = G.MB()
    mb.sphere((0, 0, 0), 14.0, "M_Candle", segs=20, rings=12)
    moon = mb.build("Moon")
    mm = bpy.data.materials.new("M_Moon")
    try:
        mm.use_nodes = True
    except Exception:
        pass
    mbsdf = next(n for n in mm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    mbsdf.inputs["Base Color"].default_value = (0.8, 0.82, 0.9, 1)
    mbsdf.inputs["Emission Color"].default_value = (0.85, 0.88, 1.0, 1)
    moon.data.materials.clear()
    moon.data.materials.append(mm)
    moon.visible_shadow = False
    # lamps & glowing materials
    lamp_lights = [l for l in bpy.data.lights if l.type == "POINT"]
    for l in lamp_lights:
        l["night_energy"] = l.energy
        try:
            l.use_shadow = "fire" in l.name.lower() or "forge" in l.name.lower()
        except Exception:
            pass
    glow = [m for m in bpy.data.materials if base_name(m.name) in G.NIGHT_MATS]
    for m in glow:
        m["night_strength"] = G.MATS[base_name(m.name)][4]["strength"]
    for (f, el, az, e, col, zen, hor, ss, lamps, win, moonv) in DN:
        q = (V((0, 0, -1))).to_track_quat("-Z", "Y")
        el_r, az_r = math.radians(el), math.radians(az)
        dirv = V((math.cos(el_r) * math.sin(az_r), math.cos(el_r) * math.cos(az_r), math.sin(el_r)))  # towards the sun
        sun.rotation_euler = (-dirv).to_track_quat("-Z", "Y").to_euler()
        sun.keyframe_insert("rotation_euler", frame=f)
        sun.data.energy = e
        sun.data.color = col
        sun.data.keyframe_insert("energy", frame=f)
        sun.data.keyframe_insert("color", frame=f)
        zenith.default_value = (*zen, 1)
        horizon.default_value = (*hor, 1)
        bg.inputs["Strength"].default_value = ss
        zenith.keyframe_insert("default_value", frame=f)
        horizon.keyframe_insert("default_value", frame=f)
        bg.inputs["Strength"].keyframe_insert("default_value", frame=f)
        for l in lamp_lights:
            always = "fire" in l.name.lower() or "forge" in l.name.lower()
            l.energy = l["night_energy"] * (1.0 if always else lamps) * 1.0
            l.keyframe_insert("energy", frame=f)
        for m in glow:
            b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            b.inputs["Emission Strength"].default_value = m["night_strength"] * win
            b.inputs["Emission Strength"].keyframe_insert("default_value", frame=f)
        moon_dir = V((math.cos(math.radians(30)) * math.sin(math.radians(20)), math.cos(math.radians(30)) * math.cos(math.radians(20)),
                      math.sin(math.radians(30))))
        moon.location = moon_dir * 700
        mbsdf.inputs["Emission Strength"].default_value = 6.0 * moonv
        mbsdf.inputs["Emission Strength"].keyframe_insert("default_value", frame=f)
        moon.hide_render = moonv <= 0.01
        moon.keyframe_insert("hide_render", frame=f)
    return sun


def lighting_presets():
    def preset(row):
        f, el, az, e, col, zen, hor, ss, lamps, win, moonv = row
        return {"frame": f, "sun_elevation_deg": el, "sun_azimuth_deg_from_north": az, "sun_energy": e, "sun_color": col,
                "sky_zenith": zen, "sky_horizon": hor, "sky_strength": ss, "lamp_factor": lamps, "window_emission_factor": win,
                "moon_factor": moonv}
    return {
        "note": "Azimuth measured from Blender +Y (= Godot -Z, north on the level plan) towards +X (east). "
                "Lamp/window factors multiply the per-light energy and per-material emission from the glTF assets. "
                "Fire, forge and coal lights are always on.",
        "keys": [preset(r) for r in DN],
        "cycle_frames": 400,
        "suggested_cycle_seconds": 1200,
        "presets": {"day": preset(DN[0]), "dusk": preset(DN[2]), "night": preset(DN[3])},
    }


# ============================================================================= renders
CAMS = {
    # name: location, look-at, fov
    "square": ((1.5, -27.0, 6.5), (1.0, 40.0, 16.0), 72),
    "square_reverse": ((2.0, 28.0, 7.0), (-2.0, -40.0, 4.0), 68),
    "town_hall": ((-14.0, 8.0, 3.5), (-36.0, -8.0, 10.0), 70),
    "karlova": ((-50.0, -25.0, 3.0), (-70.0, -31.0, 6.0), 70),
    "celetna": ((44.0, -12.5, 3.0), (80.0, -8.0, 7.0), 70),
    "tyn_court": ((1.5, 49.0, 2.5), (1.5, 74.0, 22.0), 75),
    "melantrichova": ((-3.0, -40.0, 3.0), (2.0, -70.0, 6.0), 70),
}


def camera(name, loc, look, fov, ortho=None):
    cam = bpy.data.objects.get("cam_" + name)
    if not cam:
        cam = bpy.data.objects.new("cam_" + name, bpy.data.cameras.new("cam_" + name))
        bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    d = (V(look) - V(loc)).normalized()
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens_unit = "FOV"
    cam.data.angle = math.radians(fov)
    cam.data.clip_end = 3000
    if ortho:
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = ortho
    return cam


def render_all():
    os.makedirs(RENDER_DIR, exist_ok=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    try:
        sc.eevee.taa_render_samples = 32
        sc.view_settings.view_transform = "Standard"
    except Exception:
        pass
    for o in bpy.data.objects:
        if o.name.endswith("-colonly"):
            o.hide_render = True
    out = {}
    for name, (loc, look, fov) in CAMS.items():
        sc.camera = camera(name, loc, look, fov)
        frames = [("day", FRAME_DAY), ("night", FRAME_NIGHT)] + ([("dusk", FRAME_DUSK)] if name == "square" else [])
        for tag, fr in frames:
            sc.frame_set(fr)
            sc.render.filepath = os.path.join(RENDER_DIR, f"{name}_{tag}.png")
            bpy.ops.render.render(write_still=True)
            out[f"{name}_{tag}"] = sc.render.filepath
            print("RENDERED", sc.render.filepath)
    # plan view with marker overlay
    viz = bpy.data.collections.new("MarkerViz")
    sc.collection.children.link(viz)
    colors = {"spawn": (0.9, 0.1, 0.1), "npc": (0.1, 0.8, 0.2), "merchant": (1.0, 0.85, 0.1), "door": (0.2, 0.4, 1.0),
              "window": (0.4, 0.9, 1.0), "exit": (1.0, 0.1, 0.9), "player": (1, 1, 1), "patrol": (0.1, 0.5, 0.1),
              "smith": (1.0, 0.5, 0.0), "cook": (1.0, 0.5, 0.0), "horse": (0.6, 0.35, 0.1), "wander": (0.5, 0.9, 0.5)}
    mats = {}
    for k, c in colors.items():
        m = bpy.data.materials.new("viz_" + k)
        try:
            m.use_nodes = True
        except Exception:
            pass
        b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Base Color"].default_value = (*c, 1)
        b.inputs["Emission Color"].default_value = (*c, 1)
        b.inputs["Emission Strength"].default_value = 2.0
        mats[k] = m
    for mk in MARKERS:
        if mk["kind"] not in colors:
            continue
        gx, gy, gz = mk["pos"]
        r = 1.6 if mk["kind"] in ("spawn", "exit", "player") else 0.8
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=(gx, -gz, 40.0), segments=10, ring_count=6)
        o = bpy.context.active_object
        o.data.materials.append(mats[mk["kind"]])
        for c in o.users_collection:
            c.objects.unlink(o)
        viz.objects.link(o)
    sc.camera = camera("plan", (5.0, -8.0, 300.0), (5.0, -7.99, 0.0), 50, ortho=230)
    sc.render.resolution_x, sc.render.resolution_y = 1600, 1600
    sc.frame_set(FRAME_DAY)
    sc.render.filepath = os.path.join(RENDER_DIR, "plan_markers.png")
    bpy.ops.render.render(write_still=True)
    viz.hide_render = True
    sc.render.filepath = os.path.join(RENDER_DIR, "plan.png")
    bpy.ops.render.render(write_still=True)
    for o in list(viz.objects):
        bpy.data.objects.remove(o)
    bpy.data.collections.remove(viz)
    return out


def comparisons():
    """Concept art next to the matching render (day, night)."""
    import numpy as np
    for tag in ("day", "night"):
        a = os.path.join(G.PROJECT, "concept", "locations", f"old_town_square_{tag}.png")
        b = os.path.join(RENDER_DIR, f"square_{tag}.png")
        imgs = []
        for p in (a, b):
            im = bpy.data.images.load(p)
            w, h = im.size
            px = np.array(im.pixels[:], np.float32).reshape(h, w, 4)
            ys = (np.arange(450) * h / 450).astype(int)
            xs = (np.arange(800) * w / 800).astype(int)
            imgs.append(px[ys][:, xs])
            bpy.data.images.remove(im)
        sheet = np.concatenate(imgs, axis=1)
        o = bpy.data.images.new("cmp", sheet.shape[1], sheet.shape[0], alpha=True)
        o.pixels.foreach_set(sheet.ravel())
        o.filepath_raw = os.path.join(RENDER_DIR, f"compare_{tag}.png")
        o.file_format = "PNG"
        o.save()


# ============================================================================= main
def main():
    global WORLD_COL, MARK_COL
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    G.reset_scene()
    append_assets()
    WORLD_COL = bpy.data.collections.new("World")
    bpy.context.scene.collection.children.link(WORLD_COL)
    MARK_COL = bpy.data.collections.new("Markers")
    bpy.context.scene.collection.children.link(MARK_COL)
    build_layout()
    gameplay_markers()
    setup_lighting()
    # bounds of the playable area
    xs = [m["pos"][0] for m in LAYOUT if m["group"] != "ground"]
    zs = [m["pos"][2] for m in LAYOUT if m["group"] != "ground"]
    data = {
        "level": "old_town_square",
        "version": 1,
        "coordinate_system": "Godot: +Y up, -Z = north on the plan (Blender +Y). Characters/house fronts face local +Z.",
        "bounds": {"x": [min(xs) - 10, max(xs) + 10], "z": [min(zs) - 10, max(zs) + 10]},
        "instances": LAYOUT,
        "markers": MARKERS,
        "lighting": lighting_presets(),
    }
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    kinds = {}
    for m in MARKERS:
        kinds[m["kind"]] = kinds.get(m["kind"], 0) + 1
    assets = {}
    for i in LAYOUT:
        assets[i["asset"]] = assets.get(i["asset"], 0) + 1
    print("INSTANCES", len(LAYOUT), json.dumps(assets))
    print("MARKERS", len(MARKERS), json.dumps(kinds))
    lights = sum(1 for i in LAYOUT for o in COLS[i["asset"]].all_objects if o.type == "LIGHT")
    print("LIGHTS", lights)
    bpy.context.scene.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(G.BLENDER_DIR, "world_old_town.blend"))
    if "--no-render" not in argv:
        render_all()
        comparisons()
        bpy.context.scene.frame_set(0)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(G.BLENDER_DIR, "world_old_town.blend"))
    print("DONE world")


if __name__ == "__main__":
    main()
