class_name GrassField
extends Node3D
## The long grass over the area's green ground, as the user asked for (10 October): thick, semi-long grass wherever
## the ground is green, outside the paths, which folds as the hero walks through it. Its patches are the plant
## portfolio's long grass (assets/plants), cards of thin strands crossing, exported by tools/build_demo.py's plants
## stage into assets/plants/plants.glb: one patch without seed heads and one with, a share of them.
##
## The graphics card places it, so placing it takes no time as the area loads (only block_tex does, a tenth of a
## second or so): every CHUNK-metre square of the area draws the same grid of patches (one multimesh for each patch,
## shared), and the grass shader (shaders/grass.gdshader) stands each on the ground, from a texture of the terrain's
## heights; turns, moves and sizes it by where it stands; and keeps it only on green ground, out of the paths' wear
## and off steep ground, and where nothing lies: block_tex, made here, marks the rocks and logs (the layout's solids)
## and the area's own models, its water, boardwalks, jetties, steps and bridges. It takes the ground's colour where it stands. The hero's trail, its
## last 12 m, goes to the shader every frame, and the grass folds away from it and springs back.

const PLANTS := "res://assets/plants/plants.json"
const CHUNK := 16.0  ## metres across each chunk of grass
const BLOCK_TEXEL := 0.25  ## metres per texel of block_tex
const TRAIL := 24  ## the hero's positions kept for the grass to fold round (TRAIL in the shader): 12 m of them
const TRAIL_STEP := 0.5  ## metres the hero walks between two of them
const TRAIL_JUMP := 3.0  ## metres the hero can't walk in a frame: put somewhere else, it starts a new trail
## the ground shader's parameters the grass shares (DemoWorld.set_ground_param)
const GROUND_PARAMS := ["grass_tex", "masks_tex", "path_noise_tex", "canopy_tex", "canopy_strength", "wear_spread", "worn0", "worn1"]

var world: DemoWorld
## drawn, or the mockups' grass tufts as before (DemoWorld.set_grass)
var shown := true
## the share of the grid's patches drawn
var density := 1.0
## how tall, against the patch as tuned
var height_scale := 1.0
## metres from the camera where it has sunk into the ground; the chunks are drawn out to this and their size
var reach := 45.0
## patches whose foot is this near the hero's trail fold, over by up to fold_angle radians (fully within 0.5 m)
var fold_radius := 0.9
var fold_angle := 1.4
## seconds after the hero has gone until the grass stands up again
var recover := 1.6
var _materials: Array[ShaderMaterial] = []
var _chunks: Array[MultiMeshInstance3D] = []
var _trail: Array[Vector3] = []  # x, z and its age in seconds; [0] is the hero now
var _info: Dictionary


func build(w: DemoWorld) -> void:
	world = w
	name = "Grass"
	_info = JSON.parse_string(FileAccess.get_file_as_string(PLANTS))
	var a: Dictionary = _info["LongGrass_A"]
	var spacing: float = a["spacing"]
	var share: float = a["seed_heads"]
	var scene := (load(a["file"]) as PackedScene).instantiate()
	var meshes := {}
	for node in scene.find_children("*", "MeshInstance3D", true, false):
		meshes[node.name] = (node as MeshInstance3D).mesh
	scene.free()
	var heights := _height_texture()
	var block := _block_texture()
	var b: Array = world.ground["bounds"]
	for slot: String in ["leaves", "flowers"]:
		var m := ShaderMaterial.new()
		m.shader = load("res://shaders/grass.gdshader")
		m.set_shader_parameter("card", load(a["textures"][slot]))
		var mean: Array = a["card_mean"][slot]
		var lin := Color(mean[0], mean[1], mean[2]).srgb_to_linear()
		m.set_shader_parameter("card_mean", Vector3(lin.r, lin.g, lin.b))
		m.set_shader_parameter("ground_tint", 1.0 if slot == "leaves" else 0.0)  # the seed heads keep their colours
		m.set_shader_parameter("height_tex", heights)
		m.set_shader_parameter("height_grid", Vector3(world._origin.x, world._origin.y, world._grid))
		m.set_shader_parameter("height_size", world._size)
		m.set_shader_parameter("block_tex", block)
		m.set_shader_parameter("bounds", Vector4(b[0], b[1], b[2], b[3]))
		m.set_shader_parameter("spacing", spacing)
		for param: String in GROUND_PARAMS:  # those the ground had before the grass was made
			m.set_shader_parameter(param, world.ground_param(param))
		_materials.append(m)
	# the grid of patches every chunk draws: jittered, a share of them the patch with seed heads
	var rng := RandomNumberGenerator.new()
	rng.seed = 1010
	var spots := {"LongGrass_A": [], "LongGrass_B": []}
	var n := int(round(CHUNK / spacing))
	for j in n:
		for i in n:
			var p := Vector3((i + 0.5 + rng.randf_range(-0.3, 0.3)) * spacing, 0.0, (j + 0.5 + rng.randf_range(-0.3, 0.3)) * spacing)
			(spots["LongGrass_B" if rng.randf() < share else "LongGrass_A"] as Array).append(p)
	var multimeshes := {}
	for model: String in spots:
		var mesh := (meshes[model] as Mesh).duplicate() as ArrayMesh
		for s in mesh.get_surface_count():
			var imported := mesh.surface_get_material(s)
			var surface := imported.resource_name if imported else mesh.surface_get_name(s)
			mesh.surface_set_material(s, _materials[1] if surface.begins_with("Flowers") else _materials[0])
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.mesh = mesh
		mm.instance_count = (spots[model] as Array).size()
		for k in mm.instance_count:
			mm.set_instance_transform(k, Transform3D(Basis(), spots[model][k]))
		multimeshes[model] = mm
	# a chunk's box: its ground, low to high, and the grass on it
	var tall := maxf(float(a["height"]), float(_info["LongGrass_B"]["height"])) * 1.6
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
			for model: String in multimeshes:
				var mmi := MultiMeshInstance3D.new()
				mmi.multimesh = multimeshes[model]
				mmi.position = Vector3(x0, 0.0, z0)
				mmi.custom_aabb = AABB(Vector3(-1.0, lo - 0.5, -1.0), Vector3(CHUNK + 2.0, hi - lo + tall + 1.0, CHUNK + 2.0))
				mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
				mmi.gi_mode = GeometryInstance3D.GI_MODE_DISABLED
				add_child(mmi)
				_chunks.append(mmi)
	_apply()


## A ground parameter the grass shares with the ground shader (DemoWorld.set_ground_param).
func set_ground_param(param: String, value: Variant) -> void:
	if param in GROUND_PARAMS:
		for m in _materials:
			m.set_shader_parameter(param, value)


func set_option(option: String, value: Variant) -> void:
	set(option, value)
	_apply()


func _apply() -> void:
	for m in _materials:
		m.set_shader_parameter("density", density)
		m.set_shader_parameter("height_scale", height_scale)
		m.set_shader_parameter("reach", reach)
		m.set_shader_parameter("fold_radius", fold_radius)
		m.set_shader_parameter("fold_angle", fold_angle)
		m.set_shader_parameter("recover", recover)
	for mmi in _chunks:
		mmi.visible = shown
		mmi.visibility_range_end = reach + CHUNK * 0.75  # from the chunk's middle


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
