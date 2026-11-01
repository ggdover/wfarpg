class_name Wind
extends Node
## The wind, as the user asked for it (1 November): gusts blow through, and the trees' leaves, the bushes, the grass
## and the fallen leaves in piles move with them. Every frame it hands the shaders which way it blows, how much it
## moves things and its clock (the global uniform wind), and its gusts' strength and spacing (wind_gusts); they work
## out the gusts themselves, wherever each thing stands (wind_gust in shaders/common.gdshaderinc). Gust fronts sweep
## across the ground with the wind, at any spot one every few seconds, so never 5 s without one (the user asked for
## them a lot more often than the first ones, one every 20 s or so); waves along the wind, their timing and shape bent
## by smooth noise, as games make wind (value noise, a simpler cousin of Perlin noise), so they come neither evenly nor
## in straight lines. Each one's strength is noise too, so it isn't always the same amount of movement (the user, the
## same day): about two in five milder, a third as tuned, and, where a third, slower noise runs high, about one in seven
## strong, up to strong harder than a gust. gust_at works out the same, here.

const SPEED := 4.0  ## metres a second the gusts travel (WIND_SPEED in the shaders)

## which way it blows, along the ground (x, z)
var direction := Vector2.from_angle(deg_to_rad(20.0))
## how much it moves the grass, leaves, bushes and trees: 1 as tuned (F2's Wind, movement)
var strength := 1.0
## how much harder than a gust the strongest gusts blow: 0.6 as tuned, 0 for every gust alike (F2's strong gusts)
var strong := 0.6
## seconds between gusts, about: 3.3 as tuned, so there's never 5 s without one (F2's gusts every)
var every := 3.3
## F2's Wind: off, it's still
var on := true
## seconds it has blown
var clock := 0.0
## what it last handed the shaders
var sent := Vector4.ZERO


func _process(delta: float) -> void:
	clock += delta
	sent = Vector4(direction.x, direction.y, strength if on else 0.0, clock)
	RenderingServer.global_shader_parameter_set("wind", sent)
	RenderingServer.global_shader_parameter_set("wind_gusts", Vector2(strong, every * SPEED))


func _exit_tree() -> void:  # still, for whatever is shown next
	RenderingServer.global_shader_parameter_set("wind", Vector4(direction.x, direction.y, 0.0, clock))


## How hard it gusts at (x, z), at its clock or at another time: 0 calm, 1 a gust, up to 1 + strong the strongest; as
## the shaders work it out (wind_gust).
func gust_at(x: float, z: float, at := -1.0) -> float:
	var t := clock if at < 0.0 else at
	var xz := Vector2(x, z)
	var along := xz.dot(direction)
	var warp := noise(Vector3(along / 30.0, xz.dot(Vector2(-direction.y, direction.x)) / 18.0, t * 0.1)) - 0.5
	var phase := (along - t * SPEED) / maxf(every * SPEED, 1.0) + 0.6 * warp
	var gust := smoothstep(0.45, 0.95, 0.5 + 0.5 * cos(TAU * phase))
	if gust <= 0.0:
		return 0.0
	var p := xz - direction * (t * SPEED)
	gust *= 0.6 + 0.4 * smoothstep(0.3, 0.6, noise(Vector3(p.x / 20.0 + 5.0, p.y / 20.0 + 5.0, t * 0.05 + 5.0)))
	if strong > 0.0:
		gust *= 1.0 + strong * smoothstep(0.5, 0.75, noise(Vector3(p.x / 60.0 + 31.0, p.y / 60.0 + 31.0, t * 0.03 + 31.0)))
	return gust


## Smooth value noise in 3D, 0..1, with features about a cell across: value_noise3 in shaders/common.gdshaderinc.
static func noise(p: Vector3) -> float:
	var i := p.floor()
	var f := p - i
	f = f * f * (Vector3(3.0, 3.0, 3.0) - 2.0 * f)
	var x := int(i.x)
	var y := int(i.y)
	var z := int(i.z)
	return lerpf(lerpf(lerpf(_cell(x, y, z), _cell(x + 1, y, z), f.x), lerpf(_cell(x, y + 1, z), _cell(x + 1, y + 1, z), f.x), f.y),
		lerpf(lerpf(_cell(x, y, z + 1), _cell(x + 1, y, z + 1), f.x), lerpf(_cell(x, y + 1, z + 1), _cell(x + 1, y + 1, z + 1), f.x), f.y), f.z)


## A random number, 0..1, for a cell of the grid: hash_cell3 in the shaders, on 32-bit unsigned numbers.
static func _cell(x: int, y: int, z: int) -> float:
	var v := _times(x & 0xFFFFFFFF, 1597334673) ^ _times(y & 0xFFFFFFFF, 3812015801) ^ _times(z & 0xFFFFFFFF, 2798796415)
	return float(_times(v, 1597334673)) / 4294967295.0


## a times b, as 32-bit unsigned numbers multiply (the lowest 32 bits), without going past 64 bits on the way
static func _times(a: int, b: int) -> int:
	return (a * (b & 0xFFFF) + (((a * (b >> 16)) & 0xFFFF) << 16)) & 0xFFFFFFFF
