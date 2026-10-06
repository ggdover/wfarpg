extends SceneTree
## Dev: playtests for tuning when trees go see-through (DemoWorld, cut_trees "veil"). Walks the hero, step by step, under
## every tree standing alone, along the trail through the forest, and to random spots in it, at several camera angles,
## and at each step writes a row to a CSV: for several sizes of the area round the hero (veil_round), the share of its
## points that some tree's shape is on the line to (the "cards" way of measuring), that some tree hides through the gaps
## between the leaves ("seen"), that two trees or more hide, and that at least 2, 3, 4, 6 or 8 layers of leaves hide;
## and how much of the hero itself nothing hides (its points on a fine grid). Nothing is drawn, so it runs headless;
## tools/veiltune.py then plays the settings over the rows.
## godot --headless --path game --script res://scripts/dev/veiltune.gd -- --out=/path/rows.csv

const STEP := 0.2  # metres between steps: about one measurement (30 a second) at walking speed (5.5 m/s)
const ROUNDS := [0.0, 0.5, 1.0, 1.5]  # the sizes of the area round the hero tried (veil_round, metres)
const ALONE := 8.0  # a tree with no other within this many metres stands alone
const GRID := Vector2i(9, 15)  # the fine grid over the hero, for how much of it shows
const FEATURES := ["cards", "seen", "trees2", "layers2", "layers3", "layers4", "layers6", "layers8"]
const LAYERS_CAP := 12  # layers of leaves counted along a line, at most

var world: DemoWorld
var rig: CameraRig
var out: FileAccess
var inside := PackedVector2Array()  # the walls round the walkable area


func _initialize() -> void:
	change_scene_to_file("res://scenes/demo.tscn")
	_run.call_deferred()


func _run() -> void:
	for i in 10:
		await process_frame
	var demo: Node = current_scene
	world = demo.world
	rig = demo.rig
	rig.set_process(false)
	demo.hero.set_physics_process(false)
	for q: Array in world.layout["boundary"]:
		inside.append(Vector2(q[0], q[1]))
	var path := "user://veiltune.csv"
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			path = a.substr(6)
	out = FileAccess.open(path, FileAccess.WRITE)
	var head := "scenario,walk,step,x,z,yaw,pitch,visible,on_line"
	for r: float in ROUNDS:
		for f: String in FEATURES:
			head += ",%s_%s" % [f, str(r)]
	out.store_line(head)
	var t0 := Time.get_ticks_msec()
	# under each tree standing alone, from 4 m in front of it to 16 m past it, away from the camera, through its trunk
	# and a little beside it
	var walks := 0
	for i in world._tree_xz.size():
		var c := world._tree_xz[i]
		var alone := true
		for j in world._tree_xz.size():
			if j != i and world._tree_xz[j].distance_to(c) < ALONE:
				alone = false
				break
		if not alone or not Geometry2D.is_point_in_polygon(c, inside):
			continue
		for yaw: float in [225.0, 315.0, 45.0, 135.0]:
			for pitch: float in [55.0, 35.0]:
				for beside: float in [0.0, 1.2]:
					var y := deg_to_rad(yaw)
					var ahead := Vector2(-cos(y), sin(y))  # W walks this way: away from the camera
					var across := Vector2(-ahead.y, ahead.x)
					var steps: Array[Vector2] = []
					for k in roundi(20.0 / STEP) + 1:
						var p := c + across * beside + ahead * (-4.0 + k * STEP)
						if _walkable(p):
							steps.append(p)
					_walk("alone:%s" % world._tree_sets[world._current][i]["model"], walks, steps, yaw, pitch)
					walks += 1
	print("veiltune: %d walks under trees alone, %.0f s" % [walks, (Time.get_ticks_msec() - t0) / 1000.0])
	# along the trail, the camera behind the hero, as the trail walk has it
	var trail: Array[Vector2] = []
	var wp := TrailWalk.WAYPOINTS
	for k in wp.size() - 1:
		var a: Vector2 = wp[k]
		var b: Vector2 = wp[k + 1]
		var n := maxi(1, roundi(a.distance_to(b) / STEP))
		for m in n:
			trail.append(a.lerp(b, float(m) / n))
	for pitch: float in [55.0, 30.0, 12.0]:
		_walk("trail", walks, trail, -1.0, pitch)
		walks += 1
	print("veiltune: the trail, %.0f s" % ((Time.get_ticks_msec() - t0) / 1000.0))
	# random spots in the forest, each a view of its own
	var rng := RandomNumberGenerator.new()
	rng.seed = 5
	var spots := 0
	while spots < 240:
		var p := Vector2(rng.randf_range(-74.0, -22.0), rng.randf_range(-28.0, 28.0))
		if not _walkable(p):
			continue
		var yaw := rng.randf_range(0.0, 360.0)
		var pitch: float = [12.0, 30.0, 55.0][spots % 3]
		var one: Array[Vector2] = [p]
		_walk("forest", walks, one, yaw, pitch)
		walks += 1
		spots += 1
	print("veiltune: %d forest spots, %.0f s; rows in %s" % [spots, (Time.get_ticks_msec() - t0) / 1000.0, ProjectSettings.globalize_path(path)])
	out.close()
	quit()


## Inside the walls, and not inside a trunk.
func _walkable(p: Vector2) -> bool:
	if not Geometry2D.is_point_in_polygon(p, inside):
		return false
	for i in world._tree_xz.size():
		if world._tree_xz[i].distance_to(p) < 0.9:
			return false
	return true


## One walk: a row for each of its steps. yaw -1 turns the camera to look the way the walk goes.
func _walk(scenario: String, walk: int, steps: Array[Vector2], yaw: float, pitch: float) -> void:
	for k in steps.size():
		var p := steps[k]
		var yw := yaw
		if yw < 0.0:
			var d := (steps[mini(k + 5, steps.size() - 1)] - steps[maxi(k - 5, 0)]).normalized()
			yw = rad_to_deg(atan2(d.y, -d.x))
		var hero_pos := Vector3(p.x, world.height_at(p.x, p.y), p.y)
		rig.yaw = yw
		rig.pitch = pitch
		rig.distance = 20.0
		rig._pivot = hero_pos + Vector3(0.0, 1.4, 0.0)
		rig._place()
		var cam := rig.camera
		var row := "%s,%d,%d,%.2f,%.2f,%.0f,%.0f" % [scenario, walk, k, p.x, p.y, yw, pitch]
		var seen := _hero_seen(cam.global_position, hero_pos)
		row += ",%.3f,%d" % [seen.x, int(seen.y)]
		for r: float in ROUNDS:
			for share: float in _area_shares(cam.global_position, hero_pos, r):
				row += ",%.3f" % share
		out.store_line(row)


## For the area round the hero as DemoWorld._measure_area lays it out (round: veil_round), the shares of its points,
## one per FEATURES: some tree's shape on the line; some tree hiding the point through the gaps between the leaves; two
## trees or more hiding it; and at least 2, 3, 4, 6 and 8 layers of leaves (or bark) on the line.
func _area_shares(camera_pos: Vector3, hero_pos: Vector3, round: float) -> Array[float]:
	var centre := hero_pos + Vector3(0.0, 0.9, 0.0)
	var view := (centre - camera_pos).normalized()
	var side := view.cross(Vector3.UP)
	side = side.normalized() if side.length() > 0.001 else Vector3.RIGHT
	var up := side.cross(view)
	var steep := absf(view.y)
	var half := Vector2(DemoWorld.HERO_BODY, 0.9 * sqrt(1.0 - steep * steep) + 0.36 * steep) + Vector2(round, round)
	var points := PackedVector3Array()
	for row in DemoWorld.AREA_ROWS:
		for col in DemoWorld.AREA_COLUMNS:
			var a := (2.0 * (col + 0.5) / DemoWorld.AREA_COLUMNS - 1.0) * half.x
			var b := (2.0 * (row + 0.5) / DemoWorld.AREA_ROWS - 1.0) * half.y
			var q := Vector2(absf(a), absf(b)) - (half - Vector2(round, round))
			if q.x > 0.0 and q.y > 0.0 and q.length() > round:
				continue
			points.append(centre + side * a + up * b)
	var near := _near(camera_pos, hero_pos, half.length())
	var trees: Array = world._tree_sets[world._current]
	var counts := PackedInt32Array()
	counts.resize(FEATURES.size())
	for p in points:
		var from := camera_pos + (p - camera_pos).normalized() * DemoWorld.NEAR_GONE
		var on := 0
		var hiding := 0
		var layers := 0
		for i: int in near:
			var tree: Dictionary = trees[i]
			var c := world._tree_xz[i]
			var bound: Vector3 = tree["bound"]
			var y := world._tree_y[i]
			if not DemoWorld._through(p, from, c.x, c.y, bound.x, y + bound.y, y + bound.z):
				continue
			var inv: Transform3D = tree["inv"]
			var shape := world._coverer(tree)
			var hit := shape.intersect_segment(inv * from, inv * p)
			if hit.is_empty():
				continue
			on += 1
			var n := _layers(world._cover_model(tree), shape, hit, inv * from, inv * p, LAYERS_CAP - layers)
			if n > 0:
				hiding += 1
				layers += n
		var flags := [on >= 1, hiding >= 1, hiding >= 2, layers >= 2, layers >= 3, layers >= 4, layers >= 6, layers >= 8]
		for f in flags.size():
			if flags[f]:
				counts[f] += 1
	var out: Array[float] = []
	for f in counts.size():
		out.append(float(counts[f]) / maxf(points.size(), 1.0))
	return out


## The trees near the lines from the camera to the hero and the area reach round it.
func _near(camera_pos: Vector3, hero_pos: Vector3, reach: float) -> Array:
	var near := []
	var cam2 := Vector2(camera_pos.x, camera_pos.z)
	var hero2 := Vector2(hero_pos.x, hero_pos.z)
	var trees: Array = world._tree_sets[world._current]
	for i in world._tree_xz.size():
		var c := world._tree_xz[i]
		if Geometry2D.get_closest_point_to_segment(c, hero2, cam2).distance_to(c) <= (trees[i]["bound"] as Vector3).x + reach + 0.5:
			near.append(i)
	return near


## How many layers of the tree hide b from a (both in its own space; hit, where the line first meets its shape), at most
## cap: a leaf card counts as one where its picture has a leaf, none in the gaps between the leaves; bark as two, and
## nothing of the tree behind it counts.
func _layers(model: String, shape: TriangleMesh, hit: Dictionary, a: Vector3, b: Vector3, cap: int) -> int:
	var seer := world._seer(model, shape)
	var uvs: PackedVector2Array = seer[0]
	var cards: PackedInt32Array = seer[1]
	var corners: PackedVector3Array = seer[2]
	var step := (b - a).normalized() * 0.002
	var n := 0
	for k in 64:
		var f: int = hit["face_index"]
		var card := cards[f]
		if card < 0:
			return n + 2  # bark: nothing of the tree behind it shows
		var q: Vector3 = hit["position"]
		var w := DemoWorld._barycentric(q, corners[f * 3], corners[f * 3 + 1], corners[f * 3 + 2])
		var uv := uvs[f * 3] * w.x + uvs[f * 3 + 1] * w.y + uvs[f * 3 + 2] * w.z
		var x := clampi(int(uv.x * DemoWorld.CARD_SIZE), 0, DemoWorld.CARD_SIZE - 1)
		var y := clampi(int(uv.y * DemoWorld.CARD_SIZE), 0, DemoWorld.CARD_SIZE - 1)
		if (world._card_leaves[card] as PackedByteArray)[y * DemoWorld.CARD_SIZE + x]:
			n += 1
			if n >= cap:
				return n
		hit = shape.intersect_segment(q + step, b)
		if hit.is_empty():
			return n
	return n


## How much of the hero nothing hides, through the gaps between the leaves: the share of a fine grid of points over it as
## the camera sees it; and how many trees are on the line to its middle.
func _hero_seen(camera_pos: Vector3, hero_pos: Vector3) -> Vector2:
	var centre := hero_pos + Vector3(0.0, 0.9, 0.0)
	var view := (centre - camera_pos).normalized()
	var side := view.cross(Vector3.UP)
	side = side.normalized() if side.length() > 0.001 else Vector3.RIGHT
	var up := side.cross(view)
	var steep := absf(view.y)
	var half := Vector2(DemoWorld.HERO_BODY, 0.9 * sqrt(1.0 - steep * steep) + 0.36 * steep)
	var near := []
	var cam2 := Vector2(camera_pos.x, camera_pos.z)
	var hero2 := Vector2(hero_pos.x, hero_pos.z)
	var trees: Array = world._tree_sets[world._current]
	for i in world._tree_xz.size():
		var c := world._tree_xz[i]
		if Geometry2D.get_closest_point_to_segment(c, hero2, cam2).distance_to(c) <= (trees[i]["bound"] as Vector3).x + 1.5:
			near.append(i)
	var shown := 0
	var on_line := 0
	for row in GRID.y:
		for col in GRID.x:
			var p := centre + side * ((2.0 * (col + 0.5) / GRID.x - 1.0) * half.x) + up * ((2.0 * (row + 0.5) / GRID.y - 1.0) * half.y)
			var middle := row == GRID.y / 2 and col == GRID.x / 2
			var from := camera_pos + (p - camera_pos).normalized() * DemoWorld.NEAR_GONE
			var hidden := false
			for i: int in near:
				var tree: Dictionary = trees[i]
				var c := world._tree_xz[i]
				var bound: Vector3 = tree["bound"]
				var y := world._tree_y[i]
				if not DemoWorld._through(p, from, c.x, c.y, bound.x, y + bound.y, y + bound.z):
					continue
				var inv: Transform3D = tree["inv"]
				var shape := world._coverer(tree)
				var hit := shape.intersect_segment(inv * from, inv * p)
				if hit.is_empty():
					continue
				if middle:
					on_line += 1
				if not hidden and world._blocks(world._cover_model(tree), shape, hit, inv * from, inv * p):
					hidden = true
					if not middle:
						break
			if not hidden:
				shown += 1
	return Vector2(float(shown) / (GRID.x * GRID.y), on_line)
