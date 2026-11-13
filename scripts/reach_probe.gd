extends Node
## Reachability probe (run with:  godot --path . -- --reach [--reach-step 1.0]): samples the physics world on a grid,
## flood-fills from the player start over walkable floor and writes renders/world/reach.png (+ reach.json with stats).
## Reachable cells are tinted by district; walkable floor the player cannot reach is grey; no floor is black.
## Used to find gaps that let the player leave the four districts.

var world: Node
const CLEAR := 1.6        # head-room above the floor needed to stand
const STEP := 0.45        # max height difference between neighbouring cells the capsule can walk over


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_run.call_deferred()


func _run() -> void:
	for i in 10:
		await get_tree().physics_frame
	var args := OS.get_cmdline_user_args()
	var cell := 1.0
	var jump := "--reach-jump" in args
	if "--reach-step" in args:
		cell = float(args[args.find("--reach-step") + 1])
	var b: Array = world.layout["blockers"]
	# world box = the four outer blockers
	var x0 := INF
	var x1 := -INF
	var z0 := INF
	var z1 := -INF
	for k in 4:
		var c: Array = b[k]["center"]
		var s: Array = b[k]["size"]
		x0 = min(x0, c[0] - s[0] / 2.0)
		x1 = max(x1, c[0] + s[0] / 2.0)
		z0 = min(z0, c[2] - s[2] / 2.0)
		z1 = max(z1, c[2] + s[2] / 2.0)
	var nx := int((x1 - x0) / cell)
	var nz := int((z1 - z0) / cell)
	var space: PhysicsDirectSpaceState3D = world.get_world_3d().direct_space_state
	var cap := CapsuleShape3D.new()
	cap.radius = 0.3
	cap.height = CLEAR
	var sq := PhysicsShapeQueryParameters3D.new()
	sq.shape = cap
	sq.collision_mask = 1
	var ex: Array = [world.player.get_rid()]
	sq.exclude = ex
	# floors[i] = PackedFloat32Array of standable heights in that column (top-down, up to 3)
	var floors: Array = []
	floors.resize(nx * nz)
	var t0 := Time.get_ticks_msec()
	for iz in nz:
		for ix in nx:
			var x := x0 + (ix + 0.5) * cell
			var z := z0 + (iz + 0.5) * cell
			var hs := PackedFloat32Array()
			var from_y := 60.0
			for layer in 4:
				var rq := PhysicsRayQueryParameters3D.create(Vector3(x, from_y, z), Vector3(x, -8.0, z), 1, ex)
				var hit := space.intersect_ray(rq)
				if hit.is_empty():
					break
				var y: float = hit["position"].y
				if hit["normal"].y > 0.6:
					sq.transform = Transform3D(Basis(), Vector3(x, y + 0.06 + CLEAR / 2.0, z))
					if space.intersect_shape(sq, 1).is_empty():
						hs.append(y)
				from_y = y - 0.25
			floors[iz * nx + ix] = hs
		if iz % 40 == 0:
			print("REACH row %d/%d" % [iz, nz])
	print("REACH sampled in %d ms" % (Time.get_ticks_msec() - t0))
	# flood fill from the player
	var pp: Vector3 = world.player.global_position
	var reach := {}            # key = idx * 4 + layer
	var q: Array = []
	var sx := int((pp.x - x0) / cell)
	var sz := int((pp.z - z0) / cell)
	var shs: PackedFloat32Array = floors[sz * nx + sx]
	for l in shs.size():
		if abs(shs[l] - pp.y) < 1.5:
			reach[(sz * nx + sx) * 4 + l] = true
			q.append(Vector3i(sx, sz, l))
			break
	var head := 0
	while head < q.size():
		var c: Vector3i = q[head]
		head += 1
		var h: float = floors[c.y * nx + c.x][c.z]
		for d in [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]:
			var ax: int = c.x + d.x
			var az: int = c.y + d.y
			if ax < 0 or az < 0 or ax >= nx or az >= nz:
				continue
			var ni := az * nx + ax
			var nh: PackedFloat32Array = floors[ni]
			for l in nh.size():
				if reach.has(ni * 4 + l):
					continue
				var dh: float = nh[l] - h
				var walk: bool = abs(dh) <= STEP * cell
				var hop: bool = jump and dh <= 1.0 and dh > -3.0     # a jump clears ~1 m; dropping down is always possible
				if not walk and not hop:
					continue
				# hollow (trimesh) buildings are not caught by shape queries: rays from cell to cell, at two heights and
				# offset by the capsule radius sideways (a jump only needs the upper ones clear)
				var a := Vector3(x0 + (c.x + 0.5) * cell, 0.0, z0 + (c.y + 0.5) * cell)
				var bpt := a + Vector3(d.x, 0, d.y) * cell
				var side := Vector3(-d.y, 0, d.x) * 0.3
				var top: float = max(h, nh[l])
				var tests: Array = [Vector3(0, top + 0.5, 0), Vector3(0, top + 1.4, 0), side + Vector3(0, top + 0.9, 0), -side + Vector3(0, top + 0.9, 0)]
				if not walk:
					tests = [Vector3(0, h + 1.25, 0), Vector3(0, h + 1.75, 0), side + Vector3(0, h + 1.5, 0), -side + Vector3(0, h + 1.5, 0)]
				var blocked := false
				for o in tests:
					var r1 := PhysicsRayQueryParameters3D.create(a + o, bpt + o, 1, ex)
					r1.hit_back_faces = true
					if not space.intersect_ray(r1).is_empty():
						blocked = true
						break
				if blocked:
					continue
				reach[ni * 4 + l] = true
				q.append(Vector3i(ax, az, l))
	print("REACH reachable cells: %d" % q.size())
	var img := Image.create(nx, nz, false, Image.FORMAT_RGB8)
	var tint := {"old_town": Color(1.0, 0.85, 0.55), "charles_bridge": Color(0.6, 0.85, 1.0), "mala_strana": Color(0.75, 1.0, 0.65),
		"vysehrad": Color(1.0, 0.65, 0.8)}
	var outside := 0
	var by_d := {}
	for iz in nz:
		for ix in nx:
			var i := iz * nx + ix
			var hs: PackedFloat32Array = floors[i]
			var col := Color(0, 0, 0)
			if hs.size() > 0:
				col = Color(0.28, 0.28, 0.3)
			for l in hs.size():
				if reach.has(i * 4 + l):
					var p := Vector3(x0 + (ix + 0.5) * cell, hs[l], z0 + (iz + 0.5) * cell)
					var d: String = world.district_at(p)
					var inside := false
					for dd in world.districts:
						var r: Array = dd["rect"]
						if p.x >= r[0] and p.x <= r[2] and p.z >= r[1] and p.z <= r[3]:
							inside = true
					var shade := clampf(0.75 + hs[l] * 0.02, 0.5, 1.0)
					col = tint.get(d, Color.WHITE) * shade if inside else Color(1, 0, 0)
					by_d[d] = by_d.get(d, 0) + 1
					if not inside:
						outside += 1
					break
			img.set_pixel(ix, iz, col)
	var dir := ProjectSettings.globalize_path("res://renders/world/")
	var tag := "reach_open" if "--no-seal" in args else "reach"   # unsealed grid feeds tools/seal_world.py
	DirAccess.make_dir_recursive_absolute(dir)
	img.save_png(dir + tag + ".png")
	# raw grid for offline analysis: per cell the reachable height or -99
	var raw := PackedFloat32Array()
	raw.resize(nx * nz)
	for i in nx * nz:
		raw[i] = -99.0
		var hs: PackedFloat32Array = floors[i]
		for l in hs.size():
			if reach.has(i * 4 + l):
				raw[i] = hs[l]
				break
	var f := FileAccess.open(dir + tag + ".bin", FileAccess.WRITE)
	f.store_buffer(raw.to_byte_array())
	f.close()
	var info := {"x0": x0, "z0": z0, "cell": cell, "nx": nx, "nz": nz, "reachable": q.size(), "outside_rects": outside, "by_district": by_d}
	var jf := FileAccess.open(dir + tag + ".json", FileAccess.WRITE)
	jf.store_string(JSON.stringify(info, " "))
	jf.close()
	print("REACH ", JSON.stringify(info))
	get_tree().quit()
