extends Node
## Dev: walks the hero through the scene's paths that matter (Game.scene): up the river's wooden steps and over its
## footbridge, out on the lake's jetty and into its shallows, along the bog's boardwalk, down into the autumn hollow;
## checks that it gets there and stays on what it walks on (and, in the bog, that its grass grows there), then quits.
## godot --path game res://scenes/demo.tscn -- --scene=river_cliffs --scenetest

var demo: Node
var results := []


func run(d: Node) -> void:
	demo = d
	await _frames(30)
	var hero: Hero = demo.hero
	var w: DemoWorld = demo.world
	_check("the hero stands on the ground at the start",
		absf(hero.global_position.y - w.height_at(hero.global_position.x, hero.global_position.z)) < 0.3,
		"y %.2f, ground %.2f" % [hero.global_position.y, w.height_at(hero.global_position.x, hero.global_position.z)])
	match Game.scene:
		"river_cliffs", "misty_ravine":
			await _river_cliffs()
		"forest_lake":
			await _forest_lake()
		"bog":
			await _bog()
		"autumn_hollow":
			await _autumn_hollow()
	var failed := results.filter(func(r: String) -> bool: return r.begins_with("FAIL"))
	for r: String in results:
		print(r)
	print("scenetest %s: %d passed, %d failed" % [Game.scene, results.size() - failed.size(), failed.size()])
	demo.get_tree().quit(1 if failed.size() else 0)


func _river_cliffs() -> void:
	var w: DemoWorld = demo.world
	# the wooden steps (tools/areas/river_cliffs.py, STAIRS: from (-6, -1.9) to (-6, 5.9), Blender's X and Y)
	_place(Vector2(-6.0, 5.0))
	var y0: float = demo.hero.global_position.y
	await _walk(Vector2(0, -1), 4.0)
	var climbed: float = demo.hero.global_position.y - y0
	_check("the wooden steps climb the cliffs", climbed > 3.0 and demo.hero.global_position.z < -6.0,
		"climbed %.2f m, to z %.1f" % [climbed, demo.hero.global_position.z])
	# the cliffs elsewhere are a wall
	_place(Vector2(20.0, 10.0))
	y0 = demo.hero.global_position.y
	await _walk(Vector2(0, -1), 3.0)
	_check("the cliffs are a wall elsewhere", demo.hero.global_position.y - y0 < 1.5,
		"rose %.2f m" % (demo.hero.global_position.y - y0))
	# the footbridge (BRIDGE: from (24, -20.6) to (24, -31.4)): over the river, the hero is on its deck, well above
	# the river's bed
	_place(Vector2(24.0, 18.0))
	var lowest := [100.0]
	await _walk(Vector2(0, 1), 3.5, func() -> void:
		var p: Vector3 = demo.hero.global_position
		if absf(p.z - 25.9) < 1.5:
			lowest[0] = minf(lowest[0], p.y - w.height_at(p.x, p.z)))
	_check("the footbridge carries the hero over the river", lowest[0] > 0.7 and demo.hero.global_position.z > 32.0,
		"lowest %.2f m over the bed, to z %.1f" % [lowest[0], demo.hero.global_position.z])


func _forest_lake() -> void:
	var w: DemoWorld = demo.world
	# the jetty (JETTY: from (0, -9.8) to (0, 0.5)): out to its end, on its deck, and no further
	_place(Vector2(0.0, 13.0))
	var off := [0]
	await _walk(Vector2(0, -1), 3.5, func() -> void:
		var p: Vector3 = demo.hero.global_position
		if p.z < 8.0 and p.y < 0.3:
			off[0] += 1)
	var p: Vector3 = demo.hero.global_position
	_check("the jetty: the hero walks out to its end, on its deck", off[0] == 0 and p.z < 1.5 and p.z > -1.0 and p.y > 0.3,
		"at z %.2f, y %.2f, %d frames off it" % [p.z, p.y, off[0]])
	# the shallows: the hero wades in from the shore, and the wall round the deep water stops it
	_place(Vector2(-12.0, 11.0))
	await _walk(Vector2(0, -1), 4.0)
	p = demo.hero.global_position
	_check("the hero wades into the lake and stops in the shallows", p.z < 6.0 and p.y > -0.75,
		"at z %.2f, %.2f m under the surface" % [p.z, -p.y])


func _bog() -> void:
	var w: DemoWorld = demo.world
	# along the boardwalk (WALK in tools/areas/bog.py), from one end to the other
	var pts := _catmull([Vector2(-50, 2), Vector2(-40, 3), Vector2(-30, 1), Vector2(-20, 4), Vector2(-10, 2),
		Vector2(0, -1), Vector2(10, 2), Vector2(20, 0), Vector2(30, 3), Vector2(40, 1), Vector2(50, 0)], 3)
	_place(pts[0] + Vector2(-2.0, 0.0))
	var on := [0, 0]
	await _walk_along(pts, func() -> void:
		var q: Vector3 = demo.hero.global_position
		on[1] += 1
		if q.y - w.height_at(q.x, q.z) > 0.06 or q.y > -0.02:
			on[0] += 1)
	var q: Vector3 = demo.hero.global_position
	_check("the boardwalk carries the hero across the bog", q.x > 45.0 and on[0] > on[1] * 0.9,
		"to x %.1f, on it %d of %d frames" % [q.x, on[0], on[1]])
	# the bog's grass: a field of its own, in the chunks the bog reaches, in place of the faceted tussocks and sedge,
	# folding round the hero's trail as the green grass does; As before brings those back
	var g: GrassField = w.bog_grass
	var hidden := w._old_sedge.all(func(m: MultiMeshInstance3D) -> bool: return not m.visible)
	var head := Vector2(g._trail[0].x, g._trail[0].y) if g and not g._trail.is_empty() else Vector2.INF
	_check("the bog's grass grows on the bog, in place of its faceted tussocks and sedge, and follows the hero",
		g != null and g.shown and g.style == GrassField.BOG and g._chunks.size() > 0 and g._chunks.size() < w.grass._chunks.size()
		and w._old_sedge.size() > 0 and hidden and head.distance_to(Vector2(q.x, q.z)) < 0.1,
		"%d chunks (the green grass %d); faceted ones hidden: %s; its trail %.2f m from the hero" % [g._chunks.size() if g else 0,
		w.grass._chunks.size(), hidden, head.distance_to(Vector2(q.x, q.z))])
	var style0 := Game.grass
	demo.show_grass("before")
	var before := not g.shown and w._old_sedge.all(func(m: MultiMeshInstance3D) -> bool: return m.visible)
	demo.show_grass(style0)
	_check("As before: the bog's faceted tussocks and sedge, and no bog grass", before and g.shown, "before %s" % before)


func _autumn_hollow() -> void:
	_place(Vector2(-44.0, 9.0))  # on the trail, up on the hollow's west rim
	var y0: float = demo.hero.global_position.y
	var lowest := [y0]
	await _walk_along([Vector2(-32, 5), Vector2(-16, 1), Vector2(0, -2), Vector2(16, 2), Vector2(30, 0)], func() -> void:
		lowest[0] = minf(lowest[0], demo.hero.global_position.y))
	_check("the trail goes down into the hollow and up out of it", y0 - lowest[0] > 1.5 and demo.hero.global_position.x > 28.0,
		"down %.2f m, to x %.1f" % [y0 - lowest[0], demo.hero.global_position.x])


## Put the hero at a spot (Godot's X and Z), with the camera straight over it.
func _place(spot: Vector2) -> void:
	var w: DemoWorld = demo.world
	demo.hero.global_position = Vector3(spot.x, w.height_at(spot.x, spot.y) + 0.05, spot.y)
	demo.hero.velocity = Vector3.ZERO
	demo.hero.reset_physics_interpolation()
	demo.rig._pivot = demo.hero.global_position + Vector3(0, 1.4, 0)


## Walk the hero a way (Godot's X and Z) for a while, calling each (if given) every physics frame.
func _walk(dir: Vector2, seconds: float, each := Callable()) -> void:
	demo.rig.yaw = rad_to_deg(atan2(dir.y, -dir.x))  # W walks away from the camera: (-cos yaw, sin yaw)
	await _frames(2)
	Input.action_press("move_forward")
	var t := 0.0
	while t < seconds:
		await demo.get_tree().physics_frame
		t += demo.get_physics_process_delta_time()
		if each.is_valid():
			each.call()
	Input.action_release("move_forward")
	await _frames(2)


## Walk the hero along points, steering for each in turn.
func _walk_along(pts: Array, each := Callable()) -> void:
	Input.action_press("move_forward")
	for target: Vector2 in pts:
		var frames := 0
		while frames < 600:
			var p: Vector3 = demo.hero.global_position
			var to := target - Vector2(p.x, p.z)
			if to.length() < 0.7:
				break
			demo.rig.yaw = rad_to_deg(atan2(to.y, -to.x))
			await demo.get_tree().physics_frame
			frames += 1
			if each.is_valid():
				each.call()
	Input.action_release("move_forward")
	await _frames(2)


## The points of a Catmull-Rom curve through pts, n to a span, as tools/areas use them (act1_world.catmull_open).
static func _catmull(pts: Array, n: int) -> Array:
	var out := []
	for i in pts.size() - 1:
		var p0: Vector2 = pts[maxi(0, i - 1)]
		var p1: Vector2 = pts[i]
		var p2: Vector2 = pts[i + 1]
		var p3: Vector2 = pts[mini(pts.size() - 1, i + 2)]
		for k in n:
			var t := float(k) / n
			out.append(0.5 * ((2.0 * p1) + (p2 - p0) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t * t
				+ (3.0 * p1 - p0 - 3.0 * p2 + p3) * t * t * t))
	out.append(pts[-1])
	return out


func _check(what: String, ok: bool, detail: String) -> void:
	results.append(("PASS  " if ok else "FAIL  ") + what + "  (" + detail + ")")


func _frames(n: int) -> void:
	for i in n:
		await demo.get_tree().process_frame
