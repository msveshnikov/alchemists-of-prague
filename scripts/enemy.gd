extends CharacterBody3D
class_name Enemy
## Alchemist / skeleton / golem / city guard. Simple state machine with steering (the Old Town is mostly open).

enum S { IDLE, NEUTRAL, CHASE, ATTACK, HIT, STAGGER, GRABBED, THROWN, DEAD, RETREAT }

const TYPES := {
	"skeleton": {"name": "Skeleton", "hp": 45.0, "dmg": 11.0, "speed": 2.7, "range": 1.7, "cooldown": 1.6, "detect": 14.0,
		"grab": true, "radius": 0.35, "height": 1.85, "gold": [4, 10], "loot": {"bone_dust": 0.6, "key": 0.08}},
	"alchemist": {"name": "Alchemist", "hp": 50.0, "dmg": 12.0, "speed": 2.5, "range": 10.0, "cooldown": 2.6, "detect": 17.0,
		"grab": true, "radius": 0.35, "height": 1.8, "gold": [12, 28], "loot": {"quicksilver": 0.5, "potion_health": 0.3, "scroll": 0.25, "herb": 0.4}},
	"golem": {"name": "Clay Golem", "hp": 240.0, "dmg": 30.0, "speed": 1.5, "range": 3.0, "cooldown": 2.6, "detect": 15.0,
		"grab": false, "radius": 0.85, "height": 4.0, "gold": [45, 80], "loot": {"clay_shard": 1.0}},
	"guard": {"name": "City Guard", "hp": 90.0, "dmg": 13.0, "speed": 3.1, "range": 2.4, "cooldown": 1.5, "detect": 20.0,
		"grab": true, "radius": 0.35, "height": 1.82, "gold": [0, 0], "loot": {}},
}

var kind := "skeleton"
var def: Dictionary
var world: Node
var model: Node3D
var ap: AnimationPlayer
var bar: MeshInstance3D
var hp := 1.0
var state := S.IDLE
var timer := 0.0
var cooldown := 0.0
var attack_hit_at := 0.0
var attack_done := false
var home := Vector3.ZERO
var home_yaw := 0.0
var idle_anim := "idle"
var route: Array = []
var route_i := 0
var spawn_id := ""
var holder: Node = null
var fly_noclip_y := -INF
var fly_start_y := 0.0
var defen := false
var step_t := 0.0
var stuck_t := 0.0
var interior: Node = null


func setup(p_kind: String, p_world: Node, pos: Vector3, yaw: float, p_idle := "idle") -> void:
	kind = p_kind
	def = TYPES[kind]
	world = p_world
	hp = def["hp"]
	home = pos
	home_yaw = yaw
	idle_anim = p_idle
	position = pos
	collision_layer = 4
	collision_mask = 1 | 2 | 4
	var cs := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = def["radius"]
	cap.height = max(def["height"] * 0.95, cap.radius * 2.0 + 0.1)
	cs.shape = cap
	cs.position.y = cap.height / 2.0
	add_child(cs)
	model = Chars.instance(kind)
	add_child(model)
	model.rotation.y = yaw
	ap = Chars.anim_player(model)
	bar = Chars.health_bar(self, def["height"] + 0.35, 0.9 if kind != "golem" else 1.6)
	state = S.NEUTRAL if kind == "guard" else S.IDLE
	Chars.play(ap, idle_anim)
	if ap and ap.has_animation(idle_anim):
		ap.seek(randf() * Chars.length(ap, idle_anim), true)


# ---------------------------------------------------------------- interface used by player / world
func is_dead() -> bool:
	return state == S.DEAD


func radius() -> float:
	return def["radius"]


func display_name() -> String:
	return def["name"]


func is_hostile() -> bool:
	return state in [S.CHASE, S.ATTACK, S.RETREAT, S.HIT, S.STAGGER]


func can_be_grabbed() -> bool:
	return def["grab"] and state != S.DEAD and state != S.GRABBED and state != S.THROWN and hp <= def["hp"] * 0.35


func take_hit(dmg: float, attacker: Node) -> void:
	if state == S.DEAD or state == S.GRABBED or state == S.THROWN:
		return
	hp -= dmg
	Chars.set_bar(bar, hp / def["hp"])
	_flash()
	if kind == "guard" and Game.wanted <= 0.0:
		Game.set_wanted(120.0)
	if hp <= 0.0:
		_die(false)
		return
	world.alert(global_position, 14.0)
	if kind == "golem":
		Sfx.play_at("golem", global_position + Vector3(0, 3, 0), 0.0, 0.8)
		if state != S.ATTACK:
			state = S.CHASE
		return
	Sfx.play_at("bones" if kind == "skeleton" else "hurt", global_position + Vector3(0, 1.4, 0), -3.0, 0.8 if kind == "guard" else 1.0)
	if hp <= def["hp"] * 0.35 and def["grab"]:
		state = S.STAGGER
		timer = 2.6
		Chars.play(ap, "hit", 0.05, 0.7, true)
		if not world.hint_shown_grab:
			world.hint_shown_grab = true
			world.hud.hint("The %s is reeling! Press E to seize it — then E again by a window." % def["name"])
	else:
		state = S.HIT
		timer = 0.4
		Chars.play(ap, "hit", 0.05, 1.0, true)


func _flash() -> void:
	var tw := create_tween()
	model.scale = Vector3.ONE * 1.04
	tw.tween_property(model, "scale", Vector3.ONE, 0.15)


func grab(p_holder: Node) -> void:
	holder = p_holder
	state = S.GRABBED
	collision_layer = 0
	collision_mask = 0
	Chars.play(ap, "flail", 0.1)
	Sfx.play_at("scream", global_position + Vector3(0, 1.5, 0), -8.0, 1.2)


func hold_at(pos: Vector3, yaw: float) -> void:
	global_position = pos
	model.rotation.y = yaw


func release() -> void:
	holder = null
	collision_layer = 4
	collision_mask = 1 | 2 | 4
	state = S.STAGGER
	timer = 1.0


## Launched by the player. `noclip_until` lets a body fly out through a window opening before colliding again.
func thrown(from: Vector3, vel: Vector3, out_of_window: bool, noclip_until := -INF) -> void:
	holder = null
	global_position = from
	velocity = vel
	state = S.THROWN
	defen = out_of_window
	fly_start_y = from.y
	fly_noclip_y = noclip_until
	collision_layer = 0
	collision_mask = 0 if out_of_window else 1
	Chars.play(ap, "flail", 0.05)
	if out_of_window:
		Sfx.play_at("scream", from, 2.0)
	interior = null


func _die(by_fall: bool) -> void:
	state = S.DEAD
	hp = 0.0
	Chars.set_bar(bar, 0.0)
	collision_layer = 0
	collision_mask = 1
	Chars.play(ap, "death", 0.1)
	velocity = Vector3.ZERO
	Sfx.play_at({"skeleton": "bones", "golem": "golem", "alchemist": "scream", "guard": "hurt"}[kind],
		global_position + Vector3(0, 1.2, 0), 0.0, 0.7 if kind == "golem" else 1.0)
	world.on_enemy_killed(self, by_fall)


# ---------------------------------------------------------------- main loop
func _physics_process(delta: float) -> void:
	if state == S.GRABBED:
		return
	if state == S.THROWN:
		_fly(delta)
		return
	if not is_on_floor():
		velocity.y -= 9.8 * delta
	else:
		velocity.y = -0.5
	if state == S.DEAD:
		velocity.x = move_toward(velocity.x, 0, 10 * delta)
		velocity.z = move_toward(velocity.z, 0, 10 * delta)
		move_and_slide()
		return
	cooldown = max(0.0, cooldown - delta)
	var p: Node3D = world.player
	var to_p := p.global_position - global_position
	to_p.y = 0
	var dist := to_p.length()
	match state:
		S.NEUTRAL:
			_neutral(delta, dist)
		S.IDLE:
			_idle(delta, dist)
		S.HIT:
			timer -= delta
			_slow_down(delta)
			if timer <= 0.0:
				state = S.CHASE
		S.STAGGER:
			timer -= delta
			_slow_down(delta)
			if timer <= 0.0:
				state = S.CHASE
		S.CHASE, S.RETREAT:
			_fight(delta, to_p, dist)
		S.ATTACK:
			_attack_tick(delta, to_p, dist)
	_separate()
	move_and_slide()
	if state in [S.CHASE, S.RETREAT] and Vector2(velocity.x, velocity.z).length() > 0.3:
		step_t -= delta
		if step_t <= 0.0:
			step_t = 0.55 if kind == "golem" else 0.9
			if kind == "golem":
				Sfx.play_at("slam", global_position, -10.0, 0.6)
				world.player.shake = max(world.player.shake, clamp(1.0 - dist / 14.0, 0.0, 0.35))
			elif kind == "skeleton" and randf() < 0.3:
				Sfx.play_at("bones", global_position + Vector3(0, 1, 0), -14.0)


func _slow_down(delta: float) -> void:
	velocity.x = move_toward(velocity.x, 0, 12 * delta)
	velocity.z = move_toward(velocity.z, 0, 12 * delta)


func _sees_player(dist: float) -> bool:
	var detect: float = def["detect"] * (1.2 if world.day_night.is_night else 1.0)
	if dist > detect or world.player.dead:
		return false
	if (interior != null) != world.inside_house:
		return false
	var q := PhysicsRayQueryParameters3D.create(global_position + Vector3(0, 1.5, 0), world.player.global_position + Vector3(0, 1.4, 0), 1)
	return get_world_3d().direct_space_state.intersect_ray(q).is_empty()


func _neutral(delta: float, dist: float) -> void:
	if Game.wanted > 0.0 and dist < def["detect"] and (interior != null) == world.inside_house:
		state = S.CHASE
		Sfx.play_at("grunt", global_position + Vector3(0, 1.6, 0), 0.0, 0.8)
		return
	if route.size() > 1:
		var tgt: Vector3 = route[route_i]
		var to := tgt - global_position
		to.y = 0
		if to.length() < 0.6:
			route_i = (route_i + 1) % route.size()
		else:
			var d := to.normalized()
			velocity.x = d.x * 1.1
			velocity.z = d.z * 1.1
			model.rotation.y = lerp_angle(model.rotation.y, atan2(d.x, d.z), min(1.0, delta * 6.0))
			Chars.play(ap, "walk", 0.25)
			return
	else:
		var to_home := home - global_position
		to_home.y = 0
		if to_home.length() > 1.0:
			var d2 := to_home.normalized()
			velocity.x = d2.x * 1.1
			velocity.z = d2.z * 1.1
			model.rotation.y = lerp_angle(model.rotation.y, atan2(d2.x, d2.z), min(1.0, delta * 6.0))
			Chars.play(ap, "walk", 0.25)
			return
	_slow_down(delta)
	model.rotation.y = lerp_angle(model.rotation.y, home_yaw, min(1.0, delta * 3.0))
	Chars.play(ap, idle_anim, 0.3)


func _idle(delta: float, dist: float) -> void:
	if route.size() > 1:
		_neutral(delta, 999.0)
	else:
		_slow_down(delta)
		Chars.play(ap, idle_anim, 0.3)
	if _sees_player(dist):
		state = S.CHASE
		world.alert(global_position, 12.0 if kind == "skeleton" else 6.0)
		Sfx.play_at(kind if kind in ["golem", "skeleton"] else "grunt", global_position + Vector3(0, 1.6, 0), -2.0)


func alerted() -> void:
	if state in [S.IDLE] or (state == S.NEUTRAL and Game.wanted > 0.0):
		state = S.CHASE


func _face(dir: Vector3, delta: float, rate := 8.0) -> void:
	if dir.length() > 0.01:
		model.rotation.y = lerp_angle(model.rotation.y, atan2(dir.x, dir.z), min(1.0, delta * rate))


func _fight(delta: float, to_p: Vector3, dist: float) -> void:
	if world.player.dead or (interior != null) != world.inside_house:
		state = S.NEUTRAL if kind == "guard" else S.IDLE
		return
	if kind == "guard" and Game.wanted <= 0.0:
		state = S.NEUTRAL
		return
	if dist > def["detect"] * 2.2:
		state = S.NEUTRAL if kind == "guard" else S.IDLE
		return
	var dir := to_p.normalized()
	var spd: float = def["speed"] * (1.0 if world.day_night.is_night else 0.9)
	var move := Vector3.ZERO
	if kind == "alchemist":
		if dist < 6.0:
			move = -dir
			state = S.RETREAT
		elif dist > 11.0:
			move = dir
			state = S.CHASE
		else:
			move = Vector3(-dir.z, 0, dir.x) * (0.5 if int(Time.get_ticks_msec() / 2500) % 2 == 0 else -0.5)
			state = S.CHASE
		if cooldown <= 0.0 and dist < 14.0 and _sees_player(dist):
			_begin_attack()
			return
	else:
		if dist <= def["range"] + world.player_radius() and cooldown <= 0.0:
			_begin_attack()
			return
		move = dir if dist > def["range"] * 0.8 else Vector3.ZERO
	# simple obstacle handling: if blocked, slide sideways for a while
	if is_on_wall() and move.length() > 0.1:
		stuck_t = 0.8
	if stuck_t > 0.0:
		stuck_t -= delta
		move = (move + Vector3(-move.z, 0, move.x) * 1.5).normalized()
	velocity.x = move.x * spd
	velocity.z = move.z * spd
	_face(dir, delta)
	var hv := Vector2(velocity.x, velocity.z).length()
	if hv > 0.2:
		if kind == "golem":
			Chars.play(ap, "walk", 0.25, hv / 0.9)
		else:
			Chars.play(ap, "run", 0.2, hv / 2.57)
	else:
		Chars.play(ap, "idle" if kind != "alchemist" else "cast", 0.25)


func _begin_attack() -> void:
	state = S.ATTACK
	var spd := 1.0 if kind != "golem" else 0.9
	timer = Chars.length(ap, "attack") / spd
	attack_hit_at = timer * (0.45 if kind != "golem" else 0.42)
	attack_done = false
	Chars.play(ap, "attack", 0.1, spd, true)
	if kind != "alchemist":
		Sfx.play_at("swing" if kind != "golem" else "golem", global_position + Vector3(0, 1.3, 0), -4.0, 0.8 if kind == "golem" else 1.0)


func _attack_tick(delta: float, to_p: Vector3, dist: float) -> void:
	timer -= delta
	_slow_down(delta)
	_face(to_p.normalized(), delta, 4.0)
	if not attack_done and timer <= attack_hit_at:
		attack_done = true
		var fwd := model.global_basis.z.normalized()
		var p: Node3D = world.player
		if kind == "alchemist":
			world.throw_potion(self, global_position + Vector3(0, 1.7, 0) + fwd * 0.4, p.global_position + p.velocity * 0.6)
		elif kind == "golem":
			Sfx.play_at("slam", global_position + fwd * 2.0, 4.0, 0.5)
			p.shake = max(p.shake, 0.8)
			if dist <= def["range"] + 0.8 and fwd.dot(to_p.normalized()) > 0.1:
				p.take_damage(def["dmg"], global_position)
				p.knockback(to_p.normalized() * 7.0 + Vector3(0, 3.0, 0))
		else:
			if dist <= def["range"] + 0.7 and fwd.dot(to_p.normalized()) > 0.3:
				p.take_damage(def["dmg"], global_position)
	if timer <= 0.0:
		cooldown = def["cooldown"] * randf_range(0.8, 1.3)
		state = S.CHASE


func _separate() -> void:
	for o in world.enemies:
		if o == self or not is_instance_valid(o) or o.state == S.DEAD:
			continue
		var d: Vector3 = global_position - o.global_position
		d.y = 0
		var min_d: float = radius() + o.radius() + 0.3
		if d.length() < min_d and d.length() > 0.001:
			velocity += d.normalized() * (min_d - d.length()) * 4.0


func _fly(delta: float) -> void:
	velocity.y -= 9.8 * delta
	if global_position.y > fly_noclip_y:
		global_position += velocity * delta
		model.rotation.x = lerp(model.rotation.x, -0.9, delta * 2.0)
		return
	collision_mask = 1
	move_and_slide()
	if is_on_floor() and velocity.y <= 0.0:
		model.rotation.x = 0.0
		var fall := fly_start_y - global_position.y
		collision_layer = 4
		collision_mask = 1 | 2 | 4
		Sfx.play_at("hit", global_position + Vector3(0, 0.3, 0), 4.0, 0.7)
		if defen or fall > 3.0:
			_die(true)
		else:
			hp -= 20.0
			Chars.set_bar(bar, hp / def["hp"])
			if hp <= 0.0:
				_die(false)
			else:
				state = S.STAGGER
				timer = 1.2
				Chars.play(ap, "hit", 0.05, 0.8, true)
