extends Control
## Title screen: the concept art (concept/ui/title_screen.png) IS the menu — hit areas sit on its painted
## "New Game / Continue / Settings / Exit" parchment banner.

const IMG := Vector2(1672, 941)
const ITEMS := [  # label, image-space rect (x, y, w, h)
	["new", Rect2(1262, 416, 380, 72)],
	["continue", Rect2(1262, 499, 380, 72)],
	["settings", Rect2(1262, 583, 380, 72)],
	["exit", Rect2(1262, 667, 380, 72)],
]

var bg: TextureRect
var areas := {}


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	theme = UiKit.theme()
	get_tree().paused = false
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	bg = TextureRect.new()
	bg.texture = load("res://assets/ui/title.png")
	bg.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	bg.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	var back := ColorRect.new()
	back.color = Color(0.06, 0.04, 0.03)
	back.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(back)
	add_child(bg)
	for it in ITEMS:
		var b := Button.new()
		b.flat = true
		b.focus_mode = Control.FOCUS_NONE
		var hover := StyleBoxFlat.new()
		hover.bg_color = Color(0.55, 0.08, 0.05, 0.28)
		hover.border_color = Color(0.95, 0.78, 0.35, 0.9)
		hover.set_border_width_all(3)
		hover.set_corner_radius_all(4)
		b.add_theme_stylebox_override("hover", hover)
		b.add_theme_stylebox_override("pressed", hover)
		b.add_theme_stylebox_override("normal", StyleBoxEmpty.new())
		b.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
		b.add_theme_stylebox_override("disabled", StyleBoxEmpty.new())
		b.mouse_entered.connect(func(): Sfx.play("ui", -8.0))
		b.pressed.connect(_on.bind(it[0]))
		add_child(b)
		areas[it[0]] = b
	if not Game.has_save():
		var b: Button = areas["continue"]
		b.disabled = true
		var veil := ColorRect.new()
		veil.color = Color(0.2, 0.15, 0.1, 0.55)
		veil.set_anchors_preset(Control.PRESET_FULL_RECT)
		veil.mouse_filter = Control.MOUSE_FILTER_IGNORE
		b.add_child(veil)
	var credit := UiKit.shadow_label("Prague 1357 — Old Town · Charles Bridge · Malá Strana · Vyšehrad · sounds & fonts: see assets/CREDITS.md", 16, Color(0.85, 0.78, 0.62))
	credit.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	credit.offset_left = 16
	credit.offset_top = -34
	add_child(credit)
	resized.connect(_layout)
	_layout()
	Sfx.music("town_theme", 1.5)
	if Game.autotest:
		await get_tree().create_timer(1.5).timeout
		_on("new")


func _layout() -> void:
	var s: float = min(size.x / IMG.x, size.y / IMG.y)
	var off := (size - IMG * s) / 2.0
	for it in ITEMS:
		var r: Rect2 = it[1]
		var b: Button = areas[it[0]]
		b.position = off + r.position * s
		b.size = r.size * s


func _on(what: String) -> void:
	Sfx.play("ui")
	match what:
		"new":
			Game.new_game()
			get_tree().change_scene_to_file("res://scenes/game.tscn")
		"continue":
			if Game.load_game():
				get_tree().change_scene_to_file("res://scenes/game.tscn")
		"settings":
			var st = load("res://scripts/ui/settings_ui.gd").new()
			st.on_close = func(): st.queue_free()
			add_child(st)
		"exit":
			get_tree().quit()
