class_name LeafLitter
extends Node3D
## Autumn's fallen leaves, lying thick, in an area whose ground has them (its litter.png: the autumn hollow): the user
## asked for a thick layer of leaves there, not grass, thin in places and now and then deep in piles, which stir as
## the hero walks through, a few leaves hopping up a centimetre or two and falling back (14 October). The ground
## shader paints the thin layer (its fallen leaves, two layers of them where the litter is); this lays the piles over
## it, of leaves of their own: small faceted kites, folded along the midrib, in the same colours
## (shaders/leaf_litter.gdshader).
##
## The ground's textures say where the piles are (pile_at in the shader: where the litter is and the leaves' drift
## noise runs high, broken up), and how deep. Every CHUNK-metre square that has any draws a patch of PATCH_LEAVES
## leaves at each point of a SPACING grid that's in a pile (worked out here once, as the area loads, from the same
## textures); the shader stands each leaf on the ground, stacked as deep in the pile as it lies, drops those a thin
## edge doesn't have, and stirs them along the hero's trail (scripts/hero_trail.gd).

const CHUNK := 16.0
const SPACING := 0.4  ## metres between the grid's patches
const PATCH_LEAVES := 48  ## leaves in a patch, in a disc PATCH_RADIUS across
const PATCH_RADIUS := 0.3
const MIN_PILE := 0.07  ## a pile shallower than this at a grid point has no patch there (it would draw hardly a leaf)

var world: DemoWorld
## drawn: F2's Fallen leaves, Piles (or As before: none)
var shown := true
## how much of the litter lies in piles: 1 about a third of the grove's, up to 2 about half
var amount := 1.0
## metres a stirred leaf hops, at most: 1-2 cm, as the user asked
var hop := 0.02
## metres deep at a pile's thickest
var depth := 0.12
## metres from the camera where the last of them has gone
var reach := 32.0
## seconds until the stirred leaves are still again (the hero's trail is kept at least as long)
var settle := 1.5
var _material: ShaderMaterial
var _mesh: ArrayMesh
var _chunks: Array[MultiMeshInstance3D] = []
var _masks: Image
var _litter: Image
var _block: Image
var _laid := -1.0  # the amount the patches were laid out for


## Make the field, given the ground's litter texture; block is the grass's mask of what lies on the ground
## (scripts/grass.gd).
func build(w: DemoWorld, litter: Texture2D, block: ImageTexture) -> void:
	world = w
	name = "LeafLitter"
	_litter = _image(litter)
	_masks = _image(world.ground_param("masks_tex"))
	_block = block.get_image()
	_mesh = _patch_mesh()
	_material = ShaderMaterial.new()
	_material.shader = load("res://shaders/leaf_litter.gdshader")
	var b: Array = world.ground["bounds"]
	_material.set_shader_parameter("bounds", Vector4(b[0], b[1], b[2], b[3]))
	_material.set_shader_parameter("spacing", SPACING)
	for param: String in ["canopy_tex", "canopy_strength"]:
		set_ground_param(param, world.ground_param(param))
	_mesh.surface_set_material(0, _material)
	_lay_out()
	_apply()


## A ground parameter the leaves share with the ground shader (DemoWorld.set_ground_param).
func set_ground_param(param: String, value: Variant) -> void:
	if param in ["canopy_tex", "canopy_strength"]:
		_material.set_shader_parameter(param, value)


func set_option(option: String, value: Variant) -> void:
	set(option, value)
	if option == "amount":
		_lay_out()
	_apply()


func _apply() -> void:
	_material.set_shader_parameter("hop", hop)
	_material.set_shader_parameter("depth", depth)
	_material.set_shader_parameter("reach", reach)
	_material.set_shader_parameter("settle", settle)
	world.set_ground_param("leaf_piles", amount if shown else 0.0)  # the ground under them, in their shade
	for mmi in _chunks:
		mmi.visible = shown
		mmi.visibility_range_end = reach + CHUNK * 0.75


## Every frame: the hero's trail for the shader.
func update(trail: HeroTrail) -> void:
	if not shown:
		return
	_material.set_shader_parameter("trail", trail.packed())
	_material.set_shader_parameter("trail_count", trail.points.size())
	_material.set_shader_parameter("trail_reach", trail.reach(0.6))


## The patches, in every chunk with a pile: at each point of the SPACING grid where the leaves lie any deeper than
## MIN_PILE, and nothing lies on the ground (the grass's block mask). Each patch carries what the shader needs of the
## ground there, worked out once here so its leaves needn't read the textures: how deep the pile is (0..1), the
## ground's height and its slope (INSTANCE_CUSTOM). Laid out anew when amount changes.
func _lay_out() -> void:
	if _laid == amount:
		return
	_laid = amount
	for mmi in _chunks:
		mmi.queue_free()
	_chunks.clear()
	var b: Array = world.ground["bounds"]
	var origin := Vector2(b[0], b[1])
	var size := Vector2(b[2], b[3])
	var n := int(round(CHUNK / SPACING))  # grid points a chunk across
	var tall := depth + 0.2
	for cz in int(ceil(size.y / CHUNK)):
		for cx in int(ceil(size.x / CHUNK)):
			var x0 := origin.x + cx * CHUNK
			var z0 := origin.y + cz * CHUNK
			var spots := PackedVector3Array()
			var data := PackedColorArray()
			var lo := INF
			var hi := -INF
			for j in n:
				for i in n:
					var at := Vector2(x0 + (i + 0.5) * SPACING, z0 + (j + 0.5) * SPACING)
					var uv := (at - origin) / size
					if uv.x >= 1.0 or uv.y >= 1.0:
						continue
					var pile := _pile(uv)
					if pile <= MIN_PILE or _block.get_pixel(int(uv.x * _block.get_width()), int(uv.y * _block.get_height())).r > 0.1:
						continue
					var h := world.height_at(at.x, at.y)
					var slope := Vector2(world.height_at(at.x + 0.3, at.y) - h, world.height_at(at.x, at.y + 0.3) - h) / 0.3
					lo = minf(lo, h)
					hi = maxf(hi, h)
					spots.append(Vector3(at.x - x0, 0.0, at.y - z0))
					data.append(Color(pile, h, slope.x, slope.y))
			if spots.is_empty():
				continue
			var mm := MultiMesh.new()
			mm.transform_format = MultiMesh.TRANSFORM_3D
			mm.use_custom_data = true
			mm.mesh = _mesh
			mm.instance_count = spots.size()
			for k in spots.size():
				mm.set_instance_transform(k, Transform3D(Basis(), spots[k]))
				mm.set_instance_custom_data(k, data[k])
			var mmi := MultiMeshInstance3D.new()
			mmi.multimesh = mm
			mmi.position = Vector3(x0, 0.0, z0)
			mmi.custom_aabb = AABB(Vector3(-1.0, lo - 0.5, -1.0), Vector3(CHUNK + 2.0, hi - lo + tall + 1.0, CHUNK + 2.0))
			mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			mmi.gi_mode = GeometryInstance3D.GI_MODE_DISABLED
			mmi.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF  # it never moves; laid out anew at once
			add_child(mmi)
			_chunks.append(mmi)


## How deep the leaves lie at uv over the ground's bounds, 0..1: where the litter is, where the leaves' drift noise
## (the masks' alpha, as the ground shader's fallen leaves have it) runs high, broken up by its other two noises. The
## ground shader works out the same, to darken the ground under the piles.
func _pile(uv: Vector2) -> float:
	var lit := _litter.get_pixel(int(uv.x * _litter.get_width()), int(uv.y * _litter.get_height())).r
	if lit <= 0.0:
		return 0.0
	var m := _masks.get_pixel(int(uv.x * _masks.get_width()), int(uv.y * _masks.get_height()))
	var noise := m.a + 0.35 * (_decode(m.g) - 0.5) + 0.12 * (_decode(m.b) - 0.5)
	var lo := 0.55 - 0.08 * (amount - 1.0)
	return lit * smoothstep(lo, lo + 0.14, noise)


static func _decode(v: float) -> float:  # sRGB to linear, as the shaders read the masks (source_color)
	return v / 12.92 if v <= 0.04045 else pow((v + 0.055) / 1.055, 2.4)


static func _image(texture: Texture2D) -> Image:
	var img := texture.get_image()
	if img == null:  # without a graphics card to keep it on, as with --headless
		img = Image.load_from_file(ProjectSettings.globalize_path(texture.resource_path))
	if img.is_compressed():
		img.decompress()
	return img


## A patch of PATCH_LEAVES leaves in a disc: each a kite 10-15 cm long, folded along its midrib (its sides raised a
## little), tilted up to 20 degrees and turned any way, at its own depth in the pile (CUSTOM0.y), with its middle in
## CUSTOM0.xz and its own random number in CUSTOM0.w.
func _patch_mesh() -> ArrayMesh:
	var rng := RandomNumberGenerator.new()
	rng.seed = 1014
	var verts := PackedVector3Array()
	var custom := PackedFloat32Array()
	var index := PackedInt32Array()
	for k in PATCH_LEAVES:
		var r := PATCH_RADIUS * sqrt(rng.randf())
		var a := rng.randf() * TAU
		var middle := Vector2(cos(a), sin(a)) * r
		var length := rng.randf_range(0.1, 0.15)
		var width := length * rng.randf_range(0.45, 0.75)
		var side := length * rng.randf_range(-0.15, 0.1)
		var fold := width * rng.randf_range(0.1, 0.22)
		var shape := [Vector3(-length * 0.5, 0.0, 0.0), Vector3(side, fold, width * 0.5), Vector3(length * 0.5, 0.0, 0.0),
			Vector3(side, fold, -width * 0.5)]
		var basis := Basis(Vector3.UP, rng.randf() * TAU) * Basis(Vector3(cos(a), 0.0, sin(a)), rng.randf_range(-0.35, 0.35))
		var deep := rng.randf()
		var own := rng.randf()
		var first := verts.size()
		for v: Vector3 in shape:
			verts.append(Vector3(middle.x, 0.0, middle.y) + basis * v)
			custom.append_array([middle.x, deep, middle.y, own])
		index.append_array([first, first + 1, first + 2, first, first + 2, first + 3])
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_CUSTOM0] = custom
	arrays[Mesh.ARRAY_INDEX] = index
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays, [], {},
		Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT)
	return mesh
