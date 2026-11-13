# 04 — Godot 4: the game

The Godot project lives in the repo root; Blender output is used in place (`res://assets/...`).

## Architecture

- **The level is built at runtime from JSON** (`world.gd` reads `*_layout.json` and
  `*_population.json`): instances glTF scenes, wires `INT_*`/`MARK_*` nodes to gameplay, spawns NPCs by
  schedule. A rebuilt level in Blender appears in the game with no scene editing. Show a loading screen.
- Scripts (all GDScript):

| Script | Role |
|---|---|
| `game.gd` (autoload) | state, item table, save/load, settings, input map built in code |
| `sfx.gd` (autoload) | sounds, music, ambience by time of day |
| `world.gd` | level build, day/night schedule, houses & interiors, defenestration, UI flow, debug flags |
| `day_night.gd` | sun/moon/sky/fog from the Task 3 lighting keys; lamps and lit windows at night |
| `player.gd`, `enemy.gd`, `npc.gd` | hero controller & combat, enemy AI per type, townsfolk |
| `ui/ui_kit.gd` + `ui/*.gd` | UI built in code from one kit |
| `ui/touch_controls.gd` | phone controls (floating stick, look drag, action buttons) |
| `autotest.gd`, `shot_tour.gd` | self-test and screenshot tours |

- **UI as code, not .tscn**: one `UiKit` (theme, parchment panels in wood/iron frames, blackletter
  headings, body font) used by every screen. The title screen can be the painted concept art itself
  with invisible buttons over the painted menu items. Check that fonts cover the UI language.
- **Animations** from glTF via AnimationPlayer; loop flags set in code; playback speed scaled to
  movement speed so feet don't slide.
- **Characters stream** in a radius around the player (e.g. spawn < 105 m, despawn > 150 m) to keep the
  stitched world fast, especially on web/mobile.
- Simple AI without navmesh is enough at first: move toward the player, slide sideways around
  obstacles; add NavigationRegion3D later if enemies get stuck.
- Water: a plane with a procedural shader (normals only, no screen reads) works on all renderers.
- Map tab: an image plus the world X/Z rectangle it covers (`map.rect` in the layout JSON); the player
  arrow is placed with that mapping and rotated to the hero's facing. See 05 for repainting the map.

## Debug flags (pass after `--`)

- `--autotest`: plays through movement, combat, inventory, trade, smith, house entry, defenestration,
  chest, night, fight, save/load, death, pause, settings, menu; writes `renders/game/*.png` and
  `autotest.log` (lines prefixed `AUTOTEST`). Run after every gameplay change; works in exported builds.
- `--tour x,z,yaw[,pitch[,y]] ...`: screenshots at given spots; `cam,px,py,pz,tx,ty,tz` for a free
  camera; `map,x,z,yaw[,y]` shoots the Map tab with the player arrow at that spot.
- `--touch`: force phone controls on desktop. `--layout <level>`: load a single district.
- Optional: `--perf`, `--reach` (reachability grid), `--cinematic` (scripted trailer camera recorded with
  `--write-movie`).

Run: `godot --path . scenes/game.tscn -- --autotest` (keep `--quit-after N` on long runs so a script
error can't leave it running). After adding new image files run `godot --headless --path . --import`
before testing, or `load()` returns null.

## Exports

Presets in `export_presets.cfg`: `Windows Desktop`, `Web`, `Android`.
- Web and Android use the **Compatibility** renderer; textures S3TC + ETC2; APK arm64, debug-signed.
- Include only the JSON the game loads (`include_filter`).
- Touch controls switch on automatically on phones and after the first touch.

```
godot --headless --path . --export-release "Windows Desktop" build/windows/<Game>.exe
godot --headless --path . --export-release "Web" build/web/index.html
godot --headless --path . --export-debug "Android" build/android/<Game>.apk
```

## Known traps

- `--check-only` reports false errors about autoloads; the real check is the autotest.
- Lambdas holding freed NPCs flood errors at night: disconnect or check `is_instance_valid`.
- Imported light energy far too high → fix the Blender export (RAW, 1/30), not Godot.
- Screen-space AA isn't available in Compatibility: a harmless warning on web.
