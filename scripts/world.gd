extends Node3D
## Prague: one connected world — Old Town, Charles Bridge, Mala Strana, Vysehrad — built at runtime from
## assets/levels/prague_layout.json + prague_population.json (blender/scripts/build_prague.py), plus the game systems.
## The district under the player is named on the HUD; townsfolk and enemies are spawned around the player only.

const LEVELS := {"old_town": "Old Town Square", "charles_bridge": "Charles Bridge", "mala_strana": "Malá Strana", "vysehrad": "Vyšehrad"}
const CLOSED_ROADS := {
	"powder_gate": "The Powder Gate road is barred — the plague-carts block it.",
	"jewish_town": "The gate of the Jewish Town is shut for the night of mourning.",
	"castle": "The castle guard crosses halberds: \"No one passes to the King without a summons.\"",
}
const FOG := {"old_town": 0.0045, "charles_bridge": 0.0022, "mala_strana": 0.003, "vysehrad": 0.0016}
const WORLD := "prague"
const SEAL_FILE := "res://assets/levels/prague_seal.json"
const SPAWN_R := 105.0         # population entries closer than this to the player are spawned...
const DESPAWN_R := 150.0       # ...and removed again beyond this (unless fighting)
const NEAR_ONLY := ["street_lantern", "barrel", "barrel_small", "crate", "crate_produce", "sack", "basket", "bench", "table",
	"stool", "planter", "pottery", "bread_tray", "gravestone", "grave_cross", "training_dummy", "archery_target", "fence_wood",
	"weapon_rack", "cart", "cooking_pot", "wall_torch", "hand_lantern", "boat_row", "rock_outcrop", "flag_pole", "tree",
	"pine_tree", "jetty", "guard_booth", "bridge_statue", "garden_wall", "market_stall_bread", "market_stall_produce",
	"market_stall_pottery", "market_stall_cloth", "market_stall_meat", "market_stall_weapons", "spit_roast", "anvil", "forge",
	"blacksmith_shed", "watchtower_wood", "banner_lion", "boat_barge"]
const ARRIVAL_LINES := {
	"charles_bridge": "The stone bridge over the Vltava. Throw the alchemists' creatures over the parapet — the river keeps no secrets.",
	"mala_strana": "Malá Strana, the Lesser Town below the castle. The tavern under the stairs has beds and beer.",
	"vysehrad": "Vyšehrad, my home. The garrison trains on the ramparts; the old graves stir at night.",
}
const HOUSE_DIMS := {  # asset: [width, depth, upper-floor height, inner facade inset]
	"house_burgher_a": [7.0, 12.0, 4.6, 0.5], "house_burgher_b": [6.5, 12.0, 4.6, 0.5], "house_burgher_c": [7.5, 12.0, 4.6, 0.5],
	"house_burgher_d": [8.5, 12.0, 4.6, 0.5], "house_burgher_e": [6.0, 12.0, 4.6, 0.5], "house_burgher_f": [9.0, 12.0, 4.6, 0.5],
	"house_gothic_tower": [8.0, 9.0, 3.6, 0.6],
	"house_timber_a": [7.5, 11.0, 3.8, 0.45], "house_timber_b": [9.0, 11.0, 3.8, 0.45], "house_timber_c": [6.5, 11.0, 3.8, 0.45],
	"house_timber_d": [8.0, 11.0, 3.8, 0.45],
}
const STOCK := {
	"produce": ["bread", "herb", "mushroom", "meat"], "bread": ["bread", "meat"], "meat": ["meat", "bread"],
	"pottery": ["potion_health", "potion_stamina", "potion_antidote", "quicksilver"],
	"cloth": ["gloves", "ring", "potion_stamina"], "weapons": ["helmet", "chainmail", "gloves", "potion_health"],
	"tavern": ["bread", "meat", "potion_stamina", "potion_health", "herb", "mushroom"],
}

var level := WORLD
var district := ""         # part of the city the player is in (old_town, charles_bridge, mala_strana, vysehrad)
var districts: Array = []
var _district_t := 0.0
var _stream_t := 0.0
var _phase_serial := 0
var killed := {}           # population id -> phase serial in which it died (no respawn until the next phase)
var layout: Dictionary
var population: Dictionary
var ledges: Array = []     # throw spots over parapets / walls: {pos, out, label, water}
var water_y := -INF        # river surface of this level (for splashes)
var kill_y := -60.0        # anything below this has fallen off the world
var _safe_pos := Vector3.ZERO
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
var hidden_tiles := {}     # ground tiles beyond the town walls (prague_seal.json): not placed, the meadow shows instead
var river: Node3D


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
	var l := UiKit.title("Prague, Anno Domini 1357...", 52, UiKit.PARCH)
	l.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	l.position.y -= 120
	l.name = "Label"
	_loading.add_child(l)


func _set_loading(text: String) -> void:
	if _loading:
		_loading.get_node("Label").text = text


func _build() -> void:
	level = WORLD
	var args := OS.get_cmdline_user_args()
	if "--layout" in args:          # debugging: load one of the old single-district levels instead
		level = args[args.find("--layout") + 1]
	layout = JSON.parse_string(FileAccess.get_file_as_string("res://assets/levels/%s_layout.json" % level))
	population = JSON.parse_string(FileAccess.get_file_as_string("res://assets/levels/%s_population.json" % level))
	for m in layout["markers"]:
		markers_by_name[m["name"]] = m
	districts = layout.get("districts", [])
	var order := ["vysehrad", "mala_strana", "charles_bridge", "old_town"]   # first matching rectangle wins
	districts.sort_custom(func(a, b): return order.find(a["id"]) < order.find(b["id"]))
	kill_y = float(layout.get("kill_y", -60.0))
	# saves from the time the districts were separate levels: move their position into the joined world
	if not Game.pending_load.is_empty() and Game.pending_load.has("pos") and LEVELS.has(Game.location):
		for d in districts:
			if d["id"] == Game.location:
				var o: Array = d["offset"]
				var p: Array = Game.pending_load["pos"]
				Game.pending_load["pos"] = [float(p[0]) + o[0], float(p[1]) + o[1], float(p[2]) + o[2]]
	Game.location = WORLD
	_build_environment()
	_build_water()
	_build_blockers()
	_build_seal()
	var n := 0
	var total: int = layout["instances"].size()
	for inst in layout["instances"]:
		if hidden_tiles.has(inst["id"]):
			continue
		_place(inst)
		n += 1
		if n % 40 == 0:
			_set_loading("Raising Prague... %d%%" % int(100.0 * n / total))
			await get_tree().process_frame
	for fx in population.get("fx", []):
		if fx["type"] == "prop":
			_place({"id": "fx_" + str(n), "asset": fx["asset"], "path": fx["path"], "pos": fx["pos"], "yaw_deg": fx["yaw_deg"]}, true)
			n += 1
		elif fx["type"] == "smoke":
			_smoke(Vector3(fx["pos"][0], fx["pos"][1], fx["pos"][2]))
	if water_y > -INF and level == WORLD:
		river = load("res://scripts/river.gd").new()
		add_child(river)
		river.setup(self)
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
		if Game.arrive_from == "":
			if Game.touch:
				hud.hint("Left thumb: move (push past the ring to sprint) · Right thumb: look · Tap a potion to drink · Bag: inventory · Menu: save & settings")
			else:
				hud.hint("WASD move · Shift sprint · LMB strike · RMB block · Q dodge · E interact · Tab inventory · T wait · F5 save")
		if Game.visited.is_empty():
			Game.log_journal("Karlova leads west to the stone bridge and Malá Strana beyond the Vltava; Melantrichova leads south and up to Vyšehrad.")
	_update_district(true)
	Game.pending_load = {}
	Game.arrive_from = ""
	if "--perf" in OS.get_cmdline_user_args():
		var pp = load("res://scripts/perf_probe.gd").new()
		pp.world = self
		add_child(pp)
	if "--reach" in OS.get_cmdline_user_args():       # reachability map of the world (renders/world/reach.png)
		var rp = load("res://scripts/reach_probe.gd").new()
		rp.world = self
		add_child(rp)
	if "--tour" in OS.get_cmdline_user_args():        # screenshots at given spots (renders/game/tour_N.png)
		var st = load("res://scripts/shot_tour.gd").new()
		st.world = self
		add_child(st)
	if "--cinematic" in OS.get_cmdline_user_args():   # scripted trailer camera (record with --write-movie)
		var cine = load("res://scripts/cinematic.gd").new()
		cine.world = self
		add_child(cine)
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
	var vis := 0.0
	if asset in NEAR_ONLY:
		vis = 85.0 if asset not in ["market_stall_bread", "market_stall_produce", "market_stall_pottery", "market_stall_cloth",
			"market_stall_meat", "market_stall_weapons", "blacksmith_shed", "watchtower_wood", "guard_booth"] else 130.0
	elif asset.begins_with("ground_"):
		vis = 190.0
	elif HOUSE_DIMS.has(asset) or asset in ["arch_passage", "tavern", "castle_stairs"]:
		vis = 230.0
	if vis > 0.0:
		for gi in node.find_children("*", "GeometryInstance3D", true, false):
			gi.visibility_range_end = vis
			gi.visibility_range_end_margin = 12.0
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
				var dest: String = m.get("leads_to", "")
				var to: String = LEVELS.get(dest, dest.replace("_", " ").capitalize())
				if LEVELS.has(dest):
					interactables.append({"pos": v3(m["pos"]), "radius": 3.2, "kind": "exit", "label": "Road to " + to,
						"action": func(): travel(dest), "enabled": func(): return not inside_house})
				else:
					interactables.append({"pos": v3(m["pos"]), "radius": 3.0, "kind": "exit", "label": "Road to " + to,
						"action": func(): Game.say(CLOSED_ROADS.get(dest, "The road to %s is closed." % to)),
						"enabled": func(): return not inside_house})
			"ledge":
				var yaw := deg_to_rad(float(m["yaw_deg"]))
				var out := Vector3(sin(yaw), 0, cos(yaw))
				var over_water := water_y > -INF and v3(m["pos"]).y > water_y
				var lbl := "Throw him into the Vltava!" if owner_id.begins_with("bridge_span") or owner_id.begins_with("embankment") \
					else ("Throw him off the walls!" if owner_id.begins_with("fortress") else "Throw him off the terrace!")
				ledges.append({"pos": v3(m["pos"]), "out": out, "label": lbl, "water": over_water and not owner_id.begins_with("fortress")})
			"inn":
				var ip := v3(m["pos"])
				interactables.append({"pos": ip - Vector3(1.0, 0, 0), "radius": 2.0, "kind": "trade", "label": "Tavern «At the Golden Tankard» — food & drink",
					"action": func(): open_trade("", "tavern"), "enabled": func(): return not inside_house})
				interactables.append({"pos": ip + Vector3(2.2, 0, 0), "radius": 2.0, "kind": "inn", "label": "Rent a bed (10 gold) — sleep and heal",
					"action": func(): _rent_bed(), "enabled": func(): return not inside_house})
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
	var arrive: Dictionary = marker("MARK_exit_" + Game.arrive_from) if Game.arrive_from != "" else {}
	if not arrive.is_empty():
		var ay := deg_to_rad(float(arrive["yaw_deg"]))
		player.global_position = v3(arrive["pos"]) + Vector3(sin(ay), 0, cos(ay)) * 5.0 + Vector3(0, 0.15, 0)
		player.yaw = ay + PI
	if not Game.pending_load.is_empty() and Game.pending_load.has("pos"):
		player.global_position = v3(Game.pending_load["pos"]) + Vector3(0, 0.2, 0)
		player.yaw = float(Game.pending_load.get("yaw", 0.0))
	_safe_pos = player.global_position
	player.model.rotation.y = player.yaw + PI
	player.died.connect(_on_player_died)


func player_radius() -> float:
	return 0.34


# ================================================================ population & schedule
func _on_phase(is_night: bool) -> void:
	_phase_serial += 1
	_apply_schedule(is_night)
	if hud:
		hud.add_message("Night falls over Prague. Lock your doors." if is_night else "Dawn. The merchants open their stalls.",
			Color(0.75, 0.8, 1.0) if is_night else Color(1.0, 0.9, 0.6))
	if not is_night:
		for h in interiors:
			_restore_windows(h)


func _apply_schedule(is_night: bool, phase_change := true) -> void:
	var pp: Vector3 = player.global_position if player else Vector3.ZERO
	for e in population["population"]:
		if e["character"] == "vaclav":
			continue
		var id: String = e["id"]
		var sched: String = e.get("schedule", "day")
		var want := sched == "always" or (sched == "night") == is_night
		var have: bool = spawned.has(id) and is_instance_valid(spawned[id])
		if have:
			var nd = spawned[id]
			var far: bool = nd.global_position.distance_to(pp) > DESPAWN_R
			if want and not far:
				continue
			if nd is Enemy and nd.is_hostile() and nd.global_position.distance_to(pp) < 25.0:
				continue  # don't vanish mid-fight
			if nd.is_dead():
				killed[id] = _phase_serial
			_despawn(nd)
			spawned.erase(id)
		elif want and killed.get(id, -1) != _phase_serial:
			var ep: Array = e["pos"]
			if Vector3(ep[0], ep[1], ep[2]).distance_to(pp) < SPAWN_R:
				_spawn_entry(e)
	if not phase_change:
		return    # streaming tick: corpses stay where they fell (cleaned up after a minute or at dawn/dusk)
	for e in enemies.duplicate():
		if is_instance_valid(e) and e.is_dead() and e.spawn_id == "":
			_despawn(e)


var spawn_count := 0
var sched_usec := 0
var process_usec := 0


func _spawn_entry(e: Dictionary) -> void:
	spawn_count += 1
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
	if e.spawn_id != "":
		killed[e.spawn_id] = _phase_serial
	if e.kind == "guard":
		Game.set_wanted(300.0)
		Game.say("You killed a guard of the city!", Color(1, 0.3, 0.2))
		return
	Game.kills[e.kind] = Game.kills.get(e.kind, 0) + 1
	var g := randi_range(def["gold"][0], def["gold"][1])
	if by_fall:
		g = int(g * 1.5) + 10
		Game.kills["defenestrated"] = Game.kills.get("defenestrated", 0) + 1
		var how: String = e.get_meta("thrown_from", "window")
		Game.say({"window": "DEFENESTRATED! A Prague tradition.", "water": "Into the Vltava with him!",
			"wall": "Over the walls of Vyšehrad!", "terrace": "DEFENESTRATED — from the terrace!"}.get(how, "DEFENESTRATED!"), Color(1.0, 0.75, 0.3))
		var where: String = {"window": "out of a window", "water": "off the bridge into the Vltava", "wall": "off the walls of Vyšehrad",
			"terrace": "off a terrace"}.get(how, "out of a window")
		Game.log_journal("Threw a %s %s in %s. Defenestrations so far: %d." % [def["name"].to_lower(), where, district_name(district), Game.kills["defenestrated"]])
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
	if not inside_house:
		var bl := {}
		var bdl := 2.6
		for l in ledges:
			var dl: float = Vector2(pos.x - l["pos"].x, pos.z - l["pos"].z).length()
			if dl < bdl and abs(pos.y - l["pos"].y) < 1.5:
				bdl = dl
				bl = l
		return bl
	if not interiors.has(current_house):
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
	if w.has("label"):   # a ledge: bridge parapet, embankment, rampart or terrace
		var o: Vector3 = w["out"]
		target.set_meta("thrown_from", "water" if w["water"] else ("wall" if String(w["label"]).contains("walls") else "terrace"))
		target.thrown(w["pos"] + o * 0.6 + Vector3(0, 1.7, 0), o * 6.5 + Vector3(0, 3.6, 0), true, w["pos"].y - 2.5)
		player.shake = 0.5
		return
	target.set_meta("thrown_from", "window")
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



# ================================================================ districts & world edge
func district_at(p: Vector3) -> String:
	for d in districts:
		var r: Array = d["rect"]
		if p.x >= r[0] and p.x <= r[2] and p.z >= r[1] and p.z <= r[3]:
			return d["id"]
	return district if district != "" else "old_town"


func district_name(id: String) -> String:
	for d in districts:
		if d["id"] == id:
			return d["name"]
	return LEVELS.get(id, "Prague")


func _update_district(force: bool) -> void:
	if player == null:
		return
	var d := district_at(player.global_position)
	if d == district and not force:
		return
	district = d
	if hud and hud.has_method("set_place"):
		hud.set_place(district_name(d))
	var fog: float = FOG.get(d, 0.0045)
	if env:
		create_tween().tween_property(env, "fog_density", fog, 2.5)
	if not Game.visited.has(d):
		Game.visited[d] = true
		if ARRIVAL_LINES.has(d):
			Game.log_journal(ARRIVAL_LINES[d])
		elif d == "old_town":
			Game.log_journal("I stand on the Old Town Square. By day the merchants trade; by night the alchemists' creatures walk.")
	elif not force and hud:
		hud.add_message(district_name(d), Color(1.0, 0.9, 0.6))


func _build_blockers() -> void:
	for b in layout.get("blockers", []):
		var sb := StaticBody3D.new()
		var cs := CollisionShape3D.new()
		var bs := BoxShape3D.new()
		bs.size = Vector3(b["size"][0], b["size"][1], b["size"][2])
		cs.shape = bs
		sb.add_child(cs)
		add_child(sb)
		sb.position = Vector3(b["center"][0], b["center"][1], b["center"][2])


## Stone walls that close the alleys and street ends between the districts and the empty land around them
## (assets/levels/prague_seal.json, made by tools/seal_world.py). Narrow ones get a barred plank gate.
func _build_seal() -> void:
	if level != WORLD or "--no-seal" in OS.get_cmdline_user_args() or not FileAccess.file_exists(SEAL_FILE):
		return
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(SEAL_FILE))
	for id in data.get("hidden_tiles", []):
		hidden_tiles[id] = true
	var mats := {"stone": _mat("stone_wall_rough", 0.4, Color(0.92, 0.9, 0.86)), "cap": _mat("roof_tiles", 0.6),
		"trim": _mat("stone_trim", 0.5), "wood": _mat("wood_door", 0.5), "iron": _mat("iron", 1.0, Color(0.35, 0.35, 0.36))}
	var root := Node3D.new()
	root.name = "SealWalls"
	add_child(root)
	for w in data.get("walls", []):
		_seal_wall(root, Vector3(w["a"][0], w["y"], w["a"][1]), Vector3(w["b"][0], w["y"], w["b"][1]), mats)


func _seal_wall(root: Node3D, a: Vector3, b: Vector3, mats: Dictionary) -> void:
	const H := 3.1          # stone up to here (from 0.4 below the floor), then the tiled coping
	const T := 0.7
	var length := a.distance_to(b)
	var wall := Node3D.new()
	root.add_child(wall)
	wall.position = (a + b) / 2.0
	wall.rotation.y = atan2(b.x - a.x, b.z - a.z)            # local +Z runs along the wall
	var parts: Array = [[Vector3(0, H / 2.0 - 0.4, 0), Vector3(T, H, length), "stone"],
		[Vector3(0, H - 0.4 + 0.06, 0), Vector3(T + 0.16, 0.12, length + 0.1), "trim"]]
	if length > 7.0:          # buttresses on long stretches
		var n := int(length / 4.5)
		for k in range(1, n):
			parts.append([Vector3(0, H / 2.0 - 0.6, -length / 2.0 + k * length / n), Vector3(T + 0.5, H - 0.4, 0.8), "stone"])
	if length >= 1.8 and length <= 5.5:   # a courtyard gate, barred for good
		var gl: float = min(length - 0.7, 2.6)
		parts.append([Vector3(0, 1.05 - 0.02, 0), Vector3(T + 0.1, 2.1, gl), "wood"])
		for y in [0.45, 1.6]:
			parts.append([Vector3(0, y, 0), Vector3(T + 0.14, 0.09, gl + 0.04), "iron"])
		parts.append([Vector3(0, 2.18, 0), Vector3(T + 0.12, 0.16, gl + 0.3), "trim"])
	for p in parts:
		var mi := MeshInstance3D.new()
		var bm := BoxMesh.new()
		bm.size = p[1]
		mi.mesh = bm
		mi.material_override = mats[p[2]]
		mi.position = p[0]
		mi.visibility_range_end = 200.0
		wall.add_child(mi)
	var cap := MeshInstance3D.new()
	var pm := PrismMesh.new()
	pm.size = Vector3(T + 0.3, 0.42, length + 0.1)
	cap.mesh = pm
	cap.material_override = mats["cap"]
	cap.position = Vector3(0, H - 0.4 + 0.12 + 0.21, 0)
	cap.visibility_range_end = 200.0
	wall.add_child(cap)
	var sb := StaticBody3D.new()
	var cs := CollisionShape3D.new()
	var bs := BoxShape3D.new()
	bs.size = Vector3(T + 0.1, 6.0, length)     # taller than it looks: no jumping or climbing over
	cs.shape = bs
	sb.add_child(cs)
	sb.position = Vector3(0, 2.6, 0)
	wall.add_child(sb)


# ================================================================ river, falls, travel, inn
func _build_water() -> void:
	for w in layout.get("water", []):
		water_y = max(water_y, float(w["height"]))
		_plane(w["rect"], float(w["height"]), _water_material())
	for pl in layout.get("planes", []):
		_plane(pl["rect"], float(pl["height"]), _mat(pl.get("material", "grass"), 0.08, Color(0.8, 0.85, 0.75)))


func _plane(rect: Array, h: float, mat: Material) -> void:
	var mi := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(float(rect[2]) - float(rect[0]), float(rect[3]) - float(rect[1]))
	mi.mesh = pm
	mi.material_override = mat
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(mi)
	mi.position = Vector3((float(rect[0]) + float(rect[2])) / 2.0, h, (float(rect[1]) + float(rect[3])) / 2.0)


func _water_material() -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = load("res://assets/shaders/water.gdshader")
	return m


## Falls below the world: the player climbs out (river) or is carried back; enemies are finished off by Enemy.
func _check_falls() -> void:
	if player.is_on_floor() and not inside_house and player.global_position.y > kill_y + 2.0:
		_safe_pos = player.global_position
	if player.global_position.y < kill_y and not player.dead:
		var wet := water_y > -INF and player.global_position.y < water_y + 1.5
		if wet:
			_splash(Vector3(player.global_position.x, water_y, player.global_position.z))
		player.global_position = _safe_pos + Vector3(0, 0.3, 0)
		player.velocity = Vector3.ZERO
		player.take_damage(12.0, player.global_position, "splash")
		Game.say("You haul yourself out of the Vltava, soaked and freezing." if wet else "You climb back, bruised.", Color(0.7, 0.85, 1.0))


func enemy_fell(e: Node3D) -> void:
	if water_y > -INF and e.global_position.y < water_y + 2.0:
		_splash(Vector3(e.global_position.x, water_y, e.global_position.z))
		Sfx.play_at("potion_splash", e.global_position, 6.0, 0.6)


func _splash(at: Vector3) -> void:
	var p := GPUParticles3D.new()
	p.one_shot = true
	p.amount = 80
	p.lifetime = 1.4
	p.explosiveness = 0.95
	var pm := ParticleProcessMaterial.new()
	pm.direction = Vector3(0, 1, 0)
	pm.spread = 35.0
	pm.initial_velocity_min = 3.0
	pm.initial_velocity_max = 7.0
	pm.gravity = Vector3(0, -9.8, 0)
	pm.scale_min = 0.6
	pm.scale_max = 1.4
	p.process_material = pm
	var sm := SphereMesh.new()
	sm.radius = 0.06
	sm.height = 0.12
	var m := StandardMaterial3D.new()
	m.albedo_color = Color(0.8, 0.9, 0.95, 0.8)
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.roughness = 0.1
	sm.material = m
	p.draw_pass_1 = sm
	add_child(p)
	p.global_position = at
	p.emitting = true
	get_tree().create_timer(2.0).timeout.connect(p.queue_free)


## Leave for another part of Prague: the level is rebuilt around the exit marker that leads back here.
func travel(dest: String) -> void:
	if not LEVELS.has(dest) or player.dead:
		return
	for e in enemies:
		if is_instance_valid(e) and e.is_hostile() and e.global_position.distance_to(player.global_position) < 18.0:
			Game.say("You cannot leave with enemies at your heels!", Color(1, 0.5, 0.4))
			return
	Sfx.play("door_open", -6.0, 0.8)
	Game.arrive_from = level
	Game.location = dest
	Game.pending_load = {}
	get_tree().paused = false
	get_tree().reload_current_scene()


func _rent_bed() -> void:
	if Game.gold < 10:
		Game.say("Innkeeper: \"Ten groschen for the bed, knight. Coin first.\"")
		return
	for e in enemies:
		if is_instance_valid(e) and e.is_hostile() and e.global_position.distance_to(player.global_position) < 30.0:
			Game.say("You cannot rest with enemies nearby!", Color(1, 0.5, 0.4))
			return
	Game.add_gold(-10, true)
	Sfx.play("coin")
	Game.hp = Game.max_hp
	Game.stamina = Game.max_stamina()
	Game.poison_time = 0.0
	Game.stats_changed.emit()
	var target := 345.0 / 400.0 if day_night.is_night else 165.0 / 400.0
	Game.time_of_day = target
	day_night.apply(Game.time_of_day)
	Game.say("You sleep in a lumpy bed above the taproom and wake refreshed.", Color(0.85, 0.85, 1.0))


## Map tab: which plan image to show and the world X/Z rectangle it covers.
## "rect" = Rect2(x0, z0, width, depth): image left/top edge = x0/z0 (north is up), right/bottom = x0+w / z0+d.
## Layouts give either "rect": [x0, z0, x1, z1] (painted map) or a square "center" + "size" (ortho plan render).
func map_info() -> Dictionary:
	var mi: Dictionary = layout.get("map", {})
	if mi.is_empty():
		mi = {"image": "res://assets/ui/map.png", "center": [5.0, 8.0], "size": 230.0}
	if mi.has("rect"):
		var r: Array = mi["rect"]
		return {"image": mi["image"], "rect": Rect2(r[0], r[1], r[2] - r[0], r[3] - r[1])}
	var s := float(mi["size"])
	return {"image": mi["image"], "rect": Rect2(mi["center"][0] - s / 2.0, mi["center"][1] - s / 2.0, s, s)}


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
		if is_instance_valid(nd) and nd is Npc and ((stall_id != "" and nd.entry.get("stall", "") == stall_id) or
				(stall_id == "" and nd.role == "innkeeper")):
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


## Opening a window pauses the tree, and the world itself is pausable, so its _unhandled_input goes silent
## while any window is open. Closing keys are therefore handled by this always-processing relay, in _input
## (before the GUI), so a focused button cannot swallow Tab as focus navigation either.
class UiInput extends Node:
	var world: Node

	func _input(event: InputEvent) -> void:
		if world.ui_stack.is_empty() or event.is_echo():
			return
		var top: Control = world.ui_stack.back().get_child(0)
		if event.is_action_pressed("pause") or (event.is_action_pressed("inventory") and world.is_inventory(top)):
			get_viewport().set_input_as_handled()
			if top.has_method("can_close") and not top.can_close():
				return
			world.close_ui()


func is_inventory(ui: Node) -> bool:
	return ui != null and ui.get_script() != null and ui.get_script().resource_path.ends_with("inventory_ui.gd")


func _enter_tree() -> void:
	var relay := UiInput.new()
	relay.name = "UiInput"
	relay.world = self
	relay.process_mode = Node.PROCESS_MODE_ALWAYS
	add_child(relay)


func _unhandled_input(event: InputEvent) -> void:
	if not _ready_done or not ui_stack.is_empty():
		return
	if event.is_action_pressed("pause"):
		open_ui(load("res://scripts/ui/pause_ui.gd").new())
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("inventory") and not player.dead:
		open_ui(load("res://scripts/ui/inventory_ui.gd").new())
		get_viewport().set_input_as_handled()
	elif not player.dead:
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
	var near_sq: float = 0.45
	if district == "old_town":
		near_sq = clamp(1.0 - Vector2(player.global_position.x, player.global_position.z).length() / 60.0, 0.0, 1.0)
	_check_falls()
	_district_t -= delta
	if _district_t <= 0.0:
		_district_t = 0.5
		_update_district(false)
	_stream_t -= delta
	if _stream_t <= 0.0 and not inside_house:
		_stream_t = 1.0
		var t0 := Time.get_ticks_usec()
		_apply_schedule(day_night.is_night, false)
		sched_usec = Time.get_ticks_usec() - t0
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
