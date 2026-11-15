extends Node3D
## Birds of Prague (decorative, no collision).
## Pigeons: a flock of 30 on Old Town Square walks about, bobbing their heads, pecks at the cobbles and looks around.
## Come close (or run past) and the ones near you burst up with a clatter of wings; their neighbours follow, and the
## whole group flies off together to another part of the square, a market stall roof or a cornice, and later returns.
## Gulls: sixteen circle and glide over Charles Bridge and the Vltava, flap to climb, scream, and now and then land on
## the bridge parapet, from where they take off again when you walk up. Birds sleep at night.
## Rendering: one MultiMesh per species; wings, head and legs are animated in assets/shaders/bird.gdshader.

const PIGEON_N := 30
const GULL_N := 16
const SQUARE := Rect2(-30.0, -30.0, 60.0, 58.0)           # open ground of Old Town Square (Godot x, z)
const SQUARE_C := Vector3(0.0, 0.0, -1.0)
const GULL_BOX := AABB(Vector3(-330.0, 2.5, -15.0), Vector3(145.0, 15.0, 95.0))
const PIGEON_SPEED := 6.5
const MAX_PERCHED_GULLS := 5

enum { WALK, PECK, IDLE, FLY, PERCH, SOAR }

var world: Node
var pigeons: Array = []
var gulls: Array = []
var _pmm: MultiMesh
var _gmm: MultiMesh
var _pmi: MultiMeshInstance3D
var _gmi: MultiMeshInstance3D
var _rnd := RandomNumberGenerator.new()
var _t := 0.0
var _coo_t := 3.0
var _spont_t := 20.0
var _npc_t := 0.0
var _near_npcs: Array = []
var _spawned := false
var _sleeping := false
var _parapet: Array = []      # [{pos, out}]: perches on top of the bridge parapets, clear of the statues


func setup(p_world: Node) -> void:
	world = p_world
	_rnd.seed = 1400
	var pm := _bird_mesh(false)
	var gm := _bird_mesh(true)
	var pmat := ShaderMaterial.new()
	pmat.shader = load("res://assets/shaders/bird.gdshader")
	var gmat := ShaderMaterial.new()
	gmat.shader = pmat.shader
	gmat.set_shader_parameter("gull", true)
	var g := 2.0
	gmat.set_shader_parameter("shoulder", Vector3(0.045, 0.16, -0.04) * g)
	gmat.set_shader_parameter("neck", Vector3(0.0, 0.17, -0.09) * g)
	gmat.set_shader_parameter("hip", Vector3(0.025, 0.07, 0.0) * g)
	_pmm = _multimesh(pm, PIGEON_N)
	_gmm = _multimesh(gm, GULL_N)
	_pmi = _instance(_pmm, pmat, 110.0)
	_gmi = _instance(_gmm, gmat, 260.0)
	# parapet perches between the statues
	var statues: Array = []
	var bays: Array = []
	for i in world.layout["instances"]:
		if i["asset"] == "bridge_statue":
			statues.append(float(i["pos"][0]))
		elif i["asset"] == "bridge_span":
			bays.append(Vector3(i["pos"][0], i["pos"][1], i["pos"][2]))
	for b in bays:
		for k in 5:
			var x: float = b.x - 10.0 + k * 5.0
			var clear := true
			for sx in statues:
				if absf(x - sx) < 2.6:
					clear = false
			if clear:
				for sd: float in [-1.0, 1.0]:
					_parapet.append({"pos": Vector3(x, b.y + 1.2, b.z + sd * 5.275), "out": Vector3(0, 0, sd), "taken": false})


func _multimesh(mesh: Mesh, n: int) -> MultiMesh:
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_custom_data = true
	mm.mesh = mesh
	mm.instance_count = n
	mm.visible_instance_count = 0
	return mm


func _instance(mm: MultiMesh, mat: Material, vis: float) -> MultiMeshInstance3D:
	var mi := MultiMeshInstance3D.new()
	mi.multimesh = mm
	mi.material_override = mat
	mi.custom_aabb = AABB(Vector3(-2000, -50, -2000), Vector3(4000, 200, 4000))
	mi.visibility_range_end = vis
	add_child(mi)
	return mi


# ================================================================ meshes
func _bird_mesh(gull: bool) -> ArrayMesh:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var s := 2.0 if gull else 1.0
	var body := Color(0.93, 0.93, 0.92) if gull else Color(0.4, 0.43, 0.5)
	var breast := Color(0.95, 0.95, 0.94) if gull else Color(0.47, 0.42, 0.5)
	var head := Color(0.95, 0.95, 0.95) if gull else Color(0.36, 0.38, 0.45)
	var neck := Color(0.94, 0.94, 0.94) if gull else Color(0.3, 0.4, 0.38, 0.75)
	var back := Color(0.6, 0.64, 0.7) if gull else body
	var bill := Color(0.95, 0.78, 0.18, 0.0) if gull else Color(0.16, 0.15, 0.15, 0.0)
	var legc := Color(0.85, 0.62, 0.55, 0.0) if gull else Color(0.75, 0.25, 0.25, 0.0)
	var eye := Color(0.9, 0.85, 0.5, 0.0) if gull else Color(0.85, 0.4, 0.1, 0.0)
	# body: long ellipsoid, grey mantle on top for the gull
	_ellipsoid(st, Vector3(0, 0.13, 0.01) * s, Vector3(0.06, 0.064, 0.135) * s, body, 0, back)
	_ellipsoid(st, Vector3(0, 0.14, -0.065) * s, Vector3(0.056, 0.062, 0.075) * s, breast, 0)
	_ellipsoid(st, Vector3(0, 0.178, -0.098) * s, Vector3(0.035, 0.045, 0.04) * s, neck, 0)
	_ellipsoid(st, Vector3(0, 0.205, -0.125) * s, Vector3(0.03, 0.032, 0.037) * s, head, 3)
	for sd: float in [-1.0, 1.0]:
		_ellipsoid(st, Vector3(sd * 0.024, 0.212, -0.136) * s, Vector3(0.007, 0.007, 0.007) * s, eye, 3, null, 4, 5)
	var beak_len := 0.05 if gull else 0.028
	_cone(st, Vector3(0, 0.2, -0.155) * s, Vector3(0, 0.194 if not gull else 0.19, -0.155 - beak_len) * s, 0.008 * s, bill, 3)
	# tail fan
	var tail := Color(0.94, 0.94, 0.94) if gull else Color(0.42, 0.45, 0.52)
	var tip := Color(0.94, 0.94, 0.94) if gull else Color(0.14, 0.14, 0.16)
	var rows := [[0.0, 0.022, tail], [0.75, 0.04, tail], [0.8, 0.042, tip], [1.0, 0.046, tip]]
	for i in rows.size() - 1:
		var a: Array = rows[i]
		var b: Array = rows[i + 1]
		var za := lerpf(0.1, 0.25 if not gull else 0.2, a[0])
		var zb := lerpf(0.1, 0.25 if not gull else 0.2, b[0])
		var ya := lerpf(0.13, 0.115, a[0])
		var yb := lerpf(0.13, 0.115, b[0])
		var q := [Vector3(-a[1], ya, za) * s, Vector3(a[1], ya, za) * s, Vector3(b[1], yb, zb) * s, Vector3(-b[1], yb, zb) * s]
		var cs := [a[2], a[2], b[2], b[2]]
		_quad(st, q, cs, Vector3.UP, 0, [Vector2.ZERO, Vector2.ZERO, Vector2.ZERO, Vector2.ZERO])
	# wings: a grid in the spread pose, span along X from the shoulder; the shader folds and flaps them
	var span := 0.62 if gull else 0.31
	var chord := 0.15 if gull else 0.13
	var sh := Vector3(0.045, 0.16, -0.04)
	for sd: float in [-1.0, 1.0]:
		var part := 2 if sd > 0 else 1
		var nu := 6
		var nv := 4
		var grid := []
		for iu in nu + 1:
			var u := float(iu) / nu
			var c := chord * (1.0 - (0.55 if gull else 0.3) * u) * sqrt(maxf(1.0 - pow(u, 8.0), 0.12))
			var zle := sh.z - 0.012 + u * (0.05 if gull else 0.03)
			var row := []
			for iv in nv + 1:
				var v := float(iv) / nv
				row.append(Vector3(sd * (sh.x + u * span / s), sh.y + 0.006 * sin(PI * v), zle + v * c / s) * s)
			grid.append(row)
		for iu in nu:
			for iv in nv:
				var q := [grid[iu][iv], grid[iu + 1][iv], grid[iu + 1][iv + 1], grid[iu][iv + 1]]
				var uvs := [Vector2(float(iu) / nu, float(iv) / nv), Vector2(float(iu + 1) / nu, float(iv) / nv),
					Vector2(float(iu + 1) / nu, float(iv + 1) / nv), Vector2(float(iu) / nu, float(iv + 1) / nv)]
				var w := Color(1, 1, 1, 1)
				_quad(st, q if sd > 0 else [q[1], q[0], q[3], q[2]], [w, w, w, w], Vector3.UP, part,
					uvs if sd > 0 else [uvs[1], uvs[0], uvs[3], uvs[2]])
	# legs and toes
	for sd: float in [-1.0, 1.0]:
		var part := 5 if sd > 0 else 4
		var hx := 0.025 * sd
		_box(st, Vector3(hx, 0.035, 0.0) * s, Vector3(0.009, 0.07, 0.009) * s, legc, part)
		_box(st, Vector3(hx, 0.004, -0.012) * s, Vector3(0.014 if not gull else 0.03, 0.008, 0.04) * s, legc, part)
	st.generate_tangents()
	return st.commit()


func _vtx(st: SurfaceTool, p: Vector3, n: Vector3, c: Color, part: int, uv := Vector2.ZERO) -> void:
	st.set_color(c)
	st.set_normal(n)
	st.set_uv(uv)
	st.set_uv2(Vector2(part, uv.x))
	st.add_vertex(p)


func _ellipsoid(st: SurfaceTool, c: Vector3, r: Vector3, col: Color, part: int, top = null, rings := 7, segs := 10) -> void:
	var pts := []
	for i in rings + 1:
		var th := PI * float(i) / rings
		var row := []
		for j in segs + 1:
			var ph := TAU * float(j) / segs
			var d := Vector3(sin(th) * cos(ph), cos(th), sin(th) * sin(ph))
			row.append(d)
		pts.append(row)
	for i in rings:
		for j in segs:
			var ds := [pts[i][j], pts[i + 1][j], pts[i + 1][j + 1], pts[i][j], pts[i + 1][j + 1], pts[i][j + 1]]
			for d in ds:
				var p: Vector3 = c + Vector3(d.x * r.x, d.y * r.y, d.z * r.z)
				var n := Vector3(d.x / r.x, d.y / r.y, d.z / r.z).normalized()
				var cc := col
				if top != null and d.y > 0.35 and d.z > -0.6:
					cc = top
				_vtx(st, p, n, cc, part)


func _cone(st: SurfaceTool, a: Vector3, b: Vector3, r: float, col: Color, part: int) -> void:
	var ax := (b - a).normalized()
	var u := ax.cross(Vector3.UP).normalized()
	var v := u.cross(ax).normalized()
	var segs := 6
	for j in segs:
		var p0 := a + (u * cos(TAU * j / segs) + v * sin(TAU * j / segs)) * r
		var p1 := a + (u * cos(TAU * (j + 1) / segs) + v * sin(TAU * (j + 1) / segs)) * r
		var n := ((p0 + p1) * 0.5 - a).normalized()
		_vtx(st, p0, n, col, part)
		_vtx(st, b, n, col, part)
		_vtx(st, p1, n, col, part)


func _box(st: SurfaceTool, c: Vector3, sz: Vector3, col: Color, part: int) -> void:
	var h := sz * 0.5
	var faces := [[Vector3.RIGHT, Vector3.UP, Vector3.BACK], [Vector3.LEFT, Vector3.UP, Vector3.FORWARD],
		[Vector3.UP, Vector3.BACK, Vector3.RIGHT], [Vector3.DOWN, Vector3.FORWARD, Vector3.RIGHT],
		[Vector3.BACK, Vector3.UP, Vector3.LEFT], [Vector3.FORWARD, Vector3.UP, Vector3.RIGHT]]
	for f in faces:
		var n: Vector3 = f[0]
		var a: Vector3 = f[1]
		var b: Vector3 = f[2]
		var o := c + n * h
		var ea := a * h
		var eb := b * h
		var q := [o - ea - eb, o - ea + eb, o + ea + eb, o + ea - eb]
		_quad(st, q, [col, col, col, col], n, part, [Vector2.ZERO, Vector2.ZERO, Vector2.ZERO, Vector2.ZERO])


func _quad(st: SurfaceTool, q: Array, cs: Array, n: Vector3, part: int, uvs: Array) -> void:
	for k in [0, 1, 2, 0, 2, 3]:
		_vtx(st, q[k], n, cs[k], part, uvs[k])


# ================================================================ spawning
func _spawn() -> void:
	_spawned = true
	var groups := 4
	var per := PIGEON_N / groups
	for gi in groups:
		var c := _ground_spot_in_square(Vector3.INF, 0.0)
		for k in (per if gi < groups - 1 else PIGEON_N - per * (groups - 1)):
			var p := _scatter(c, 2.5, false)
			pigeons.append(_pigeon(p))
	for i in GULL_N:
		var g := {"pos": _gull_target(), "vel": Vector3.ZERO, "state": SOAR, "target": Vector3.ZERO, "flap": 0.0,
			"phase": _rnd.randf() * TAU, "burst": 0.0, "burst_t": _rnd.randf_range(1.0, 6.0), "cry_t": _rnd.randf_range(1.0, 8.0),
			"yaw": 0.0, "pitch": 0.0, "roll": 0.0, "head": 0.0, "fold": 0.0, "perch": null, "perch_t": 0.0,
			"path": [], "ft": 0.0, "fdur": 1.0, "cry_head": 0.0, "walk": 8.0}
		var a := _rnd.randf() * TAU
		g["vel"] = Vector3(cos(a), 0, sin(a)) * 8.0
		g["target"] = _gull_target()
		if i < 3:
			_gull_perch_now(g)
		gulls.append(g)
	_pmm.visible_instance_count = pigeons.size()
	_gmm.visible_instance_count = gulls.size()


func _pigeon(p: Vector3) -> Dictionary:
	return {"pos": p, "yaw": _rnd.randf() * TAU, "state": PECK, "t": _rnd.randf_range(0.3, 3.0), "target": p,
		"walk": 0.0, "head": 0.0, "flap": 0.0, "fold": 1.0, "variant": _variant(), "delay": -1.0, "dest": p,
		"path": [], "ft": 0.0, "fdur": 1.0, "tk": _rnd.randf() * 5.0, "pitch": 0.0, "roll": 0.0, "speed": 0.45,
		"phase": 0.0, "perch_t": 0.0}


func _variant() -> int:
	var r := _rnd.randf()
	return 0 if r < 0.55 else (1 if r < 0.75 else (2 if r < 0.87 else 3))


func _ray(from: Vector3, to: Vector3) -> Dictionary:
	var q := PhysicsRayQueryParameters3D.create(from, to, 1)
	return get_world_3d().direct_space_state.intersect_ray(q)


func _ground_ok(p: Vector3) -> float:
	## Height of open cobbles at (p.x, p.z), or INF if something stands there.
	var h := _ray(Vector3(p.x, 6.0, p.z), Vector3(p.x, -1.0, p.z))
	if h.is_empty() or h["position"].y > 0.4 or h["normal"].y < 0.9:
		return INF
	return h["position"].y


func _ground_spot_in_square(avoid: Vector3, min_d: float, near := Vector3.INF, rmin := 0.0, rmax := 999.0) -> Vector3:
	for i in 40:
		var p := Vector3(_rnd.randf_range(SQUARE.position.x, SQUARE.end.x), 0.0, _rnd.randf_range(SQUARE.position.y, SQUARE.end.y))
		if avoid != Vector3.INF and _flat(p).distance_to(_flat(avoid)) < min_d:
			continue
		if near != Vector3.INF:
			var d := _flat(p).distance_to(_flat(near))
			if d < rmin or d > rmax:
				continue
		var y := _ground_ok(p)
		if y < INF:
			return Vector3(p.x, y, p.z)
	return SQUARE_C


func _perch_spot(avoid: Vector3, near: Vector3) -> Vector3:
	## A flat-ish spot up on a stall roof, a cornice or the column, away from the player and not too far to fly.
	for i in 40:
		var p := Vector3(_rnd.randf_range(-40.0, 40.0), 0.0, _rnd.randf_range(-40.0, 37.0))
		if avoid != Vector3.INF and _flat(p).distance_to(_flat(avoid)) < 10.0:
			continue
		if _flat(p).distance_to(_flat(near)) > 32.0:
			continue
		var h := _ray(Vector3(p.x, 40.0, p.z), Vector3(p.x, 0.5, p.z))
		if h.is_empty() or h["normal"].y < 0.7:
			continue
		var y: float = h["position"].y
		if y > 1.6 and y < 22.0:
			return h["position"]
	return Vector3.INF


func _scatter(c: Vector3, r: float, perch: bool) -> Vector3:
	for i in 12:
		var a := _rnd.randf() * TAU
		var d := sqrt(_rnd.randf()) * r
		var p := c + Vector3(cos(a) * d, 0, sin(a) * d)
		if perch:
			var h := _ray(Vector3(p.x, c.y + 1.5, p.z), Vector3(p.x, c.y - 1.0, p.z))
			if not h.is_empty() and h["normal"].y > 0.7:
				return h["position"]
		else:
			var y := _ground_ok(p)
			if y < INF:
				return Vector3(p.x, y, p.z)
	return c


static func _flat(v: Vector3) -> Vector3:
	return Vector3(v.x, 0.0, v.z)


# ================================================================ update
func _process(delta: float) -> void:
	if world == null or world.player == null:
		return
	delta = minf(delta, 0.1)
	_t += delta
	var night: bool = world.day_night != null and world.day_night.is_night
	if night != _sleeping:
		_sleeping = night
		visible = not night
		if not night and _spawned:
			_morning()
	if night:
		return
	var pp: Vector3 = world.player.global_position
	if not _spawned:
		if _t < 1.0:
			return
		_spawn()
	if _flat(pp).distance_to(SQUARE_C) < 170.0:
		_pmi.visible = true
		_update_pigeons(delta, pp)
	else:
		_pmi.visible = false
	if pp.x < -120.0 and pp.x > -420.0 and absf(pp.z - 32.0) < 260.0:
		_gmi.visible = true
		_update_gulls(delta, pp)
	else:
		_gmi.visible = false


func _morning() -> void:
	for b in pigeons:
		b["pos"] = _scatter(_ground_spot_in_square(Vector3.INF, 0.0), 2.5, false)
		b["state"] = PECK
		b["fold"] = 1.0
		b["delay"] = -1.0


# ---------------------------------------------------------------- pigeons
func _update_pigeons(dt: float, pp: Vector3) -> void:
	var pv: Vector3 = world.player.velocity
	var fast := Vector2(pv.x, pv.z).length() > 3.5
	var scare_r := 5.5 if fast else 3.2
	if world.player.attacking > 0.0:
		scare_r = 7.0
	_npc_t -= dt
	if _npc_t <= 0.0:
		_npc_t = 0.5
		_near_npcs.clear()
		for n in world.npcs:
			if is_instance_valid(n) and _flat(n.global_position).distance_to(SQUARE_C) < 45.0:
				_near_npcs.append(n)
	# spontaneous relocations keep the flock moving even when nobody comes near
	_spont_t -= dt
	if _spont_t <= 0.0:
		_spont_t = _rnd.randf_range(14.0, 32.0)
		var b: Dictionary = pigeons[_rnd.randi() % pigeons.size()]
		if b["state"] != FLY and b["delay"] < 0.0 and _flat(b["pos"]).distance_to(_flat(pp)) > 8.0:
			if b["state"] == PERCH:
				_take_off_group(b, pp, 3.0, false)
			else:
				_take_off_group(b, pp, 3.5, _rnd.randf() < 0.35)
	# a coo now and then from a pigeon near the player
	_coo_t -= dt
	if _coo_t <= 0.0:
		_coo_t = _rnd.randf_range(2.0, 5.5)
		var b: Dictionary = pigeons[_rnd.randi() % pigeons.size()]
		if b["state"] != FLY and b["pos"].distance_to(pp) < 22.0:
			_sound("coo", b["pos"] + Vector3(0, 0.2, 0), -9.0, 3.0, 28.0, _rnd.randf_range(0.9, 1.1))
	for i in pigeons.size():
		var b: Dictionary = pigeons[i]
		var st: int = b["state"]
		if b["delay"] >= 0.0:
			b["delay"] -= dt
			if b["delay"] < 0.0:
				_fly(b, b["dest"])
				st = FLY
		elif st != FLY:
			var d := _flat(b["pos"]).distance_to(_flat(pp))
			if d < scare_r and absf(pp.y - b["pos"].y) < 2.5:
				_take_off_group(b, pp, 4.5, _rnd.randf() < 0.25)
				st = b["state"]
		match st:
			FLY:
				_pigeon_fly(b, dt)
			PERCH:
				_pigeon_perch(b, dt, pp)
			_:
				_pigeon_ground(b, dt)
		_pmm.set_instance_transform(i, _xform(b))
		_pmm.set_instance_custom_data(i, Color(b["flap"], b["fold"], b["head"], b["walk"] + 10.0 * b["variant"]))


func _take_off_group(lead: Dictionary, pp: Vector3, radius: float, to_perch: bool) -> void:
	## The lead bird and its grounded neighbours take off together and land as a group somewhere else.
	var group: Array = []
	for b in pigeons:
		if b["state"] == FLY or b["delay"] >= 0.0:
			continue
		if b["pos"].distance_to(lead["pos"]) < radius:
			group.append(b)
	if group.is_empty():
		return
	var dest := Vector3.INF
	var perch := false
	if to_perch:
		dest = _perch_spot(pp, lead["pos"])
		perch = dest != Vector3.INF
	if dest == Vector3.INF:
		dest = _ground_spot_in_square(pp, 12.0, lead["pos"], 10.0, 38.0)
	for b in group:
		b["dest"] = _scatter(dest, 1.2 if perch else 2.6, perch)
		b["delay"] = 0.0 if b == lead else _rnd.randf_range(0.04, 0.45)
	_sound("wings", lead["pos"] + Vector3(0, 0.3, 0), -4.0 + minf(group.size(), 8) * 0.8, 4.0, 40.0, _rnd.randf_range(0.9, 1.1))


func _fly(b: Dictionary, dest: Vector3) -> void:
	var a: Vector3 = b["pos"]
	var hd := _flat(dest - a)
	var l := hd.length()
	var dir := hd / maxf(l, 0.01)
	var up := 2.5 + l * 0.12
	var p1 := a + Vector3(0, up, 0) + dir * l * 0.18
	var p2 := dest + Vector3(0, 1.6 + l * 0.08, 0) - dir * l * 0.22
	b["path"] = [a, p1, p2, dest]
	var plen := a.distance_to(p1) + p1.distance_to(p2) + p2.distance_to(dest)
	b["fdur"] = maxf(plen / PIGEON_SPEED, 1.4)
	b["ft"] = 0.0
	b["state"] = FLY
	b["fold"] = 0.0
	b["phase"] = _rnd.randf() * TAU


static func _bez(p: Array, t: float) -> Vector3:
	var u := 1.0 - t
	return p[0] * u * u * u + p[1] * 3.0 * u * u * t + p[2] * 3.0 * u * t * t + p[3] * t * t * t


func _pigeon_fly(b: Dictionary, dt: float) -> void:
	b["ft"] += dt
	var t := clampf(b["ft"] / b["fdur"], 0.0, 1.0)
	var s := t * t * (3.0 - 2.0 * t) * 0.6 + t * 0.4
	var prev: Vector3 = b["pos"]
	b["pos"] = _bez(b["path"], s)
	var v: Vector3 = b["pos"] - prev
	if v.length() > 0.0005:
		var vn := v.normalized()
		var ny := atan2(-vn.x, -vn.z)
		var dy := wrapf(ny - b["yaw"], -PI, PI)
		b["yaw"] = b["yaw"] + dy * minf(1.0, dt * 10.0)
		b["pitch"] = lerpf(b["pitch"], clampf(asin(clampf(vn.y, -1, 1)), -0.5, 0.8), minf(1.0, dt * 8.0))
		b["roll"] = lerpf(b["roll"], clampf(dy / maxf(dt, 0.001) * 0.15, -0.6, 0.6), minf(1.0, dt * 5.0))
	if t < 0.3:
		b["phase"] += dt * 32.0
		b["flap"] = sin(b["phase"]) * 1.15 + 0.25
	elif t > 0.82:
		b["phase"] += dt * 26.0
		b["flap"] = sin(b["phase"]) * 0.9 + 0.45
		b["pitch"] = lerpf(b["pitch"], 0.5, minf(1.0, dt * 6.0))
	else:
		var glide := fmod(b["ft"] * 1.7 + b["tk"], 3.0) > 2.0
		if glide:
			b["flap"] = lerpf(b["flap"], 0.32, minf(1.0, dt * 10.0))
		else:
			b["phase"] += dt * 24.0
			b["flap"] = sin(b["phase"]) * 0.85 + 0.15
	b["walk"] = 8.0 if t < 0.85 else 0.0
	b["head"] = 0.15
	if t >= 1.0:
		b["state"] = PERCH if b["pos"].y > 0.8 else PECK
		b["t"] = _rnd.randf_range(1.0, 3.0)
		b["perch_t"] = _rnd.randf_range(15.0, 45.0)
		b["pitch"] = 0.0
		b["roll"] = 0.0


func _settle_wings(b: Dictionary, dt: float) -> void:
	b["fold"] = move_toward(b["fold"], 1.0, dt * 3.5)
	b["flap"] = move_toward(b["flap"], 0.0, dt * 6.0)
	b["pitch"] = lerpf(b["pitch"], 0.0, minf(1.0, dt * 8.0))
	b["roll"] = lerpf(b["roll"], 0.0, minf(1.0, dt * 8.0))


func _pigeon_ground(b: Dictionary, dt: float) -> void:
	_settle_wings(b, dt)
	b["t"] -= dt
	b["tk"] += dt
	# step aside from townsfolk walking through the flock
	for n in _near_npcs:
		if not is_instance_valid(n):
			continue
		var away := _flat(b["pos"] - n.global_position)
		if away.length() < 1.1 and b["speed"] < 1.0:
			var tgt: Vector3 = b["pos"] + away.normalized() * 1.4
			if _ground_ok(tgt) < INF:
				b["target"] = Vector3(tgt.x, b["pos"].y, tgt.z)
				b["state"] = WALK
				b["speed"] = 1.3
				b["t"] = 3.0
			break
	match b["state"]:
		WALK:
			var to: Vector3 = _flat(b["target"] - b["pos"])
			var l := to.length()
			if l < 0.04 or b["t"] <= 0.0:
				_next_ground_state(b)
			else:
				var step := minf(l, b["speed"] * dt)
				b["pos"] += to / l * step
				var ny := atan2(-to.x, -to.z)
				b["yaw"] = lerp_angle(b["yaw"], ny, minf(1.0, dt * 9.0))
				b["walk"] = fmod(b["walk"] + dt * (14.0 if b["speed"] < 1.0 else 24.0), TAU)
				b["head"] = 0.05
		PECK:
			b["walk"] = 0.0
			var cyc := fmod(b["tk"], 1.7)
			b["head"] = -1.0 * pow(maxf(sin(cyc * 11.0), 0.0), 1.5) if cyc < 1.0 else 0.08
			if b["t"] <= 0.0:
				_next_ground_state(b)
		IDLE:
			b["walk"] = 0.0
			b["head"] = 0.2
			if fmod(b["tk"], 1.3) < dt:
				b["yaw"] += _rnd.randf_range(-0.8, 0.8)
			if b["t"] <= 0.0:
				_next_ground_state(b)


func _next_ground_state(b: Dictionary) -> void:
	var r := _rnd.randf()
	b["speed"] = 0.45
	if r < 0.45:
		b["state"] = PECK
		b["t"] = _rnd.randf_range(1.2, 4.0)
	elif r < 0.85:
		var a := _rnd.randf() * TAU
		var tgt: Vector3 = b["pos"] + Vector3(cos(a), 0, sin(a)) * _rnd.randf_range(0.4, 2.2)
		# keep to the square
		tgt.x = clampf(tgt.x, SQUARE.position.x, SQUARE.end.x)
		tgt.z = clampf(tgt.z, SQUARE.position.y, SQUARE.end.y)
		if _ground_ok(tgt) < INF:
			b["target"] = Vector3(tgt.x, b["pos"].y, tgt.z)
			b["state"] = WALK
			b["t"] = 8.0
		else:
			b["state"] = IDLE
			b["t"] = 1.0
	else:
		b["state"] = IDLE
		b["t"] = _rnd.randf_range(0.8, 2.5)


func _pigeon_perch(b: Dictionary, dt: float, pp: Vector3) -> void:
	_settle_wings(b, dt)
	b["walk"] = 0.0
	b["tk"] += dt
	b["head"] = 0.15 if fmod(b["tk"], 4.0) < 3.0 else -0.4
	if fmod(b["tk"], 2.1) < dt:
		b["yaw"] += _rnd.randf_range(-0.7, 0.7)
	b["perch_t"] -= dt
	if b["perch_t"] <= 0.0:
		b["perch_t"] = _rnd.randf_range(5.0, 15.0)
		var dest := _ground_spot_in_square(pp, 9.0, b["pos"], 3.0, 30.0)
		var group: Array = []
		for o in pigeons:
			if o["state"] == PERCH and o["delay"] < 0.0 and o["pos"].distance_to(b["pos"]) < 3.0:
				group.append(o)
		for o in group:
			o["dest"] = _scatter(dest, 2.4, false)
			o["delay"] = 0.0 if o == b else _rnd.randf_range(0.1, 1.2)


func _xform(b: Dictionary) -> Transform3D:
	var bs := Basis(Vector3.UP, b["yaw"]) * Basis(Vector3.RIGHT, b["pitch"]) * Basis(Vector3.BACK, b["roll"])
	return Transform3D(bs, b["pos"])


# ---------------------------------------------------------------- gulls
func _gull_target() -> Vector3:
	# often circle close to the player when they are on the bridge or the embankments
	if world.player and _rnd.randf() < 0.45:
		var pp: Vector3 = world.player.global_position
		if GULL_BOX.grow(30.0).has_point(Vector3(pp.x, 5.0, pp.z)):
			return Vector3(pp.x + _rnd.randf_range(-22.0, 22.0), pp.y + _rnd.randf_range(4.0, 12.0), pp.z + _rnd.randf_range(-22.0, 22.0))
	var a := GULL_BOX
	return Vector3(_rnd.randf_range(a.position.x, a.end.x), _rnd.randf_range(a.position.y, a.end.y), _rnd.randf_range(a.position.z, a.end.z))


func _free_perch() -> Dictionary:
	var n := 0
	for g in gulls:
		if g["perch"] != null:
			n += 1
	if n >= MAX_PERCHED_GULLS or _parapet.is_empty():
		return {}
	for i in 8:
		var p: Dictionary = _parapet[_rnd.randi() % _parapet.size()]
		if not p["taken"] and p["pos"].distance_to(world.player.global_position) > 10.0:
			return p
	return {}


func _gull_perch_now(g: Dictionary) -> void:
	var p := _free_perch()
	if p.is_empty():
		return
	p["taken"] = true
	g["perch"] = p
	g["pos"] = p["pos"]
	g["state"] = PERCH
	g["fold"] = 1.0
	g["walk"] = 0.0
	g["perch_t"] = _rnd.randf_range(20.0, 60.0)
	g["yaw"] = atan2(-p["out"].x, -p["out"].z) + _rnd.randf_range(-1.2, 1.2)


func _update_gulls(dt: float, pp: Vector3) -> void:
	for i in gulls.size():
		var g: Dictionary = gulls[i]
		match g["state"]:
			SOAR:
				_gull_soar(g, dt)
			FLY:
				_gull_path(g, dt)
			PERCH:
				_gull_perch(g, dt, pp)
		# cries
		g["cry_t"] -= dt
		g["cry_head"] = maxf(g["cry_head"] - dt, 0.0)
		if g["cry_t"] <= 0.0:
			g["cry_t"] = _rnd.randf_range(5.0, 14.0) if g["state"] != PERCH else _rnd.randf_range(7.0, 20.0)
			if g["pos"].distance_to(pp) < 110.0:
				_sound("gull", g["pos"], -1.0, 14.0, 130.0, _rnd.randf_range(0.88, 1.12))
				g["cry_head"] = 1.1
		var head: float = g["head"]
		if g["cry_head"] > 0.0:
			head = 0.55 if g["state"] == PERCH else 0.25
		_gmm.set_instance_transform(i, _xform(g))
		_gmm.set_instance_custom_data(i, Color(g["flap"], g["fold"], head, g["walk"]))


func _gull_soar(g: Dictionary, dt: float) -> void:
	var to: Vector3 = g["target"] - g["pos"]
	if to.length() < 12.0:
		if _rnd.randf() < 0.16:
			var p := _free_perch()
			if not p.is_empty():
				_gull_land(g, p)
				return
		g["target"] = _gull_target()
		to = g["target"] - g["pos"]
	var vel: Vector3 = g["vel"]
	var fwd := vel.normalized()
	var want := to.normalized()
	var ang := fwd.angle_to(want)
	if ang > 0.001:
		fwd = fwd.slerp(want, minf(1.0, 0.75 * dt / ang)).normalized()
	fwd.y = clampf(fwd.y, -0.3, 0.3)
	fwd = fwd.normalized()
	var speed := 8.5 - fwd.y * 6.0
	g["vel"] = fwd * speed
	g["pos"] += g["vel"] * dt
	var ny := atan2(-fwd.x, -fwd.z)
	var dy := wrapf(ny - g["yaw"], -PI, PI)
	g["yaw"] = ny
	g["pitch"] = lerpf(g["pitch"], asin(fwd.y) * 0.8, minf(1.0, dt * 3.0))
	g["roll"] = lerpf(g["roll"], clampf(dy / maxf(dt, 0.001) * 0.9, -0.75, 0.75), minf(1.0, dt * 2.5))
	g["fold"] = 0.0
	g["walk"] = 8.0
	g["head"] = 0.0
	# wingbeats: to climb, and in short bursts; otherwise a stiff glide with the wings a little raised
	g["burst_t"] -= dt
	if g["burst_t"] <= 0.0:
		g["burst"] = _rnd.randf_range(0.8, 2.0)
		g["burst_t"] = _rnd.randf_range(3.0, 9.0)
	g["burst"] = maxf(g["burst"] - dt, 0.0)
	if fwd.y > 0.06 or g["burst"] > 0.0:
		g["phase"] += dt * 15.0
		g["flap"] = sin(g["phase"]) * 0.7 + 0.1
	else:
		g["flap"] = lerpf(g["flap"], 0.1 + sin(_t * 1.3 + g["burst_t"]) * 0.04, minf(1.0, dt * 4.0))


func _gull_land(g: Dictionary, p: Dictionary) -> void:
	p["taken"] = true
	g["perch"] = p
	var a: Vector3 = g["pos"]
	var dest: Vector3 = p["pos"]
	var fwd: Vector3 = g["vel"].normalized()
	var out: Vector3 = p["out"]
	g["path"] = [a, a + fwd * 12.0, dest + out * 4.0 + Vector3(0, 3.0, 0), dest]
	var plen := a.distance_to(dest) * 1.3 + 8.0
	g["fdur"] = maxf(plen / 9.0, 2.5)
	g["ft"] = 0.0
	g["state"] = FLY


func _gull_take_off(g: Dictionary) -> void:
	var p: Dictionary = g["perch"]
	p["taken"] = false
	g["perch"] = null
	var a: Vector3 = g["pos"]
	var out: Vector3 = p["out"]
	var side := Vector3(1, 0, 0) * (1.0 if _rnd.randf() < 0.5 else -1.0)
	var dest := a + out * 14.0 + side * 8.0 + Vector3(0, 7.0, 0)
	g["path"] = [a, a + out * 2.0 + Vector3(0, 2.0, 0), dest - out * 4.0 - side * 3.0, dest]
	g["fdur"] = 2.6
	g["ft"] = 0.0
	g["state"] = FLY
	g["fold"] = 0.0
	g["target"] = _gull_target()
	_sound("gull", a, 0.0, 14.0, 130.0, _rnd.randf_range(0.95, 1.1))
	g["cry_head"] = 0.8


func _gull_path(g: Dictionary, dt: float) -> void:
	g["ft"] += dt
	var t := clampf(g["ft"] / g["fdur"], 0.0, 1.0)
	var landing: bool = g["perch"] != null
	var s: float = t * t * (3.0 - 2.0 * t) * 0.5 + t * 0.5 if landing else t
	var prev: Vector3 = g["pos"]
	g["pos"] = _bez(g["path"], s)
	var v: Vector3 = g["pos"] - prev
	if v.length() > 0.0005:
		var vn := v.normalized()
		var ny := atan2(-vn.x, -vn.z)
		var dy := wrapf(ny - g["yaw"], -PI, PI)
		g["yaw"] = g["yaw"] + dy * minf(1.0, dt * 8.0)
		g["pitch"] = lerpf(g["pitch"], clampf(asin(clampf(vn.y, -1, 1)), -0.5, 0.7), minf(1.0, dt * 6.0))
		g["roll"] = lerpf(g["roll"], clampf(dy / maxf(dt, 0.001) * 0.5, -0.6, 0.6), minf(1.0, dt * 4.0))
		g["vel"] = vn * maxf(v.length() / maxf(dt, 0.001), 6.0)
	g["fold"] = 0.0
	if landing:
		if t > 0.7:
			g["phase"] += dt * 14.0
			g["flap"] = sin(g["phase"]) * 0.8 + 0.5
			g["pitch"] = lerpf(g["pitch"], 0.45, minf(1.0, dt * 5.0))
			g["walk"] = 0.0 if t > 0.85 else 8.0
		else:
			g["flap"] = lerpf(g["flap"], 0.15, minf(1.0, dt * 4.0))
			g["walk"] = 8.0
	else:
		g["phase"] += dt * 16.0
		g["flap"] = sin(g["phase"]) * 0.85 + 0.25
		g["walk"] = 8.0
	if t >= 1.0:
		if landing:
			g["state"] = PERCH
			g["perch_t"] = _rnd.randf_range(20.0, 70.0)
			g["walk"] = 0.0
			g["pitch"] = 0.0
			g["roll"] = 0.0
		else:
			g["state"] = SOAR
			g["target"] = _gull_target()


func _gull_perch(g: Dictionary, dt: float, pp: Vector3) -> void:
	_settle_wings(g, dt * 0.8)
	g["walk"] = 0.0
	g["perch_t"] -= dt
	g["head"] = 0.0 if fmod(_t + g["burst_t"], 5.0) < 4.0 else -0.35
	if fmod(_t + g["phase"], 3.3) < dt:
		g["yaw"] += _rnd.randf_range(-0.6, 0.6)
	var d := _flat(g["pos"]).distance_to(_flat(pp))
	if g["perch_t"] <= 0.0 or (d < 4.5 and absf(pp.y - g["pos"].y) < 3.0):
		_gull_take_off(g)


# ---------------------------------------------------------------- sound
func _sound(name: String, pos: Vector3, vol: float, unit: float, maxd: float, pitch: float) -> void:
	var s: AudioStream = Sfx.stream(name)
	if s == null:
		return
	var p := AudioStreamPlayer3D.new()
	p.stream = s
	p.bus = "SFX"
	p.volume_db = vol
	p.unit_size = unit
	p.max_distance = maxd
	p.pitch_scale = pitch
	add_child(p)
	p.global_position = pos
	p.play()
	p.finished.connect(p.queue_free)
