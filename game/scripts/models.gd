class_name Models
extends RefCounted
## The demo's models: the meshes in the .glb files that tools/build_demo.py exports, with the game's materials.
##
## kit.json, trees.json and stumps.json list every model with its file, size and footprint. A portfolio tree's
## surfaces are named after its Blender materials (Bark, Leaves <tree>, Berries Rowan); the kit's are LowPoly and
## RuneDay. Every tree, old and new, has a stump, <model>_stump, shown in its place while it's in the way.

const INFO_FILES := ["res://assets/kit/kit.json", "res://assets/trees/trees.json", "res://assets/trees/stumps.json"]

static var info := {}
static var _meshes := {}  # model -> mesh with the game's materials
static var _files := {}  # .glb file -> {node name: imported mesh}
static var _materials := {}


static func load_info() -> void:
	if not info.is_empty():
		return
	for path: String in INFO_FILES:
		info.merge(JSON.parse_string(FileAccess.get_file_as_string(path)))


static func has(model: String) -> bool:
	load_info()
	return info.has(model)


static func mesh(model: String) -> Mesh:
	if _meshes.has(model):
		return _meshes[model]
	load_info()
	var file: String = info[model]["file"]
	if not _files.has(file):
		var scene := (load(file) as PackedScene).instantiate()
		var found := {}
		for node in scene.find_children("*", "MeshInstance3D", true, false):
			found[node.name] = (node as MeshInstance3D).mesh
		scene.free()
		_files[file] = found
	var m := _files[file][model] as ArrayMesh
	for i in m.get_surface_count():
		m.surface_set_material(i, _material_for(model, m.surface_get_name(i), m.surface_get_material(i)))
	_meshes[model] = m
	return m


## Trees fade out when they stand in the way between the camera and the hero, so it never disappears behind them.
static func is_tree(model: String) -> bool:
	load_info()
	var file := (info[model]["file"] as String).get_file()  # old_trees.glb, trees.glb, trees_trim.glb, trees_few.glb
	return file.ends_with("trees.glb") or file.begins_with("trees_") or model.begins_with("Snag")


static func _material_for(model: String, surface: String, imported: Material) -> Material:
	var name := imported.resource_name if imported else surface
	if name.begins_with("Leaves") or name.begins_with("Berries"):
		var slot := "berries" if name.begins_with("Berries") else "leaves"
		return _leaf_material(info[model]["textures"][slot])
	if name == "RuneDay":
		return _cached("rune", func() -> Material:
			var m := StandardMaterial3D.new()
			m.albedo_color = Color("#3A3A36")
			m.roughness = 0.9
			return m)
	if model.begins_with("Pebble"):
		return _cached("pebble", func() -> Material:
			var m := ShaderMaterial.new()
			m.shader = load("res://shaders/lowpoly_pebble.gdshader")
			return m)
	var fade := is_tree(model)
	return _cached("lowpoly_fade" if fade else "lowpoly", func() -> Material:
		var m := ShaderMaterial.new()
		m.shader = load("res://shaders/lowpoly_fade.gdshader" if fade else "res://shaders/lowpoly.gdshader")
		if name == "Bark":
			m.set_shader_parameter("roughness", 0.9)
		return m)


static func _leaf_material(texture: String) -> Material:
	return _cached(texture, func() -> Material:
		var m := ShaderMaterial.new()
		m.shader = load("res://shaders/leaves.gdshader")
		m.set_shader_parameter("card", load(texture))
		return m)


static func _cached(key: String, make: Callable) -> Material:
	if not _materials.has(key):
		_materials[key] = make.call()
	return _materials[key]
