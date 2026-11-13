extends Node3D
## River traffic on the Vltava: boats moored along both embankments, and punts, cargo barges and big sailing barges
## that travel up and down the river through the arches of the Charles Bridge. A boatman poles at the stern, barges
## carry a lantern that is lit at night, and the sailing barges lower their mast to pass under the bridge.
## Purely decorative (no collision); far vessels are hidden and their boatmen stop animating.

const BARGE := "res://assets/props/boat_barge.gltf"
const ROW := "res://assets/props/boat_row.gltf"
const Z_MIN := -330.0        # vessels wrap around between these (far beyond the fog, where nobody looks)
const Z_MAX := 430.0
const SHOW_R := 240.0
const SHIP_SCALE := 1.45

var world: Node
var water := -6.0
var bridge_z := 32.0
var movers: Array = []       # {node, x, z, speed, dir, ap, phase, near, mast, sail}
var bobbers: Array = []      # {node, base_y, phase}
var _t := 0.0
var _vis_t := 0.0
var _canvas: StandardMaterial3D
var _wood: StandardMaterial3D


func setup(p_world: Node) -> void:
	world = p_world
	water = world.water_y
	var w: Dictionary = world.layout["water"][0]
	var x0: float = w["rect"][0]   # west bank (Mala Strana side)
	var x1: float = w["rect"][2]   # east bank (Old Town side)
	var rnd := RandomNumberGenerator.new()
	rnd.seed = 1357
	_canvas = StandardMaterial3D.new()
	_canvas.albedo_texture = load("res://assets/textures/canvas_striped.png")
	_canvas.cull_mode = BaseMaterial3D.CULL_DISABLED
	_canvas.roughness = 0.95
	_wood = StandardMaterial3D.new()
	_wood.albedo_texture = load("res://assets/textures/timber.png")
	_wood.roughness = 0.9
	# --- moored along the embankment walls (length along the bank), clear of the bridge, the jetty and the old boats
	var bays: Array = []
	var taken: Array = []
	for i in world.layout["instances"]:
		if i["asset"] in ["boat_row", "boat_barge", "jetty"]:
			taken.append(Vector2(i["pos"][0], i["pos"][2]))
		elif i["asset"] == "bridge_span":
			bays.append(float(i["pos"][0]))
			bridge_z = float(i["pos"][2])
	bays.sort()
	var moor := [[x1 - 2.2, -128.0, ROW], [x1 - 2.2, -116.0, ROW], [x1 - 2.2, -110.5, ROW], [x1 - 2.6, -84.0, BARGE],
		[x1 - 2.2, -52.0, ROW], [x1 - 2.2, -14.0, ROW], [x1 - 2.2, -8.5, ROW], [x1 - 2.2, 58.0, ROW], [x1 - 2.6, 112.0, BARGE],
		[x1 - 2.2, 150.0, ROW], [x1 - 2.2, 155.5, ROW], [x1 - 2.6, 190.0, BARGE],
		[x0 + 2.2, -124.0, ROW], [x0 + 2.2, -92.0, ROW], [x0 + 2.2, -86.5, ROW], [x0 + 2.6, -50.0, BARGE], [x0 + 2.2, -8.0, ROW],
		[x0 + 2.2, 68.0, ROW], [x0 + 2.2, 73.5, ROW], [x0 + 2.2, 96.0, ROW], [x0 + 2.6, 160.0, BARGE], [x0 + 2.2, 188.0, ROW],
		[x0 + 2.2, 193.5, ROW], [x0 + 2.6, 230.0, BARGE]]
	for m in moor:
		var p := Vector2(m[0], m[1])
		var clash: bool = abs(p.y - bridge_z) < 18.0
		for t in taken:
			if p.distance_to(t) < 7.0:
				clash = true
		if clash:
			continue
		var b := _boat(m[2])
		add_child(b)
		b.position = Vector3(p.x, water, p.y)
		b.rotation.y = deg_to_rad(90.0 + rnd.randf_range(-6.0, 6.0) + (180.0 if rnd.randf() < 0.5 else 0.0))
		bobbers.append({"node": b, "base_y": water, "phase": rnd.randf() * TAU})
	# --- travelling through the two middle arches: two lanes per bay (downstream = north = -Z, upstream slower)
	if bays.size() < 4:
		return
	var plan := [["ship", "punt", "barge"], ["barge", "punt", "ship"], ["punt", "barge", "ship"], ["ship", "barge", "punt"]]
	var lanes := [[bays[2] - 4.0, -1.0], [bays[2] + 4.0, 1.0], [bays[3] - 4.0, -1.0], [bays[3] + 4.0, 1.0]]
	for li in lanes.size():
		var dir: float = lanes[li][1]
		var speed := rnd.randf_range(2.0, 2.5) if dir < 0 else rnd.randf_range(1.2, 1.5)
		for j in 3:
			var z := lerpf(-170.0, 290.0, fmod(j / 3.0 + li * 0.27 + 0.08, 1.0))   # all in sight of the bridge at first
			movers.append(_mover(plan[li][j], lanes[li][0], z, speed, dir, rnd))


func _boat(path: String) -> Node3D:
	var b: Node3D = load(path).instantiate()
	for gi in b.find_children("*", "GeometryInstance3D", true, false):
		gi.visibility_range_end = SHOW_R
		gi.visibility_range_end_margin = 15.0
	return b


func _part(parent: Node3D, mesh: Mesh, mat: Material, pos: Vector3) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = mat
	mi.position = pos
	mi.visibility_range_end = SHOW_R
	parent.add_child(mi)
	return mi


func _mover(kind: String, x: float, z: float, speed: float, dir: float, rnd: RandomNumberGenerator) -> Dictionary:
	var v := Node3D.new()        # the vessel: moves and bobs; hull and crew are children
	add_child(v)
	var barge := kind != "punt"
	var s := SHIP_SCALE if kind == "ship" else 1.0
	var hull := _boat(BARGE if barge else ROW)
	hull.scale = Vector3.ONE * s
	v.add_child(hull)
	# barge bow = local -X (steering oar astern at +X); the punt is poled stern-first along local +X
	var fwd := -1.0 if barge else 1.0
	v.rotation.y = (-PI / 2.0 if dir < 0 else PI / 2.0) * fwd
	var man := Chars.instance("boatman")
	v.add_child(man)
	man.position = Vector3(3.3 * s, 0.12 * s, 0.0) if barge else Vector3(-1.5, -0.15, 0.0)
	man.rotation.y = PI / 2.0 * fwd
	for gi in man.find_children("*", "GeometryInstance3D", true, false):
		gi.visibility_range_end = 140.0
	var ap := Chars.anim_player(man)
	Chars.play(ap, "work", 0.0, rnd.randf_range(0.7, 0.9))
	if ap:
		ap.seek(rnd.randf() * Chars.length(ap, "work"), true)
	var out := {"node": v, "x": x, "z": z, "speed": speed, "dir": dir, "ap": ap, "phase": rnd.randf() * TAU, "near": true,
		"mast": null, "sail": null}
	if not barge:
		return out
	# lantern on a pole at the bow, lit by the day/night cycle
	var bow := -4.1 * s
	var pole := CylinderMesh.new()
	pole.top_radius = 0.035
	pole.bottom_radius = 0.035
	pole.height = 1.8
	_part(v, pole, _wood, Vector3(bow, 0.9 + 0.1 * s, 0.0))
	var gm := StandardMaterial3D.new()
	gm.albedo_color = Color(1.0, 0.75, 0.4)
	gm.emission_enabled = true
	gm.emission = Color(1.0, 0.62, 0.28)
	gm.emission_energy_multiplier = 1.5
	var lb := BoxMesh.new()
	lb.size = Vector3(0.22, 0.3, 0.22)
	_part(v, lb, gm, Vector3(bow, 1.95 + 0.1 * s, 0.0))
	world.day_night.register_glow(gm)
	var l := OmniLight3D.new()
	l.name = "LIGHT_boat"
	l.light_color = Color(1.0, 0.68, 0.35)
	l.light_energy = 1.6
	l.omni_range = 9.0
	l.position = Vector3(bow, 2.0, 0.0)
	v.add_child(l)
	world.day_night.register_light(l)
	if kind != "ship":
		return out
	# sailing barge: a hinged mast on a post in front of the cover, square striped sail on a yard
	var post := BoxMesh.new()
	post.size = Vector3(0.3, 2.3, 0.3)
	_part(v, post, _wood, Vector3(-3.0 * s, 1.15, 0.0))
	var mast := Node3D.new()
	mast.position = Vector3(-3.0 * s, 2.25, 0.0)
	v.add_child(mast)
	var mm := CylinderMesh.new()
	mm.top_radius = 0.07
	mm.bottom_radius = 0.12
	mm.height = 7.0
	_part(mast, mm, _wood, Vector3(0, 3.5, 0))
	var yard := CylinderMesh.new()
	yard.top_radius = 0.06
	yard.bottom_radius = 0.06
	yard.height = 4.6
	var ym := _part(mast, yard, _wood, Vector3(0.1, 6.5, 0))
	ym.rotation.x = PI / 2.0
	var sail := Node3D.new()                # pivot at the yard so the sail furls upwards
	sail.position = Vector3(0.18, 6.45, 0)
	mast.add_child(sail)
	var sm := BoxMesh.new()
	sm.size = Vector3(0.04, 4.0, 4.2)
	var sp := _part(sail, sm, _canvas, Vector3(0, -2.0, 0))
	sp.rotation.z = 0.06                    # bellied a little before the wind
	out["mast"] = mast
	out["sail"] = sail
	return out


func _process(delta: float) -> void:
	_t += delta
	for m in movers:
		m["z"] += m["speed"] * m["dir"] * delta
		if m["z"] < Z_MIN:
			m["z"] += Z_MAX - Z_MIN
		elif m["z"] > Z_MAX:
			m["z"] -= Z_MAX - Z_MIN
		var b: Node3D = m["node"]
		var ph: float = m["phase"]
		b.position = Vector3(m["x"] + 0.4 * sin(_t * 0.11 + ph), water + 0.05 * sin(_t * 1.4 + ph), m["z"])
		b.rotation.x = 0.02 * sin(_t * 1.1 + ph)
		b.rotation.z = 0.015 * sin(_t * 0.9 + ph * 2.0)
		if m["mast"] != null:       # strike the mast toward the stern while passing under the bridge
			var mast: Node3D = m["mast"]
			var down: bool = abs(float(m["z"]) - bridge_z) < 34.0
			var target := -1.45 if down else 0.0
			mast.rotation.z = move_toward(mast.rotation.z, target, delta * 0.5 if _t > 0.5 else 10.0)
			var furl: float = 1.0 - 0.85 * clampf(-mast.rotation.z / 1.45, 0.0, 1.0)
			m["sail"].scale = Vector3(1.0, furl, 1.0)
	for o in bobbers:
		var n: Node3D = o["node"]
		var ph2: float = o["phase"]
		n.position.y = o["base_y"] + 0.05 * sin(_t * 1.3 + ph2)
		n.rotation.x = 0.025 * sin(_t * 1.05 + ph2)
		n.rotation.z = 0.02 * sin(_t * 0.8 + ph2)
	_vis_t -= delta
	var cam := get_viewport().get_camera_3d()
	if _vis_t <= 0.0 and cam:
		_vis_t = 1.0
		var pp: Vector3 = cam.global_position
		for m in movers:     # far vessels: hide them and stop the boatman's animation
			var near: bool = m["node"].position.distance_to(pp) < SHOW_R + 20.0
			if near != m["near"]:
				m["near"] = near
				m["node"].visible = near
				if m["ap"]:
					if near:
						m["ap"].play()
					else:
						m["ap"].pause()
