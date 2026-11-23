extends CanvasLayer
## In-game HUD in the style of concept/ui/hud.png.

var world: Node
var hp_bar: TextureProgressBar
var st_bar: TextureProgressBar
var compass: Control
var place_label: Label
var compass_letters: Array = []
var disc: TextureRect
var clock_label: Label
var gold_label: Label
var sword_icon: TextureRect
var potion_counts: Array = []
var prompt: Label
var feed: VBoxContainer
var hint_label: Label
var hint_panel: PanelContainer
var vignette: TextureRect
var poison: ColorRect
var wanted_label: Label
var _hint_t := 0.0
var quest_mark: Label          # gold diamond on the compass strip: bearing to the tracked objective
var tracker: PanelContainer    # tracked quest: title, objective, distance (under the health bars)
var tracker_title: Label
var tracker_text: Label
var tracker_dist: Label
var banner: VBoxContainer      # "New quest" / "Quest complete" announcement under the compass
var banner_title: Label
var banner_text: Label
var _banner_tw: Tween


func _ready() -> void:
	layer = 10
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.theme = UiKit.theme()
	add_child(root)
	vignette = TextureRect.new()
	vignette.texture = UiKit.tex("vignette_red.png")
	vignette.set_anchors_preset(Control.PRESET_FULL_RECT)
	vignette.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	vignette.stretch_mode = TextureRect.STRETCH_SCALE
	vignette.modulate.a = 0.0
	vignette.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(vignette)
	poison = ColorRect.new()
	poison.color = Color(0.2, 0.8, 0.1, 0.0)
	poison.set_anchors_preset(Control.PRESET_FULL_RECT)
	poison.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(poison)
	_bars(root)
	_compass(root)
	_daynight(root)
	_slots(root)
	prompt = UiKit.shadow_label("", 28)
	prompt.add_theme_font_override("font", Game.FONT_GOTHIC)
	prompt.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	prompt.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	prompt.offset_left = -400
	prompt.offset_right = 400
	prompt.offset_top = -230
	prompt.offset_bottom = -190
	root.add_child(prompt)
	feed = VBoxContainer.new()
	feed.set_anchors_preset(Control.PRESET_CENTER_LEFT)
	feed.offset_left = 24
	feed.offset_top = -40
	feed.offset_right = 700
	feed.offset_bottom = 260
	feed.alignment = BoxContainer.ALIGNMENT_END
	feed.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(feed)
	hint_panel = PanelContainer.new()
	var hs := StyleBoxFlat.new()
	hs.bg_color = Color(0.08, 0.06, 0.04, 0.78)
	hs.border_color = UiKit.GOLD
	hs.set_border_width_all(2)
	hs.set_content_margin_all(12)
	hint_panel.add_theme_stylebox_override("panel", hs)
	hint_panel.set_anchors_preset(Control.PRESET_CENTER_TOP)
	hint_panel.offset_left = -370
	hint_panel.offset_right = 370
	hint_panel.offset_top = 205
	hint_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hint_label = UiKit.label("", 22, UiKit.PARCH, true)
	hint_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint_panel.add_child(hint_label)
	hint_panel.visible = false
	root.add_child(hint_panel)
	wanted_label = UiKit.shadow_label("", 26, Color(1, 0.35, 0.3))
	wanted_label.add_theme_font_override("font", Game.FONT_GOTHIC)
	wanted_label.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	wanted_label.offset_left = -420
	wanted_label.offset_right = -30
	wanted_label.offset_top = 250
	wanted_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	root.add_child(wanted_label)
	_tracker(root)
	_banner(root)
	Game.gold_changed.connect(_on_gold)
	Game.inventory_changed.connect(_refresh_slots)
	Game.stats_changed.connect(_refresh_slots)
	_refresh_slots()


func _tracker(root: Control) -> void:
	tracker = PanelContainer.new()
	var st := StyleBoxFlat.new()
	st.bg_color = Color(0.07, 0.05, 0.03, 0.72)
	st.border_color = Color(0.55, 0.42, 0.22, 0.9)
	st.border_width_left = 3
	st.set_content_margin_all(10)
	st.content_margin_left = 14
	tracker.add_theme_stylebox_override("panel", st)
	tracker.position = Vector2(24, 146)
	tracker.custom_minimum_size = Vector2(400, 0)
	tracker.size = Vector2(400, 0)
	tracker.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(tracker)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 2)
	tracker.add_child(v)
	tracker_title = UiKit.shadow_label("", 24, UiKit.GOLD)
	tracker_title.add_theme_font_override("font", Game.FONT_GOTHIC)
	v.add_child(tracker_title)
	tracker_text = UiKit.shadow_label("", 18, UiKit.PARCH)
	tracker_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	tracker_text.custom_minimum_size = Vector2(370, 0)
	v.add_child(tracker_text)
	tracker_dist = UiKit.shadow_label("", 17, Color(0.85, 0.75, 0.5))
	v.add_child(tracker_dist)
	tracker.visible = false
	Quests.changed.connect(_refresh_tracker)
	Game.inventory_changed.connect(_refresh_tracker)
	_refresh_tracker()


func _refresh_tracker() -> void:
	var q := Quests.tracked
	tracker.visible = q != "" and Quests.is_active(q)
	if not tracker.visible:
		return
	tracker_title.text = ("✠ " if Quests.QUESTS[q].get("main", false) else "") + Quests.QUESTS[q]["title"]
	tracker_text.text = Quests.objective(q)
	tracker.size = Vector2(400, 0)


func _banner(root: Control) -> void:
	banner = VBoxContainer.new()
	banner.set_anchors_preset(Control.PRESET_CENTER_TOP)
	banner.offset_left = -500
	banner.offset_right = 500
	banner.offset_top = 80
	banner.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(banner)
	banner_title = UiKit.shadow_label("", 40, UiKit.GOLD)
	banner_title.add_theme_font_override("font", Game.FONT_GOTHIC)
	banner_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	banner.add_child(banner_title)
	banner_text = UiKit.shadow_label("", 21, UiKit.PARCH)
	banner_text.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	banner_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	banner.add_child(banner_text)
	banner.modulate.a = 0.0


## Big announcement under the compass: "New quest: ..." / "Quest complete: ...".
func quest_banner(title: String, text: String) -> void:
	banner_title.text = title
	banner_text.text = text
	if _banner_tw:
		_banner_tw.kill()
	banner.modulate.a = 1.0
	_banner_tw = banner.create_tween()
	_banner_tw.set_pause_mode(Tween.TWEEN_PAUSE_PROCESS)
	_banner_tw.tween_interval(5.0)
	_banner_tw.tween_property(banner, "modulate:a", 0.0, 1.2)
	add_message(title, UiKit.GOLD)


func _bar(parent: Control, icon: String, fill: String, y: float) -> TextureProgressBar:
	var ic := TextureRect.new()
	ic.texture = UiKit.tex(icon)
	ic.position = Vector2(26, y - 6)
	ic.size = Vector2(44, 44)
	ic.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	parent.add_child(ic)
	var frame := NinePatchRect.new()
	frame.texture = UiKit.tex("frame_iron.png")
	frame.patch_margin_left = 34
	frame.patch_margin_right = 34
	frame.patch_margin_top = 34
	frame.patch_margin_bottom = 34
	frame.position = Vector2(72, y - 10)
	frame.size = Vector2(392, 52)
	frame.draw_center = false
	parent.add_child(frame)
	var b := TextureProgressBar.new()
	b.texture_under = UiKit.tex("bar_back.png")
	b.texture_progress = UiKit.tex(fill)
	b.nine_patch_stretch = true
	b.position = Vector2(84, y + 2)
	b.size = Vector2(368, 28)
	b.max_value = 100
	b.value = 100
	parent.add_child(b)
	return b


func _bars(root: Control) -> void:
	hp_bar = _bar(root, "heart.png", "bar_health.png", 26)
	st_bar = _bar(root, "stamina.png", "bar_stamina.png", 80)


func _compass(root: Control) -> void:
	var holder := Control.new()
	holder.set_anchors_preset(Control.PRESET_CENTER_TOP)
	holder.offset_left = -220
	holder.offset_right = 220
	holder.offset_top = 22
	holder.offset_bottom = 74
	root.add_child(holder)
	var frame := NinePatchRect.new()
	frame.texture = UiKit.tex("frame_iron.png")
	frame.patch_margin_left = 34
	frame.patch_margin_right = 34
	frame.patch_margin_top = 34
	frame.patch_margin_bottom = 34
	frame.set_anchors_preset(Control.PRESET_FULL_RECT)
	holder.add_child(frame)
	compass = Control.new()
	compass.clip_contents = true
	compass.set_anchors_preset(Control.PRESET_FULL_RECT)
	compass.offset_left = 30
	compass.offset_right = -30
	holder.add_child(compass)
	for d in [["N", 0.0], ["E", 90.0], ["S", 180.0], ["W", 270.0], ["·", 45.0], ["·", 135.0], ["·", 225.0], ["·", 315.0]]:
		var l := UiKit.shadow_label(d[0], 26 if d[0] != "·" else 22)
		l.add_theme_font_override("font", Game.FONT_GOTHIC)
		l.set_meta("deg", d[1])
		compass.add_child(l)
		compass_letters.append(l)
	quest_mark = UiKit.shadow_label("◆", 30, UiKit.GOLD)
	quest_mark.visible = false
	compass.add_child(quest_mark)
	var needle := UiKit.shadow_label("▼", 16, UiKit.GOLD)
	needle.set_anchors_preset(Control.PRESET_CENTER_TOP)
	needle.offset_top = -14
	needle.offset_left = -8
	holder.add_child(needle)


func _daynight(root: Control) -> void:
	disc = TextureRect.new()
	disc.texture = UiKit.tex("daynight.png")
	disc.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	disc.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	disc.offset_left = -330
	disc.offset_right = -210
	disc.offset_top = 18
	disc.offset_bottom = 138
	disc.pivot_offset = Vector2(60, 60)
	root.add_child(disc)
	var pan := PanelContainer.new()
	var ps := StyleBoxTexture.new()
	ps.texture = UiKit.tex("parchment.png")
	ps.set_content_margin_all(10)
	pan.add_theme_stylebox_override("panel", ps)
	pan.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	pan.offset_left = -205
	pan.offset_right = -24
	pan.offset_top = 30
	pan.offset_bottom = 126
	root.add_child(pan)
	var v := VBoxContainer.new()
	pan.add_child(v)
	var t1 := UiKit.label("Prague", 24, UiKit.INK)
	place_label = t1
	t1.add_theme_font_override("font", Game.FONT_GOTHIC)
	t1.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(t1)
	var t2 := UiKit.label("Prague, 1357", 17, UiKit.INK)
	t2.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(t2)
	clock_label = UiKit.label("Day · 12:00", 20, UiKit.INK)
	clock_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(clock_label)
	var gp := PanelContainer.new()
	var gs := StyleBoxFlat.new()
	gs.bg_color = Color(0.1, 0.08, 0.06, 0.85)
	gs.border_color = Color(0.4, 0.33, 0.24)
	gs.set_border_width_all(2)
	gs.set_content_margin_all(6)
	gp.add_theme_stylebox_override("panel", gs)
	gp.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	gp.offset_left = -205
	gp.offset_right = -24
	gp.offset_top = 140
	gp.offset_bottom = 190
	root.add_child(gp)
	var h := HBoxContainer.new()
	h.alignment = BoxContainer.ALIGNMENT_CENTER
	gp.add_child(h)
	var gi := TextureRect.new()
	gi.texture = Game.icon("gold")
	gi.custom_minimum_size = Vector2(40, 36)
	gi.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	gi.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	h.add_child(gi)
	gold_label = UiKit.shadow_label(str(Game.gold), 30)
	gold_label.add_theme_font_override("font", Game.FONT_GOTHIC)
	h.add_child(gold_label)


func _slots(root: Control) -> void:
	var box := HBoxContainer.new()
	box.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	box.offset_left = 24
	box.offset_top = -150
	box.offset_bottom = -24
	box.add_theme_constant_override("separation", 10)
	box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(box)
	var sw := UiKit.slot("", 0, 126)
	sw.mouse_filter = Control.MOUSE_FILTER_IGNORE
	sword_icon = TextureRect.new()
	sword_icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	sword_icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	sword_icon.set_anchors_preset(Control.PRESET_FULL_RECT)
	sword_icon.offset_left = 12
	sword_icon.offset_top = 12
	sword_icon.offset_right = -12
	sword_icon.offset_bottom = -12
	sw.add_child(sword_icon)
	box.add_child(sw)
	var v := VBoxContainer.new()
	v.alignment = BoxContainer.ALIGNMENT_END
	box.add_child(v)
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 6)
	v.add_child(h)
	for i in 3:
		var id: String = ["potion_health", "potion_stamina", "potion_antidote"][i]
		var s := UiKit.slot(id, 0, 86)
		s.mouse_filter = Control.MOUSE_FILTER_IGNORE
		var key := UiKit.shadow_label(str(i + 1), 18, UiKit.GOLD)
		key.position = Vector2(8, 2)
		s.add_child(key)
		var c := UiKit.shadow_label("0", 22)
		c.position = Vector2(58, 56)
		s.add_child(c)
		potion_counts.append(c)
		h.add_child(s)
	var food := UiKit.slot("bread", 0, 86)
	food.mouse_filter = Control.MOUSE_FILTER_IGNORE
	food.modulate = Color(1, 1, 1, 0.55)
	h.add_child(food)


func _on_gold(g: int) -> void:
	gold_label.text = str(g)


func _refresh_slots() -> void:
	if sword_icon == null:
		return
	sword_icon.texture = Game.icon(Game.ITEMS[Game.weapon_id()]["icon"])
	for i in 3:
		var id: String = ["potion_health", "potion_stamina", "potion_antidote"][i]
		potion_counts[i].text = str(Game.count(id))
	gold_label.text = str(Game.gold)


func set_place(text: String) -> void:
	if place_label:
		place_label.text = {"Old Town Square": "Old Town", "Charles Bridge": "Stone Bridge"}.get(text, text)


func set_prompt(text: String) -> void:
	prompt.text = ((("" if Game.touch else "[E]  ") + text) if text != "" else "")


func add_message(text: String, color := Color(0.95, 0.9, 0.8)) -> void:
	var l := UiKit.shadow_label(text, 21, color)
	feed.add_child(l)
	while feed.get_child_count() > 7:
		feed.get_child(0).queue_free()
		feed.remove_child(feed.get_child(0))
	var tw := l.create_tween()
	tw.tween_interval(6.0)
	tw.tween_property(l, "modulate:a", 0.0, 1.5)
	tw.tween_callback(l.queue_free)


func hint(text: String) -> void:
	hint_label.text = text
	hint_panel.visible = true
	_hint_t = 9.0


func flash_damage(amount: float) -> void:
	vignette.modulate.a = clamp(0.35 + amount / 30.0, 0.0, 1.0)


func _process(delta: float) -> void:
	if world == null or world.player == null:
		return
	hp_bar.value = Game.hp / Game.max_hp * 100.0
	st_bar.value = Game.stamina / Game.max_stamina() * 100.0
	vignette.modulate.a = max(0.0, vignette.modulate.a - delta * 0.8)
	if Game.hp < Game.max_hp * 0.25:
		vignette.modulate.a = max(vignette.modulate.a, 0.35 + 0.15 * sin(Time.get_ticks_msec() * 0.006))
	poison.color.a = 0.12 if Game.poison_time > 0.0 else (0.0)
	var dn: DayNight = world.day_night
	disc.rotation = -dn.frame / 400.0 * TAU + PI * 0.5
	clock_label.text = ("Night · " if dn.is_night else "Day · ") + dn.clock()
	var heading := fmod(rad_to_deg(-world.player.yaw) + 720.0, 360.0)   # 0 = north (-Z)
	var w: float = compass.size.x
	for l in compass_letters:
		var d: float = fposmod(float(l.get_meta("deg")) - heading + 180.0, 360.0) - 180.0
		l.visible = abs(d) < 75.0
		l.position = Vector2(w / 2.0 + d / 75.0 * (w / 2.0) - l.size.x / 2.0, 6)
	wanted_label.text = ("Wanted by the guard: %ds" % int(Game.wanted)) if Game.wanted > 0.0 else ""
	_update_quest_pointer(heading, w)
	if _hint_t > 0.0:
		_hint_t -= delta
		if _hint_t <= 0.0:
			hint_panel.visible = false


## Compass diamond + distance for the tracked quest's objective.
func _update_quest_pointer(heading: float, w: float) -> void:
	var q := Quests.tracked
	var tp = Quests.target(q) if q != "" else null
	quest_mark.visible = false
	if tracker.visible:
		tracker_dist.text = ""
		var ot := Quests.objective(q)      # progress / "by day" can change without a quest event
		if tracker_text.text != ot:
			tracker_text.text = ot
	if tp == null or world.inside_house:
		return
	var to: Vector3 = tp - world.player.global_position
	var dist := Vector2(to.x, to.z).length()
	var bearing := fmod(rad_to_deg(atan2(to.x, -to.z)) + 720.0, 360.0)     # 0 = north (-Z), 90 = east (+X)
	var d: float = fposmod(bearing - heading + 180.0, 360.0) - 180.0
	quest_mark.visible = true
	var edge: bool = abs(d) > 72.0
	quest_mark.text = "◆" if not edge else ("◀" if d < 0.0 else "▶")
	var x: float = w / 2.0 + clamp(d, -72.0, 72.0) / 75.0 * (w / 2.0)
	quest_mark.position = Vector2(x - quest_mark.size.x / 2.0, 2)
	quest_mark.modulate.a = 0.75 + 0.25 * sin(Time.get_ticks_msec() * 0.006) if dist > 6.0 else 1.0
	if tracker.visible:
		var dir := ""
		if abs(d) <= 20.0:
			dir = "ahead"
		elif abs(d) >= 150.0:
			dir = "behind you"
		else:
			dir = "to the left" if d < 0.0 else "to the right"
		tracker_dist.text = ("Here" if dist < 4.0 else "%d m %s" % [int(dist), dir]) + ("" if abs(to.y) < 4.0 else (" · above" if to.y > 0.0 else " · below"))
