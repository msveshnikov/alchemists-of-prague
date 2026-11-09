extends Node
## Sound manager: one-shot 2D/3D sounds with random variants, music with crossfade, ambience layers.

const SFX_DIR := "res://assets/audio/sfx/"
const VARIANTS := {
	"step": ["step_stone_1", "step_stone_2", "step_stone_3", "step_stone_4", "step_stone_5", "step_stone_6"],
	"swing": ["swing_1", "swing_2", "swing_3"],
	"hit": ["hit_1", "hit_2", "hit_3", "hit_4"],
	"clash": ["clash_1", "clash_2", "clash_3"],
	"glass": ["glass_1", "glass_2", "glass_3"],
	"bones": ["bones_1", "bones_2", "bones_3"],
	"scream": ["scream_0", "scream_1", "scream_2", "scream_3", "scream_4", "scream_5", "scream_6", "scream_7"],
	"hurt": ["hurt_1", "hurt_2", "hurt_3"],
	"grunt": ["grunt_1", "grunt_2", "grunt_3"],
	"coin": ["coin_1", "coin_2"],
	"ui": ["ui_1", "ui_2", "ui_3"],
	"golem": ["golem_1", "golem_2", "golem_3"],
	"skeleton": ["skeleton_1", "skeleton_2", "skeleton_3"],
}

var _cache := {}
var _music_a: AudioStreamPlayer
var _music_b: AudioStreamPlayer
var _current_music := ""
var _amb := {}


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_music_a = _make_player("Music")
	_music_b = _make_player("Music")
	for n in ["market_crowd", "night_crickets"]:
		var p := _make_player("SFX")
		p.stream = _load_any("res://assets/audio/ambience/" + n)
		_set_loop(p.stream)
		p.volume_db = -80.0
		_amb[n] = p


func _make_player(bus: String) -> AudioStreamPlayer:
	var p := AudioStreamPlayer.new()
	p.bus = bus
	add_child(p)
	return p


func _load_any(base: String) -> AudioStream:
	for ext in [".ogg", ".wav", ".mp3"]:
		if ResourceLoader.exists(base + ext):
			return load(base + ext)
	return null


func _set_loop(s: AudioStream) -> void:
	if s is AudioStreamOggVorbis or s is AudioStreamMP3:
		s.loop = true
	elif s is AudioStreamWAV:
		s.loop_mode = AudioStreamWAV.LOOP_FORWARD
		s.loop_end = int(s.get_length() * s.mix_rate)


func stream(name: String) -> AudioStream:
	var key := name
	if VARIANTS.has(name):
		key = VARIANTS[name][randi() % VARIANTS[name].size()]
	if not _cache.has(key):
		_cache[key] = _load_any(SFX_DIR + key)
	return _cache[key]


## 2D one-shot (UI, player-centred sounds).
func play(name: String, volume_db := 0.0, pitch := 1.0) -> void:
	var s := stream(name)
	if s == null:
		return
	var p := AudioStreamPlayer.new()
	p.stream = s
	p.bus = "SFX"
	p.volume_db = volume_db
	p.pitch_scale = pitch * randf_range(0.94, 1.06)
	add_child(p)
	p.play()
	p.finished.connect(p.queue_free)


## Positional one-shot in the 3D world.
func play_at(name: String, pos: Vector3, volume_db := 0.0, pitch := 1.0, parent: Node = null) -> void:
	var s := stream(name)
	if s == null:
		return
	var p := AudioStreamPlayer3D.new()
	p.stream = s
	p.bus = "SFX"
	p.volume_db = volume_db
	p.unit_size = 6.0
	p.max_distance = 60.0
	p.pitch_scale = pitch * randf_range(0.92, 1.08)
	var host: Node = parent if parent else get_tree().current_scene
	if host == null:
		return
	host.add_child(p)
	p.global_position = pos
	p.play()
	p.finished.connect(p.queue_free)


## Looping 3D emitter (fire, horse trot).
func loop_at(name: String, parent: Node3D, volume_db := -6.0, unit_size := 4.0) -> AudioStreamPlayer3D:
	var base := "res://assets/audio/ambience/" + name
	var s: AudioStream = _load_any(base)
	if s == null:
		s = _load_any(SFX_DIR + name)
	if s == null:
		return null
	s = s.duplicate()
	_set_loop(s)
	var p := AudioStreamPlayer3D.new()
	p.stream = s
	p.bus = "SFX"
	p.volume_db = volume_db
	p.unit_size = unit_size
	p.max_distance = 40.0
	parent.add_child(p)
	p.play(randf() * 2.0)
	return p


func music(name: String, fade := 2.0) -> void:
	if name == _current_music:
		return
	_current_music = name
	var old := _music_a if _music_a.playing else _music_b
	var new_p := _music_b if old == _music_a else _music_a
	if old.playing:
		var tw := create_tween()
		tw.tween_property(old, "volume_db", -60.0, fade)
		tw.tween_callback(old.stop)
	if name == "":
		return
	var s: AudioStream = _load_any("res://assets/audio/music/" + name)
	if s == null:
		return
	s = s.duplicate()
	_set_loop(s)
	new_p.stream = s
	new_p.volume_db = -60.0
	new_p.play()
	var tw2 := create_tween()
	tw2.tween_property(new_p, "volume_db", -8.0 if name == "town_theme" else -5.0, fade)


## Ambience mix: market (0..1) and night (0..1) levels.
func ambience(market: float, night: float) -> void:
	_amb_level("market_crowd", market, -14.0)
	_amb_level("night_crickets", night, -10.0)


func _amb_level(n: String, level: float, max_db: float) -> void:
	var p: AudioStreamPlayer = _amb[n]
	if level <= 0.01:
		if p.playing:
			p.stop()
		return
	if not p.playing:
		p.play()
	p.volume_db = lerp(-40.0, max_db, clamp(level, 0.0, 1.0))


func stop_ambience() -> void:
	for p in _amb.values():
		p.stop()
