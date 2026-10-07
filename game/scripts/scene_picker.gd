class_name ScenePicker
extends PanelContainer
## A list of the demo's scenes (scripts/scenes.gd) to pick from: a button each, with its title and a line about it,
## in two columns, the current one marked. The start screen shows it, and the game opens it with the Scenes button or Tab.

signal picked(id: String)

const INK := Color("#E6E0D2")
const DIM := Color("#B7AE9A")
const BRASS := Color("#C9A24A")

var _buttons := {}  # scene id -> its button


func setup(current: String, title := "Scenes") -> void:
	var bg := StyleBoxFlat.new()
	bg.bg_color = Color(0.09, 0.08, 0.065, 0.92)
	bg.border_color = Color(0.72, 0.6, 0.38, 0.75)
	bg.set_border_width_all(1)
	bg.set_content_margin_all(12)
	add_theme_stylebox_override("panel", bg)
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 6)
	add_child(col)
	var grid := GridContainer.new()
	grid.columns = 2
	grid.add_theme_constant_override("h_separation", 4)
	grid.add_theme_constant_override("v_separation", 4)
	if title:
		var head := Label.new()
		head.text = title
		head.add_theme_font_override("font", load("res://assets/fonts/Cinzel.ttf"))
		head.add_theme_font_size_override("font_size", 18)
		head.add_theme_color_override("font_color", Color("#E8D9B0"))
		col.add_child(head)
	col.add_child(grid)
	for s: Dictionary in Scenes.LIST:
		var b := Button.new()
		b.toggle_mode = true
		b.focus_mode = Control.FOCUS_NONE
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		b.custom_minimum_size = Vector2(430, 0)
		b.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		b.text = "%s\n%s" % [s["title"], s["about"]]
		b.add_theme_font_size_override("font_size", 14)
		for state in ["normal", "hover", "pressed", "hover_pressed"]:
			var sb := StyleBoxFlat.new()
			var on: bool = (state as String).contains("pressed")
			sb.bg_color = Color("#5A4A2A") if on else (Color("#3A3328") if state == "hover" else Color("#2A2620"))
			sb.border_color = BRASS if on else Color("#6E5D3E")
			sb.set_border_width_all(1)
			sb.content_margin_left = 10
			sb.content_margin_right = 10
			sb.content_margin_top = 5
			sb.content_margin_bottom = 5
			b.add_theme_stylebox_override(state, sb)
		b.add_theme_color_override("font_color", DIM)
		b.add_theme_color_override("font_hover_color", INK)
		b.add_theme_color_override("font_pressed_color", Color("#FFF1CC"))
		b.add_theme_color_override("font_hover_pressed_color", Color("#FFF1CC"))
		b.pressed.connect(_pick.bind(s["id"]))
		grid.add_child(b)
		_buttons[s["id"]] = b
	mark(current)


## Mark the scene as the one picked.
func mark(id: String) -> void:
	for k: String in _buttons:
		(_buttons[k] as Button).set_pressed_no_signal(k == id)


func _pick(id: String) -> void:
	mark(id)
	picked.emit(id)
