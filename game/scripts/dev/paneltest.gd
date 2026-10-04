extends Node
## Dev: presses every switch of the performance panel in turn, at the start, and prints what each costs against the
## defaults (the graphics card's time per frame and the frame rate), then quits.
## godot --path game res://scenes/demo.tscn -- --paneltest [--quick]

const TRIES := [["trimmed", false], ["fewer", true], ["tree_shadows", "full"], ["tree_shadows", "mid"], ["tree_shadows", "far"], ["tree_shadows", "off"],
	["shadow_reach", 0.0], ["shadow_reach", 40.0], ["impostors", 0.0], ["impostors", 60.0], ["details", 3],
	["fade", true], ["sight", false], ["scale", 0.75], ["scale", 0.5], ["aa", Viewport.SCREEN_SPACE_AA_FXAA], ["aa", Viewport.SCREEN_SPACE_AA_DISABLED],
	["shadows", false], ["shadow_fit", false], ["shadow_size", 4096], ["shadow_size", 1024], ["shadow_size", 512],
	["shadow_soft", RenderingServer.SHADOW_QUALITY_HARD], ["shadow_soft", RenderingServer.SHADOW_QUALITY_SOFT_HIGH],
	["cascades", DirectionalLight3D.SHADOW_ORTHOGONAL], ["cascades", DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS],
	["details", 2], ["details", 1], ["details", 0],
	["ssao", RenderingServer.ENV_SSAO_QUALITY_VERY_LOW], ["ssao", RenderingServer.ENV_SSAO_QUALITY_LOW],
	["ssao", RenderingServer.ENV_SSAO_QUALITY_HIGH], ["ssao", -1], ["fog", false],
	["trees", "old"]]
const DEFAULTS := {"trimmed": true, "fewer": false, "tree_shadows": "pictures", "shadow_reach": 60.0, "impostors": 90.0, "fade": false, "sight": true, "scale": 1.0,
	"aa": Viewport.SCREEN_SPACE_AA_SMAA, "shadows": true, "shadow_fit": true, "shadow_size": 2048,
	"shadow_soft": RenderingServer.SHADOW_QUALITY_SOFT_LOW, "cascades": DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS,
	"details": 4, "ssao": RenderingServer.ENV_SSAO_QUALITY_MEDIUM, "fog": true, "trees": "new"}


func run(demo: Node) -> void:
	var panel: PerfPanel = demo._panel
	panel.visible = true
	await _frames(demo, 90)
	var base := await _measure(demo)
	print("paneltest: defaults: %.1f ms on the graphics card, %d fps" % [base.x, roundi(base.y)])
	for t: Array in TRIES:
		if OS.get_cmdline_user_args().has("--quick") and t[0] in ["aa", "fog", "trees", "fade", "scale", "trimmed", "fewer", "tree_shadows", "shadows", "shadow_soft", "cascades"]:
			continue
		panel.choose(t[0], t[1])
		await _frames(demo, 45)
		var m := await _measure(demo)
		print("  %-14s %-10s %5.1f ms (%+5.1f)   %4d fps" % [t[0], (panel._groups[t[0]][t[1]] as Button).text, m.x, m.x - base.x, roundi(m.y)])
		panel.choose(t[0], DEFAULTS[t[0]])
		await _frames(demo, 30)
	base = await _measure(demo)
	print("paneltest: defaults again: %.1f ms" % base.x)
	# the speed-ups' buttons: all as before them, then all on, which should be the defaults again
	panel.choose_all(PerfPanel.BEFORE)
	await _frames(demo, 45)
	var before := await _measure(demo)
	panel.choose_all(PerfPanel.SPED_UP)
	await _frames(demo, 45)
	var after := await _measure(demo)
	var same := PerfPanel.SPED_UP.keys().all(func(k: String) -> bool: return (panel._groups[k][PerfPanel.SPED_UP[k]] as Button).button_pressed)
	print("paneltest: speed-ups all as before: %.1f ms, %d fps; all on: %.1f ms, %d fps%s" % [before.x, roundi(before.y), after.x, roundi(after.y),
		"" if same else " (FAIL: not all on)"])
	# the frame rate limit slider: capped below what the defaults reach, then no limit
	panel.slide("fps", 40.0)
	var limit := Engine.max_fps
	await _frames(demo, 30)
	var capped := await _measure(demo)
	panel.slide("fps", PerfPanel.NO_LIMIT)
	await _frames(demo, 30)
	var free := await _measure(demo)
	print("paneltest: frame rate limit %d: %d fps; then %s: %d fps" % [limit, roundi(capped.y),
		"no limit" if Engine.max_fps == 0 else "limit %d" % Engine.max_fps, roundi(free.y)])
	if OS.get_cmdline_user_args().has("--quick"):
		demo.get_tree().quit()
		return
	# a walk along the trail from the panel's button, listed in its runs
	panel._toggle_walk()
	while panel._walk:
		await demo.get_tree().process_frame
	print("paneltest: run listed: ", panel._runs_label.text.split("\n")[0], " | ", panel._runs_label.text.split("\n")[1].strip_edges())
	demo.get_tree().quit()


func _measure(demo: Node) -> Vector2:
	var vp := demo.get_viewport().get_viewport_rid()
	var gpu := 0.0
	var t0 := Time.get_ticks_usec()
	for i in 90:
		await demo.get_tree().process_frame
		gpu += RenderingServer.viewport_get_measured_render_time_gpu(vp)
	return Vector2(gpu / 90.0, 90.0 / ((Time.get_ticks_usec() - t0) / 1000000.0))


func _frames(demo: Node, n: int) -> void:
	for i in n:
		await demo.get_tree().process_frame
