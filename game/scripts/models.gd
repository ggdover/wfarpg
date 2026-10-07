class_name Models
extends RefCounted
## The demo's models: the meshes in the .glb files that tools/build_demo.py exports, with the game's materials.
##
## kit.json, trees.json and stumps.json list every model with its file, size and footprint. A portfolio tree's
## surfaces are named after its Blender materials (Bark, Leaves <tree>, Berries Rowan); the kit's are LowPoly and
## RuneDay. Every tree, old and new, has a stump, <model>_stump, shown in its place while it's in the way, and a bare
## trunk, <model>_trunk, which the x-ray leaves standing. A portfolio tree's full version also has a thinned one, made
## as it loads (thinned).

const INFO_FILES := ["res://assets/kit/kit.json", "res://assets/trees/trees.json", "res://assets/trees/stumps.json"]

static var info := {}
static var _meshes := {}  # model -> mesh with the game's materials
static var _files := {}  # .glb file -> {node name: imported mesh}
static var _materials := {}
static var _thinned := {}  # a portfolio tree's full version -> the same with its leaf cards thinned out (thinned)
## the share of a portfolio tree's leaf cards its thinned version keeps
const THIN_KEEP := 0.5


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
	if thinnable(model):
		m = _thin(model, m)
	for i in m.get_surface_count():
		m.surface_set_material(i, _material_for(model, m.surface_get_name(i), m.surface_get_material(i)))
	if _thinned.has(model):
		var t: ArrayMesh = _thinned[model]
		for i in t.get_surface_count():
			t.surface_set_material(i, m.surface_get_material(i))
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
	if model.ends_with("_trunk"):  # a tree's bare trunk, which the x-ray leaves standing
		return _cached("lowpoly_trunk", func() -> Material:
			var m := ShaderMaterial.new()
			m.shader = load("res://shaders/lowpoly_trunk.gdshader")
			m.set_shader_parameter("roughness", 0.9)
			return m)
	var fade := is_tree(model)
	return _cached("lowpoly_fade" if fade else "lowpoly", func() -> Material:
		var m := ShaderMaterial.new()
		m.shader = load("res://shaders/lowpoly_fade.gdshader" if fade else "res://shaders/lowpoly.gdshader")
		if name == "Bark":
			m.set_shader_parameter("roughness", 0.9)
		return m)


## The kit's material, for an area's own models (scripts/world.gd, _build_extras).
static func lowpoly_material() -> Material:
	return _cached("lowpoly", func() -> Material:
		var m := ShaderMaterial.new()
		m.shader = load("res://shaders/lowpoly.gdshader")
		return m)


## Water (shaders/water.gdshader), in WATER's colours for its kind: Lake, River or Pool.
static func water_material(kind: String) -> Material:
	return _cached("water " + kind, func() -> Material:
		var m := ShaderMaterial.new()
		m.shader = load("res://shaders/water.gdshader")
		var look: Dictionary = WATER.get(kind, WATER["Lake"])
		for param: String in look:
			m.set_shader_parameter(param, look[param])
		return m)


## The kinds of water: a forest lake's dark, brownish water, a stream's clearer water over stones, a bog pool's black.
const WATER := {
	"Lake": {"shallow": Color("#4A4632"), "deep": Color("#101D22"), "clear": 0.9, "ripple": 0.005, "roughness": 0.02,
		"specular": 0.7},
	"River": {"shallow": Color("#5A5438"), "deep": Color("#17241E"), "clear": 0.45, "ripple": 0.06, "roughness": 0.08},
	"Pool": {"shallow": Color("#3A3222"), "deep": Color("#161B21"), "clear": 0.35, "ripple": 0.004, "roughness": 0.02,
		"specular": 0.7},
}


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


## Has the model a thinned version? A portfolio tree's full version has, with square or trimmed leaf cards, its lighter
## spruce leaves too (trees.json says which: tools/build_demo.py).
static func thinnable(model: String) -> bool:
	load_info()
	return info.has(model) and info[model].get("thinnable", false)


## A portfolio tree's full version with its leaf cards thinned out, for drawing it see-through near the camera
## (DemoWorld.veil_lighter), which costs less with fewer cards: the same cards, each where it is, but only THIN_KEEP
## of them. The full version marks the ones dropped (UV2.y = 1), so that as the tree goes see-through, they can go
## first (sight_thin in shaders/leaves.gdshader). Both are made as the full version loads.
static func thinned(model: String) -> Mesh:
	mesh(model)
	return _thinned[model]


## Make the model's thinned version from its imported mesh (src), and return its full version, the same but for the
## dropped cards' marks. Both are made from the imported mesh's own data, byte for byte, so that every vertex stays
## exactly where it was (rebuilding them from their arrays would round them anew, which shifts the leaves' edges by a
## pixel here and there): the full version with the marks written into it, the thinned one drawing only the triangles
## of the cards kept. The cards dropped are picked at random, the same every time, so that the crown thins out evenly:
## dropping those deepest in it instead would cost less still, but bares the branches that a spruce's inner sprays hide.
## A rowan's berries all stay.
static func _thin(model: String, src: ArrayMesh) -> ArrayMesh:
	var surfaces: Array = src.get("_surfaces")  # the imported mesh's data, as it's saved
	var indices := []  # per surface: its triangles' corners
	var cards := []  # per surface: each vertex's card, as its lowest-numbered vertex, or null for a surface kept whole
	var every := []  # every leaf card, as [surface, its lowest-numbered vertex]
	for s in surfaces.size():
		var idx: PackedInt32Array = src.surface_get_arrays(s)[Mesh.ARRAY_INDEX]
		indices.append(idx)
		if not src.surface_get_name(s).begins_with("Leaves"):
			cards.append(null)
			continue
		var root := _join_cards(idx, surfaces[s]["vertex_count"])
		cards.append(root)
		for v in root.size():
			if root[v] == v:
				every.append([s, v])
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(model)
	for k in range(every.size() - 1, 0, -1):  # shuffled, the same every time
		var j := rng.randi_range(0, k)
		var swap: Array = every[k]
		every[k] = every[j]
		every[j] = swap
	var dropped := {}  # surface -> the first vertex of each card dropped
	for k in roundi(every.size() * (1.0 - THIN_KEEP)):
		if not dropped.has(every[k][0]):
			dropped[every[k][0]] = {}
		dropped[every[k][0]][every[k][1]] = true
	# the full version, with the dropped cards marked, and the thinned one, without them
	var full_surfaces := []
	var thin_surfaces := []
	for s in surfaces.size():
		var data: Dictionary = surfaces[s]
		var thin_data := data.duplicate()
		if cards[s] != null:
			var root: PackedInt32Array = cards[s]
			var gone: Dictionary = dropped.get(s, {})
			var format: int = data["format"]
			var count: int = data["vertex_count"]
			var stride := RenderingServer.mesh_surface_get_format_attribute_stride(format, count)
			var at := RenderingServer.mesh_surface_get_format_offset(format, count, Mesh.ARRAY_TEX_UV2)
			var packed := (format & Mesh.ARRAY_FLAG_COMPRESS_ATTRIBUTES) != 0  # UV2 as two 16-bit fractions, or two floats
			var attributes: PackedByteArray = data["attribute_data"]
			for v in count:
				if gone.has(root[v]):
					if packed:
						attributes.encode_u16(v * stride + at + 2, 65535)  # UV2.y = 1
					else:
						attributes.encode_float(v * stride + at + 4, 1.0)
			data["attribute_data"] = attributes
			thin_data["attribute_data"] = attributes
			var idx: PackedInt32Array = indices[s]
			var size := RenderingServer.mesh_surface_get_format_index_stride(format, count)
			var kept := PackedByteArray()
			kept.resize(idx.size() * size)
			var n := 0
			for t in range(0, idx.size(), 3):
				if gone.has(root[idx[t]]):
					continue
				for c in 3:
					if size == 2:
						kept.encode_u16(n * 2, idx[t + c])
					else:
						kept.encode_u32(n * 4, idx[t + c])
					n += 1
			kept.resize(n * size)
			thin_data["index_data"] = kept
			thin_data["index_count"] = n
		full_surfaces.append(data)
		thin_surfaces.append(thin_data)
	var full := ArrayMesh.new()
	full.set("_surfaces", full_surfaces)
	var thin := ArrayMesh.new()
	thin.set("_surfaces", thin_surfaces)
	_thinned[model] = thin
	return full


## Which card each vertex belongs to, as the lowest-numbered vertex of its card: the triangles' corners joined up, as a
## card shares none with another.
static func _join_cards(idx: PackedInt32Array, count: int) -> PackedInt32Array:
	var root := PackedInt32Array()
	root.resize(count)
	for v in count:
		root[v] = v
	for t in idx.size():
		var a := idx[t - t % 3]
		var b := idx[t]
		while root[a] != a:
			a = root[a]
		while root[b] != b:
			b = root[b]
		if a != b:
			root[maxi(a, b)] = mini(a, b)
	for v in count:
		var r := root[v]
		while root[r] != r:
			r = root[r]
		root[v] = r
	return root
