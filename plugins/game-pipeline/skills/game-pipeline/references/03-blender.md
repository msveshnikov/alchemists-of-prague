# 03 — Blender: everything from Python

Blender runs headless: `blender -b --factory-startup -P <script>.py -- <args>` from `blender/scripts/`.
No manual edits in the UI, ever: a fix is a code change plus a re-run. Each builder saves a `.blend`
library (for later scripts) AND exports glTF (for Godot) AND renders previews (for you to look at).

## Script layout (proven split)

| Script | Role |
|---|---|
| `lib_geo.py` | mesh builders (boxes, prisms, lofts, arches, roofs), world-scale planar UVs, glTF export helpers |
| `lib_tex.py` (+ `lib_tex2.py`, `lib_tex_char.py`) | numpy-painted tileable textures + normal maps from height |
| `lib_heraldry.py` etc. | emblems / decals drawn by code |
| `lib_render.py` | preview cameras, lights, day/night emission switch, contact sheets |
| `lib_char.py`, `lib_gait.py` | character bodies, skeleton, skinning, poses, procedural walk/run with IK |
| `make_textures.py`, `make_char_textures.py` | write textures to `assets/textures/` |
| `build_architecture.py`, `build_props.py` | Task 1 assets → `blender/*.blend` + `assets/architecture|props/*.gltf` + previews |
| `build_characters.py` | Task 2 → `characters.blend` + `assets/characters/*.gltf` |
| `build_world.py` | Task 3 → level `.blend` + `assets/levels/<level>_layout.json` + day/night renders |
| `build_scene.py` | Task 4 → population + effects + `<level>_population.json` |
| `build_<location>.py` / `build_world_ext.py` | run 2 districts |
| `build_<world>.py` | stitched world, top-down plan render for the map |
| `make_ui_assets.py` | UI frames, buttons, item icons |
| `sheet.py` | contact sheet of many renders: `blender -b -P sheet.py -- out.png 400 4 a.png b.png ...` |
| `style_check.py` | one scene with assets side by side, day and night, to judge consistency |

Give long builders `--no-render` and `--only name1,name2` flags: full preview renders can take 10+ min.
Document the exact rebuild order in README ("textures → architecture/props → characters → districts → world").

## Conventions (write them into decisions.md in Task 1, obey them everywhere)

- 1 unit = 1 m. Blender Z up → glTF/Godot Y up.
- **Front faces Blender −Y = Godot +Z** for buildings, props, characters AND markers (a marker faces
  where the character standing on it faces). Pivot = centre of the base on the ground.
- Node-name prefixes the game code relies on:
  - `INT_door_*` door leaves, pivot on the hinge; `INT_window_*` defenestration windows with
    `*_shutter_L/R`; `INT_stall_*` merchant stalls; `INT_anvil`; chests etc.
  - `MARK_*` empties: `MARK_door` (outside), `MARK_interior`, `MARK_window_N` (where a thrown body
    lands), `MARK_merchant`, `MARK_customer`, `MARK_cook`, `MARK_smith`, `MARK_horse`, `MARK_mount`...
  - `ANIM_*` simple looped motions (spit rotation, banner sway, wheels).
  - `LIGHT_*` point lights (KHR_lights_punctual).
  - `*-colonly` simplified collision meshes → Godot makes StaticBody3D automatically.
  - characters: `<name>_body`, `<name>_rig`, `WEAPON_*`, `HELD_*`.
- Duplicate names inside one .blend get `.001`: rename temporarily during export so glTF names are clean.
- Wall-mounted props: pivot on the wall plane at ground level, mount height fixed (torch 2.2 m, banner 4.2 m).

## Assets

- **Real openings** for doors and windows (the wall is built around them) so entering and
  defenestration are visible; a small vestibule behind every front door. Far windows can be decals.
- **Textures painted with numpy**: tileable, baked seam shading in the look of early-2000s hand-painted
  textures, normal maps from height. Palette = style block.
- **World-scale planar UVs** per face → identical texel density on every asset; a `fit` mode for decals
  (clock faces, shields, banners).
- **Export glTF Separate** (`.gltf` + `.bin`) with textures shared in `assets/textures/` — `.glb`
  would duplicate the same textures into every file (25 MB per house instead of a shared 28 MB set).
- **Lights**: export RAW with a 1/30 multiplier (a 70 W Blender torch → energy ≈ 2.3 in Godot);
  the default SPEC mode gives energies in the thousands.
- **Night emission**: lit-window and lantern-glass materials carry emissive textures; the game turns
  emission off by day. Fire and coals glow always.
- Variety by parameters: e.g. 6 burgher house variants (colour, width, floors, gable type, arcades).

## Characters

- One shared humanoid skeleton (≈20 bones, same names) for all humans and humanoid monsters; animals
  get their own.
- Bodies from **lofts**: elliptical tubes along bones, so limbs and torso have no seams. Clothes are
  separate shells (surcoat, robe skirts, hoods).
- **Skinning by code**: weight = 1/d^k to the allowed bones of each body part (≤3 bones per vertex).
  Blender's automatic heat weights are unreliable on non-intersecting shells.
- **Poses** as rotations about world axes in rest pose, converted to bone-local quaternions (bone roll
  doesn't matter). Animations are procedural functions (sine gait with knee lift, pelvis sway) and key
  poses with smoothstep; later a foot-planted IK gait (`lib_gait.py`) removed foot sliding.
- Held items are modelled in the character's base pose and moved into rest pose via the bone matrix,
  so the sword sits in the fist.
- **Each animation is a separate NLA track** → separate glTF animation with a short name; 24 fps.
  No root motion: store in `characters_list.md` the walk/run speed at which feet don't slide, and let
  Godot scale playback speed to the actual movement speed.
- Standard set: humans `idle, walk, run, hit, death, flail`; fighters `attack`; hero `block, throw,
  sprint, roll, backstep, jump`; townsfolk `talk`/`work`; animals `idle, walk, pull`.
- Blender may crash on exit after big builds (`EXCEPTION_ACCESS_VIOLATION`): harmless if everything
  was saved/exported first — print a `DONE` line before exit and check for it.

## Levels (Task 3–4)

- Plan from the world map but **follow the location concept art** when they disagree; compress distances.
- Place instances of library collections, plus markers, districts, lighting presets (day/night key
  values, fog, sky), and write `*_layout.json`: `instances` (asset, glTF path, group, pos, rot), `markers`
  (kind, pos, yaw, owner), `districts` (name, rect, offset, fog), `water`, `blockers`, `kill_y`, `map`.
- Population JSON: character, marker, facing, `schedule` (`day`/`night`/`always`), behaviour, plus `fx`
  entries (smoke, fire) for Godot particles.
- Render each location day and night from the same cameras as the concept art and compare side by side.
- For the stitched world: a reachability probe (walk a grid in Godot, render reachable cells) helps
  seal holes in the border; a top-down **orthographic plan render** is the basis of the in-game map.
