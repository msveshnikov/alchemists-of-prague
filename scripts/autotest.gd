extends Node
## Automated play-through (run with:  godot --path . -- --autotest).
## Exercises movement, combat, UI, trade, smith, house entry + defenestration, night, save/load, death.
## Screenshots -> renders/game/, log -> renders/game/autotest.log (and stdout, prefixed AUTOTEST).

var world: Node
var shots_dir := ""
var log_lines: PackedStringArray = []
var fails := 0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	shots_dir = ProjectSettings.globalize_path("res://renders/game/")
	DirAccess.make_dir_recursive_absolute(shots_dir)
	_run.call_deferred()


func _log(msg: String) -> void:
	print("AUTOTEST ", msg)
	log_lines.append(msg)


func _check(cond: bool, what: String) -> void:
	if cond:
		_log("PASS " + what)
	else:
		fails += 1
		_log("FAIL " + what)


func _wait(sec: float) -> void:
	await get_tree().create_timer(sec, true, false, true).timeout


func _shot(name: String) -> void:
	if DisplayServer.get_name() == "headless":
		_log("screenshot skipped (headless) " + name)
		return
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png(shots_dir + name + ".png")
	_log("screenshot " + name)


func _tap_key(key: Key) -> void:
	for pressed in [true, false]:
		var ev := InputEventKey.new()
		ev.keycode = key
		ev.physical_keycode = key
		ev.pressed = pressed
		Input.parse_input_event(ev)
		await _wait(0.12)


func _inventory_open() -> bool:
	return not world.ui_stack.is_empty() and world.ui_stack.back().get_child(0).get_script().resource_path.ends_with("inventory_ui.gd")


## Regression for "can't leave the inventory": every way in must have a way out, also after clicking inside it.
func _inventory_keys() -> void:
	for pair in [[KEY_TAB, KEY_TAB], [KEY_I, KEY_I], [KEY_TAB, KEY_ESCAPE], [KEY_I, KEY_TAB]]:
		await _tap_key(pair[0])
		var opened := _inventory_open()
		if opened:
			# click into the UI first: a focused button is what used to swallow Tab
			var inv = world.ui_stack.back().get_child(0)
			var btn: Button = inv.grid.get_child(0)
			btn.grab_focus()
			btn.pressed.emit()
			await _wait(0.2)
		await _tap_key(pair[1])
		var closed: bool = world.ui_stack.is_empty()
		_check(opened and closed, "inventory opens with %s and closes with %s (opened=%s closed=%s paused=%s)" % [OS.get_keycode_string(pair[0]), OS.get_keycode_string(pair[1]), opened, closed, get_tree().paused])
		while not world.ui_stack.is_empty():
			world.close_ui()
		await _wait(0.2)
	await _tap_key(KEY_TAB)
	var inv2 = world.ui_stack.back().get_child(0) if not world.ui_stack.is_empty() else null
	var close_btn: Button = null
	if inv2:
		for b in inv2.find_children("*", "Button", true, false):
			if b.text == "Close":
				close_btn = b
	_check(close_btn != null, "inventory has a Close button")
	if close_btn:
		close_btn.pressed.emit()
		await _wait(0.2)
	_check(world.ui_stack.is_empty() and not get_tree().paused, "Close button leaves the inventory and unpauses")
	while not world.ui_stack.is_empty():
		world.close_ui()


func _hold(action: String, sec: float) -> void:
	Input.action_press(action)
	await _wait(sec)
	Input.action_release(action)


func _run() -> void:
	var stage: int = Game.get_meta("autotest_stage", 0)
	if stage == 0:
		await _stage_main()
	elif stage == 1:
		await _stage_after_load()
	elif stage == 90:
		await _stage_verify_load()


func _stage_main() -> void:
	var p: Player = world.player
	_log("start: houses=%d enemies=%d npcs=%d interactables=%d" % [world.houses.size(), world.enemies.size(), world.npcs.size(), world.interactables.size()])
	_check(world.houses.size() > 100, "level built from layout JSON (houses > 100)")
	_check(world.npcs.size() > 30, "day population spawned (npcs > 30)")
	await _wait(2.5)
	p.yaw = 0.0   # look north towards Tyn church
	await _wait(0.6)
	await _shot("01_square_day")
	var start := p.global_position
	await _hold("move_forward", 2.0)
	_check(p.global_position.distance_to(start) > 2.0, "player moves (%.1f m)" % p.global_position.distance_to(start))
	await _npc_sanity()
	await _hold("sprint", 0.05)
	Input.action_press("sprint")
	await _hold("move_forward", 1.0)
	Input.action_release("sprint")
	Input.action_press("attack")
	await _wait(0.1)
	Input.action_release("attack")
	await _wait(0.3)
	_check(p.attacking > 0.0 or p.ap.current_animation == "attack", "attack animation plays")
	await _wait(1.0)
	await _shot("02_square_walk")
	# --- inventory (opened and closed with real key events, through the GUI like a player would)
	await _inventory_keys()
	if "--inv-only" in OS.get_cmdline_user_args():
		_log("DONE fails=%d" % fails)
		get_tree().quit(0 if fails == 0 else 1)
		return
	world.open_ui(load("res://scripts/ui/inventory_ui.gd").new())
	await _wait(1.0)
	await _shot("03_inventory")
	world.close_ui()
	await _wait(0.3)
	# --- trade
	var trade_it: Dictionary = {}
	for it in world.interactables:
		if it["kind"] == "trade" and it["enabled"].call():
			trade_it = it
			break
	_check(not trade_it.is_empty(), "a trader is open for business by day")
	if not trade_it.is_empty():
		p.global_position = trade_it["pos"] + Vector3(0, 0.1, 0)
		await _wait(0.4)
		trade_it["action"].call()
		await _wait(0.8)
		var ui = world.ui_stack.back().get_child(0)
		var g0 := Game.gold
		ui._buy(ui.stock[0])
		_check(Game.gold < g0, "buying deducts gold (%d -> %d)" % [g0, Game.gold])
		await _shot("04_trade")
		world.close_ui()
	# --- smith
	Game.add_gold(300, true)
	world.open_ui(load("res://scripts/ui/smith_ui.gd").new())
	await _wait(0.6)
	await _shot("05_smith")
	var ui2 = world.ui_stack.back().get_child(0)
	ui2._upgrade(Game.SWORDS[1]["cost"])
	_check(Game.sword_level == 1, "smith upgrades the sword")
	world.close_ui()
	# --- house + defenestration
	var door: Dictionary = {}
	var best := 1e9
	for it in world.interactables:
		if it["kind"] == "door" and String(it["label"]).begins_with("Enter"):
			var d: float = it["pos"].distance_to(p.global_position)
			if d < best:
				best = d
				door = it
	p.global_position = door["pos"] + Vector3(0, 0.1, 0)
	await _wait(0.5)
	await _shot("06_house_door")
	door["action"].call()
	await _wait(1.0)
	_check(world.inside_house, "entered a house interior")
	var interior: Dictionary = world.interiors[world.current_house]
	_check(interior["windows"].size() > 0, "interior has throwable windows (%d)" % interior["windows"].size())
	await _shot("07_interior")
	var foe: Enemy = null
	for e in interior["enemies"]:
		foe = e
	_check(foe != null, "first house hides an alchemist")
	if foe and interior["windows"].size() > 0:
		var w: Dictionary = interior["windows"][0]
		var out: Vector3 = w["out"]
		p.global_position = Vector3(w["pos"].x, foe.global_position.y + 0.05, w["pos"].z) - out * 1.3
		p.yaw = atan2(-out.x, -out.z) + PI
		p.model.rotation.y = atan2(out.x, out.z)
		foe.global_position = p.global_position + out * 0.9
		await _wait(0.3)
		foe.take_hit(foe.hp - foe.def["hp"] * 0.3, p)
		_check(foe.can_be_grabbed(), "wounded alchemist can be seized")
		p._update_focus()
		_check(p.focus.get("kind", "") == "grab", "prompt offers to seize the enemy")
		p._interact()
		await _wait(0.5)
		_check(p.grabbed == foe, "player holds the enemy")
		p._update_focus()
		_check(p.focus.get("kind", "") == "throw" and String(p.focus["label"]).contains("window"), "prompt offers to throw out of the window")
		var kills0: int = Game.kills["defenestrated"]
		p._interact()
		await _wait(0.35)
		await _shot("08_defenestration")
		for i in 50:                         # slow machines: wait for the fall itself, not a fixed time
			if not is_instance_valid(foe) or foe.is_dead():
				break
			await _wait(0.2)
		await _wait(0.5)
		_check(foe.is_dead(), "defenestrated alchemist dies on the cobbles")
		_check(Game.kills["defenestrated"] == kills0 + 1, "defenestration counted")
		_check(foe.global_position.y < 1.0, "body landed on the street (y=%.1f)" % foe.global_position.y)
	# chest
	for it in world.interactables:
		if it["kind"] == "chest" and it["enabled"].call():
			var g1 := Game.gold
			it["action"].call()
			_check(Game.gold > g1, "chest looted for gold")
			break
	world.exit_house()
	await _wait(0.8)
	_check(not world.inside_house, "left the house")
	p.yaw += PI
	await _wait(0.5)
	await _shot("09_body_on_street")
	# --- night
	Game.time_of_day = 252.0 / 400.0
	world.day_night.apply(Game.time_of_day)
	await _wait(2.0)
	_check(world.day_night.is_night, "night falls")
	var night_enemies := 0
	for e in world.enemies:
		if is_instance_valid(e) and e.kind != "guard" and not e.is_dead():
			night_enemies += 1
	_check(night_enemies >= 12, "night enemies spawned around the square (%d)" % night_enemies)
	var traders_open := false
	for it in world.interactables:
		if it["kind"] == "trade" and it["enabled"].call() and not String(it["label"]).begins_with("Tavern"):
			traders_open = true
	_check(not traders_open, "merchants closed at night")
	var st: Dictionary = world.marker("MARK_player_start")
	p.global_position = Vector3(st["pos"][0], 0.1, st["pos"][2])
	p.yaw = 0.0
	await _wait(1.5)
	await _shot("10_square_night")
	# fight skeletons in the Tyn court
	p.global_position = Vector3(1.5, 0.1, -50.0)
	p.yaw = 0.0   # facing the church (north)
	await _wait(3.0)
	var hostile := 0
	for e in world.enemies:
		if is_instance_valid(e) and e.is_hostile():
			hostile += 1
	_check(hostile > 0, "enemies notice the player at night (%d hostile)" % hostile)
	for i in 6:
		Input.action_press("attack")
		await _wait(0.1)
		Input.action_release("attack")
		await _wait(0.5)
	await _shot("11_night_fight")
	_check(Game.hp < Game.max_hp, "enemies deal damage (hp %d)" % Game.hp)
	Game.hp = Game.max_hp
	# the skeletons can kill the hero here; a dead hero can't save (quicksave() refuses), so bring him back first
	if p.dead:
		_log("hero fell in the night fight, reviving before the save")
		await _wait(3.0)                     # let the death screen open (2.6 s) so it can be closed
		while not world.ui_stack.is_empty():
			world.close_ui()
		p.revive()
	# --- save & load
	Game.time_of_day = 0.2
	world.day_night.apply(Game.time_of_day)
	p.global_position = Vector3(st["pos"][0], 0.1, st["pos"][2])
	await _wait(0.5)
	# remove any save from an earlier run, so "saved to disk" (and the gold check after loading) can't pass on a stale file
	if Game.has_save():
		DirAccess.remove_absolute(ProjectSettings.globalize_path(Game.SAVE_PATH))
	world.quicksave()
	_check(Game.has_save(), "game saved to disk")
	Game.set_meta("autotest_stage", 1)
	Game.set_meta("autotest_gold", Game.gold)
	Game.set_meta("autotest_fails", fails)
	Game.set_meta("autotest_log", log_lines)
	Game.add_gold(-Game.gold, true)
	_log("reloading save...")
	world.quickload()


func _stage_after_load() -> void:
	fails = Game.get_meta("autotest_fails", 0)
	log_lines = Game.get_meta("autotest_log", PackedStringArray())
	var p: Player = world.player
	await _wait(1.5)
	_check(Game.gold == Game.get_meta("autotest_gold", -1), "load restores gold (%d, saved %d)" % [Game.gold, Game.get_meta("autotest_gold", -1)])
	_check(Game.sword_level == 1, "load restores sword level")
	_check(Game.kills["defenestrated"] >= 1, "load restores kill counts")
	# --- death
	p.take_damage(9999.0, p.global_position + p.facing())
	await _wait(4.0)
	_check(p.dead, "player can die")
	_check(not world.ui_stack.is_empty(), "death screen shown")
	await _shot("12_death")
	# --- pause / settings
	world.close_ui()
	p.revive()
	Game.hp = Game.max_hp
	world.open_ui(load("res://scripts/ui/pause_ui.gd").new())
	await _wait(0.5)
	await _shot("13_pause")
	world.open_ui(load("res://scripts/ui/settings_ui.gd").new())
	await _wait(0.5)
	await _shot("14_settings")
	world.close_ui()
	world.close_ui()
	# --- on to the other parts of Prague (run 2): out through the Karlova exit
	Game.time_of_day = 0.93
	world.day_night.apply(Game.time_of_day)
	await _wait(0.5)
	await _stage_world()


# ================================================================ the joined world: walk between the districts
func _restore_log() -> void:
	fails = Game.get_meta("autotest_fails", 0)
	log_lines = Game.get_meta("autotest_log", PackedStringArray())


func _store_log(next_stage: int) -> void:
	Game.set_meta("autotest_stage", next_stage)
	Game.set_meta("autotest_fails", fails)
	Game.set_meta("autotest_log", log_lines)


## District-local position (as in the old per-district levels) -> world position.
func _at(d: String, local: Vector3) -> Vector3:
	for dd in world.districts:
		if dd["id"] == d:
			return local + Vector3(dd["offset"][0], dd["offset"][1], dd["offset"][2])
	return local


func _walk(from: Vector3, yaw: float, sec: float) -> void:
	var p: Player = world.player
	p.global_position = from
	p.velocity = Vector3.ZERO
	p.yaw = yaw
	await _wait(0.6)
	Input.action_press("move_forward")
	await _wait(sec)
	Input.action_release("move_forward")
	await _wait(0.4)


func _stage_world() -> void:
	var p: Player = world.player
	_check(world.districts.size() == 4, "one world with four districts (%d)" % world.districts.size())
	_log("fps on the Old Town Square: %d, instances %d" % [Engine.get_frames_per_second(), world.layout["instances"].size()])
	# Old Town -> along Karlova -> the street in front of the Old Town bridge tower
	await _walk(Vector3(-80.0, 0.2, 31.5), PI / 2.0, 12.0)
	_check(p.global_position.x < -100.0 and world.district == "charles_bridge",
		"walked from Karlova onto the bridge approach (x=%.0f, %s)" % [p.global_position.x, world.district])
	await _shot("world_01_karlova_to_bridge")
	# over the bridge, through the Lesser Town tower into Mala Strana
	await _walk(Vector3(-318.0, 0.2, 32.0), PI / 2.0, 11.0)
	_check(p.global_position.x < -342.0 and world.district == "mala_strana",
		"walked through the Lesser Town tower into Malá Strana (x=%.0f, %s)" % [p.global_position.x, world.district])
	await _shot("world_02_into_mala_strana")
	# from the end of Melantrichova up the road and into the Vysehrad gate lane
	await _walk(Vector3(2.0, 0.2, 94.0), PI, 28.0)
	_check(p.global_position.y > 9.0, "climbed the road towards Vyšehrad (y=%.1f)" % p.global_position.y)
	await _shot("world_03_road_up")
	Input.action_press("move_forward")
	p.yaw = PI / 2.0
	await _wait(16.0)
	Input.action_release("move_forward")
	await _wait(0.8)
	_check(p.global_position.x < -30.0 and world.district == "vysehrad",
		"walked along the gate lane into Vyšehrad (x=%.0f, %s)" % [p.global_position.x, world.district])
	await _shot("world_04_vysehrad_gate")
	_log("fps at Vyšehrad gate: %d, npcs spawned %d, enemies %d" % [Engine.get_frames_per_second(), world.npcs.size(), world.enemies.size()])
	# nobody leaves the world: past the end of an embankment street there is a wall
	await _walk(_at("charles_bridge", Vector3(78.0, 0.2, -150.0)), 0.0, 6.0)
	_check(p.global_position.z > -134.0, "the embankment street ends at a wall (z=%.0f)" % p.global_position.z)
	await _field_backstop()
	for d in ["charles_bridge", "mala_strana", "vysehrad"]:
		await _check_district(d)
	world.quicksave()
	_store_log(90)
	world.quickload()


## Regressions: townsfolk marching on the spot, the cart horse hanging on its cart, cart horses flying off at the turn.
func _npc_sanity() -> void:
	var on_spot := 0
	var horses := 0
	var driver: Npc = null
	for n in world.npcs:
		if not is_instance_valid(n):
			continue
		if n.anim in ["walk", "run", "pull"] and n.route.size() < 2 and n.role != "carter":
			on_spot += 1
		if n.character == "horse":
			horses += 1
			if n.role == "cart_driver" and driver == null:
				driver = n
	_check(on_spot == 0, "no townsfolk walk on the spot (%d)" % on_spot)
	if driver:
		# put the cart horse at the last stretch of its street, so it has to turn round with the cart
		var last: Vector3 = driver.route[driver.route.size() - 1]
		var prev: Vector3 = driver.route[driver.route.size() - 2]
		var d := (last - prev).normalized()
		driver.global_position = last - d * 2.0 + Vector3(0, 0.3, 0)
		driver.model.rotation.y = atan2(d.x, d.z)
		driver.route_i = driver.route.size() - 1
		driver.route_dir = 1
		await _wait(9.0)
		var back := (driver.route[driver.route.size() - 2] as Vector3) - last
		var heading := Vector3(sin(driver.model.rotation.y), 0, cos(driver.model.rotation.y))
		_check(heading.dot(back.normalized()) > 0.7, "cart horse turned round at the end of its street")
		_check(driver.global_position.y < driver.home.y + 0.6 and driver.cart.global_position.y < driver.home.y + 0.6,
			"cart horse and cart stay on the ground (y=%.2f, cart %.2f)" % [driver.global_position.y, driver.cart.global_position.y])
		_check(driver.global_position.distance_to(driver.cart.global_position) > 2.5, "horse does not walk into its cart")
	for n in world.npcs:
		if is_instance_valid(n) and n.character == "horse":
			_check(n.is_on_floor() and n.global_position.y < n.home.y + 0.6,
				"horse %s stands on the ground (y=%.2f, home %.2f)" % [n.entry["id"], n.global_position.y, n.home.y])


## Whatever gap the player finds in the town walls, he cannot stand on the field beyond them.
func _field_backstop() -> void:
	var p: Player = world.player
	var fi: Dictionary = world._field_info
	if fi.is_empty():
		_check(false, "field mask loaded from prague_seal.json")
		return
	var here := p.global_position
	var best := -1
	var best_d := INF
	for i in world._field.size():
		if world._field[i] == 1:
			var q := Vector3(float(fi["x0"]) + (i % int(fi["nx"]) + 0.5) * float(fi["cell"]), 0, float(fi["z0"]) + (i / int(fi["nx"]) + 0.5) * float(fi["cell"]))
			var dd := Vector2(q.x - here.x, q.z - here.z).length()
			if dd < best_d:
				best_d = dd
				best = i
	var fp := Vector3(float(fi["x0"]) + (best % int(fi["nx"]) + 0.5) * float(fi["cell"]), here.y + 0.5, float(fi["z0"]) + (best / int(fi["nx"]) + 0.5) * float(fi["cell"]))
	p.global_position = fp
	await _wait(0.3)
	var d2 := Vector2(p.global_position.x - fp.x, p.global_position.z - fp.z).length()
	_check(d2 > 0.5, "stepping onto the field beyond the walls is undone (%.1f m back)" % d2)


func _check_district(lv: String) -> void:
	var p: Player = world.player
	var st: Dictionary = world.marker("MARK_player_start@" + lv)
	p.global_position = world.v3(st["pos"]) + Vector3(0, 0.3, 0)
	p.yaw = deg_to_rad(float(st["yaw_deg"])) + PI
	world._stream_t = 0.0
	await _wait(2.5)
	_check(world.district == lv, "%s: the HUD names the district (%s)" % [lv, world.district])
	var near := 0
	for n in world.npcs:
		if is_instance_valid(n) and n.global_position.distance_to(p.global_position) < 120.0:
			near += 1
	_check(near >= 8, "%s: townsfolk around (%d)" % [lv, near])
	await _shot("%s_01_arrival" % lv)
	if lv == "charles_bridge":
		_check(world.water_y == -6.0, "Vltava water plane under the bridge")
		p.global_position = _at(lv, Vector3(20.0, 0.2, 0.0))
		p.yaw = -PI / 2.0
		await _wait(1.2)
		await _shot("%s_02_deck" % lv)
		await _throw_test(lv, "Vltava")
	elif lv == "mala_strana":
		var inn := {}
		var bed := {}
		for it in world.interactables:
			if it["kind"] == "trade" and String(it["label"]).begins_with("Tavern"):
				inn = it
			if it["kind"] == "inn":
				bed = it
		_check(not inn.is_empty() and not bed.is_empty(), "tavern: food & drink and a bed to rent")
		if not inn.is_empty():
			p.global_position = inn["pos"] + Vector3(0, 0.1, 0)
			await _wait(0.4)
			inn["action"].call()
			await _wait(0.6)
			_check(not world.ui_stack.is_empty(), "tavern trade window opens")
			await _shot("%s_02_tavern" % lv)
			world.close_ui()
			Game.add_gold(20, true)
			var t0 := Game.time_of_day
			bed["action"].call()
			_check(Game.time_of_day != t0 and Game.hp == Game.max_hp, "renting a bed passes time and heals")
			Game.time_of_day = 0.93
			world.day_night.apply(Game.time_of_day)
		await _walk(_at(lv, Vector3(12.0, 0.2, -4.0)), 0.0, 14.0)
		_check(p.global_position.y > 6.0, "climbed the castle stairs (y=%.1f)" % p.global_position.y)
		await _shot("%s_03_terrace" % lv)
		var door := {}
		var best := 1e9
		for it in world.interactables:
			if it["kind"] == "door" and String(it["label"]).begins_with("Enter"):
				var d: float = it["pos"].distance_to(_at(lv, Vector3(60, 0, 0)))
				if d < best:
					best = d
					door = it
		_check(not door.is_empty() and best < 30.0, "timber houses are enterable")
		if not door.is_empty():
			p.global_position = door["pos"] + Vector3(0, 0.1, 0)
			await _wait(0.3)
			door["action"].call()
			await _wait(0.8)
			_check(world.inside_house and world.interiors[world.current_house]["windows"].size() > 0,
				"timber house interior has throwable windows")
			await _shot("%s_04_interior" % lv)
			world.exit_house()
			await _wait(0.5)
	elif lv == "vysehrad":
		p.global_position = _at(lv, Vector3(-40.0, 0.2, 16.0))
		p.yaw = PI / 2.0
		world._stream_t = 0.0
		await _wait(2.5)
		var spar := 0
		for n in world.npcs:
			if is_instance_valid(n) and n.role == "knight_spar":
				spar += 1
		_check(spar >= 4, "knights spar on the training ground (%d)" % spar)
		await _shot("%s_02_training" % lv)
		await _throw_test(lv, "walls")
		p.global_position = _at(lv, Vector3(-52.0, 0.2, -30.0))
		p.yaw = PI * 0.5 + 0.6
		await _wait(1.0)
		await _shot("%s_03_view" % lv)
	# night
	p.global_position = world.v3(st["pos"]) + Vector3(0, 0.3, 0)
	Game.time_of_day = 252.0 / 400.0
	world.day_night.apply(Game.time_of_day)
	await _wait(2.0)
	var night_enemies := 0
	for e in world.enemies:
		if is_instance_valid(e) and e.kind != "guard" and not e.is_dead() and e.global_position.distance_to(p.global_position) < 130.0:
			night_enemies += 1
	_check(night_enemies >= 3, "%s: night enemies around (%d)" % [lv, night_enemies])
	p.yaw = deg_to_rad(float(st["yaw_deg"])) + PI
	await _wait(1.5)
	await _shot("%s_05_night" % lv)
	Game.time_of_day = 0.93
	world.day_night.apply(Game.time_of_day)
	for e in world.enemies.duplicate():
		if is_instance_valid(e) and e.kind != "guard":
			world._despawn(e)
	Game.hp = Game.max_hp
	await _wait(1.0)


## Seize a reeling skeleton at a ledge and throw it over (into the river / off the ramparts).
func _throw_test(lv: String, word: String) -> void:
	var p: Player = world.player
	var best := {}
	var bd := 1e9
	for l in world.ledges:
		var d: float = l["pos"].distance_to(p.global_position)
		if d < bd and abs(l["pos"].y - p.global_position.y) < 1.5:
			bd = d
			best = l
	_check(not best.is_empty(), "%s: a ledge to throw from" % lv)
	if best.is_empty():
		return
	var out: Vector3 = best["out"]
	p.global_position = best["pos"] + Vector3(0, 0.1, 0)
	p.yaw = atan2(-out.x, -out.z) + PI
	p.model.rotation.y = atan2(out.x, out.z)
	var foe := Enemy.new()
	foe.setup("skeleton", world, p.global_position + out * 0.9 + Vector3(0, 0.1, 0), atan2(-out.x, -out.z), "idle")
	world.add_child(foe)
	world.enemies.append(foe)
	await _wait(0.4)
	foe.take_hit(foe.hp - foe.def["hp"] * 0.3, p)
	p._update_focus()
	p._interact()
	await _wait(0.4)
	_check(p.grabbed == foe, "%s: seized the reeling skeleton" % lv)
	p.global_position = best["pos"] + Vector3(0, 0.1, 0)
	p._update_focus()
	_check(String(p.focus.get("label", "")).contains(word), "%s: prompt offers to throw him (%s)" % [lv, p.focus.get("label", "")])
	var k0: int = Game.kills["defenestrated"]
	p._interact()
	await _wait(0.5)
	await _shot("%s_06_throw" % lv)
	for i in 50:
		if not is_instance_valid(foe) or foe.is_dead():
			break
		await _wait(0.2)
	var gone := not is_instance_valid(foe) or foe.is_dead()
	_check(gone, "%s: the thrown skeleton is destroyed" % lv)
	_check(Game.kills["defenestrated"] == k0 + 1, "%s: counted as a defenestration" % lv)


func _stage_verify_load() -> void:
	_restore_log()
	await _wait(1.5)
	_check(world.district == "vysehrad", "loading a save puts the knight back where he was (%s)" % world.district)
	await _finish()


func _finish() -> void:
	get_tree().paused = false
	Game.autotest = false
	reparent(get_tree().root)
	get_tree().change_scene_to_file("res://scenes/main_menu.tscn")
	await _wait(1.0)
	await _shot("15_main_menu")
	_log("DONE fails=%d" % fails)
	var f := FileAccess.open(shots_dir + "autotest.log", FileAccess.WRITE)
	f.store_string("\n".join(log_lines))
	f.close()
	get_tree().quit(0 if fails == 0 else 1)
