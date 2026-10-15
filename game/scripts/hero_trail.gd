class_name HeroTrail
extends RefCounted
## The hero's trail, newest first, which the grass folds round (scripts/grass.gd) and the fallen leaves stir along
## (scripts/leaf_litter.gd): its position now, then a point every STEP metres it walked, each with how many seconds ago
## the hero was there, kept for keep seconds, at most SIZE of them (SIZE in the shaders: 18 m, a little more than
## the hero walks while a lane through the leaves fills in again). The world updates it every frame
## (DemoWorld.update_sight); the fields hand it to their shaders.

const SIZE := 24
const STEP := 0.75  ## metres the hero walks between two points
const JUMP := 3.0  ## metres the hero can't walk in a frame: put somewhere else, it starts a new trail

## seconds a point is kept: as long as anything along it is still moving (the world sets it)
var keep := 1.6
## x, z and its age in seconds; [0] is the hero now
var points: Array[Vector3] = []


func update(hero_pos: Vector3, delta: float) -> void:
	for i in points.size():
		var p := points[i]
		p.z += delta
		points[i] = p
	var here := Vector3(hero_pos.x, hero_pos.z, 0.0)
	if points.is_empty() or Vector2(here.x - points[0].x, here.y - points[0].y).length() > JUMP:
		points = [here, here]
	points[0] = here
	if Vector2(here.x - points[1].x, here.y - points[1].y).length() >= STEP:
		points.insert(1, here)
	while points.size() > SIZE or (points.size() > 2 and points[-1].z > keep):
		points.pop_back()


## The points for a shader's trail uniform (vec4: x, z, age, 0), SIZE of them.
func packed() -> PackedVector4Array:
	var out := PackedVector4Array()
	for p in points:
		out.append(Vector4(p.x, p.y, p.z, 0.0))
	out.resize(SIZE)
	return out


## How far from the hero now any of it reaches, and radius more: the shaders skip what's further.
func reach(radius: float) -> float:
	var far := 0.0
	for p in points:
		far = maxf(far, Vector2(p.x - points[0].x, p.y - points[0].y).length())
	return far + radius
