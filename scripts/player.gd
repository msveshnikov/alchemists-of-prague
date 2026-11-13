extends CharacterBody3D
class_name Player
## Václav: third-person controller, sword & shield combat, stamina, potions, interaction, grab & defenestration.

signal died

const JOG := 3.4
const SPRINT := 5.6
const WALK := 1.5
const BLOCK_SPEED := 1.4
const JUMP := 4.4
const DODGE_SPEED := 6.5         # roll: 0.5 s x 6.5 m/s ~ 3.3 m (the old 0.32 s was too short to show a roll)
const DODGE_TIME := 0.5
const DODGE_IFRAMES := 0.35      # invulnerable for the first part of the roll, as before
# ground speeds the locomotion clips are authored for (lib_gait.py): played at 1x the feet don't slide
const ANIM_WALK := 1.5
const ANIM_RUN := 3.4
const ANIM_SPRINT := 5.6
const ATTACK_RANGE := 2.3
const ATTACK_ARC := 0.35          # cos of half-angle (~70 deg)

var world: Node
var model: Node3D
var ap: AnimationPlayer
var pivot: Node3D
var spring: SpringArm3D
var camera: Camera3D
var sword_mesh: MeshInstance3D

var yaw := 0.0
var pitch := -0.25
var attacking := 0.0
var attack_hit_at := 0.0
var attack_done := false
var attack_queued := false
var blocking := false
var dodge_time := 0.0
var dodge_dir := Vector3.ZERO
var dodge_back := false
var hurt_time := 0.0
var dead := false
var grabbed: Node = null
var throwing := 0.0
var step_t := 0.0
var walk_mode := false
var jump_t := 0.0
var combo := 0
var shake := 0.0
var focus: Dictionary = {}
var input_enabled := true


func _ready() -> void:
	collision_layer = 2
	collision_mask = 1 | 4
	var cs := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.34
	cap.height = 1.8
	cs.shape = cap
	cs.position.y = 0.9
	add_child(cs)
	model = Chars.instance("vaclav")
	add_child(model)
	ap = Chars.anim_player(model)
	sword_mesh = Chars.find_mesh(model, "WEAPON_sword")
	apply_sword_look()
	pivot = Node3D.new()
	pivot.top_level = true
	add_child(pivot)
	spring = SpringArm3D.new()
	spring.spring_length = 3.8
	spring.collision_mask = 1
	spring.margin = 0.2
	var sph := SphereShape3D.new()
	sph.radius = 0.25
	spring.shape = sph
	spring.add_excluded_object(get_rid())
	pivot.add_child(spring)
	camera = Camera3D.new()
	camera.fov = 68.0
	camera.far = 1600.0
	camera.near = 0.08
	spring.add_child(camera)
	camera.current = true
	Chars.play(ap, "idle")


func apply_sword_look() -> void:
	if sword_mesh == null:
		return
	var lvl := Game.sword_level
	if lvl == 0:
		sword_mesh.material_override = null
		return
	var m := StandardMaterial3D.new()
	m.metallic = 1.0
	m.roughness = [0.4, 0.25, 0.2, 0.15][lvl]
	m.albedo_color = [Color(0.7, 0.7, 0.72), Color(0.85, 0.85, 0.9), Color(0.8, 0.62, 0.32), Color(0.95, 0.75, 0.3)][lvl]
	if lvl >= 3:
		m.emission_enabled = true
		m.emission = Color(1.0, 0.6, 0.2)
		m.emission_energy_multiplier = 0.4
	sword_mesh.material_override = m


func _unhandled_input(event: InputEvent) -> void:
	if dead or not input_enabled:
		return
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		var sens: float = float(Game.settings["mouse_sens"]) * 0.01
		yaw -= event.relative.x * sens
		var inv := -1.0 if Game.settings["invert_y"] else 1.0
		pitch = clamp(pitch - event.relative.y * sens * inv, -1.2, 0.6)
	elif event is InputEventKey and event.pressed and not event.echo and event.physical_keycode == KEY_CAPSLOCK:
		walk_mode = not walk_mode
		Game.say("Walking" if walk_mode else "Running")


func cam_forward() -> Vector3:
	return Vector3(-sin(yaw), 0, -cos(yaw))


func facing() -> Vector3:
	return model.global_basis.z.normalized()


func _physics_process(delta: float) -> void:
	pivot.global_position = global_position + Vector3(0, 1.65, 0)
	pivot.rotation = Vector3(pitch, yaw, 0)
	if shake > 0.0:
		shake = max(0.0, shake - delta * 2.5)
		camera.h_offset = randf_range(-1, 1) * shake * 0.12
		camera.v_offset = randf_range(-1, 1) * shake * 0.12
	_regen(delta)
	if not is_on_floor():
		velocity.y -= 9.8 * delta
	if dead:
		velocity.x = 0
		velocity.z = 0
		move_and_slide()
		return
	var can_act := input_enabled and not get_tree().paused
	var raw := Vector2.ZERO
	if can_act:
		raw = Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var fwd := cam_forward()
	var right := Vector3(-fwd.z, 0, fwd.x)
	var dir := (right * raw.x - fwd * raw.y)
	if dir.length() > 1.0:
		dir = dir.normalized()
	hurt_time = max(0.0, hurt_time - delta)
	jump_t = max(0.0, jump_t - delta)
	throwing = max(0.0, throwing - delta)
	blocking = can_act and Input.is_action_pressed("block") and attacking <= 0.0 and dodge_time <= 0.0 and grabbed == null \
		and Game.stamina > 1.0
	var speed := JOG
	var sprinting := can_act and Input.is_action_pressed("sprint") and dir.length() > 0.1 and Game.stamina > 2.0 and not blocking
	if walk_mode:
		speed = WALK
	if sprinting:
		speed = SPRINT
		Game.stamina = max(0.0, Game.stamina - 14.0 * delta)
	if blocking:
		speed = BLOCK_SPEED
	if grabbed:
		speed = 1.6
	if Game.slow_time > 0.0:
		speed *= 0.55
	if attacking > 0.0 or throwing > 0.0:
		speed = 0.6
	# dodge
	if dodge_time > 0.0:
		dodge_time -= delta
		velocity.x = dodge_dir.x * DODGE_SPEED
		velocity.z = dodge_dir.z * DODGE_SPEED
	else:
		velocity.x = move_toward(velocity.x, dir.x * speed, 30.0 * delta)
		velocity.z = move_toward(velocity.z, dir.z * speed, 30.0 * delta)
	if can_act and Input.is_action_just_pressed("jump") and is_on_floor() and attacking <= 0.0 and grabbed == null:
		velocity.y = JUMP
		jump_t = 0.75
		Chars.play(ap, "jump", 0.06, 1.15, true)
	if can_act and Input.is_action_just_pressed("dodge") and dodge_time <= 0.0 and Game.stamina >= 25.0 and grabbed == null:
		dodge_back = dir.length() <= 0.1
		dodge_dir = -facing() if dodge_back else dir.normalized()
		dodge_time = DODGE_TIME
		var da := "dodge_back" if dodge_back and ap.has_animation("dodge_back") else "dodge"
		Chars.play(ap, da, 0.04, Chars.length(ap, da) / DODGE_TIME, true)
		attacking = 0.0
		Game.stamina -= 25.0
		Sfx.play("cloth")
	move_and_slide()
	# facing
	var face_dir := Vector3.ZERO
	if attacking > 0.0 or blocking:
		face_dir = fwd
	elif dir.length() > 0.1:
		face_dir = dir
	if face_dir.length() > 0.01:
		var target := atan2(face_dir.x, face_dir.z)
		model.rotation.y = lerp_angle(model.rotation.y, target, min(1.0, delta * 12.0))
	# combat
	if can_act and Input.is_action_just_pressed("attack"):
		if attacking > 0.25:
			attack_queued = true
		elif attacking <= 0.0 and grabbed == null and dodge_time <= 0.0:
			_start_attack()
	if attacking > 0.0:
		attacking -= delta
		if not attack_done and attacking <= attack_hit_at:
			attack_done = true
			_deal_hit()
		if attacking <= 0.0 and attack_queued and Game.stamina >= 10.0:
			attack_queued = false
			_start_attack()
		elif attacking <= 0.0:
			combo = 0
	if grabbed and is_instance_valid(grabbed):
		grabbed.hold_at(global_position + facing() * 0.85 + Vector3(0, 0.25, 0), model.rotation.y + PI)
	elif grabbed:
		grabbed = null
	if can_act:
		for i in [1, 2, 3]:
			if Input.is_action_just_pressed("potion_%d" % i):
				var id: String = ["potion_health", "potion_stamina", "potion_antidote"][i - 1]
				if not Game.use_item(id):
					Game.say("No %s left." % Game.ITEMS[id]["name"], Color(1, 0.6, 0.4))
		_update_focus()
		if Input.is_action_just_pressed("interact"):
			_interact()
	_animate(dir, speed, sprinting, delta)


func _start_attack() -> void:
	if Game.stamina < 10.0:
		Game.say("Too exhausted to swing.", Color(1, 0.7, 0.4))
		return
	Game.stamina -= 12.0
	var spd := 1.25
	# chained swings alternate forehand / backhand
	var anim := "attack2" if combo % 2 == 1 and ap.has_animation("attack2") else "attack"
	combo += 1
	attacking = Chars.length(ap, anim) / spd * 0.85
	attack_hit_at = attacking * 0.52
	attack_done = false
	Chars.play(ap, anim, 0.08, spd, true)
	Sfx.play_at("swing", global_position + Vector3(0, 1.2, 0), -2.0)


func _deal_hit() -> void:
	var dmg := Game.sword_damage()
	var hit_any := false
	for t in world.attackable():
		if not is_instance_valid(t) or t.is_dead():
			continue
		var to: Vector3 = t.global_position - global_position
		to.y = 0
		var reach: float = ATTACK_RANGE + t.radius()
		if to.length() <= reach and facing().dot(to.normalized()) >= ATTACK_ARC:
			t.take_hit(dmg, self)
			hit_any = true
	if hit_any:
		shake = max(shake, 0.35)
		Sfx.play_at("hit", global_position + facing() * 1.2 + Vector3(0, 1.2, 0))


func take_damage(amount: float, from_pos: Vector3, kind := "melee") -> void:
	if dead or dodge_time > DODGE_TIME - DODGE_IFRAMES:
		return
	var to := (from_pos - global_position)
	to.y = 0
	var frontal := facing().dot(to.normalized()) > 0.25
	if blocking and frontal and kind != "splash":
		var bf := Game.block_factor()
		Game.stamina = max(0.0, Game.stamina - amount * 0.9)
		amount *= (1.0 - bf)
		Sfx.play_at("clash", global_position + Vector3(0, 1.3, 0))
		shake = max(shake, 0.2)
		if Game.stamina <= 0.5:
			Game.say("Your guard is broken!", Color(1, 0.5, 0.3))
			blocking = false
	var arm := Game.armor()
	amount *= 40.0 / (40.0 + arm * 3.0)
	amount *= float(Game.settings["difficulty"])
	if amount <= 0.05:
		return
	Game.hp = max(0.0, Game.hp - amount)
	Game.stats_changed.emit()
	world.hud.flash_damage(amount)
	shake = max(shake, clamp(amount / 30.0, 0.15, 0.7))
	if amount > 7.0 and attacking <= 0.0 and not blocking:
		hurt_time = 0.4
		Chars.play(ap, "hit", 0.05, 1.0, true)
	if amount > 4.0:
		Sfx.play("grunt", -4.0, 1.15)
	if Game.hp <= 0.0:
		_die()


func knockback(v: Vector3) -> void:
	velocity += v


func _die() -> void:
	dead = true
	attacking = 0.0
	if grabbed:
		grabbed.release()
		grabbed = null
	Chars.play(ap, "death", 0.1)
	Sfx.play("scream", -2.0, 0.9)
	died.emit()


func revive() -> void:
	dead = false
	hurt_time = 0.0
	Chars.play(ap, "idle", 0.1)


func _regen(delta: float) -> void:
	var rate := 18.0 if attacking <= 0.0 and not blocking else 4.0
	if Game.vigour_time > 0.0:
		Game.vigour_time -= delta
		rate *= 2.0
	Game.stamina = min(Game.max_stamina(), Game.stamina + rate * delta)
	if Game.poison_time > 0.0:
		Game.poison_time -= delta
		Game.hp = max(0.0, Game.hp - 4.0 * delta * float(Game.settings["difficulty"]))
		if Game.hp <= 0.0 and not dead:
			_die()
	if Game.slow_time > 0.0:
		Game.slow_time -= delta
	if Game.hp < Game.max_hp and Game.poison_time <= 0.0 and not dead:
		Game.hp = min(Game.max_hp, Game.hp + 0.6 * delta)


func _animate(dir: Vector3, speed: float, sprinting: bool, delta: float) -> void:
	if attacking > 0.0 or hurt_time > 0.0 or throwing > 0.0:
		return
	var hv := Vector2(velocity.x, velocity.z).length()
	if blocking:
		Chars.play(ap, "block", 0.15)
	elif dodge_time > 0.0:
		var da := "dodge_back" if dodge_back and ap.has_animation("dodge_back") else "dodge"
		if ap.has_animation(da):
			Chars.play(ap, da, 0.04, Chars.length(ap, da) / DODGE_TIME)
		else:
			Chars.play(ap, "run", 0.05, 2.2)
	elif jump_t > 0.0 and not is_on_floor() and ap.has_animation("jump"):
		pass
	elif grabbed:
		Chars.play(ap, "walk" if hv > 0.2 else "idle", 0.2, 1.2)
	elif hv > 0.2:
		if speed <= WALK + 0.01:
			Chars.play(ap, "walk", 0.2, hv / ANIM_WALK)
		elif sprinting and hv > (ANIM_RUN + ANIM_SPRINT) * 0.5 and ap.has_animation("sprint"):
			Chars.play(ap, "sprint", 0.25, hv / ANIM_SPRINT)
		else:
			Chars.play(ap, "run", 0.2, hv / ANIM_RUN)
	else:
		Chars.play(ap, "idle", 0.25)
	if hv > 0.3 and is_on_floor():
		step_t -= delta * hv
		if step_t <= 0.0:
			step_t = 0.69 if hv < 2.5 else (1.06 if hv < 4.5 else 1.63)   # = step length of walk/run/sprint
			Sfx.play_at("step", global_position, -9.0 if not sprinting else -6.0, 0.9 if world.inside_house else 1.0)


# ---------------------------------------------------------------- interaction / grab / throw
func _update_focus() -> void:
	focus = {}
	var best := 1e9
	if grabbed:
		var w: Dictionary = world.nearest_window(global_position)
		focus = {"label": w.get("label", "Throw out of the window!") if not w.is_empty() else "Throw", "kind": "throw"}
		world.hud.set_prompt(focus["label"])
		return
	for t in world.attackable():
		if is_instance_valid(t) and t.can_be_grabbed():
			var d: float = global_position.distance_to(t.global_position)
			if d < 2.0 and d < best:
				best = d
				focus = {"label": "Seize the %s" % t.display_name(), "kind": "grab", "target": t}
	if focus.is_empty():
		for it in world.interactables:
			if it.has("enabled") and not it["enabled"].call():
				continue
			var p: Vector3 = it["node"].global_position if it.has("node") else it["pos"]
			var d := global_position.distance_to(p)
			if d < it.get("radius", 2.0) and d < best:
				var to := p - global_position
				to.y = 0
				if to.length() > 0.6 and facing().dot(to.normalized()) < -0.2 and cam_forward().dot(to.normalized()) < -0.2:
					continue
				best = d
				focus = it
	world.hud.set_prompt(focus.get("label", "") if not focus.is_empty() else "")


func _interact() -> void:
	if focus.is_empty():
		return
	match focus.get("kind", ""):
		"throw":
			_throw()
		"grab":
			var t = focus["target"]
			if is_instance_valid(t) and t.can_be_grabbed():
				grabbed = t
				t.grab(self)
				attacking = 0.0
				Sfx.play("cloth")
				Game.say("You seize the %s. Find a window!" % t.display_name(), Color(1, 0.85, 0.5))
		_:
			if focus.has("action"):
				focus["action"].call()


func _throw() -> void:
	if grabbed == null or not is_instance_valid(grabbed):
		grabbed = null
		return
	var target = grabbed
	grabbed = null
	throwing = 0.9
	Chars.play(ap, "throw", 0.08, 1.4, true)
	var w: Dictionary = world.nearest_window(global_position)
	if not w.is_empty():
		world.defenestrate(target, w)
	else:
		var v := facing() * 5.5 + Vector3(0, 3.2, 0)
		target.thrown(global_position + facing() * 1.0 + Vector3(0, 1.0, 0), v, false)
