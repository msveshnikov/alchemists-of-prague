"""Preview rendering of assets (EEVEE, day / night)."""
import math
import os

import bpy
from mathutils import Vector

import lib_geo as G

PREVIEW_DIR = os.path.join(G.PROJECT, "renders", "previews")


def _world(color, strength):
    w = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (*color, 1)
    bg.inputs["Strength"].default_value = strength


def _get(name, kind):
    ob = bpy.data.objects.get(name)
    if ob:
        return ob
    if kind == "SUN":
        ld = bpy.data.lights.new(name, "SUN")
    else:
        ld = bpy.data.cameras.new(name)
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def _ground():
    ob = bpy.data.objects.get("_preview_ground")
    if ob:
        return ob
    mb = G.MB()
    mb.box((-60, -60, -0.2), (60, 60, 0.0), "M_Cobble")
    ob = mb.build("_preview_ground")
    return ob


def setup_scene():
    sc = bpy.context.scene
    try:
        sc.render.engine = "BLENDER_EEVEE"
    except TypeError as e:
        print("engine", e)
    sc.render.resolution_x = 960
    sc.render.resolution_y = 720
    sc.render.film_transparent = False
    try:
        sc.eevee.taa_render_samples = 48
    except Exception:
        pass
    try:
        sc.view_settings.view_transform = "Standard"
        sc.view_settings.look = "None"
    except Exception:
        pass
    _ground()


def bounds(root):
    pts = []
    for o in G.descendants(root):
        if o.type == "MESH" and not o.name.endswith("-colonly") and not o.hide_render:
            pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def render_asset(root, night=False, suffix="", view=(0.55, -1.0, 0.3), fov=35.0, out_name=None):
    setup_scene()
    sc = bpy.context.scene
    vl = bpy.context.view_layer
    keep = root.users_collection[0].name
    for c in vl.layer_collection.children:
        c.exclude = c.name != keep
    for o in G.descendants(root):
        if o.name.endswith("-colonly"):
            o.hide_render = True
    sun = _get("_preview_sun", "SUN")
    cam = _get("_preview_cam", "CAM")
    sc.camera = cam
    cam.data.lens_unit = "FOV"
    cam.data.angle = math.radians(fov)
    cam.data.clip_end = 2000
    mn, mx = bounds(root)
    c = (mn + mx) / 2
    rad = (mx - mn).length / 2
    d = Vector(view).normalized()
    vfov = 2 * math.atan(math.tan(math.radians(fov) / 2) * 0.75)   # 4:3 frame: vertical is the tight one
    dist = rad / math.sin(vfov / 2) * 1.02
    cam.location = c + d * dist
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    if night:
        _world((0.012, 0.018, 0.045), 1.0)
        sun.data.energy = 0.25
        sun.data.color = (0.55, 0.65, 1.0)
        sun.rotation_euler = (math.radians(50), 0, math.radians(-140))
        G.set_night_emission(True)
        for o in bpy.data.objects:
            if o.type == "LIGHT" and o.name.startswith("LIGHT_"):
                o.hide_render = False
    else:
        _world((0.55, 0.65, 0.8), 0.9)
        sun.data.energy = 4.0
        sun.data.color = (1.0, 0.9, 0.75)
        sun.data.angle = math.radians(2)
        sun.rotation_euler = (math.radians(48), 0, math.radians(-35))
        G.set_night_emission(False)
        for o in bpy.data.objects:
            if o.type == "LIGHT" and o.name.startswith("LIGHT_"):
                o.hide_render = True
    os.makedirs(PREVIEW_DIR, exist_ok=True)
    name = out_name or (root.name + ("_night" if night else "") + suffix)
    sc.render.filepath = os.path.join(PREVIEW_DIR, name + ".png")
    bpy.ops.render.render(write_still=True)
    for c in vl.layer_collection.children:
        c.exclude = False
    print("RENDERED", sc.render.filepath)
    return sc.render.filepath
