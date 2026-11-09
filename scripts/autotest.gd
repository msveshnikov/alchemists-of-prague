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


func _hold(action: String, sec: float) -> void:
	Input.action_press(action)
	await _wait(sec)
	Input.action_release(action)


func _run() -> void:
	var stage: int = Game.get_meta("autotest_stage", 0)
	if stage == 0:
		await _stage_main()
	else:
		await _stage_after_load()


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
	_check(p.global_position.distance_to(start) > 3.0, "player moves (%.1f m)" % p.global_position.distance_to(start))
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
	# --- inventory
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
		await _wait(2.6)
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
	_check(night_enemies >= 15, "night enemies spawned (%d)" % night_enemies)
	var traders_open := false
	for it in world.interactables:
		if it["kind"] == "trade" and it["enabled"].call():
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
	# --- save & load
	Game.time_of_day = 0.2
	world.day_night.apply(Game.time_of_day)
	p.global_position = Vector3(st["pos"][0], 0.1, st["pos"][2])
	await _wait(0.5)
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
	_check(Game.gold == Game.get_meta("autotest_gold", -1), "load restores gold (%d)" % Game.gold)
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
	# --- finish on the main menu
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
