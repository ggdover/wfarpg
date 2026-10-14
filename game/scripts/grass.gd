class_name GrassField
extends Node3D
## The grass over the area's green ground, as the user asked for (10 October): grass wherever the ground is green,
## outside the paths, which folds as the hero walks through it. Its patches are one of the plant portfolio's grasses
## (assets/plants), cards of strands crossing, exported by tools/build_demo.py's plants stage into assets/plants: the
## grass styles (wisps, tufts, clumps, short), each with a ground texture of its strands lying flat, which the ground
## shader lays over the green ground so the grass and the ground under it match; or the long grass, the first try.
## STYLES lists them; F2's Grass and G switch between them, and "before" shows the mockups' grass tufts instead.
##
## The graphics card places it, so placing it takes no time as the area loads (only block_tex does, a tenth of a
## second or so): every CHUNK-metre square of the area draws the same grid of patches (one multimesh for each of a
## style's two patches, shared), and the grass shader (shaders/grass.gdshader) stands each on the ground, from a
## texture of the terrain's heights; turns, moves and sizes it, and every card of it, by where it stands; and keeps it
## only on green ground, out of the paths' wear and off steep ground, and where nothing lies: block_tex, made here,
## marks the rocks and logs (the layout's solids) and the area's own models, its water, boardwalks, jetties, steps and
## bridges. It takes the ground's colour where it stands. The hero's trail, its last 12 m, goes to the shader every
## frame, and the grass folds away from it and springs back.

const PLANTS := "res://assets/plants/plants.json"
## the grasses to choose from, in F2's and G's order, and what they're called there; "before" is the mockups' tufts
const STYLES := {"GrassWisps": "Wisps", "GrassTufts": "Tufts", "GrassClumps": "Clumps", "GrassShort": "Short",
	"LongGrass": "First try", "before": "As before"}
const CHUNK := 16.0  ## metres across each chunk of grass
const MAX_DENSITY := 3.0  ## the most strands F2's slider gives, against a style's as tuned
const MAX_SIZE := 2.0  ## the biggest strands it gives
const BLOCK_TEXEL := 0.25  ## metres per texel of block_tex
const TRAIL := 24  ## the hero's positions kept for the grass to fold round (TRAIL in the shader): 12 m of them
const TRAIL_STEP := 0.5  ## metres the hero walks between two of them
const TRAIL_JUMP := 3.0  ## metres the hero can't walk in a frame: put somewhere else, it starts a new trail
## the ground shader's parameters the grass shares (DemoWorld.set_ground_param)
const GROUND_PARAMS := ["grass_tex", "masks_tex", "path_noise_tex", "canopy_tex", "canopy_strength", "wear_spread", "worn0",
	"worn1", "strokes_tex", "strokes_mean", "strokes_metres", "strokes_amount", "strokes_shade"]

var world: DemoWorld
## the grass shown: one of STYLES (DemoWorld.set_grass)
var style := "GrassTufts"
## drawn: not "before"
var shown := true
## how many strands, against the style's as tuned: its patches stand this much closer together (above 1) or further
## apart, each as it was, so the strands keep their colours and only how many of them there are changes (the user,
## 14 October). The grid of patches is laid out anew for it (_lay_out).
var density := 1.0
## how big the strands are, against as tuned: each card taller and wider, its strands too, and the strands lying flat
## in the style's ground texture as much bigger, so they still match. 1.4 since the user asked for them a bit taller
## and wider (14 October), so it's easier to see the hero walking through them
var strand_size := 1.4
## how tall, against the patches as tuned, on top of their size
var height_scale := 1.0
## metres from the camera where it has sunk into the ground; the chunks are drawn out to this and their size
var reach := 45.0
## how strongly a style's ground texture shows on the green ground: 0 none, 1 as painted
var ground_texture := 1.0
## how much darker the ground is under the grass, in its shade, so its lighter strands show: 1 not at all
var ground_shade := 0.85
## patches whose foot is this near the hero's trail fold, over by up to fold_angle radians (fully within 0.5 m)
var fold_radius := 0.9
var fold_angle := 1.4
## seconds after the hero has gone until the grass stands up again
var recover := 1.6
var _info: Dictionary
var _styles := {}  # style -> {materials: [leaves, flowers], multimeshes: [A, B], ground: {...} or null}, once made
var _materials: Array[ShaderMaterial] = []  # the style shown's
var _chunks: Array[MultiMeshInstance3D] = []  # two a chunk: its A patches and its B
var _ground := {}  # the ground's parameters the grass shares, as last set
var _heights: ImageTexture
var _block: ImageTexture
var _trail: Array[Vector3] = []  # x, z and its age in seconds; [0] is the hero now


func build(w: DemoWorld, first_style: String) -> void:
	world = w
	name = "Grass"
	_info = JSON.parse_string(FileAccess.get_file_as_string(PLANTS))
	_heights = _height_texture()
	_block = _block_texture()
	for param: String in GROUND_PARAMS:  # those the ground had before the grass was made
		_ground[param] = world.ground_param(param)
	# a chunk's box: its ground, low to high, and the tallest grass on it
	var b: Array = world.ground["bounds"]
	var tall := 0.0
	for key: String in _info["grass"]:
		tall = maxf(tall, float(_info["grass"][key]["height"]) * 1.6 * MAX_SIZE)
	for cz in int(ceil(b[3] / CHUNK)):
		for cx in int(ceil(b[2] / CHUNK)):
			var x0: float = b[0] + cx * CHUNK
			var z0: float = b[1] + cz * CHUNK
			var lo := INF
			var hi := -INF
			for sz in 9:
				for sx in 9:
					var h := world.height_at(x0 + sx * CHUNK / 8.0, z0 + sz * CHUNK / 8.0)
					lo = minf(lo, h)
					hi = maxf(hi, h)
			for k in 2:
				var mmi := MultiMeshInstance3D.new()
				mmi.position = Vector3(x0, 0.0, z0)
				mmi.custom_aabb = AABB(Vector3(-1.0, lo - 0.5, -1.0), Vector3(CHUNK + 2.0, hi - lo + tall + 1.0, CHUNK + 2.0))
				mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
				mmi.gi_mode = GeometryInstance3D.GI_MODE_DISABLED
				mmi.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF  # it never moves; laid out anew at once
				add_child(mmi)
				_chunks.append(mmi)
	set_style(first_style)


## Show one of STYLES: its patches in every chunk, its ground texture on the green ground; "before", none (the world
## shows the mockups' tufts then, DemoWorld.set_grass).
func set_style(which: String) -> void:
	style = which if STYLES.has(which) else "GrassTufts"
	shown = style != "before"
	if shown:
		var s := _style(style)
		_materials = s["materials"]
		if s["density"] != density:
			_lay_out(style)
		for i in _chunks.size():
			_chunks[i].multimesh = s["multimeshes"][i % 2]
	_apply()


## A ground parameter the grass shares with the ground shader (DemoWorld.set_ground_param).
func set_ground_param(param: String, value: Variant) -> void:
	if param in GROUND_PARAMS:
		_ground[param] = value
		for s: Dictionary in _styles.values():
			for m: ShaderMaterial in s["materials"]:
				m.set_shader_parameter(param, value)


func set_option(option: String, value: Variant) -> void:
	set(option, value)
	if option == "density" and shown:
		_lay_out(style)
	_apply()


func _apply() -> void:
	for m in _materials:
		m.set_shader_parameter("size", strand_size)
		m.set_shader_parameter("height_scale", height_scale)
		m.set_shader_parameter("reach", reach)
		m.set_shader_parameter("fold_radius", fold_radius)
		m.set_shader_parameter("fold_angle", fold_angle)
		m.set_shader_parameter("recover", recover)
	for mmi in _chunks:
		mmi.visible = shown
		mmi.visibility_range_end = reach + CHUNK * 0.75  # from the chunk's middle
	# the style's ground texture on the green ground, for the ground and the grass's feet alike
	var ground: Variant = _style(style)["ground"] if shown else null
	if ground:
		world.set_ground_param("strokes_tex", ground["texture"])
		world.set_ground_param("strokes_mean", ground["mean"])
		world.set_ground_param("strokes_metres", ground["metres"] * strand_size)
	world.set_ground_param("strokes_amount", ground_texture if ground else 0.0)
	world.set_ground_param("strokes_shade", ground_shade)


## A style's materials and multimeshes, made the first time it's shown.
func _style(key: String) -> Dictionary:
	if _styles.has(key):
		return _styles[key]
	var g: Dictionary = _info["grass"][key]
	var meshes := {}
	var file: String = _info[g["meshes"][0]]["file"]
	var scene := (load(file) as PackedScene).instantiate()
	for node in scene.find_children("*", "MeshInstance3D", true, false):
		meshes[node.name] = (node as MeshInstance3D).mesh
	scene.free()
	var first := key == "LongGrass"  # the first try keeps its colours as it had them: tinted by its cards' average
	var materials: Array[ShaderMaterial] = []
	var b: Array = world.ground["bounds"]
	for slot: String in ["leaves", "flowers"]:
		var m := ShaderMaterial.new()
		m.shader = load("res://shaders/grass.gdshader")
		if g["textures"].has(slot):
			m.set_shader_parameter("card", load(g["textures"][slot]))
			m.set_shader_parameter("card_foot", _linear(g["card_mean" if first else "card_foot"][slot]))
		m.set_shader_parameter("ground_tint", 1.0 if slot == "leaves" else 0.0)  # the seed heads keep their colours
		m.set_shader_parameter("root_blend", 0.0 if first else 0.3)
		m.set_shader_parameter("card_spin", g["spin"])
		m.set_shader_parameter("card_lean", 0.45 * float(g["spin"]))
		m.set_shader_parameter("height_tex", _heights)
		m.set_shader_parameter("height_grid", Vector3(world._origin.x, world._origin.y, world._grid))
		m.set_shader_parameter("height_size", world._size)
		m.set_shader_parameter("block_tex", _block)
		m.set_shader_parameter("bounds", Vector4(b[0], b[1], b[2], b[3]))
		for param: String in _ground:
			m.set_shader_parameter(param, _ground[param])
		materials.append(m)
	var multimeshes := []
	for k in 2:
		var mesh := (meshes[g["meshes"][k]] as Mesh).duplicate() as ArrayMesh
		for s in mesh.get_surface_count():
			var imported := mesh.surface_get_material(s)
			var surface := imported.resource_name if imported else mesh.surface_get_name(s)
			mesh.surface_set_material(s, materials[1] if surface.begins_with("Flowers") else materials[0])
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.mesh = mesh
		multimeshes.append(mm)
	var ground: Variant = null
	if g["ground"]:
		ground = {"texture": load(g["ground"]["texture"]), "mean": _linear(g["ground"]["mean"]), "metres": g["ground"]["metres"]}
	_styles[key] = {"materials": materials, "multimeshes": multimeshes, "ground": ground, "density": -1.0}
	_lay_out(key)
	return _styles[key]


## The grid of patches every chunk draws, for the density: n by n, jittered, a share of them B. The style's spacing
## gives as tuned; n is the whole number that gives at least the density, and the shader draws the share of them that
## makes it exactly that (density there). The same every time for the same n.
func _lay_out(key: String) -> void:
	var s: Dictionary = _styles[key]
	var g: Dictionary = _info["grass"][key]
	var tuned: float = g["spacing"]
	var n := ceili(CHUNK * sqrt(density) / tuned)
	var spacing := CHUNK / n
	var rng := RandomNumberGenerator.new()
	rng.seed = 1010
	var spots := [[], []]
	for j in n:
		for i in n:
			var p := Vector3((i + 0.5 + rng.randf_range(-0.3, 0.3)) * spacing, 0.0, (j + 0.5 + rng.randf_range(-0.3, 0.3)) * spacing)
			(spots[1 if rng.randf() < float(g["share_b"]) else 0] as Array).append(p)
	for k in 2:
		var mm: MultiMesh = s["multimeshes"][k]
		mm.instance_count = (spots[k] as Array).size()
		for i in mm.instance_count:
			mm.set_instance_transform(i, Transform3D(Basis(), spots[k][i]))
	for m: ShaderMaterial in s["materials"]:
		m.set_shader_parameter("spacing", spacing)
		m.set_shader_parameter("density", minf(density * spacing * spacing / (tuned * tuned), 1.0))
	s["density"] = density


static func _linear(srgb: Array) -> Vector3:
	var c := Color(srgb[0], srgb[1], srgb[2]).srgb_to_linear()
	return Vector3(c.r, c.g, c.b)


## Every frame: the hero's trail for the shader, newest first. A new point each TRAIL_STEP metres walked; the oldest
## go once the grass there has stood up again.
func update(hero_pos: Vector3, delta: float) -> void:
	if not shown:
		return
	for i in _trail.size():
		var p := _trail[i]
		p.z += delta
		_trail[i] = p
	var here := Vector3(hero_pos.x, hero_pos.z, 0.0)
	if _trail.is_empty() or Vector2(here.x - _trail[0].x, here.y - _trail[0].y).length() > TRAIL_JUMP:
		_trail = [here, here]
	_trail[0] = here
	if Vector2(here.x - _trail[1].x, here.y - _trail[1].y).length() >= TRAIL_STEP:
		_trail.insert(1, here)
	while _trail.size() > TRAIL or (_trail.size() > 2 and _trail[-1].z > recover):
		_trail.pop_back()
	var points := PackedVector4Array()
	var far := 0.0
	for p in _trail:
		points.append(Vector4(p.x, p.y, p.z, 0.0))
		far = maxf(far, Vector2(p.x - here.x, p.y - here.y).length())
	points.resize(TRAIL)
	for m in _materials:
		m.set_shader_parameter("trail", points)
		m.set_shader_parameter("trail_count", _trail.size())
		m.set_shader_parameter("trail_reach", far + fold_radius)


## The terrain's heights as a texture, one texel per point of its grid: half floats, which the graphics card can
## interpolate between the points (the areas' heights stay within 8 m of 0, where they're true to 4 mm).
func _height_texture() -> ImageTexture:
	var img := Image.create_from_data(world._size.x, world._size.y, false, Image.FORMAT_RF, world.heights.to_byte_array())
	img.convert(Image.FORMAT_RH)
	return ImageTexture.create_from_image(img)


## Where something lies on the ground, so no grass grows there: 1 under the rocks and logs (the layout's solids, as
## far out as they're solid) and under the area's own models wherever they're above the ground (water, boardwalks,
## jetties, steps, bridges), over the ground's bounds at BLOCK_TEXEL. The shader reads it filtered, so a patch keeps
## a little way off them.
func _block_texture() -> ImageTexture:
	var b: Array = world.ground["bounds"]
	var size := Vector2i(int(ceil(b[2] / BLOCK_TEXEL)), int(ceil(b[3] / BLOCK_TEXEL)))
	var data := PackedByteArray()
	data.resize(size.x * size.y)
	var origin := Vector2(b[0], b[1])
	for s: Array in world.layout["solids"]:
		var c := (Vector2(s[0], s[2]) - origin) / BLOCK_TEXEL
		var r: float = maxf(s[3] / BLOCK_TEXEL, 0.71)  # the texel it stands on, however thin
		for j in range(maxi(0, floori(c.y - r)), mini(size.y, ceili(c.y + r) + 1)):
			for i in range(maxi(0, floori(c.x - r)), mini(size.x, ceili(c.x + r) + 1)):
				if Vector2(i + 0.5, j + 0.5).distance_to(c) <= r:
					data[j * size.x + i] = 255
	var extras := world.get_node_or_null("Extras")
	if extras:
		for mi: MeshInstance3D in extras.find_children("*", "MeshInstance3D", true, false):
			var xf := mi.global_transform
			for surface in mi.mesh.get_surface_count():
				var arrays := mi.mesh.surface_get_arrays(surface)
				var verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
				var index: PackedInt32Array = arrays[Mesh.ARRAY_INDEX] if arrays[Mesh.ARRAY_INDEX] != null else PackedInt32Array(range(verts.size()))
				for t in range(0, index.size(), 3):
					_block_triangle(data, size, origin, xf * verts[index[t]], xf * verts[index[t + 1]], xf * verts[index[t + 2]])
	return ImageTexture.create_from_image(Image.create_from_data(size.x, size.y, false, Image.FORMAT_L8, data))


## Mark the texels under a triangle where it's above the ground (or no more than 5 cm under it): a plank, a step,
## the water. One standing on edge (a plank's side) lies along one that doesn't, so it's skipped.
func _block_triangle(data: PackedByteArray, size: Vector2i, origin: Vector2, a: Vector3, b: Vector3, c: Vector3) -> void:
	if absf((b - a).cross(c - a).normalized().y) < 0.2:
		return
	var pa := (Vector2(a.x, a.z) - origin) / BLOCK_TEXEL
	var pb := (Vector2(b.x, b.z) - origin) / BLOCK_TEXEL
	var pc := (Vector2(c.x, c.z) - origin) / BLOCK_TEXEL
	var det := (pb.y - pc.y) * (pa.x - pc.x) + (pc.x - pb.x) * (pa.y - pc.y)
	if absf(det) < 1e-9:  # standing on its edge, seen from above
		return
	for j in range(maxi(0, floori(minf(pa.y, minf(pb.y, pc.y)))), mini(size.y, ceili(maxf(pa.y, maxf(pb.y, pc.y))) + 1)):
		for i in range(maxi(0, floori(minf(pa.x, minf(pb.x, pc.x)))), mini(size.x, ceili(maxf(pa.x, maxf(pb.x, pc.x))) + 1)):
			var k := j * size.x + i
			if data[k] != 0:
				continue
			var p := Vector2(i + 0.5, j + 0.5)
			var u := ((pb.y - pc.y) * (p.x - pc.x) + (pc.x - pb.x) * (p.y - pc.y)) / det
			var v := ((pc.y - pa.y) * (p.x - pc.x) + (pa.x - pc.x) * (p.y - pc.y)) / det
			if u < -0.02 or v < -0.02 or u + v > 1.02:
				continue
			var y := a.y * u + b.y * v + c.y * (1.0 - u - v)
			var at := origin + p * BLOCK_TEXEL
			if y > world.height_at(at.x, at.y) - 0.05:
				data[k] = 255
