# Алхимики Праги — ассеты и сцена (вертикальный срез: Староместская площадь)

Экшен-RPG в средневековой Праге (стиль Gothic 1–2). Готовы Task 1–5 для одной локации — Староместской площади:
окружение, персонажи, пустой уровень с маркерами, живая сцена и играбельная игра на Godot 4.7.

Всё сгенерировано Python-скриптами в Blender 5.2: модели, текстуры, риги, анимации, раскладка уровня.
Любой файл пересобирается одной командой (см. «Пересборка»).

## Играть (Task 5)

- Билд: `build/windows/AlchemistsOfPrague.exe` (Windows, всё внутри).
- Из исходников: открыть папку в Godot 4.7.2 и нажать F5.

| Клавиша | Действие |
|---|---|
| W A S D | движение |
| Shift | спринт |
| Caps Lock | шаг / бег |
| Space | прыжок |
| Q / Alt | уклонение |
| Левая кнопка мыши | удар (клик ещё раз — комбо) |
| Правая кнопка мыши | блок щитом |
| E / F | войти в дом · торговать · кузнец · сундук · говорить · **схватить шатающегося врага** · **выбросить его в окно** |
| 1 / 2 / 3 | лечение / бодрость / противоядие |
| Tab / I | инвентарь (Персонаж, Журнал, Карта) |
| T | ждать до заката или рассвета |
| F5 / F9 | быстрое сохранение / загрузка |
| Esc | пауза |

Совет: в первом доме на площади прячется алхимик — раньте его, схватите (E) и выбросьте в окно (E).
Автотест: `godot --path . -- --autotest` → `renders/game/`.

## Структура

```
prague/
├─ README.md                      ← этот файл
├─ project.godot, export_presets.cfg   проект Godot 4.7 и пресет экспорта Windows
├─ scenes/                         main_menu.tscn, game.tscn
├─ scripts/                        GDScript игры (game, sfx, world, day_night, player, enemy, npc, potion, autotest, ui/)
├─ build/windows/                  AlchemistsOfPrague.exe (.gdignore)
├─ task1.md … task5.md            задачи (срез «Староместская площадь»)
├─ report_task1.md … report_task5.md   отчёты по задачам
├─ decisions.md                   все принятые решения и соглашения (оси, имена узлов, маркеры)
├─ issues.md                      известные проблемы и обходы
├─ props_list.md                  список окружения и пропсов (Task 1)
├─ characters_list.md             персонажи: рост, анимации, скорости (Task 2)
│
├─ concept/                       концепт-арты: locations/, characters/, ui/  (.gdignore)
├─ concept_art/                   исходные картинки (.gdignore)
│
├─ assets/                        ← ВСЁ, что нужно игре (импортируется в Godot)
│  ├─ architecture/*.gltf|.bin    здания: ратуша, Тынский храм, 6 бюргерских домов, готический дом,
│  │                              арка-проход, Марианская колонна, тайл брусчатки
│  ├─ props/*.gltf|.bin           31 пропс: прилавки, вертел, кузница, телега, фонари, факелы, знамя, мебель…
│  ├─ characters/*.gltf|.bin      12 персонажей со скелетом и анимациями
│  ├─ textures/*.png              общие текстуры всех glTF (альбедо + *_n нормали)
│  ├─ audio/ fonts/ ui/            звуки и музыка, шрифты, UI-текстуры и иконки (Task 5)
│  ├─ levels/
│  │  ├─ old_town_layout.json     уровень: размещение ассетов + маркеры + пресеты освещения
│  │  └─ old_town_population.json население: персонажи, расписание день/ночь, маршруты, эффекты
│  └─ CREDITS.md                  внешние ассеты (пока нет — всё своё)
│
├─ blender/                       исходники (.gdignore — Godot их не импортирует)
│  ├─ scripts/                    генераторы (см. ниже)
│  ├─ textures/                   сгенерированные текстуры (источник для assets/textures)
│  ├─ architecture.blend          библиотека зданий (коллекция на ассет)
│  ├─ props.blend                 библиотека пропсов
│  ├─ characters.blend            персонажи с ригами (анимации — NLA-треки)
│  ├─ world_old_town.blend        пустой уровень (Task 3): инстансы коллекций, маркеры, цикл день/ночь
│  └─ scene_old_town.blend        живая сцена (Task 4): уровень + население + эффекты
│
└─ renders/                       превью (.gdignore)
   ├─ previews/                   каждый ассет и персонаж (+ ночные, + раскадровки анимаций)
   ├─ world/                      пустой уровень: день/закат/ночь, план с маркерами, сравнение с артом
   └─ scene/                      живая сцена: день/ночь, крупные планы, сравнение с артом
```

## Соглашения (кратко; подробно — decisions.md)

- 1 unit = 1 м. В JSON-файлах координаты уже **в системе Godot** (+Y вверх, север плана = −Z).
- Фасады зданий и «перед» персонажей смотрят в **Godot +Z** (стандарт glTF). `yaw_deg` — поворот вокруг +Y.
- Маркер смотрит туда же, куда должен смотреть персонаж на нём.
- Узлы внутри glTF:

| Префикс | Что это |
|---|---|
| `INT_door_*` | дверь, pivot на петле |
| `INT_window_*` (+`_shutter_L/R`) | окно для дефенестрации и ставни на петлях |
| `INT_stall_*`, `INT_anvil` | торговец, кузнец |
| `MARK_*` | точки: дверь/интерьер/под окном/торговец/покупатель/кузнец/повар/лошадь |
| `ANIM_spit`, `ANIM_banner` | вращение вертела, покачивание знамени |
| `LIGHT_*` | точечный свет; ночной свет умножать на `lamp_factor` из пресетов |
| `*-colonly` | коллизия (Godot сам делает из неё StaticBody3D) |
| `<имя>_body`, `<имя>_rig` | меш и скелет персонажа |
| `WEAPON_*`, `HELD_*` | оружие и предметы в руках, можно скрывать или менять |

- Материалы, светящиеся ночью: `M_WindowLit`, `M_LanternGlass` — днём гасить emission. Огонь и угли светятся всегда.
- Анимации персонажей: `idle, walk, run, hit, death, flail` + `attack` (враги, стража), `block, throw` (Вацлав),
  `talk/work/beg/cast` (горожане, алхимик), у лошади `idle, walk, pull`. Без root motion; скорости — в characters_list.md.

## Как использовать в Godot (Task 5)

1. Корень проекта Godot — эта папка (`project.godot` создаётся в Task 5). Пути в JSON — `res://assets/...`.
2. Уровень: прочитать `assets/levels/old_town_layout.json` и для каждой записи `instances[]` инстанцировать
   `path` в `pos` с поворотом `yaw_deg` вокруг Y. 488 инстансов, сцены glTF переиспользуются.
3. Маркеры `markers[]`:

| `kind` | Что это |
|---|---|
| `door` / `interior` / `window` | входы в дома и окна для дефенестрации; поле `owner` — дом |
| `merchant` / `customer` / `smith` / `cook` / `horse` | рабочие места |
| `spawn` | враги (`enemy`, `time: night`) |
| `npc`, `patrol`, `wander` | NPC, маршрут стражи, точки блуждания |
| `player` | старт игрока |
| `exit` | выходы к будущим локациям (`leads_to`) |

4. Население: `assets/levels/old_town_population.json → population[]`:
   - `character` и `path` — какую сцену инстанцировать;
   - `animation` — какую анимацию играть;
   - `schedule` — когда персонаж на сцене: `day`, `night` или `always`;
   - `role` — роль, `route`/`route_points` — маршрут.
5. Эффекты: `fx[]` — вращение вертела, покачивание знамён, мерцание огня, дым (в Godot — GPUParticles3D),
   знамёна-пропсы.
6. День/ночь: `layout.lighting.keys` — ключи солнца, неба, ламп и окон на цикле 400 кадров.
   Рекомендуемая длина цикла — 1200 с (≈20 минут, как в Task 5).

## Пересборка

`blender` = `C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`, запуск из `blender/scripts`:

```
blender -b --factory-startup -P make_textures.py          # текстуры окружения
blender -b --factory-startup -P make_char_textures.py     # текстуры персонажей
blender -b --factory-startup -P build_architecture.py     # здания (+превью)        [-- --no-render | --only a,b]
blender -b --factory-startup -P build_props.py            # пропсы (+превью)
blender -b --factory-startup -P build_characters.py       # персонажи (+превью)
blender -b --factory-startup -P build_world.py            # уровень + layout.json (+рендеры)
blender -b --factory-startup -P build_scene.py            # население + эффекты + population.json (+рендеры)
blender -b --factory-startup -P make_ui_assets.py         # UI-текстуры и иконки предметов (Task 5)
```

Порядок важен: текстуры → архитектура/пропсы → персонажи → мир → сцена.

Модули:
- `lib_tex.py`, `lib_tex_char.py` — текстуры;
- `lib_geo.py` — меши, материалы, UV, экспорт glTF;
- `lib_char.py` — лофты, скелеты, скиннинг, позы, анимации;
- `lib_render.py`, `sheet.py` — превью.
