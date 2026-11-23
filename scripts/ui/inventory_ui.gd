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
var quest_list: VBoxContainer
var quest_view: VBoxContainer
var journal_sel := ""
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
	Chars.show_weapon(model, Game.weapon_id())
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


## Journal: quest list (active, then completed) | the selected quest's page | the diary below it.
func _journal_tab(tabs: TabContainer) -> void:
	var h := HBoxContainer.new()
	h.name = "Journal"
	h.add_theme_constant_override("separation", 28)
	tabs.add_child(h)
	var lsc := ScrollContainer.new()
	lsc.custom_minimum_size = Vector2(430, 640)
	lsc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	h.add_child(lsc)
	quest_list = VBoxContainer.new()
	quest_list.custom_minimum_size = Vector2(410, 0)
	quest_list.add_theme_constant_override("separation", 6)
	lsc.add_child(quest_list)
	var rsc := ScrollContainer.new()
	rsc.custom_minimum_size = Vector2(840, 640)
	rsc.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	rsc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	h.add_child(rsc)
	var rv := VBoxContainer.new()
	rv.custom_minimum_size = Vector2(820, 0)
	rv.add_theme_constant_override("separation", 12)
	rsc.add_child(rv)
	quest_view = VBoxContainer.new()
	quest_view.add_theme_constant_override("separation", 10)
	rv.add_child(quest_view)
	journal_box = VBoxContainer.new()
	journal_box.add_theme_constant_override("separation", 8)
	rv.add_child(journal_box)
	journal_sel = Quests.tracked


func _map_tab(tabs: TabContainer) -> void:
	var c := Control.new()
	c.name = "Map"
	tabs.add_child(c)
	var info: Dictionary = world.map_info() if world else {"image": "res://assets/ui/map.png", "rect": Rect2(-110, -107, 230, 230)}
	var area: Rect2 = info["rect"]      # world X/Z covered by the image; image top = north (-Z)
	var img := TextureRect.new()
	img.texture = load(info["image"])
	img.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	img.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	img.set_anchors_preset(Control.PRESET_FULL_RECT)
	c.add_child(img)
	# Where the image actually lands inside the tab (keep-aspect, centred), and world X/Z -> tab pixels.
	var img_box := func() -> Rect2:
		var ts: Vector2 = img.texture.get_size()
		var k: float = min(c.size.x / ts.x, c.size.y / ts.y)
		return Rect2((c.size - ts * k) / 2.0, ts * k)
	var to_px := func(x: float, z: float) -> Vector2:
		var b: Rect2 = img_box.call()
		return b.position + Vector2((x - area.position.x) / area.size.x, (z - area.position.y) / area.size.y) * b.size
	var marks: Array = []      # [label, world x, world z]
	if world:
		for d in world.districts:
			var r: Array = d["rect"]
			var lbl := UiKit.shadow_label(d["name"], 26, UiKit.PARCH)
			c.add_child(lbl)
			marks.append([lbl, (r[0] + r[2]) / 2.0, (r[1] + r[3]) / 2.0])
	var qmarks: Array = []    # [control, world pos]
	for q in Quests.active_quests():
		var tp = Quests.target(q)
		if tp == null:
			continue
		var tracked: bool = q == Quests.tracked
		var qm := Control.new()
		qm.mouse_filter = Control.MOUSE_FILTER_IGNORE
		var r := 13.0 if tracked else 9.0
		qm.draw.connect(func():
			var pts := PackedVector2Array([Vector2(0, -r), Vector2(r, 0), Vector2(0, r), Vector2(-r, 0)])
			qm.draw_colored_polygon(pts, UiKit.GOLD if tracked else Color(0.75, 0.6, 0.35))
			qm.draw_polyline(pts + PackedVector2Array([pts[0]]), Color(0.1, 0.05, 0.02), 2.5, true))
		c.add_child(qm)
		var ql := UiKit.shadow_label(Quests.QUESTS[q]["title"], 20 if tracked else 16, UiKit.GOLD if tracked else UiKit.PARCH)
		c.add_child(ql)
		qmarks.append([qm, ql, tp])
	var seen := {}
	for o in Quests.offered():     # people with work for you: a gold "!" where they stand
		if seen.has(o[1]) or not Quests.npc_home.has(o[1]):
			continue
		seen[o[1]] = true
		var ex := UiKit.shadow_label("!", 30, UiKit.GOLD)
		ex.add_theme_font_override("font", Game.FONT_GOTHIC)
		c.add_child(ex)
		var nl := UiKit.shadow_label(Quests.npc_name(o[1]), 14, UiKit.PARCH)
		c.add_child(nl)
		var hp3: Vector3 = Quests.npc_home[o[1]]
		qmarks.append([ex, nl, hp3])
	var marker: Control = null
	if world and world.player:
		# player arrow: drawn at the exact world position, pointing where the hero faces
		marker = Control.new()
		marker.mouse_filter = Control.MOUSE_FILTER_IGNORE
		marker.draw.connect(func():
			var pts := PackedVector2Array([Vector2(17, 0), Vector2(-10, 11), Vector2(-5, 0), Vector2(-10, -11)])
			marker.draw_circle(Vector2.ZERO, 15.0, Color(0, 0, 0, 0.35))
			marker.draw_colored_polygon(pts, UiKit.BLOOD)
			marker.draw_polyline(pts + PackedVector2Array([pts[0]]), UiKit.PARCH, 2.0, true))
		c.add_child(marker)
	var place := func():
		var me := Vector2(-1e6, -1e6)
		if marker:
			var p: Vector3 = world.player.global_position
			var f: Vector3 = world.player.facing()
			me = to_px.call(p.x, p.z)
			marker.position = me
			marker.rotation = atan2(f.z, f.x)
		for qm in qmarks:
			var qp: Vector2 = to_px.call(qm[2].x, qm[2].z)
			qm[0].position = qp if not (qm[0] is Label) else qp - qm[0].size / 2.0
			qm[1].position = qp + Vector2(-qm[1].size.x / 2.0, 12)
		for mk in marks:
			var ctl: Control = mk[0]
			ctl.position = to_px.call(mk[1], mk[2]) - Vector2(ctl.size.x / 2.0, 16)
			# a district name sitting on top of the hero fades so the arrow stays readable
			ctl.modulate.a = 0.3 if Rect2(ctl.position, ctl.size).grow(14).has_point(me) else 1.0
	c.resized.connect(place)
	c.visibility_changed.connect(place)


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
			icon_id = Game.ITEMS[Game.weapon_id()]["icon"]
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
	if model:
		Chars.show_weapon(model, Game.weapon_id())
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
			var tl := UiKit.title(s["name"], 36)
			tl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
			details.add_child(tl)
			details.add_child(_icon_big(s["icon"]))
			details.add_child(UiKit.label("Damage: %d–%d\nReach: %.1f m · Speed: %d%%\nStamina per swing: %d" % [s["min"], s["max"], s["reach"], int(s["speed"] * 100), s["cost"]], 22))
			details.add_child(UiKit.label(s["desc"], 20, Color(0.25, 0.17, 0.1), true))
			details.add_child(UiKit.label("Buy better weapons from Radim on the square; Havel the smith hones the edge.", 19, UiKit.INK, true))
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
	elif it["type"] in ["equip", "weapon"]:
		details.add_child(UiKit.button("Equip", func(): Game.equip(key), 240))
	if it["type"] != "quest":
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
	if it["type"] == "weapon":
		stats += Game.item_stats(id) + "\n"
	if it["type"] == "quest":
		stats += "Quest item — cannot be sold.\n"
	if it.has("armor"):
		stats += "Armour: +%d\n" % it["armor"]
	if it.has("stamina"):
		stats += "Stamina: +%d\n" % it["stamina"]
	if it.has("block"):
		stats += "Blocks: %d%%\n" % int(it["block"] * 100)
	stats += ("Value: %d gold · " % it["price"] if it["price"] > 0 else "") + "Weight: %.1f" % it["weight"]
	details.add_child(UiKit.label(stats, 21))
	details.add_child(UiKit.label(it["desc"], 20, Color(0.25, 0.17, 0.1), true))


func _refresh_stats() -> void:
	for ch in stats_box.get_children():
		ch.queue_free()
	stats_box.add_child(UiKit.title("Václav of Vyšehrad", 52))
	var lines := [
		"Level %d · Experience %d / %d" % [Game.level, Game.xp, Game.xp_for_next()],
		"Health: %d / %d" % [Game.hp, Game.max_hp],
		"Stamina: %d / %d" % [Game.stamina, Game.max_stamina()],
		"Weapon: %s (%d–%d, reach %.1f m)" % [Game.sword()["name"], Game.sword()["min"], Game.sword()["max"], Game.sword()["reach"]],
		"Armour: %d" % Game.armor(),
		"Shield: blocks %d%% of frontal blows" % int(Game.block_factor() * 100),
		"",
		"Alchemists slain: %d" % Game.kills["alchemist"],
		"Skeletons destroyed: %d" % Game.kills["skeleton"],
		"Golems broken: %d" % Game.kills["golem"],
		"Defenestrations: %d" % Game.kills["defenestrated"],
		"Houses searched: %d" % Game.looted_houses.size(),
		"Quests completed: %d of %d" % [Quests.done_quests().size(), Quests.QUESTS.size()],
	]
	for l in lines:
		stats_box.add_child(UiKit.label(l, 26))


func _refresh_journal() -> void:
	for ch in quest_list.get_children():
		ch.queue_free()
	var act: Array = Quests.active_quests()
	var done: Array = Quests.done_quests()
	if journal_sel == "" or not Quests.state.has(journal_sel):
		journal_sel = Quests.tracked if Quests.tracked != "" else (act[0] if not act.is_empty() else "")
	quest_list.add_child(UiKit.title("Quests", 40))
	quest_list.add_child(UiKit.label("Active", 22, UiKit.BLOOD))
	if act.is_empty():
		quest_list.add_child(UiKit.label("Nothing to do. Talk to people with a  !  over their heads.", 19, UiKit.INK, true))
	for q in act:
		quest_list.add_child(_quest_button(q, false))
	var offers: Array = Quests.offered()
	if not offers.is_empty():
		quest_list.add_child(UiKit.label("They have work for you  !", 22, UiKit.BLOOD))
		for o in offers:
			var place: String = Quests.npc_place(o[1])
			var l := UiKit.label("!  %s%s%s" % [Quests.npc_name(o[1]), (" — " + place) if place != "" else "",
				"  ✠" if Quests.QUESTS[o[0]].get("main", false) else ""], 19, UiKit.INK, true)
			quest_list.add_child(l)
	if not done.is_empty():
		quest_list.add_child(UiKit.label("Completed (%d of %d)" % [done.size(), Quests.QUESTS.size()], 22, UiKit.BLOOD))
		for q in done:
			quest_list.add_child(_quest_button(q, true))
	_refresh_quest_view()
	for ch in journal_box.get_children():
		ch.queue_free()
	journal_box.add_child(UiKit.title("Diary", 34))
	var j := Game.journal.duplicate()
	j.reverse()
	for e in j:
		journal_box.add_child(UiKit.label("• " + e, 19, Color(0.3, 0.22, 0.14), true))


func _quest_button(q: String, done: bool) -> Button:
	var qq: Dictionary = Quests.QUESTS[q]
	var mark := "✓ " if done else ("➤ " if q == Quests.tracked else "")
	var b := Button.new()
	b.text = mark + qq["title"] + ("" if not qq.get("main", false) else "  ✠")
	b.alignment = HORIZONTAL_ALIGNMENT_LEFT
	b.custom_minimum_size = Vector2(400, 46)
	b.add_theme_font_size_override("font_size", 24)
	b.focus_mode = Control.FOCUS_NONE
	if done:
		b.modulate = Color(1, 1, 1, 0.6)
	if q == journal_sel:
		b.add_theme_color_override("font_color", UiKit.BLOOD)
	b.pressed.connect(func(): Sfx.play("paper"); journal_sel = q; _refresh_journal())
	return b


func _refresh_quest_view() -> void:
	for ch in quest_view.get_children():
		ch.queue_free()
	if journal_sel == "" or not Quests.QUESTS.has(journal_sel):
		quest_view.add_child(UiKit.title("Journal", 44))
		quest_view.add_child(UiKit.label("Talk to the people of Prague. A gold  !  over a head means they have work for you; a  ?  means they expect you.", 22, UiKit.INK, true))
		return
	var q := journal_sel
	var qq: Dictionary = Quests.QUESTS[q]
	var t := UiKit.title(qq["title"], 44)
	t.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
	quest_view.add_child(t)
	quest_view.add_child(UiKit.label(("Main story" if qq.get("main", false) else "Side quest") + " · from " + Quests.npc_name(qq["giver"]), 20, UiKit.BLOOD))
	quest_view.add_child(UiKit.label(qq["summary"], 22, UiKit.INK, true))
	var st: Array = qq["stages"]
	var cur: int = Quests.state[q]["stage"]
	for i in st.size():
		if i > cur:
			break
		var done: bool = i < cur or Quests.is_done(q)
		var txt: String = st[i]["text"] if done else Quests.objective(q)
		var l := UiKit.label(("✓  " if done else "➤  ") + txt, 21, Color(0.35, 0.3, 0.22) if done else UiKit.INK, true)
		quest_view.add_child(l)
	var r: Dictionary = qq.get("reward", {})
	var rw: Array = []
	if r.has("gold"):
		rw.append("%d gold" % r["gold"])
	for id in r.get("items", {}):
		rw.append(Game.ITEMS[id]["name"])
	if r.has("max_hp"):
		rw.append("+%d max health" % r["max_hp"])
	if r.has("xp"):
		rw.append("%d experience" % r["xp"])
	quest_view.add_child(UiKit.label("Reward: " + ", ".join(rw), 20, Color(0.35, 0.25, 0.12), true))
	if Quests.is_active(q):
		if q != Quests.tracked:
			quest_view.add_child(UiKit.button("Track on the compass", func(): Quests.set_tracked(q); _refresh_journal(), 360))
		else:
			quest_view.add_child(UiKit.label("➤ Tracked: the gold mark on the compass and the map points the way.", 20, UiKit.BLOOD, true))
	quest_view.add_child(HSeparator.new())
