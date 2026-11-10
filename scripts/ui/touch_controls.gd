extends CanvasLayer
## On-screen touch controls for phones / tablets / touch browsers.
## Left half: floating move stick (drag past the ring to sprint). Right half: drag to look around.
## Bottom-right: Strike (big), Block (hold), Dodge, Jump, Use. Top-right: Bag, Wait, Menu.
## The HUD's potion slots become tap targets. Buttons drive the same InputMap actions as the keyboard,
## so player.gd needs no touch-specific logic beyond the camera.

const STICK_R := 115.0           # ring radius (canvas px)
const SPRINT_AT := 1.32          # finger beyond this * STICK_R from the origin -> sprint
const LOOK_SENS := 0.0055        # radians per canvas px (scaled by the mouse-sensitivity setting)
const MOVE_ACTIONS := ["move_left", "move_right", "move_forward", "move_back"]

var world: Node
var pad: Control

var stick_idx := -1
var stick_origin := Vector2.ZERO
var stick_finger := Vector2.ZERO
var stick_rest := Vector2.ZERO
var sprinting := false
var look_idx := -1
var held := {}                   # touch index -> button dict
var _release_at := {}            # action -> physics frame after which it may be released

## id, action (InputMap) or event (InputEventAction routed through _unhandled_input), anchor corner offset, radius, label, icon
var buttons := [
	{"id": "attack", "action": "attack", "off": Vector2(-190, -190), "r": 92.0, "label": "Strike", "icon": "sword_1"},
	{"id": "block", "action": "block", "off": Vector2(-392, -168), "r": 64.0, "label": "Block", "icon": "shield"},
	{"id": "dodge", "action": "dodge", "off": Vector2(-352, -330), "r": 58.0, "label": "Dodge"},
	{"id": "jump", "action": "jump", "off": Vector2(-222, -392), "r": 58.0, "label": "Jump"},
	{"id": "interact", "action": "interact", "off": Vector2(-80, -376), "r": 62.0, "label": "Use"},
	{"id": "menu", "event": "pause", "off": Vector2(-66, -0), "top": 268.0, "r": 46.0, "label": "Menu"},
	{"id": "bag", "event": "inventory", "off": Vector2(-168, 0), "top": 268.0, "r": 46.0, "label": "Bag", "icon": "scroll"},
	{"id": "wait", "event": "wait", "off": Vector2(-270, 0), "top": 268.0, "r": 46.0, "label": "Wait"},
]


func _ready() -> void:
	layer = 12
	process_mode = Node.PROCESS_MODE_ALWAYS
	pad = Control.new()
	pad.set_anchors_preset(Control.PRESET_FULL_RECT)
	pad.mouse_filter = Control.MOUSE_FILTER_IGNORE
	pad.draw.connect(_draw_pad)
	add_child(pad)
	for b in buttons:
		if b.has("icon"):
			b["tex"] = Game.icon(b["icon"])
	if world and world.hud and world.hud.wanted_label:
		world.hud.wanted_label.offset_top = 330   # make room for the top-right buttons


func _blocked() -> bool:
	return get_tree().paused or world == null or world.player == null or world.player.dead or not world.ui_stack.is_empty()


func _center(b: Dictionary) -> Vector2:
	var s := pad.size
	if b.has("top"):
		return Vector2(s.x + b["off"].x, b["top"])
	return s + b["off"]


func _button_at(p: Vector2) -> Dictionary:
	for b in buttons:
		if p.distance_to(_center(b)) <= b["r"] * 1.12:
			return b
	return {}


func _potion_at(p: Vector2) -> int:
	if world.hud == null:
		return -1
	for i in world.hud.potion_counts.size():
		var slot: Control = world.hud.potion_counts[i].get_parent()
		if slot.get_global_rect().grow(6).has_point(p):
			return i + 1
	return -1


func _input(event: InputEvent) -> void:
	if not (event is InputEventScreenTouch or event is InputEventScreenDrag):
		return
	if _blocked():
		if event is InputEventScreenTouch and not event.pressed:
			_finger_up(event.index)
		return
	if event is InputEventScreenTouch:
		if event.pressed:
			_finger_down(event.index, event.position)
		else:
			_finger_up(event.index)
	else:
		_finger_drag(event.index, event.position, event.relative)


func _finger_down(idx: int, p: Vector2) -> void:
	var b := _button_at(p)
	if not b.is_empty():
		held[idx] = b
		if b.has("action"):
			Input.action_press(b["action"])
			_release_at[b["action"]] = Engine.get_physics_frames() + 2
		else:
			var ev := InputEventAction.new()
			ev.action = b["event"]
			ev.pressed = true
			Input.parse_input_event(ev)
			if b["event"] in ["pause", "inventory"]:
				release_all()
		pad.queue_redraw()
		return
	var pot := _potion_at(p)
	if pot > 0:
		Input.action_press("potion_%d" % pot)
		_release_at["potion_%d" % pot] = Engine.get_physics_frames() + 2
		_release_later("potion_%d" % pot)
		return
	if p.x < pad.size.x * 0.45 and p.y > 150.0:
		if stick_idx < 0:
			stick_idx = idx
			stick_origin = p
			stick_finger = p
			_apply_stick()
	elif look_idx < 0:
		look_idx = idx


func _finger_up(idx: int) -> void:
	if held.has(idx):
		var b: Dictionary = held[idx]
		held.erase(idx)
		if b.has("action"):
			_release_later(b["action"])
		pad.queue_redraw()
	if idx == stick_idx:
		stick_idx = -1
		sprinting = false
		_apply_stick()
	if idx == look_idx:
		look_idx = -1


func _finger_drag(idx: int, p: Vector2, rel: Vector2) -> void:
	if idx == stick_idx:
		stick_finger = p
		_apply_stick()
	elif idx == look_idx or (held.has(idx) and held[idx]["id"] == "attack"):
		# Look with the right thumb; sliding off the Strike button also turns the camera.
		var pl = world.player
		var k: float = LOOK_SENS * float(Game.settings["mouse_sens"]) / 0.22
		pl.yaw -= rel.x * k
		var inv := -1.0 if Game.settings["invert_y"] else 1.0
		pl.pitch = clamp(pl.pitch - rel.y * k * 0.8 * inv, -1.2, 0.6)


func _apply_stick() -> void:
	var v := Vector2.ZERO
	if stick_idx >= 0:
		var d := stick_finger - stick_origin
		sprinting = d.length() > STICK_R * SPRINT_AT
		if d.length() > STICK_R * SPRINT_AT * 1.25:
			# drag the origin along so the thumb never runs out of room
			stick_origin = stick_finger - d.normalized() * STICK_R * SPRINT_AT * 1.25
			d = stick_finger - stick_origin
		v = d / STICK_R
		if v.length() > 1.0:
			v = v.normalized()
		if v.length() < 0.12:
			v = Vector2.ZERO
	_set_axis("move_left", max(0.0, -v.x))
	_set_axis("move_right", max(0.0, v.x))
	_set_axis("move_forward", max(0.0, -v.y))
	_set_axis("move_back", max(0.0, v.y))
	if sprinting:
		Input.action_press("sprint")
	else:
		Input.action_release("sprint")
	pad.queue_redraw()


func _set_axis(action: String, strength: float) -> void:
	if strength > 0.0:
		Input.action_press(action, strength)
	else:
		Input.action_release(action)


## Keep a tap pressed for at least two physics frames so is_action_just_pressed() in _physics_process sees it.
func _release_later(action: String) -> void:
	while Engine.get_physics_frames() < int(_release_at.get(action, 0)):
		await get_tree().physics_frame
	for b in held.values():
		if b.get("action", "") == action:
			return   # pressed again meanwhile
	Input.action_release(action)


func release_all() -> void:
	for a in MOVE_ACTIONS + ["sprint", "attack", "block", "dodge", "jump", "interact"]:
		Input.action_release(a)
	held.clear()
	stick_idx = -1
	look_idx = -1
	sprinting = false
	pad.queue_redraw()


var _was_blocked := false


func _process(_delta: float) -> void:
	var blk := _blocked()
	if blk != _was_blocked:
		_was_blocked = blk
		if blk:
			release_all()
		pad.visible = not blk
	if not blk:
		pad.queue_redraw()


# ---------------------------------------------------------------- drawing
func _draw_pad() -> void:
	var font: Font = Game.FONT_BODY
	# move stick
	var active := stick_idx >= 0
	var o := stick_origin if active else Vector2(250, pad.size.y - 330)
	var ring_col := Color(1.0, 0.82, 0.4, 0.75) if sprinting else Color(0.95, 0.9, 0.8, 0.45 if active else 0.22)
	pad.draw_circle(o, STICK_R, Color(0.08, 0.06, 0.04, 0.28 if active else 0.14))
	pad.draw_arc(o, STICK_R, 0, TAU, 48, ring_col, 4.0, true)
	if active:
		pad.draw_arc(o, STICK_R * SPRINT_AT, 0, TAU, 48, Color(1.0, 0.82, 0.4, 0.35 if not sprinting else 0.8), 2.0, true)
	var knob := o
	if active:
		var d := stick_finger - stick_origin
		knob = o + (d.normalized() * min(d.length(), STICK_R) if d.length() > 0.0 else Vector2.ZERO)
	pad.draw_circle(knob, 48.0, Color(0.95, 0.88, 0.7, 0.6 if active else 0.3))
	if not active:
		_text(font, "Move", o + Vector2(0, STICK_R + 30), 28, Color(0.95, 0.9, 0.8, 0.5))
	# buttons
	var focus_on: bool = world != null and world.player != null and not world.player.focus.is_empty()
	for b in buttons:
		var c := _center(b)
		var r: float = b["r"]
		var down := false
		for hb in held.values():
			if hb["id"] == b["id"]:
				down = true
		var bg := Color(0.1, 0.07, 0.05, 0.62 if down else 0.42)
		var edge := Color(0.86, 0.68, 0.32, 0.95 if down else 0.6)
		if b["id"] == "interact":
			if focus_on:
				var pulse := 0.5 + 0.5 * sin(Time.get_ticks_msec() / 160.0)
				edge = Color(1.0, 0.85, 0.35, 0.7 + 0.3 * pulse)
				bg = Color(0.35, 0.22, 0.05, 0.55 + 0.15 * pulse)
			else:
				bg.a *= 0.6
				edge.a *= 0.5
		if b["id"] == "block" and down:
			bg = Color(0.15, 0.2, 0.35, 0.65)
		pad.draw_circle(c, r, bg)
		pad.draw_arc(c, r, 0, TAU, 56, edge, 4.0 if r > 50.0 else 3.0, true)
		var tex: Texture2D = b.get("tex")
		var fs := 32 if r > 50.0 else 26
		if tex:
			var isz := r * (1.05 if r > 50.0 else 0.95)
			pad.draw_texture_rect(tex, Rect2(c - Vector2(isz, isz) * 0.5 - Vector2(0, r * 0.14), Vector2(isz, isz)), false,
				Color(1, 1, 1, 0.9))
			_text(font, b["label"], c + Vector2(0, r * 0.6), fs - 4, Color(0.98, 0.93, 0.82, 0.95))
		else:
			_text(font, b["label"], c, fs, Color(0.98, 0.93, 0.82, 0.95))


func _text(font: Font, s: String, center: Vector2, size: int, col: Color) -> void:
	var w := font.get_string_size(s, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
	var asc := font.get_ascent(size)
	var desc := font.get_descent(size)
	var pos := center + Vector2(-w * 0.5, (asc - desc) * 0.5)
	pad.draw_string(font, pos + Vector2(2, 2), s, HORIZONTAL_ALIGNMENT_LEFT, -1, size, Color(0, 0, 0, col.a * 0.7))
	pad.draw_string(font, pos, s, HORIZONTAL_ALIGNMENT_LEFT, -1, size, col)
