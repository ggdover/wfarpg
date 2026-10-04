class_name PerfPanel
extends PanelContainer
## The performance panel (F2). At the top, a graph of every frame's time over the last few seconds, with the frame
## rate now, on average, and in the slowest 5% and 1% of frames, and what the graphics card spends on a frame. Below,
## switches for what costs time, which take effect at once, so you can flip back and forth and watch the numbers.
## "Walk the trail" walks the same way every time (scripts/trail_walk.gd) and lists each run with its settings.

const WINDOW := 3.0  ## seconds shown in the graph and counted in the numbers
const GRAPH_MS := 50.0  ## frame time at the graph's top
const INK := Color("#E6E0D2")
const DIM := Color("#B7AE9A")
const BRASS := Color("#C9A24A")

var demo: Node
var _frames: Array[Vector2] = []  # (time in s, frame ms)
var _last := 0
var _gpu: Array[float] = []
var _graph: FrameGraph
var _now_label: Label
var _detail_label: Label
var _runs_label: Label
var _walk_button: Button
var _walk: TrailWalk
var _runs: Array[String] = []
var _choices := {}  # setting -> label of the chosen option, for the run list
var _groups := {}  # setting -> {value: Button}
var _texts := {}  # setting -> its row's text
var _refresh := 0.0


func setup(d: Node) -> void:
	demo = d
	var bg := StyleBoxFlat.new()
	bg.bg_color = Color(0.09, 0.08, 0.065, 0.86)
	bg.border_color = Color(0.72, 0.6, 0.38, 0.75)
	bg.set_border_width_all(1)
	bg.set_content_margin_all(12)
	add_theme_stylebox_override("panel", bg)
	custom_minimum_size = Vector2(410, 0)
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 5)
	add_child(col)
	var title := Label.new()
	title.text = "Performance  ·  F2 hides"
	title.add_theme_font_override("font", load("res://assets/fonts/Cinzel.ttf"))
	title.add_theme_font_size_override("font_size", 17)
	title.add_theme_color_override("font_color", Color("#E8D9B0"))
	col.add_child(title)
	_graph = FrameGraph.new()
	_graph.panel = self
	_graph.custom_minimum_size = Vector2(386, 96)
	col.add_child(_graph)
	_now_label = _label(col, "", 15, INK)
	_detail_label = _label(col, "", 12, DIM)
	_rule(col)

	var w: DemoWorld = demo.world
	var vp := get_viewport()
	var sun: DirectionalLight3D = demo.get_node("DirectionalLight3D")
	var env: Environment = (demo.get_child(0) as WorldEnvironment).environment
	_choice(col, "trees", "Trees", [["Old", "old"], ["New", "new"]], Game.tree_set, func(v: String) -> void: demo.show_tree_set(v))
	_choice(col, "trimmed", "Leaf cards", [["Square", false], ["Trimmed", true]], w.trimmed, func(v: bool) -> void: w.set_trees("trimmed", v))
	_choice(col, "fewer", "Cards per clump", [["As tuned", false], ["Fewer", true]], w.fewer, func(v: bool) -> void: w.set_trees("fewer", v))
	_choice(col, "tree_shadows", "Tree shadows from", [["Full", "full"], ["Mid", "mid"], ["Far", "far"], ["None", "off"]], w.tree_shadows,
		func(v: String) -> void: w.set_trees("tree_shadows", v))
	_slider(col, "Lighter trees from", 10.0, 110.0, 5.0, w.lod_near, "%d m", func(v: float) -> void: w.set_trees("lod_near", v))
	_choice(col, "fade", "Fade trees near camera", [["On", true], ["Off", false]], w.fade_near_camera,
		func(v: bool) -> void: w.set_trees("fade_near_camera", v))
	_rule(col)
	_choice(col, "scale", "Render scale", [["100%", 1.0], ["75%", 0.75], ["50%", 0.5]], snappedf(vp.scaling_3d_scale, 0.05),
		func(v: float) -> void:
			vp.scaling_3d_mode = Viewport.SCALING_3D_MODE_FSR if v < 0.99 else Viewport.SCALING_3D_MODE_BILINEAR
			vp.scaling_3d_scale = v)
	_choice(col, "aa", "Antialiasing", [["SMAA", Viewport.SCREEN_SPACE_AA_SMAA], ["FXAA", Viewport.SCREEN_SPACE_AA_FXAA], ["Off", Viewport.SCREEN_SPACE_AA_DISABLED]],
		vp.screen_space_aa, func(v: int) -> void: vp.screen_space_aa = v as Viewport.ScreenSpaceAA)
	_choice(col, "vsync", "VSync", [["On", true], ["Off", false]], DisplayServer.window_get_vsync_mode() != DisplayServer.VSYNC_DISABLED,
		func(v: bool) -> void: DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_ENABLED if v else DisplayServer.VSYNC_DISABLED))
	_choice(col, "shadows", "Shadows", [["On", true], ["Off", false]], sun.shadow_enabled, func(v: bool) -> void: sun.shadow_enabled = v)
	_slider(col, "Shadow distance", 20.0, 120.0, 5.0, sun.directional_shadow_max_distance, "%d m",
		func(v: float) -> void: sun.directional_shadow_max_distance = v)
	_choice(col, "cascades", "Shadow cascades", [["2", DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS], ["4", DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS]],
		sun.directional_shadow_mode, func(v: int) -> void: sun.directional_shadow_mode = v as DirectionalLight3D.ShadowMode)
	_choice(col, "details", "Ground details", [["On", true], ["Off", false]], true,
		func(v: bool) -> void: w._ground_material.set_shader_parameter("details", v))
	_choice(col, "ssao", "Ambient occlusion (SSAO)", [["On", true], ["Off", false]], env.ssao_enabled, func(v: bool) -> void: env.ssao_enabled = v)
	_choice(col, "fog", "Haze", [["On", true], ["Off", false]], env.fog_enabled, func(v: bool) -> void: env.fog_enabled = v)
	_rule(col)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	col.add_child(row)
	_walk_button = _button(row, "Walk the trail", func() -> void: _toggle_walk())
	_walk_button.tooltip_text = "Walks from the start to the meadow, the same way each time, and lists the result below"
	_button(row, "Clear runs", func() -> void:
		_runs.clear()
		_update_runs())
	_runs_label = _label(col, "", 12, DIM)
	_runs_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_update_runs()
	RenderingServer.viewport_set_measure_render_time(get_viewport().get_viewport_rid(), true)
	_last = Time.get_ticks_usec()


## The frames inside the graph's window: (seconds ago, frame ms).
func frames() -> Array[Vector2]:
	return _frames


func _process(delta: float) -> void:
	var now := Time.get_ticks_usec()
	var ms := (now - _last) / 1000.0
	_last = now
	var t := now / 1000000.0
	_frames.append(Vector2(t, ms))
	while _frames.size() > 0 and _frames[0].x < t - WINDOW:
		_frames.pop_front()
	_gpu.append(RenderingServer.viewport_get_measured_render_time_gpu(get_viewport().get_viewport_rid()))
	if _gpu.size() > 30:
		_gpu.pop_front()
	_graph.queue_redraw()
	_refresh -= delta
	if _refresh <= 0.0 and visible:
		_refresh = 0.2
		_update_numbers()


func _update_numbers() -> void:
	if _frames.size() < 2:
		return
	var ms := PackedFloat32Array()
	var recent := 0.0
	var recent_n := 0
	for f in _frames:
		ms.append(f.y)
		if f.x > _frames[-1].x - 0.25:
			recent += f.y
			recent_n += 1
	var s := TrailWalk.summary(ms)
	var gpu := 0.0
	for g in _gpu:
		gpu += g
	gpu /= maxf(1.0, _gpu.size())
	_now_label.text = "Now %d   Average %d   5%% low %d   1%% low %d  fps" % [roundi(1000.0 * recent_n / maxf(recent, 0.001)),
		roundi(s["fps"]), roundi(s["low5"]), roundi(s["low1"])]
	_detail_label.text = "Graphics card %.1f ms a frame   ·   %.2f M triangles   ·   %d draw calls" % [gpu,
		RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME) / 1000000.0,
		RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME)]


func _toggle_walk() -> void:
	if _walk:
		_walk.stop()
		_walk = null
		_walk_button.text = "Walk the trail"
		return
	_walk = TrailWalk.new()
	demo.add_child(_walk)
	_walk.start(demo)
	_walk.finished.connect(_walk_done)
	_walk_button.text = "Stop walking"


func _walk_done(r: Dictionary) -> void:
	_walk = null
	_walk_button.text = "Walk the trail"
	if r.is_empty():
		return
	var settings := []
	for k in ["trees", "trimmed", "fewer", "tree_shadows", "scale", "shadows", "vsync"]:
		settings.append(_choices[k])
	_runs.push_front("%d · avg %d, 5%% low %d, 1%% low %d fps%s\n    %s" % [_runs.size() + 1, roundi(r["fps"]), roundi(r["low5"]),
		roundi(r["low1"]), "" if r["completed"] else " (stopped early)", ", ".join(settings)])
	_update_runs()


func _update_runs() -> void:
	_runs_label.text = "\n".join(_runs.slice(0, 6)) if _runs else "Runs show here. VSync caps the frame rate at the screen's; turn it off to compare."


# ------------------------------------------------------------------ building the rows
func _choice(parent: Control, key: String, text: String, options: Array, current: Variant, apply: Callable) -> void:
	var row := HBoxContainer.new()
	parent.add_child(row)
	var l := _label(row, text, 13, INK)
	l.custom_minimum_size.x = 168
	var group := ButtonGroup.new()
	_groups[key] = {}
	_texts[key] = text
	for o: Array in options:
		var b := Button.new()
		b.text = o[0]
		b.toggle_mode = true
		b.button_group = group
		b.focus_mode = Control.FOCUS_NONE
		b.add_theme_font_size_override("font_size", 12)
		b.custom_minimum_size = Vector2(52, 24)
		_style(b)
		row.add_child(b)
		_groups[key][o[1]] = b
		if o[1] == current:
			b.button_pressed = true
			_choices[key] = "%s %s" % [text.to_lower(), o[0].to_lower()]
		b.toggled.connect(func(on: bool) -> void:
			if on:
				_choices[key] = "%s %s" % [text.to_lower(), o[0].to_lower()]
				apply.call(o[1]))


## Press one of a row's buttons, as a click would (for the dev panel test).
func choose(key: String, value: Variant) -> void:
	(_groups[key][value] as Button).button_pressed = true


## Mark a choice as made elsewhere (T swaps the trees, F4 the render scale) without applying it again.
func show_choice(key: String, value: Variant) -> void:
	var b: Button = _groups.get(key, {}).get(value)
	if b and not b.button_pressed:
		b.set_pressed_no_signal(true)
		_choices[key] = "%s %s" % [_texts[key].to_lower(), b.text.to_lower()]


func _slider(parent: Control, text: String, lo: float, hi: float, step: float, value: float, fmt: String, apply: Callable) -> void:
	var row := HBoxContainer.new()
	parent.add_child(row)
	var l := _label(row, text, 13, INK)
	l.custom_minimum_size.x = 168
	var s := HSlider.new()
	s.min_value = lo
	s.max_value = hi
	s.step = step
	s.value = value
	s.focus_mode = Control.FOCUS_NONE
	s.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	s.custom_minimum_size.y = 22
	row.add_child(s)
	var v := _label(row, fmt % value, 12, DIM)
	v.custom_minimum_size.x = 42
	s.value_changed.connect(func(x: float) -> void: v.text = fmt % x)
	s.drag_ended.connect(func(_changed: bool) -> void: apply.call(s.value))


func _button(parent: Control, text: String, on_press: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.focus_mode = Control.FOCUS_NONE
	b.add_theme_font_size_override("font_size", 13)
	b.custom_minimum_size = Vector2(0, 28)
	_style(b)
	b.pressed.connect(on_press)
	parent.add_child(b)
	return b


func _style(b: Button) -> void:
	for state in ["normal", "hover", "pressed", "hover_pressed"]:
		var sb := StyleBoxFlat.new()
		var on: bool = (state as String).contains("pressed")
		sb.bg_color = Color("#5A4A2A") if on else (Color("#3A3328") if state == "hover" else Color("#2A2620"))
		sb.border_color = BRASS if on else Color("#6E5D3E")
		sb.set_border_width_all(1)
		sb.set_content_margin_all(4)
		b.add_theme_stylebox_override(state, sb)
	b.add_theme_color_override("font_color", DIM)
	b.add_theme_color_override("font_pressed_color", Color("#FFF1CC"))
	b.add_theme_color_override("font_hover_color", INK)
	b.add_theme_color_override("font_hover_pressed_color", Color("#FFF1CC"))


func _label(parent: Control, text: String, size: int, colour: Color) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", colour)
	parent.add_child(l)
	return l


func _rule(parent: Control) -> void:
	var r := ColorRect.new()
	r.color = Color(0.72, 0.6, 0.38, 0.35)
	r.custom_minimum_size = Vector2(0, 1)
	parent.add_child(r)


## The frame-time graph: one bar per frame over the last few seconds, green under 60 fps' 16.7 ms, amber under
## 30 fps' 33.3 ms, red above, with lines at both.
class FrameGraph extends Control:
	var panel: PerfPanel

	func _draw() -> void:
		var w := size.x
		var h := size.y
		draw_rect(Rect2(Vector2.ZERO, size), Color(0, 0, 0, 0.35))
		var frames := panel.frames()
		if frames.is_empty():
			return
		var t1: float = frames[-1].x
		for f in frames:
			var x := w * (1.0 - (t1 - f.x) / PerfPanel.WINDOW)
			var bh := h * minf(f.y / PerfPanel.GRAPH_MS, 1.0)
			var c := Color("#7FB069") if f.y < 17.5 else (Color("#E0B850") if f.y < 34.0 else Color("#D9534F"))
			draw_line(Vector2(x, h), Vector2(x, h - bh), c, 2.0)
		var font := get_theme_default_font()
		for line in [[1000.0 / 60.0, "60 fps"], [1000.0 / 30.0, "30 fps"]]:
			var y: float = h - h * float(line[0]) / PerfPanel.GRAPH_MS
			draw_line(Vector2(0, y), Vector2(w, y), Color(1, 1, 1, 0.45), 1.0)
			draw_rect(Rect2(2, y - 14, 44, 13), Color(0, 0, 0, 0.6))
			draw_string(font, Vector2(5, y - 4), line[1], HORIZONTAL_ALIGNMENT_LEFT, -1, 11, Color(1, 1, 1, 0.85))
		draw_string(font, Vector2(w - 76, 12), "last %d s" % PerfPanel.WINDOW, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, Color(1, 1, 1, 0.6))
