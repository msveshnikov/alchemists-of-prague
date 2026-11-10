extends Node
## Scripted trailer on the Old Town Square. Record with Godot's Movie Maker:
##   godot --path . scenes/game.tscn --fixed-fps 30 --quit-after 4000 --write-movie out.avi -- --cinematic > out.log
## then cut it with:  python tools/edit_trailer.py out.avi out.log trailer.mp4
## --resolution is ignored (project.godot sets window_*_override): for 1080p put a temporary override.cfg next to
## project.godot with display/window/size/window_width_override=1920 and window_height_override=1080.
## `-- --cinematic --night-only` re-takes just the sunset and the night fights; `--probe` saves stills to renders/cine/.
## Each cut prints "CINE cut <name> frame <n> drawn <d> t <sec>"; drawn/30 is the cut's time in the recording.

const FPS := 30.0
const DAY := 0.08
const NIGHT := 0.6
const FIGHT_AT := Vector3(19.0, 0.1, -10.0)   # open cobbles NE of the column, Týn and the north row behind

var world: Node
var p: Player
var cam: Camera3D
var out_dir := ""
var frame := 0
var rec_t := 0.0
var god := true

# director state
var route: Array = []
var route_i := 0
var sprint := false
var steer_rate := 6.0
var _stuck_t := 0.0
var _veer_t := 0.0
var fighting := false
var _atk_t := 0.0
var _dodge_cd := 0.0
var _release := {}          # action -> frames left before release
var cam_fn := Callable()
var shot_t := 0.0
var _cam_pos := Vector3.ZERO
var _cam_at := Vector3.ZERO
var _cam_smooth := 0.0      # 0 = exact, >0 = exponential follow rate
var cam_collide := false     # pull script cameras in front of walls they would clip into
var titles: CanvasLayer
var _mine: Array = []          # enemies staged by the script; any other creature near the fight is removed
var _clean_strays := false   # from sunset on, remove night creatures the script did not stage (and their flasks)
var _fill: OmniLight3D
var _rim: OmniLight3D


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	p = world.player
	out_dir = ProjectSettings.globalize_path("res://renders/cine/")
	DirAccess.make_dir_recursive_absolute(out_dir)
	cam = Camera3D.new()
	cam.fov = 60.0
	cam.near = 0.08
	cam.far = 1600.0
	world.add_child(cam)
	world.hud.visible = false
	Game.settings["day_minutes"] = 100000.0
	var mi := AudioServer.get_bus_index("Music")
	if mi >= 0 and not ("--probe" in OS.get_cmdline_user_args()):
		AudioServer.set_bus_mute(mi, true)       # the music is laid in during the edit
	titles = CanvasLayer.new()
	titles.layer = 60
	add_child(titles)
	_run.call_deferred()


# ---------------------------------------------------------------- helpers
func _frames(n: int) -> void:
	for i in n:
		await get_tree().process_frame


func _secs(s: float) -> void:
	await _frames(int(round(s * FPS)))


func _still(name: String) -> void:
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(out_dir + name + ".png")
	print("CINE still ", name)


func _look(from: Vector3, at: Vector3) -> void:
	cam.global_position = from
	if from.distance_to(at) > 0.01:
		cam.look_at(at, Vector3.UP)
	cam.current = true


func _tod(t: float) -> void:
	Game.time_of_day = t
	world.day_night.apply(t)


func _tap(action: String, frames := 3) -> void:
	Input.action_press(action)
	_release[action] = frames


func _release_all() -> void:
	for a in ["move_forward", "move_back", "move_left", "move_right", "sprint", "attack", "block", "dodge", "jump"]:
		Input.action_release(a)
	_release.clear()


func _ease(x: float) -> float:
	x = clamp(x, 0.0, 1.0)
	return x * x * (3.0 - 2.0 * x)


func head() -> Vector3:
	return p.global_position + Vector3(0, 1.55, 0)


## Start a shot: cam_fn(t) returns [from, at] (or [from, at, fov]); null cam_fn = the player's own gameplay camera.
func _cut(name: String, fn = null, smooth := 0.0) -> void:
	print("CINE cut %s frame %d drawn %d t %.2f" % [name, frame, Engine.get_frames_drawn(), rec_t])
	shot_t = 0.0
	_cam_smooth = smooth
	if fn == null:
		cam_fn = Callable()
		p.camera.current = true
	else:
		cam_fn = fn
		var r: Array = fn.call(0.0)
		_cam_pos = r[0]
		_cam_at = r[1]
		_apply_cam(r)


func _apply_cam(r: Array) -> void:
	if cam_collide:
		var q := PhysicsRayQueryParameters3D.create(_cam_at, _cam_pos, 1)
		var hit := cam.get_world_3d().direct_space_state.intersect_ray(q)
		if not hit.is_empty():
			_cam_pos = hit["position"] + (_cam_at - hit["position"]).normalized() * 0.35
	if r.size() > 2:
		cam.fov = r[2]
	else:
		cam.fov = 60.0
	_look(_cam_pos, _cam_at)


func _process(delta: float) -> void:
	frame += 1
	rec_t += delta
	shot_t += delta
	if god:
		Game.hp = Game.max_hp
		Game.stamina = Game.max_stamina()
		Game.poison_time = 0.0
		Game.slow_time = 0.0
	for a in _release.keys():
		_release[a] -= 1
		if _release[a] <= 0:
			Input.action_release(a)
			_release.erase(a)
	if route_i < route.size():
		_follow(delta)
	if fighting:
		_fight_tick(delta)
	if _fill:
		_fill.global_position = p.global_position + Vector3(-1.8, 2.6, 2.2)
		_rim.global_position = p.global_position + Vector3(2.5, 2.2, -3.0)
	if _clean_strays:
		for c in world.get_children():
			if c is Potion:
				c.queue_free()
		for e in world.enemies.duplicate():
			if is_instance_valid(e) and not (e in _mine) and e.kind != "guard" and e.global_position.distance_to(p.global_position) < 40.0:
				if e.spawn_id != "":
					world.killed[e.spawn_id] = world._phase_serial
				world._despawn(e)
	if cam_fn.is_valid():
		var r: Array = cam_fn.call(shot_t)
		if _cam_smooth > 0.0:
			var k := 1.0 - exp(-_cam_smooth * delta)
			_cam_pos = _cam_pos.lerp(r[0], k)
			_cam_at = _cam_at.lerp(r[1], k)
		else:
			_cam_pos = r[0]
			_cam_at = r[1]
		_apply_cam(r)


func _go(points: Array, run_fast := false) -> void:
	route = points
	route_i = 0
	sprint = run_fast


func _follow(delta: float) -> void:
	var tgt: Vector3 = route[route_i]
	var to := tgt - p.global_position
	to.y = 0
	if to.length() < 1.3:
		route_i += 1
		if route_i >= route.size():
			Input.action_release("move_forward")
			Input.action_release("sprint")
			return
		tgt = route[route_i]
		to = tgt - p.global_position
		to.y = 0
	# blocked by a stall or a townsman: veer right for a moment
	if Vector2(p.velocity.x, p.velocity.z).length() < 1.0:
		_stuck_t += delta
	else:
		_stuck_t = 0.0
	if _stuck_t > 0.35:
		_veer_t = 0.6
		_stuck_t = 0.0
	var want := atan2(-to.x, -to.z)
	if _veer_t > 0.0:
		_veer_t -= delta
		want -= 1.1
	p.yaw = lerp_angle(p.yaw, want, min(1.0, delta * steer_rate))
	Input.action_press("move_forward")
	if sprint:
		Input.action_press("sprint")
	else:
		Input.action_release("sprint")


func _foes() -> Array:
	var out: Array = []
	for e in world.enemies:
		if is_instance_valid(e) and not e.is_dead() and e.kind != "guard" and e.interior == null \
				and e.global_position.distance_to(p.global_position) < 30.0:
			out.append(e)
	return out


func _nearest_foe() -> Enemy:
	var best: Enemy = null
	var bd := 1e9
	for e in _foes():
		var d: float = e.global_position.distance_to(p.global_position)
		if d < bd:
			bd = d
			best = e
	return best


func _fight_tick(delta: float) -> void:
	_dodge_cd -= delta
	var foe := _nearest_foe()
	if foe == null:
		Input.action_release("move_forward")
		return
	var to := foe.global_position - p.global_position
	to.y = 0
	p.yaw = lerp_angle(p.yaw, atan2(-to.x, -to.z), min(1.0, delta * 9.0))
	var reach := 1.5 + foe.radius()
	if foe.kind == "golem" and foe.state == Enemy.S.ATTACK and _dodge_cd <= 0.0 and to.length() < 4.5:
		_dodge_cd = 2.2
		_tap("dodge", 2)
		return
	if to.length() > reach:
		Input.action_press("move_forward")
	else:
		Input.action_release("move_forward")
		_atk_t -= delta
		if _atk_t <= 0.0:
			_atk_t = 0.3
			_tap("attack", 2)


func _spawn(kind: String, pos: Vector3, yaw := 0.0, chase := true) -> Enemy:
	var en := Enemy.new()
	en.setup(kind, world, pos, yaw)
	world.add_child(en)
	world.enemies.append(en)
	if en.bar:
		en.bar.visible = false     # no health bars in the trailer
	if chase:
		en.alerted()
	return en


func _title(text: String, size: int, y: float, color: Color, t_in: float, hold: float, t_out: float) -> void:
	var l := UiKit.title(text, size, color)
	l.set_anchors_preset(Control.PRESET_TOP_WIDE)
	l.position.y = y
	l.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.75))
	l.add_theme_constant_override("shadow_offset_x", 3)
	l.add_theme_constant_override("shadow_offset_y", 3)
	l.add_theme_constant_override("shadow_outline_size", 10)
	l.modulate.a = 0.0
	titles.add_child(l)
	var tw := create_tween()
	tw.tween_property(l, "modulate:a", 1.0, t_in)
	tw.tween_interval(hold)
	tw.tween_property(l, "modulate:a", 0.0, t_out)
	tw.tween_callback(l.queue_free)


## Hide townsfolk standing between the camera and the action (they wander into the lens otherwise).
var _hidden: Array = []


func _clear_view(from: Vector3, to: Vector3, r: float) -> void:
	for n in world.npcs:
		if not is_instance_valid(n):
			continue
		var q: Vector3 = Geometry3D.get_closest_point_to_segment(n.global_position + Vector3(0, 1, 0), from, to)
		if q.distance_to(n.global_position + Vector3(0, 1, 0)) < r and n.visible:
			n.visible = false
			_hidden.append(n)


func _unhide() -> void:
	for n in _hidden:
		if is_instance_valid(n):
			n.visible = true
	_hidden.clear()


## Night needs a little film lighting: a warm torch-like key on Václav, a cold moon rim, lifted exposure.
func _night_look() -> void:
	_fill = OmniLight3D.new()
	_fill.light_color = Color(1.0, 0.72, 0.42)
	_fill.light_energy = 2.4
	_fill.omni_range = 11.0
	_fill.omni_attenuation = 1.2
	world.add_child(_fill)
	_rim = OmniLight3D.new()
	_rim.light_color = Color(0.55, 0.68, 1.0)
	_rim.light_energy = 1.6
	_rim.omni_range = 12.0
	world.add_child(_rim)
	world.env.tonemap_exposure = 1.45
	world.env.adjustment_saturation = 1.15


func _place_player(pos: Vector3, yaw: float) -> void:
	p.global_position = pos
	p.velocity = Vector3.ZERO
	p.yaw = yaw
	p.model.rotation.y = yaw + PI


# ---------------------------------------------------------------- the trailer
func _run() -> void:
	if "--probe" in OS.get_cmdline_user_args():
		await _probe()
		get_tree().quit()
		return
	Game.sword_level = 3
	p.apply_sword_look()
	Game.sword_level = 1          # golden look, modest damage: fights last long enough to film
	_tod(DAY)
	_place_player(Vector3(0, 0.1, 21.0), 0.0)
	_look(Vector3(0, 44, 64), Vector3(0, 8, -40))
	await _secs(2.5)             # let the town settle (streamed population, lights); trimmed in the edit
	if not ("--night-only" in OS.get_cmdline_user_args()):   # quick re-take of the night half
		await _shot_establish()
		await _shot_close()
		await _shot_gameplay()
		await _shot_side()
		await _shot_drone()
		await _shot_window()
	await _shot_timelapse()
	await _shot_fight()
	await _shot_golem()
	await _shot_finale()
	print("CINE end frame %d t %.2f" % [frame, rec_t])
	get_tree().quit()


# 1. aerial establishing shot, descending over the square towards Václav
func _shot_establish() -> void:
	var cf := func(t: float) -> Array:
		# glide in over the south roofs first (z eases out), drop to street level only inside the square (y eases in)
		var u: float = clamp(t / 7.0, 0.0, 1.0)
		var uz: float = 1.0 - pow(1.0 - u, 2.0)
		var uy: float = pow(u, 2.2)
		var from: Vector3 = Vector3(lerp(-8.0, 1.5, uz), lerp(46.0, 2.6, uy), lerp(74.0, 27.0, uz))
		var at: Vector3 = Vector3(0, lerp(10.0, 1.8, _ease(u)), lerp(-50.0, 20.0, _ease(u)))
		return [from, at, 55.0]
	_cut("establish", cf, 0.0)
	_title("Alchemists of Prague", 96, 330, UiKit.PARCH, 1.2, 3.0, 1.2)
	await _secs(1.0)
	_title("Old Town Square  ·  Anno Domini 1357", 40, 450, UiKit.GOLD, 1.2, 2.5, 1.2)
	await _secs(6.0)


# 2. close-up of the hero; he sets off and runs past the low camera
func _shot_close() -> void:
	var base := p.global_position
	var cf := func(t: float) -> Array:
		var a: float = lerp(0.95, 0.25, _ease(t / 5.0))   # his right side: the shield is on his left arm
		var from: Vector3 = base + Vector3(sin(a) * 2.3, 1.5 - 0.5 * _ease((t - 2.0) / 3.0), -cos(a) * 2.3)
		var at: Vector3 = p.global_position + Vector3(0, 1.45 - 0.25 * _ease((t - 2.2) / 1.0), 0)
		return [from, at, 42.0]
	_cut("close", cf, 0.0)
	await _secs(2.2)
	_go([Vector3(-0.8, 0, 12.0), Vector3(-3.5, 0, 8.0), Vector3(-3.4, 0, 0.0), Vector3(-3.6, 0, -5.5),
		Vector3(-7.5, 0, -10.0), Vector3(-7.5, 0, -19.0), Vector3(-3.0, 0, -24.0), Vector3(30.0, 0, -24.0)])
	await _secs(2.8)


# 3. gameplay camera: jog, sprint, jump through the market
func _shot_gameplay() -> void:
	p.pitch = -0.2
	p.spring.spring_length = 3.8
	_cut("gameplay")
	await _secs(1.6)
	sprint = true
	await _secs(2.2)
	_tap("jump", 3)
	await _secs(2.4)


# 4. side tracking shot at running height, the Marian column passing behind
func _shot_side() -> void:
	var cf := func(t: float) -> Array:
		var pp := p.global_position
		var from: Vector3 = Vector3(pp.x - 6.5, 1.1, pp.z - 2.0)
		return [from, pp + Vector3(0, 1.0, -1.0), 50.0]
	_cut("side", cf, 6.0)
	await _secs(4.2)


# 5. drone: the camera climbs until Václav is a speck crossing the square
func _shot_drone() -> void:
	var cf := func(t: float) -> Array:
		var u := _ease(t / 6.5)
		var pp := p.global_position
		var h: float = lerp(9.0, 48.0, u)
		var from: Vector3 = pp + Vector3(lerp(-6.0, -14.0, u), h, lerp(10.0, 26.0, u))
		return [from, pp + Vector3(0, 0.5, 0), lerp(55.0, 48.0, u)]
	_cut("drone", cf, 3.0)
	await _secs(6.5)
	route = []
	_release_all()


# 6. defenestration seen from the square
func _shot_window() -> void:
	var hid := "house_burgher_c#00"
	if not world.houses.has(hid):
		hid = world.houses.keys()[0]
	world.enter_house(hid)
	var it: Dictionary = world.interiors[hid]
	var foe: Enemy = null
	for e in it["enemies"]:
		if is_instance_valid(e):
			foe = e
	var w: Dictionary = it["windows"][0]
	for cand in it["windows"]:
		if abs(cand["pos"].x - world.houses[hid]["node"].global_position.x) < abs(w["pos"].x - world.houses[hid]["node"].global_position.x):
			w = cand
	var out: Vector3 = w["out"]
	var wp: Vector3 = w["pos"]
	var side := Vector3(-out.z, 0, out.x)
	var ground := Vector3(wp.x, 0, wp.z)
	var cf := func(t: float) -> Array:
		var u := _ease(t / 5.5)
		var from: Vector3 = ground + out * lerp(17.0, 14.5, u) + side * 5.5 + Vector3(0, lerp(1.3, 1.7, u), 0)
		var at: Vector3 = ground + out * lerp(3.0, 6.5, _ease((t - 1.2) / 1.6)) + Vector3(0, lerp(wp.y - 0.8, 1.0, _ease((t - 1.2) / 1.6)), 0)
		_clear_view(from, ground + out * 2.0 + Vector3(0, 1, 0), 2.6)
		_clear_view(from, ground + out * 9.0, 2.6)
		return [from, at, 52.0]
	_cut("window", cf, 0.0)
	if foe:
		_place_player(Vector3(wp.x, foe.global_position.y + 0.05, wp.z) - out * 1.3, atan2(-out.x, -out.z))
		p.model.rotation.y = atan2(out.x, out.z)
		foe.global_position = p.global_position + out * 0.9
		await _secs(0.4)
		foe.take_hit(foe.hp - foe.def["hp"] * 0.3, p)
		p._update_focus()
		p._interact()
		await _secs(0.6)
		p._update_focus()
		p._interact()
	await _secs(4.5)
	world.exit_house()
	_unhide()


# 7. time-lapse: the sun sets over the square, lamps and windows light up
func _shot_timelapse() -> void:
	_place_player(FIGHT_AT, 0.0)
	_clean_strays = true
	var cf := func(t: float) -> Array:
		var u := _ease(t / 6.0)
		_tod(lerp(0.3, NIGHT, u))
		var from: Vector3 = Vector3(lerp(30.0, 24.0, u), lerp(20.0, 26.0, u), lerp(26.0, 32.0, u))
		return [from, Vector3(lerp(-6.0, 0.0, u), 10.0, -45.0), 52.0]
	_cut("timelapse", cf, 0.0)
	await _secs(6.0)
	_tod(NIGHT)


# 8. night fight by the Marian column
func _shot_fight() -> void:
	_place_player(FIGHT_AT, 0.0)
	for e in _foes():
		world._despawn(e)
	_night_look()
	for off in [Vector3(-2.5, 0, -7.0), Vector3(2.5, 0, -8.0), Vector3(0.0, 0, -10.0), Vector3(-5.0, 0, -10.5)]:
		_mine.append(_spawn("skeleton", FIGHT_AT + off, 0.0))
	# 8a. low wide from behind: the dead come out of the dark under the column
	var cf := func(t: float) -> Array:
		var pp := p.global_position
		return [pp + Vector3(-2.2, 0.55, 4.2), pp + Vector3(0.5, 1.6, -6.0), 52.0]
	cam_collide = true
	_cut("fight_wide", cf, 4.0)
	_tap("block", 40)
	await _secs(1.4)
	fighting = true
	await _secs(2.2)
	# 8b. gameplay camera in the melee
	p.spring.spring_length = 3.2
	p.pitch = -0.22
	_cut("fight_play")
	await _secs(4.0)
	# 8c. slow low orbit around the swordsman
	var c0 := p.global_position
	var cf2 := func(t: float) -> Array:
		var a: float = 0.6 + t * 0.35
		var pp := p.global_position.lerp(c0, 0.5)
		return [pp + Vector3(sin(a) * 3.4, 0.7, cos(a) * 3.4), p.global_position + Vector3(0, 1.2, 0), 50.0]
	_cut("fight_orbit", cf2, 5.0)
	for i in 50:
		if _foes().is_empty():
			break
		await _secs(0.1)
	await _secs(0.6)


# 9. the clay golem
func _shot_golem() -> void:
	fighting = false
	_release_all()
	var g := _spawn("golem", p.global_position + Vector3(1.0, 0.1, -9.0), 0.0)
	_mine.append(g)
	g.hp = 150.0
	var cf := func(t: float) -> Array:
		var pp := p.global_position
		var gp := g.global_position
		return [pp + (pp - gp).normalized() * 2.6 + Vector3(0.9, 0.45, 0), gp + Vector3(0, 2.6, 0), 58.0]
	_cut("golem_reveal", cf, 4.0)
	await _secs(2.4)
	fighting = true
	await _secs(2.0)
	p.spring.spring_length = 4.6
	p.pitch = -0.12
	_cut("golem_fight")
	for i in 70:
		if not is_instance_valid(g) or g.is_dead():
			break
		await _secs(0.1)
	await _secs(1.2)
	fighting = false
	_release_all()


# 10. crane up from the victor to the Týn church under the moon
func _shot_finale() -> void:
	var pp := p.global_position
	p.yaw = 0.0
	var cf := func(t: float) -> Array:
		var u := _ease(t / 8.0)
		var from: Vector3 = Vector3(lerp(pp.x + 1.5, 7.0, u), lerp(1.2, 22.0, u), lerp(pp.z + 3.0, 26.0, u))
		var at: Vector3 = pp.lerp(Vector3(1.5, 14.0, -78.0), _ease(t / 6.0)) + Vector3(0, 1.4, 0)
		return [from, at, 55.0]
	cam_collide = false
	_cut("finale", cf, 0.0)
	await _secs(3.2)
	_title("Alchemists of Prague", 104, 330, UiKit.PARCH, 1.4, 3.2, 0.6)
	await _secs(0.8)
	_title("Play in your browser  ·  severance.lol/4", 40, 460, UiKit.GOLD, 1.2, 2.6, 0.6)
	await _secs(4.8)


func _probe() -> void:
	await _frames(30)
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = 110.0
	_look(Vector3(0, 120, 0.01), Vector3.ZERO)
	await _frames(20)
	await _still("plan")
	cam.projection = Camera3D.PROJECTION_PERSPECTIVE
	for t in [0.93, 0.05, 0.2, 0.28, 0.33, 0.37, 0.42, 0.6]:
		_tod(t)
		_look(Vector3(0, 30, 45), Vector3(0, 8, -40))
		await _frames(12)
		await _still("aerial_%03d" % int(t * 1000))
