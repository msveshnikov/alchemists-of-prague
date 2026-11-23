extends Node
## Clean screenshots for the store page (run with a 1920x1080 window:  godot --path . scenes/game.tscn -- --storeshots)
## -> renders/play/raw/sN_name.png. Fresh game state, no test chatter in the message feed.

var world: Node
var out := ""


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	out = ProjectSettings.globalize_path("res://renders/play/raw/")
	DirAccess.make_dir_recursive_absolute(out)
	_run.call_deferred()


func _wait(sec: float) -> void:
	await get_tree().create_timer(sec, true, false, true).timeout


var cam: Camera3D


## A composed shot: own camera at `pos` looking at `look` (the HUD stays). _cam_off() goes back to the hero's camera.
func _cam(pos: Vector3, look: Vector3) -> void:
	if cam == null:
		cam = Camera3D.new()
		cam.fov = 62.0
		cam.far = 1600.0
		world.add_child(cam)
	cam.global_position = pos
	cam.look_at(look)
	cam.current = true


func _cam_off() -> void:
	world.player.camera.current = true


## Remove every foe except `keep`, and any potion splashes flying around.
func _quiet(keep: Array = []) -> void:
	for e in world.enemies.duplicate():
		if is_instance_valid(e) and not e in keep:
			world.enemies.erase(e)
			e.queue_free()
	for n in world.get_children():
		if n.get_script() != null and String(n.get_script().resource_path).ends_with("potion.gd"):
			n.queue_free()


func _clean() -> void:
	var hud = world.hud
	hud.banner.modulate.a = 0.0
	for c in hud.feed.get_children():
		c.queue_free()
	hud.hint_panel.visible = false
	Game.wanted = 0.0


func _shot(name: String) -> void:
	_clean()
	await _wait(0.3)
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(out + name + ".png")
	print("STORESHOT ", name)


func _place(pos: Vector3, yaw_deg: float, pitch := -0.18) -> void:
	var p: Player = world.player
	if world.inside_house:
		world.exit_house()
	p.global_position = pos
	p.velocity = Vector3.ZERO
	p.yaw = deg_to_rad(yaw_deg)
	p.pitch = pitch
	p.model.rotation.y = p.yaw + PI
	world._stream_t = 0.0


func _day(t := 0.97) -> void:
	Game.time_of_day = t
	world.day_night.apply(t)


func _run() -> void:
	await _wait(3.0)
	Game.new_game()
	Game.gold = 420
	Game.inventory_changed.emit()
	Game.stats_changed.emit()
	_day()
	# 1. Old Town Square by day, the first quest on the HUD, Bořek with his "?"
	var borek = Quests.npc_nodes.get("borek")
	_place(Vector3(1.0, 0.2, 14.0), 0.0, -0.12)
	await _wait(6.0)
	_cam(Vector3(3.0, 7.5, 29.0), Vector3(2.0, 9.0, -70.0))
	await _wait(1.0)
	await _shot("s1_square")
	_cam_off()
	# 2. talking to Sergeant Bořek: the topics
	if borek:
		var bp2: Vector3 = borek.global_position
		_place(bp2 + Vector3(1.8, 0.2, 0.8), rad_to_deg(atan2(1.8, 0.8)), -0.15)
		await _wait(1.5)
		_cam(bp2 + Vector3(3.2, 1.9, -1.2), bp2 + Vector3(0.6, 1.35, 0.4))
		world.open_dialog(borek)
		await _wait(0.5)
		var ui = world.ui_stack.back().get_child(0)
		ui._next()
		await _wait(0.6)
		await _shot("s2_dialogue")
		world.close_ui()
		_cam_off()
	# 3. weapons stall: the bastard sword picked
	world.open_trade("market_stall_weapons#00", "weapons")
	await _wait(0.6)
	var tui = world.ui_stack.back().get_child(0)
	tui._pick("w_longsword")
	await _wait(0.4)
	await _shot("s3_weapons")
	world.close_ui()
	# 4./5. journal and map with several quests running
	for q in ["s_cloth", "s_toy", "s_pork"]:
		Quests.start(q)
	Quests.set_tracked("m1_night")
	var inv = load("res://scripts/ui/inventory_ui.gd").new()
	world.open_ui(inv)
	await _wait(0.6)
	var tabs: TabContainer = inv.find_children("*", "TabContainer", true, false)[0]
	tabs.current_tab = 2
	await _wait(0.6)
	await _shot("s4_journal")
	tabs.current_tab = 3
	await _wait(0.6)
	await _shot("s5_map")
	world.close_ui()
	# 6. night on the square: skeletons close in
	Game.time_of_day = 300.0 / 400.0
	world.day_night.apply(Game.time_of_day)
	_place(Vector3(2.0, 0.2, -6.0), 0.0, -0.2)
	await _wait(2.0)
	_quiet()
	var mine: Array = []
	for i in 3:
		var en := Enemy.new()
		en.setup("skeleton", world, world.player.global_position + Vector3(-2.5 + 2.5 * i, 0.2, -4.0 - (i % 2) * 1.5), PI)
		world.add_child(en)
		world.enemies.append(en)
		mine.append(en)
	await _wait(1.6)
	_quiet(mine)
	Input.action_press("attack")
	await _wait(0.1)
	Input.action_release("attack")
	await _wait(0.35)
	await _shot("s6_night_fight")
	Game.hp = Game.max_hp
	# 7. the clay giant on the Stone Bridge
	_day(0.12)
	var gol := Enemy.new()
	gol.setup("golem", world, Vector3(-206.0, 0.1, 32.0), deg_to_rad(90.0))
	gol.customize({"name": "The Bridge Golem"})
	world.add_child(gol)
	world.enemies.append(gol)
	_place(Vector3(-196.0, 0.3, 30.5), 90.0, -0.05)
	await _wait(3.0)
	await _shot("s7_bridge_golem")
	gol.queue_free()
	world.enemies.erase(gol)
	# 8. dusk on the Stone Bridge, lanterns lit, looking towards Malá Strana
	_quiet()
	Game.time_of_day = 0.45
	world.day_night.apply(Game.time_of_day)
	_place(Vector3(-262.0, 0.3, 32.0), 90.0, -0.05)
	await _wait(3.0)
	_cam(Vector3(-238.0, 5.0, 36.5), Vector3(-330.0, 6.0, 31.0))
	await _wait(1.0)
	await _shot("s8_bridge_dusk")
	_cam_off()
	get_tree().quit()
