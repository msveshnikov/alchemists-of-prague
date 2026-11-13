# 02 — The five task files

Each task is a markdown file run by one autonomous Claude Code session ("do task3.md"). Run them
strictly in order. **Run 1 = vertical slice** (one location, the most detailed). Review it, fix the
task texts, then **run 2** = the same five tasks for the remaining locations, then stitch one world.

Paste these two blocks at the top of every task file.

## Block A — autonomous mode

```markdown
## Mode: fully autonomous
- Don't ask questions or wait for confirmation. Make every decision yourself and record it in decisions.md.
- If something is unclear in the concept art, choose a reasonable option in the target style and continue.
- Don't wait for Blender MCP, Godot MCP or other tools to connect. Work with what is there: run Blender
  from the command line with Python scripts (blender -b --factory-startup -P script.py).
- If a step fails, try another approach. If that fails too, record the problem in issues.md and move on.
- Don't stop until the task is complete. At the end write a short report in report_taskN.md:
  what was done, what did not work.
- Look at your results (preview renders, contact sheets, screenshots) and compare with the concept art
  before calling anything done.
```

## Block B — external assets

```markdown
## External assets
- Build all models and textures (buildings, props, characters) yourself in Blender with Python scripts.
  No paid 3D generation services.
- No terrain plugins: the world is mostly flat; model hills/cliffs in Blender.
- Sounds and music: search and download free ones (footsteps, swords, market, horses, fire, night
  ambience, hits, screams).
- Animations: make them in Blender first. Only if they still look bad after several attempts (foot
  sliding, jerks, unnatural poses), find a free one and retarget it to your rigs.
- Only free assets with open licences (CC0, CC-BY): Freesound, OpenGameArt, Kenney, Quaternius, Sonniss
  GDC bundles. Godot Asset Library (godotengine.org/asset-library/api) for water/sky shaders, day-night,
  particles, controllers — check Godot version compatibility.
- If a site needs a login, skip it and use another source; don't wait for the user.
- Record every downloaded asset in assets/CREDITS.md: file, source, author, licence, link.
```

## task1.md — environment and props (Blender)

```markdown
# Task 1: Environment and props in Blender
## Goal
From the location concept art, build 3D models of the environment and props for <Game>
(<style: e.g. Gothic 1–2, semi-realistic, hand-painted textures, not cartoon, not low-poly>).
## Inputs
- concept/locations/ (day and night art), concept/locations/world_map.png
## Steps
1. Study the art. Write props_list.md per location: buildings, doors, windows, stalls, spits, barrels,
   carts, lanterns, torches, bridges, walls, ...
2. Split into architecture (static), props (small), interactive (doors, windows for throwing enemies
   out, merchant stalls, anvils, chests).
3. Model each as a separate asset in Blender, one shared scale (1 unit = 1 m).
4. Make textures in one style and the palette of the style block.
5. Lanterns, torches, windows: light sources + emissive materials for night.
6. Export to assets/props/ and assets/architecture/ (glTF), with preview renders of every asset.
## Result
props_list.md, .blend libraries, glTF exports, preview renders, conventions written into decisions.md.
```

## task2.md — characters

```markdown
# Task 2: Characters
## Goal
3D models of all characters from concept/characters/ in the same style and scale as Task 1.
## Steps
1. Write characters_list.md with height and key details of each.
2. Model them: humans ~1.8 m, big monsters per the art.
3. Rig and animate: idle, walk, run, attack, hit, death; hero also block and throw (grab and toss an
   enemy); townsfolk talk/work; animals idle/walk/pull.
4. Emissive details (glowing runes, eyes, potions).
5. Export to assets/characters/ (glTF with animations), preview renders and contact sheets.
## Result
characters_list.md (incl. the walk/run speed at which feet don't slide), rigged animated models, renders.
```

## task3.md — empty levels

```markdown
# Task 3: Empty levels
## Goal
Assemble from Task 1 assets the empty level(s) without characters, matching concept/empty/ and the
world map.
## Steps
1. Plan the layout from the world map: compress distances for play, add side streets, arches and
   alleys between locations that the player can run through.
2. Place architecture and static props; the main location is the most detailed.
3. Place empty markers: house entries, windows for defenestration, merchant spots, NPC and enemy spawns.
4. Lighting: day preset (warm sun) and night preset (moon, lanterns, torches, lit windows), smooth
   day-night transition.
5. Render every location day and night and compare with the concept art.
6. Write the level for the engine as JSON (assets/levels/<level>_layout.json: instances, markers,
   districts, lighting presets, map info).
## Result
Level .blend, layout JSON, day/night renders.
```

## task4.md — population

```markdown
# Task 4: Bring the scene to life
## Steps
1. Place characters on Task 3 markers: merchants at stalls, cook at the spit, guards, townsfolk,
   horses with carts.
2. Place enemies (more at night).
3. Put the hero at the start point.
4. Effects: rotating spits, smoke, fire, flags, river water.
5. Check day and night in every location against the art; fix style mismatches.
6. Export for the engine: assets/levels/<level>_population.json (who, where, facing, schedule
   day/night/always, behaviour), describe the file structure in README.md.
## Result
Full scene, day/night renders, population JSON, README.md.
```

## task5.md — the game in Godot

```markdown
# Task 5: Game logic and UI in Godot 4
## Steps
1. Import world, characters, animations. Check scale, collisions, materials, lights. Build the level at
   runtime from the Task 3/4 JSON.
2. Hero control: third-person camera, walk, run, sprint, jump, dodge, interact.
3. Combat: strike/combo, shield block, dodge, damage, death. Enemy AI per type (ranged keeps distance,
   heavy is slow and strong, weak ones attack in groups).
4. Houses: enter through doors, interiors; defenestration — grab a staggered enemy and throw it out of
   a window with falling physics.
5. Economy: gold from enemies and looting, market buy/sell, blacksmith sword upgrades, potions.
6. Day/night: ~20 min real-time cycle, lamps at night, more enemies, merchants close.
7. UI in the style of concept/ui (title screen, settings, HUD, inventory with paper doll, trade,
   death, pause, map).
8. Sound: footsteps, combat, market by day, night ambience, menu and combat music.
9. Save/load.
10. An --autotest mode that plays through everything and writes screenshots + a log.
11. Export Windows (+ Web and Android with touch controls), play it, fix bugs, ship (06).
## Result
Playable builds, Godot project, README.md with controls and rebuild steps, report_task5.md.
```

## Run 2 and the stitched world

For each further location, copy the five tasks with "Run 2 — <locations>" in the title, list exactly
which new assets/characters/levels are needed, and require reuse of the run-1 libraries and conventions.
Afterwards write a "one world" task: a world builder script that places all district layouts with
offsets, connects them with streets/bridges, seals the borders (river, walls, closed gates), assigns
district names for the HUD, streams NPCs by distance, renders a top-down plan for the map, and writes
one `<world>_layout.json` + `<world>_population.json`.
