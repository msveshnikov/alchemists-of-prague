extends Control
## Conversation with a named NPC, Gothic style: the lines play one by one at the bottom of the screen (click / E /
## Space / Enter to go on), then the topics are listed — pick one with the mouse, a tap, or the keys 1–9.
## Topics come from Quests.topics(): quest steps, new quests ("!"), reminders, small talk; plus trade / smith / bed.

var world: Node
var npc: Node                  # the Npc we talk to
var npc_id := ""
var panel: PanelContainer
var portrait: TextureRect
var speaker: Label
var text: Label
var hint: Label
var options: VBoxContainer
var queue: Array = []          # lines still to show
var after: Callable            # run when the queue is empty
var choices: Array = []
var _lines_mode := false


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	theme = UiKit.theme()
	process_mode = Node.PROCESS_MODE_ALWAYS
	var shade := ColorRect.new()
	shade.color = Color(0, 0, 0, 0.0)
	shade.set_anchors_preset(Control.PRESET_FULL_RECT)
	shade.mouse_filter = Control.MOUSE_FILTER_STOP
	shade.gui_input.connect(_on_click)
	add_child(shade)
	var grad := TextureRect.new()      # darken the lower part of the screen so the text reads over any scene
	var gt := GradientTexture2D.new()
	var g := Gradient.new()
	g.set_color(0, Color(0, 0, 0, 0))
	g.set_color(1, Color(0, 0, 0, 0.75))
	gt.gradient = g
	gt.fill_from = Vector2(0, 0)
	gt.fill_to = Vector2(0, 1)
	grad.texture = gt
	grad.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	grad.offset_top = -470
	grad.mouse_filter = Control.MOUSE_FILTER_IGNORE
	grad.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	add_child(grad)
	panel = PanelContainer.new()
	var st := StyleBoxFlat.new()
	st.bg_color = Color(0.06, 0.045, 0.03, 0.88)
	st.border_color = Color(0.6, 0.46, 0.24)
	st.set_border_width_all(2)
	st.set_corner_radius_all(4)
	st.set_content_margin_all(18)
	panel.add_theme_stylebox_override("panel", st)
	panel.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	panel.grow_vertical = Control.GROW_DIRECTION_BEGIN
	panel.offset_left = -640
	panel.offset_right = 640
	panel.offset_bottom = -24
	panel.mouse_filter = Control.MOUSE_FILTER_PASS
	panel.gui_input.connect(_on_click)
	add_child(panel)
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 20)
	panel.add_child(h)
	portrait = TextureRect.new()
	portrait.custom_minimum_size = Vector2(170, 230)
	portrait.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	portrait.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	portrait.mouse_filter = Control.MOUSE_FILTER_IGNORE
	h.add_child(portrait)
	var v := VBoxContainer.new()
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	v.add_theme_constant_override("separation", 8)
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	h.add_child(v)
	speaker = UiKit.shadow_label("", 30, UiKit.GOLD)
	speaker.add_theme_font_override("font", Game.FONT_GOTHIC)
	v.add_child(speaker)
	text = UiKit.shadow_label("", 25, UiKit.PARCH)
	text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	text.custom_minimum_size = Vector2(1000, 0)
	v.add_child(text)
	options = VBoxContainer.new()
	options.add_theme_constant_override("separation", 2)
	v.add_child(options)
	hint = UiKit.shadow_label("", 17, Color(0.7, 0.62, 0.45))
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	v.add_child(hint)
	var d: Dictionary = Quests.NPCS.get(npc_id, {})
	var ch: String = d.get("character", "")
	var pp := "res://assets/ui/portraits/%s.png" % ch
	portrait.texture = load(pp) if ResourceLoader.exists(pp) else null
	portrait.visible = portrait.texture != null
	if is_instance_valid(npc) and npc.has_method("face_player"):
		npc.face_player()
	Sfx.play("paper")
	_play([d.get("greet", "...")], _show_choices)


# ---------------------------------------------------------------- lines
func _play(lines: Array, then: Callable) -> void:
	queue = lines.duplicate()
	after = then
	_lines_mode = true
	_next()


func _next() -> void:
	if queue.is_empty():
		_lines_mode = false
		if after.is_valid():
			var cb := after
			after = Callable()
			cb.call()
		return
	var line: String = queue.pop_front()
	for c in options.get_children():
		c.queue_free()
	if line.begins_with("V:"):
		speaker.text = "Václav"
		speaker.add_theme_color_override("font_color", Color(0.75, 0.82, 0.95))
		text.text = line.substr(2).strip_edges()
		text.add_theme_color_override("font_color", Color(0.85, 0.9, 1.0))
	elif line.begins_with("*"):
		speaker.text = ""
		text.text = line.substr(1).strip_edges()
		text.add_theme_color_override("font_color", UiKit.GOLD)
	else:
		speaker.text = Quests.npc_name(npc_id)
		speaker.add_theme_color_override("font_color", UiKit.GOLD)
		text.text = line
		text.add_theme_color_override("font_color", UiKit.PARCH)
	hint.text = "Tap to continue" if Game.touch else "Click · E · Space — continue"


# ---------------------------------------------------------------- topics
func _show_choices() -> void:
	for c in options.get_children():
		c.queue_free()
	choices = Quests.topics(npc_id)
	var role: String = npc.role if is_instance_valid(npc) else ""
	if role.begins_with("trader") or role == "innkeeper":
		choices.append({"text": "Show me your wares.", "kind": "trade"})
	if role == "innkeeper":
		choices.append({"text": "I need a bed for the night (10 gold).", "kind": "inn"})
	if npc_id == "havel":
		choices.append({"text": "Hone my weapon.", "kind": "smith"})
	choices.append({"text": "Farewell.", "kind": "bye"})
	var i := 0
	for c in choices:
		i += 1
		var b := Button.new()
		var mark: String = {"new": "!  ", "quest": "?  "}.get(c["kind"], "")
		b.text = "%d.  %s%s" % [i, mark, c["text"]]
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.flat = true
		b.focus_mode = Control.FOCUS_NONE
		b.add_theme_font_override("font", Game.FONT_BODY)
		b.add_theme_font_size_override("font_size", 24)
		var col: Color = {"new": UiKit.GOLD, "quest": Color(1.0, 0.8, 0.45)}.get(c["kind"], UiKit.PARCH)
		b.add_theme_color_override("font_color", col)
		b.add_theme_color_override("font_hover_color", Color(1, 1, 1))
		b.add_theme_color_override("font_pressed_color", Color(1, 1, 1))
		b.mouse_entered.connect(func(): b.add_theme_color_override("font_color", Color(1, 1, 1)))
		b.mouse_exited.connect(func(): b.add_theme_color_override("font_color", col))
		b.pressed.connect(_choose.bind(i - 1))
		options.add_child(b)
	hint.text = "Choose a topic" if Game.touch else "Choose: click or 1–%d · Esc — leave" % min(9, choices.size())


func _choose(i: int) -> void:
	if _lines_mode or i < 0 or i >= choices.size():
		return
	var c: Dictionary = choices[i]
	Sfx.play("ui")
	match c["kind"]:
		"bye":
			world.close_ui()
		"trade":
			world.close_ui()
			world.open_trade(npc.entry.get("stall", "") if is_instance_valid(npc) else "", "tavern" if npc.role == "innkeeper" else npc.role.replace("trader_", ""))
		"smith":
			world.close_ui()
			world.open_ui(load("res://scripts/ui/smith_ui.gd").new())
		"inn":
			world.close_ui()
			world._rent_bed()
		_:
			var act = c.get("act")
			_play(["V: " + c["text"]] + c.get("lines", []), func():
				if act is Callable and act.is_valid():
					act.call()
				_show_choices())


# ---------------------------------------------------------------- input
func _on_click(ev: InputEvent) -> void:
	if _lines_mode and ev is InputEventMouseButton and ev.pressed and ev.button_index == MOUSE_BUTTON_LEFT:
		accept_event()
		_next()


func _input(ev: InputEvent) -> void:
	if not (ev is InputEventKey) or not ev.pressed or ev.echo:
		return
	if _lines_mode:
		if ev.is_action_pressed("interact") or ev.physical_keycode in [KEY_SPACE, KEY_ENTER, KEY_KP_ENTER]:
			get_viewport().set_input_as_handled()
			_next()
		return
	var k: int = ev.physical_keycode
	if k >= KEY_1 and k <= KEY_9:
		get_viewport().set_input_as_handled()
		_choose(k - KEY_1)
