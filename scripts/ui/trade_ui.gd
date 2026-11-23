extends Control
## Market trade window: merchant portrait | merchant goods (buy) | your goods (sell at 50%) | purse.

var world: Node
var stock: Array = []
var stall_type := "produce"
var merchant := "merchant"
var merchant_name := ""
var buy_grid: GridContainer
var sell_grid: GridContainer
var gold_label: Label
var info: Label
var buy_btn: Button
var picked := ""               # merchant's item chosen with a click: its details + the Buy button

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
	var n := UiKit.title(merchant_name if merchant_name != "" else NAMES.get(merchant, "Trader"), 30)
	n.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	left.add_child(n)
	info = UiKit.label("\"Look, but pay before you touch.\"
Click my goods to see them, yours to sell them.", 20, Color(0.3, 0.2, 0.12), true)
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
	buy_btn = UiKit.button("Buy", func(): _buy(picked), 240)
	buy_btn.visible = false
	left.add_child(buy_btn)
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
		var stats := Game.item_stats(id)
		buy_grid.add_child(_cell(id, 0, price, _pick.bind(id), "%s%s
%s" % [Game.ITEMS[id]["name"], ("
" + stats) if stats != "" else "", Game.ITEMS[id]["desc"]]))
	for id in Game.inventory:
		if Game.ITEMS[id]["type"] == "quest":
			continue
		var sp: int = max(1, int(Game.ITEMS[id]["price"] * 0.5))
		sell_grid.add_child(_cell(id, Game.count(id), sp, _sell.bind(id), "%s — click to sell" % Game.ITEMS[id]["name"]))
	gold_label.text = str(Game.gold)
	if picked != "" and buy_btn:
		buy_btn.disabled = Game.gold < int(Game.ITEMS[picked]["price"])


## Click on the merchant's goods: show what it is first, buy with the button.
func _pick(id: String) -> void:
	picked = id
	Sfx.play("cloth")
	var it: Dictionary = Game.ITEMS[id]
	var stats := Game.item_stats(id)
	info.text = "%s%s
%s" % [it["name"], ("
" + stats) if stats != "" else "", it["desc"]]
	buy_btn.text = "Buy — %d g" % it["price"]
	buy_btn.disabled = Game.gold < int(it["price"])
	buy_btn.visible = true


func _buy(id: String) -> void:
	if id == "":
		return
	var price: int = Game.ITEMS[id]["price"]
	if Game.gold < price:
		info.text = "\"You are %d groschen short, sir knight.\"" % (price - Game.gold)
		return
	Game.add_gold(-price, true)
	Game.add_item(id, 1, true)
	Sfx.play("coin")
	info.text = "\"%s — a fine choice.\"" % Game.ITEMS[id]["name"]
	if Game.ITEMS[id]["type"] in ["weapon", "equip"] and (Game.ITEMS[id]["type"] == "weapon" or Game.equipment.get(Game.ITEMS[id]["slot"], "") == ""):
		Game.equip(id)        # into your hand / onto you right away; the old weapon goes into the pack
		info.text = "\"%s — a fine choice. Wear it well, sir knight.\"
%s" % [Game.ITEMS[id]["name"], Game.item_stats(id)]
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
