extends SceneTree
## Dev: one of F2's settings at two values or more, back to back in one run, so whatever else the machine is doing
## weighs on each alike: it flips between them every second or so and prints, for each, the graphics card's time per
## frame (the mean and median of its spells) and the frame rate. Then quits.
## godot --path game --script res://scripts/dev/abbench.gd -- --ab=bark=true,false [--spells=24] [--scene=open_forest]
##   (a slider too: --ab=grass_reach=45,25)
##   [--pose=x,z,yaw,pitch,distance] [--set:option=value ...] (the other options as for the demo, scripts/demo.gd)

var demo: Node


func _initialize() -> void:
	change_scene_to_file("res://scenes/demo.tscn")
	_run.call_deferred()


func _frames(n: int) -> void:
	for i in n:
		await process_frame


func _run() -> void:
	await _frames(30)
	demo = current_scene
	demo.get_node("Hud").visible = false
	demo.hero.set_physics_process(false)
	var key := ""
	var values: Array = []
	var spells := 24
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--ab="):
			var kv := a.substr(5).split("=")
			key = kv[0]
			for s in kv[1].split(","):
				var v: Variant = str_to_var(s)
				values.append(s if v == null else v)
		elif a.begins_with("--spells="):
			spells = int(a.substr(9))
	if key == "" or values.size() < 2:
		print("abbench: --ab=option=value,value needed")
		quit(1)
		return
	var panel: Node = demo._panel  # untyped: a --script loads before the autoloads, which the panel uses
	var vp := root.get_viewport_rid()
	RenderingServer.viewport_set_measure_render_time(vp, true)
	await _frames(90)  # the pictures of the trees are baked, the trees in the way settle
	var gpu := {}
	var fps := {}
	for v: Variant in values:
		gpu[v] = []
		fps[v] = []
	for i in spells * values.size():
		var v: Variant = values[i % values.size()]
		if panel._sliders.has(key):
			panel.slide(key, v)
		else:
			panel.choose(key, v)
		await _frames(15)
		var t0 := Time.get_ticks_usec()
		var total := 0.0
		var n := 0
		while Time.get_ticks_usec() - t0 < 1000000:
			await process_frame
			total += RenderingServer.viewport_get_measured_render_time_gpu(vp)
			n += 1
		gpu[v].append(total / n)
		fps[v].append(n * 1000000.0 / (Time.get_ticks_usec() - t0))
	for v: Variant in values:
		var g: Array = gpu[v].duplicate()
		g.sort()
		var f: Array = fps[v]
		print("%s=%s: gpu %.2f ms (median %.2f, %.2f to %.2f), %.1f fps" % [key, v, _mean(g), g[g.size() / 2], g[0], g[-1], _mean(f)])
	quit()


func _mean(a: Array) -> float:
	var s := 0.0
	for x: float in a:
		s += x
	return s / a.size()
