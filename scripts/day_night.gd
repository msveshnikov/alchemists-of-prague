extends Node
class_name DayNight
## Drives sun/moon, sky, fog, lamps and glowing windows from the lighting keys exported by Task 3
## (assets/levels/old_town_layout.json -> lighting.keys, 400-frame cycle).

signal phase_changed(is_night: bool)

const CYCLE := 400.0
const NIGHT_FROM := 170.0
const NIGHT_TO := 330.0

var keys: Array = []
var sun: DirectionalLight3D
var env: Environment
var sky_mat: ProceduralSkyMaterial
var moon: MeshInstance3D
var lamps: Array = []          # [{light, base, always}]
var glow_mats: Array = []      # [{mat, base}]
var is_night := false
var frame := 0.0
var _first := true


func setup(p_keys: Array, p_sun: DirectionalLight3D, p_env: Environment, p_moon: MeshInstance3D) -> void:
	keys = p_keys
	sun = p_sun
	env = p_env
	sky_mat = env.sky.sky_material
	moon = p_moon


func register_light(l: OmniLight3D) -> void:
	var n := String(l.name).to_lower()
	var always := n.contains("fire") or n.contains("forge")
	lamps.append({"light": l, "base": l.light_energy, "always": always})
	l.shadow_enabled = false
	l.light_specular = 0.3


func register_glow(m: BaseMaterial3D) -> void:
	glow_mats.append({"mat": m, "base": m.emission_energy_multiplier})


## Hour of the day for the HUD clock: frame 0 = 12:00 noon, 150 = dusk (~19:30), 250 = midnight.
func clock() -> String:
	var hours := fmod(12.0 + frame / CYCLE * 24.0, 24.0)
	return "%02d:%02d" % [int(hours), int(fmod(hours, 1.0) * 60.0)]


func _process(delta: float) -> void:
	if keys.is_empty():
		return
	var day_len: float = float(Game.settings["day_minutes"]) * 60.0
	Game.time_of_day = fmod(Game.time_of_day + delta / max(day_len, 30.0), 1.0)
	apply(Game.time_of_day)


func apply(t: float) -> void:
	frame = t * CYCLE
	var a: Dictionary = keys[0]
	var b: Dictionary = keys[0]
	var u := 0.0
	for i in range(keys.size() - 1):
		if frame >= keys[i]["frame"] and frame <= keys[i + 1]["frame"]:
			a = keys[i]
			b = keys[i + 1]
			u = (frame - a["frame"]) / max(1.0, b["frame"] - a["frame"])
			break
	u = u * u * (3.0 - 2.0 * u)
	var el: float = deg_to_rad(lerp(float(a["sun_elevation_deg"]), float(b["sun_elevation_deg"]), u))
	var az: float = deg_to_rad(lerp_angle_deg(a["sun_azimuth_deg_from_north"], b["sun_azimuth_deg_from_north"], u))
	var to_sun := Vector3(cos(el) * sin(az), sin(el), -cos(el) * cos(az)).normalized()
	sun.global_basis = Basis.looking_at(-to_sun, Vector3.UP if abs(to_sun.y) < 0.98 else Vector3.FORWARD)
	sun.light_energy = lerp(float(a["sun_energy"]), float(b["sun_energy"]), u) * 0.42
	sun.light_color = _col(a["sun_color"]).lerp(_col(b["sun_color"]), u)
	var zen := _col(a["sky_zenith"]).lerp(_col(b["sky_zenith"]), u)
	var hor := _col(a["sky_horizon"]).lerp(_col(b["sky_horizon"]), u)
	var ss: float = lerp(float(a["sky_strength"]), float(b["sky_strength"]), u)
	sky_mat.sky_top_color = zen
	sky_mat.sky_horizon_color = hor
	sky_mat.ground_horizon_color = hor * 0.7
	sky_mat.ground_bottom_color = hor * 0.25
	sky_mat.sky_energy_multiplier = ss
	env.fog_light_color = hor.lerp(zen, 0.3)
	env.ambient_light_energy = clamp(ss * (0.45 + 0.6 * sun.light_energy), 0.3, 1.1)
	env.fog_density = lerp(0.0016, 0.004, night_amount())
	var lamp_f: float = lerp(float(a["lamp_factor"]), float(b["lamp_factor"]), u)
	var win_f: float = lerp(float(a["window_emission_factor"]), float(b["window_emission_factor"]), u)
	var moon_f: float = lerp(float(a["moon_factor"]), float(b["moon_factor"]), u)
	for l in lamps:
		var light: OmniLight3D = l["light"]
		if not is_instance_valid(light):
			continue
		var f: float = 1.0 if l["always"] else lamp_f * 0.75
		light.visible = f > 0.02
		light.light_energy = l["base"] * f * (0.9 + 0.1 * sin(Time.get_ticks_msec() * 0.013 + light.get_instance_id() % 17) if l["always"] else 1.0)
	for g in glow_mats:
		g["mat"].emission_energy_multiplier = g["base"] * win_f * 1.4
	if moon:
		moon.visible = moon_f > 0.05
	var night := frame >= NIGHT_FROM and frame < NIGHT_TO
	if night != is_night or _first:
		is_night = night
		_first = false
		phase_changed.emit(is_night)


func night_amount() -> float:
	## 0 = full day, 1 = full night (for ambience mixing)
	if frame < 120.0 or frame > 380.0:
		return 0.0
	if frame < 180.0:
		return (frame - 120.0) / 60.0
	if frame > 330.0:
		return 1.0 - (frame - 330.0) / 50.0
	return 1.0


static func lerp_angle_deg(a: float, b: float, u: float) -> float:
	return rad_to_deg(lerp_angle(deg_to_rad(a), deg_to_rad(b), u))


static func _col(c) -> Color:
	return Color(c[0], c[1], c[2])
