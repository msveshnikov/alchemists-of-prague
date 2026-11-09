extends Control
## Settings: Graphics, Sound, Controls, Gameplay (concept: parchment panel, slider rows, wax-seal checkboxes).

var world: Node = null      # set when opened in-game
var on_close: Callable


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	theme = UiKit.theme()
	UiKit.dim(self, 0.6)
	var p := UiKit.panel(Vector2(900, 640))
	UiKit.centered(self, p)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 10)
	p.add_child(v)
	v.add_child(UiKit.title("Settings", 52))
	var tabs := TabContainer.new()
	tabs.custom_minimum_size = Vector2(820, 430)
	v.add_child(tabs)
	var g := _page(tabs, "Graphics")
	_check(g, "Fullscreen", "fullscreen")
	_check(g, "Vertical sync", "vsync")
	_check(g, "Sun shadows", "shadows")
	_check(g, "Ambient occlusion (SSAO)", "ssao")
	_check(g, "Glow of fires and windows", "glow")
	_slider(g, "Render scale", "render_scale", 0.5, 1.0, 0.05)
	var s := _page(tabs, "Sound")
	_slider(s, "Master volume", "master", 0.0, 1.0, 0.05)
	_slider(s, "Music", "music", 0.0, 1.0, 0.05)
	_slider(s, "Effects", "sfx", 0.0, 1.0, 0.05)
	var c := _page(tabs, "Controls")
	_slider(c, "Mouse sensitivity", "mouse_sens", 0.05, 0.6, 0.01)
	_check(c, "Invert mouse Y", "invert_y")
	var keys := UiKit.label("W A S D — move      Shift — sprint      Caps Lock — walk / run\nSpace — jump      Q / Alt — dodge\n" +
		"Left mouse — strike (click again to chain)      Right mouse — block with the shield\n" +
		"E / F — interact · seize a reeling enemy · throw him (by a window!)\n1 / 2 / 3 — healing, vigour, antidote      Tab / I — inventory\n" +
		"T — wait until dusk / dawn      F5 — quick save      F9 — quick load      Esc — pause", 19, UiKit.INK, true)
	c.add_child(keys)
	var gp := _page(tabs, "Gameplay")
	_slider(gp, "Length of a day (minutes)", "day_minutes", 6.0, 40.0, 1.0)
	_slider(gp, "Damage taken (difficulty)", "difficulty", 0.5, 1.5, 0.1)
	var row := HBoxContainer.new()
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_child(UiKit.button("Back", _close))
	v.add_child(row)


func _page(tabs: TabContainer, name: String) -> VBoxContainer:
	var m := MarginContainer.new()
	m.name = name
	m.add_theme_constant_override("margin_left", 20)
	m.add_theme_constant_override("margin_top", 16)
	m.add_theme_constant_override("margin_right", 20)
	tabs.add_child(m)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 14)
	m.add_child(v)
	return v


func _check(parent: Control, text: String, key: String) -> void:
	var cb := CheckBox.new()
	cb.text = "  " + text
	cb.button_pressed = bool(Game.settings[key])
	cb.add_theme_font_size_override("font_size", 24)
	cb.toggled.connect(func(on): Game.settings[key] = on; _apply())
	parent.add_child(cb)


func _slider(parent: Control, text: String, key: String, lo: float, hi: float, step: float) -> void:
	var h := HBoxContainer.new()
	var l := UiKit.label(text, 22)
	l.custom_minimum_size = Vector2(340, 0)
	h.add_child(l)
	var s := HSlider.new()
	s.min_value = lo
	s.max_value = hi
	s.step = step
	s.value = float(Game.settings[key])
	s.custom_minimum_size = Vector2(320, 30)
	h.add_child(s)
	var val := UiKit.label("%.2f" % s.value, 20)
	h.add_child(val)
	s.value_changed.connect(func(x): Game.settings[key] = x; val.text = "%.2f" % x; _apply())
	parent.add_child(h)


func _apply() -> void:
	Game.apply_settings()
	if world and world.env:
		world.env.ssao_enabled = bool(Game.settings["ssao"])
		world.env.glow_enabled = bool(Game.settings["glow"])
		world.day_night.sun.shadow_enabled = bool(Game.settings["shadows"])


func _close() -> void:
	Game.save_settings()
	if world:
		world.close_ui()
	elif on_close.is_valid():
		on_close.call()
	else:
		queue_free()
