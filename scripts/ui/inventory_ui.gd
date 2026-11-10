extends Control
## Inventory & equipment (concept/ui/inventory.png): item grid | paper doll | item details; plus Character, Journal, Map tabs.

var world: Node
var grid: GridContainer
var details: VBoxContainer
var doll_slots := {}
var selected := ""
var gold_label: Label
var weight_label: Label
var stats_box: VBoxContainer
var journal_box: VBoxContainer
var model: Node3D


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	theme = UiKit.theme()
	process_mode = Node.PROCESS_MODE_ALWAYS
	UiKit.dim(self, 0.55)
	var p := UiKit.panel(Vector2(1440, 800))
	UiKit.centered(self, p)
	var tabs := TabContainer.new()
	p.add_child(tabs)
	tabs.tab_changed.connect(func(_i): Sfx.play("paper"))
	_inventory_tab(tabs)
	_character_tab(tabs)
	_journal_tab(tabs)
	_map_tab(tabs)
	Game.inventory_changed.connect(_refresh)
	_refresh()
	var close := UiKit.button("Close", func(): world.close_ui(), 180)
	close.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	close.offset_left = -204
	close.offset_right = -24
	close.offset_top = 4
	close.offset_bottom = 48
	close.focus_mode = Control.FOCUS_NONE
	add_child(close)
	if not Game.touch:
		var hint := UiKit.label("Tab · I · Esc — close", 20, UiKit.PARCH)
		hint.set_anchors_preset(Control.PRESET_TOP_RIGHT)
		hint.offset_left = -440
		hint.offset_right = -220
		hint.offset_top = 12
		hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		add_child(hint)


func _inventory_tab(tabs: TabContainer) -> void:
	var h := HBoxContainer.new()
	h.name = "Inventory"
	h.add_theme_constant_override("separation", 26)
	tabs.add_child(h)
	# left: grid
	var left := VBoxContainer.new()
	left.custom_minimum_size = Vector2(430, 0)
	h.add_child(left)
	var sc := ScrollContainer.new()
	sc.custom_minimum_size = Vector2(430, 560)
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	left.add_child(sc)
	grid = GridContainer.new()
	grid.columns = 4
	grid.add_theme_constant_override("h_separation", 8)
	grid.add_theme_constant_override("v_separation", 8)
	sc.add_child(grid)
	var gh := HBoxContainer.new()
	var gi := TextureRect.new()
	gi.texture = Game.icon("gold")
	gi.custom_minimum_size = Vector2(48, 40)
	gi.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	gi.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	gh.add_child(gi)
	gold_label = UiKit.title("0", 36)
	gh.add_child(gold_label)
	left.add_child(gh)
	weight_label = UiKit.label("", 20)
	left.add_child(weight_label)
	# centre: paper doll
	var mid := HBoxContainer.new()
	mid.add_theme_constant_override("separation", 10)
	h.add_child(mid)
	var lc := VBoxContainer.new()
	var rc := VBoxContainer.new()
	for s in ["helmet", "armor", "gloves"]:
		lc.add_child(_doll_slot(s))
	for s in ["sword", "shield", "ring"]:
		rc.add_child(_doll_slot(s))
	mid.add_child(lc)
	mid.add_child(_doll_view())
	mid.add_child(rc)
	# right: details
	details = VBoxContainer.new()
	details.custom_minimum_size = Vector2(380, 0)
	details.add_theme_constant_override("separation", 10)
	h.add_child(details)


func _doll_slot(slot: String) -> Button:
	var id: String = Game.equipment.get(slot, "")
	var b := UiKit.slot("", 0, 104)
	b.tooltip_text = slot.capitalize()
	doll_slots[slot] = b
	b.pressed.connect(func(): _select_slot(slot))
	return b


func _doll_view() -> SubViewportContainer:
	var svc := SubViewportContainer.new()
	svc.custom_minimum_size = Vector2(340, 560)
	svc.stretch = true
	var sv := SubViewport.new()
	sv.own_world_3d = true
	sv.transparent_bg = true
	sv.process_mode = Node.PROCESS_MODE_ALWAYS
	svc.add_child(sv)
	var cam := Camera3D.new()
	cam.position = Vector3(0, 1.05, 3.3)
	cam.fov = 38
	sv.add_child(cam)
	var l := DirectionalLight3D.new()
	l.rotation = Vector3(-0.6, 0.5, 0)
	l.light_energy = 1.4
	sv.add_child(l)
	var env := WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_CLEAR_COLOR
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color(0.75, 0.68, 0.6)
	e.ambient_light_energy = 0.8
	env.environment = e
	sv.add_child(env)
	model = Chars.instance("vaclav")
	model.process_mode = Node.PROCESS_MODE_ALWAYS
	sv.add_child(model)
	var ap := Chars.anim_player(model)
	if ap:
		ap.process_mode = Node.PROCESS_MODE_ALWAYS
		Chars.play(ap, "idle")
	var sm := Chars.find_mesh(model, "WEAPON_sword")
	if sm and world and world.player.sword_mesh:
		sm.material_override = world.player.sword_mesh.material_override
	return svc


func _process(delta: float) -> void:
	if model:
		model.rotation.y += delta * 0.5


func _character_tab(tabs: TabContainer) -> void:
	var m := MarginContainer.new()
	m.name = "Character"
	tabs.add_child(m)
	stats_box = VBoxContainer.new()
	stats_box.add_theme_constant_override("separation", 10)
	m.add_child(stats_box)


func _journal_tab(tabs: TabContainer) -> void:
	var sc := ScrollContainer.new()
	sc.name = "Journal"
	tabs.add_child(sc)
	journal_box = VBoxContainer.new()
	journal_box.custom_minimum_size = Vector2(1300, 0)
	journal_box.add_theme_constant_override("separation", 12)
	sc.add_child(journal_box)


func _map_tab(tabs: TabContainer) -> void:
	var c := Control.new()
	c.name = "Map"
	tabs.add_child(c)
	var info: Dictionary = world.map_info() if world else {"image": "res://assets/ui/map.png", "center": Vector2(5, 8), "size": 230.0}
	var img := TextureRect.new()
	img.texture = load(info["image"])
	img.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	img.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	img.set_anchors_preset(Control.PRESET_FULL_RECT)
	c.add_child(img)
	var marks: Array = []      # [control, u, v]: placed on the square map image whenever the tab resizes
	if world:
		var c0: Vector2 = info["center"]
		for d in world.districts:
			var r: Array = d["rect"]
			var lbl := UiKit.shadow_label(d["name"], 26, UiKit.PARCH)
			c.add_child(lbl)
			marks.append([lbl, ((r[0] + r[2]) / 2.0 - c0.x) / float(info["size"]) + 0.5, ((r[1] + r[3]) / 2.0 - c0.y) / float(info["size"]) + 0.5])
		c.resized.connect(func():
			var s: float = min(c.size.x, c.size.y)
			var ox := (c.size.x - s) / 2.0
			var oy := (c.size.y - s) / 2.0
			for mk in marks:
				var ctl: Control = mk[0]
				ctl.position = Vector2(ox + mk[1] * s - ctl.size.x / 2.0, oy + mk[2] * s - 16))
	if world and world.player:
		var dot := UiKit.title("✚", 40, UiKit.BLOOD)
		c.add_child(dot)
		# map render: square ortho plan of `size` metres centred on `center` (Godot X, Z)
		var p: Vector3 = world.player.global_position
		var mc: Vector2 = info["center"]
		var u := (p.x - mc.x) / float(info["size"]) + 0.5
		var v := (p.z - mc.y) / float(info["size"]) + 0.5
		c.resized.connect(func():
			var s: float = min(c.size.x, c.size.y)
			var ox := (c.size.x - s) / 2.0
			var oy := (c.size.y - s) / 2.0
			dot.position = Vector2(ox + u * s - 14, oy + v * s - 26))


func _refresh() -> void:
	for ch in grid.get_children():
		ch.queue_free()
	var ids := Game.inventory.keys()
	ids.sort_custom(func(a, b): return Game.ITEMS[a]["type"] < Game.ITEMS[b]["type"])
	for id in ids:
		var b := UiKit.slot(id, Game.count(id), 98, Game.ITEMS[id]["name"])
		b.pressed.connect(func(): _select(id))
		grid.add_child(b)
	for i in range(max(0, 20 - ids.size())):
		var e := UiKit.slot("", 0, 98)
		e.disabled = true
		grid.add_child(e)
	for s in doll_slots:
		var b: Button = doll_slots[s]
		for ch in b.get_children():
			ch.queue_free()
		var id: String = Game.equipment.get(s, "")
		var icon_id := ""
		if s == "sword":
			icon_id = "sword_%d" % (Game.sword_level + 1)
		elif id != "":
			icon_id = Game.ITEMS[id]["icon"]
		if icon_id != "":
			var ic := TextureRect.new()
			ic.texture = Game.icon(icon_id)
			ic.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
			ic.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
			ic.set_anchors_preset(Control.PRESET_FULL_RECT)
			ic.offset_left = 12
			ic.offset_top = 12
			ic.offset_right = -12
			ic.offset_bottom = -12
			ic.mouse_filter = Control.MOUSE_FILTER_IGNORE
			b.add_child(ic)
	gold_label.text = str(Game.gold)
	weight_label.text = "Weight: %.1f / 70" % Game.weight()
	_refresh_stats()
	_refresh_journal()
	if selected != "" and (Game.count(selected) > 0 or selected.begins_with("slot:")):
		_show_details(selected)
	else:
		_show_details("")


func _select(id: String) -> void:
	selected = id
	Sfx.play("cloth")
	_show_details(id)


func _select_slot(slot: String) -> void:
	selected = "slot:" + slot
	_show_details(selected)


func _show_details(key: String) -> void:
	for ch in details.get_children():
		ch.queue_free()
	if key == "":
		details.add_child(UiKit.title("Possessions", 40))
		details.add_child(UiKit.label("Select an item to inspect it. Click a potion or food to use it, equipment to wear it.", 20, UiKit.INK, true))
		return
	if key.begins_with("slot:"):
		var slot := key.substr(5)
		if slot == "sword":
			var s: Dictionary = Game.sword()
			details.add_child(UiKit.title(s["name"], 40))
			details.add_child(UiKit.label("One-handed sword", 22))
			details.add_child(_icon_big("sword_%d" % (Game.sword_level + 1)))
			details.add_child(UiKit.label("Damage: %d–%d\nReach: 2.3 m" % [s["min"], s["max"]], 22))
			details.add_child(UiKit.label("The smith on the square can improve it.", 20, UiKit.INK, true))
			return
		var id: String = Game.equipment.get(slot, "")
		if id == "":
			details.add_child(UiKit.title(slot.capitalize(), 40))
			details.add_child(UiKit.label("Nothing equipped.", 22))
			return
		_item_text(id)
		if slot != "shield":
			details.add_child(UiKit.button("Take off", func(): Game.unequip(slot), 240))
		return
	_item_text(key)
	var it: Dictionary = Game.ITEMS[key]
	if it["type"] in ["potion", "food"]:
		details.add_child(UiKit.button("Use", func(): Game.use_item(key), 240))
	elif it["type"] == "equip":
		details.add_child(UiKit.button("Equip", func(): Game.equip(key), 240))
	details.add_child(UiKit.button("Drop", func(): Game.add_item(key, -1, true); Sfx.play("cloth"), 240))


func _icon_big(icon_id: String) -> TextureRect:
	var ic := TextureRect.new()
	ic.texture = Game.icon(icon_id)
	ic.custom_minimum_size = Vector2(200, 200)
	ic.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	ic.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	return ic


func _item_text(id: String) -> void:
	var it: Dictionary = Game.ITEMS[id]
	details.add_child(UiKit.title(it["name"], 38))
	details.add_child(_icon_big(it["icon"]))
	var stats := ""
	if it.has("armor"):
		stats += "Armour: +%d\n" % it["armor"]
	if it.has("stamina"):
		stats += "Stamina: +%d\n" % it["stamina"]
	if it.has("block"):
		stats += "Blocks: %d%%\n" % int(it["block"] * 100)
	stats += "Value: %d gold · Weight: %.1f" % [it["price"], it["weight"]]
	details.add_child(UiKit.label(stats, 21))
	details.add_child(UiKit.label(it["desc"], 20, Color(0.25, 0.17, 0.1), true))


func _refresh_stats() -> void:
	for ch in stats_box.get_children():
		ch.queue_free()
	stats_box.add_child(UiKit.title("Václav of Vyšehrad", 52))
	var lines := [
		"Health: %d / %d" % [Game.hp, Game.max_hp],
		"Stamina: %d / %d" % [Game.stamina, Game.max_stamina()],
		"Weapon: %s (%d–%d)" % [Game.sword()["name"], Game.sword()["min"], Game.sword()["max"]],
		"Armour: %d" % Game.armor(),
		"Shield: blocks %d%% of frontal blows" % int(Game.block_factor() * 100),
		"",
		"Alchemists slain: %d" % Game.kills["alchemist"],
		"Skeletons destroyed: %d" % Game.kills["skeleton"],
		"Golems broken: %d" % Game.kills["golem"],
		"Defenestrations: %d" % Game.kills["defenestrated"],
		"Houses searched: %d" % Game.looted_houses.size(),
	]
	for l in lines:
		stats_box.add_child(UiKit.label(l, 26))


func _refresh_journal() -> void:
	for ch in journal_box.get_children():
		ch.queue_free()
	journal_box.add_child(UiKit.title("Journal", 48))
	var j := Game.journal.duplicate()
	j.reverse()
	for e in j:
		journal_box.add_child(UiKit.label("• " + e, 22, UiKit.INK, true))
