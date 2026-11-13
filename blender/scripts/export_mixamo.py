"""Export a character as an unrigged, single-mesh FBX (embedded textures) for Mixamo auto-rigging.

blender -b --factory-startup -P export_mixamo.py -- vaclav [--keep-weapons]
Output: build/mixamo/<name>_mixamo.fbx + <name>_mixamo_front.png preview of the rest pose.
"""
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, "..", ".."))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
name = argv[0] if argv else "vaclav"
keep_weapons = "--keep-weapons" in argv
out_dir = os.path.join(PROJECT, "build", "mixamo")
os.makedirs(out_dir, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(PROJECT, "assets", "characters", f"{name}.gltf"))

# The glTF importer adds an unlinked "Icosphere" as the bone display shape; skip anything not in the scene.
shapes = {pb.custom_shape for a in bpy.data.objects if a.type == "ARMATURE" for pb in a.pose.bones if pb.custom_shape}
for ob in shapes:
    bpy.data.objects.remove(ob, do_unlink=True)

# Raise the arms into an A-pose (the game rig rests with arms nearly at the sides, which makes Mixamo's
# auto-rig bleed arm weights into the torso), then bake that pose into the mesh.
from mathutils import Matrix, Vector
A_POSE_DEG = 40.0
for arm in [o for o in bpy.data.objects if o.type == "ARMATURE"]:
    to_arm = arm.matrix_world.inverted().to_3x3()
    for side, sign in (("L", -1.0), ("R", 1.0)):
        pb = arm.pose.bones.get(f"upper_arm.{side}")
        if not pb:
            continue
        axis = (to_arm @ Vector((0, 1, 0))).normalized()
        head = pb.matrix.to_translation()
        rot = Matrix.Rotation(sign * math.radians(A_POSE_DEG), 4, axis)
        pb.matrix = Matrix.Translation(head) @ rot @ Matrix.Translation(-head) @ pb.matrix
        bpy.context.view_layer.update()
for ob in [o for o in bpy.data.objects if o.type == "MESH"]:
    for m in [m for m in ob.modifiers if m.type == "ARMATURE"]:
        with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob]):
            bpy.ops.object.modifier_apply(modifier=m.name)
world = {ob.name: ob.matrix_world.copy() for ob in bpy.data.objects}

# Drop the rig: Mixamo auto-rigs a bare mesh; a foreign skeleton makes it reject or mis-map the upload.
for ob in list(bpy.data.objects):
    if ob.type == "ARMATURE":
        bpy.data.objects.remove(ob, do_unlink=True)
meshes = []
for ob in list(bpy.data.objects):
    if ob.type != "MESH":
        if ob.type != "EMPTY":
            bpy.data.objects.remove(ob, do_unlink=True)
        continue
    if ob.name.startswith("WEAPON_") and not keep_weapons:
        bpy.data.objects.remove(ob, do_unlink=True)
        continue
    for m in list(ob.modifiers):
        ob.modifiers.remove(m)
    ob.vertex_groups.clear()
    meshes.append(ob)

# Bake parent transforms, then one mesh object.
for ob in meshes:
    ob.parent = None
    ob.matrix_world = world[ob.name]
for ob in list(bpy.data.objects):
    if ob.type == "EMPTY":
        bpy.data.objects.remove(ob, do_unlink=True)
bpy.ops.object.select_all(action="DESELECT")
for ob in meshes:
    ob.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.join()
body = bpy.context.view_layer.objects.active
body.name = name
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
dims = body.dimensions
print(f"[mixamo] {name}: verts={len(body.data.vertices)} tris~{sum(len(p.vertices)-2 for p in body.data.polygons)} "
      f"size={dims.x:.2f}x{dims.y:.2f}x{dims.z:.2f} m, materials={len(body.data.materials)}")

fbx = os.path.join(out_dir, f"{name}_mixamo.fbx")
bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, object_types={"MESH"}, apply_unit_scale=True,
                         apply_scale_options="FBX_SCALE_ALL", path_mode="COPY", embed_textures=True,
                         mesh_smooth_type="FACE", add_leaf_bones=False, bake_anim=False)
print(f"[mixamo] wrote {fbx} ({os.path.getsize(fbx)/1e6:.1f} MB)")

# Front preview so the rest pose (T / A) can be checked before uploading.
import math
from mathutils import Vector
scn = bpy.context.scene
scn.render.engine = "BLENDER_WORKBENCH"
scn.display.shading.color_type = "TEXTURE"
scn.render.resolution_x, scn.render.resolution_y = 900, 900
cam_data = bpy.data.cameras.new("cam"); cam_data.type = "ORTHO"
cam = bpy.data.objects.new("cam", cam_data); scn.collection.objects.link(cam); scn.camera = cam
bb = [body.matrix_world @ Vector(c) for c in body.bound_box]
ctr = sum(bb, Vector()) / 8
cam_data.ortho_scale = max(dims.x, dims.z) * 1.15
cam.location = (ctr.x, ctr.y - 10, ctr.z)
cam.rotation_euler = (math.radians(90), 0, 0)
scn.render.filepath = os.path.join(out_dir, f"{name}_mixamo_front.png")
bpy.ops.render.render(write_still=True)
