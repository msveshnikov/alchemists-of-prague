extends Node
## Plays every quest from start to finish in the real world (run with:  godot --path . scenes/game.tscn -- --quest-run).
## Walks (teleports) to every giver and target, talks through Quests.topics(), enters the quest houses, kills the
## quest's own foes, picks up the items. Catches wrong NPC / house / item ids, foes that fall through the ground,
## people that never spawn. Log: renders/game/quest_run.log; exit code 1 on any failure.

var world: Node
var fails := 0
var lines: PackedStringArray = []


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_run.call_deferred()


func _log(t: String) -> void:
	print("QUESTRUN ", t)
	lines.append(t)


func _check(ok: bool, what: String) -> bool:
	if not ok:
		fails += 1
	_log(("PASS " if ok else "FAIL ") + what)
	return ok


func _wait(sec: float) -> void:
	await get_tree().create_timer(sec, true, false, true).timeout


func _goto(p: Vector3) -> void:
	var pl: Player = world.player
	if world.inside_house:
		world.exit_house()
	pl.global_position = p + Vector3(0, 0.6, 0)
	pl.velocity = Vector3.ZERO
	await _wait(1.6)          # streaming tick spawns the people around, Quests.tick spawns foes / pickups


func _npc(id: String) -> Node:
	var n = Quests.npc_nodes.get(id)
	return n if n != null and is_instance_valid(n) and not n.dead else null


func _talk(id: String, topic_text: String) -> bool:
	var home: Vector3 = Quests.npc_home.get(id, Vector3.ZERO)
	await _goto(home + Vector3(1.5, 0, 1.5))
	var n := _npc(id)
	if not _check(n != null, "%s is there" % Quests.npc_name(id)):
		return false
	_check(n.global_position.distance_to(home) < 30.0 and n.global_position.y > home.y - 1.5,
		"%s stands where expected (%.1f m from home, y %.1f)" % [Quests.npc_name(id), n.global_position.distance_to(home), n.global_position.y])
	for t in Quests.topics(id):
		if t["text"] == topic_text and t["act"] is Callable:
			t["act"].call()
			return true
	_check(false, "topic \"%s\" offered by %s" % [topic_text, Quests.npc_name(id)])
	return false


func _run() -> void:
	for i in 8:
		await get_tree().physics_frame
	await _wait(2.0)
	Game.time_of_day = 0.93
	world.day_night.apply(Game.time_of_day)
	Game.gold = 5000
	for q in Quests.QUESTS:
		var qq: Dictionary = Quests.QUESTS[q]
		_log("=== %s (%s)" % [q, qq["title"]])
		if not Quests.state.has(q):
			if not _check(Quests.is_available(q), "%s is available" % q):
				continue
			await _talk(qq["giver"], qq["offer"])
		if not _check(Quests.is_active(q), "%s started" % q):
			continue
		var guard := 0
		while Quests.is_active(q) and guard < 8:
			guard += 1
			var st: int = Quests.state[q]["stage"]
			var s: Dictionary = Quests.stage(q)
			_log("stage %d: %s" % [st, s["do"]])
			_check(Quests.target(q) != null or s["do"] == "defenestrate", "stage %d has a target for the compass" % st)
			match s["do"]:
				"talk", "deliver":
					for id in s.get("items", {}):
						var need: int = int(s["items"][id]) - Game.count(id)
						if need > 0 and Game.ITEMS[id]["type"] != "quest":
							Game.add_item(id, need, true)
					_check(Quests.npc_marker(s["npc"]) == "?", "%s shows ?" % Quests.npc_name(s["npc"]))
					await _talk(s["npc"], s["topic"])
				"kill":
					if s.has("house"):
						var dm: Dictionary = world.marker("MARK_door@" + String(s["house"]))
						if not _check(not dm.is_empty() and world.houses.has(s["house"]), "house %s exists" % s["house"]):
							break
						await _goto(world.v3(dm["pos"]))
						world.enter_house(s["house"])
						await _wait(1.2)
					elif s.has("spawn"):
						var p0: Array = s["spawn"][0]["pos"]
						await _goto(Vector3(p0[0], p0[1], p0[2]) + Vector3(6, 0, 0))
						await _wait(1.5)
					else:
						await _goto(Vector3(s["at"][0], s["at"][1], s["at"][2]))
						for i in int(s["n"]):
							var en := Enemy.new()
							en.setup(s["kind"], world, world.player.global_position + Vector3(2 + i, 0.2, 0), 0.0)
							world.add_child(en)
							world.enemies.append(en)
					await _wait(0.5)
					var foes: Array = []
					for e in world.enemies:
						if is_instance_valid(e) and not e.is_dead() and (e.get_meta("quest", "") == q or not s.has("spawn")):
							if s.has("spawn") or e.global_position.distance_to(world.player.global_position) < 8.0:
								foes.append(e)
					_check(not foes.is_empty(), "foes of %s are present (%d)" % [q, foes.size()])
					for e in foes:
						var sp_y: float = e.home.y
						_check(e.global_position.y > sp_y - 1.0, "%s stands on the ground (y %.1f, spawned %.1f)" % [e.def["name"], e.global_position.y, sp_y])
					for e in foes:
						if is_instance_valid(e) and not e.is_dead():
							if e.duel:
								e.take_hit(e.hp * 0.8, world.player)
							else:
								e.take_hit(99999.0, world.player)
						await _wait(0.1)
					await _wait(0.4)
					if world.inside_house:
						world.exit_house()
				"pickup":
					await _goto(Vector3(s["pos"][0], s["pos"][1], s["pos"][2]) + Vector3(1, 0, 0))
					var done := false
					for it in world.interactables:
						if it.get("kind", "") == "pickup" and it["enabled"].call():
							it["action"].call()
							done = true
							break
					_check(done, "pickup lies at its spot")
				"defenestrate":
					for i in int(s["n"]):
						var en := Enemy.new()
						en.setup("skeleton", world, world.player.global_position + Vector3(3, 0.2, 0), 0.0)
						world.add_child(en)
						world.enemies.append(en)
						en.set_meta("thrown_from", "window")
						en._die(true)
					await _wait(0.3)
			await _wait(0.3)
			if Quests.is_active(q) and Quests.state[q]["stage"] == st:
				_check(false, "%s stage %d advanced" % [q, st])
				break
		_check(Quests.is_done(q), "%s completed" % q)
	_check(Game.weapon_id() == "w_vysehrad" or Game.count("w_vysehrad") == 1, "the Blade of Vyšehrad is the final reward")
	_check(Quests.done_quests().size() == Quests.QUESTS.size(), "all %d quests completed (%d)" % [Quests.QUESTS.size(), Quests.done_quests().size()])
	_log("DONE fails=%d level=%d xp=%d gold=%d" % [fails, Game.level, Game.xp, Game.gold])
	var f := FileAccess.open(ProjectSettings.globalize_path("res://renders/game/quest_run.log"), FileAccess.WRITE)
	f.store_string("\n".join(lines))
	f.close()
	get_tree().quit(0 if fails == 0 else 1)
