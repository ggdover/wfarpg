class_name Bushes
extends RefCounted
## The plant portfolio's bushes as the hero meets them, as the user asked (1 November): it walks into one rather than
## being stopped by it (DemoWorld._build_solids leaves them out), just a little slower in it (drag), and the bush shakes
## a little as the hero pushes through, leaning away and springing back, its leaves rustling. Each bush is a spring,
## its top's lean along the ground, pushed away from the hero and dragged along the way it walks while it's in the bush;
## those moving are worked out every frame and handed to their shaders through their multimesh's custom data (bush_sway
## in shaders/common.gdshaderinc): the lean (x, z), the rustle, and the bush's height.

const CELL := 4.0  ## metres a cell of the grid the bushes are found by
const HERO_RADIUS := 0.34  ## the hero's own (scripts/hero.gd)
const FREQUENCY := 2.0  ## a bush's swings back and forth, a second
const DAMPING := 0.2  ## how soon it stops swinging: lower, the longer it shakes
const PUSH := 0.035  ## metres its top leans away from the hero right in it
const ALONG := 0.008  ## and along the way the hero walks, metres for each metre a second

## how much they shake, against as tuned (F2)
var shake := 1.0
## the share of the hero's speed a bush takes in its middle part, less toward its edge (F2): a little, as asked
var drag := 0.15
## drawn (F2's Bushes): hidden, they neither slow the hero nor shake
var shown := true
var _bushes := []  # each [x, z, how far it reaches, height, its multimesh, its instance there]
var _cells := {}  # Vector2i -> the bushes reaching into the cell
var _moving := {}  # bush -> [its top's lean, how fast that changes, how much its leaves rustle]
var _last := Vector2.INF  # where the hero was the frame before


## A bush with its foot at foot, reaching radius metres out and height up, drawn as instance index of multimesh mm
## (which has custom data).
func add(foot: Vector3, radius: float, height: float, mm: MultiMesh, index: int) -> void:
	var i := _bushes.size()
	_bushes.append([foot.x, foot.z, radius, height, mm, index])
	mm.set_instance_custom_data(index, Color(0.0, 0.0, 0.0, height))
	var reach := radius + HERO_RADIUS
	for cz in range(floori((foot.z - reach) / CELL), floori((foot.z + reach) / CELL) + 1):
		for cx in range(floori((foot.x - reach) / CELL), floori((foot.x + reach) / CELL) + 1):
			var key := Vector2i(cx, cz)
			if not _cells.has(key):
				_cells[key] = []
			(_cells[key] as Array).append(i)


## How fast the hero walks at p, against its own speed: slower in a bush, the most in its middle part.
func speed_at(p: Vector3) -> float:
	if not shown:
		return 1.0
	var deep := 0.0
	for i: int in _near(p):
		var b: Array = _bushes[i]
		deep = maxf(deep, 1.0 - smoothstep(0.35 * b[2], b[2], Vector2(p.x - b[0], p.z - b[1]).length()))
	return 1.0 - drag * deep


## Every frame, the hero at hero: the bushes it walks through pushed and dragged along, and every bush that's moving
## sprung back, handed to its shader. A long frame (the camera snapping somewhere) settles them all.
func update(hero: Vector3, delta: float) -> void:
	var at := Vector2(hero.x, hero.z)
	var walk := (at - _last) / delta if _last.is_finite() and delta > 0.0 and delta < 0.25 else Vector2.ZERO
	_last = at
	if delta >= 0.25 or not shown:
		for i: int in _moving:
			_hand(i, Vector2.ZERO, 0.0)
		_moving.clear()
		return
	if walk.length() > 0.1:  # standing still in a bush doesn't shake it
		for i: int in _near(hero):
			if _touch(i, at) > 0.0 and not _moving.has(i):
				_moving[i] = [Vector2.ZERO, Vector2.ZERO, 0.0]
	var k := pow(TAU * FREQUENCY, 2.0)
	var c := 2.0 * DAMPING * TAU * FREQUENCY
	var steps := ceili(delta * 120.0)  # short enough steps to stay steady
	for i: int in _moving.keys():
		var m: Array = _moving[i]
		var b: Array = _bushes[i]
		var lean: Vector2 = m[0]
		var speed: Vector2 = m[1]
		var touch := _touch(i, at)
		var push := Vector2.ZERO  # where the hero would hold its top, pushed in
		if touch > 0.0:
			var away := Vector2(b[0], b[1]) - at
			away = away.normalized() if away.length() > 0.05 else walk.normalized()
			push = (away * PUSH + walk * ALONG) * touch
			m[2] = maxf(m[2], touch * minf(walk.length() / 5.5, 1.0))
		for s in steps:
			speed += ((push - lean) * k - speed * c) * (delta / steps)
			lean += speed * (delta / steps)
		m[0] = lean
		m[1] = speed
		m[2] *= exp(-delta * 2.5)
		if touch <= 0.0 and lean.length() < 0.001 and speed.length() < 0.01 and m[2] < 0.01:
			_moving.erase(i)
			_hand(i, Vector2.ZERO, 0.0)
		else:
			_hand(i, lean, m[2])


## How far the bushes have been pushed: the most any of them leans now, metres at its top.
func most_lean() -> float:
	var most := 0.0
	for i: int in _moving:
		most = maxf(most, (_moving[i][0] as Vector2).length())
	return most


## How much the hero at at touches bush i: 0 clear of it, up to 1 in its middle part.
func _touch(i: int, at: Vector2) -> float:
	var b: Array = _bushes[i]
	return 1.0 - smoothstep(0.35 * b[2], b[2] + HERO_RADIUS, at.distance_to(Vector2(b[0], b[1])))


func _near(p: Vector3) -> Array:
	return _cells.get(Vector2i(floori(p.x / CELL), floori(p.z / CELL)), [])


func _hand(i: int, lean: Vector2, rustle: float) -> void:
	var b: Array = _bushes[i]
	(b[4] as MultiMesh).set_instance_custom_data(b[5], Color(lean.x * shake, lean.y * shake, rustle * shake, b[3]))
