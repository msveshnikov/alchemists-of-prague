"""Style check: re-import the exported glTFs and arrange a rough Old Town Square vignette
from the concept-art camera angle, render day + night for comparison with
concept/locations/old_town_square_{day,night}.png.  (Not the Task 3 level layout.)

blender -b --factory-startup -P style_check.py
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import lib_geo as G  # noqa: E402

A = os.path.join(G.PROJECT, "assets")
PI = math.pi


def place(asset, loc, rot=0.0, cat="props"):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(A, cat, asset + ".gltf"))
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        if o.name.endswith("-colonly") or "-colonly" in o.name:
            o.hide_render = True
        if o.type == "LIGHT":
            o.data.energy /= G.GODOT_LIGHT_SCALE
    roots = [o for o in new if o.parent is None]
    for r in roots:
        r.location = Vector(loc) + r.location
        r.rotation_mode = "XYZ"
        r.rotation_euler.z += rot
    return roots


def main():
    G.reset_scene()
    sc = bpy.context.scene
    # ground
    for x in range(-3, 4):
        for y in range(-3, 6):
            place("ground_cobble", (x * 16, y * 16, 0), cat="architecture")
    # background row facing the camera, Tyn church behind it
    xs = -24.0
    for i, h in enumerate(["house_burgher_d", "house_burgher_b", "house_burgher_e", "house_burgher_a", "house_burgher_c",
                           "house_burgher_f", "house_burgher_b"]):
        w = {"a": 7.0, "b": 6.5, "c": 7.5, "d": 8.5, "e": 6.0, "f": 9.0}[h[-1]]
        place(h, (xs + w / 2, 46, 0), 0, "architecture")
        xs += w
    place("tyn_church", (2, 100, 0), 0, "architecture")
    # right row facing west (toward the square)
    ys = 38.0
    for h in ["house_burgher_a", "house_burgher_f", "house_burgher_b", "house_burgher_c", "house_burgher_d", "house_burgher_a",
              "house_burgher_e"]:
        w = {"a": 7.0, "b": 6.5, "c": 7.5, "d": 8.5, "e": 6.0, "f": 9.0}[h[-1]]
        place(h, (22, ys - w / 2, 0), -PI / 2, "architecture")
        ys -= w
    # left: town hall facing east, gothic tower house further back
    place("old_town_hall", (-20, 6, 0), PI / 2, "architecture")
    place("house_gothic_tower", (-21, 30, 0), PI / 2, "architecture")
    place("marian_column", (-1, 34, 0), 0, "architecture")
    # market
    place("spit_roast", (-11, -6, 0), 0.3)
    place("market_stall_meat", (-13, -1, 0), PI / 2 + 0.1)
    place("market_stall_bread", (-4, 4, 0), 0.0)
    place("market_stall_produce", (1, 12, 0), 0.1)
    place("market_stall_pottery", (-7, 16, 0), 0.4)
    place("market_stall_cloth", (6, 24, 0), -0.2)
    place("market_stall_weapons", (11, 3, 0), -0.6)
    place("blacksmith_shed", (14, -9, 0), -PI / 2 + 0.3)
    place("forge", (14.8, -8.6, 0), -PI / 2 + 0.3)
    place("anvil", (12.6, -10.2, 0), 0.4)
    place("cart", (8, 13, 0), -2.4)
    for p, l in (("barrel", (-14, -9)), ("barrel", (-13.2, -9.6)), ("barrel_small", (-12.5, -8.8)), ("crate", (-3, 0.5)),
                 ("sack", (-2.4, 1.2)), ("crate_produce", (2.5, 9.5)), ("basket", (0, 9.6)), ("bench", (-8, 9)),
                 ("weapon_rack", (12.5, 6.5)), ("table", (-6, -5)), ("stool", (-6.8, -4.6)), ("cooking_pot", (4, -4))):
        place(p, (*l, 0), 0.5)
    for t in ((-12, 22), (13, 30), (-14, 40)):
        place("tree", (*t, 0), 0)
    for l in ((-9, 6), (9, 8), (-4, 26), (7, -8)):
        place("street_lantern", (*l, 0), 0)
    # camera like the concept art: low three-quarter view toward Tyn church
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.location = (1.5, -27, 9)
    cam.rotation_euler = (math.radians(85), 0, 0)
    cam.data.lens_unit = "FOV"
    cam.data.angle = math.radians(72)
    cam.data.clip_end = 1000
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sc.collection.objects.link(sun)
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    try:
        sc.eevee.taa_render_samples = 64
        sc.view_settings.view_transform = "Standard"
    except Exception:
        pass
    w = bpy.data.worlds.new("w")
    sc.world = w
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    out = os.path.join(G.PROJECT, "renders")
    lights = [o for o in bpy.data.objects if o.type == "LIGHT" and o.name.startswith("LIGHT_")]
    glow = [m for m in bpy.data.materials if m.name.startswith(("M_WindowLit", "M_LanternGlass"))]

    def emission(on):
        for m in glow:
            b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            b.inputs["Emission Strength"].default_value = 1.5 if on else 0.0

    # day
    bg.inputs["Color"].default_value = (0.5, 0.62, 0.82, 1)
    bg.inputs["Strength"].default_value = 1.0
    sun.data.energy, sun.data.color, sun.data.angle = 4.5, (1.0, 0.88, 0.7), math.radians(2)
    sun.rotation_euler = (math.radians(55), 0, math.radians(-150))
    for o in lights:
        o.hide_render = True
    emission(False)
    sc.render.filepath = os.path.join(out, "style_check_day.png")
    bpy.ops.render.render(write_still=True)
    # night
    bg.inputs["Color"].default_value = (0.01, 0.016, 0.045, 1)
    sun.data.energy, sun.data.color = 0.3, (0.5, 0.62, 1.0)
    for o in lights:
        o.hide_render = False
    emission(True)
    sc.render.filepath = os.path.join(out, "style_check_night.png")
    bpy.ops.render.render(write_still=True)
    print("STYLE CHECK DONE")


main()
