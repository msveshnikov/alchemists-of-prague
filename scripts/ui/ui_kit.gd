class_name UiKit
extends RefCounted
## Builders for the medieval-manuscript UI: parchment panels in dark wood + iron frames, Gothic headings.

const INK := Color(0.16, 0.1, 0.06)
const GOLD := Color(0.86, 0.68, 0.32)
const PARCH := Color(0.93, 0.86, 0.7)
const BLOOD := Color(0.55, 0.08, 0.06)

static var _theme: Theme


static func tex(path: String) -> Texture2D:
	return load("res://assets/ui/" + path)


static func theme() -> Theme:
	if _theme:
		return _theme
	var t := Theme.new()
	t.default_font = Game.FONT_BODY
	t.default_font_size = 22
	var btn := StyleBoxTexture.new()
	btn.texture = tex("button.png")
	btn.content_margin_left = 18
	btn.content_margin_right = 18
	btn.content_margin_top = 6
	btn.content_margin_bottom = 6
	var hov := btn.duplicate()
	hov.texture = tex("button_hover.png")
	var dis := btn.duplicate()
	dis.modulate_color = Color(0.6, 0.6, 0.6, 0.8)
	t.set_stylebox("normal", "Button", btn)
	t.set_stylebox("hover", "Button", hov)
	t.set_stylebox("pressed", "Button", hov)
	t.set_stylebox("focus", "Button", StyleBoxEmpty.new())
	t.set_stylebox("disabled", "Button", dis)
	t.set_color("font_color", "Button", INK)
	t.set_color("font_hover_color", "Button", PARCH)
	t.set_color("font_pressed_color", "Button", PARCH)
	t.set_color("font_disabled_color", "Button", Color(0.3, 0.25, 0.2))
	t.set_font("font", "Button", Game.FONT_GOTHIC)
	t.set_font_size("font_size", "Button", 28)
	t.set_color("font_color", "Label", INK)
	var panel := StyleBoxTexture.new()
	panel.texture = tex("panel_parchment.png")
	panel.texture_margin_left = 34
	panel.texture_margin_right = 34
	panel.texture_margin_top = 34
	panel.texture_margin_bottom = 34
	panel.content_margin_left = 40
	panel.content_margin_right = 40
	panel.content_margin_top = 36
	panel.content_margin_bottom = 36
	t.set_stylebox("panel", "PanelContainer", panel)
	t.set_stylebox("panel", "Panel", panel)
	var sl := StyleBoxFlat.new()
	sl.bg_color = Color(0.25, 0.18, 0.12)
	sl.content_margin_top = 4
	sl.content_margin_bottom = 4
	t.set_stylebox("slider", "HSlider", sl)
	var grab := StyleBoxFlat.new()
	grab.bg_color = Color(0.55, 0.42, 0.25)
	t.set_stylebox("grabber_area", "HSlider", grab)
	t.set_stylebox("grabber_area_highlight", "HSlider", grab)
	t.set_color("font_color", "CheckBox", INK)
	t.set_color("font_hover_color", "CheckBox", BLOOD)
	t.set_color("font_pressed_color", "CheckBox", INK)
	t.set_color("font_hover_pressed_color", "CheckBox", BLOOD)
	t.set_color("font_color", "TabBar", Color(0.85, 0.75, 0.55))
	t.set_color("font_selected_color", "TabBar", PARCH)
	t.set_color("font_hovered_color", "TabBar", Color(1, 0.9, 0.7))
	t.set_font("font", "TabBar", Game.FONT_GOTHIC)
	t.set_font_size("font_size", "TabBar", 26)
	var tab_sel := StyleBoxFlat.new()
	tab_sel.bg_color = BLOOD
	tab_sel.set_content_margin_all(10)
	tab_sel.border_color = GOLD
	tab_sel.set_border_width_all(2)
	var tab_un := StyleBoxFlat.new()
	tab_un.bg_color = Color(0.17, 0.12, 0.08)
	tab_un.set_content_margin_all(10)
	tab_un.border_color = Color(0.35, 0.28, 0.2)
	tab_un.set_border_width_all(2)
	t.set_stylebox("tab_selected", "TabContainer", tab_sel)
	t.set_stylebox("tab_unselected", "TabContainer", tab_un)
	t.set_stylebox("tab_hovered", "TabContainer", tab_un)
	t.set_stylebox("panel", "TabContainer", StyleBoxEmpty.new())
	t.set_color("font_selected_color", "TabContainer", PARCH)
	t.set_color("font_unselected_color", "TabContainer", Color(0.8, 0.7, 0.5))
	t.set_color("font_hovered_color", "TabContainer", Color(1, 0.9, 0.7))
	t.set_font("font", "TabContainer", Game.FONT_GOTHIC)
	t.set_font_size("font_size", "TabContainer", 26)
	var tip := StyleBoxFlat.new()
	tip.bg_color = Color(0.12, 0.09, 0.06, 0.95)
	tip.border_color = GOLD
	tip.set_border_width_all(1)
	tip.set_content_margin_all(8)
	t.set_stylebox("panel", "TooltipPanel", tip)
	t.set_color("font_color", "TooltipLabel", PARCH)
	_theme = t
	return t


static func title(text: String, size := 44, color := INK) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_override("font", Game.FONT_GOTHIC)
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	return l


static func label(text: String, size := 22, color := INK, wrap := false) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	if wrap:
		l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	return l


static func shadow_label(text: String, size := 22, color := PARCH) -> Label:
	var l := label(text, size, color)
	l.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.85))
	l.add_theme_constant_override("shadow_offset_x", 2)
	l.add_theme_constant_override("shadow_offset_y", 2)
	l.add_theme_constant_override("outline_size", 4)
	l.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.6))
	return l


static func button(text: String, cb: Callable, min_w := 260) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(min_w, 54)
	b.pressed.connect(func(): Sfx.play("ui"); cb.call())
	return b


static func panel(min_size := Vector2(600, 400)) -> PanelContainer:
	var p := PanelContainer.new()
	p.theme = theme()
	p.custom_minimum_size = min_size
	return p


static func dim(parent: Control, alpha := 0.55) -> ColorRect:
	var c := ColorRect.new()
	c.color = Color(0.03, 0.02, 0.01, alpha)
	c.set_anchors_preset(Control.PRESET_FULL_RECT)
	c.mouse_filter = Control.MOUSE_FILTER_STOP
	parent.add_child(c)
	return c


static func centered(parent: Control, child: Control) -> Control:
	## Anchor the child to the centre of the parent; it grows both ways as its content grows.
	parent.add_child(child)
	child.grow_horizontal = Control.GROW_DIRECTION_BOTH
	child.grow_vertical = Control.GROW_DIRECTION_BOTH
	child.set_anchors_and_offsets_preset(Control.PRESET_CENTER, Control.PRESET_MODE_MINSIZE)
	return child


## Item slot: framed icon with count badge. Returns the Button so callers can connect.
static func slot(id: String, count_: int, size := 84, tip := "") -> Button:
	var b := Button.new()
	b.custom_minimum_size = Vector2(size, size)
	b.flat = true
	var st := StyleBoxTexture.new()
	st.texture = tex("slot.png")
	st.texture_margin_left = 12
	st.texture_margin_right = 12
	st.texture_margin_top = 12
	st.texture_margin_bottom = 12
	b.add_theme_stylebox_override("normal", st)
	var sh := st.duplicate()
	sh.modulate_color = Color(1.25, 1.1, 0.9)
	b.add_theme_stylebox_override("hover", sh)
	b.add_theme_stylebox_override("pressed", sh)
	b.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
	if id != "":
		var ic := TextureRect.new()
		ic.texture = Game.icon(Game.ITEMS[id]["icon"]) if Game.ITEMS.has(id) else Game.icon(id)
		ic.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		ic.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		ic.set_anchors_preset(Control.PRESET_FULL_RECT)
		ic.offset_left = 10
		ic.offset_top = 10
		ic.offset_right = -10
		ic.offset_bottom = -10
		ic.mouse_filter = Control.MOUSE_FILTER_IGNORE
		b.add_child(ic)
	if count_ > 1:
		var c := shadow_label(str(count_), 20)
		c.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
		c.offset_left = -30
		c.offset_top = -30
		c.offset_right = -8
		c.offset_bottom = -4
		c.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		c.mouse_filter = Control.MOUSE_FILTER_IGNORE
		b.add_child(c)
	b.tooltip_text = tip
	return b
