extends Control
## Blacksmith: sword upgrades.

var world: Node
var body: VBoxContainer


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	theme = UiKit.theme()
	UiKit.dim(self, 0.5)
	var p := UiKit.panel(Vector2(760, 520))
	UiKit.centered(self, p)
	body = VBoxContainer.new()
	body.add_theme_constant_override("separation", 14)
	p.add_child(body)
	_refresh()


func _refresh() -> void:
	for c in body.get_children():
		c.queue_free()
	body.add_child(UiKit.title("The Blacksmith's Anvil", 48))
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 24)
	h.alignment = BoxContainer.ALIGNMENT_CENTER
	body.add_child(h)
	var cur: Dictionary = Game.sword()
	h.add_child(_card(Game.sword_level, cur, "Your blade"))
	if Game.sword_level < Game.SWORDS.size() - 1:
		var arrow := UiKit.title("→", 64, UiKit.BLOOD)
		h.add_child(arrow)
		var nxt: Dictionary = Game.SWORDS[Game.sword_level + 1]
		h.add_child(_card(Game.sword_level + 1, nxt, "After the work"))
		var cost: int = nxt["cost"]
		var b := UiKit.button("Hammer it — %d gold" % cost, _upgrade.bind(cost), 380)
		b.disabled = Game.gold < cost
		body.add_child(_center(b))
		var lbl := UiKit.label("\"Bring me coin and I'll fold the steel again.\"" if Game.gold < cost else "\"A fine blade deserves a fine edge.\"", 20, UiKit.INK)
		lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		body.add_child(lbl)
	else:
		var l := UiKit.label("\"There is nothing left I can teach this steel.\"", 22)
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		body.add_child(l)
	var gl := UiKit.label("Your purse: %d gold" % Game.gold, 22, UiKit.INK)
	gl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	body.add_child(gl)
	body.add_child(_center(UiKit.button("Leave", func(): world.close_ui())))


func _center(c: Control) -> CenterContainer:
	var cc := CenterContainer.new()
	cc.add_child(c)
	return cc


func _card(lvl: int, s: Dictionary, caption: String) -> VBoxContainer:
	var v := VBoxContainer.new()
	v.custom_minimum_size = Vector2(230, 0)
	var ic := TextureRect.new()
	ic.texture = Game.icon("sword_%d" % (lvl + 1))
	ic.custom_minimum_size = Vector2(140, 140)
	ic.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	ic.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	v.add_child(ic)
	var t := UiKit.title(s["name"], 30)
	v.add_child(t)
	var d := UiKit.label("Damage: %d–%d" % [s["min"], s["max"]], 22)
	d.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(d)
	var c := UiKit.label(caption, 18, Color(0.35, 0.25, 0.15))
	c.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	v.add_child(c)
	return v


func _upgrade(cost: int) -> void:
	if Game.gold < cost:
		return
	Game.add_gold(-cost, true)
	Game.sword_level += 1
	Sfx.play("anvil")
	Game.say("The smith reforges your sword: %s." % Game.sword()["name"], Color(1, 0.85, 0.4))
	Game.stats_changed.emit()
	world.player.apply_sword_look()
	_refresh()
