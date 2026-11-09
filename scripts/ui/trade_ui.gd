extends Control
## Market trade window: merchant portrait | merchant goods (buy) | your goods (sell at 50%) | purse.

var world: Node
var stock: Array = []
var stall_type := "produce"
var merchant := "merchant"
var buy_grid: GridContainer
var sell_grid: GridContainer
var gold_label: Label
var info: Label

const NAMES := {"merchant": "Master Kunz, merchant", "market_woman": "Dorota, market woman", "butcher": "Havel the butcher"}


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	theme = UiKit.theme()
	UiKit.dim(self, 0.5)
	var p := UiKit.panel(Vector2(1380, 760))
	UiKit.centered(self, p)
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 24)
	p.add_child(h)
	var left := VBoxContainer.new()
	left.custom_minimum_size = Vector2(300, 0)
	h.add_child(left)
	var por := TextureRect.new()
	var pp := "res://assets/ui/portraits/%s.png" % merchant
	por.texture = load(pp) if ResourceLoader.exists(pp) else load("res://assets/ui/portraits/merchant.png")
	por.custom_minimum_size = Vector2(300, 420)
	por.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	por.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	left.add_child(por)
	var n := UiKit.title(NAMES.get(merchant, "Trader"), 30)
	n.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	left.add_child(n)
	info = UiKit.label("\"Look, but pay before you touch.\"", 20, Color(0.3, 0.2, 0.12), true)
	left.add_child(info)
	var gh := HBoxContainer.new()
	var gi := TextureRect.new()
	gi.texture = Game.icon("gold")
	gi.custom_minimum_size = Vector2(48, 40)
	gi.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	gi.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	gh.add_child(gi)
	gold_label = UiKit.title(str(Game.gold), 40)
	gh.add_child(gold_label)
	left.add_child(gh)
	left.add_child(UiKit.button("Leave", func(): world.close_ui(), 240))
	buy_grid = _column(h, "Merchant's goods")
	sell_grid = _column(h, "Your goods")
	Game.inventory_changed.connect(_refresh)
	_refresh()


func _column(parent: Control, title: String) -> GridContainer:
	var v := VBoxContainer.new()
	v.custom_minimum_size = Vector2(480, 0)
	parent.add_child(v)
	v.add_child(UiKit.title(title, 36))
	var sc := ScrollContainer.new()
	sc.custom_minimum_size = Vector2(480, 600)
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	v.add_child(sc)
	var g := GridContainer.new()
	g.columns = 4
	g.add_theme_constant_override("h_separation", 10)
	g.add_theme_constant_override("v_separation", 6)
	sc.add_child(g)
	return g


func _cell(id: String, n: int, price: int, cb: Callable, tip: String) -> VBoxContainer:
	var v := VBoxContainer.new()
	var b := UiKit.slot(id, n, 104, tip)
	b.pressed.connect(cb)
	v.add_child(b)
	var tag := PanelContainer.new()
	var ts := StyleBoxTexture.new()
	ts.texture = UiKit.tex("parchment.png")
	ts.set_content_margin_all(2)
	tag.add_theme_stylebox_override("panel", ts)
	var l := UiKit.label("%d g" % price, 18)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	tag.add_child(l)
	v.add_child(tag)
	return v


func _refresh() -> void:
	for c in buy_grid.get_children():
		c.queue_free()
	for c in sell_grid.get_children():
		c.queue_free()
	for id in stock:
		var price: int = Game.ITEMS[id]["price"]
		buy_grid.add_child(_cell(id, 0, price, _buy.bind(id), "%s — %s" % [Game.ITEMS[id]["name"], Game.ITEMS[id]["desc"]]))
	for id in Game.inventory:
		var sp: int = max(1, int(Game.ITEMS[id]["price"] * 0.5))
		sell_grid.add_child(_cell(id, Game.count(id), sp, _sell.bind(id), "%s — click to sell" % Game.ITEMS[id]["name"]))
	gold_label.text = str(Game.gold)


func _buy(id: String) -> void:
	var price: int = Game.ITEMS[id]["price"]
	if Game.gold < price:
		info.text = "\"You are %d groschen short, sir knight.\"" % (price - Game.gold)
		return
	Game.add_gold(-price, true)
	Game.add_item(id, 1, true)
	Sfx.play("coin")
	info.text = "\"%s — a fine choice.\"" % Game.ITEMS[id]["name"]
	_refresh()


func _sell(id: String) -> void:
	if Game.count(id) <= 0:
		return
	var sp: int = max(1, int(Game.ITEMS[id]["price"] * 0.5))
	Game.add_item(id, -1, true)
	Game.add_gold(sp, true)
	Sfx.play("coin")
	info.text = "\"I'll take that %s off your hands.\"" % Game.ITEMS[id]["name"].to_lower()
	_refresh()
