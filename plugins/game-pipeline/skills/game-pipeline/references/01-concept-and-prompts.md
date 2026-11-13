# 01 — Design doc, style block and art prompts

The design doc is the single source the whole pipeline grows from. Name it
`<Game title> — concept art and tasks.md` and keep it in the repo root. Sections:

1. **Pitch** (3–5 lines): genre, setting, hero, enemies, core mechanics, day/night or other cycles.
   Example: *Action RPG in medieval Prague. Hero: knight Václav of Vyšehrad. Enemies: evil alchemists,
   golems, skeletons. Mechanics: melee combat, entering houses and throwing enemies out of windows
   (defenestration), market, trading, looting, sword upgrades. Day/night cycle.*
2. **Style block**: pasted at the start of EVERY image prompt so all art matches.
3. **Lighting add-ons**: day and night variants (or seasons, weather, etc.).
4. **Prompts**: locations, empty locations, world map, characters, UI screens.
5. **Task files**: the five task templates filled in for this game (see 02).

## Style block template

Name a reference game/era, the rendering style, what to avoid, the setting, the palette, the light,
the camera and the aspect ratio:

```
Game concept art in the style of <reference games/era>: <semi-realistic, hand-painted textures,
grounded look, slightly stylized proportions>, no cartoon, no low-poly, no photorealism.
<Setting, century>. Consistent palette: <4–6 named colours>. Soft painterly lighting, readable
silhouettes, isometric-ish three-quarter view from above, 16:9.
```

The Prague version:

```
Game concept art in the style of early-2000s European PC RPGs like Gothic 1 and Gothic 2: semi-realistic,
hand-painted textures, grounded medieval look, slightly stylized proportions, no cartoon, no low-poly,
no photorealism. Medieval Prague, 14th century. Consistent palette: warm stone beige, terracotta roofs,
dark timber, muted greens and deep reds. Soft painterly lighting, readable silhouettes, isometric-ish
three-quarter view from above, 16:9.
```

Day add-on: `Daytime, bright sunny late morning, warm golden light, clear sky with soft clouds, lively and beautiful atmosphere.`
Night add-on: `Night, deep blue moonlit sky, lit torches, lanterns and glowing windows, warm orange light pools against cold blue shadows, mysterious but not horror.`

**Consistency trick:** once one image is great, attach it to every next request and write
"keep exactly the same art style as the reference image" (05 shows how to attach files).

## Prompt sets

### Locations (each twice: day and night)
Describe landmarks, the ground, the buildings and that doors and windows look *enterable*, market
stalls and props, people, and the streets leading out. Make the main (vertical-slice) location the
most detailed. Example:

```
Old Town Square of medieval Prague, wide cobblestone square, Gothic Týn church with two dark spires in
the background, Old Town Hall with astronomical clock tower, colorful gabled burgher houses with arcades
and wooden doors that look enterable. Busy market: wooden stalls with cloth awnings, meat roasting on
rotating spits over open fire, bread, vegetables, pottery, weapons stall, blacksmith. People in medieval
clothes, merchants, guards, horses and a cart. Narrow streets of Old Town radiating out from the square.
```

### Empty locations (for building levels)
Same prompt + `Empty scene: no people, no animals, no carts, no loose items, only architecture, ground and fixed props.`
These go to `concept/empty/` and drive task3.

### World map
```
Top-down stylized overview map of a compact <setting> game world: <main location> in the center with
streets radiating out, <landmark A> ..., <landmark B> ..., all close together. Clear readable layout like
a game level map.
```
Later the *in-game* map is not this picture: it is repainted from a render of the real level (05).

### Characters
Add `full body character concept, front view and side view, neutral grey background, character sheet`.
Give age, build, face, hair, clothing layers, colours, emblem, weapons, and for monsters the size
relative to a human and any glow. Include the hero, each enemy type, townsfolk as one sheet, animals.

```
Young Czech knight Václav, around 30, short dark hair, light beard, determined face, worn chainmail with
a dark red surcoat with a simple white emblem, leather belts, longsword, round shield, practical not
shiny armor.
```

### UI
Add `game UI design, <manuscript/sci-fi/...> style, <materials of panels and frames>, <heading font
style>, readable, in the style of <reference game> menus`. Screens: title screen (with the game title
and menu items painted in — it can be used directly as the menu background with invisible buttons),
settings, HUD, inventory/equipment, trade, death screen, pause.

## Where things go

```
concept/locations/<place>_day.png, <place>_night.png, world_map.png
concept/empty/<place>_empty.png
concept/characters/<name>.png
concept/ui/title_screen.png, settings.png, hud.png, inventory.png, trade.png, death.png
concept_art/   extra reference art ordered later (mood pieces, map repaints) — has .gdignore
```
