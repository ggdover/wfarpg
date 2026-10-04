class_name DemoWorld
extends Node3D
## The demo's area, built when the scene starts from what tools/build_demo.py exported: the terrain and its
## collider, the trees of one set or the other, the rocks and plants, the colliders round the trees and rocks, and
## the walls round the walkable area.
##
## Each tree is drawn on its own, so the camera skips the ones it doesn't see; the portfolio's trees switch to
## lighter versions with distance. How the trees are drawn (which versions, which casts the shadow) can change while
## playing, from the performance panel (scripts/perf_panel.gd). Rocks and plants are multimeshes in square chunks.

const LAYOUT := "res://data/demo_layout.json"
const GROUND := "res://assets/ground/ground.json"
const CHUNK := 32.0
const LOD_MARGIN := 5.0
const PLANT_RANGE := 110.0  # small plants and pebbles are not drawn further off than this
const LAYER_GROUND := 1
const LAYER_SOLID := 2

var layout: Dictionary
var ground: Dictionary
var heights := PackedFloat32Array()
var _size := Vector2i.ZERO
var _origin := Vector2.ZERO
var _grid := 0.5
var _tree_sets := {}  # "old"/"new" -> Array of trees: {model, kind, draw: [instances], shadow: instance or none}
var _tree_xz := PackedVector2Array()
var _tree_cells := {}  # Vector2i -> tree indices, for finding the trees near the camera
var _skipped := {}  # tree index -> true while the tree is faded out completely and not drawn
var _current := ""
const CELL := 8.0

var _ground_material: ShaderMaterial

# How the new trees are drawn; set them with set_trees().
## leaf cards cut down from their squares to the outline round their leaves (looks the same, fewer pixels to draw)
var trimmed := false
## about half the leaf cards per clump (changes the look)
var fewer := false
## which version casts a tree's shadow: "full", "mid" (the first lighter one), "far" (the lightest), or "off"
var tree_shadows := "mid"
## where the lighter versions take over (metres from the camera)
var lod_near := 45.0
var lod_far := 120.0
## fade out trees near a high camera, as the mockups hide them (scripts/camera_rig.gd)
var fade_near_camera := true
## small plants and pebbles cast no shadows
var plant_shadows := false
## for measuring: draw the new trees' lighter versions up close too (--treelod=1 or 2)
var tree_lod := 0


func build(tree_set: String) -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--treelod="):
			tree_lod = int(a.substr(10))
	layout = JSON.parse_string(FileAccess.get_file_as_string(LAYOUT))
	ground = JSON.parse_string(FileAccess.get_file_as_string(GROUND))
	_build_terrain()
	_build_props()
	_build_solids()
	_build_walls()
	show_trees(tree_set)


## Show one tree set, building it the first time.
func show_trees(which: String) -> void:
	_unskip()
	if not _tree_sets.has(which):
		_tree_sets[which] = _build_trees(which)
	for k: String in _tree_sets:
		if k != which:
			for tree: Dictionary in _tree_sets[k]:
				for rid: RID in _instances(tree):
					RenderingServer.instance_set_visible(rid, false)
	_current = which
	_apply_trees()
	_ground_material.set_shader_parameter("canopy_tex", load("res://assets/ground/canopy_%s.png" % which))


## The shaders fade out trees near a high camera (tree_fade in shaders/common.gdshaderinc); those faded out
## completely are not drawn at all, which saves a lot in thick forest. Their shadows stay.
func skip_faded(camera_pos: Vector3, radius: float) -> void:
	var inner := radius - 2.6 if fade_near_camera else 0.0
	var c := Vector2(camera_pos.x, camera_pos.z)
	var now := {}
	if inner > 0.5:
		for cx in range(floori((c.x - inner) / CELL), floori((c.x + inner) / CELL) + 1):
			for cz in range(floori((c.y - inner) / CELL), floori((c.y + inner) / CELL) + 1):
				for i: int in _tree_cells.get(Vector2i(cx, cz), []):
					if c.distance_to(_tree_xz[i]) < inner:
						now[i] = true
	for i: int in _skipped:
		if not now.has(i):
			_draw_tree(i, true)
	for i: int in now:
		if not _skipped.has(i):
			_draw_tree(i, false)
	_skipped = now


func _draw_tree(i: int, draw: bool) -> void:
	var tree: Dictionary = _tree_sets[_current][i]
	var rid: RID = tree["draw"][0]
	if _casts_shadow(tree, 0):  # keep its shadow while it isn't drawn
		RenderingServer.instance_geometry_set_cast_shadows_setting(rid, RenderingServer.SHADOW_CASTING_SETTING_ON if draw
			else RenderingServer.SHADOW_CASTING_SETTING_SHADOWS_ONLY)
	else:
		RenderingServer.instance_set_visible(rid, draw)


func _unskip() -> void:
	if _current != "":
		for i: int in _skipped:
			_draw_tree(i, true)
	_skipped.clear()


## Change how the trees are drawn, now: any of trimmed, fewer, tree_shadows, lod_near, lod_far, fade_near_camera.
func set_trees(option: String, value: Variant) -> void:
	_unskip()
	set(option, value)
	_apply_trees()


## Does this instance of the tree (0: the one drawn near the camera) cast the tree's shadow?
func _casts_shadow(tree: Dictionary, i: int) -> bool:
	if tree_shadows == "off":
		return false
	if tree["kind"] != "full":  # old trees and young spruces cast their own
		return true
	return i > 0 if tree_shadows != "full" else true


func start_position() -> Vector3:
	var p: Array = layout["start"]["position"]
	return Vector3(p[0], p[1], p[2])


## The ground's height under a point, from the terrain's height grid.
func height_at(x: float, z: float) -> float:
	var fx := clampf((x - _origin.x) / _grid, 0.0, _size.x - 1.001)
	var fz := clampf((z - _origin.y) / _grid, 0.0, _size.y - 1.001)
	var i := int(fx)
	var j := int(fz)
	var a := fx - i
	var b := fz - j
	var h00 := heights[j * _size.x + i]
	var h10 := heights[j * _size.x + i + 1]
	var h01 := heights[(j + 1) * _size.x + i]
	var h11 := heights[(j + 1) * _size.x + i + 1]
	return lerpf(lerpf(h00, h10, a), lerpf(h01, h11, a), b)


# ------------------------------------------------------------------ terrain
func _build_terrain() -> void:
	var b: Array = ground["bounds"]
	_origin = Vector2(b[0], b[1])
	_grid = ground["grid"]
	_size = Vector2i(ground["size"][0], ground["size"][1])
	heights = FileAccess.get_file_as_bytes(ground["heights"]).to_float32_array()
	_ground_material = ShaderMaterial.new()
	_ground_material.shader = load("res://shaders/ground.gdshader")
	_ground_material.set_shader_parameter("grass_tex", load("res://assets/ground/grass.jpg"))
	_ground_material.set_shader_parameter("dirt_tex", load("res://assets/ground/dirt.jpg"))
	_ground_material.set_shader_parameter("masks_tex", load("res://assets/ground/masks.png"))
	_ground_material.set_shader_parameter("bounds", Vector4(b[0], b[1], b[2], b[3]))
	# the detailed ground, in strips so the camera can skip what it doesn't see
	var strip := 64
	for j0 in range(0, _size.y - 1, strip):
		var mi := MeshInstance3D.new()
		mi.mesh = _grid_mesh(heights, _size, _origin, _grid, j0, mini(j0 + strip, _size.y - 1), Rect2())
		mi.material_override = _ground_material
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(mi)
	# the outer ground, under the distant forest, with a hole where the detailed ground lies
	var fb: Array = ground["far_bounds"]
	var far_size := Vector2i(ground["far_size"][0], ground["far_size"][1])
	var far_heights := FileAccess.get_file_as_bytes(ground["far_heights"]).to_float32_array()
	var far_mat := ShaderMaterial.new()
	far_mat.shader = load("res://shaders/ground_far.gdshader")
	far_mat.set_shader_parameter("grass_tex", load("res://assets/ground/grass_far.jpg"))
	far_mat.set_shader_parameter("bounds", Vector4(fb[0], fb[1], fb[2], fb[3]))
	var far := MeshInstance3D.new()
	var hole := Rect2(_origin + Vector2.ONE * 6.0, Vector2(b[2], b[3]) - Vector2.ONE * 12.0)
	far.mesh = _grid_mesh(far_heights, far_size, Vector2(fb[0], fb[1]), ground["far_grid"], 0, far_size.y - 1, hole, -0.06)
	far.material_override = far_mat
	far.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(far)
	# the collider: Godot's height map shape is centred and one unit per cell, so it is scaled to the grid
	var body := StaticBody3D.new()
	body.collision_layer = LAYER_GROUND
	var shape := HeightMapShape3D.new()
	shape.map_width = _size.x
	shape.map_depth = _size.y
	var scaled := PackedFloat32Array(heights)
	for k in scaled.size():
		scaled[k] /= _grid
	shape.map_data = scaled
	var cs := CollisionShape3D.new()
	cs.shape = shape
	body.add_child(cs)
	body.scale = Vector3.ONE * _grid
	body.position = Vector3(_origin.x + (_size.x - 1) * _grid * 0.5, 0.0, _origin.y + (_size.y - 1) * _grid * 0.5)
	add_child(body)


## A terrain mesh over rows j0..j1 of a height grid, leaving out the cells inside hole.
static func _grid_mesh(h: PackedFloat32Array, size: Vector2i, origin: Vector2, step: float, j0: int, j1: int, hole: Rect2, drop := 0.0) -> ArrayMesh:
	var rows := j1 - j0 + 1
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	verts.resize(rows * size.x)
	normals.resize(rows * size.x)
	for j in rows:
		var jj := j0 + j
		for i in size.x:
			var k := jj * size.x + i
			verts[j * size.x + i] = Vector3(origin.x + i * step, h[k] + drop, origin.y + jj * step)
			var hl := h[jj * size.x + maxi(i - 1, 0)]
			var hr := h[jj * size.x + mini(i + 1, size.x - 1)]
			var hu := h[maxi(jj - 1, 0) * size.x + i]
			var hd := h[mini(jj + 1, size.y - 1) * size.x + i]
			normals[j * size.x + i] = Vector3(hl - hr, 2.0 * step, hu - hd).normalized()
	var idx := PackedInt32Array()
	idx.resize((rows - 1) * (size.x - 1) * 6)
	var n := 0
	for j in rows - 1:
		for i in size.x - 1:
			if hole.size.x > 0.0 and hole.has_point(origin + Vector2(i + 0.5, j0 + j + 0.5) * step):
				continue
			var a := j * size.x + i
			idx[n] = a
			idx[n + 1] = a + 1
			idx[n + 2] = a + size.x
			idx[n + 3] = a + 1
			idx[n + 4] = a + size.x + 1
			idx[n + 5] = a + size.x
			n += 6
	idx.resize(n)
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_INDEX] = idx
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return mesh


# ------------------------------------------------------------------ trees and props
func _build_trees(which: String) -> Array:
	var trees := []
	var scenario := get_world_3d().scenario
	var first_set := _tree_xz.is_empty()
	for t: Dictionary in layout["trees"]:
		var p: Array = t["p"]
		var model: String = t[which]
		var xf := Transform3D(Basis(Vector3.UP, t["r"]).scaled(Vector3.ONE * float(t["s_" + which])), Vector3(p[0], p[1], p[2]))
		if first_set:
			var cell := Vector2i(floori(p[0] / CELL), floori(p[2] / CELL))
			if not _tree_cells.has(cell):
				_tree_cells[cell] = []
			(_tree_cells[cell] as Array).append(_tree_xz.size())
			_tree_xz.append(Vector2(p[0], p[2]))
		# old trees: one instance; portfolio trees: full, mid and far versions, and one more that casts the shadow;
		# young spruces: the mid and far versions, which are fine for something that small
		var kind := "old"
		if Models.has(model + "_1"):
			kind = "young" if t["kind"] == "YoungSpruce" else "full"
		var count: int = {"old": 1, "young": 2, "full": 3}[kind]
		var tree := {"model": model, "kind": kind, "draw": [], "shadow": RID()}
		for i in count:
			var rid := RenderingServer.instance_create2(Models.mesh(model).get_rid(), scenario)
			RenderingServer.instance_set_transform(rid, xf)
			(tree["draw"] as Array).append(rid)
		if kind == "full":
			tree["shadow"] = RenderingServer.instance_create2(Models.mesh(model).get_rid(), scenario)
			RenderingServer.instance_set_transform(tree["shadow"], xf)
		trees.append(tree)
	return trees


## Point every tree of the shown set at the versions the settings ask for, with their distances and shadows.
func _apply_trees() -> void:
	var t_ := "_t" if trimmed else ""
	for tree: Dictionary in _tree_sets[_current]:
		var draw: Array = tree["draw"]
		var m: String = tree["model"]
		var names: Array
		match tree["kind"]:
			"old":
				names = [m]
			"young":
				names = [m + "_1" + t_, m + "_2" + t_]
			_:
				names = [m + ("_f" if fewer else "") + t_, m + "_1" + t_, m + "_2" + t_]
		if tree_lod > 0 and tree["kind"] != "old":
			names = names.map(func(_n: String) -> String: return m + "_%d" % tree_lod + t_)
		var ranges: Array = [[0.0, 0.0]] if names.size() == 1 else ([[0.0, lod_far], [lod_far, 0.0]] if names.size() == 2
			else [[0.0, lod_near], [lod_near, lod_far], [lod_far, 0.0]])
		for i in draw.size():
			var rid: RID = draw[i]
			RenderingServer.instance_set_base(rid, Models.mesh(names[i]).get_rid())
			RenderingServer.instance_geometry_set_visibility_range(rid, ranges[i][0], ranges[i][1],
				LOD_MARGIN if i > 0 else 0.0, LOD_MARGIN if i < draw.size() - 1 else 0.0,
				RenderingServer.VISIBILITY_RANGE_FADE_DISABLED)  # a dithered cross-fade leaves black holes with alpha-cut leaves
			RenderingServer.instance_geometry_set_cast_shadows_setting(rid, RenderingServer.SHADOW_CASTING_SETTING_ON
				if _casts_shadow(tree, i) else RenderingServer.SHADOW_CASTING_SETTING_OFF)
			RenderingServer.instance_set_visible(rid, true)
		var shadow: RID = tree["shadow"]
		if shadow.is_valid():
			# the full version's shadow comes from a lighter one, drawn into the shadow map only
			var use := tree_shadows in ["mid", "far"]
			RenderingServer.instance_set_visible(shadow, use)
			if use:
				var far := tree_shadows == "far"
				RenderingServer.instance_set_base(shadow, Models.mesh(m + ("_2" if far else "_1") + t_).get_rid())
				RenderingServer.instance_geometry_set_visibility_range(shadow, 0.0, lod_near, 0.0, LOD_MARGIN,
					RenderingServer.VISIBILITY_RANGE_FADE_DISABLED)
				RenderingServer.instance_geometry_set_cast_shadows_setting(shadow, RenderingServer.SHADOW_CASTING_SETTING_SHADOWS_ONLY)
				if far:  # the mid version's own shadow comes from the lightest too
					RenderingServer.instance_geometry_set_cast_shadows_setting(draw[1], RenderingServer.SHADOW_CASTING_SETTING_OFF)
					RenderingServer.instance_geometry_set_visibility_range(shadow, 0.0, lod_far, 0.0, LOD_MARGIN,
						RenderingServer.VISIBILITY_RANGE_FADE_DISABLED)


func _instances(tree: Dictionary) -> Array:
	var out: Array = (tree["draw"] as Array).duplicate()
	if (tree["shadow"] as RID).is_valid():
		out.append(tree["shadow"])
	return out


func _exit_tree() -> void:
	for set: Array in _tree_sets.values():
		for tree: Dictionary in set:
			for rid: RID in _instances(tree):
				RenderingServer.free_rid(rid)


func _build_props() -> void:
	var root := Node3D.new()
	root.name = "Props"
	add_child(root)
	for model: String in layout["props"]:
		var groups := {}
		for it: Array in layout["props"][model]:
			var xf := Transform3D(Basis(Vector3.UP, it[3]).scaled(Vector3.ONE * it[4]), Vector3(it[0], it[1], it[2]))
			var key := Vector2i(floori(it[0] / CHUNK), floori(it[2] / CHUNK))
			if not groups.has(key):
				groups[key] = []
			(groups[key] as Array).append(xf)
		var small := model.begins_with("Pebble") or model.begins_with("Grass") or model.begins_with("Lichen")
		var plant := small or model.begins_with("Shrub") or model.begins_with("Blueberry") or model.begins_with("Lingonberry") or model.begins_with("TallGrass")
		for key: Vector2i in groups:
			var mmi := _add_multimesh(root, model, groups[key], key, CHUNK, PLANT_RANGE if small else 0.0)
			if plant and not plant_shadows:
				mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF


func _add_multimesh(parent: Node3D, model: String, xforms: Array, chunk: Vector2i, size: float, range_end: float) -> MultiMeshInstance3D:
	var centre := Vector3((chunk.x + 0.5) * size, 0.0, (chunk.y + 0.5) * size)
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = Models.mesh(model)
	mm.instance_count = xforms.size()
	for i in xforms.size():
		var xf: Transform3D = xforms[i]
		xf.origin -= centre
		mm.set_instance_transform(i, xf)
	var mmi := MultiMeshInstance3D.new()
	mmi.multimesh = mm
	mmi.position = centre
	if range_end > 0.0:
		mmi.visibility_range_end = range_end
		mmi.visibility_range_end_margin = 10.0
		mmi.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
	parent.add_child(mmi)
	return mmi


# ------------------------------------------------------------------ colliders
func _build_solids() -> void:
	var body := StaticBody3D.new()
	body.name = "Solids"
	body.collision_layer = LAYER_SOLID
	add_child(body)
	for s: Array in layout["solids"]:
		var shape := CylinderShape3D.new()
		shape.radius = s[3]
		shape.height = s[4] + 1.0
		var cs := CollisionShape3D.new()
		cs.shape = shape
		cs.position = Vector3(s[0], s[1] + s[4] * 0.5 - 0.5, s[2])
		body.add_child(cs)


## Invisible walls round the walkable area; the forest beyond them hides the edge.
func _build_walls() -> void:
	var body := StaticBody3D.new()
	body.name = "Walls"
	body.collision_layer = LAYER_SOLID
	add_child(body)
	var pts: Array = layout["boundary"]
	for i in pts.size():
		var a := Vector2(pts[i][0], pts[i][1])
		var b := Vector2(pts[(i + 1) % pts.size()][0], pts[(i + 1) % pts.size()][1])
		var mid := (a + b) * 0.5
		var shape := BoxShape3D.new()
		shape.size = Vector3(a.distance_to(b) + 0.6, 12.0, 0.6)
		var cs := CollisionShape3D.new()
		cs.shape = shape
		cs.position = Vector3(mid.x, height_at(mid.x, mid.y) + 4.0, mid.y)
		cs.rotation.y = -(b - a).angle()
		body.add_child(cs)
