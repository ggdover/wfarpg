extends Control
## The start screen: pick one of the demo's scenes (scripts/scenes.gd), and start it with the new trees or the old.

func _ready() -> void:
	var font: Font = load("res://assets/fonts/Cinzel.ttf")
	var bold: Font = load("res://assets/fonts/CinzelDecorative-Bold.ttf")
	var bg := ColorRect.new()
	bg.color = Color("#1E1C18")
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	var centre := CenterContainer.new()
	centre.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(centre)
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 14)
	col.alignment = BoxContainer.ALIGNMENT_CENTER
	centre.add_child(col)
	var title := Label.new()
	title.text = "wfarpg"
	title.add_theme_font_override("font", bold)
	title.add_theme_font_size_override("font_size", 64)
	title.add_theme_color_override("font_color", Color("#E8D9B0"))
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	col.add_child(title)
	var sub := Label.new()
	sub.text = "Play demo · Act 1"
	sub.add_theme_font_override("font", font)
	sub.add_theme_font_size_override("font_size", 24)
	sub.add_theme_color_override("font_color", Color("#C9B58A"))
	sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	col.add_child(sub)
	var about := Label.new()
	about.text = "Pick a scene, then start it with the new trees or the old: the same place either way, only the trees differ."
	about.add_theme_font_size_override("font_size", 15)
	about.add_theme_color_override("font_color", Color("#CFC6B2"))
	about.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	col.add_child(about)
	var picker := ScenePicker.new()
	picker.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	col.add_child(picker)
	picker.setup(Game.scene, "")
	picker.picked.connect(func(id: String) -> void: Game.scene = id)
	var gap := Control.new()
	gap.custom_minimum_size = Vector2(0, 10)
	col.add_child(gap)
	for choice in [["new", "New trees", "the tree portfolio, built in Blender"], ["old", "Old trees", "as in the mockup screenshots"]]:
		var b := Button.new()
		b.text = "%s  ·  %s" % [choice[1], choice[2]]
		b.custom_minimum_size = Vector2(520, 54)
		b.add_theme_font_override("font", font)
		b.add_theme_font_size_override("font_size", 19)
		for state in ["normal", "hover", "pressed", "focus"]:
			var sb := StyleBoxFlat.new()
			sb.bg_color = Color("#2A2620") if state == "normal" else Color("#3A3328")
			sb.border_color = Color("#B8995E") if state != "normal" else Color("#6E5D3E")
			sb.set_border_width_all(1)
			sb.set_corner_radius_all(0)
			sb.draw_center = state != "focus"
			b.add_theme_stylebox_override(state, sb)
		b.add_theme_color_override("font_color", Color("#E8D9B0"))
		b.add_theme_color_override("font_hover_color", Color("#FFF1CC"))
		b.pressed.connect(_start.bind(choice[0]))
		col.add_child(b)
		if choice[0] == Game.tree_set:
			b.call_deferred("grab_focus")
	var keys := Label.new()
	keys.text = "WASD walk  ·  right mouse button orbits the camera  ·  wheel zooms  ·  T swaps the trees  ·  Tab scenes  ·  F1 help"
	keys.add_theme_font_size_override("font_size", 13)
	keys.add_theme_color_override("font_color", Color("#9C927E"))
	keys.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	col.add_child(keys)
	for a in OS.get_cmdline_user_args():  # for checking the screen from the command line
		if a == "--play":  # straight into the demo, as the exported game can't be given demo.tscn to start in
			_start.call_deferred(Game.tree_set)
		elif a.begins_with("--shot="):
			await get_tree().create_timer(0.5).timeout
			get_viewport().get_texture().get_image().save_png(a.substr(7))
			get_tree().quit()


func _start(which: String) -> void:
	Game.tree_set = which
	get_tree().change_scene_to_file("res://scenes/demo.tscn")
