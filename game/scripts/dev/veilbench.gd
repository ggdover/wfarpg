extends SceneTree
## Dev: what the see-through trees cost. At random spots in the forest with the camera low, how long the graphics card
## takes per frame with the trees as the game draws them, then, at the slowest spots, with each way of drawing the
## see-through trees, and with them hidden, which is what they'd cost if they were free. Then quits.
## godot --path game --script res://scripts/dev/veilbench.gd [-- --spots=40] [--keep=3] [--poses=x,z,yaw,pitch,dist;...]

var demo: Node
var world: DemoWorld
var hero: Hero
var rig: CameraRig


func _initialize() -> void:
	change_scene_to_file("res://scenes/demo.tscn")
	_run.call_deferred()


func _frames(n: int) -> void:
	for i in n:
		await process_frame


## The graphics card's time per frame (ms), over n frames.
func _gpu(n := 40) -> float:
	var vp := root.get_viewport_rid()
	var total := 0.0
	for i in n:
		await process_frame
		total += RenderingServer.viewport_get_measured_render_time_gpu(vp)
	return total / n


func _pose(v: PackedFloat64Array) -> void:
	hero.global_position = Vector3(v[0], world.height_at(v[0], v[1]) + 0.02, v[1])
	hero.reset_physics_interpolation()
	rig.yaw = v[2]
	rig.pitch = v[3]
	rig.distance = v[4]
	rig._pivot = hero.global_position + Vector3(0, 1.4, 0)
	world._unskip()
	rig._place()
	await _frames(25)  # the trees in the way settle


## The see-through trees hidden, or shown again.
func _hide_veiled(hide: bool) -> void:
	for i: int in world._veiled:
		for rid: RID in world._tree_sets[world._current][i]["draw"]:
			RenderingServer.instance_set_visible(rid, not hide)


func _run() -> void:
	await _frames(30)
	demo = current_scene
	world = demo.world
	hero = demo.hero
	rig = demo.rig
	demo.get_node("Hud").visible = false
	hero.set_physics_process(false)
	RenderingServer.viewport_set_measure_render_time(root.get_viewport_rid(), true)
	var spots := 40
	var keep := 3
	var poses: Array[PackedFloat64Array] = []
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--spots="):
			spots = int(a.substr(8))
		elif a.begins_with("--keep="):
			keep = int(a.substr(7))
		elif a.begins_with("--poses="):
			for p in a.substr(8).split(";"):
				poses.append(p.split_floats(","))
	await _frames(60)  # the pictures of the trees are baked
	if poses.is_empty():
		var rng := RandomNumberGenerator.new()
		rng.seed = 11
		var found := []
		while found.size() < spots:
			var p := Vector2(rng.randf_range(-74.0, -22.0), rng.randf_range(-28.0, 28.0))
			var free := true
			for i in world._tree_xz.size():
				if world._tree_xz[i].distance_to(p) < 0.9:
					free = false
					break
			if not free:
				continue
			var v := PackedFloat64Array([p.x, p.y, rng.randf_range(0.0, 360.0), rng.randf_range(8.0, 16.0), rng.randf_range(10.0, 22.0)])
			await _pose(v)
			var ms := await _gpu(20)
			found.append([ms, v, world._veiled.size()])
			print("spot %2d  %6.1f, %6.1f  yaw %3d pitch %2d dist %2d: %5.1f ms, %d see-through" % [found.size(), v[0], v[1],
				roundi(v[2]), roundi(v[3]), roundi(v[4]), ms, world._veiled.size()])
		found.sort_custom(func(a: Array, b: Array) -> bool: return a[0] > b[0])
		for k in mini(keep, found.size()):
			poses.append(found[k][1])
	print("veilbench: modes at %d spots" % poses.size())
	for v in poses:
		await _pose(v)
		var line := "%.1f,%.1f,%.0f,%.0f,%.0f  %d see-through:" % [v[0], v[1], v[2], v[3], v[4], world._veiled.size()]
		for mode: Array in [["all cards", "veil_lighter", false], ["thinned", "veil_lighter", true]]:
			world.set_trees(mode[1], mode[2])
			await _frames(25)
			line += "  %s %.1f" % [mode[0], await _gpu()]
		_hide_veiled(true)
		line += "  hidden %.1f" % await _gpu()
		_hide_veiled(false)
		print(line)
	quit()
