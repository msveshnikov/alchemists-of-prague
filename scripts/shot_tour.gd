extends Node
## Screenshot tour (run with:  godot --path . scenes/game.tscn -- --tour x,z,yaw_deg[,pitch_deg[,y]] ...):
## puts the player at each spot, waits, saves renders/game/tour_N.png, then quits. For checking world edits by eye.
## A spot "cam,px,py,pz,tx,ty,tz" shoots from a free camera at p looking at t instead;
## "map,x,z,yaw_deg[,y]" puts the player at (x, z) and shoots the inventory Map tab (checks the map marker).

var world: Node


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_run.call_deferred()


func _run() -> void:
	var args := OS.get_cmdline_user_args()
	var spots: Array = []
	for i in range(args.find("--tour") + 1, args.size()):
		if args[i].begins_with("--"):
			break
		spots.append(args[i].split(","))
	var dir := ProjectSettings.globalize_path("res://renders/game/")
	DirAccess.make_dir_recursive_absolute(dir)
	Game.time_of_day = 0.05 if "--tour-night" not in args else 0.6
	var free_cam := Camera3D.new()
	free_cam.far = 1500.0
	world.add_child(free_cam)
	world.day_night.apply(Game.time_of_day)
	var k := 0
	for s in spots:
		var p: Player = world.player
		if s[0] == "cam":
			free_cam.global_position = Vector3(float(s[1]), float(s[2]), float(s[3]))
			free_cam.look_at(Vector3(float(s[4]), float(s[5]), float(s[6])))
			free_cam.current = true
			for f in 120:
				await get_tree().process_frame
			await RenderingServer.frame_post_draw
			get_viewport().get_texture().get_image().save_png(dir + "tour_%d.png" % k)
			print("TOUR shot %d at %s" % [k, s])
			k += 1
			continue
		if s[0] == "map":      # "map,x,z,yaw_deg": stand there, open Tab -> Map, shoot the map with the player arrow
			p.camera.current = true
			p.global_position = Vector3(float(s[1]), float(s[4]) if s.size() > 4 else 0.3, float(s[2]))
			p.velocity = Vector3.ZERO
			p.yaw = deg_to_rad(float(s[3]) if s.size() > 3 else 0.0)
			p.model.rotation.y = p.yaw + PI
			for f in 30:
				p.global_position = Vector3(float(s[1]), p.global_position.y, float(s[2]))
				await get_tree().process_frame
			var inv: Control = load("res://scripts/ui/inventory_ui.gd").new()
			world.open_ui(inv)
			await get_tree().process_frame
			var tabs: TabContainer = inv.find_children("*", "TabContainer", true, false)[0]
			tabs.current_tab = tabs.get_tab_count() - 1
			for f in 10:
				await get_tree().process_frame
			await RenderingServer.frame_post_draw
			get_viewport().get_texture().get_image().save_png(dir + "tour_%d.png" % k)
			print("TOUR map %d at %s" % [k, s])
			world.close_ui()
			k += 1
			continue
		p.camera.current = true
		var y := float(s[4]) if s.size() > 4 else 0.3
		p.global_position = Vector3(float(s[0]), y, float(s[1]))
		p.velocity = Vector3.ZERO
		p.yaw = deg_to_rad(float(s[2]))
		p.pitch = deg_to_rad(float(s[3])) if s.size() > 3 else -0.2
		p.model.rotation.y = p.yaw + PI
		for f in 90:
			p.global_position = Vector3(float(s[0]), p.global_position.y, float(s[1]))
			await get_tree().process_frame
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png(dir + "tour_%d.png" % k)
		print("TOUR shot %d at %s" % [k, s])
		k += 1
	get_tree().quit()
