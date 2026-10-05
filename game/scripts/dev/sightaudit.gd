extends SceneTree
## Dev: checks the hiding of trees in the way of the hero (DemoWorld.update_sight, with cut_trees "line" and no
## stumps) by their pixels, at random spots in the forest and camera angles from low to high, then quits. At each spot, with the camera held still and no shadows or ambient
## occlusion (so removing a tree changes only its own pixels):
##   covered  how much of the hero the trees still cover as the game draws it; should be none
##   hidden   each tree the game hides, with how much of the hero it would cover on its own; for one that would
##            cover none, how far its nearest pixel is from the hero's, in metres at the hero (hidden that early)
## With --mode=veil (or cone, front, xray...), that way of cutting trees instead, with its own fades and the trees left
## standing; for those that cut no tree whole, only how much of the hero the trees cover. With "veil", the trees in
## front of the hero only go see-through, so they may cover it a little.
## godot --path game --script res://scripts/dev/sightaudit.gd [-- --trimmed] [--spots=24] [--mode=veil]

var demo: Node
var world: DemoWorld
var hero: Hero


func _initialize() -> void:
	change_scene_to_file("res://scenes/demo.tscn")
	_run.call_deferred()


func _frames(n: int) -> void:
	for i in n:
		await process_frame


func _picture() -> Image:
	await _frames(5)
	return root.get_texture().get_image()


func _show(i: int, on: bool) -> void:
	for rid: RID in world._tree_sets[world._current][i]["draw"]:
		RenderingServer.instance_set_visible(rid, on)


static func _differ(a: Color, b: Color, by: float) -> bool:
	return maxf(absf(a.r - b.r), maxf(absf(a.g - b.g), absf(a.b - b.b))) > by


## The hero's pixels: where the picture with it and without trees differs from the one without either.
static func _hero_pixels(clear: Image, nohero: Image, box: Rect2i) -> Array[Vector2i]:
	var out: Array[Vector2i] = []
	for y in range(box.position.y, box.end.y):
		for x in range(box.position.x, box.end.x):
			if _differ(clear.get_pixel(x, y), nohero.get_pixel(x, y), 0.04):
				out.append(Vector2i(x, y))
	return out


## How much of the hero (%) something covers in pic: its pixels that differ from the clear picture.
static func _covered(pic: Image, clear: Image, hero_px: Array[Vector2i]) -> float:
	var n := 0
	for p in hero_px:
		if _differ(pic.get_pixel(p.x, p.y), clear.get_pixel(p.x, p.y), 0.08):
			n += 1
	return 100.0 * n / maxf(hero_px.size(), 1.0)


## How close a tree drawn on its own (alone) comes to the hero on screen, in metres at the hero (from its height on
## screen); -1 when none of it is drawn within 300 pixels of the hero, as when it's faded right at the camera.
static func _gap(alone: Image, clear: Image, hero_px: Array[Vector2i], box: Rect2i) -> float:
	var around := box.grow(300).intersection(Rect2i(Vector2i.ZERO, alone.get_size()))
	var best := INF
	for y in range(around.position.y, around.end.y, 2):
		for x in range(around.position.x, around.end.x, 2):
			if not _differ(alone.get_pixel(x, y), clear.get_pixel(x, y), 0.08):
				continue
			for h in hero_px:
				best = minf(best, Vector2(h - Vector2i(x, y)).length())
	return best / (box.size.y / 1.8) if best < INF else -1.0


func _run() -> void:
	await _frames(20)
	demo = current_scene
	world = demo.world
	hero = demo.hero
	var rig: CameraRig = demo.rig
	var spots := 24
	var mode := "line"
	world.set_trees("leave", "nothing")
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--mode="):
			mode = a.substr(7)
	world.set_trees("cut_trees", mode)
	for a in OS.get_cmdline_user_args():
		if a == "--trimmed":
			world.set_trees("trimmed", true)
		elif a.begins_with("--spots="):
			spots = int(a.substr(8))
	demo.get_node("Hud").visible = false
	(demo.get_node("DirectionalLight3D") as DirectionalLight3D).shadow_enabled = false
	(demo.get_child(0) as WorldEnvironment).environment.ssao_enabled = false
	rig.set_process(false)
	hero.set_physics_process(false)
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	var trees: Array = world._tree_sets[world._current]
	var n := 0
	var worst := 0.0
	var hidden_n := 0
	var early: Array[float] = []
	var unseen := 0
	while n < spots:
		var p := Vector2(rng.randf_range(-74.0, -22.0), rng.randf_range(-28.0, 28.0))  # in the forest, not in a trunk
		var free := true
		for i in world._tree_xz.size():
			if world._tree_xz[i].distance_to(p) < 0.9:
				free = false
				break
		if not free:
			continue
		n += 1
		hero.global_position = Vector3(p.x, world.height_at(p.x, p.y) + 0.02, p.y)
		hero.reset_physics_interpolation()
		rig.yaw = rng.randf_range(0.0, 360.0)
		rig.pitch = [15.0, 30.0, 55.0, 80.0][n % 4]
		rig.distance = [12.0, 20.0, 30.0][n % 3]
		rig._pivot = hero.global_position + Vector3(0, 1.4, 0)
		rig._place()
		var cam := rig.camera
		world._unskip()
		world.update_sight(cam, hero.global_position, 10.0)
		var r := Rect2(cam.unproject_position(hero.global_position), Vector2.ZERO)
		for c in 8:
			r = r.expand(cam.unproject_position(hero.global_position
				+ Vector3(0.3 if c & 1 else -0.3, 1.8 if c & 2 else 0.0, 0.19 if c & 4 else -0.19)))
		var game := await _picture()
		var box := Rect2i(r.grow(2.0)).intersection(Rect2i(Vector2i.ZERO, game.get_size()))
		var hidden: Array[int] = []
		for i: int in world._sight:
			if world._sight[i] >= 1.0:
				hidden.append(i)
		# the hero with no trees round it, and without the hero too
		var nearby: Array[int] = []
		for i in trees.size():
			if world._tree_xz[i].distance_to(p) < 45.0:
				nearby.append(i)
		world.set_trees("cut_trees", "off")
		for i in nearby:
			_show(i, false)
		var clear := await _picture()
		hero.visible = false
		var nohero := await _picture()
		hero.visible = true
		var hero_px := _hero_pixels(clear, nohero, box)
		var covered := _covered(game, clear, hero_px)
		var line := ""
		for i in hidden:
			_show(i, true)
			var alone := await _picture()
			_show(i, false)
			var c := _covered(alone, clear, hero_px)
			hidden_n += 1
			if c > 0.0:
				line += " %.0f%%" % c
				continue
			var gap := _gap(alone, clear, hero_px, box)
			if gap < 0.0:
				unseen += 1
				line += " -"
			else:
				early.append(gap)
				line += " (%.2f m off)" % gap
		for i in nearby:
			_show(i, true)
		world.set_trees("cut_trees", mode)
		worst = maxf(worst, covered)
		print("spot %2d  pitch %2d, %2d m: trees cover %4.1f%% of the hero; hidden %2d:%s" % [n, roundi(rig.pitch),
			roundi(rig.distance), covered, hidden.size(), line])
	early.sort()
	print("sightaudit: trees cover at most %.1f%% of the hero; of %d trees hidden, %d not drawn near the hero anyway (-),"
		% [worst, hidden_n, unseen] + " %d hidden while %s m off it" % [early.size(), ", ".join(early.map(func(g: float) -> String: return "%.2f" % g))])
	quit()
