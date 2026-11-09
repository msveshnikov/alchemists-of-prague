# Алхимики Праги — концепт-арт и задачи для Claude Code

Экшен-RPG в средневековой Праге. Главный герой — рыцарь Вацлав из Вышеграда. Враги: злые алхимики, големы, скелеты. Механики: ближний бой, вход в дома и дефенестрация врагов, рынок, торговля, грабёж, прокачка меча. Смена дня и ночи.

## Стилевой блок (вставлять в начало КАЖДОГО промпта)

```
Game concept art in the style of early-2000s European PC RPGs like Gothic 1 and Gothic 2: semi-realistic, hand-painted textures, grounded medieval look, slightly stylized proportions, no cartoon, no low-poly, no photorealism. Medieval Prague, 14th century. Consistent palette: warm stone beige, terracotta roofs, dark timber, muted greens and deep reds. Soft painterly lighting, readable silhouettes, isometric-ish three-quarter view from above, 16:9.
```

Дневное дополнение:

```
Daytime, bright sunny late morning, warm golden light, clear sky with soft clouds, lively and beautiful atmosphere.
```

Ночное дополнение:

```
Night, deep blue moonlit sky, lit torches, lanterns and glowing windows, warm orange light pools against cold blue shadows, mysterious but not horror.
```

Совет: первую удачную картинку подкладывай как референс ко всем следующим и пиши: "keep exactly the same art style as the reference image".

## Промпты: локации

Каждую локацию генерировать дважды: со дневным и с ночным дополнением.

### 1. Староместская площадь (главная, самая детальная)

```
Old Town Square of medieval Prague, wide cobblestone square, Gothic Týn church with two dark spires in the background, Old Town Hall with astronomical clock tower, colorful gabled burgher houses with arcades and wooden doors that look enterable. Busy market: wooden stalls with cloth awnings, meat roasting on rotating spits over open fire, bread, vegetables, pottery, weapons stall, blacksmith. People in medieval clothes, merchants, guards, horses and a cart. Narrow streets of Old Town radiating out from the square.
```

### 2. Карлов мост

```
Stone Gothic bridge over the Vltava river in medieval Prague, massive bridge towers at both ends, stone arches, river below with small wooden boats, view of the castle hill on the far bank, travelers, carts and a guard post on the bridge.
```

### 3. Мала Страна

```
Malá Strana district of medieval Prague below the castle hill, steep narrow winding streets, red-roofed houses, small courtyards, taverns with hanging signs, stairs leading uphill, gardens and stone walls, enterable doors and windows on upper floors.
```

### 4. Вышеград

```
Vyšehrad fortress on a rocky cliff above the Vltava, thick stone walls, gate tower, small Romanesque rotunda, old cemetery, training ground for knights, view down to the river and the city nearby. Compact layout, close to Old Town.
```

### 5. Общая карта мира

```
Top-down stylized overview map of a compact medieval Prague game world: Old Town Square in the center with streets radiating out, Charles Bridge across the Vltava, Malá Strana on the other bank, Vyšehrad fortress to the south, all close together. Clear readable layout like a game level map.
```

### 6. Пустые локации (для сборки)

К каждому промпту локации добавить:

```
Empty scene: no people, no animals, no carts, no loose items, only architecture, ground and fixed props.
```

## Промпты: персонажи

Для персонажей добавлять: `full body character concept, front view and side view, neutral grey background, character sheet`.

### Вацлав из Вышеграда (герой)

```
Young Czech knight Václav, around 30, short dark hair, light beard, determined face, worn chainmail with a dark red surcoat with a simple white emblem, leather belts, longsword, round shield, practical not shiny armor.
```

### Злой алхимик

```
Sinister medieval alchemist, long dark hooded robe with stains and burn marks, belts with glass vials of glowing green and purple liquids, leather gloves, staff with brass apparatus, pale face, sharp eyes.
```

### Голем

```
Large clay golem from Prague legend, massive humanoid body of cracked grey-brown clay, glowing Hebrew letters on the forehead, roughly shaped hands, heavy slow posture, about twice human height.
```

### Скелет-воин

```
Undead skeleton warrior raised by alchemy, yellowed bones, rusty helmet and broken chainmail scraps, notched sword, faint green glow in the eye sockets.
```

### Горожане и торговцы

```
Set of medieval Prague townsfolk: butcher at a roasting spit, market woman with basket, merchant with fur hat, city guard with halberd, beggar, children. Same art style, character sheet.
```

### Лошадь

```
Medieval workhorse, brown with dark mane, simple leather harness, side view and three-quarter view.
```

## Промпты: интерфейс

К UI-промптам добавлять: `game UI design, medieval manuscript style, aged parchment, dark wood and wrought iron frames, gold leaf ornaments, Gothic blackletter headings, readable, in the style of Gothic 1–2 menus`.

### Стартовый экран

```
Title screen for the game "Alchemists of Prague": painted panorama of medieval Prague at dusk with Týn church spires and Charles Bridge, a knight silhouette in the foreground, a looming clay golem in the mist, game title in ornate Gothic lettering, menu: New Game, Continue, Settings, Exit, on a parchment banner.
```

### Настройки

```
Settings menu: parchment panel in a dark wood and iron frame, tabs Graphics, Sound, Controls, Gameplay, sliders shaped like sword blades, checkboxes as wax seals.
```

### HUD

```
In-game HUD over a medieval Prague street: health bar as a red ornate bar, stamina bar, gold coin counter, current sword icon in an iron frame, quick slots with potions (red health, blue stamina, green antidote), small compass at top, day/night sun-moon indicator.
```

### Инвентарь и экипировка

```
Inventory screen: knight paper-doll in the center showing equipped helmet, chainmail, surcoat, sword, shield, grid of item slots on parchment with potions, gold, alchemical ingredients, sword upgrade panel with stats.
```

### Торговля

```
Market trade window: merchant portrait on the left, two item grids for buying and selling, gold balance, price tags on small parchment labels.
```

### Экран смерти

```
Death screen: dark red vignette over a blurred cobblestone street, broken sword on the ground, Gothic text "You have fallen", buttons Load Game and Main Menu on parchment.
```

## Задачи для Claude Code

Каждую задачу сохранить отдельным файлом: task1.md, task2.md, task3.md, task4.md. Все концепт-арты положить в папку `concept/` (локации: `concept/locations/`, персонажи: `concept/characters/`, пустые сцены: `concept/empty/`). Запускать задачи строго по порядку.

**Порядок запуска: сначала вертикальный срез.** Первый прогон task 1–5 делать только для Староместской площади. Проверить результат, поправить задачи, и только потом запускать их на Карлов мост, Малу Страну и Вышеград.

### Правила автономной работы (вставить в начало каждого task-файла)

```markdown
## Режим работы: полностью автономный
- Не задавай вопросов и не жди подтверждения. Все решения принимай сам и записывай их в decisions.md.
- Если что-то неясно на концепт-арте, выбери разумный вариант в стиле Gothic 1–2 и продолжай.
- Не жди подключения Blender MCP, Godot MCP или других инструментов. Работай с тем, что уже есть: запускай Blender через командную строку и Python-скрипты (blender --background --python script.py).
- Если шаг не удаётся, попробуй другой подход. Если и он не сработал, запиши проблему в issues.md и переходи к следующему шагу.
- Не останавливайся до конца задачи. В конце запиши краткий отчёт в report_taskN.md: что сделано, что не получилось.
```

### Ассеты из интернета (тоже вставить в каждый task-файл)

```markdown
## Внешние ассеты
- Все модели и текстуры (здания, предметы, персонажи) создавай сам в Blender через Python-скрипты. Платных сервисов генерации 3D нет, не используй их.
- Террейн-плагины не нужны: мир почти плоский, холм Вышеграда смоделируй в Blender.
- Звуки и музыку ищи и скачивай в интернете: шаги, мечи, рынок, лошади, огонь, ночные звуки, удары, крики при дефенестрации.
- Анимации сначала делай сам в Blender. Если после нескольких попыток анимация выглядит корявой (скольжение ног, рывки, неестественные позы), найди и скачай готовую бесплатную.
- Бери только бесплатные ассеты с открытой лицензией (CC0, CC-BY). Подходящие источники: Freesound, OpenGameArt, Kenney, Quaternius, Sonniss GDC bundles.
- Godot Asset Library (godotengine.org/asset-library): ищи там шейдеры воды и неба, системы день/ночь, освещение, частицы огня и дыма, контроллеры персонажа. Если Godot MCP подключён, можно через него; если нет, качай напрямую через открытый API библиотеки (godotengine.org/asset-library/api), не жди MCP. Проверяй совместимость с версией Godot.
- Если сайт требует логин, пропусти его и ищи другой источник, не жди меня.
- Каждый скачанный ассет запиши в assets/CREDITS.md: файл, источник, автор, лицензия, ссылка.
- Скачанные анимации перенацель (retarget) на ригги своих персонажей.
```

### task1.md — Окружение и предметы

```markdown
# Task 1: Окружение и пропсы в Blender

## Цель
По концепт-артам локаций создать в Blender 3D-модели окружения и предметов для игры «Алхимики Праги» (средневековая Прага, стиль Gothic 1–2: полуреализм, рисованные текстуры, не мультяшно, не лоу-поли).

## Входные данные
- concept/locations/ — дневные и ночные арты 4 локаций и общей карты.

## Шаги
1. Изучи все арты. Составь список объектов по каждой локации (props_list.md): здания, двери, окна, прилавки, вертела с мясом, бочки, повозки, фонари, факелы, мост, стены Вышеграда и т.д.
2. Раздели объекты на: архитектура (неподвижное), пропсы (мелкие предметы), интерактивное (двери, окна для дефенестрации, прилавки торговцев).
3. Смоделируй каждый объект в Blender отдельным ассетом, с единым масштабом (1 unit = 1 m).
4. Сделай текстуры в едином стиле и палитре из стилевого блока.
5. Для фонарей, факелов и окон добавь источники света и emissive-материалы для ночного режима.
6. Экспортируй ассеты в assets/props/ и assets/architecture/ (glTF).

## Результат
- props_list.md, .blend файлы, экспорт в glTF, превью-рендеры каждого ассета.
```

### task2.md — Персонажи

```markdown
# Task 2: Персонажи

## Цель
Создать 3D-модели всех персонажей по концепт-артам в том же стиле, что окружение из Task 1.

## Входные данные
- concept/characters/ — Вацлав, алхимик, голем, скелет, горожане, лошадь.
- Ассеты из Task 1 (для сверки стиля и масштаба).

## Шаги
1. Изучи арты, составь characters_list.md с ростом и ключевыми деталями каждого.
2. Смоделируй персонажей, рост человека около 1.8 m, голем около 3.5 m.
3. Сделай риг и базовые анимации: idle, ходьба, бег, атака, получение урона, смерть. Для Вацлава ещё блок щитом и бросок врага (дефенестрация). Для лошади: стоит, идёт, тянет повозку.
4. Для голема: светящиеся буквы на лбу (emissive). Для скелета: зелёное свечение глаз.
5. Экспорт в assets/characters/ (glTF с анимациями).

## Результат
- characters_list.md, модели с ригом и анимациями, превью-рендеры.
```

### task3.md — Пустые локации

```markdown
# Task 3: Пустые карты уровней

## Цель
Собрать из ассетов Task 1 пустые уровни без персонажей: Староместская площадь со Старым городом, Карлов мост, Мала Страна, Вышеград, соединённые в один компактный мир.

## Входные данные
- concept/empty/ и общая карта из concept/locations/.
- Ассеты из Task 1.

## Шаги
1. По общей карте сделай план мира: площадь в центре, улицы расходятся от неё, мост через Влтаву, Мала Страна на другом берегу, Вышеград недалеко к югу. Расстояния сжать для удобства игры. Между локациями сделай кварталы Старого города с узкими извилистыми улочками, арками и переулками, по которым можно бегать.
2. Расставь архитектуру и неподвижные пропсы. Староместская площадь — самая детальная.
3. Отметь точки входа в дома, окна для дефенестрации, места торговцев, точки спавна врагов и NPC (пустые маркеры).
4. Настрой освещение: дневной пресет (тёплое солнце) и ночной (луна, фонари, факелы, светящиеся окна). Сделай плавный переход день–ночь.
5. Сделай рендеры каждой локации днём и ночью и сравни с концепт-артами.

## Результат
- Сцена мира, файл маркеров, рендеры день/ночь.
```

### task4.md — Сборка

```markdown
# Task 4: Финальная сборка сцены

## Цель
Объединить окружение, пустые карты и персонажей в живой мир, соответствующий концепт-артам.

## Входные данные
- Результаты Task 1–3 и все концепт-арты.

## Шаги
1. Размести персонажей по маркерам из Task 3: торговцы у прилавков, повар у вертела, стража, горожане, лошади с повозками.
2. Размести врагов: алхимики, големы, скелеты (ночью их больше).
3. Добавь Вацлава как игрового персонажа в точке старта на Староместской площади.
4. Оживи сцену: вращение мяса на вертелах, дым, огонь, флаги, вода во Влтаве.
5. Проверь день и ночь на каждой локации, сравни с дневными и ночными артами, исправь расхождения стиля.
6. Подготовь экспорт для игрового движка и опиши структуру файлов в README.md.

## Результат
- Полная собранная сцена, рендеры день/ночь, README.md.
```

### task5.md — Игра в Godot

```markdown
# Task 5: Игровая логика и интерфейс в Godot

## Цель
Собрать из результатов Task 1–4 играбельную игру в Godot 4.

## Входные данные
- Сцена и ассеты из Task 4, звуки из assets/, UI-арты из concept/ui/.

## Шаги
1. Импортируй мир, персонажей и анимации в Godot. Проверь масштаб, коллизии, материалы и свет.
2. Управление Вацлавом: камера от третьего лица, ходьба, бег, прыжок, взаимодействие.
3. Бой: удар мечом, блок щитом, уклонение, урон, смерть. ИИ врагов: алхимик держит дистанцию и бросает зелья, голем медленный и сильный, скелеты нападают группами.
4. Дома: вход через двери, интерьеры, дефенестрация — схватить врага и выбросить в окно с физикой падения.
5. Экономика: золото с врагов и грабежа, рынок с покупкой и продажей, кузнец для прокачки меча, зелья лечения и выносливости.
6. День и ночь: цикл примерно 20 минут реального времени, фонари зажигаются ночью, ночью больше врагов, торговцы закрываются.
7. Интерфейс в стиле UI-артов (пергамент, тёмное дерево, железо, готический шрифт): стартовый экран, настройки (графика, звук, управление), HUD (здоровье, выносливость, золото, текущий меч, слоты зелий, индикатор дня и ночи), инвентарь с экипировкой, окно торговли, экран смерти, пауза.
8. Звук: шаги по брусчатке, бой, шум рынка днём, ночная атмосфера, музыка для меню и боя.
9. Сохранение и загрузка.
10. Собери билд под Windows, пройдись по игре сам и исправь найденные баги.

## Результат
- Играбельный билд, проект Godot, README.md с управлением, report_task5.md.
```
