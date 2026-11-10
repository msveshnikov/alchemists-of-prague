"""Run 2, Task 1: environment assets for Charles Bridge, Mala Strana and Vysehrad (+ distant backdrops).

blender -b --factory-startup -P build_locations.py [-- --only bridge_span,tavern] [--no-render]
Outputs: blender/locations.blend, assets/architecture/*.gltf, assets/props/*.gltf, renders/previews/*.png
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402

import lib_geo as G  # noqa: E402
import loc_common as LC  # noqa: E402
import loc_bridge  # noqa: E402
import loc_mala  # noqa: E402
import loc_vysehrad  # noqa: E402

NIGHT = {"bridge_tower", "tavern", "castle_stairs", "gate_tower", "retaining_wall_niche"}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only = argv[argv.index("--only") + 1].split(",") if "--only" in argv else None
    render = "--no-render" not in argv
    G.reset_scene()
    builders = {}
    builders.update(loc_bridge.BUILDERS)
    builders.update(loc_mala.BUILDERS)
    builders.update(loc_vysehrad.BUILDERS)
    builders["ground_grass"] = lambda: LC.ground_tile("ground_grass", "M_Grass")
    builders["ground_dirt"] = lambda: LC.ground_tile("ground_dirt", "M_Dirt")
    roots = []
    for name, fn in builders.items():
        if only and name not in only:
            continue
        print("BUILD", name)
        roots.append(fn())
    for r in roots:
        cat = r.get("asset_category", "props")
        G.export_asset(r, os.path.join(G.PROJECT, "assets", cat))
    if render:
        import lib_render as R
        for r in roots:
            R.render_asset(r)
            if r.name in NIGHT:
                R.render_asset(r, night=True)
        for n in ("_preview_ground", "_preview_cam", "_preview_sun"):
            ob = bpy.data.objects.get(n)
            if ob:
                bpy.data.objects.remove(ob)
    if not only:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(G.BLENDER_DIR, "locations.blend"))
    print("DONE locations", len(roots))


if __name__ == "__main__":
    main()
