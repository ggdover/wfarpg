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
const NO_LIMIT := 250.0  ## the frame rate limit slider's top end, which means no limit
## the speed-ups of the performance pass (README.md, Speed), each switch as it was before it and as it is now
const BEFORE := {"trimmed": false, "tree_shadows": "mid", "shadow_reach": 0.0, "impostors": 0.0, "details": 3}
const SPED_UP := {"trimmed": true, "tree_shadows": "pictures", "shadow_reach": 60.0, "impostors": 90.0, "details": 4}

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
var _sliders := {}  # setting -> a function that moves its slider and applies the value
var _refresh := 0.0
var _theme_box: OptionButton


func setup(d: Node) -> void:
	demo = d
	var bg := StyleBoxFlat.new()
	bg.bg_color = Color(0.09, 0.08, 0.065, 0.86)
	bg.border_color = Color(0.72, 0.6, 0.38, 0.75)
	bg.set_border_width_all(1)
	bg.set_content_margin_all(12)
	add_theme_stylebox_override("panel", bg)
	custom_minimum_size = Vector2(500, 0)
	var scroll := ScrollContainer.new()  # in a small window, the panel scrolls
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.custom_minimum_size = Vector2(476, minf(get_viewport().get_visible_rect().size.y - 60.0, 900.0))
	add_child(scroll)
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 3)
	col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(col)
	var title := Label.new()
	title.text = "Performance  ·  F2 hides"
	title.add_theme_font_override("font", load("res://assets/fonts/Cinzel.ttf"))
	title.add_theme_font_size_override("font_size", 17)
	title.add_theme_color_override("font_color", Color("#E8D9B0"))
	col.add_child(title)
	_graph = FrameGraph.new()
	_graph.panel = self
	_graph.custom_minimum_size = Vector2(464, 90)
	col.add_child(_graph)
	_now_label = _label(col, "", 15, INK)
	_detail_label = _label(col, "", 12, DIM)
	_rule(col)

	var w: DemoWorld = demo.world
	var vp := get_viewport()
	var sun: DirectionalLight3D = demo.get_node("DirectionalLight3D")
	var env: Environment = (demo.get_child(0) as WorldEnvironment).environment
	var row_s := HBoxContainer.new()  # all the speed-ups at once; each has its own switch below too
	row_s.add_theme_constant_override("separation", 8)
	col.add_child(row_s)
	var ls := _label(row_s, "Speed-ups", 13, INK)
	ls.custom_minimum_size.x = 150
	var before := _button(row_s, "All as before", func() -> void: choose_all(BEFORE))
	before.tooltip_text = "Square leaf cards, shadows from the mid trees, from all trees, no far trees as pictures, ground details high"
	var on := _button(row_s, "All on", func() -> void: choose_all(SPED_UP))
	on.tooltip_text = "Trimmed leaf cards, shadows from pictures, from trees within 60 m, far trees as pictures from 90 m, ground details baked"
	_choice(col, "trees", "Trees", [["Old", "old"], ["New", "new"]], Game.tree_set, func(v: String) -> void: demo.show_tree_set(v))
	var row0 := HBoxContainer.new()
	col.add_child(row0)
	var l0 := _label(row0, "Path colours (P)", 13, INK)
	l0.custom_minimum_size.x = 150
	_theme_box = OptionButton.new()
	_theme_box.focus_mode = Control.FOCUS_NONE
	_theme_box.add_theme_font_size_override("font_size", 12)
	_theme_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	for t: String in PathThemes.ORDER:
		_theme_box.add_item(t)
		_theme_box.set_item_tooltip(_theme_box.item_count - 1, PathThemes.THEMES[t]["about"])
	_theme_box.select(PathThemes.ORDER.find(Game.path_theme))
	_theme_box.item_selected.connect(func(i: int) -> void: demo.show_path_theme(PathThemes.ORDER[i]))
	row0.add_child(_theme_box)
	_choices["theme"] = "paths " + Game.path_theme.to_lower()
	_slider(col, "path_wear", "Path wear spread", 0.0, 1.0, 0.1, w.path_wear, "%.1f", func(v: float) -> void: w.set_path_wear(v))
	_choice(col, "trimmed", "Leaf cards", [["Square", false], ["Trimmed", true]], w.trimmed, func(v: bool) -> void: w.set_trees("trimmed", v))
	_choice(col, "fewer", "Cards per clump", [["As tuned", false], ["Fewer", true]], w.fewer, func(v: bool) -> void: w.set_trees("fewer", v))
	_choice(col, "tree_shadows", "Tree shadows from", [["Full", "full"], ["Mid", "mid"], ["Far", "far"], ["Pictures", "pictures"], ["None", "off"]], w.tree_shadows,
		func(v: String) -> void: w.set_trees("tree_shadows", v))
	_choice(col, "shadow_reach", "  from trees within", [["All", 0.0], ["60 m", 60.0], ["40 m", 40.0], ["25 m", 25.0]], w.shadow_reach,
		func(v: float) -> void: w.set_trees("shadow_reach", v))
	_slider(col, "lod_near", "Lighter trees from", 10.0, 110.0, 5.0, w.lod_near, "%d m", func(v: float) -> void: w.set_trees("lod_near", v))
	_choice(col, "impostors", "Far trees as pictures", [["Never", 0.0], ["From 120 m", 120.0], ["90 m", 90.0], ["60 m", 60.0]], w.impostors_from,
		func(v: float) -> void: w.set_trees("impostors_from", v))
	_choice(col, "fade", "Fade trees near camera", [["On", true], ["Off", false]], w.fade_near_camera,
		func(v: bool) -> void: w.set_trees("fade_near_camera", v))
	var percent := func(v: float) -> String: return "%d%%" % roundi(v * 100.0)
	_choice(col, "sight", "Trees in the way", [["Trunk", "trunk"], ["Cone", "cone"], ["Front", "front"], ["X-ray", "xray"], ["Area", "area"], ["Line", "line"], ["Keep", "off"]],
		w.cut_trees, func(v: String) -> void: w.set_trees("cut_trees", v))
	_slider(col, "reveal", "  trunk: cone behind", 1.0, 6.0, 1.0, w.reveal_layers,
		func(v: float) -> String: return "%d tree%s" % [roundi(v), "" if roundi(v) == 1 else "s"],
		func(v: float) -> void: w.reveal_layers = roundi(v))
	_slider(col, "reveal_out", "  trunk: cone fades out", 0.0, 1.0, 0.05, w.reveal_out, "%.2f s", func(v: float) -> void: w.reveal_out = v)
	_slider(col, "spruce_cover", "  spruce covers", 0.2, 1.0, 0.05, w.spruce_cover, percent, func(v: float) -> void: w.spruce_cover = v)
	_slider(col, "spruce_veil", "  spruce see-through", 0.0, 0.9, 0.05, w.spruce_veil, percent, func(v: float) -> void: w.set_trees("spruce_veil", v))
	_slider(col, "cone_soft", "  cone: soft share", 0.1, 1.0, 0.05, w.cone_soft, percent, func(v: float) -> void: w.cone_soft = v)
	_choice(col, "cone_style", "  cone: fade in", [["Dither", "dither"], ["Patches", "patches"]], w.cone_style,
		func(v: String) -> void: w.cone_style = v)
	_slider(col, "cone_tip", "  cone: round the hero", 1.0, 6.0, 0.25, w.cone_tip, "%.1f×", func(v: float) -> void: w.cone_tip = v)
	_slider(col, "cone_power", "  cone: wide for longer", 0.5, 3.0, 0.1, w.cone_power, "%.1f", func(v: float) -> void: w.cone_power = v)
	_choice(col, "leave", "  leave", [["Stumps", "stumps"], ["Trunks", "trunks"], ["Nothing", "nothing"]], w.leave,
		func(v: String) -> void: w.set_trees("leave", v))
	_choice(col, "cut_by", "  a tree goes by", [["Its trunk", "trunk"], ["Any part", "any"]], w.cut_by,
		func(v: String) -> void: w.set_trees("cut_by", v))
	_slider(col, "cut_width", "  area width", 0.2, 1.0, 0.02, w.cut_half_width * 2.0, percent, func(v: float) -> void: w.cut_half_width = v * 0.5)
	_slider(col, "cut_top", "  area from the top", 0.0, 0.5, 0.02, w.cut_top, percent, func(v: float) -> void: w.cut_top = v)
	_slider(col, "cut_near", "  near the camera", 0.0, 0.8, 0.05, w.cut_near, percent, func(v: float) -> void: w.cut_near = v)
	_slider(col, "cut_front", "  in front: by at least", 0.0, 5.0, 0.5, w.cut_front, "%.1f m", func(v: float) -> void: w.cut_front = v)
	_slider(col, "cut_behind", "  lower middle: past hero", 0.0, 20.0, 1.0, w.cut_behind, "%d m", func(v: float) -> void: w.cut_behind = v)
	_slider(col, "sight_clear", "  clear round the hero", 0.0, 8.0, 0.5, w.sight_clear, "%.1f m", func(v: float) -> void: w.sight_clear = v)
	_rule(col)
	_choice(col, "scale", "Render scale", [["100%", 1.0], ["75%", 0.75], ["50%", 0.5]], snappedf(vp.scaling_3d_scale, 0.05),
		func(v: float) -> void:
			vp.scaling_3d_mode = Viewport.SCALING_3D_MODE_FSR if v < 0.99 else Viewport.SCALING_3D_MODE_BILINEAR
			vp.scaling_3d_scale = v)
	_choice(col, "aa", "Antialiasing", [["SMAA", Viewport.SCREEN_SPACE_AA_SMAA], ["FXAA", Viewport.SCREEN_SPACE_AA_FXAA], ["Off", Viewport.SCREEN_SPACE_AA_DISABLED]],
		vp.screen_space_aa, func(v: int) -> void: vp.screen_space_aa = v as Viewport.ScreenSpaceAA)
	_choice(col, "vsync", "VSync", [["On", true], ["Off", false]], DisplayServer.window_get_vsync_mode() != DisplayServer.VSYNC_DISABLED,
		func(v: bool) -> void: DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_ENABLED if v else DisplayServer.VSYNC_DISABLED))
	# the frame rate limit: the slider's top end is none
	var fps_text := func(v: float) -> String: return "none" if v > NO_LIMIT - 1.0 else "%d fps" % roundi(v)
	_choices["fps"] = "limit " + fps_text.call(NO_LIMIT if Engine.max_fps == 0 else float(Engine.max_fps))
	_slider(col, "fps", "Frame rate limit", 30.0, NO_LIMIT, 10.0, NO_LIMIT if Engine.max_fps == 0 else float(Engine.max_fps), fps_text,
		func(v: float) -> void:
			Engine.max_fps = 0 if v > NO_LIMIT - 1.0 else roundi(v)
			_choices["fps"] = "limit " + fps_text.call(v))
	_rule(col)
	_choice(col, "shadows", "Shadows", [["On", true], ["Off", false]], sun.shadow_enabled, func(v: bool) -> void: sun.shadow_enabled = v)
	_choice(col, "shadow_fit", "Shadow distance", [["Fit the view", true], ["Fixed", false]], demo.shadow_fit,
		func(v: bool) -> void: demo.shadow_fit = v)
	_slider(col, "shadow_cap", "  fixed, or at most", 20.0, 120.0, 5.0, demo.shadow_cap, "%d m", func(v: float) -> void: demo.shadow_cap = v)
	_choice(col, "shadow_size", "Shadow resolution", [["4096", 4096], ["2048", 2048], ["1024", 1024], ["512", 512]],
		ProjectSettings.get_setting("rendering/lights_and_shadows/directional_shadow/size"),
		func(v: int) -> void: RenderingServer.directional_shadow_atlas_set_size(v, true))
	_choice(col, "shadow_soft", "Shadow softness", [["Hard", RenderingServer.SHADOW_QUALITY_HARD], ["Low", RenderingServer.SHADOW_QUALITY_SOFT_LOW],
		["High", RenderingServer.SHADOW_QUALITY_SOFT_HIGH]], RenderingServer.SHADOW_QUALITY_SOFT_LOW,
		func(v: int) -> void: RenderingServer.directional_soft_shadow_filter_set_quality(v as RenderingServer.ShadowQuality))
	_choice(col, "cascades", "Shadow cascades", [["1", DirectionalLight3D.SHADOW_ORTHOGONAL], ["2", DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS],
		["4", DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS]], sun.directional_shadow_mode,
		func(v: int) -> void: sun.directional_shadow_mode = v as DirectionalLight3D.ShadowMode)
	_rule(col)
	_choice(col, "details", "Ground details", [["High", 3], ["Baked", 4], ["Medium", 2], ["Low", 1], ["Off", 0]], w.ground_detail,
		func(v: int) -> void: w.set_ground_detail(v))
	_choice(col, "ssao", "Ambient occlusion", [["Off", -1], ["Very low", RenderingServer.ENV_SSAO_QUALITY_VERY_LOW],
		["Low", RenderingServer.ENV_SSAO_QUALITY_LOW], ["Medium", RenderingServer.ENV_SSAO_QUALITY_MEDIUM], ["High", RenderingServer.ENV_SSAO_QUALITY_HIGH]],
		RenderingServer.ENV_SSAO_QUALITY_MEDIUM if env.ssao_enabled else -1,
		func(v: int) -> void:
			env.ssao_enabled = v >= 0
			if v >= 0:
				RenderingServer.environment_set_ssao_quality(v as RenderingServer.EnvironmentSSAOQuality, v < RenderingServer.ENV_SSAO_QUALITY_HIGH, 0.5,
					1 if v <= RenderingServer.ENV_SSAO_QUALITY_LOW else 2, 50.0, 300.0))
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
	for k in ["trees", "trimmed", "fewer", "tree_shadows", "shadow_reach", "impostors", "sight", "scale", "shadows", "shadow_size", "details", "ssao", "vsync", "fps"]:
		settings.append(_choices[k])
	_runs.push_front("%d · avg %d, 5%% low %d, 1%% low %d fps%s\n    %s" % [_runs.size() + 1, roundi(r["fps"]), roundi(r["low5"]),
		roundi(r["low1"]), "" if r["completed"] else " (stopped early)", ", ".join(settings)])
	_update_runs()


func _update_runs() -> void:
	_runs_label.text = "\n".join(_runs.slice(0, 6)) if _runs else "Runs show here. VSync and the frame rate limit cap the frame rate; with both off, it goes as high as it can."


# ------------------------------------------------------------------ building the rows
func _choice(parent: Control, key: String, text: String, options: Array, current: Variant, apply: Callable) -> void:
	var row := HBoxContainer.new()
	parent.add_child(row)
	var l := _label(row, text, 13, INK)
	l.custom_minimum_size.x = 150
	l.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	var buttons := HFlowContainer.new()  # a long row wraps
	buttons.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(buttons)
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
		b.custom_minimum_size = Vector2(46, 22)
		_style(b)
		buttons.add_child(b)
		_groups[key][o[1]] = b
		if o[1] == current:
			b.button_pressed = true
			_choices[key] = "%s %s" % [text.to_lower(), o[0].to_lower()]
		b.toggled.connect(func(on: bool) -> void:
			if on:
				_choices[key] = "%s %s" % [text.to_lower(), o[0].to_lower()]
				apply.call(o[1]))


## Press one of a row's buttons, as a click would (for --set and the dev panel test). A number matches whichever
## button has the same value, 0 or 0.0.
func choose(key: String, value: Variant) -> void:
	var group: Dictionary = _groups[key]
	if not group.has(value) and (value is int or value is float):
		for k: Variant in group:
			if (k is int or k is float) and is_equal_approx(float(k), float(value)):
				value = k
	(group[value] as Button).button_pressed = true


## Make several choices at once, {setting: value}.
func choose_all(settings: Dictionary) -> void:
	for k: String in settings:
		choose(k, settings[k])


func show_theme(theme: String) -> void:
	_theme_box.select(PathThemes.ORDER.find(theme))
	_choices["theme"] = "paths " + theme.to_lower()


## Mark a choice as made elsewhere (T swaps the trees, F4 the render scale) without applying it again.
func show_choice(key: String, value: Variant) -> void:
	var b: Button = _groups.get(key, {}).get(value)
	if b and not b.button_pressed:
		b.set_pressed_no_signal(true)
		_choices[key] = "%s %s" % [_texts[key].to_lower(), b.text.to_lower()]


## Move a slider and apply its value, as letting go of it would (for --set and the dev panel test).
func slide(key: String, value: float) -> void:
	(_sliders[key] as Callable).call(value)


func has_slider(key: String) -> bool:
	return _sliders.has(key)


## A slider row; fmt is a format string for the value, or a function that turns it into text.
func _slider(parent: Control, key: String, text: String, lo: float, hi: float, step: float, value: float, fmt: Variant, apply: Callable) -> void:
	var row := HBoxContainer.new()
	parent.add_child(row)
	var l := _label(row, text, 13, INK)
	l.custom_minimum_size.x = 150
	var s := HSlider.new()
	s.min_value = lo
	s.max_value = hi
	s.step = step
	s.value = value
	s.focus_mode = Control.FOCUS_NONE
	s.scrollable = false  # the wheel scrolls the panel instead: a slider applies its value only when let go
	s.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	s.custom_minimum_size.y = 22
	row.add_child(s)
	var show := func(x: float) -> String: return (fmt as Callable).call(x) if fmt is Callable else (fmt as String) % x
	var v := _label(row, show.call(value), 12, DIM)
	v.custom_minimum_size.x = 48
	s.value_changed.connect(func(x: float) -> void: v.text = show.call(x))
	s.drag_ended.connect(func(_changed: bool) -> void: apply.call(s.value))
	_sliders[key] = func(x: float) -> void:
		s.value = x
		apply.call(s.value)


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
## 30 fps' 33.3 ms, red above, with lines at 120, 60 and 30 fps.
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
		for line in [[1000.0 / 120.0, "120 fps"], [1000.0 / 60.0, "60 fps"], [1000.0 / 30.0, "30 fps"]]:
			var y: float = h - h * float(line[0]) / PerfPanel.GRAPH_MS
			draw_line(Vector2(0, y), Vector2(w, y), Color(1, 1, 1, 0.45), 1.0)
			draw_rect(Rect2(2, y - 14, 50, 13), Color(0, 0, 0, 0.6))
			draw_string(font, Vector2(5, y - 4), line[1], HORIZONTAL_ALIGNMENT_LEFT, -1, 11, Color(1, 1, 1, 0.85))
		draw_string(font, Vector2(w - 76, 12), "last %d s" % PerfPanel.WINDOW, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, Color(1, 1, 1, 0.6))
