extends Node
## Dev: walks the hero along the trail from the start towards the meadow, steering the camera so W follows the
## trail, and records every frame's time, to tell a low frame rate from stutters. Prints the numbers and quits.
## godot --path game res://scenes/demo.tscn -- --walktest=20 [--trees=old|new]

# the trail's bends, in Godot's X and Z (tools/demo_area.py, PATHS["trail"], with Z = -Y)
const WAYPOINTS := [Vector2(-60, -2), Vector2(-48, -1), Vector2(-37, 6), Vector2(-25, 5), Vector2(-14, -3), Vector2(-2, -5),
	Vector2(10, -1), Vector2(23, 5), Vector2(36, 3), Vector2(48, -5)]

var demo: Node
var times := PackedFloat32Array()


func run(d: Node, seconds: float) -> void:
	demo = d
	var hero: Hero = demo.hero
	var rig: CameraRig = demo.rig
	print("walktest starts with the ", Game.tree_set, " trees")
	for i in 60:  # let shaders compile and the first frames settle
		await demo.get_tree().process_frame
	var next := 0
	var t := 0.0
	var last := Time.get_ticks_usec()
	Input.action_press("move_forward")
	while t < seconds and next < WAYPOINTS.size():
		await demo.get_tree().process_frame
		var now := Time.get_ticks_usec()
		var dt := (now - last) / 1000.0
		last = now
		times.append(dt)
		t += dt / 1000.0
		var p := Vector2(hero.global_position.x, hero.global_position.z)
		var target: Vector2 = WAYPOINTS[next]
		if p.distance_to(target) < 2.0:
			next += 1
			continue
		var dir := (target - p).normalized()
		var want := rad_to_deg(atan2(dir.y, -dir.x))  # the yaw that makes W walk towards the target
		rig.yaw = fposmod(rig.yaw + angle_difference(deg_to_rad(rig.yaw), deg_to_rad(want)) * 180.0 / PI * minf(1.0, dt / 150.0), 360.0)
	Input.action_release("move_forward")
	var sorted := times.duplicate()
	sorted.sort()
	var n := sorted.size()
	var total := 0.0
	for x in times:
		total += x
	var slow := 0
	for x in times:
		if x > 33.4:
			slow += 1
	print("walktest %s: %d frames in %.1f s, reached waypoint %d/%d, at %s" % [Game.tree_set, n, total / 1000.0, next, WAYPOINTS.size(), hero.global_position.snapped(Vector3.ONE * 0.1)])
	print("  frame ms: mean %.1f  median %.1f  95%% %.1f  99%% %.1f  worst %.1f   (%.0f fps on average)" % [total / n,
		sorted[n / 2], sorted[int(n * 0.95)], sorted[int(n * 0.99)], sorted[n - 1], 1000.0 * n / total])
	print("  frames slower than 33 ms (under 30 fps): %d" % slow)
	demo.get_tree().quit()
