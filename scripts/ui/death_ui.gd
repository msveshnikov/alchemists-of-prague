extends Control
## Death screen (concept: dark red vignette, broken sword, "You have fallen").

var world: Node


func can_close() -> bool:
	return false


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	theme = UiKit.theme()
	var dark := ColorRect.new()
	dark.color = Color(0.08, 0.0, 0.0, 0.55)
	dark.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(dark)
	var vig := TextureRect.new()
	vig.texture = UiKit.tex("vignette_red.png")
	vig.set_anchors_preset(Control.PRESET_FULL_RECT)
	vig.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	vig.stretch_mode = TextureRect.STRETCH_SCALE
	add_child(vig)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 18)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	UiKit.centered(self, v)
	var sw := TextureRect.new()
	sw.texture = Game.icon("sword_%d" % (Game.sword_level + 1))
	sw.custom_minimum_size = Vector2(160, 160)
	sw.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	sw.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	sw.rotation = 1.2
	sw.pivot_offset = Vector2(80, 80)
	sw.modulate = Color(0.7, 0.6, 0.6)
	v.add_child(sw)
	var t := UiKit.title("You have fallen", 84, Color(0.85, 0.15, 0.1))
	t.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 1))
	t.add_theme_constant_override("shadow_offset_x", 3)
	t.add_theme_constant_override("shadow_offset_y", 3)
	v.add_child(t)
	var sub := UiKit.shadow_label("The Old Town claims another knight.", 24)
	sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(sub)
	var lb := UiKit.button("Load Game", func(): world.quickload(), 320)
	lb.disabled = not Game.has_save()
	v.add_child(lb)
	v.add_child(UiKit.button("Main Menu", _to_menu, 320))
	modulate.a = 0.0
	create_tween().tween_property(self, "modulate:a", 1.0, 1.2)
	Sfx.music("", 1.0)


func _to_menu() -> void:
	get_tree().paused = false
	Sfx.stop_ambience()
	get_tree().change_scene_to_file("res://scenes/main_menu.tscn")
