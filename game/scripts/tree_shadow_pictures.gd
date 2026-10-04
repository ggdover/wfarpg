class_name TreeShadowPictures
extends RefCounted
## Tree shadows from pictures: each tree model's leaves pictured from the sun, from FRAMES sides round it, white where
## a leaf is, all baked into one atlas at startup, a row a model. A tree's shadow is then cast by its trunk and branches
## as they are, and by one quad facing the sun through the middle of its crown, cut out to the picture from the side
## nearest the sun's (shaders/shadow_picture.gdshader), instead of by its hundreds of leaf cards. The ground and the
## hero under it get much the same shadow; the crowns shade themselves a little more simply. scripts/world.gd uses
## them when tree_shadows is "pictures".

const FRAMES := 16
const PX_PER_M := 24.0  ## the pictures' detail, in pixels a metre (the shadow map's round the hero is about 20)
const MAX_PX := 16384

var meshes := {}  ## model -> what casts its shadow: its trunk and branches and the quad, in the model's units
var _bake_materials := {}


## Picture the given models' leaves (each in the version in versions[model]) as the sun sees them, to_light being the
## direction towards it, and make their shadow casters. A frame.
func bake(parent: Node, models: Array, versions: Dictionary, to_light: Vector3) -> void:
	var el := asin(to_light.y)
	var rows := []
	var tall := 0.0  # metres
	var wide := 0.0
	for m: String in models:
		var mesh := Models.mesh(versions[m])
		var b := _leaf_bounds(mesh)
		var reach: float = b[0]
		# the leaves' outline in the pictures, from any side: across the trunk, and up it, tilted towards the sun
		var y0: float = b[1] * cos(el) - reach * sin(el)
		var y1: float = b[2] * cos(el) + reach * sin(el)
		rows.append({"model": m, "mesh": mesh, "reach": reach, "y0": y0, "y1": y1, "mid": (b[1] + b[2]) * 0.5})
		tall += y1 - y0
		wide = maxf(wide, 2.0 * reach * FRAMES)
	var ppm := minf(PX_PER_M, minf((MAX_PX - 2 * rows.size() - 2) / tall, (MAX_PX - 2 * FRAMES - 2) / wide))
	var w_px := 0
	var h_px := 0
	for r: Dictionary in rows:
		r["fw"] = ceili(2.0 * r["reach"] * ppm) + 2
		r["fh"] = ceili((r["y1"] - r["y0"]) * ppm) + 2
		r["top"] = h_px
		h_px += r["fh"]
		w_px = maxi(w_px, r["fw"] * FRAMES)
	var vp := SubViewport.new()
	vp.size = Vector2i(w_px, h_px)
	vp.own_world_3d = true
	vp.transparent_bg = true
	vp.render_target_update_mode = SubViewport.UPDATE_DISABLED
	var cam := Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.keep_aspect = Camera3D.KEEP_HEIGHT
	cam.size = h_px / ppm
	cam.near = 1.0
	cam.far = 200.0
	cam.position = Vector3(w_px * 0.5 / ppm, -h_px * 0.5 / ppm, 100.0)
	vp.add_child(cam)
	for r: Dictionary in rows:
		var mesh: Mesh = r["mesh"]
		var yc: float = (r["y0"] + r["y1"]) * 0.5
		for f in FRAMES:
			var mi := MeshInstance3D.new()
			mi.mesh = mesh
			for s in mesh.get_surface_count():
				mi.set_surface_override_material(s, _bake_material(mesh.surface_get_material(s)))
			# turned to frame f, tilted towards the camera as far as the sun is above the horizon, the outline's middle
			# on the frame's
			var b := Basis(Vector3.RIGHT, el) * Basis(Vector3.UP, TAU * f / FRAMES)
			mi.transform = Transform3D(b, Vector3((f + 0.5) * r["fw"], -(r["top"] + r["fh"] * 0.5), 0.0) / ppm - Vector3(0.0, yc, 0.0))
			vp.add_child(mi)
	parent.add_child(vp)
	vp.render_target_update_mode = SubViewport.UPDATE_ONCE
	await RenderingServer.frame_post_draw
	var img := vp.get_texture().get_image()
	vp.queue_free()
	img.convert(Image.FORMAT_R8)
	img.generate_mipmaps()
	var atlas := ImageTexture.create_from_image(img)
	var shader: Shader = load("res://shaders/shadow_picture.gdshader")
	for r: Dictionary in rows:
		var mat := ShaderMaterial.new()
		mat.shader = shader
		mat.set_shader_parameter("atlas", atlas)
		mat.set_shader_parameter("frames", float(FRAMES))
		mat.set_shader_parameter("frame_u", float(r["fw"]) / w_px)
		mat.set_shader_parameter("row", Vector2(float(r["top"]) / h_px, float(r["top"] + r["fh"]) / h_px))
		mat.set_shader_parameter("to_light", to_light)
		mat.set_shader_parameter("crown_mid", r["mid"])
		var half := Vector2(r["fw"], r["fh"]) * 0.5 / ppm
		meshes[r["model"]] = _caster(r["mesh"], mat, half, (r["y0"] + r["y1"]) * 0.5, r["mid"], to_light)


## How far a model's leaves reach from its trunk, and their lowest and highest points.
static func _leaf_bounds(mesh: Mesh) -> Array:
	var r2 := 0.0
	var lo := INF
	var hi := -INF
	for s in mesh.get_surface_count():
		if not _is_leaf(mesh.surface_get_material(s)):
			continue
		for v: Vector3 in mesh.surface_get_arrays(s)[Mesh.ARRAY_VERTEX]:
			r2 = maxf(r2, v.x * v.x + v.z * v.z)
			lo = minf(lo, v.y)
			hi = maxf(hi, v.y)
	return [sqrt(r2), lo, hi]


static func _is_leaf(m: Material) -> bool:
	return m is ShaderMaterial and (m as ShaderMaterial).get_shader_parameter("card") != null


## The unlit material a surface is pictured with: a leaf card in white, or nothing for the bark.
func _bake_material(game: Material) -> Material:
	var card: Variant = (game as ShaderMaterial).get_shader_parameter("card") if _is_leaf(game) else null
	var key: Variant = card if card else "bark"
	if not _bake_materials.has(key):
		var m := ShaderMaterial.new()
		m.shader = load("res://shaders/impostor_bake.gdshader")
		m.set_shader_parameter("leaf", card != null)
		m.set_shader_parameter("silhouette", true)
		if card:
			m.set_shader_parameter("card", card)
		_bake_materials[key] = m
	return _bake_materials[key]


## The model's trunk and branches, as they are, and the quad: half wide and high round (0, yc) in the picture's
## coordinates. Its box holds the quad whichever way the tree is turned.
static func _caster(mesh: Mesh, mat: ShaderMaterial, half: Vector2, yc: float, mid: float, to_light: Vector3) -> ArrayMesh:
	var out := ArrayMesh.new()
	for s in mesh.get_surface_count():
		if not _is_leaf(mesh.surface_get_material(s)):
			out.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(s))
			out.surface_set_material(out.get_surface_count() - 1, mesh.surface_get_material(s))
	var corners := [Vector2(-half.x, yc + half.y), Vector2(half.x, yc + half.y), Vector2(half.x, yc - half.y), Vector2(-half.x, yc - half.y)]
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = PackedVector3Array(corners.map(func(c: Vector2) -> Vector3: return Vector3(c.x, c.y, 0.0)))
	arrays[Mesh.ARRAY_NORMAL] = PackedVector3Array([Vector3.BACK, Vector3.BACK, Vector3.BACK, Vector3.BACK])
	arrays[Mesh.ARRAY_TEX_UV] = PackedVector2Array([Vector2(0, 0), Vector2(1, 0), Vector2(1, 1), Vector2(0, 1)])
	arrays[Mesh.ARRAY_INDEX] = PackedInt32Array([0, 1, 2, 0, 2, 3])
	out.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	out.surface_set_material(out.get_surface_count() - 1, mat)
	# where the shader puts the corners (shadow_picture.gdshader), measured from the trunk, which turns with the tree
	var right := Vector3.UP.cross(to_light).normalized()
	var up := to_light.cross(right)
	var box := mesh.get_aabb()
	var reach := 0.0
	for c: Vector2 in corners:
		var p := right * c.x + up * c.y + to_light * (mid * to_light.y)
		reach = maxf(reach, Vector2(p.x, p.z).length())
		box = box.expand(Vector3(0.0, p.y, 0.0))
	box = box.merge(AABB(Vector3(-reach, box.position.y, -reach), Vector3(2.0 * reach, box.size.y, 2.0 * reach)))
	out.custom_aabb = box
	return out
