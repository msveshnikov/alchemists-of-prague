"""Run 2, Tasks 3 + 4: empty levels and their population for Charles Bridge, Mala Strana and Vysehrad.

blender -b --factory-startup -P build_world_ext.py -- --level charles_bridge [--no-render]
Outputs per level <L>:
  Task 3: blender/world_<L>.blend, assets/levels/<L>_layout.json, renders/world/<L>_*.png (empty level, plan, compare)
  Task 4: blender/scene_<L>.blend, assets/levels/<L>_population.json, renders/scene/<L>_*.png, assets/ui/map_<L>.png
Coordinates in the JSON are Godot coordinates (+Y up, north of the plan = -Z), exactly like old_town_layout.json.
Extra layout fields used by the game: "display" (name), "water" (river planes), "planes" (far land), "kill_y", "map".
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
import loc_common  # noqa: E402,F401  (registers run-2 materials)
import build_world as BW  # noqa: E402
import build_scene as BS  # noqa: E402

PI = math.pi
V = Vector
yf = BW.yaw_from_facing
TIMBER = ["house_timber_a", "house_timber_b", "house_timber_c", "house_timber_d"]
BURGHER = BW.HOUSE_POOL

BW.MARK_KIND[:0] = [("MARK_ledge", "ledge"), ("MARK_gate", "gate"), ("MARK_innkeeper", "npc_slot"), ("MARK_inn", "inn"),
                    ("MARK_stairs", "poi"), ("MARK_guard_post", "guard_post"), ("MARK_pier", None)]


def append_all():
    for fname in ("architecture.blend", "props.blend", "locations.blend"):
        with bpy.data.libraries.load(os.path.join(G.BLENDER_DIR, fname), link=False) as (src, dst):
            dst.collections = list(src.collections)
        for c in dst.collections:
            BW.COLS[c.name] = c
            root = c.objects.get(c.name) or next((o for o in c.objects if o.parent is None), None)
            BW.CATEGORY[c.name] = root.get("asset_category", "props") if root else "props"
            if root and "size" in root:
                BW.SIZE[c.name] = list(root["size"])


def I(asset, x, y, yaw=0.0, z=0.0, g="misc", m=True):
    return BW.inst(asset, x, y, yaw, z, group=g, markers=m)


def M(name, kind, x, y, yaw=0.0, z=0.0, **extra):
    return BW.add_marker(name, kind, V((x, y, z)), yaw, extra=extra or None)


def tiles(asset, xs, ys, z=0.0, g="ground"):
    for x in xs:
        for y in ys:
            I(asset, x, y, 0.0, z, g, False)


def frange(a, b, step):
    out = []
    v = a
    while v <= b + 1e-6:
        out.append(v)
        v += step
    return out


# ============================================================================= Charles Bridge
def level_charles_bridge(rnd):
    # bridge: six 24 m bays from x=-72 to 72, towers on both banks (gate passage along X)
    for x in frange(-60, 60, 24):
        I("bridge_span", x, 0, 0.0, g="bridge")
    I("bridge_tower", 77.5, 0, yf((1, 0)), g="bridge")
    I("bridge_tower_lesser", -77.5, 0, yf((-1, 0)), g="bridge")
    for x in (-48, -24, 0, 24, 48):
        for sy in (-1, 1):
            if (x, sy) in ((24, 1),):
                continue
            I("bridge_statue", x, sy * 5.85, yf((0, -sy)), 1.2, "bridge", False)
    for k, x in enumerate(frange(-60, 60, 24)):
        sy = 1 if k % 2 else -1
        I("street_lantern", x, sy * 4.4, yf((0, -sy)), g="lights", m=False)
    I("guard_booth", 18, 3.5, 0.0, g="bridge")
    # river banks: stone embankments, landing stage, boats on the Vltava
    for sx in (-1, 1):
        for y in frange(14, 158, 16):
            for sy in (-1, 1):
                I("embankment", sx * 72, sy * y, yf((-sx, 0)), g="banks")
    I("jetty", 68.5, -50, PI / 2, -5.4, "river", False)
    I("boat_row", 64.0, -44.0, PI / 2 + 0.1, -6.0, "river", False)
    I("boat_barge", 28.0, -46.0, 0.25, -6.0, "river", False)
    I("boat_row", -32.0, 28.0, 1.2, -6.0, "river", False)
    I("boat_row", 46.0, 74.0, -0.4, -6.0, "river", False)
    I("boat_barge", -44.0, -90.0, -0.2, -6.0, "river", False)
    # Old Town bank (east): embankment street, small square in front of the tower, street to the Old Town
    tiles("ground_cobble", frange(80, 160, 16), frange(-160, 160, 16))
    BW.fill_row((84, 160), (-1, 0), 142, rnd, "east_bank", pool=BURGHER, gothic=0.1)
    BW.fill_row((84, -18), (-1, 0), 142, rnd, "east_bank", pool=BURGHER, gothic=0.1)
    BW.fill_row((96, 18), (0, -1), 34, rnd, "east_square", pool=BURGHER, gothic=0.0)
    BW.fill_row((130, -18), (0, 1), 34, rnd, "east_square", pool=BURGHER, gothic=0.0)
    BW.fill_row((130, 18), (-1, 0), 13, rnd, "east_square", pool=["house_burgher_e", "house_burgher_b"], gothic=0.0)
    BW.fill_row((130, -5), (-1, 0), 13, rnd, "east_square", pool=["house_burgher_e", "house_burgher_b"], gothic=0.0)
    BW.fill_row((142, 5), (0, -1), 18, rnd, "east_street", pool=BURGHER, gothic=0.0)
    BW.fill_row((160, -5), (0, 1), 18, rnd, "east_street", pool=BURGHER, gothic=0.0)
    I("house_gothic_tower", 172, 0, yf((-1, 0)), g="east_street")
    for a, x, y, yaw in (("market_stall_produce", 100, -11, 0.15), ("market_stall_bread", 112, 11, PI + 0.1)):
        I(a, x, y, yaw, g="east_square")
    for a, x, y in (("barrel", 96, -14), ("barrel_small", 97, -15.2), ("crate", 104, -14.5), ("sack", 108, 13.5),
                    ("crate_produce", 115, 13.5), ("basket", 98, -8.5), ("barrel", 124, 14)):
        I(a, x, y, rnd.uniform(0, 2 * PI), g="east_square", m=False)
    I("cart", 120, -8, 2.2, g="east_square", m=False)
    I("tree", 125, -13, 0.4, g="east_square", m=False)
    for x, y in ((90, 9), (90, -9), (126, 3), (78, 30), (78, -30), (78, 70), (78, -70), (78, 110), (78, -110)):
        I("street_lantern", x, y, yf((-1, 0)) if x < 80 else yf((0, -1 if y > 0 else 1)), g="lights", m=False)
    # Mala Strana bank (west): embankment street of half-timbered houses, street west to Mala Strana
    tiles("ground_cobble", frange(-160, -80, 16), frange(-160, 160, 16))
    BW.fill_row((-84, 18), (1, 0), 142, rnd, "west_bank", pool=TIMBER, gothic=0.0)
    BW.fill_row((-84, -160), (1, 0), 142, rnd, "west_bank", pool=TIMBER, gothic=0.0)
    BW.fill_row((-150, 6), (0, -1), 66, rnd, "west_street", pool=TIMBER, gothic=0.0)
    BW.fill_row((-84, -6), (0, 1), 66, rnd, "west_street", pool=TIMBER, gothic=0.0)
    I("house_timber_b", -162, 0, yf((1, 0)), g="west_street")
    for x, y in ((-78, 30), (-78, -30), (-78, 70), (-78, -70), (-110, 4), (-130, -4)):
        I("street_lantern", x, y, yf((1, 0)) if x > -80 else yf((0, -1 if y > 0 else 1)), g="lights", m=False)
    for y in (40, 90, -60):
        I("tree", -76, y, rnd.uniform(0, 6), g="west_bank", m=False)
    # backdrops
    I("castle_hill", -470, 70, yf((1, 0)), 12.0, "backdrop", False)
    I("st_nicholas", -230, 40, yf((1, 0)), 6.0, "backdrop", False)
    I("city_backdrop", 360, 0, yf((-1, 0)), 0.0, "backdrop", False)
    # gameplay markers
    M("MARK_player_start", "player", 110, 0, yf((-1, 0)))
    M("MARK_exit_old_town", "exit", 156, 0, yf((-1, 0)), leads_to="old_town")
    M("MARK_exit_mala_strana", "exit", -150, 0, yf((1, 0)), leads_to="mala_strana")
    for i, (t, x, y) in enumerate((("skeleton", 2, 1.5), ("skeleton", -1, -2), ("skeleton", 4, -1), ("golem", 36, 0),
                                   ("alchemist", -48, 2), ("alchemist", 104, 12), ("skeleton", -118, 2), ("skeleton", -122, -2),
                                   ("alchemist", -40, -2), ("skeleton", 60, 2))):
        M(f"MARK_spawn_{t}_{i:02d}", "spawn", x, y, PI, enemy=t, time="night")
    for i, (x, y) in enumerate(((66, 0), (30, -2.5), (-30, 2.5), (-66, 0), (-30, -2.5), (30, 2.5))):
        M(f"MARK_patrol_bridge_{i}", "patrol", x, y, route="bridge", index=i)
    for i, (x, y) in enumerate(((100, 2), (60, -3), (0, -2), (-60, -3), (-100, 1), (-60, 3), (0, 2), (60, 3))):
        M(f"MARK_wander_{i:02d}", "wander", x, y)
    water = [{"height": -6.0, "rect": [-72.0, -600.0, 72.0, 600.0]}]
    return dict(display="Charles Bridge", water=water, kill_z=-5.5,
                planes=[], map=dict(center=(0.0, 0.0), size=340.0),
                cams={"bridge": ((70.0, -44.0, 21.0), (-34.0, 8.0, 0.0), 70),
                      "deck": ((66.0, -1.5, 1.8), (-60.0, 2.0, 4.0), 70),
                      "river": ((60.0, -70.0, -2.5), (-10.0, 10.0, -1.0), 70),
                      "west": ((-100.0, 2.0, 2.4), (-160.0, 2.0, 5.0), 70)},
                concept="bridge")


# ============================================================================= Mala Strana
def level_mala_strana(rnd):
    tiles("ground_cobble", frange(-104, 120, 16), frange(-40, 24, 16))
    tiles("ground_cobble", frange(-104, 120, 16), (41, 57, 73), z=8.0, g="terrace")
    # lower street (Mostecka) and the little square with St Nicholas at its west end
    BW.fill_row((-20, 5), (0, -1), 28.9, rnd, "lower_north", pool=TIMBER, gothic=0.0)
    BW.fill_row((15.1, 5), (0, -1), 99.9, rnd, "lower_north", pool=TIMBER, gothic=0.0)
    I("tavern", 40, -10.5, yf((0, 1)), g="lower_south")
    BW.fill_row((115, -5), (0, 1), 69, rnd, "lower_south", pool=TIMBER, gothic=0.0)
    BW.fill_row((34, -5), (0, 1), 54, rnd, "lower_south", pool=TIMBER + ["house_burgher_c"], gothic=0.0)
    BW.fill_row((-60, 20), (0, -1), 40, rnd, "square", pool=TIMBER, gothic=0.0)
    BW.fill_row((-20, -20), (0, 1), 40, rnd, "square", pool=TIMBER, gothic=0.0)
    I("st_nicholas", -62, 0, yf((1, 0)), g="square")
    for y in (15.5, -15.5):
        I("garden_wall", -63, y, yf((1, 0)), g="square", m=False)
    I("bridge_tower_lesser", 121, 0, yf((-1, 0)), g="lower_street")
    # castle stairs up to the terrace, retaining walls with a statue niche, upper street (Nerudova)
    I("castle_stairs", 12, 19, 0.0, g="stairs")
    for x in (0.9, -15.1, -31.1, -47.1, -63.1, -79.1, -95.1):
        I("retaining_wall", x, 33, 0.0, g="terrace")
    for x in (23.1, 39.1, 55.1, 71.1, 87.1, 103.1, 119.1):
        I("retaining_wall_niche" if x == 23.1 else "retaining_wall", x, 33, 0.0, g="terrace")
    BW.fill_row((-56, 47), (0, -1), 168, rnd, "terrace", pool=TIMBER, gothic=0.0)
    I("gate_tower", -62, 41, yf((-1, 0)), 8.0, "terrace")
    I("house_timber_c", 118, 41, yf((-1, 0)), 8.0, "terrace")
    for x in (-40, -10, 30, 60, 90):
        I("street_lantern", x, 36.2, yf((0, 1)), 8.0, "lights", False)
    # street furnishing: tavern terrace, square market, lanterns, planters
    for x in (35.5, 44.5):
        I("table", x, -3.0, 0.0, g="tavern", m=False)
        I("bench", x, -1.9, 0.0, g="tavern", m=False)
        I("bench", x, -4.1, PI, g="tavern", m=False)
    for a, x, y in (("barrel", 31.0, -4.2), ("barrel_small", 31.8, -3.4), ("barrel", 49.2, -4.3), ("planter", 52, -4.6),
                    ("planter", 27, -4.6), ("planter", 70, 4.6), ("planter", -5, 4.6), ("crate", 92, -4.2), ("sack", 93, -3.6)):
        I(a, x, y, 0.0 if a == "planter" else rnd.uniform(0, 6), g="street_props", m=False)
    for a, x, y, yaw in (("market_stall_produce", -42, -9, 0.2), ("market_stall_bread", -34, 9, PI - 0.15),
                         ("market_stall_pottery", -48, 8, PI + 0.2)):
        I(a, x, y, yaw, g="square")
    I("cart", -28, -12, 0.6, g="square", m=False)
    for x, y in ((-52, -14), (-24, 13)):
        I("tree", x, y, rnd.uniform(0, 6), g="square", m=False)
    for x, y in ((-30, -2), (-50, 2)):
        I("bench", x, y, PI / 2 if x < -40 else -PI / 2, g="square", m=False)
    for k, x in enumerate(frange(-10, 100, 18)):
        sy = 1 if k % 2 else -1
        I("street_lantern", x, sy * 4.2, yf((0, -sy)), g="lights", m=False)
    for x, y in ((-26, 16), (-26, -16), (-56, 14), (-56, -14)):
        I("street_lantern", x, y, yf((0, -1 if y > 0 else 1)), g="lights", m=False)
    I("castle_hill", -40, 330, 0.0, 10.0, "backdrop", False)
    I("city_backdrop", 420, -20, yf((-1, 0)), 0.0, "backdrop", False)
    M("MARK_player_start", "player", 96, 0, yf((-1, 0)))
    M("MARK_exit_charles_bridge", "exit", 110, 0, yf((-1, 0)), leads_to="charles_bridge")
    M("MARK_exit_castle", "exit", -52, 41, yf((1, 0)), z=8.0, leads_to="castle")
    for i, (t, x, y, z) in enumerate((("alchemist", 0, 41, 8), ("alchemist", 62, 40, 8), ("skeleton", -40, 0, 0),
                                      ("skeleton", -37, 4, 0), ("skeleton", -43, -4, 0), ("golem", 72, 0, 0),
                                      ("skeleton", 14, 39, 8), ("alchemist", 40, 1, 0), ("skeleton", 90, 2, 0))):
        M(f"MARK_spawn_{t}_{i:02d}", "spawn", x, y, PI, z=z, enemy=t, time="night")
    for i, (x, y) in enumerate(((90, 1), (60, -1), (25, 1), (-10, -1), (-30, 6), (-50, -6), (-30, -8), (0, 1), (50, 1))):
        M(f"MARK_wander_{i:02d}", "wander", x, y)
    for i, (x, y) in enumerate(((-40, 40), (20, 41), (80, 40), (20, 41))):
        M(f"MARK_patrol_terrace_{i}", "patrol", x, y, z=8.0, route="terrace", index=i)
    return dict(display="Mala Strana", water=[], kill_z=-10.0, planes=[], map=dict(center=(10.0, -20.0), size=270.0),
                cams={"street": ((88.0, -2.0, 2.6), (-20.0, 10.0, 9.0), 72),
                      "stairs": ((62.0, -1.5, 2.6), (0.0, 14.0, 7.0), 74),
                      "terrace": ((70.0, 38.0, 10.4), (-30.0, 42.0, 12.0), 72),
                      "square": ((-18.0, -3.0, 2.4), (-62.0, 2.0, 14.0), 70)},
                concept="stairs")


# ============================================================================= Vysehrad
def level_vysehrad(rnd):
    dirt = {(-40, -24), (-40, -8), (-40, 8), (-24, -24), (-24, -8), (-24, 8)}
    for x in frange(-56, 56, 16):
        for y in frange(-56, 56, 16):
            I("ground_dirt" if (x, y) in dirt else "ground_grass", x, y, 0.0, g="ground", m=False)
    tiles("ground_dirt", frange(72, 120, 16), (0,), g="road")
    # curtain: crenellated parapets on the cliff (west, north-west), tall walls elsewhere, towers, gate
    for y in frange(-42, 42, 12):
        I("fortress_parapet", -60, y, yf((-1, 0)), g="walls")
    for x in (-50, -38, -26, -14, -2):
        I("fortress_parapet", x, 50, yf((0, 1)), g="walls")
    for x in (10, 22, 34, 46, 52):
        I("fortress_wall", x, 50, yf((0, 1)), g="walls")
    for x in frange(-50, 52, 12):
        I("fortress_wall", x, -50, 0.0, g="walls")
    for y in (-11, -23, -35, -47, 11, 23, 35, 47):
        I("fortress_wall", 60, y, yf((1, 0)), g="walls")
    for x, y in ((-60, 50), (60, 50), (60, -50), (-60, -50)):
        I("fortress_tower", x, y, 0.0, g="walls")
    I("gate_tower", 60, 0, yf((1, 0)), g="walls")
    for x in frange(70, 118, 12):                                       # walled approach lane outside the gate
        I("fortress_wall", x, 8.4, yf((0, 1)), g="road", m=False)
        I("fortress_wall", x, -8.4, 0.0, g="road", m=False)
    I("fortress_tower", 128, 0, 0.0, g="road")
    for x, sy in ((76, 1), (90, -1), (104, 1), (116, -1)):                 # lanterns along the approach lane
        I("street_lantern", x, sy * 4.8, yf((0, -sy)), g="lights", m=False)
    # the crag under the parapets, river far below
    for y in (-24, 24):
        I("cliff_rock_a" if y < 0 else "cliff_rock_b", -61, y, yf((-1, 0)), g="cliff", m=False)
    I("cliff_rock_b", -66, 58, yf((-0.7, 0.7)), g="cliff", m=False)
    for x in (-36, 10):
        I("cliff_rock_a", x, 51, yf((0, 1)), g="cliff", m=False)
    for x in (-36, 10, 46):
        I("cliff_rock_b" if x == 10 else "cliff_rock_a", x, -51, 0.0, g="cliff", m=False)
    I("cliff_rock_a", -66, -58, yf((-0.7, -0.7)), g="cliff", m=False)
    # churches and the cemetery
    I("rotunda", 6, 33, 0.0, g="church")
    I("basilica", 30, 10, 0.0, g="church")
    for k in range(24):
        x, y = rnd.uniform(-6, 18), rnd.uniform(16, 44)
        if (x - 6) ** 2 + (y - 33) ** 2 < 49 or (abs(x - 6) < 3 and y < 30):
            continue
        I(rnd.choice(["gravestone", "gravestone", "grave_cross"]), x, y, rnd.uniform(-0.2, 0.2), g="cemetery", m=False)
    for k in range(10):
        x, y = rnd.uniform(41, 54), rnd.uniform(14, 44)
        I(rnd.choice(["gravestone", "grave_cross"]), x, y, PI / 2 + rnd.uniform(-0.2, 0.2), g="cemetery", m=False)
    for x in (-4.0, 4.0, 12.0):
        I("garden_wall", x, 13.5, 0.0, g="cemetery", m=False)
    for x, y in ((-2, 46), (20, 46), (50, 44), (54, 18), (-52, 40), (46, -10), (-10, -42)):
        I("pine_tree", x, y, rnd.uniform(0, 6), g="trees", m=False)
    for x, y in ((24, -30), (-8, 6)):
        I("tree", x, y, rnd.uniform(0, 6), g="trees", m=False)
    # training ground: fence, dummies, targets, watchtower
    for y in frange(-30, 14, 4):
        if abs(y + 6) < 3:
            continue
        I("fence_wood", -13, y, PI / 2, g="training", m=False)
    for y in (-28, -18, -6):
        I("archery_target", -54, y, yf((1, 0)), g="training", m=False)
    for x, y in ((-40, -12), (-34, -18), (-44, 4), (-30, 6)):
        I("training_dummy", x, y, yf((1, 0)), g="training", m=False)
    I("weapon_rack", -24, 12, PI, g="training", m=False)
    I("watchtower_wood", -24, 22, 0.0, g="training", m=False)
    for x, y in ((-18, -32), (-17, -30.8)):
        I("barrel", x, y, rnd.uniform(0, 6), g="training", m=False)
    I("bench", -20, -24, -PI / 2, g="training", m=False)
    # canons' houses along the south wall (enterable), armourer and smithy
    BW.fill_row((40, -36), (0, 1), 46, rnd, "houses", pool=TIMBER, gothic=0.0)
    I("market_stall_weapons", 20, -18, 0.0, g="market")
    _, shed = I("blacksmith_shed", 44, -24, PI, g="market")
    for slot, asset in (("MARK_forge", "forge"), ("MARK_anvil", "anvil")):
        loc, yaw = shed[slot]
        I(asset, loc.x, loc.y, yaw + (PI if asset == "forge" else 0.0), g="market")
    for x, y in ((52, 8), (52, -8), (-10, 40)):
        I("flag_pole", x, y, rnd.uniform(-0.3, 0.3), g="flags")
    for x, y in ((40, 0), (16, 0), (-6, -8), (-6, 20), (30, -28), (0, -28)):
        I("street_lantern", x, y, rnd.uniform(0, 6), g="lights", m=False)
    # long views: Prague Castle on its hill, the Old Town and Charles Bridge far to the north
    I("castle_hill", -330, 560, 0.25, -40.0, "backdrop", False)
    I("city_backdrop", 140, 430, 0.0, -38.0, "backdrop", False)
    I("bridge_far", -190, 330, 0.0, -34.0, "backdrop", False)
    I("city_backdrop", -560, 250, yf((1, 0)), -36.0, "backdrop", False)
    M("MARK_player_start", "player", 100, 0, yf((-1, 0)))
    M("MARK_exit_old_town", "exit", 116, 0, yf((-1, 0)), leads_to="old_town")
    spawns = (("skeleton", 0, 22), ("skeleton", 4, 26), ("skeleton", -3, 28), ("skeleton", 46, 22), ("skeleton", 48, 30),
              ("skeleton", 45, 38), ("alchemist", 8, 24), ("alchemist", -32, 0), ("golem", -30, -14), ("alchemist", 30, -30),
              ("skeleton", -40, 30))
    for i, (t, x, y) in enumerate(spawns):
        M(f"MARK_spawn_{t}_{i:02d}", "spawn", x, y, PI, enemy=t, time="night")
    for i, (x, y) in enumerate(((50, 0), (10, -4), (-6, 10), (20, 30), (40, 30), (40, -10))):
        M(f"MARK_patrol_walls_{i}", "patrol", x, y, route="walls", index=i)
    for i, (x, y) in enumerate(((2, 18), (14, 22), (14, 42), (-2, 42), (-4, 24))):
        M(f"MARK_wander_{i:02d}", "wander", x, y)
    water = [{"height": -40.0, "rect": [-1600.0, -1200.0, -68.0, 1600.0]}]
    planes = [{"height": -38.5, "rect": [-68.0, -1200.0, 1600.0, 1600.0], "material": "grass"},
              {"height": -38.5, "rect": [-1600.0, 900.0, -68.0, 1600.0], "material": "grass"}]
    return dict(display="Vysehrad", water=water, kill_z=-22.0, planes=planes, map=dict(center=(30.0, 0.0), size=220.0),
                cams={"ramparts": ((-118.0, -78.0, 22.0), (-12.0, 14.0, -6.0), 64),
                      "training": ((-6.0, -20.0, 3.0), (-50.0, 0.0, 2.0), 70),
                      "view_north": ((-50.0, 30.0, 2.6), (-120.0, 300.0, -10.0), 66),
                      "gate": ((90.0, 0.0, 2.4), (50.0, 0.0, 8.0), 70)},
                concept="ramparts")


LEVELS = {"charles_bridge": level_charles_bridge, "mala_strana": level_mala_strana, "vysehrad": level_vysehrad}


# ============================================================================= Task 4: population
def populate(level, layout):
    by_name = {m["name"]: m for m in layout["markers"]}
    insts = {i["id"]: i for i in layout["instances"]}
    S = BS.spawn
    g = lambda p: BS.from_godot(p)  # noqa: E731
    rnd = random.Random(sum(ord(ch) * (i + 1) for i, ch in enumerate(level)))   # stable (hash() is salted per run)

    def mk(prefix):
        return [m for m in layout["markers"] if m["name"].startswith(prefix)]

    def route(prefix):
        return [m["name"] for m in sorted(mk(prefix), key=lambda m: m.get("index", 0))]

    for m in mk("MARK_spawn_"):
        t = m["enemy"]
        anim = {"alchemist": "cast", "skeleton": "idle", "golem": "idle"}[t]
        S(t, g(m["pos"]), math.radians(m["yaw_deg"]), anim, "night", f"enemy_{t}")
    # traders at the stalls of this level
    for i in layout["instances"]:
        if i["asset"].startswith("market_stall_"):
            kind = i["asset"].replace("market_stall_", "")
            mm = by_name.get(f"MARK_merchant@{i['id']}")
            cm = by_name.get(f"MARK_customer@{i['id']}")
            ch, an = BS.STALL_KEEPER[kind]
            if level == "vysehrad" and kind == "weapons":
                ch = "knight"
            if mm:
                S(ch, g(mm["pos"]), math.radians(mm["yaw_deg"]), an if ch != "knight" else "talk", "day", f"trader_{kind}",
                  extra={"stall": i["id"]})
            if cm and rnd.random() < 0.7:
                S(rnd.choice(["merchant", "market_woman"]), g(cm["pos"]), math.radians(cm["yaw_deg"]), "talk", "day", "customer",
                  extra={"stall": i["id"]})
    for m in mk("MARK_smith@"):
        if m.get("owner", "").startswith("anvil"):
            S("butcher", g(m["pos"]), math.radians(m["yaw_deg"]), "work", "day", "blacksmith")
    for m in mk("MARK_guard_post@"):
        S("guard", g(m["pos"]), math.radians(m["yaw_deg"]), "idle", "always", "npc_guard")
    wr = route("MARK_wander_")
    walkers = ["merchant", "market_woman", "child_boy", "monk", "market_woman", "merchant"]
    for k in range(min(5, len(wr))):
        ch = walkers[k % len(walkers)] if level != "vysehrad" else ["monk", "monk", "market_woman"][k % 3]
        r = wr[k:] + wr[:k]
        S(ch, g(by_name[r[0]]["pos"]), 0.0, "walk", "day", "wanderer", extra={"route": r})
    if level == "charles_bridge":
        S("guard", V((92, -6, 0)), yf((-1, 0)), "idle", "always", "npc_guard")
        S("guard", V((-92, 6, 0)), yf((1, 0)), "idle", "always", "npc_guard")
        pr = route("MARK_patrol_bridge_")
        S("guard", g(by_name[pr[0]]["pos"]), 0.0, "walk", "always", "patrol", extra={"route": pr, "speed_mps": 1.1})
        S("horse", V((126, 1.5, 0)), yf((-1, 0)), "pull", "day", "cart_driver",
          extra={"route_points": [[126.0, 0.0, -1.5], [100.0, 0.0, -1.5], [40.0, 0.0, -1.8], [-40.0, 0.0, -1.8], [-126.0, 0.0, -1.5]],
                 "speed_mps": 1.0, "pulls": "res://assets/props/cart.gltf", "cart_offset_m": 3.0})
        for (x, y, z, yaw) in ((28.0, -46.0, -5.88, 0.25 + PI / 2), (-32.0, 28.0, -5.88, 1.2 + PI / 2), (46.0, 74.0, -5.88, -0.4)):
            S("boatman", V((x, y, z)), yaw, "work", "day", "boatman", extra={"static": True})
        S("beggar", V((-24, -3.6, 0)), yf((0, 1)), "beg", "always", "npc_beggar")
        for k in range(8):
            x, y = rnd.uniform(90, 124), rnd.uniform(-14, 14)
            if abs(y) < 3 and x < 100:
                continue
            S(rnd.choice(["merchant", "market_woman", "child_girl", "butcher"]), V((x, y, 0)), rnd.uniform(0, 2 * PI), "talk", "day", "crowd")
        S("monk", V((-10, 2.4, 0)), yf((0, -1)), "pray", "day", "npc_monk")
    elif level == "mala_strana":
        im = by_name.get(next((n for n in by_name if n.startswith("MARK_innkeeper@")), ""), None)
        if im:
            S("market_woman", g(im["pos"]), math.radians(im["yaw_deg"]), "talk", "always", "innkeeper")
        for (x, y, yaw) in ((35.5, -1.4, PI), (44.5, -4.6, 0.0), (36.5, -4.6, 0.0), (43.5, -1.4, PI)):
            S(rnd.choice(["merchant", "butcher", "market_woman"]), V((x, y, 0)), yaw, "talk", "always", "patron")
        S("guard", V((16.5, 3.6, 0)), yf((0, -1)), "idle", "always", "npc_guard")
        S("guard", V((16.0, 37.0, 8.0)), yf((0, -1)), "idle", "always", "npc_guard")
        pr = route("MARK_patrol_terrace_")
        S("guard", g(by_name[pr[0]]["pos"]), 0.0, "walk", "always", "patrol", extra={"route": pr[:3], "speed_mps": 1.1})
        S("monk", V((-58.5, 0.0, 0)), yf((1, 0)), "pray", "day", "npc_monk")
        S("child_boy", V((-30, 4, 0)), 0.0, "run", "day", "npc_child_boy", extra={"route_points": [[-30.0, 0.0, -4.0], [-44.0, 0.0, -2.0], [-40.0, 0.0, 6.0]]})
        S("child_girl", V((-31, 2.5, 0)), 1.0, "idle", "day", "npc_child_girl")
        S("beggar", V((8.0, 4.0, 0)), yf((0, -1)), "beg", "always", "npc_beggar")
        S("horse", V((84, 2.0, 0)), yf((-1, 0)), "pull", "day", "cart_driver",
          extra={"route_points": [[84.0, 0.0, -2.0], [40.0, 0.0, 1.0], [-10.0, 0.0, 1.0]], "speed_mps": 1.0,
                 "pulls": "res://assets/props/cart.gltf", "cart_offset_m": 3.0})
        for k in range(6):
            x, y = rnd.uniform(-55, -25), rnd.uniform(-14, 14)
            S(rnd.choice(["merchant", "market_woman", "butcher"]), V((x, y, 0)), rnd.uniform(0, 2 * PI), "talk", "day", "crowd")
    elif level == "vysehrad":
        for (x, y) in ((-40, -6), (-32, -24), (-46, 10)):                    # sparring pairs
            S("knight", V((x - 1.2, y, 0)), yf((1, 0)), "spar", "day", "knight_spar")
            S("knight", V((x + 1.2, y, 0)), yf((-1, 0)), "spar", "day", "knight_spar", offset=30)
        S("knight", V((-48, -20, 0)), yf((-1, 0)), "idle", "day", "knight")
        S("knight", V((-24.5, 19.0, 0)), yf((0, -1)), "talk", "day", "knight_captain")
        S("guard", V((53, 4.5, 0)), yf((1, 0)), "idle", "always", "npc_guard")
        S("guard", V((53, -4.5, 0)), yf((1, 0)), "idle", "always", "npc_guard")
        S("knight", V((70, 5, 0)), yf((0, -1)), "idle", "always", "npc_knight_gate")
        pr = route("MARK_patrol_walls_")
        S("guard", g(by_name[pr[0]]["pos"]), 0.0, "walk", "always", "patrol", extra={"route": pr, "speed_mps": 1.1})
        S("monk", V((6, 26.5, 0)), yf((0, -1)), "pray", "day", "npc_monk")
        S("monk", V((30, 8.5, 0)), yf((0, -1)), "talk", "day", "npc_monk")
        S("monk", V((16, 30, 0)), yf((-1, 0)), "pray", "always", "npc_monk")
        S("child_boy", V((10, -10, 0)), 0.0, "run", "day", "npc_child_boy", extra={"route_points": [[10.0, 0.0, 10.0], [-6.0, 0.0, 4.0], [4.0, 0.0, -6.0]]})
        S("market_woman", V((12, -8, 0)), 2.0, "talk", "day", "npc_market_woman")


def fx_level(level, layout):
    BS.FX.clear()
    for i in layout["instances"]:
        p = BS.from_godot(i["pos"])
        if i["asset"] == "forge":
            BS.smoke("forge", p + V((0, 0, 3.6)), height=7.0, size=0.4)
    for o in bpy.data.objects:
        if o.name.startswith("ANIM_banner") and not any(f["type"] == "sway" for f in BS.FX):
            BS.FX.append({"type": "sway", "node": "ANIM_banner", "amplitude_deg": 5.0, "period_s": 5.0})
    if level == "charles_bridge":
        BS.FX.append({"type": "river", "note": "Vltava water planes from layout.water; boats bob on the swell"})
    if level == "mala_strana":
        BS.smoke("tavern_chimney", V((44.0, -16.0, 16.5)), n=4, height=8.0, size=0.4)
        BS.FX.append({"type": "smoke", "pos": [44.0, 16.5, 16.0]})
    for i in layout["instances"]:
        if i["asset"] == "forge":
            q = i["pos"]
            BS.FX.append({"type": "smoke", "pos": [q[0], q[1] + 3.6, q[2]]})


# ============================================================================= renders
def water_planes(info):
    for k, w in enumerate(info["water"]):
        x0, z0, x1, z1 = w["rect"]
        mb = G.MB()
        mb.box((x0, -z1, w["height"] - 0.2), (x1, -z0, w["height"]), "M_Water")
        mb.build(f"water_{k}")
    for k, p in enumerate(info["planes"]):
        x0, z0, x1, z1 = p["rect"]
        mb = G.MB()
        mb.box((x0, -z1, p["height"] - 0.2), (x1, -z0, p["height"]), "M_Grass")
        mb.build(f"far_ground_{k}")


def render_set(level, info, out_dir, prefix, compare=True):
    import numpy as np
    os.makedirs(out_dir, exist_ok=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    try:
        sc.eevee.taa_render_samples = 24
        sc.view_settings.view_transform = "Standard"
    except Exception:
        pass
    for o in bpy.data.objects:
        if o.name.endswith("-colonly"):
            o.hide_render = True
    for name, (loc, look, fov) in info["cams"].items():
        sc.camera = BW.camera(f"{level}_{name}", loc, look, fov)
        for tag, fr in (("day", BW.FRAME_DAY), ("night", BW.FRAME_NIGHT)):
            sc.frame_set(fr)
            sc.render.filepath = os.path.join(out_dir, f"{prefix}{level}_{name}_{tag}.png")
            bpy.ops.render.render(write_still=True)
            print("RENDERED", sc.render.filepath)
    if compare:
        for tag in ("day", "night"):
            imgs = []
            for p in (os.path.join(G.PROJECT, "concept", "locations", f"{level}_{tag}.png"),
                      os.path.join(out_dir, f"{prefix}{level}_{info['concept']}_{tag}.png")):
                im = bpy.data.images.load(p)
                w, h = im.size
                px = np.array(im.pixels[:], np.float32).reshape(h, w, 4)
                imgs.append(px[(np.arange(450) * h / 450).astype(int)][:, (np.arange(800) * w / 800).astype(int)])
                bpy.data.images.remove(im)
            sheet = np.concatenate(imgs, axis=1)
            o = bpy.data.images.new("cmp", sheet.shape[1], sheet.shape[0], alpha=True)
            o.pixels.foreach_set(sheet.ravel())
            o.filepath_raw = os.path.join(out_dir, f"{prefix}{level}_compare_{tag}.png")
            o.file_format = "PNG"
            o.save()
            bpy.data.images.remove(o)


def render_plan(level, info):
    """Top-down map for the in-game Map tab (assets/ui/map_<level>.png); Godot centre/size go into layout.map."""
    sc = bpy.context.scene
    cx, cz = info["map"]["center"]
    size = info["map"]["size"]
    hide = [o for o in bpy.data.objects if o.name.startswith(("castle_hill", "city_backdrop", "bridge_far", "st_nicholas#"))
            and o.instance_type == "COLLECTION"]
    hide += [o for o in bpy.data.objects if o.instance_type == "COLLECTION" and o.instance_collection and
             o.instance_collection.name in ("castle_hill", "city_backdrop", "bridge_far")]
    for o in hide:
        o.hide_render = True
    sc.camera = BW.camera(f"{level}_plan", (cx, -cz, 300.0), (cx, -cz + 0.01, 0.0), 50, ortho=size)
    sc.render.resolution_x = sc.render.resolution_y = 1200
    sc.frame_set(BW.FRAME_DAY)
    out = os.path.join(G.PROJECT, "renders", "world", f"{level}_plan.png")
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    shutil.copy(out, os.path.join(G.PROJECT, "assets", "ui", f"map_{level}.png"))
    for o in hide:
        o.hide_render = False
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900


# ============================================================================= main
def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    level = argv[argv.index("--level") + 1]
    render = "--no-render" not in argv
    if "--rerender" in argv:          # re-render some cameras of the saved world / scene files (no rebuild)
        cams = argv[argv.index("--rerender") + 1].split(",")
        rnd = random.Random(0)
        G.reset_scene()
        append_all()
        BW.WORLD_COL = bpy.data.collections.new("World")
        BW.MARK_COL = bpy.data.collections.new("Markers")
        info = LEVELS[level](rnd)
        info["cams"] = {k: v for k, v in info["cams"].items() if k in cams}
        for kind in ("world", "scene"):
            bpy.ops.wm.open_mainfile(filepath=os.path.join(G.BLENDER_DIR, f"{kind}_{level}.blend"))
            render_set(level, info, os.path.join(G.PROJECT, "renders", kind), "", compare=info["concept"] in cams)
        print("DONE rerender", level)
        return
    G.reset_scene()
    append_all()
    BW.WORLD_COL = bpy.data.collections.new("World")
    bpy.context.scene.collection.children.link(BW.WORLD_COL)
    BW.MARK_COL = bpy.data.collections.new("Markers")
    bpy.context.scene.collection.children.link(BW.MARK_COL)
    rnd = random.Random({"charles_bridge": 1357, "mala_strana": 1257, "vysehrad": 1070}[level])
    info = LEVELS[level](rnd)
    BW.setup_lighting()
    water_planes(info)
    xs = [m["pos"][0] for m in BW.LAYOUT if m["group"] not in ("ground", "backdrop")]
    zs = [m["pos"][2] for m in BW.LAYOUT if m["group"] not in ("ground", "backdrop")]
    data = {
        "level": level, "display": info["display"], "version": 1,
        "coordinate_system": "Godot: +Y up, -Z = north on the plan (Blender +Y). Characters/house fronts face local +Z.",
        "bounds": {"x": [min(xs) - 10, max(xs) + 10], "z": [min(zs) - 10, max(zs) + 10]},
        "water": info["water"], "planes": info["planes"], "kill_y": info["kill_z"],
        "map": {"center": list(info["map"]["center"]), "size": info["map"]["size"], "image": f"res://assets/ui/map_{level}.png"},
        "instances": BW.LAYOUT, "markers": BW.MARKERS, "lighting": BW.lighting_presets(),
    }
    out_json = os.path.join(G.PROJECT, "assets", "levels", f"{level}_layout.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    kinds = {}
    for m in BW.MARKERS:
        kinds[m["kind"]] = kinds.get(m["kind"], 0) + 1
    print("INSTANCES", len(BW.LAYOUT), "MARKERS", len(BW.MARKERS), json.dumps(kinds))
    bpy.context.scene.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(G.BLENDER_DIR, f"world_{level}.blend"))
    if render:
        render_plan(level, info)
        render_set(level, info, os.path.join(G.PROJECT, "renders", "world"), "", compare=True)
    # ---------------- Task 4
    BS.load_characters()
    for c in BS.CHARS.values():
        for o in c.all_objects:
            if o.type == "ARMATURE" and o.animation_data:
                for t in o.animation_data.nla_tracks:
                    t.mute = True
    populate(level, data)
    fx_level(level, data)
    counts = {}
    for p in BS.POP:
        key = f"{p['schedule']}:{p['character']}"
        counts[key] = counts.get(key, 0) + 1
    pop = {"level": level, "version": 1,
           "coordinate_system": f"Godot coordinates (same as {level}_layout.json). Characters face local +Z.",
           "schedule": {"day": "visible/active by day", "night": "spawned at dusk (enemies)", "always": "day and night"},
           "population": BS.POP, "fx": BS.FX, "counts": counts}
    with open(os.path.join(G.PROJECT, "assets", "levels", f"{level}_population.json"), "w", encoding="utf-8") as f:
        json.dump(pop, f, ensure_ascii=False, indent=1)
    print("POPULATION", len(BS.POP), json.dumps(counts))
    bpy.context.scene.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(G.BLENDER_DIR, f"scene_{level}.blend"))
    if render:
        render_set(level, info, os.path.join(G.PROJECT, "renders", "scene"), "", compare=True)
    print("DONE", level)


if __name__ == "__main__":
    main()
