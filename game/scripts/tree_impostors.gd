class_name TreeImpostors
extends RefCounted
## Distant trees as impostors: pictures of each tree model from FRAMES sides round it, a little from above, all baked
## into one atlas at startup, a row a model. Far off, a tree is drawn as one quad that turns to face the camera and
## shows the pictures from the two sides nearest the camera's, blended (shaders/impostor.gdshader), instead of its
## hundreds of overlapping leaf cards. The pictures, and the quads, are cut to the tree's outline from any side, so
## that little of a quad is empty. scripts/world.gd decides from how far.

const FRAMES := 8
const PX := 256  ## pixels along a picture's longer side
const ELEVATION := 8.0  ## degrees above the horizon the pictures are taken from, as distant trees are seen

var meshes := {}  ## model -> its quad, in the model's units, with its material
var _bake_materials := {}


## Picture the given models (each drawn as the version in versions[model]), and make their quads. A frame.
func bake(parent: Node, models: Array, versions: Dictionary) -> void:
	var el := deg_to_rad(ELEVATION)
	var rows := []
	var w_px := 0
	var h_px := 0
	for m: String in models:
		var mesh := Models.mesh(versions[m])
		var b := _bounds(mesh)
		var reach: float = b[0]
		# the outline in the pictures, from any side: across the trunk, and up it, tilted a little towards the camera
		var y0: float = b[1] * cos(el) - reach * sin(el)
		var y1: float = b[2] * cos(el) + reach * sin(el)
		var ppm := (PX - 2) / maxf(2.0 * reach, y1 - y0)  # pixels a metre, in the model's units
		var r := {"model": m, "mesh": mesh, "ppm": ppm, "yc": (y0 + y1) * 0.5, "top": h_px,
			"fw": ceili(2.0 * reach * ppm) + 2, "fh": ceili((y1 - y0) * ppm) + 2}
		rows.append(r)
		h_px += r["fh"]
		w_px = maxi(w_px, r["fw"] * FRAMES)
	var vp := SubViewport.new()
	vp.size = Vector2i(w_px, h_px)
	vp.own_world_3d = true
	vp.transparent_bg = true
	vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	var cam := Camera3D.new()  # a unit a pixel
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.keep_aspect = Camera3D.KEEP_HEIGHT
	cam.size = float(h_px)
	cam.near = 1.0
	cam.far = 4.0 * PX
	cam.position = Vector3(w_px * 0.5, -h_px * 0.5, 2.0 * PX)
	vp.add_child(cam)
	for r: Dictionary in rows:
		var mesh: Mesh = r["mesh"]
		for f in FRAMES:
			var mi := MeshInstance3D.new()
			mi.mesh = mesh
			for s in mesh.get_surface_count():
				mi.set_surface_override_material(s, _bake_material(mesh.surface_get_material(s)))
			var b := (Basis(Vector3.RIGHT, el) * Basis(Vector3.UP, TAU * f / FRAMES)) * float(r["ppm"])
			mi.transform = Transform3D(b, Vector3((f + 0.5) * r["fw"], -(r["top"] + r["fh"] * 0.5) - r["yc"] * r["ppm"], 0.0))
			vp.add_child(mi)
	parent.add_child(vp)
	vp.render_target_update_mode = SubViewport.UPDATE_ONCE
	await RenderingServer.frame_post_draw
	var img := vp.get_texture().get_image()
	vp.queue_free()
	img.generate_mipmaps()
	var atlas := ImageTexture.create_from_image(img)
	var shader: Shader = load("res://shaders/impostor.gdshader")
	for r: Dictionary in rows:
		var mat := ShaderMaterial.new()
		mat.shader = shader
		mat.set_shader_parameter("atlas", atlas)
		mat.set_shader_parameter("frames", float(FRAMES))
		mat.set_shader_parameter("frame_u", float(r["fw"]) / w_px)
		var half := Vector2(r["fw"], r["fh"]) * 0.5 / float(r["ppm"])
		meshes[r["model"]] = _quad(half, r["yc"], float(r["top"]) / h_px, float(r["top"] + r["fh"]) / h_px, mat)


## How far a model reaches from its trunk, and its lowest and highest points.
static func _bounds(mesh: Mesh) -> Array:
	var r2 := 0.0
	var lo := INF
	var hi := -INF
	for s in mesh.get_surface_count():
		for v: Vector3 in mesh.surface_get_arrays(s)[Mesh.ARRAY_VERTEX]:
			r2 = maxf(r2, v.x * v.x + v.z * v.z)
			lo = minf(lo, v.y)
			hi = maxf(hi, v.y)
	return [sqrt(r2), lo, hi]


## The unlit material a surface is pictured with: its leaf card, or its vertex colours.
func _bake_material(game: Material) -> Material:
	var card: Variant = (game as ShaderMaterial).get_shader_parameter("card") if game is ShaderMaterial else null
	var key: Variant = card if card else "bark"
	if not _bake_materials.has(key):
		var m := ShaderMaterial.new()
		m.shader = load("res://shaders/impostor_bake.gdshader")
		m.set_shader_parameter("leaf", card != null)
		if card:
			m.set_shader_parameter("card", card)
		_bake_materials[key] = m
	return _bake_materials[key]


## A quad half.x either side of the trunk and half.y above and below the height yc; UV across a picture and down its
## row (v0..v1), UV2 across and down the quad.
static func _quad(half: Vector2, yc: float, v0: float, v1: float, mat: Material) -> ArrayMesh:
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = PackedVector3Array([Vector3(-half.x, yc + half.y, 0), Vector3(half.x, yc + half.y, 0),
		Vector3(half.x, yc - half.y, 0), Vector3(-half.x, yc - half.y, 0)])
	arrays[Mesh.ARRAY_NORMAL] = PackedVector3Array([Vector3.BACK, Vector3.BACK, Vector3.BACK, Vector3.BACK])
	arrays[Mesh.ARRAY_TEX_UV] = PackedVector2Array([Vector2(0, v0), Vector2(1, v0), Vector2(1, v1), Vector2(0, v1)])
	arrays[Mesh.ARRAY_TEX_UV2] = PackedVector2Array([Vector2(0, 0), Vector2(1, 0), Vector2(1, 1), Vector2(0, 1)])
	arrays[Mesh.ARRAY_INDEX] = PackedInt32Array([0, 1, 2, 0, 2, 3])
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	mesh.surface_set_material(0, mat)
	# the quad turns in the shader, so its box must hold it at any turn
	mesh.custom_aabb = AABB(Vector3(-half.x, yc - half.y, -half.x), Vector3(2.0 * half.x, 2.0 * half.y, 2.0 * half.x))
	return mesh
