"""One connected world: Old Town, Charles Bridge, Mala Strana and Vysehrad side by side (Tasks 3 + 4, run 3).

blender -b --factory-startup -P build_prague.py [-- --no-render]
Outputs: blender/world_prague.blend, blender/scene_prague.blend,
         assets/levels/prague_layout.json, assets/levels/prague_population.json, assets/ui/map_prague.png,
         renders/world/prague_*.png

Every district is built by its own level builder (build_world.build_layout for the Old Town, build_world_ext.LEVELS for
the others) in its local frame; inst()/add_marker()/spawn() are wrapped so everything lands at the district's offset.
Geography (Blender coords, north = +Y): the Old Town at the origin; Karlova runs west into the street in front of the
Old Town bridge tower; the bridge crosses the Vltava (x -328..-184) to the Lesser Town tower, behind which Mala Strana's
Mostecka continues west; Vysehrad sits south of the Old Town on a crag over the river, 10 m up, reached by a road that
climbs from the end of Melantrichova to the gate lane. River, walls, closed gates and invisible blockers bound the world.
"""
import json
import math
import os
import random
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import lib_geo as G  # noqa: E402
import build_world as BW  # noqa: E402
import build_scene as BS  # noqa: E402
import build_world_ext as BX  # noqa: E402

PI = math.pi
V = Vector
yf = BW.yaw_from_facing

DISTRICTS = [  # id, display name, offset (Blender x, y, z)
    ("old_town", "Old Town Square", (0.0, 0.0, 0.0)),
    ("charles_bridge", "Charles Bridge", (-256.0, -32.0, 0.0)),
    ("mala_strana", "Malá Strana", (-456.0, -32.0, 0.0)),
    ("vysehrad", "Vyšehrad", (-134.0, -170.0, 10.0)),
]
# rectangles (Blender x0, x1, y0, y1) used by the game to name the district under the player; first match wins
DISTRICT_RECTS = [("vysehrad", (-210, 24, -245, -98)), ("mala_strana", (-610, -341, -75, 75)),
                  ("charles_bridge", (-360, -96, -215, 145)), ("old_town", (-140, 150, -130, 140))]
TRAVEL = {"old_town", "charles_bridge", "mala_strana", "vysehrad"}
WATER = [{"height": -6.0, "rect": [-328.0, -1500.0, -184.0, 1500.0]}]
PLANES = [{"height": -0.4, "rect": [-1500.0, -1500.0, -328.0, 1500.0], "material": "grass"},
          {"height": -0.4, "rect": [-184.0, -1500.0, 1500.0, 1500.0], "material": "grass"}]
MAP = dict(center=(-210.0, -45.0), size=800.0)          # Blender centre; Godot centre = (x, -y)
# Painted map = crop of the 1600 px plan render, px (40, 300)-(1540, 1300) at 0.5 m/px -> Godot X/Z rectangle.
# If the plan or the world bounds change, re-crop, repaint (AGENTS.md) and update this.
MAP_PAINTED_RECT = (-590.0, -205.0, 160.0, 295.0)

CUR = {"d": "old_town", "off": V((0, 0, 0))}
_IN = [False]
_TILES = []                                            # placed ground tiles: (x0, x1, y0, y1, z)
_orig_inst = BW.inst
_orig_marker = BW.add_marker
_orig_spawn = BS.spawn


# ============================================================================= what to leave out where districts meet
def skip(d, asset, group, lx, ly, wx, wy):
    if asset in ("city_backdrop", "bridge_far") or (asset == "castle_hill" and d != "mala_strana"):
        return True
    if d == "old_town":
        # end-cap houses of Karlova and Melantrichova: those streets now continue into the bridge street / the road
        if group == "street_karlova" and asset.startswith("house") and lx < -99:
            return True
        if group == "street_melantrichova" and asset.startswith("house") and ly < -99:
            return True
    if d == "charles_bridge":
        if group == "west_street" or (group == "lights" and lx < -100):
            return True                                # Mala Strana's own Mostecka replaces it
        if group == "east_street" and lx > 166:
            return True                                # end cap: Karlova continues here
        if asset == "st_nicholas" and group == "backdrop":
            return True
        if group in ("east_bank", "banks", "ground", "lights") and lx > 0 and wy < -88:
            return True                                # south of here the Vysehrad crag meets the river
        if group == "west_bank" and lx < 0 and 0 < ly and wy < 52:
            return True                                # room for Mala Strana's terrace
    if d == "mala_strana":
        if asset == "bridge_tower_lesser":
            return True                                # the bridge level's tower is the same tower
        if group == "terrace" and lx > 92 and asset != "street_lantern":
            return True                                # terrace ends at the river street (new east wall)
        if asset == "ground_cobble" and ly > 30 and lx > 88:
            return True
    if d == "vysehrad":
        if asset == "fortress_tower" and lx > 120:
            return True                                # lane end: the road from the Old Town comes in here
    return False


def tile_free(wx, wy, wz, half=8.0):
    for (x0, x1, y0, y1, z) in _TILES:
        if abs(z - wz) < 0.5 and min(x1, wx + half) - max(x0, wx - half) > 0.5 and min(y1, wy + half) - max(y0, wy - half) > 0.5:
            return False
    _TILES.append((wx - half, wx + half, wy - half, wy + half, wz))
    return True


# ============================================================================= wrappers
def inst(asset, x, y, yaw=0.0, z=0.0, group="misc", markers=True):
    d, o = CUR["d"], CUR["off"]
    wx, wy, wz = x + o.x, y + o.y, z + o.z
    if skip(d, asset, group, x, y, wx, wy):
        return None, {}
    if asset.startswith("ground_") and not tile_free(wx, wy, wz):
        return None, {}
    _IN[0] = True
    try:
        e, out = _orig_inst(asset, wx, wy, yaw, wz, group=group, markers=markers)
    finally:
        _IN[0] = False
    BW.LAYOUT[-1]["district"] = d
    for m in BW.MARKERS:
        m.setdefault("district", d)
    return e, out


def add_marker(name, kind, loc, yaw=0.0, owner=None, extra=None):
    d = CUR["d"]
    if not _IN[0]:
        if kind == "exit" and (extra or {}).get("leads_to") in TRAVEL:
            return None                                # districts are joined: no travel exits any more
        loc = V(loc) + CUR["off"]
        if d != "old_town":
            name = f"{name}@{d}"
    e = _orig_marker(name, kind, loc, yaw, owner, extra)
    BW.MARKERS[-1]["district"] = d
    return e


def godot_off():
    o = CUR["off"]
    return (o.x, o.z, -o.y)


def spawn(char, loc, yaw, action, schedule="day", role="", offset=None, group=None, extra=None):
    d = CUR["d"]
    gx, gy, gz = godot_off()
    extra = dict(extra or {})
    if "route_points" in extra:
        extra["route_points"] = [[round(p[0] + gx, 2), round(p[1] + gy, 2), round(p[2] + gz, 2)] for p in extra["route_points"]]
    if "route" in extra and d != "old_town":
        extra["route"] = [f"{n}@{d}" for n in extra["route"]]
    extra["district"] = d
    return _orig_spawn(char, V(loc) + CUR["off"], yaw, action, schedule, role, offset, group, extra)


BW.inst = inst
BW.add_marker = add_marker


# ============================================================================= joints between the districts
def J(asset, x, y, yaw=0.0, z=0.0, g="joints"):
    CUR["d"], CUR["off"] = "joints", V((0, 0, 0))
    _IN[0] = True
    try:
        _orig_inst(asset, x, y, yaw, z, group=g, markers=False)
    finally:
        _IN[0] = False
    BW.LAYOUT[-1]["district"] = "joints"


def joints():
    # the road up to Vysehrad: four ramps from the end of Melantrichova (y=-98, z=0) to the gate lane (y=-162, z=10)
    def h(y):
        return max(0.0, min(10.0, 10.0 * (-98.0 - y) / 64.0))
    for k in range(4):
        J("road_ramp", 2.0, -106.0 - 16.0 * k, PI, 2.5 * k)
    for yc in (-104, -116, -128, -140, -152):
        J("fortress_wall", -5.4, yc, yf((-1, 0)), h(yc) - 2.0)
        J("fortress_wall", 9.4, yc, yf((1, 0)), h(yc) - 2.0)
    J("ground_dirt", 2.0, -170.0, 0.0, 10.0)                       # landing in front of the lane
    for x in (-10.0,):
        J("fortress_wall", x, -161.6, yf((0, 1)), 8.0)
    J("fortress_wall", 13.0, -161.6, yf((0, 1)), 8.0)
    J("fortress_wall", 10.0, -170.0, yf((1, 0)), 8.0)
    for x in (-6.0, 6.0):
        J("fortress_wall", x, -178.4, 0.0, 8.0)
    for y in (-110.0, -150.0):
        J("street_lantern", 7.2, y, yf((-1, 0)), h(y), "lights")
    # embankment streets end against short city walls
    for xs, y, face in (((-178, -166), 130.0, 1), ((-178, -166), -90.0, -1), ((-346, -334), 130.0, 1), ((-346, -334), -194.0, -1)):
        for x in xs:
            J("fortress_wall", x, y, yf((0, face)))
    # Mala Strana's terrace ends above the river street with a retaining wall facing east
    for y in (9.0, 25.0, 41.0):
        J("retaining_wall", -360.0, y, yf((1, 0)))
    J("garden_wall", -356.0, 52.5, 0.0)


def blockers():
    """Invisible walls (Godot coords: centre, size): the edge of the world and the closed castle gate."""
    def box(x0, x1, y0, y1, z0, z1):
        return {"center": [round((x0 + x1) / 2, 2), round((z0 + z1) / 2, 2), round(-(y0 + y1) / 2, 2)],
                "size": [round(x1 - x0, 2), round(z1 - z0, 2), round(y1 - y0, 2)]}
    X0, X1, Y0, Y1 = -620.0, 200.0, -260.0, 160.0
    out = [box(X0, X1, Y1, Y1 + 2, -10, 60), box(X0, X1, Y0 - 2, Y0, -10, 60),
           box(X0 - 2, X0, Y0, Y1, -10, 60), box(X1, X1 + 2, Y0, Y1, -10, 60)]
    out.append(box(-517.0, -515.5, 4.0, 14.0, 8.0, 14.0))         # castle gate on the Nerudova terrace (closed road)
    out.append(box(-360.6, -359.4, 49.0, 56.0, 0.0, 12.0))        # corner between terrace wall and garden wall
    return out


# ============================================================================= helpers for Task 4
def local_layout(data, d, off):
    """The district's slice of the world layout, moved back into its own frame (names without the @district)."""
    gx, gy, gz = off.x, off.z, -off.y
    suf = "@" + d

    def back(p):
        return [round(p[0] - gx, 3), round(p[1] - gy, 3), round(p[2] - gz, 3)]
    inst_ = [dict(i, pos=back(i["pos"])) for i in data["instances"] if i.get("district") == d]
    marks = []
    for m in data["markers"]:
        if m.get("district") != d:
            continue
        n = m["name"][:-len(suf)] if m["name"].endswith(suf) else m["name"]
        marks.append(dict(m, name=n, pos=back(m["pos"])))
    return {"instances": inst_, "markers": marks}


def render_world():
    sc = bpy.context.scene
    hide = [o for o in bpy.data.objects if o.instance_type == "COLLECTION" and o.instance_collection and
            o.instance_collection.name == "castle_hill"]
    for o in hide:
        o.hide_render = True
    cx, cy = MAP["center"]
    sc.render.engine = "BLENDER_EEVEE"
    try:
        sc.eevee.taa_render_samples = 24
        sc.view_settings.view_transform = "Standard"
    except Exception:
        pass
    for o in bpy.data.objects:
        if o.name.endswith("-colonly"):
            o.hide_render = True
    sc.camera = BW.camera("prague_plan", (cx, cy, 400.0), (cx, cy + 0.01, 0.0), 50, ortho=MAP["size"])
    sc.render.resolution_x = sc.render.resolution_y = 1600
    sc.frame_set(BW.FRAME_DAY)
    out = os.path.join(G.PROJECT, "renders", "world", "prague_plan.png")
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    shutil.copy(out, os.path.join(G.PROJECT, "assets", "ui", "map_prague.png"))
    for o in hide:
        o.hide_render = False
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    cams = {"overview": ((-120.0, -330.0, 140.0), (-250.0, 0.0, 0.0), 62),
            "karlova_bridge": ((-70.0, -30.5, 3.0), (-200.0, -32.0, 6.0), 70),
            "road_vysehrad": ((2.0, -94.0, 3.2), (2.0, -170.0, 12.0), 70),
            "bridge_mala": ((-300.0, -33.5, 2.6), (-480.0, -30.0, 10.0), 70)}
    for name, (loc, look, fov) in cams.items():
        sc.camera = BW.camera("prague_" + name, loc, look, fov)
        for tag, fr in (("day", BW.FRAME_DAY), ("night", BW.FRAME_NIGHT)):
            sc.frame_set(fr)
            sc.render.filepath = os.path.join(G.PROJECT, "renders", "world", f"prague_{name}_{tag}.png")
            bpy.ops.render.render(write_still=True)
            print("RENDERED", sc.render.filepath)


# ============================================================================= main
def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    G.reset_scene()
    BX.append_all()
    BW.WORLD_COL = bpy.data.collections.new("World")
    bpy.context.scene.collection.children.link(BW.WORLD_COL)
    BW.MARK_COL = bpy.data.collections.new("Markers")
    bpy.context.scene.collection.children.link(BW.MARK_COL)
    seeds = {"charles_bridge": 1357, "mala_strana": 1257, "vysehrad": 1070}
    for d, _name, off in DISTRICTS:
        CUR["d"], CUR["off"] = d, V(off)
        print("DISTRICT", d)
        if d == "old_town":
            BW.build_layout()
            BW.gameplay_markers()
        else:
            BX.LEVELS[d](random.Random(seeds[d]))
    joints()
    CUR["d"], CUR["off"] = "old_town", V((0, 0, 0))
    BW.setup_lighting()
    BX.water_planes({"water": WATER, "planes": PLANES})
    districts = []
    for d, name, off in DISTRICTS:
        x0, x1, y0, y1 = dict(DISTRICT_RECTS)[d]
        districts.append({"id": d, "name": name, "rect": [x0, -y1, x1, -y0], "offset": [off[0], off[2], -off[1]],
                          "fog": BX_FOG.get(d, 0.003)})
    xs = [m["pos"][0] for m in BW.LAYOUT if m["group"] not in ("ground", "backdrop")]
    zs = [m["pos"][2] for m in BW.LAYOUT if m["group"] not in ("ground", "backdrop")]
    data = {
        "level": "prague", "display": "Prague", "version": 2,
        "coordinate_system": "Godot: +Y up, -Z = north on the plan (Blender +Y). Characters/house fronts face local +Z.",
        "bounds": {"x": [min(xs) - 10, max(xs) + 10], "z": [min(zs) - 10, max(zs) + 10]},
        "districts": districts, "water": WATER, "planes": PLANES, "blockers": blockers(), "kill_y": -5.5,
        # Map tab: hand-painted map (concept_art/map/, made from a crop of the plan render, then aligned to it).
        # "rect" = Godot [x0, z0, x1, z1] covered by the image; "center"/"size" describe the raw plan render.
        "map": {"rect": list(MAP_PAINTED_RECT), "image": "res://assets/ui/map_prague_painted.png",
                "center": [MAP["center"][0], -MAP["center"][1]], "size": MAP["size"]},
        "instances": BW.LAYOUT, "markers": BW.MARKERS, "lighting": BW.lighting_presets(),
    }
    with open(os.path.join(G.PROJECT, "assets", "levels", "prague_layout.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    per = {}
    for i in BW.LAYOUT:
        per[i.get("district", "?")] = per.get(i.get("district", "?"), 0) + 1
    print("INSTANCES", len(BW.LAYOUT), json.dumps(per), "MARKERS", len(BW.MARKERS))
    bpy.context.scene.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(G.BLENDER_DIR, "world_prague.blend"))
    if "--no-render" not in argv:
        render_world()
    # ---------------- Task 4: population of every district in its own frame, moved into place by spawn()
    BS.load_characters()
    for c in BS.CHARS.values():
        for o in c.all_objects:
            if o.type == "ARMATURE" and o.animation_data:
                for t in o.animation_data.nla_tracks:
                    t.mute = True
    BS.spawn = spawn
    fx_all = []
    for d, _name, off in DISTRICTS:
        CUR["d"], CUR["off"] = d, V(off)
        loc = local_layout(data, d, V(off))
        BS.FX.clear()
        if d == "old_town":
            BS.banners(loc)
            BS.populate(loc)
            BS.animate_environment(loc)
        else:
            BX.populate(d, loc)
            BX.fx_level(d, loc)
        gx, gy, gz = off[0], off[2], -off[1]
        for fx in BS.FX:
            if "pos" in fx and isinstance(fx["pos"], list) and d != "old_town":
                fx = dict(fx, pos=[fx["pos"][0] + gx, fx["pos"][1] + gy, fx["pos"][2] + gz])
            if fx not in fx_all:
                fx_all.append(dict(fx, district=d))
    counts = {}
    for p in BS.POP:
        key = f"{p['district']}:{p['schedule']}"
        counts[key] = counts.get(key, 0) + 1
    pop = {"level": "prague", "version": 2,
           "coordinate_system": "Godot coordinates (same as prague_layout.json). Characters face local +Z.",
           "schedule": {"day": "visible/active by day", "night": "spawned at dusk (enemies)", "always": "day and night"},
           "population": BS.POP, "fx": fx_all, "counts": counts}
    with open(os.path.join(G.PROJECT, "assets", "levels", "prague_population.json"), "w", encoding="utf-8") as f:
        json.dump(pop, f, ensure_ascii=False, indent=1)
    print("POPULATION", len(BS.POP), json.dumps(counts))
    bpy.context.scene.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(G.BLENDER_DIR, "scene_prague.blend"))
    print("DONE prague")


BX_FOG = {"old_town": 0.0045, "charles_bridge": 0.0022, "mala_strana": 0.003, "vysehrad": 0.0016}

if __name__ == "__main__":
    main()
