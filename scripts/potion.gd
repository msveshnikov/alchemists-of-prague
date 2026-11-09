extends Node3D
class_name Potion
## Alchemist's thrown flask: ballistic arc, shatters into a splash. Green = poison, purple = slowing fumes.

var vel := Vector3.ZERO
var world: Node
var green := true
var life := 4.0
var splash_r := 2.4
var dmg := 12.0


static func launch(p_world: Node, from: Vector3, target: Vector3, p_green: bool) -> Potion:
	var p := Potion.new()
	p.world = p_world
	p.green = p_green
	p_world.add_child(p)
	p.global_position = from
	var flat := Vector3(target.x - from.x, 0, target.z - from.z)
	var t: float = clamp(flat.length() / 9.0, 0.55, 1.4)
	p.vel = flat / t
	p.vel.y = (target.y + 0.3 - from.y + 0.5 * 9.8 * t * t) / t
	var mi := MeshInstance3D.new()
	var sm := SphereMesh.new()
	sm.radius = 0.09
	sm.height = 0.2
	mi.mesh = sm
	var m := StandardMaterial3D.new()
	var c := Color(0.35, 1.0, 0.25) if p_green else Color(0.7, 0.25, 1.0)
	m.albedo_color = c
	m.emission_enabled = true
	m.emission = c
	m.emission_energy_multiplier = 3.0
	mi.material_override = m
	p.add_child(mi)
	var l := OmniLight3D.new()
	l.light_color = c
	l.light_energy = 1.2
	l.omni_range = 3.0
	p.add_child(l)
	Sfx.play_at("bottle", from, -4.0)
	return p


func _physics_process(delta: float) -> void:
	life -= delta
	vel.y -= 9.8 * delta
	var nxt := global_position + vel * delta
	var q := PhysicsRayQueryParameters3D.create(global_position, nxt, 1 | 2)
	var hit := get_world_3d().direct_space_state.intersect_ray(q)
	if not hit.is_empty() or life <= 0.0:
		_burst(hit.get("position", nxt))
		return
	global_position = nxt
	rotation.x += delta * 9.0


func _burst(at: Vector3) -> void:
	Sfx.play_at("glass", at, 0.0)
	Sfx.play_at("potion_splash", at, -2.0)
	var c := Color(0.35, 1.0, 0.25) if green else Color(0.7, 0.25, 1.0)
	var parts := GPUParticles3D.new()
	parts.one_shot = true
	parts.amount = 40
	parts.lifetime = 1.4
	parts.explosiveness = 0.9
	var pm := ParticleProcessMaterial.new()
	pm.direction = Vector3.UP
	pm.spread = 70.0
	pm.initial_velocity_min = 1.5
	pm.initial_velocity_max = 4.0
	pm.gravity = Vector3(0, -2.0, 0)
	pm.scale_min = 0.4
	pm.scale_max = 1.2
	pm.color = c
	parts.process_material = pm
	var dm := SphereMesh.new()
	dm.radius = 0.12
	dm.height = 0.24
	var mm := StandardMaterial3D.new()
	mm.albedo_color = Color(c, 0.6)
	mm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mm.vertex_color_use_as_albedo = true
	dm.material = mm
	parts.draw_pass_1 = dm
	world.add_child(parts)
	parts.global_position = at
	parts.emitting = true
	world.get_tree().create_timer(2.0).timeout.connect(parts.queue_free)
	var p: Node3D = world.player
	if p.global_position.distance_to(at) <= splash_r and not p.dead:
		p.take_damage(dmg, at, "splash")
		if green:
			Game.poison_time = max(Game.poison_time, 6.0)
			Game.say("Poisoned! Drink an antidote (3).", Color(0.5, 1.0, 0.4))
		else:
			Game.slow_time = max(Game.slow_time, 4.0)
			Game.say("Choking fumes slow you down!", Color(0.8, 0.5, 1.0))
	queue_free()
