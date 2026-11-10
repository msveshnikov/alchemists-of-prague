extends Node3D
## The Old Town level: built at runtime from Task 3/4 JSON (layout + population), plus game systems.

const LAYOUT := "res://assets/levels/old_town_layout.json"
const POPULATION := "res://assets/levels/old_town_population.json"
const HOUSE_DIMS := {  # asset: [width, depth, upper-floor height, inner facade inset]
	"house_burgher_a": [7.0, 12.0, 4.6, 0.5], "house_burgher_b": [6.5, 12.0, 4.6, 0.5], "house_burgher_c": [7.5, 12.0, 4.6, 0.5],
	"house_burgher_d": [8.5, 12.0, 4.6, 0.5], "house_burgher_e": [6.0, 12.0, 4.6, 0.5], "house_burgher_f": [9.0, 12.0, 4.6, 0.5],
	"house_gothic_tower": [8.0, 9.0, 3.6, 0.6],
}
const STOCK := {
	"produce": ["bread", "herb", "mushroom", "meat"], "bread": ["bread", "meat"], "meat": ["meat", "bread"],
	"pottery": ["potion_health", "potion_stamina", "potion_antidote", "quicksilver"],
	"cloth": ["gloves", "ring", "potion_stamina"], "weapons": ["helmet", "chainmail", "gloves", "potion_health"],
}

var layout: Dictionary
var population: Dictionary
var player: Player
var hud: Node
var day_night: DayNight
var env: Environment
var enemies: Array = []
var npcs: Array = []
var interactables: Array = []
var houses := {}
var markers_by_name := {}
var spawned := {}          # population id -> node
var inside_house := false
var current_house := ""
var interiors := {}        # house id -> {root, windows, enemies}
var hint_shown_grab := false
var anim_nodes: Array = []
var ui_stack: Array = []
var _loading: Control
var _music_cd := 0.0
var _ready_done := false


func _ready() -> void:
	_show_loading()
	await get_tree().process_frame
	await _build()


# ================================================================ build
func _show_loading() -> void:
	var cl := CanvasLayer.new()
	cl.layer = 50
	add_child(cl)
	_loading = Control.new()
	_loading.set_anchors_preset(Control.PRESET_FULL_RECT)
	cl.add_child(_loading)
	var bg := TextureRect.new()
	bg.texture = load("res://assets/ui/title.png")
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	bg.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	bg.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	bg.modulate = Color(0.45, 0.4, 0.35)
	_loading.add_child(bg)
	var l := UiKit.title("Loading the Old Town...", 52, UiKit.PARCH)
	l.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	l.position.y -= 120
	l.name = "Label"
	_loading.add_child(l)


func _set_loading(text: String) -> void:
	if _loading:
		_loading.get_node("Label").text = text


func _build() -> void:
	layout = JSON.parse_string(FileAccess.get_file_as_string(LAYOUT))
	population = JSON.parse_string(FileAccess.get_file_as_string(POPULATION))
	for m in layout["markers"]:
		markers_by_name[m["name"]] = m
	_build_environment()
	var n := 0
	var total: int = layout["instances"].size()
	for inst in layout["instances"]:
		_place(inst)
		n += 1
		if n % 40 == 0:
			_set_loading("Raising the Old Town... %d%%" % int(100.0 * n / total))
			await get_tree().process_frame
	for fx in population.get("fx", []):
		if fx["type"] == "prop":
			_place({"id": "fx_" + str(n), "asset": fx["asset"], "path": fx["path"], "pos": fx["pos"], "yaw_deg": fx["yaw_deg"]}, true)
			n += 1
		elif fx["type"] == "smoke":
			_smoke(Vector3(fx["pos"][0], fx["pos"][1], fx["pos"][2]))
	_set_loading("Waking the townsfolk...")
	await get_tree().process_frame
	_register_interactables()
	_spawn_player()
	hud = load("res://scripts/ui/hud.gd").new()
	hud.world = self
	add_child(hud)
	day_night.apply(Game.time_of_day)
	_apply_schedule(day_night.is_night)
	day_night.phase_changed.connect(_on_phase)
	Game.message.connect(_on_message)
	_loading.get_parent().queue_free()
	_loading = null
	_ready_done = true
	Game.capture_mouse()
	if Game.touch:
		_add_touch_controls()
	else:
		Game.touch_mode_changed.connect(_add_touch_controls, CONNECT_ONE_SHOT)
	if Game.pending_load.is_empty():
		if Game.touch:
			hud.hint("Left thumb: move (push past the ring to sprint) · Right thumb: look · Tap a potion to drink · Bag: inventory · Menu: save & settings")
		else:
			hud.hint("WASD move · Shift sprint · LMB strike · RMB block · Q dodge · E interact · Tab inventory · T wait · F5 save")
		Game.log_journal("I stand on the Old Town Square. By day the merchants trade; by night the alchemists' creatures walk.")
	Game.pending_load = {}
	if Game.autotest:
		var at = load("res://scripts/autotest.gd").new()
		at.world = self
		add_child(at)


var touch_controls: CanvasLayer = null


func _add_touch_controls() -> void:
	if touch_controls != null:
		return
	touch_controls = load("res://scripts/ui/touch_controls.gd").new()
	touch_controls.world = self
	add_child(touch_controls)


func _build_environment() -> void:
	var we := WorldEnvironment.new()
	env = Environment.new()
	env.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	var sm := ProceduralSkyMaterial.new()
	sm.sun_angle_max = 20.0
	sky.sky_material = sm
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_sky_contribution = 0.85
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.tonemap_exposure = 1.05
	env.glow_enabled = bool(Game.settings["glow"])
	env.glow_intensity = 0.6
	env.glow_bloom = 0.08
	env.glow_hdr_threshold = 1.1
	env.ssao_enabled = bool(Game.settings["ssao"])
	env.ssao_radius = 1.2
	env.ssao_intensity = 1.6
	env.fog_enabled = true
	env.fog_density = 0.0045
	env.fog_sky_affect = 0.25
	env.adjustment_enabled = true
	env.adjustment_saturation = 1.08
	env.adjustment_contrast = 1.05
	we.environment = env
	add_child(we)
	var sun := DirectionalLight3D.new()
	sun.shadow_enabled = bool(Game.settings["shadows"])
	sun.directional_shadow_max_distance = 90.0
	sun.shadow_blur = 1.5
	add_child(sun)
	var moon := MeshInstance3D.new()
	var mm := SphereMesh.new()
	mm.radius = 16.0
	mm.height = 32.0
	moon.mesh = mm
	var mmat := StandardMaterial3D.new()
	mmat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mmat.albedo_color = Color(0.92, 0.93, 1.0)
	mmat.disable_fog = true
	moon.material_override = mmat
	moon.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(moon)
	moon.position = Vector3(cos(deg_to_rad(30)) * sin(deg_to_rad(20)), sin(deg_to_rad(30)), -cos(deg_to_rad(30)) * cos(deg_to_rad(20))) * 900.0
	day_night = DayNight.new()
	add_child(day_night)
	day_night.setup(layout["lighting"]["keys"], sun, env, moon)


var _glow_shared := {}


func _place(inst: Dictionary, extra := false) -> void:
	var ps: PackedScene = load(inst["path"])
	if ps == null:
		push_warning("missing " + inst["path"])
		return
	var node: Node3D = ps.instantiate()
	node.name = String(inst["id"]).replace("#", "_")
	add_child(node)
	node.position = Vector3(inst["pos"][0], inst["pos"][1], inst["pos"][2])
	node.rotation.y = deg_to_rad(float(inst["yaw_deg"]))
	var asset: String = inst["asset"]
	if HOUSE_DIMS.has(asset):
		houses[inst["id"]] = {"node": node, "asset": asset}
	for l in node.find_children("LIGHT_*", "OmniLight3D", true, false):
		day_night.register_light(l)
	for mi in node.find_children("*", "MeshInstance3D", true, false):
		if mi.mesh == null:
			continue
		for i in mi.mesh.get_surface_count():
			var m: Material = mi.mesh.surface_get_material(i)
			if m == null:
				continue
			var rn: String = m.resource_name
			if rn.begins_with("M_WindowLit") or rn.begins_with("M_LanternGlass"):
				var key: String = rn.substr(0, 14)
				if not _glow_shared.has(key):
					var dup: BaseMaterial3D = m.duplicate()
					_glow_shared[key] = dup
					day_night.register_glow(dup)
				mi.set_surface_override_material(i, _glow_shared[key])
	for a in node.find_children("ANIM_*", "Node3D", true, false):
		anim_nodes.append(a)
	if asset in ["spit_roast", "forge", "cooking_pot"]:
		Sfx.loop_at("fire", node, -10.0, 3.0)


func _smoke(at: Vector3) -> void:
	var p := GPUParticles3D.new()
	p.amount = 24
	p.lifetime = 5.0
	var pm := ParticleProcessMaterial.new()
	pm.direction = Vector3(0.15, 1, 0.05)
	pm.spread = 12.0
	pm.initial_velocity_min = 0.8
	pm.initial_velocity_max = 1.4
	pm.gravity = Vector3(0.12, 0.25, 0.05)
	pm.scale_min = 0.8
	pm.scale_max = 1.6
	var curve := CurveTexture.new()
	var c := Curve.new()
	c.add_point(Vector2(0, 0.3))
	c.add_point(Vector2(1, 2.5))
	curve.curve = c
	pm.scale_curve = curve
	var grad := Gradient.new()
	grad.set_color(0, Color(0.3, 0.29, 0.28, 0.45))
	grad.set_color(1, Color(0.4, 0.4, 0.4, 0.0))
	var gt := GradientTexture1D.new()
	gt.gradient = grad
	pm.color_ramp = gt
	p.process_material = pm
	var q := QuadMesh.new()
	q.size = Vector2(1, 1)
	var m := StandardMaterial3D.new()
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	m.vertex_color_use_as_albedo = true
	var img := Image.create(64, 64, false, Image.FORMAT_RGBA8)
	for y in 64:
		for x in 64:
			var d := Vector2(x - 31.5, y - 31.5).length() / 32.0
			img.set_pixel(x, y, Color(1, 1, 1, clamp(1.0 - d, 0.0, 1.0) ** 1.6))
	m.albedo_texture = ImageTexture.create_from_image(img)
	q.material = m
	p.draw_pass_1 = q
	add_child(p)
	p.global_position = at


func marker(name: String) -> Dictionary:
	return markers_by_name.get(name, {})


static func v3(a: Array) -> Vector3:
	return Vector3(a[0], a[1], a[2])


func _register_interactables() -> void:
	for m in layout["markers"]:
		var owner_id: String = m.get("owner", "")
		match m["kind"]:
			"door":
				if houses.has(owner_id):
					var hid := owner_id
					interactables.append({"pos": v3(m["pos"]), "radius": 2.2, "kind": "door",
						"label": "Enter the house" + (" (searched)" if Game.looted_houses.has(hid) else ""),
						"action": func(): enter_house(hid), "enabled": func(): return not inside_house})
				elif owner_id.begins_with("old_town_hall"):
					interactables.append({"pos": v3(m["pos"]), "radius": 2.5, "kind": "door", "label": "Town Hall portal",
						"action": func(): Game.say("The councillors have barred the portal. \"Come back when the dead stop walking!\""),
						"enabled": func(): return not inside_house})
			"exit":
				var to: String = m.get("leads_to", "").replace("_", " ").capitalize()
				interactables.append({"pos": v3(m["pos"]), "radius": 3.0, "kind": "exit", "label": "Road to " + to,
					"action": func(): Game.say("The road to %s is closed for now — this chapter ends at the Old Town Square." % to),
					"enabled": func(): return not inside_house})
			"customer":
				var stall_id := owner_id
				var stall_type := stall_id.split("#")[0].replace("market_stall_", "")
				interactables.append({"pos": v3(m["pos"]), "radius": 2.4, "kind": "trade", "label": "Trade",
					"action": func(): open_trade(stall_id, stall_type), "enabled": func(): return _trader_present(stall_id)})
			"smith":
				if owner_id.begins_with("anvil"):
					interactables.append({"pos": v3(m["pos"]), "radius": 2.6, "kind": "smith", "label": "Blacksmith — improve your sword",
						"action": func(): open_ui(load("res://scripts/ui/smith_ui.gd").new()), "enabled": func(): return not day_night.is_night})
			"cook":
				var cp := v3(m["pos"])
				interactables.append({"pos": cp, "radius": 2.6, "kind": "cook", "label": "Buy roast pork (6 gold)",
					"action": func(): _buy_pork(), "enabled": func(): return not day_night.is_night})


func _trader_present(stall_id: String) -> bool:
	if day_night.is_night or inside_house:
		return false
	for id in spawned:
		var nd = spawned[id]
		if is_instance_valid(nd) and nd is Npc and nd.entry.get("stall", "") == stall_id and nd.role.begins_with("trader") and not nd.dead:
			return true
	return false


func _buy_pork() -> void:
	if Game.gold < 6:
		Game.say("Cook: \"Six groschen, knight. No coin, no pork.\"")
		return
	Game.add_gold(-6, true)
	Game.add_item("meat", 1)
	Sfx.play("coin")


func _spawn_player() -> void:
	player = Player.new()
	player.world = self
	add_child(player)
	var st: Dictionary = marker("MARK_player_start")
	player.global_position = v3(st["pos"]) + Vector3(0, 0.1, 0)
	player.yaw = deg_to_rad(st["yaw_deg"]) + PI
	if not Game.pending_load.is_empty() and Game.pending_load.has("pos"):
		player.global_position = v3(Game.pending_load["pos"]) + Vector3(0, 0.2, 0)
		player.yaw = float(Game.pending_load.get("yaw", 0.0))
	player.model.rotation.y = player.yaw + PI
	player.died.connect(_on_player_died)


func player_radius() -> float:
	return 0.34


# ================================================================ population & schedule
func _on_phase(is_night: bool) -> void:
	_apply_schedule(is_night)
	if hud:
		hud.add_message("Night falls over Prague. Lock your doors." if is_night else "Dawn. The merchants open their stalls.",
			Color(0.75, 0.8, 1.0) if is_night else Color(1.0, 0.9, 0.6))
	if not is_night:
		for h in interiors:
			_restore_windows(h)


func _apply_schedule(is_night: bool) -> void:
	for e in population["population"]:
		if e["character"] == "vaclav":
			continue
		var sched: String = e.get("schedule", "day")
		var want := sched == "always" or (sched == "night") == is_night
		var have: bool = spawned.has(e["id"]) and is_instance_valid(spawned[e["id"]])
		if want and not have:
			_spawn_entry(e)
		elif not want and have:
			var nd = spawned[e["id"]]
			if nd is Enemy and nd.is_hostile() and nd.global_position.distance_to(player.global_position) < 25.0:
				continue  # don't vanish mid-fight
			_despawn(nd)
			spawned.erase(e["id"])
	for e in enemies.duplicate():
		if is_instance_valid(e) and e.is_dead() and e.spawn_id == "":
			_despawn(e)


func _spawn_entry(e: Dictionary) -> void:
	var ch: String = e["character"]
	var p := v3(e["pos"])
	var yaw := deg_to_rad(float(e.get("yaw_deg", 0)))
	var node: Node3D
	if ch in ["alchemist", "skeleton", "golem", "guard"]:
		var en := Enemy.new()
		var idle: String = e.get("animation", "idle")
		if idle in ["walk", "run"]:
			idle = "idle"
		en.setup(ch, self, p, yaw, idle)
		en.spawn_id = e["id"]
		var r: Array = []
		for key in ["route", "route_points"]:
			for x in e.get(key, []):
				if x is String:
					var mk := marker(x)
					if not mk.is_empty():
						r.append(v3(mk["pos"]))
				else:
					r.append(v3(x))
		en.route = r
		add_child(en)
		enemies.append(en)
		node = en
	else:
		var npc := Npc.new()
		add_child(npc)
		npc.setup(self, e)
		npcs.append(npc)
		node = npc
		if not npc.role.begins_with("trader") and npc.role not in ["cook", "blacksmith", "cart_driver", "cart_horse"]:
			interactables.append({"pos": Vector3.ZERO, "radius": 1.8, "kind": "talk", "label": "Talk", "node": npc,
				"action": func(): _talk_to(npc),
				"enabled": func(): return is_instance_valid(npc) and not npc.dead and not inside_house})
	spawned[e["id"]] = node


func _despawn(nd: Node) -> void:
	enemies.erase(nd)
	npcs.erase(nd)
	interactables = interactables.filter(func(it): return not it.has("node") or it["node"] != nd)
	nd.queue_free()


func attackable() -> Array:
	var out: Array = []
	for e in enemies:
		if is_instance_valid(e) and not e.is_dead() and (e.interior != null) == inside_house:
			out.append(e)
	if not inside_house:
		for n in npcs:
			if is_instance_valid(n) and not n.dead:
				out.append(n)
	return out


func alert(pos: Vector3, r: float) -> void:
	for e in enemies:
		if is_instance_valid(e) and e.global_position.distance_to(pos) < r:
			e.alerted()


func on_enemy_killed(e: Enemy, by_fall: bool) -> void:
	var def: Dictionary = e.def
	if e.kind == "guard":
		Game.set_wanted(300.0)
		Game.say("You killed a guard of the city!", Color(1, 0.3, 0.2))
		return
	Game.kills[e.kind] = Game.kills.get(e.kind, 0) + 1
	var g := randi_range(def["gold"][0], def["gold"][1])
	if by_fall:
		g = int(g * 1.5) + 10
		Game.kills["defenestrated"] = Game.kills.get("defenestrated", 0) + 1
		Game.say("DEFENESTRATED! A Prague tradition.", Color(1.0, 0.75, 0.3))
		Game.log_journal("Threw a %s out of a window in the Old Town. Defenestrations so far: %d." % [def["name"].to_lower(), Game.kills["defenestrated"]])
	Game.add_gold(g)
	Sfx.play("coin")
	for item in def["loot"]:
		if randf() < def["loot"][item]:
			Game.add_item(item, 1)
	var total: int = Game.kills["alchemist"] + Game.kills["skeleton"] + Game.kills["golem"]
	if total in [1, 5, 10, 20]:
		Game.log_journal("Creatures of the alchemists slain: %d." % total)
	get_tree().create_timer(60.0).timeout.connect(_cleanup_corpse.bind(e))


func _cleanup_corpse(e) -> void:
	if is_instance_valid(e) and not inside_house:
		_despawn(e)


func _on_message(text: String, color: Color) -> void:
	if hud:
		hud.add_message(text, color)


func _talk_to(npc) -> void:
	if is_instance_valid(npc):
		npc.talk()


func throw_potion(from_enemy: Enemy, from: Vector3, target: Vector3) -> void:
	Potion.launch(self, from, target, randf() < 0.65)


# ================================================================ houses, interiors & windows
func _house_frame(hid: String) -> Dictionary:
	var h: Dictionary = houses[hid]
	var d: Array = HOUSE_DIMS[h["asset"]]
	return {"node": h["node"], "w": d[0], "depth": d[1], "floor": d[2], "inset": d[3]}


func enter_house(hid: String) -> void:
	if not interiors.has(hid):
		interiors[hid] = _build_interior(hid)
	var it: Dictionary = interiors[hid]
	var f := _house_frame(hid)
	var node: Node3D = f["node"]
	inside_house = true
	current_house = hid
	Sfx.play("door_open")
	player.global_position = node.to_global(Vector3(0, f["floor"] + 0.15, f["depth"] / 2.0 - 5.6))
	player.velocity = Vector3.ZERO
	player.yaw = node.rotation.y + PI
	player.model.rotation.y = node.rotation.y
	it["root"].visible = true
	for en in it["enemies"]:
		if is_instance_valid(en) and not en.is_dead():
			en.interior = it["root"]
	Game.say("You climb the stairs to the upper floor.", Color(0.85, 0.8, 0.7))
	if not Game.looted_houses.has(hid) and not Game.journal.has("houses"):
		hud.hint("Search chests to loot them — but if a guard sees you by day, you are a thief.")


func exit_house() -> void:
	if not inside_house:
		return
	var hid := current_house
	inside_house = false
	current_house = ""
	Sfx.play("door_close")
	var dm := marker("MARK_door@" + hid)
	var p: Vector3 = v3(dm["pos"]) if not dm.is_empty() else houses[hid]["node"].global_position
	player.global_position = p + Vector3(0, 0.1, 0)
	player.velocity = Vector3.ZERO
	if interiors.has(hid):
		interiors[hid]["root"].visible = false


func _mat(tex_name: String, scale := 0.5, color := Color.WHITE) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_texture = load("res://assets/textures/%s.png" % tex_name)
	m.albedo_color = color
	m.uv1_triplanar = true
	m.uv1_world_triplanar = true
	m.uv1_scale = Vector3.ONE * scale
	m.roughness = 0.9
	return m


func _box(parent: Node3D, center: Vector3, size: Vector3, mat: Material, collide := true) -> void:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	mi.material_override = mat
	mi.position = center
	parent.add_child(mi)
	if collide:
		var sb := StaticBody3D.new()
		var cs := CollisionShape3D.new()
		var bs := BoxShape3D.new()
		bs.size = size
		cs.shape = bs
		sb.add_child(cs)
		sb.position = center
		parent.add_child(sb)


func _build_interior(hid: String) -> Dictionary:
	var f := _house_frame(hid)
	var node: Node3D = f["node"]
	var root := Node3D.new()
	root.name = "Interior"
	node.add_child(root)
	var w: float = f["w"]
	var fy: float = f["floor"]
	var zf: float = f["depth"] / 2.0 - f["inset"]       # inner face of the facade (Godot +Z = front)
	var zb: float = zf - 6.5
	var xi: float = w / 2.0 - 0.45
	var hgt := 3.0
	var wood := _mat("wood_dark", 0.6)
	var plaster := _mat("plaster_cream", 0.35, Color(0.85, 0.8, 0.72))
	var timber := _mat("timber", 0.5)
	_box(root, Vector3(0, fy - 0.05, (zf + zb) / 2.0), Vector3(w - 0.4, 0.1, zf - zb + 0.4), wood)
	_box(root, Vector3(0, fy + hgt + 0.05, (zf + zb) / 2.0), Vector3(w - 0.4, 0.1, zf - zb + 0.4), timber)
	_box(root, Vector3(0, fy + hgt / 2.0, zb - 0.1), Vector3(w - 0.4, hgt, 0.2), plaster)
	_box(root, Vector3(-xi - 0.1, fy + hgt / 2.0, (zf + zb) / 2.0), Vector3(0.2, hgt, zf - zb), plaster)
	_box(root, Vector3(xi + 0.1, fy + hgt / 2.0, (zf + zb) / 2.0), Vector3(0.2, hgt, zf - zb), plaster)
	# invisible collider along the facade so the player cannot walk out through the windows
	var sb := StaticBody3D.new()
	var cs := CollisionShape3D.new()
	var bs := BoxShape3D.new()
	bs.size = Vector3(w, hgt, 0.2)
	cs.shape = bs
	sb.add_child(cs)
	sb.position = Vector3(0, fy + hgt / 2.0, zf - 0.05)
	root.add_child(sb)
	for k in range(int(w / 1.6)):
		_box(root, Vector3(-w / 2.0 + 0.8 + k * 1.6, fy + hgt - 0.12, (zf + zb) / 2.0), Vector3(0.2, 0.22, zf - zb), timber, false)
	var light := OmniLight3D.new()
	light.light_color = Color(1.0, 0.7, 0.4)
	light.light_energy = 1.8
	light.omni_range = 8.0
	light.shadow_enabled = true
	light.position = Vector3(0, fy + 2.4, (zf + zb) / 2.0)
	root.add_child(light)
	var props := [["table", Vector3(0.3, fy, zb + 2.6), 0.2], ["bench", Vector3(0.3, fy, zb + 1.6), 0.2],
		["stool", Vector3(-1.2, fy, zb + 2.8), 0.0], ["barrel_small", Vector3(xi - 0.5, fy, zb + 0.6), 0.0],
		["crate", Vector3(-xi + 0.6, fy, zb + 0.7), 0.3]]
	for pr in props:
		var ps: PackedScene = load("res://assets/props/%s.gltf" % pr[0])
		var pn: Node3D = ps.instantiate()
		root.add_child(pn)
		pn.position = pr[1]
		pn.rotation.y = pr[2]
	var candle := OmniLight3D.new()
	candle.light_color = Color(1.0, 0.6, 0.25)
	candle.light_energy = 0.8
	candle.omni_range = 4.0
	candle.position = Vector3(0.3, fy + 1.1, zb + 2.6)
	root.add_child(candle)
	# chest & stairs
	var chest_pos: Vector3 = node.to_global(Vector3(-xi + 0.6, fy + 0.4, zb + 0.7))
	interactables.append({"pos": chest_pos, "radius": 1.8, "kind": "chest", "label": "Search the chest",
		"action": func(): _loot_chest(hid), "enabled": func(): return inside_house and current_house == hid and not Game.looted_houses.has(hid)})
	var stairs: Vector3 = node.to_global(Vector3(xi - 0.6, fy, zb + 2.0))
	_box(root, Vector3(xi - 0.6, fy + 0.15, zb + 2.0), Vector3(0.9, 0.3, 1.2), wood, false)
	interactables.append({"pos": stairs, "radius": 1.8, "kind": "stairs", "label": "Go downstairs and leave",
		"action": func(): exit_house(), "enabled": func(): return inside_house and current_house == hid})
	# windows of this floor (INT_window_* nodes from Task 1)
	var windows: Array = []
	for wn in node.find_children("INT_window_*", "", true, false):
		if String(wn.name).contains("shutter") or not (wn is Node3D):
			continue
		var wp: Vector3 = wn.global_position
		if abs(wp.y - (node.global_position.y + fy + 0.9)) > 1.2:
			continue
		windows.append({"node": wn, "pos": wp + Vector3(0, 0.8, 0), "out": node.global_basis.z.normalized(), "mesh": wn.mesh if wn is MeshInstance3D else null})
	# occupants
	var occ: Array = []
	var night := day_night.is_night
	var first := interiors.is_empty()
	var count := 0
	if first:
		count = 1
	elif night:
		count = 1 + int(randf() < 0.5)
	elif randf() < 0.3:
		count = 1
	for i in count:
		var kind := "alchemist" if (first or randf() < 0.6) else "skeleton"
		var en := Enemy.new()
		var lp := Vector3(-0.8 + i * 1.6, fy + 0.1, zb + 4.0)
		en.setup(kind, self, node.to_global(lp), node.rotation.y + PI, "idle" if kind == "skeleton" else "cast")
		en.interior = root
		add_child(en)
		enemies.append(en)
		occ.append(en)
	if first:
		hud.hint("An alchemist hides in this house! Wound him, seize him (E) and throw him out of a window (E).")
	return {"root": root, "windows": windows, "enemies": occ}


func _loot_chest(hid: String) -> void:
	Game.looted_houses[hid] = true
	Sfx.play("chest_open")
	var g := randi_range(8, 35)
	Game.add_gold(g)
	Sfx.play("coin")
	var pool := ["bread", "herb", "mushroom", "key", "potion_health", "scroll", "ring", "quicksilver"]
	var weights := [0.5, 0.4, 0.3, 0.15, 0.2, 0.1, 0.04, 0.12]
	for i in pool.size():
		if randf() < weights[i]:
			Game.add_item(pool[i], 1)
	if not day_night.is_night:
		var door := v3(marker("MARK_door@" + hid).get("pos", [0, 0, 0]))
		for e in enemies:
			if is_instance_valid(e) and e.kind == "guard" and not e.is_dead() and e.global_position.distance_to(door) < 30.0:
				Game.set_wanted(120.0)
				Game.say("A guard saw you sneak in. Thief!", Color(1, 0.35, 0.3))
				return
	Game.say("Nobody saw you. This time.", Color(0.8, 0.8, 0.7))


func nearest_window(pos: Vector3) -> Dictionary:
	if not inside_house or not interiors.has(current_house):
		return {}
	var best := {}
	var bd := 2.4
	for w in interiors[current_house]["windows"]:
		var d: float = Vector2(pos.x - w["pos"].x, pos.z - w["pos"].z).length()
		if d < bd and abs(pos.y + 1.0 - w["pos"].y) < 1.5:
			bd = d
			best = w
	return best


func defenestrate(target: Enemy, w: Dictionary) -> void:
	var wn: Node3D = w["node"]
	if wn is MeshInstance3D:
		wn.mesh = null
	for sh in wn.get_children():
		if sh is Node3D and String(sh.name).contains("shutter"):
			var s := 1.0 if String(sh.name).ends_with("L") else -1.0
			var tw := create_tween()
			tw.tween_property(sh, "rotation:y", s * 0.6, 0.12)
			tw.tween_property(sh, "rotation:y", 0.0, 0.8).set_trans(Tween.TRANS_ELASTIC)
	Sfx.play_at("glass", w["pos"], 4.0)
	var out: Vector3 = w["out"]
	target.thrown(w["pos"] + out * 0.2, out * 6.5 + Vector3(0, 2.4, 0), true, w["pos"].y - 2.2)
	_glass_burst(w["pos"] + out * 0.3)
	player.shake = 0.5


func _glass_burst(at: Vector3) -> void:
	var p := GPUParticles3D.new()
	p.one_shot = true
	p.amount = 60
	p.lifetime = 1.6
	p.explosiveness = 1.0
	var pm := ParticleProcessMaterial.new()
	pm.direction = Vector3(0, 0.3, 1)
	pm.spread = 60.0
	pm.initial_velocity_min = 2.0
	pm.initial_velocity_max = 6.0
	pm.gravity = Vector3(0, -9.8, 0)
	pm.scale_min = 0.5
	pm.scale_max = 1.0
	p.process_material = pm
	var bm := BoxMesh.new()
	bm.size = Vector3(0.05, 0.05, 0.01)
	var m := StandardMaterial3D.new()
	m.albedo_color = Color(0.7, 0.85, 0.8)
	m.metallic = 0.6
	m.roughness = 0.1
	bm.material = m
	p.draw_pass_1 = bm
	add_child(p)
	p.global_position = at
	p.emitting = true
	get_tree().create_timer(2.5).timeout.connect(p.queue_free)


func _restore_windows(hid: String) -> void:
	for w in interiors[hid]["windows"]:
		if w["mesh"] and is_instance_valid(w["node"]):
			w["node"].mesh = w["mesh"]


# ================================================================ UI flow
func open_ui(ui: Control) -> void:
	var cl := CanvasLayer.new()
	cl.layer = 20
	cl.process_mode = Node.PROCESS_MODE_ALWAYS
	add_child(cl)
	ui.set("world", self)
	cl.add_child(ui)
	ui_stack.append(cl)
	get_tree().paused = true
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	hud.set_prompt("")


func close_ui() -> void:
	if ui_stack.is_empty():
		return
	var cl = ui_stack.pop_back()
	cl.queue_free()
	if ui_stack.is_empty():
		get_tree().paused = false
		if not player.dead:
			Game.capture_mouse()


func open_trade(stall_id: String, stall_type: String) -> void:
	var ui = load("res://scripts/ui/trade_ui.gd").new()
	ui.stock = STOCK.get(stall_type, ["bread"])
	ui.stall_type = stall_type
	for id in spawned:
		var nd = spawned[id]
		if is_instance_valid(nd) and nd is Npc and nd.entry.get("stall", "") == stall_id:
			ui.merchant = nd.character
	open_ui(ui)


func _on_player_died() -> void:
	await get_tree().create_timer(2.6).timeout
	open_ui(load("res://scripts/ui/death_ui.gd").new())


func quicksave() -> void:
	if player.dead:
		return
	var pos := player.global_position
	if inside_house:
		pos = v3(marker("MARK_door@" + current_house)["pos"])
	Game.save_game(pos, player.yaw)


func quickload() -> void:
	if Game.load_game():
		get_tree().paused = false
		get_tree().reload_current_scene()
	else:
		Game.say("No saved game.", Color(1, 0.6, 0.4))


func wait_until_next_phase() -> void:
	for e in enemies:
		if is_instance_valid(e) and e.is_hostile() and e.global_position.distance_to(player.global_position) < 30.0:
			Game.say("You cannot rest with enemies nearby!", Color(1, 0.5, 0.4))
			return
	var target := 165.0 / 400.0 if not day_night.is_night else 345.0 / 400.0
	if Game.time_of_day > target and not day_night.is_night:
		target = 165.0 / 400.0
	Game.time_of_day = target
	day_night.apply(Game.time_of_day)
	Game.say("You wait until %s..." % ("dusk" if target < 0.5 else "dawn"), Color(0.8, 0.8, 1.0))


func _unhandled_input(event: InputEvent) -> void:
	if not _ready_done:
		return
	if event.is_action_pressed("pause"):
		if ui_stack.is_empty():
			open_ui(load("res://scripts/ui/pause_ui.gd").new())
		else:
			var top = ui_stack.back().get_child(0)
			if top.has_method("can_close") and not top.can_close():
				return
			close_ui()
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("inventory") and not player.dead:
		if ui_stack.is_empty():
			open_ui(load("res://scripts/ui/inventory_ui.gd").new())
		elif ui_stack.back().get_child(0).get_script().resource_path.ends_with("inventory_ui.gd"):
			close_ui()
		get_viewport().set_input_as_handled()
	elif ui_stack.is_empty() and not player.dead:
		if event.is_action_pressed("quicksave"):
			quicksave()
		elif event.is_action_pressed("quickload"):
			quickload()
		elif event.is_action_pressed("wait"):
			wait_until_next_phase()


func _process(delta: float) -> void:
	if not _ready_done:
		return
	var t := Time.get_ticks_msec() / 1000.0
	for a in anim_nodes:
		if not is_instance_valid(a):
			continue
		if String(a.name).begins_with("ANIM_spit"):
			a.rotation.x = fmod(t * TAU / 4.0, TAU)
		elif String(a.name).begins_with("ANIM_banner"):
			a.rotation.x = deg_to_rad(4.0 * sin(t * TAU / 5.0) + 1.5 * sin(t * TAU / 1.7))
	if Game.wanted > 0.0:
		Game.wanted = max(0.0, Game.wanted - delta)
		if Game.wanted <= 0.0:
			Game.say("The guards have lost interest in you.", Color(0.7, 0.9, 0.7))
			Game.wanted_changed.emit(0.0)
	# ambience & music
	var night := day_night.night_amount()
	var near_sq: float = clamp(1.0 - Vector2(player.global_position.x, player.global_position.z).length() / 60.0, 0.0, 1.0)
	Sfx.ambience(0.0 if inside_house else (1.0 - night) * near_sq, night * (0.3 if inside_house else 1.0))
	_music_cd -= delta
	if _music_cd <= 0.0:
		_music_cd = 1.0
		var fighting := false
		for e in enemies:
			if is_instance_valid(e) and e.is_hostile() and e.global_position.distance_to(player.global_position) < 28.0:
				fighting = true
				break
		Sfx.music("battle_theme" if fighting else ("town_theme" if night < 0.5 else ""), 2.5)
