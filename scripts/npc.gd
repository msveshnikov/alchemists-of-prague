extends CharacterBody3D
class_name Npc
## Townsfolk from old_town_population.json: traders, cook, smith, beggars, crowd, wanderers, horses.
## Attacking them makes them flee and calls the city guard.

const LINES := [
	"God keep you, sir knight.", "The bread is fresh today — fresh as last week.", "They say the dead walk by the Tyn church at night.",
	"Mind your purse in the crowd.", "The alchemists pay well for bones. Too well.", "The clock on the town hall has not lied in thirty years.",
	"Stay off the streets after dark, if you value your skin.", "My cousin saw a clay giant on Celetna. Nobody believes him.",
	"Buy something or move along!", "A copper for a poor soul?", "The guards are no use against what comes at night.",
]

var world: Node
var entry: Dictionary
var character := ""
var role := ""
var model: Node3D
var ap: AnimationPlayer
var anim := "idle"
var home := Vector3.ZERO
var home_yaw := 0.0
var route: Array = []
var route_i := 0
var route_dir := 1
var ping_pong := false
var speed := 1.0
var hp := 30.0
var dead := false
var flee_t := 0.0
var talk_t := 0.0
var cart: Node3D
var trot: AudioStreamPlayer3D
var schedule := "day"


func setup(p_world: Node, e: Dictionary) -> void:
	world = p_world
	entry = e
	character = e["character"]
	role = e.get("role", "")
	schedule = e.get("schedule", "day")
	anim = e.get("animation", "idle")
	var p: Array = e["pos"]
	home = Vector3(p[0], p[1], p[2])
	home_yaw = deg_to_rad(float(e.get("yaw_deg", 0.0)))
	position = home
	collision_layer = 4
	collision_mask = 1 | 2
	var cs := CollisionShape3D.new()
	if character == "horse":
		var bx := BoxShape3D.new()
		bx.size = Vector3(0.8, 1.6, 2.2)
		cs.shape = bx
		cs.position.y = 1.0
	else:
		var cap := CapsuleShape3D.new()
		cap.radius = 0.3
		cap.height = 1.7 if not character.begins_with("child") else 1.25
		cs.shape = cap
		cs.position.y = cap.height / 2.0
	add_child(cs)
	model = Chars.instance(character)
	add_child(model)
	model.rotation.y = home_yaw
	ap = Chars.anim_player(model)
	Chars.play(ap, anim)
	if ap and ap.has_animation(anim):
		ap.seek(randf() * Chars.length(ap, anim), true)
	speed = float(e.get("speed_mps", 1.0))
	if anim == "run":
		speed = 1.9
	for key in ["route", "route_points"]:
		if e.has(key):
			for r in e[key]:
				if r is String:
					var m: Dictionary = world.marker(r)
					if not m.is_empty():
						route.append(Vector3(m["pos"][0], m["pos"][1], m["pos"][2]))
				else:
					route.append(Vector3(r[0], r[1], r[2]))
	if role == "cart_driver":
		ping_pong = true
		var cs2: PackedScene = load("res://assets/props/cart.gltf")
		cart = cs2.instantiate()
		world.add_child(cart)
		trot = Sfx.loop_at("horse_trot", self, -4.0, 5.0)
	if role == "carter":
		ping_pong = true


func is_dead() -> bool:
	return dead


func radius() -> float:
	return 0.3 if character != "horse" else 0.9


func display_name() -> String:
	return {"market_woman": "market woman", "child_boy": "boy", "child_girl": "girl"}.get(character, character)


func can_be_grabbed() -> bool:
	return false


func take_hit(dmg: float, _attacker: Node) -> void:
	if dead:
		return
	hp -= dmg
	Sfx.play_at("hurt", global_position + Vector3(0, 1.4, 0), -2.0, 1.25 if character in ["market_woman", "child_girl", "child_boy"] else 1.0)
	if hp <= 0.0:
		dead = true
		collision_layer = 0
		Chars.play(ap, "death", 0.1)
		Game.set_wanted(240.0)
		Game.say("Murder! The whole town will hunt you.", Color(1, 0.25, 0.2))
		return
	flee_t = 6.0
	Game.set_wanted(90.0)


func talk() -> void:
	talk_t = 3.0
	var line: String = LINES[randi() % LINES.size()]
	if role.begins_with("npc_beggar") or character == "beggar":
		line = "Alms for the poor, noble sir... A single groschen?"
	Game.say("%s: \"%s\"" % [display_name().capitalize(), line], Color(0.95, 0.88, 0.7))
	var to: Vector3 = world.player.global_position - global_position
	model.rotation.y = atan2(to.x, to.z)
	Chars.play(ap, "talk" if ap.has_animation("talk") else "idle", 0.2)


func _physics_process(delta: float) -> void:
	if dead:
		return
	if not is_on_floor():
		velocity.y -= 9.8 * delta
	else:
		velocity.y = 0.0
	if flee_t > 0.0:
		flee_t -= delta
		var away: Vector3 = global_position - world.player.global_position
		away.y = 0
		away = away.normalized()
		velocity.x = away.x * 4.0
		velocity.z = away.z * 4.0
		model.rotation.y = atan2(away.x, away.z)
		Chars.play(ap, "run", 0.15, 1.5)
		move_and_slide()
		return
	if talk_t > 0.0:
		talk_t -= delta
		velocity.x = 0
		velocity.z = 0
		move_and_slide()
		return
	if route.size() > 1:
		var tgt: Vector3 = route[route_i]
		var to := tgt - global_position
		to.y = 0
		if to.length() < 0.5:
			if ping_pong:
				if route_i + route_dir >= route.size() or route_i + route_dir < 0:
					route_dir = -route_dir
				route_i += route_dir
			else:
				route_i = (route_i + 1) % route.size()
		else:
			var d := to.normalized()
			velocity.x = d.x * speed
			velocity.z = d.z * speed
			model.rotation.y = lerp_angle(model.rotation.y, atan2(d.x, d.z), min(1.0, delta * 5.0))
			var a := anim if anim in ["walk", "run", "pull"] else "walk"
			Chars.play(ap, a, 0.25, speed / ({"walk": 1.12, "run": 1.9, "pull": 1.0}.get(a, 1.0)))
		move_and_slide()
		if cart:
			var back := -model.global_basis.z.normalized()
			cart.global_position = global_position + back * 3.0
			cart.rotation.y = model.rotation.y
		return
	velocity.x = 0
	velocity.z = 0
	model.rotation.y = lerp_angle(model.rotation.y, home_yaw, min(1.0, delta * 3.0))
	Chars.play(ap, anim, 0.3)
	move_and_slide()
