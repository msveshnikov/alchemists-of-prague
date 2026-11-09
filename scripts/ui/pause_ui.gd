extends Control
## Pause menu (Esc).

var world: Node


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	theme = UiKit.theme()
	UiKit.dim(self, 0.6)
	var p := UiKit.panel(Vector2(460, 560))
	UiKit.centered(self, p)
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", 12)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	p.add_child(v)
	v.add_child(UiKit.title("Paused", 56))
	v.add_child(UiKit.button("Resume", func(): world.close_ui()))
	v.add_child(UiKit.button("Save Game", func(): world.quicksave()))
	var lb := UiKit.button("Load Game", func(): world.quickload())
	lb.disabled = not Game.has_save()
	v.add_child(lb)
	v.add_child(UiKit.button("Settings", func(): world.open_ui(load("res://scripts/ui/settings_ui.gd").new())))
	v.add_child(UiKit.button("Main Menu", _to_menu))
	v.add_child(UiKit.button("Quit", func(): get_tree().quit()))
	var stats := UiKit.label("Slain — alchemists %d · skeletons %d · golems %d · defenestrated %d" % [
		Game.kills["alchemist"], Game.kills["skeleton"], Game.kills["golem"], Game.kills["defenestrated"]], 18, UiKit.INK, true)
	stats.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(stats)


func _to_menu() -> void:
	get_tree().paused = false
	Sfx.stop_ambience()
	get_tree().change_scene_to_file("res://scenes/main_menu.tscn")
