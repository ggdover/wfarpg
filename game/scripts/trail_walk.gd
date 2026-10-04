class_name TrailWalk
extends Node
## Walks the hero along the trail from the start, out of the thicket and onto the meadow, steering the camera so W
## follows the trail, the same way every time, and measures every frame. For comparing settings fairly: the
## performance panel's "Walk the trail" button and the --walktest option use it.

signal finished(result: Dictionary)

# the trail's bends, in Godot's X and Z (tools/demo_area.py, PATHS["trail"], with Z = -Y)
const WAYPOINTS := [Vector2(-60, -2), Vector2(-48, -1), Vector2(-37, 6), Vector2(-25, 5), Vector2(-14, -3), Vector2(-2, -5),
	Vector2(10, -1), Vector2(23, 5), Vector2(36, 3), Vector2(48, -5)]
const WARM_UP := 30  # frames to let the view settle after moving the hero to the start
const MAX_SECONDS := 40.0

var demo: Node
var times := PackedFloat32Array()
var _next := 0
var _warm := 0
var _last := 0
var _elapsed := 0.0


func start(d: Node) -> void:
	demo = d
	var hero: Hero = demo.hero
	var rig: CameraRig = demo.rig
	hero.global_position = demo.world.start_position() + Vector3(0, 0.1, 0)
	hero.velocity = Vector3.ZERO
	hero.reset_physics_interpolation()
	rig.pitch = 55.0
	rig.distance = 20.0
	rig.yaw = _yaw_towards(WAYPOINTS[0])
	rig.snap()
	_warm = WARM_UP
	times.clear()
	_next = 0
	_elapsed = 0.0


func stop() -> void:
	Input.action_release("move_forward")
	set_process(false)
	queue_free()


func _process(_delta: float) -> void:
	var now := Time.get_ticks_usec()
	if _warm > 0:
		_warm -= 1
		_last = now
		if _warm == 0:
			Input.action_press("move_forward")
		return
	var ms := (now - _last) / 1000.0
	_last = now
	times.append(ms)
	_elapsed += ms / 1000.0
	var rig: CameraRig = demo.rig
	var hero: Hero = demo.hero
	var p := Vector2(hero.global_position.x, hero.global_position.z)
	if p.distance_to(WAYPOINTS[_next]) < 2.0:
		_next += 1
	if _next >= WAYPOINTS.size() or _elapsed > MAX_SECONDS:
		Input.action_release("move_forward")
		finished.emit(summary(times, _next >= WAYPOINTS.size()))
		set_process(false)
		queue_free()
		return
	var turn := angle_difference(deg_to_rad(rig.yaw), deg_to_rad(_yaw_towards(WAYPOINTS[_next])))
	rig.yaw = fposmod(rig.yaw + rad_to_deg(turn) * minf(1.0, ms / 150.0), 360.0)


func _yaw_towards(target: Vector2) -> float:
	var p := Vector2(demo.hero.global_position.x, demo.hero.global_position.z)
	var dir := (target - p).normalized()
	return rad_to_deg(atan2(dir.y, -dir.x))  # the yaw that makes W walk towards the target


## Frame-time numbers: mean, median, percentiles, the frame rate on average and in the slowest 1% and 5% of frames.
static func summary(ms: PackedFloat32Array, completed := true) -> Dictionary:
	var sorted := ms.duplicate()
	sorted.sort()
	var n := sorted.size()
	if n == 0:
		return {}
	var total := 0.0
	for x in sorted:
		total += x
	return {"frames": n, "seconds": total / 1000.0, "completed": completed, "mean_ms": total / n,
		"median_ms": sorted[n / 2], "p95_ms": sorted[mini(n - 1, int(n * 0.95))], "worst_ms": sorted[n - 1],
		"fps": 1000.0 * n / total, "low1": low_fps(sorted, 0.01), "low5": low_fps(sorted, 0.05)}


## The frame rate over the slowest share of frames (sorted frame times, fastest first): "1% low" for share 0.01.
static func low_fps(sorted: PackedFloat32Array, share: float) -> float:
	var n := sorted.size()
	var k := maxi(1, ceili(n * share))
	var total := 0.0
	for i in range(n - k, n):
		total += sorted[i]
	return 1000.0 * k / total
