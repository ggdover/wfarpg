extends Node3D
## The play demo: one of its scenes (scripts/scenes.gd, Game.scene), an area of forest in a mood, the first a small
## part of Storskogen. The Scenes button, or Tab, switches between them. It shows the mockups' trees or the tree
## portfolio's (Game.tree_set), and T swaps them where you stand.
##
## For checking it from the command line (see README.md), after the scene path and "--":
##   --trees=old|new  which trees            --pose=x,z,yaw,pitch,distance[,facing]  where the hero and camera are
##   --shot=out.png   take a screenshot and quit (after --wait=frames, default 90)    --nohud  without the HUD
##   --walk=seconds   walk forward that long before the screenshot, to see the grass fold round the hero
##   --fps=seconds    measure the frame rate first and print it                       --selftest  try the controls
##   --scene=id       which scene (scripts/scenes.gd)       --scenetest  walk the scene's steps, bridges and jetties
##   --mood=name      the scene's area in another mood (scripts/mood.gd)
##   --grass=style    the grass over the green ground: GrassClumps, GrassWisps, GrassTufts, GrassShort, LongGrass, before
##   --walktest       walk the trail and print the frame times                       --treelod=1|2  lighter trees
##   --panel          open the performance panel (F2); --panel=advanced with its advanced settings shown
##   --set:option=value  a panel option or slider, e.g. --set:shadow_size=1024 --set:details=2 --set:tree_shadows=far
##                       --set:shadow_cap=40 --set:fps=60 (the frame rate limit) --set:path_wear=0
##                       --set:preset=thick|one (a preset at the panel's top)
##   for measuring what costs what: --hide=NorwaySpruce,ScotsPine (kinds of tree not drawn), --noshadow, --nofade,
##   --flatground, --canopy=0..1, --bump=0..1, --sun:property=value, --env:property=value, --vp:property=value

var world: DemoWorld
var scene: Dictionary  # the scene shown (scripts/scenes.gd)
var hero: Hero
var rig: CameraRig
var _info: Label
var _help: Control
var _fps: Label
var _panel: PerfPanel
var _scenes: ScenePicker
## the shadows reach as far as the camera sees the ground, at most shadow_cap metres; or always shadow_cap if false
var shadow_fit := true
var shadow_cap := 70.0
var _shot := ""
var _wait := 90
var _walk := 0.0
var _measure := 0.0
var _frames := 0
var _time := 0.0
var _cpu := 0.0
var _gpu := 0.0


func _ready() -> void:
	scene = Scenes.find(Game.scene)
	var env := WorldEnvironment.new()
	add_child(env)
	var sun := DirectionalLight3D.new()
	sun.name = "DirectionalLight3D"
	add_child(sun)
	var mood: String = scene["mood"]
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--mood="):  # another mood for the scene's area, for trying them out
			mood = a.substr(7)
	Mood.apply(env, sun, mood, scene.get("reflections", false))
	world = DemoWorld.new()
	add_child(world)
	world.build(scene["area"], Game.tree_set)
	for param: String in scene.get("ground", {}):
		world.set_ground_param(param, scene["ground"][param])
	PathThemes.apply(world, Game.path_theme)
	hero = Hero.new()
	add_child(hero)
	hero.global_position = world.start_position() + Vector3(0, 0.1, 0)
	var f := deg_to_rad(float(world.layout["start"]["facing"]))  # degrees anticlockwise from east, Blender's way
	hero.facing = atan2(-cos(f), sin(f))
	hero.reset_physics_interpolation()
	rig = CameraRig.new()
	add_child(rig)
	rig.hero = hero
	rig.world = world
	hero.camera_rig = rig
	_build_hud()
	_panel.use_preset(scene.get("view", "clear"))  # what happens to the trees in the way, in this scene
	if scene.has("pose"):  # a scene that starts somewhere of its own, or with the camera low
		_pose(scene["pose"])
	_read_args()
	rig.snap()
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--walktest"):
			var walk: Node = load("res://scripts/dev/walktest.gd").new()
			add_child(walk)
			walk.run(self)
		elif a == "--panel" or a == "--panel=advanced":
			_panel.visible = true
			if a == "--panel=advanced":
				_panel.show_advanced(true)
		elif a == "--paneltest":
			var test: Node = load("res://scripts/dev/paneltest.gd").new()
			add_child(test)
			test.run(self)
	if "--selftest" in OS.get_cmdline_user_args():
		var test: Node = load("res://scripts/dev/selftest.gd").new()
		add_child(test)
		test.run(self)
	elif "--scenetest" in OS.get_cmdline_user_args():
		var test: Node = load("res://scripts/dev/scenetest.gd").new()
		add_child(test)
		test.run(self)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("swap_trees"):
		show_tree_set("old" if Game.tree_set == "new" else "new")
	elif event.is_action_pressed("perf_panel"):
		_panel.visible = not _panel.visible
	elif event.is_action_pressed("scene_menu"):
		_scenes.visible = not _scenes.visible
	elif event.is_action_pressed("path_theme"):
		var order := PathThemes.ORDER
		show_path_theme(order[(order.find(Game.path_theme) + 1) % order.size()])
	elif event.is_action_pressed("grass_style"):
		var styles := GrassField.STYLES.keys()
		show_grass(styles[(styles.find(Game.grass) + 1) % styles.size()])
	elif event.is_action_pressed("toggle_help"):
		_help.visible = not _help.visible
	elif event.is_action_pressed("toggle_fps"):
		_fps.visible = not _fps.visible
	elif event.is_action_pressed("render_scale"):
		var vp := get_viewport()
		vp.scaling_3d_mode = Viewport.SCALING_3D_MODE_FSR
		vp.scaling_3d_scale = {1.0: 0.75, 0.75: 0.5}.get(snappedf(vp.scaling_3d_scale, 0.01), 1.0)
		_panel.show_choice("scale", snappedf(vp.scaling_3d_scale, 0.05))
		_update_info()
	elif event.is_action_pressed("screenshot"):
		DirAccess.make_dir_recursive_absolute("user://screenshots")
		var path := "user://screenshots/%s.png" % Time.get_datetime_string_from_system().replace(":", "-")
		get_viewport().get_texture().get_image().save_png(path)
		_info.text += "\nSaved " + ProjectSettings.globalize_path(path)
	elif event.is_action_pressed("menu"):
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		get_tree().change_scene_to_file("res://scenes/start.tscn")


## Paint the paths in one of the colour themes (scripts/path_themes.gd).
func show_path_theme(theme: String) -> void:
	Game.path_theme = theme
	PathThemes.apply(world, theme)
	_update_info()
	_panel.show_theme(theme)


## Show one of the grasses over the green ground (GrassField.STYLES), or the mockups' tufts as before them.
func show_grass(style: String) -> void:
	Game.grass = style
	world.set_grass(style)
	_update_info()
	_panel.show_choice("grass", style)


## Show the old trees or the new ones, where you stand.
func show_tree_set(which: String) -> void:
	Game.tree_set = which
	world.show_trees(which)
	_update_info()
	_panel.show_choice("trees", which)


func _process(delta: float) -> void:
	_fps.text = "%d fps" % Engine.get_frames_per_second()
	_fit_shadows()
	if _shot == "":
		return
	if _walk > 0.0 and _wait <= 1:  # --walk: walking, until the screenshot
		Input.action_press("move_forward")
		_walk -= delta
		return
	_wait -= 1
	if _wait == 0:
		if _measure > 0.0:
			_time = 0.0
			_frames = 0
			RenderingServer.viewport_set_measure_render_time(get_viewport().get_viewport_rid(), true)
		else:
			_take_shot()
	elif _wait < 0:
		_time += delta
		_frames += 1
		var vp := get_viewport().get_viewport_rid()
		_cpu += RenderingServer.viewport_get_measured_render_time_cpu(vp) + RenderingServer.get_frame_setup_time_cpu()
		_gpu += RenderingServer.viewport_get_measured_render_time_gpu(vp)
		if _time >= _measure:
			print("fps over %.1f s: %.1f   render cpu %.1f ms, gpu %.1f ms, draw calls %d, objects %d, primitives %d" % [_time, _frames / _time,
				_cpu / _frames, _gpu / _frames, RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME),
				RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_OBJECTS_IN_FRAME),
				RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME)])
			_take_shot()


## Godot's shadows reach a set distance from the camera. Make that just as far as the camera sees the ground (the
## top edge of the screen, measured along the view), so the shadows round the hero always stay, none are drawn that
## can't be seen, and the shadow map's detail goes where it's needed. Low cameras that see the horizon get shadow_cap.
func _fit_shadows() -> void:
	var sun: DirectionalLight3D = get_node("DirectionalLight3D")
	var want := shadow_cap
	if shadow_fit:
		var cam := rig.camera
		var vp := get_viewport().get_visible_rect().size
		var forward := -cam.global_basis.z
		for x in [0.0, 0.5, 1.0]:  # the top edge's corners and middle
			var ray := cam.project_ray_normal(Vector2(vp.x * x, 0.0))
			var reach := shadow_cap
			if ray.y < -0.02:
				var t := (cam.global_position.y - hero.global_position.y) / -ray.y
				reach = minf(t * ray.dot(forward) + 6.0, shadow_cap)
			want = reach if x == 0.0 else maxf(want, reach)
		want = maxf(want, rig.distance + 12.0)
	if absf(sun.directional_shadow_max_distance - want) > 0.5:
		sun.directional_shadow_max_distance = want


func _take_shot() -> void:
	get_viewport().get_texture().get_image().save_png(_shot)
	print("saved ", _shot)
	get_tree().quit()


func _read_args() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--shot="):
			_shot = a.substr(7)
		elif a.begins_with("--wait="):
			_wait = int(a.substr(7))
		elif a.begins_with("--walk="):
			_walk = float(a.substr(7))
		elif a.begins_with("--fps="):
			_measure = float(a.substr(6))
		elif a == "--nohud":
			$Hud.visible = false
		elif a == "--noshadow":  # the rest are for measuring what costs what
			(get_node("DirectionalLight3D") as DirectionalLight3D).shadow_enabled = false
		elif a.begins_with("--sun:") or a.begins_with("--env:"):  # --sun:property=value, for tuning
			var kv := a.substr(6).split("=")
			var target: Object = get_node("DirectionalLight3D") if a.begins_with("--sun:") else (get_child(0) as WorldEnvironment).environment
			target.set(kv[0], str_to_var(kv[1]))
		elif a.begins_with("--vp:"):
			var kv := a.substr(5).split("=")
			get_viewport().set(kv[0], str_to_var(kv[1]))
		elif a.begins_with("--ground:"):  # --ground:parameter=value, the ground shader's
			var kv := a.substr(9).split("=")
			world.set_ground_param(kv[0], str_to_var(kv[1]))
		elif a.begins_with("--set:"):  # --set:option=value, a performance panel option or slider (see dev/paneltest.gd)
			var kv := a.substr(6).split("=")
			var v: Variant = str_to_var(kv[1])
			if kv[0] == "preset":
				_panel.use_preset(kv[1])
			elif _panel.has_slider(kv[0]):
				_panel.slide(kv[0], float(v))
			else:
				_panel.choose(kv[0], kv[1] if v == null else v)
		elif a.begins_with("--bump="):
			world.set_ground_param("bump_strength", float(a.substr(7)))
		elif a.begins_with("--canopy="):
			world.set_ground_param("canopy_strength", float(a.substr(9)))
		elif a.begins_with("--detail="):
			world.set_ground_detail(int(a.substr(9)))
		elif a == "--nofade":
			RenderingServer.global_shader_parameter_set("hero_fade_on", 0.0)
		elif a == "--flatground":
			world.set_ground_detail(0)
		elif a.begins_with("--pose="):
			_pose(a.substr(7))


## Put the hero and the camera somewhere: "x,z,yaw,pitch,distance[,hero facing in degrees like the start's]".
func _pose(spec: String) -> void:
	var v := spec.split_floats(",")
	hero.global_position = Vector3(v[0], world.height_at(v[0], v[1]) + 0.05, v[1])
	rig.yaw = v[2]
	rig.pitch = v[3]
	rig.distance = v[4]
	if v.size() > 5:
		var f := deg_to_rad(v[5])
		hero.facing = atan2(-cos(f), sin(f))
		hero.rotation.y = hero.facing
	hero.reset_physics_interpolation()


# ------------------------------------------------------------------ HUD
func _build_hud() -> void:
	var layer := CanvasLayer.new()
	layer.name = "Hud"
	add_child(layer)
	var area := SightArea.new()  # the area round the hero that decides when trees go see-through, if shown (F2)
	area.world = world
	area.camera = rig.camera
	layer.add_child(area)
	var font: Font = load("res://assets/fonts/Cinzel.ttf")
	var box := PanelContainer.new()
	box.position = Vector2(16, 14)
	box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var bg := StyleBoxFlat.new()
	bg.bg_color = Color(0.1, 0.09, 0.07, 0.62)
	bg.set_content_margin_all(10)
	bg.border_color = Color(0.72, 0.6, 0.38, 0.7)
	bg.set_border_width_all(1)
	box.add_theme_stylebox_override("panel", bg)
	layer.add_child(box)
	var col := VBoxContainer.new()
	box.add_child(col)
	var title := Label.new()
	title.text = "%s · play demo" % scene["title"]
	title.add_theme_font_override("font", font)
	title.add_theme_font_size_override("font_size", 20)
	title.add_theme_color_override("font_color", Color("#E8D9B0"))
	col.add_child(title)
	var scenes := Button.new()  # the scenes to switch to: _scenes
	scenes.text = "Scenes  (Tab)"
	scenes.focus_mode = Control.FOCUS_NONE
	scenes.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	scenes.add_theme_font_size_override("font_size", 14)
	for state in ["normal", "hover", "pressed"]:
		var sb := StyleBoxFlat.new()
		sb.bg_color = Color("#2A2620") if state == "normal" else Color("#3A3328")
		sb.border_color = Color("#C9A24A") if state != "normal" else Color("#6E5D3E")
		sb.set_border_width_all(1)
		sb.set_content_margin_all(5)
		scenes.add_theme_stylebox_override(state, sb)
	scenes.add_theme_color_override("font_color", Color("#E8D9B0"))
	scenes.pressed.connect(func() -> void: _scenes.visible = not _scenes.visible)
	col.add_child(scenes)
	_info = Label.new()
	_info.add_theme_color_override("font_color", Color("#E6E0D2"))
	_info.add_theme_font_size_override("font_size", 14)
	col.add_child(_info)
	_help = Label.new()
	(_help as Label).text = ("WASD  walk (W walks away from the camera)\n"
		+ "Right mouse button + move  orbit the camera\n"
		+ "Mouse wheel  zoom\n"
		+ "Left mouse button  'attack': face the cursor, walk slower\n"
		+ "T  swap old and new trees    P  path colours    G  grass    F2  performance    F3  frame rate\n"
		+ "F4  render scale    F12  screenshot    Tab  scenes    F1  hide this    Esc  menu")
	_help.add_theme_color_override("font_color", Color("#CFC6B2"))
	_help.add_theme_font_size_override("font_size", 13)
	col.add_child(_help)
	_fps = Label.new()
	_fps.position = Vector2(16, 0)
	_fps.anchor_top = 1.0
	_fps.anchor_bottom = 1.0
	_fps.offset_top = -30
	_fps.add_theme_color_override("font_color", Color("#E6E0D2"))
	_fps.visible = false
	layer.add_child(_fps)
	_scenes = ScenePicker.new()
	_scenes.visible = false
	_scenes.set_anchors_preset(Control.PRESET_CENTER)
	_scenes.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_scenes.grow_vertical = Control.GROW_DIRECTION_BOTH
	layer.add_child(_scenes)
	_scenes.setup(Game.scene, "Scenes  ·  Tab closes")
	_scenes.picked.connect(func(id: String) -> void:
		Game.scene = id
		get_tree().reload_current_scene())
	_panel = PerfPanel.new()
	_panel.visible = false
	_panel.anchor_left = 1.0
	_panel.anchor_right = 1.0
	_panel.offset_left = -526.0
	_panel.offset_right = -16.0
	_panel.offset_top = 14.0
	layer.add_child(_panel)
	_panel.setup(self)
	_update_info()


func _update_info() -> void:
	_info.text = ("New trees: the tree portfolio (Blender)" if Game.tree_set == "new"
		else "Old trees: as in the mockups") + "   ·   T swaps them"
	_info.text += "\nPaths: %s   ·   P changes them" % Game.path_theme
	_info.text += "\nGrass: %s   ·   G changes it" % GrassField.STYLES.get(Game.grass, Game.grass)
	var scale := get_viewport().scaling_3d_scale
	if scale < 0.99:
		_info.text += "\nRendering at %d%% (F4)" % roundi(scale * 100.0)
