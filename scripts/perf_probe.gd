extends Node
## Performance probe (run with:  godot --path . -- --perf): logs frame time, draw calls, objects, nodes and time spent in
## process / physics at a few spots of the joined world, then quits. Output lines are prefixed PERF.

var world: Node


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_run.call_deferred()


func _sample(tag: String, sec := 3.0) -> void:
	await get_tree().create_timer(sec, true, false, true).timeout
	var P := Performance
	print("PERF %s fps=%d frame_ms=%.1f process_ms=%.1f physics_ms=%.1f draws=%d objects=%d prims=%d nodes=%d npcs=%d enemies=%d lights=%d spawns=%d sched_ms=%.1f interactables=%d" % [
		tag, Engine.get_frames_per_second(), 1000.0 / max(1.0, Engine.get_frames_per_second()),
		P.get_monitor(P.TIME_PROCESS) * 1000.0, P.get_monitor(P.TIME_PHYSICS_PROCESS) * 1000.0,
		P.get_monitor(P.RENDER_TOTAL_DRAW_CALLS_IN_FRAME), P.get_monitor(P.RENDER_TOTAL_OBJECTS_IN_FRAME),
		P.get_monitor(P.RENDER_TOTAL_PRIMITIVES_IN_FRAME), P.get_monitor(P.OBJECT_NODE_COUNT),
		world.npcs.size(), world.enemies.size(), world.day_night.lamps.size(), world.spawn_count, world.sched_usec / 1000.0,
		world.interactables.size()])


func _run() -> void:
	var p: Node3D = world.player
	await _sample("start")
	await _sample("start_again")
	p.yaw = PI / 2.0
	await _sample("start_look_west")
	for spot in [["bridge", Vector3(-236, 0.3, 32), PI / 2.0], ["mala", Vector3(-420, 0.3, 32), PI / 2.0],
			["vysehrad", Vector3(-160, 10.3, 170), PI / 2.0]]:
		p.global_position = spot[1]
		p.yaw = spot[2]
		world._stream_t = 0.0
		await _sample(spot[0], 4.0)
	get_tree().quit()
