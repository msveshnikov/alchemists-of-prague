extends Node
## Global game state: player stats, inventory, equipment, settings, save/load, item database.

signal gold_changed(value: int)
signal inventory_changed
signal stats_changed
signal message(text: String, color: Color)
signal wanted_changed(seconds: float)

const SAVE_PATH := "user://save_slot1.json"
const SETTINGS_PATH := "user://settings.cfg"

const FONT_GOTHIC := preload("res://assets/fonts/UnifrakturMaguntia-Book.ttf")
const FONT_BODY := preload("res://assets/fonts/IMFellEnglish-Roman.ttf")

## Item database. price = buy price at merchants (they pay 50% when buying from you).
const ITEMS := {
	"potion_health": {"name": "Healing Draught", "icon": "potion_health", "type": "potion", "price": 25, "weight": 0.5,
		"desc": "Red tincture of the barber-surgeons. Restores 50 health."},
	"potion_stamina": {"name": "Vigour Tonic", "icon": "potion_stamina", "type": "potion", "price": 20, "weight": 0.5,
		"desc": "Blue tonic. Restores all stamina and speeds its recovery for 20 s."},
	"potion_antidote": {"name": "Antidote", "icon": "potion_antidote", "type": "potion", "price": 15, "weight": 0.5,
		"desc": "Green remedy against the alchemists' poisons."},
	"bread": {"name": "Rye Bread", "icon": "bread", "type": "food", "price": 3, "weight": 0.4, "desc": "Restores 10 health."},
	"meat": {"name": "Roast Pork", "icon": "meat", "type": "food", "price": 6, "weight": 0.6, "desc": "Restores 18 health."},
	"herb": {"name": "Mandrake Leaves", "icon": "herb", "type": "ingredient", "price": 4, "weight": 0.1,
		"desc": "Alchemical ingredient. Merchants pay a little for it."},
	"mushroom": {"name": "Toadstool", "icon": "mushroom", "type": "ingredient", "price": 5, "weight": 0.1, "desc": "Alchemical ingredient."},
	"quicksilver": {"name": "Vial of Quicksilver", "icon": "quicksilver", "type": "ingredient", "price": 18, "weight": 0.3,
		"desc": "Taken from an alchemist. Valuable."},
	"clay_shard": {"name": "Golem Clay Shard", "icon": "clay_shard", "type": "ingredient", "price": 40, "weight": 1.0,
		"desc": "A shard of living clay. The letters on it still glow faintly."},
	"bone_dust": {"name": "Bone Dust", "icon": "bone_dust", "type": "ingredient", "price": 8, "weight": 0.2, "desc": "What remains of a risen skeleton."},
	"scroll": {"name": "Alchemist's Notes", "icon": "scroll", "type": "misc", "price": 30, "weight": 0.1,
		"desc": "Cipher and sigils. Someone in the Old Town is paying for these."},
	"key": {"name": "Rusty Key", "icon": "key", "type": "misc", "price": 2, "weight": 0.1, "desc": "Opens nothing you know of. Yet."},
	"helmet": {"name": "Iron Kettle Hat", "icon": "helmet", "type": "equip", "slot": "helmet", "armor": 4, "price": 80, "weight": 2.0,
		"desc": "Wide-brimmed helmet of the city guard. Armour +4."},
	"chainmail": {"name": "Chainmail Coif", "icon": "chainmail", "type": "equip", "slot": "armor", "armor": 6, "price": 120, "weight": 4.0,
		"desc": "Riveted mail for head and shoulders. Armour +6."},
	"gloves": {"name": "Leather Gauntlets", "icon": "gloves", "type": "equip", "slot": "gloves", "armor": 2, "price": 40, "weight": 0.8,
		"desc": "Armour +2."},
	"ring": {"name": "Ring of Vigour", "icon": "ring", "type": "equip", "slot": "ring", "stamina": 25, "price": 90, "weight": 0.0,
		"desc": "Amethyst ring. Maximum stamina +25."},
	"shield": {"name": "Lion Shield", "icon": "shield", "type": "equip", "slot": "shield", "block": 0.8, "price": 60, "weight": 3.0,
		"desc": "Round shield with the Bohemian lion. Blocks 80% of frontal damage."},
}

const SWORDS := [
	{"name": "Knightly Sword", "min": 14, "max": 20, "cost": 0},
	{"name": "Honed Sword", "min": 20, "max": 27, "cost": 60},
	{"name": "Tempered Blade", "min": 27, "max": 35, "cost": 130},
	{"name": "Blade of Vysehrad", "min": 35, "max": 46, "cost": 240},
]

# ---------------------------------------------------------------- state
var gold := 30
var hp := 100.0
var max_hp := 100.0
var stamina := 100.0
var base_stamina := 100.0
var sword_level := 0
var inventory := {}            # id -> count
var equipment := {"sword": "sword", "shield": "shield", "helmet": "", "armor": "", "gloves": "", "ring": ""}
var poison_time := 0.0
var slow_time := 0.0
var vigour_time := 0.0
var wanted := 0.0              # seconds the guards stay hostile
var looted_houses := {}        # house id -> true
var kills := {"alchemist": 0, "skeleton": 0, "golem": 0, "defenestrated": 0}
var journal: Array[String] = []
var time_of_day := 0.93        # 0..1 of the day cycle (0 = noon key of the lighting cycle); 0.93 = mid-morning
var pending_load := {}         # filled by load_game() before the world scene starts
var location := "old_town"     # level being played: old_town, charles_bridge, mala_strana, vysehrad
var arrive_from := ""          # level we just travelled from (spawn at its exit marker), "" = start marker / save
var visited := {}              # level -> true
var autotest := false
## Touch mode: on-screen controls instead of mouse look. On for phones/tablets (native or browser),
## and switched on by the first real screen touch anywhere else (e.g. a touchscreen laptop).
var touch := false
signal touch_mode_changed

var settings := {
	"master": 0.8, "music": 0.55, "sfx": 0.85, "mouse_sens": 0.22, "invert_y": false, "fullscreen": false,
	"shadows": true, "ssao": true, "glow": true, "render_scale": 1.0, "day_minutes": 20.0, "difficulty": 1.0, "vsync": true,
}


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	autotest = "--autotest" in OS.get_cmdline_user_args() or "--autotest" in OS.get_cmdline_args()
	_setup_input()
	if OS.has_feature("mobile") or OS.has_feature("web_android") or OS.has_feature("web_ios") or "--touch" in OS.get_cmdline_user_args():
		enable_touch()
	load_settings()
	apply_settings()


# ---------------------------------------------------------------- input map
func _key(action: String, keys: Array, mouse: Array = []) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action)
	for k in keys:
		var ev := InputEventKey.new()
		ev.physical_keycode = k
		InputMap.action_add_event(action, ev)
	for b in mouse:
		var mev := InputEventMouseButton.new()
		mev.button_index = b
		InputMap.action_add_event(action, mev)


func _setup_input() -> void:
	_key("move_forward", [KEY_W, KEY_UP])
	_key("move_back", [KEY_S, KEY_DOWN])
	_key("move_left", [KEY_A, KEY_LEFT])
	_key("move_right", [KEY_D, KEY_RIGHT])
	_key("jump", [KEY_SPACE])
	_key("sprint", [KEY_SHIFT])
	_key("dodge", [KEY_Q, KEY_ALT])
	_key("attack", [], [MOUSE_BUTTON_LEFT])
	_key("block", [], [MOUSE_BUTTON_RIGHT])
	_key("interact", [KEY_E, KEY_F])
	_key("potion_1", [KEY_1])
	_key("potion_2", [KEY_2])
	_key("potion_3", [KEY_3])
	_key("inventory", [KEY_TAB, KEY_I])
	_key("pause", [KEY_ESCAPE])
	_key("quicksave", [KEY_F5])
	_key("quickload", [KEY_F9])
	_key("wait", [KEY_T])


func _input(event: InputEvent) -> void:
	if not touch and event is InputEventScreenTouch:
		enable_touch()


func enable_touch() -> void:
	if touch:
		return
	touch = true
	# Touches are emulated as left-mouse clicks for the GUI; they must not also swing the sword / raise the shield.
	for a in ["attack", "block"]:
		for ev in InputMap.action_get_events(a):
			if ev is InputEventMouseButton:
				InputMap.action_erase_event(a, ev)
	if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	touch_mode_changed.emit()


## Gameplay mouse mode: captured mouse-look on desktop, free pointer in touch mode.
func capture_mouse() -> void:
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE if touch else Input.MOUSE_MODE_CAPTURED


# ---------------------------------------------------------------- state helpers
func new_game() -> void:
	gold = 30
	max_hp = 100.0
	hp = max_hp
	base_stamina = 100.0
	stamina = max_stamina()
	sword_level = 0
	inventory = {"potion_health": 3, "potion_stamina": 2, "potion_antidote": 1, "bread": 2}
	equipment = {"sword": "sword", "shield": "shield", "helmet": "", "armor": "", "gloves": "", "ring": ""}
	poison_time = 0.0
	slow_time = 0.0
	vigour_time = 0.0
	wanted = 0.0
	looted_houses = {}
	kills = {"alchemist": 0, "skeleton": 0, "golem": 0, "defenestrated": 0}
	journal = ["Prague, Anno Domini 1357. The alchemists of the Old Town have raised the dead. Clear the square by night, trade by day."]
	time_of_day = 0.93
	pending_load = {}
	location = "old_town"
	arrive_from = ""
	visited = {}


func max_stamina() -> float:
	var s := base_stamina
	if equipment.get("ring", "") != "":
		s += float(ITEMS[equipment["ring"]].get("stamina", 0))
	return s


func armor() -> float:
	var a := 0.0
	for slot in ["helmet", "armor", "gloves"]:
		var id: String = equipment.get(slot, "")
		if id != "":
			a += float(ITEMS[id].get("armor", 0))
	return a


func block_factor() -> float:
	var id: String = equipment.get("shield", "")
	return float(ITEMS[id].get("block", 0.5)) if id != "" and ITEMS.has(id) else 0.0


func sword() -> Dictionary:
	return SWORDS[sword_level]


func sword_damage() -> float:
	var s := sword()
	return randf_range(s["min"], s["max"])


func add_gold(n: int, quiet := false) -> void:
	gold = max(0, gold + n)
	gold_changed.emit(gold)
	if not quiet and n != 0:
		say(("+%d gold" % n) if n > 0 else ("%d gold" % n), Color(1.0, 0.85, 0.3))


func add_item(id: String, n := 1, quiet := false) -> void:
	inventory[id] = inventory.get(id, 0) + n
	if inventory[id] <= 0:
		inventory.erase(id)
	inventory_changed.emit()
	if not quiet and n > 0:
		say("Received: %s%s" % [ITEMS[id]["name"], (" ×%d" % n) if n > 1 else ""], Color(0.9, 0.85, 0.7))


func count(id: String) -> int:
	return inventory.get(id, 0)


func weight() -> float:
	var w := 0.0
	for id in inventory:
		w += float(ITEMS[id]["weight"]) * inventory[id]
	return w


func say(text: String, color := Color(0.95, 0.9, 0.8)) -> void:
	message.emit(text, color)


func log_journal(text: String) -> void:
	journal.append(text)
	say(text, Color(0.85, 0.75, 0.5))


func use_item(id: String) -> bool:
	if count(id) <= 0:
		return false
	var it: Dictionary = ITEMS[id]
	match id:
		"potion_health":
			hp = min(max_hp, hp + 50.0)
		"potion_stamina":
			stamina = max_stamina()
			vigour_time = 20.0
		"potion_antidote":
			poison_time = 0.0
			say("The poison fades.", Color(0.5, 1.0, 0.5))
		"bread":
			hp = min(max_hp, hp + 10.0)
		"meat":
			hp = min(max_hp, hp + 18.0)
		_:
			if it["type"] == "equip":
				equip(id)
				return true
			return false
	add_item(id, -1, true)
	Sfx.play("drink" if it["type"] == "potion" else "cloth")
	stats_changed.emit()
	return true


func equip(id: String) -> void:
	var slot: String = ITEMS[id]["slot"]
	var old: String = equipment.get(slot, "")
	if old == id:
		return
	if count(id) <= 0:
		return
	add_item(id, -1, true)
	if old != "" and old != "sword":
		add_item(old, 1, true)
	equipment[slot] = id
	stamina = min(stamina, max_stamina())
	Sfx.play("equip")
	say("Equipped: %s" % ITEMS[id]["name"])
	inventory_changed.emit()
	stats_changed.emit()


func unequip(slot: String) -> void:
	var id: String = equipment.get(slot, "")
	if id == "" or slot == "sword":
		return
	equipment[slot] = ""
	add_item(id, 1, true)
	stamina = min(stamina, max_stamina())
	inventory_changed.emit()
	stats_changed.emit()


func set_wanted(seconds: float) -> void:
	var was := wanted > 0.0
	wanted = max(wanted, seconds)
	if not was:
		say("The city guard is after you!", Color(1.0, 0.35, 0.3))
	wanted_changed.emit(wanted)


# ---------------------------------------------------------------- save / load
func has_save() -> bool:
	return FileAccess.file_exists(SAVE_PATH)


func save_game(player_pos: Vector3, player_yaw: float, extra := {}) -> bool:
	var data := {
		"version": 1, "gold": gold, "hp": hp, "stamina": stamina, "sword_level": sword_level, "inventory": inventory,
		"equipment": equipment, "wanted": wanted, "looted": looted_houses, "kills": kills, "journal": journal,
		"time_of_day": time_of_day, "pos": [player_pos.x, player_pos.y, player_pos.z], "yaw": player_yaw,
		"poison": poison_time, "saved_at": Time.get_datetime_string_from_system(), "location": location, "visited": visited,
	}
	data.merge(extra)
	var f := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if f == null:
		say("Could not save the game!", Color(1, 0.3, 0.3))
		return false
	f.store_string(JSON.stringify(data, "\t"))
	f.close()
	say("Game saved.", Color(0.7, 0.9, 1.0))
	return true


func load_game() -> bool:
	if not has_save():
		return false
	var f := FileAccess.open(SAVE_PATH, FileAccess.READ)
	var data = JSON.parse_string(f.get_as_text())
	f.close()
	if typeof(data) != TYPE_DICTIONARY:
		return false
	new_game()
	gold = int(data.get("gold", 30))
	hp = float(data.get("hp", 100))
	stamina = float(data.get("stamina", 100))
	sword_level = int(data.get("sword_level", 0))
	inventory = {}
	for k in data.get("inventory", {}):
		inventory[k] = int(data["inventory"][k])
	equipment = data.get("equipment", equipment)
	wanted = float(data.get("wanted", 0))
	looted_houses = data.get("looted", {})
	kills = data.get("kills", kills)
	journal.assign(data.get("journal", journal))
	time_of_day = float(data.get("time_of_day", 0.93))
	poison_time = float(data.get("poison", 0))
	location = String(data.get("location", "old_town"))
	visited = data.get("visited", {})
	arrive_from = ""
	pending_load = data
	return true


# ---------------------------------------------------------------- settings
func load_settings() -> void:
	var cf := ConfigFile.new()
	if cf.load(SETTINGS_PATH) == OK:
		for k in settings.keys():
			settings[k] = cf.get_value("settings", k, settings[k])


func save_settings() -> void:
	var cf := ConfigFile.new()
	for k in settings.keys():
		cf.set_value("settings", k, settings[k])
	cf.save(SETTINGS_PATH)


func apply_settings() -> void:
	var bus := {"Master": settings["master"], "Music": settings["music"], "SFX": settings["sfx"]}
	for name in bus:
		var idx := AudioServer.get_bus_index(name)
		if idx < 0:
			AudioServer.add_bus()
			idx = AudioServer.bus_count - 1
			AudioServer.set_bus_name(idx, name)
			AudioServer.set_bus_send(idx, "Master")
		AudioServer.set_bus_volume_db(idx, linear_to_db(max(0.0001, float(bus[name]))))
	if not autotest and not OS.has_feature("web") and not OS.has_feature("mobile"):
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN if settings["fullscreen"] else DisplayServer.WINDOW_MODE_WINDOWED)
		DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_ENABLED if settings["vsync"] else DisplayServer.VSYNC_DISABLED)
	get_tree().root.scaling_3d_scale = float(settings["render_scale"])


func icon(id: String) -> Texture2D:
	var path := "res://assets/ui/icons/%s.png" % id
	return load(path) if ResourceLoader.exists(path) else null
