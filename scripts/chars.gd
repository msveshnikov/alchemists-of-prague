class_name Chars
extends RefCounted
## Helpers for the character glTFs from Task 2 (face +Z, animations idle/walk/run/attack/hit/death/...).

const LOOPS := ["idle", "walk", "run", "sprint", "block", "talk", "beg", "work", "flail", "pull", "cast", "spar", "pray"]

static var _scenes := {}
static var _looped := {}


static func instance(character: String) -> Node3D:
	if not _scenes.has(character):
		_scenes[character] = load("res://assets/characters/%s.gltf" % character)
	var n: Node3D = _scenes[character].instantiate()
	var ap := anim_player(n)
	if ap and not _looped.has(character):
		_looped[character] = true
		for a in ap.get_animation_list():
			if a in LOOPS:
				ap.get_animation(a).loop_mode = Animation.LOOP_LINEAR
	return n


static func anim_player(n: Node) -> AnimationPlayer:
	var list := n.find_children("*", "AnimationPlayer", true, false)
	return list[0] if list.size() > 0 else null


static func find_mesh(n: Node, name_prefix: String) -> MeshInstance3D:
	for m in n.find_children(name_prefix + "*", "MeshInstance3D", true, false):
		return m
	return null


static func play(ap: AnimationPlayer, anim: String, blend := 0.18, speed := 1.0, restart := false) -> void:
	if ap == null or not ap.has_animation(anim):
		return
	if ap.current_animation == anim and not restart:
		ap.speed_scale = speed
		return
	ap.play(anim, blend)
	ap.speed_scale = speed
	if restart:
		ap.seek(0.0, true)


static func length(ap: AnimationPlayer, anim: String) -> float:
	return ap.get_animation(anim).length if ap and ap.has_animation(anim) else 1.0


## Billboard health bar (two quads) parented above a character.
static func health_bar(parent: Node3D, height: float, width := 0.8) -> MeshInstance3D:
	var root := Node3D.new()
	root.name = "HealthBar"
	parent.add_child(root)
	root.position = Vector3(0, height, 0)
	var back := MeshInstance3D.new()
	var qm := QuadMesh.new()
	qm.size = Vector2(width + 0.06, 0.12)
	back.mesh = qm
	var bm := StandardMaterial3D.new()
	bm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	bm.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	bm.albedo_color = Color(0.05, 0.03, 0.02, 0.85)
	bm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	bm.no_depth_test = true
	bm.render_priority = 1
	back.material_override = bm
	root.add_child(back)
	var fill := MeshInstance3D.new()
	var fq := QuadMesh.new()
	fq.size = Vector2(width, 0.08)
	fill.mesh = fq
	var fm := StandardMaterial3D.new()
	fm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	fm.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	fm.albedo_color = Color(0.75, 0.1, 0.06)
	fm.no_depth_test = true
	fm.render_priority = 2
	fill.material_override = fm
	fill.set_meta("width", width)
	root.add_child(fill)
	root.visible = false
	set_bar(fill, 1.0)
	return fill


static func set_bar(fill: MeshInstance3D, ratio: float) -> void:
	if fill == null:
		return
	var w: float = fill.get_meta("width", 0.8)
	var r: float = clamp(ratio, 0.0, 1.0)
	var q: QuadMesh = fill.mesh
	q.size = Vector2(max(0.001, w * r), 0.08)
	q.center_offset = Vector3(-w / 2.0 + w * r / 2.0, 0, 0.002)
	fill.get_parent().visible = r < 0.999 and r > 0.0
