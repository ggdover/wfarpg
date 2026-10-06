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
var _tree_sets := {}  # "old"/"new" -> Array of trees: {model, kind, draw: [instances], shadow: instance or none,
		# bound: how far it reaches from its trunk, its bottom and its top where it stands, inv: its transform's inverse}
var _tree_xz := PackedVector2Array()
var _tree_y := PackedFloat32Array()
var _tree_cells := {}  # Vector2i -> tree indices, for finding the trees near the camera
var _skipped := {}  # tree index -> true while the tree is faded out near the camera
var _sight := {}  # tree index -> how far it has faded out of the way between the camera and the hero, 0..1
var _clear_for := {}  # tree index -> seconds since it was last in the way
var _undrawn := {}  # tree index -> true while the tree isn't drawn (faded out near the camera or out of the way)
var _bounds := {}  # model -> Vector3(how far it reaches from the trunk, bottom, top), unscaled
var _occluders := {}  # model version -> its shape as a TriangleMesh, for finding whether it's in the way (_occluder)
var _profiles := {}  # model -> how far it reaches from its trunk in each of BANDS slices up it (_profile)
var _samples := {}  # model -> a few hundred of its points, for how near it comes to the camera (_samples_of)
const SAMPLES := 300
var _xray := 0.0  # the x-ray as the shaders have it (xray_on)
var _trunks := {}  # tree index -> how far its bare trunk has faded out, 0..1, while it's drawn (_leave)
var _stumped := {}  # tree index -> true while its stump is drawn
var _reach := 0.0  # the fade near the camera as the shaders have it (xray_near)
var _cone := 0.0  # how strongly the cone is on, as the shaders have it (cone_shape.w)
var _veiled := {}  # tree index -> how see-through it is, 0..veil_amount, with "veil" (sight_veil in the shaders)
var _covering := {}  # tree index -> seconds since it last covered some of the area round the hero (_measure_area)
var _cover := 0.0  # how much of the area round the hero the trees cover, 0..1, as last measured
var _veil_for := INF  # seconds since the trees last covered veil_cover of the area
var _area_age := INF  # seconds since the area was last measured
var _coverers := {}  # model version -> its shape as drawn, as a TriangleMesh, for how much of the area it covers
## the area round the hero, as last measured (for scripts/sight_area.gd): its outline, the points across it that lines
## from the camera were tested to, and which of those some tree covers (1) or not (0)
var area_outline := PackedVector3Array()
var area_points := PackedVector3Array()
var area_covered := PackedByteArray()
var _max_reach := 0.0
var _current := ""
const CELL := 8.0
const SIGHT_OUT := 0.15  # seconds a tree in the way takes to fade out
const SIGHT_IN := 0.45  # and to fade back
const SIGHT_HOLD := 0.35  # seconds it stays out of the way after it no longer is
# The hero as the camera sees it, for finding the trees in the way (_hero_points): its outline this far either side of
# its middle (m), and this much beyond its top and bottom. A tree out of the way stays out while it's in the way of a
# bigger hero, so it doesn't flicker as the lines brush its edge.
const HERO_HALF := 0.42
const HERO_PAD := 0.08
const KEEP_HALF := 1.0
const KEEP_PAD := 0.6
const NEAR_GONE := 1.0  # metres from the camera within which trees have faded out anyway (tree_fade in common.gdshaderinc)
const AREA_KEEP := 0.04  # a tree that's gone comes back once it's this far out of the area (a fraction of the screen)
const AREA_BELOW := 0.5  # the area reaches this far below the screen (a fraction of it), so trees coming into view
		# from below as the hero walks towards the camera are stumps already
const BANDS := 6  # slices up a tree, for finding whether any part of it is in the area (_profile)
const XRAY_EDGE := 0.07  # how soft the x-ray's edges are, a fraction of the screen's height
const XRAY_CORNER := 0.12  # how round its top corners
const STANDS := 2.0  # where a tree stands, for the area: its foot and this much of its trunk (metres). Its whole
		# trunk would count tall trees beside the area, as seen from above their trunks lean in towards the screen's
		# middle as they rise
const HERO_BODY := 0.3  # the hero's own half width (m)
const VEIL_HOLD := 0.1  # seconds the trees stay see-through after they no longer cover enough of the area
const VEIL_STAY := 0.8  # once see-through, the trees stay so until they cover less than this share of veil_cover
		# (72% of the area for the user's 90%), so that they don't flicker while what they cover hovers round veil_cover
const VEIL_FADE := 0.15  # seconds a tree takes to go see-through, and back
const COVER_HOLD := 0.25  # seconds a tree that's see-through stays so after it last covered some of the area
const KEEP_MARGIN := 1.5  # with veil_keep, a hidden tree comes back as one of those nearest the hero only once it's
		# this much nearer it (m) than one kept, so two about as near don't keep swapping
const AREA_COLUMNS := 5  # the points across the area that lines from the camera are tested to: a grid this wide
const AREA_ROWS := 7  # and this high, those inside its rounded outline
const AREA_EVERY := 1.0 / 30.0  # seconds between measurements of the area

var _ground_materials := {}  # detail level -> its material (shaders/ground*.gdshader)
var _ground_meshes: Array[MeshInstance3D] = []
var ground_detail := 4
## how far the paths' wear spreads into the grass: 0 as in the mockups, 1 the widest (wear_spread in the ground shader)
var path_wear := 1.0
const GROUND_SHADERS := {3: "res://shaders/ground.gdshader", 2: "res://shaders/ground_medium.gdshader",
	1: "res://shaders/ground_low.gdshader", 0: "res://shaders/ground_flat.gdshader", 4: "res://shaders/ground_baked.gdshader"}
const BAKED := 4  ## the ground detail level that reads High's details from textures baked at startup (scripts/ground_detail.gd)
var _baked_ready := false

# How the new trees are drawn; set them with set_trees().
## leaf cards cut down from their squares to the outline round their leaves (looks the same, fewer pixels to draw)
var trimmed := true
## about half the leaf cards per clump (changes the look)
var fewer := false
## what casts a tree's shadow: a version of it, "full", "mid" (the first lighter one) or "far" (the lightest), or
## "pictures" (its trunk and branches, and a picture of its leaves as the sun sees them: TreeShadowPictures), or "off"
var tree_shadows := "pictures"
## only the trees within this far of the camera cast shadows (metres; 0 for every tree)
var shadow_reach := 60.0
## where the lighter versions take over (metres from the camera)
var lod_near := 45.0
var lod_far := 120.0
## from this far off (metres; 0 for never), the new trees are drawn as impostors: one quad each, showing pictures of
## the tree baked at startup (scripts/tree_impostors.gd), instead of hundreds of overlapping leaf cards
var impostors_from := 90.0
var _impostors: TreeImpostors = null
var _impostors_baking := false
var _shadow_pictures: TreeShadowPictures = null
var _shadow_pictures_baking := false
## fade out trees near a high camera, as the mockups hide them, though never near the hero (scripts/camera_rig.gd);
## off, as trees should only go once they're in the way
var fade_near_camera := false
## which trees go, so that you can see past them (update_sight): "veil", no tree whole, but once the trees in front of
## the hero cover veil_cover of the area round it (the hero and veil_round round it, as the camera sees it), each of
## them goes evenly see-through, standing on its stump (_cut_veil); "front",
## whole, those in front of the hero in the lower middle of the screen (cut_half_width, cut_top) and any in the way of
## the hero, while those beside it or past it stay; "area", whole, those in the lower middle of the screen up to
## cut_behind past the hero too, as in Path of Exile 2, and any in the way of the hero; "line", whole, only those in the
## way of the hero; "xray", no tree whole, but whatever of a tree is in the lower middle of the screen and nearer the
## camera than the hero, cut away by the shaders (xray_fade in shaders/common.gdshaderinc); "cone", no tree whole, but
## whatever of a tree is inside a cone from the edges of the screen to the hero fades away, wholly at its middle and
## gradually towards its edges (cone_fade in shaders/common.gdshaderinc), ref_imgs/tree_disappear/camera_view.png; or
## "off". With "front" and "xray", whatever of a tree comes near the camera fades away too (cut_near). Their shadows
## stay.
var cut_trees := "veil"
## with "veil": the trees go see-through once they cover this share of the area round the hero (the user's 90%)
var veil_cover := 0.9
## the area: the hero and this far round it (m), as the camera sees it (the user's: the hero alone)
var veil_round := 0.0
## and how see-through they go: the share of what's behind them they let through (0 for never)
var veil_amount := 0.5
## draw the area on the screen, with which of the points across it the trees cover (scripts/sight_area.gd)
var show_area := false
## with "veil", deep in the forest: keep only this many see-through trees, those nearest the hero, and hide the rest
## whole, leaving only their shadows, which costs nothing to draw (0: keep them all see-through)
var veil_keep := 0
## draw the see-through trees near the camera with half their leaf cards (their thinned version, Models.thinned: the
## same cards, each where it is, but every other one, picked at random, left out; those go first as the tree goes
## see-through, so nothing shifts or pops, _thin_out): where a tree lets what's behind it through, each of its cards
## still runs its shader before it's thrown away, layer on layer, which deep in the forest with the camera low costs
## 5-10 ms a frame; with half the cards, about half
var veil_lighter := true
## what's left of a tree that goes: "trunks", its bare trunk, until that hides the hero, which takes it down to its
## stump (a spruce, whose branches reach the ground, goes to its stump straight away); "stumps"; or "nothing"
var leave := "stumps"
## the lower middle of the screen, where trees go: half its width either side of the middle, and from how far down
## its top is, as fractions of the screen's (ref_imgs/camera_disappearing_tree.png: the middle 52%, from 30% down)
var cut_half_width := 0.26
var cut_top := 0.30
## which part of a tree in the area makes it go: "trunk" (where it stands: its foot and the bottom of its trunk) or
## "any" (any part of it)
var cut_by := "trunk"
## with "area", trees beyond the hero go only this far beyond it (metres, along the ground away from the camera), so a
## low camera, which sees far past the hero, doesn't clear a lane to the horizon
var cut_behind := 6.0
## with "front" and "xray", whatever of a tree comes within this fraction of the way from the camera to the hero
## fades away (3 to 12 m from it; from 60% of that out), wherever it is on the screen, so the branches round the
## camera don't sweep across it; with leave "trunks", their trunks stay
var cut_near := 0.4
## with "front", the trees in the lower middle of the screen go only once they stand at least this far in front of the
## hero (metres, along the ground towards the camera); those beside it or past it stay, unless they hide the hero or
## come near the camera
var cut_front := 1.0
## with "cone": the share of the cone, from its edge in, where trees fade gradually, rather than wholly
var cone_soft := 0.3
## and how they fade: "dither", in a fine even dither on the screen, which reads as their opacity changing, or
## "patches", in patches a few centimetres across, like the other fades (faded_fine in shaders/common.gdshaderinc)
var cone_style := "dither"
## and how big it is round the hero, where it ends, as many times the hero's size on the screen
var cone_tip := 2.5
## and how its size goes with the depth: 1, evenly from the whole screen at the camera to round the hero; above 1, it
## stays wide further out
var cone_power := 1.0
## also keep the ground this far round the hero clear of trees in the way (metres; 0 for the hero alone)
var sight_clear := 0.0
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
	set_ground_param("canopy_tex", load("res://assets/ground/canopy_%s.png" % which))
	_build_occluders()


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
	var old := _skipped
	_skipped = now
	for i: int in old:
		if not now.has(i):
			_refresh_drawn(i)
	for i: int in now:
		if not old.has(i):
			_refresh_drawn(i)


## Fade out the trees that block the view, and fade them back once they don't; leave their trunks or stumps (leave).
## With cut_trees "veil", the trees covering enough of the area round the hero go see-through (_cut_veil); with
## "front", "area" and "line", whole trees go (_cut_whole); with "xray", the shaders cut away
## whatever of a tree is in the lower middle of the screen in front of the hero; with "cone", whatever of a tree is in
## the cone. With "front" and "xray", the shaders also fade whatever of a tree comes near the camera. What's left of the
## trees is _leave's. Called every frame by the camera rig, with how long the frame took.
func update_sight(camera: Camera3D, hero_pos: Vector3, delta: float) -> void:
	if _current == "":
		return
	var camera_pos := camera.global_position
	var xray := 1.0 if cut_trees == "xray" else 0.0
	if xray != _xray:
		_xray = xray
		RenderingServer.global_shader_parameter_set("xray_on", xray)
	var reach := clampf(cut_near * camera_pos.distance_to(hero_pos), 3.0, 12.0) if cut_near > 0.0 and cut_trees in ["front", "xray"] else 0.0
	if absf(reach - _reach) > 0.01:
		_reach = reach
		RenderingServer.global_shader_parameter_set("xray_near", Vector2(0.6 * reach, reach))
	var window := []
	if xray > 0.0:
		RenderingServer.global_shader_parameter_set("xray_rect", Vector4(cut_half_width, cut_top, XRAY_EDGE, XRAY_CORNER))
		window = _area_planes(camera, AREA_KEEP)
	elif cut_trees == "veil":
		_cut_veil(camera, hero_pos, delta)
	elif cut_trees != "off" and cut_trees != "cone":
		_cut_whole(camera, hero_pos, delta)
	var cone := 1.0 if cut_trees == "cone" else 0.0
	if cone > 0.0:
		_update_cone(camera, hero_pos, cone)
	elif _cone > 0.0:
		RenderingServer.global_shader_parameter_set("cone_shape", Vector4(1.0, cone_soft, cone_power, 0.0))
	_cone = cone
	_leave(camera, hero_pos, delta, reach, window)


## The cone (cut_trees "cone"): where the hero is on the screen, how big (cone_tip times its size there), how far from
## the camera, and how strongly it's on, for cone_fade in the shaders.
func _update_cone(camera: Camera3D, hero_pos: Vector3, strength: float) -> void:
	var size := camera.get_viewport().get_visible_rect().size
	var r := Rect2(camera.unproject_position(hero_pos), Vector2.ZERO)
	for c in 8:
		r = r.expand(camera.unproject_position(hero_pos + Vector3(0.4 if c & 1 else -0.4, 1.8 if c & 2 else 0.0, 0.4 if c & 4 else -0.4)))
	var centre := r.get_center() / size
	var half := r.size * 0.5 * cone_tip / size
	var depth := -(camera.global_transform.affine_inverse() * (hero_pos + Vector3(0.0, 0.9, 0.0))).z
	RenderingServer.global_shader_parameter_set("cone_hero", Vector4(centre.x, centre.y, half.x, half.y))
	RenderingServer.global_shader_parameter_set("cone_shape", Vector4(maxf(depth, 0.5), cone_soft, cone_power, strength))
	RenderingServer.global_shader_parameter_set("cone_style", 1.0 if cone_style == "dither" else 0.0)


## Fade out whole the trees that block the view, and fade them back once they don't. With cut_trees "front", those in
## front of the hero in the lower middle of the screen (_in_area); with "area", those in the lower middle of the screen
## up to cut_behind past the hero, as Path of Exile 2 cuts its trees. With every one of them, any tree in the way of the
## hero: once some part of it, a leaf card, a branch or the trunk, is on a line from the camera to the hero (or to the
## ground sight_clear metres round them), and not before.
func _cut_whole(camera: Camera3D, hero_pos: Vector3, delta: float) -> void:
	var camera_pos := camera.global_position
	var points := _hero_points(camera_pos, hero_pos, HERO_HALF, HERO_PAD)  # on the hero, for the trees not yet gone
	var keep := _hero_points(camera_pos, hero_pos, KEEP_HALF, KEEP_PAD)  # on a wider hero, for those that are
	var area := []  # the planes round the area where trees go
	var area_keep := []  # and round a wider one, for those already gone
	var ahead := Vector2.ZERO  # along the ground, away from the camera
	var past := cut_behind if cut_trees == "area" else -cut_front  # how far past the hero trees in the area go
	if sight_clear > 0.1:
		for k in 8:
			var a := TAU * k / 8.0
			var p := hero_pos + Vector3(cos(a), 0.0, sin(a)) * sight_clear + Vector3(0, 0.3, 0)
			points.append(p)
			keep.append(p)
	var reach := _max_reach + KEEP_HALF + KEEP_PAD + sight_clear + 1.0
	var lo := Vector2(minf(camera_pos.x, hero_pos.x) - reach, minf(camera_pos.z, hero_pos.z) - reach)
	var hi := Vector2(maxf(camera_pos.x, hero_pos.x) + reach, maxf(camera_pos.z, hero_pos.z) + reach)
	if cut_trees == "area" or cut_trees == "front":
		area = _area_planes(camera, 0.0)
		area_keep = _area_planes(camera, AREA_KEEP)
		var b := camera.global_basis
		ahead = Vector2(-b.z.x + b.y.x, -b.z.z + b.y.z).normalized()  # from above too, where the screen's up is
		for g: Vector2 in _area_on_ground(camera, hero_pos, past):
			lo = lo.min(g - Vector2.ONE * (_max_reach + 1.0))
			hi = hi.max(g + Vector2.ONE * (_max_reach + 1.0))
	var check := {}
	for cx in range(floori(lo.x / CELL), floori(hi.x / CELL) + 1):
		for cz in range(floori(lo.y / CELL), floori(hi.y / CELL) + 1):
			for i: int in _tree_cells.get(Vector2i(cx, cz), []):
				check[i] = true
	for i: int in _sight:
		check[i] = true
	var trees: Array = _tree_sets[_current]
	for i: int in check:
		var f: float = _sight.get(i, 0.0)
		var tree: Dictionary = trees[i]
		var in_way := (not area.is_empty() and _in_area(tree, i, area_keep if f > 0.0 else area, hero_pos, ahead, past + (1.0 if f > 0.0 else 0.0))) \
			or _in_way(tree, i, camera_pos, hero_pos, keep if f > 0.0 else points)
		_fade_whole(i, tree, f, in_way, delta)


## Fade the tree out whole while it's in the way, and back once it hasn't been for SIGHT_HOLD; f is how far it had
## faded. Returns how far it has now.
func _fade_whole(i: int, tree: Dictionary, f: float, in_way: bool, delta: float) -> float:
	if not in_way and f == 0.0:
		return 0.0
	var was := f
	if in_way:
		_clear_for[i] = 0.0
		f = minf(f + delta / SIGHT_OUT, 1.0)
	else:
		var t: float = _clear_for.get(i, 0.0) + delta
		_clear_for[i] = t
		if t > SIGHT_HOLD:
			f = maxf(f - delta / SIGHT_IN, 0.0)
	if f != was:
		for rid: RID in tree["draw"]:
			RenderingServer.instance_geometry_set_shader_parameter(rid, "sight_fade", f)
	if f > 0.0:
		_sight[i] = f
	else:
		_sight.erase(i)
		_clear_for.erase(i)
	if (f >= 1.0) != (was >= 1.0):
		_refresh_drawn(i)
	return f


## With cut_trees "veil": measure how much of the area round the hero the trees in front of it cover, now and then
## (_measure_area); while that's veil_cover or more, each tree covering some of it goes evenly see-through, standing on
## its stump (_leave), over VEIL_FADE, and back once it no longer does (after COVER_HOLD), or once they cover less than
## VEIL_STAY of veil_cover (after VEIL_HOLD). With veil_keep, only that many of them stay see-through, those nearest the
## hero, and the rest go whole (_fade_whole), leaving nothing but their shadows; otherwise no tree goes whole.
func _cut_veil(camera: Camera3D, hero_pos: Vector3, delta: float) -> void:
	_area_age += delta
	for i: int in _covering:
		_covering[i] += delta
	if _area_age >= AREA_EVERY:
		_area_age = 0.0
		_measure_area(camera, hero_pos)
	var veiling := _veil_for <= VEIL_HOLD
	_veil_for = 0.0 if veil_amount > 0.0 and _cover >= veil_cover * (VEIL_STAY if veiling else 1.0) else _veil_for + delta
	veiling = _veil_for <= VEIL_HOLD
	var trees: Array = _tree_sets[_current]
	var all := _covering.duplicate()
	all.merge(_veiled)
	var keeping := []  # the trees going or gone see-through, for veil_keep
	for i: int in all:
		var covers: bool = _covering.get(i, INF) <= COVER_HOLD
		if not covers:
			_covering.erase(i)
		elif veiling:
			keeping.append(i)
		var v: float = _veiled.get(i, 0.0)
		var was := v
		v = move_toward(v, veil_amount if veiling and covers else 0.0, delta * maxf(veil_amount, 0.1) / VEIL_FADE)
		if v != was:
			# its stump (_leave) stands in for its foot, so all its bark goes see-through: kept solid up to the cut, it
			# would stand above the stump's slanted top on its low side
			var solid: float = 0.0 if Models.has(trees[i]["model"] + "_stump") else trees[i]["cut"]
			for rid: RID in trees[i]["draw"]:
				RenderingServer.instance_geometry_set_shader_parameter(rid, "sight_veil", Vector2(v, solid))
			_thin_out(trees[i], v)
		if v > 0.0:
			_veiled[i] = v
		else:
			_veiled.erase(i)
	# with veil_keep, all but the see-through trees nearest the hero go whole, and come back once they don't cover it
	var hide := {}
	if veil_keep > 0 and keeping.size() > veil_keep:
		var hero2 := Vector2(hero_pos.x, hero_pos.z)
		keeping.sort_custom(func(a: int, b: int) -> bool:
			return _tree_xz[a].distance_to(hero2) + (KEEP_MARGIN if _sight.has(a) else 0.0) \
				< _tree_xz[b].distance_to(hero2) + (KEEP_MARGIN if _sight.has(b) else 0.0))
		for k in range(veil_keep, keeping.size()):
			hide[keeping[k]] = true
	var fading := hide.duplicate()
	fading.merge(_sight)
	for i: int in fading:
		_fade_whole(i, trees[i], _sight.get(i, 0.0), hide.has(i), delta)


## Are the trees covering the area round the hero see-through (or going so) now? Then they stay so until they cover less
## than VEIL_STAY of veil_cover (for scripts/sight_area.gd).
func veil_on() -> bool:
	return _veil_for <= VEIL_HOLD


## With veil_lighter, thin out a portfolio tree's leaf cards near the camera as it goes see-through (v, 0..veil_amount):
## the cards its thinned version leaves out (Models.thinned) go see-through faster than the rest (sight_thin in
## shaders/leaves.gdshader), and once they've gone, as the tree is as see-through as it goes, it's drawn as that
## version, which looks the same; going back, the other way round. Its other cards stay as they are.
func _thin_out(tree: Dictionary, v: float) -> void:
	var m: String = tree["names"][0]
	if not veil_lighter or tree["kind"] != "full" or not Models.thinnable(m):
		return
	var rid: RID = tree["draw"][0]
	RenderingServer.instance_geometry_set_shader_parameter(rid, "sight_thin", minf(v / maxf(veil_amount, 0.01), 1.0))
	var thin := v > 0.0 and v >= veil_amount
	if thin != tree.get("light", false):
		tree["light"] = thin
		RenderingServer.instance_set_base(rid, (Models.thinned(m) if thin else Models.mesh(m)).get_rid())


## How much of the area round the hero the trees in front of it cover (_cover), and which of them cover some of it
## (_covering). The area is the hero as the camera sees it, on a plane through its middle that faces the camera
## (HERO_BODY either side of the middle, and its height, or from above its footprint), and veil_round round that, its
## corners rounded; lines from the camera go to a grid of points across it (AREA_COLUMNS by AREA_ROWS), and a point is
## covered if some tree's shape as drawn (_coverer), leaves, branches or trunk, is on its line. Each line stops at the
## first tree on it, but each tree is tested till it's found on one, so that one behind another counts too.
func _measure_area(camera: Camera3D, hero_pos: Vector3) -> void:
	var camera_pos := camera.global_position
	var centre := hero_pos + Vector3(0.0, 0.9, 0.0)
	var view := (centre - camera_pos).normalized()
	var side := view.cross(Vector3.UP)
	side = side.normalized() if side.length() > 0.001 else Vector3.RIGHT
	var up := side.cross(view)  # up the screen
	var steep := absf(view.y)  # 0 looking along the ground, 1 straight down
	var r := veil_round
	var half := Vector2(HERO_BODY, 0.9 * sqrt(1.0 - steep * steep) + 0.36 * steep) + Vector2(r, r)
	area_points.clear()
	for row in AREA_ROWS:
		for col in AREA_COLUMNS:
			var a := (2.0 * (col + 0.5) / AREA_COLUMNS - 1.0) * half.x
			var b := (2.0 * (row + 0.5) / AREA_ROWS - 1.0) * half.y
			var q := Vector2(absf(a), absf(b)) - (half - Vector2(r, r))
			if q.x > 0.0 and q.y > 0.0 and q.length() > r:
				continue  # in a rounded-off corner
			area_points.append(centre + side * a + up * b)
	area_outline.clear()
	for k in 4:  # round the corners, anticlockwise from the top right
		var sx := 1.0 if k == 0 or k == 3 else -1.0
		var sy := 1.0 if k < 2 else -1.0
		for j in 7:
			var t := (k + j / 6.0) * PI * 0.5
			var o := Vector2(sx * (half.x - r), sy * (half.y - r)) + Vector2(cos(t), sin(t)) * r
			area_outline.append(centre + side * o.x + up * o.y)
	var n := area_points.size()
	area_covered.resize(n)
	area_covered.fill(0)
	var cam2 := Vector2(camera_pos.x, camera_pos.z)
	var hero2 := Vector2(hero_pos.x, hero_pos.z)
	var reach := _max_reach + half.x + 1.0
	var lo := cam2.min(hero2) - Vector2.ONE * reach
	var hi := cam2.max(hero2) + Vector2.ONE * reach
	var trees: Array = _tree_sets[_current]
	for cx in range(floori(lo.x / CELL), floori(hi.x / CELL) + 1):
		for cz in range(floori(lo.y / CELL), floori(hi.y / CELL) + 1):
			for i: int in _tree_cells.get(Vector2i(cx, cz), []):
				var tree: Dictionary = trees[i]
				var c := _tree_xz[i]
				var bound: Vector3 = tree["bound"]
				if Geometry2D.get_closest_point_to_segment(c, hero2, cam2).distance_to(c) > bound.x + half.length() + 0.5:
					continue
				var y := _tree_y[i]
				var inv: Transform3D = tree["inv"]
				var shape: TriangleMesh = null
				var found := false
				for k in n:
					if found and area_covered[k]:
						continue  # nothing more to learn from this line
					var p := area_points[k]
					var from := camera_pos + (p - camera_pos).normalized() * NEAR_GONE
					if not _through(p, from, c.x, c.y, bound.x, y + bound.y, y + bound.z):
						continue
					if shape == null:
						shape = _coverer(tree)
					if not shape.intersect_segment(inv * from, inv * p).is_empty():
						area_covered[k] = 1
						found = true
				if found:
					_covering[i] = 0.0
	var on := 0
	for k in n:
		on += area_covered[k]
	_cover = float(on) / maxf(n, 1.0)


## A tree's shape as it's drawn near the camera (as _apply_trees picks it, with trimmed leaf cards if they are), for
## how much of the area round the hero it covers.
func _coverer(tree: Dictionary) -> TriangleMesh:
	var m: String = tree["model"]
	if tree["kind"] != "old":
		if tree_lod > 0:
			m += "_%d" % tree_lod
		elif tree["kind"] == "young":
			m += "_1"
		elif fewer:
			m += "_f"
		if trimmed and Models.has(m + "_t"):
			m += "_t"
	if not _coverers.has(m):
		_coverers[m] = Models.mesh(m).generate_triangle_mesh()
	return _coverers[m]


## What's left of the trees that go (leave): with "trunks", every tree that's gone whole (_cut_whole), whose trunk
## stands in the x-ray's window (window, with "xray"), or that comes within reach of the camera, where the shaders
## fade it, gets its bare trunk drawn in its place (<model>_trunk), which neither the x-ray nor the fade near the
## camera touch; once that trunk hides the hero, it fades out over the tree's stump. A spruce, whose branches reach the
## ground, goes to its stump straight away, as do they all with "stumps". With "veil", a see-through tree stands on its
## stump, cut top and all, while one hidden whole (veil_keep) leaves nothing.
func _leave(camera: Camera3D, hero_pos: Vector3, delta: float, reach: float, window: Array) -> void:
	var camera_pos := camera.global_position
	var check := {}
	for i: int in _sight:
		check[i] = true
	for i: int in _trunks:
		check[i] = true
	for i: int in _stumped:
		check[i] = true
	for i: int in _veiled:
		check[i] = true
	if leave != "nothing" and (not window.is_empty() or (reach > 0.0 and leave == "trunks")):
		var lo := Vector2(camera_pos.x, camera_pos.z) - Vector2.ONE * (reach + _max_reach)
		var hi := Vector2(camera_pos.x, camera_pos.z) + Vector2.ONE * (reach + _max_reach)
		if not window.is_empty():
			lo = lo.min(Vector2(hero_pos.x, hero_pos.z))
			hi = hi.max(Vector2(hero_pos.x, hero_pos.z))
			for g: Vector2 in _area_on_ground(camera, hero_pos, 2.0):
				lo = lo.min(g - Vector2.ONE * 2.0)
				hi = hi.max(g + Vector2.ONE * 2.0)
		for cx in range(floori(lo.x / CELL), floori(hi.x / CELL) + 1):
			for cz in range(floori(lo.y / CELL), floori(hi.y / CELL) + 1):
				for i: int in _tree_cells.get(Vector2i(cx, cz), []):
					check[i] = true
	var points := _hero_points(camera_pos, hero_pos, HERO_HALF, HERO_PAD)
	var trees: Array = _tree_sets[_current]
	var view := Vector2(hero_pos.x - camera_pos.x, hero_pos.z - camera_pos.z)
	for i: int in check:
		var tree: Dictionary = trees[i]
		var c := _tree_xz[i]
		var y := _tree_y[i]
		var top: float = tree["trunk_top"]
		var r: float = tree["trunk"]
		var bare := top > 0.0 and not _spruce(tree["model"])  # a tree whose bare trunk would look right
		var gone := float(_sight.get(i, 0.0)) > 0.0
		# with the x-ray: its trunk stands in the window, and not beyond the hero
		var in_window := not window.is_empty() \
			and (c - Vector2(camera_pos.x, camera_pos.z)).dot(view.normalized()) < view.length() + 2.0 \
			and _segment_in(window, Vector3(c.x, y + (tree["bound"] as Vector3).y, c.y), Vector3(c.x, y + top, c.y), r)
		var pole := leave == "trunks" and bare and (gone or in_window
			or (reach > 0.0 and _near_camera(tree, i, camera_pos, reach + (1.0 if _trunks.has(i) else 0.0))))
		var stump := leave != "nothing" and (gone or in_window) and (leave == "stumps" or not bare)
		if cut_trees == "veil":
			pole = false
			stump = _veiled.has(i) and not gone
		if pole:
			var f: float = _trunks.get(i, -1.0)
			if f < 0.0:
				f = 0.0
				_show_part(tree, "pole", true)
				RenderingServer.instance_geometry_set_shader_parameter(tree["pole"], "sight_fade", 0.0)
			# a trunk that hides the hero fades out over its stump
			var hides := false
			for p in points:
				var from := camera_pos + (p - camera_pos).normalized() * NEAR_GONE
				if _through(from, p, c.x, c.y, r + (0.15 if f > 0.0 else 0.05), y, y + top):
					hides = true
					break
			var was := f
			f = minf(f + delta / SIGHT_OUT, 1.0) if hides else maxf(f - delta / SIGHT_IN, 0.0)
			if f != was:
				RenderingServer.instance_geometry_set_shader_parameter(tree["pole"], "sight_fade", f)
			_trunks[i] = f
			stump = f > 0.0
		elif _trunks.has(i):
			_trunks.erase(i)
			_show_part(tree, "pole", false)
		if stump != _stumped.has(i):
			if stump:
				_stumped[i] = true
			else:
				_stumped.erase(i)
			_show_stump(tree, stump)


## Does the model have branches all the way down, so its bare trunk would look wrong (the spruces, old and new)?
static func _spruce(model: String) -> bool:
	return model.begins_with("NorwaySpruce") or model.begins_with("TallSpruce") or model.begins_with("YoungSpruce")


## Show the tree's bare trunk ("pole") in its place, or not, making it the first time.
func _show_part(tree: Dictionary, part: String, show: bool) -> void:
	var rid: RID = tree[part]
	if not rid.is_valid():
		var m: String = tree["model"] + "_trunk"
		if not show or not Models.has(m):
			return
		rid = RenderingServer.instance_create2(Models.mesh(m).get_rid(), get_world_3d().scenario)
		RenderingServer.instance_set_transform(rid, tree["xf"])
		RenderingServer.instance_geometry_set_cast_shadows_setting(rid, RenderingServer.SHADOW_CASTING_SETTING_OFF)  # the tree's own shadow stays
		tree[part] = rid
	RenderingServer.instance_set_visible(rid, show)


## The planes round the part of the camera's view where trees go: the screen's lower middle (cut_half_width,
## cut_top), grown by grow (a fraction of the screen) on each side, and down past the screen's bottom edge by
## AREA_BELOW. Each is [normal, offset], facing in: a point p is inside where normal.dot(p) >= offset for all four.
func _area_planes(camera: Camera3D, grow: float) -> Array:
	var size := camera.get_viewport().get_visible_rect().size
	var x0 := (0.5 - cut_half_width) * size.x - grow * size.y
	var x1 := (0.5 + cut_half_width) * size.x + grow * size.y
	var y0 := (cut_top - grow) * size.y
	var y1 := (1.0 + AREA_BELOW + grow) * size.y
	var rays: Array[Vector3] = [camera.project_ray_normal(Vector2(x0, y0)), camera.project_ray_normal(Vector2(x1, y0)),
		camera.project_ray_normal(Vector2(x1, y1)), camera.project_ray_normal(Vector2(x0, y1))]
	var mid := camera.project_ray_normal(Vector2((x0 + x1) * 0.5, (y0 + y1) * 0.5))
	var origin := camera.global_position
	var planes := []
	for k in 4:
		var n := rays[k].cross(rays[(k + 1) % 4]).normalized()
		if n.dot(mid) < 0.0:
			n = -n
		planes.append([n, n.dot(origin)])
	return planes


## Where the area's corners meet the ground at the hero's height, or for those that look over it, a point well past
## the hero: the trees to test lie round these.
func _area_on_ground(camera: Camera3D, hero_pos: Vector3, past: float) -> Array[Vector2]:
	var size := camera.get_viewport().get_visible_rect().size
	var origin := camera.global_position
	var far := Vector2(hero_pos.x - origin.x, hero_pos.z - origin.z).length() + past + 2.0
	var out: Array[Vector2] = []
	for c: Vector2 in [Vector2(0.5 - cut_half_width, cut_top), Vector2(0.5 + cut_half_width, cut_top),
			Vector2(0.5 + cut_half_width, 1.0 + AREA_BELOW), Vector2(0.5 - cut_half_width, 1.0 + AREA_BELOW)]:
		var r := camera.project_ray_normal(c * size)
		var t := (hero_pos.y - origin.y) / r.y if r.y < -0.01 else INF
		var flat := Vector2(r.x, r.z).length()
		t = minf(t, far / maxf(flat, 0.01))
		out.append(Vector2(origin.x + r.x * t, origin.z + r.z * t))
	return out


## Is the tree in the area? Where it stands, an upright line from its foot STANDS metres up its trunk, as thick as its
## trunk, is in the planes' area (cut_by "trunk"), or any of the BANDS slices up it, each a ball round the trunk as
## wide as the tree there (cut_by "any"). Only trees up to past metres past the hero count, or with past below 0, at
## least that far in front of it.
func _in_area(tree: Dictionary, i: int, planes: Array, hero_pos: Vector3, ahead: Vector2, past: float) -> bool:
	var c := _tree_xz[i]
	if (c - Vector2(hero_pos.x, hero_pos.z)).dot(ahead) > past:
		return false
	var y := _tree_y[i]
	var bound: Vector3 = tree["bound"]
	if cut_by == "trunk":
		return _segment_in(planes, Vector3(c.x, y + bound.y, c.y), Vector3(c.x, y + STANDS, c.y), tree["trunk"])
	var s: float = tree["s"]
	for band: Vector2 in _profile(tree["model"]):
		if _sphere_in(planes, Vector3(c.x, y + band.x * s, c.y), band.y * s):
			return true
	return false


## Do the tree's leaves or branches come within radius of the camera? Measured to a few hundred of its own points
## (_samples_of), in its own space.
func _near_camera(tree: Dictionary, i: int, camera_pos: Vector3, radius: float) -> bool:
	var c := _tree_xz[i]
	var bound: Vector3 = tree["bound"]
	if Vector2(camera_pos.x, camera_pos.z).distance_to(c) > radius + bound.x:
		return false
	var local: Vector3 = (tree["inv"] as Transform3D) * camera_pos
	var r := radius / float(tree["s"])
	var r2 := r * r
	for p in _samples_of(tree["model"]):
		if local.distance_squared_to(p) < r2:
			return true
	return false


## A few hundred of a model's points (SAMPLES), evenly through its vertices, in its own space: its full version's,
## which hold the lighter ones'.
func _samples_of(model: String) -> PackedVector3Array:
	if not _samples.has(model):
		var verts := PackedVector3Array()
		var m := Models.mesh(model)
		for k in m.get_surface_count():
			verts.append_array(m.surface_get_arrays(k)[Mesh.ARRAY_VERTEX])
		var out := PackedVector3Array()
		var step := maxi(1, verts.size() / SAMPLES)
		for k in range(0, verts.size(), step):
			out.append(verts[k])
		_samples[model] = out
	return _samples[model]


## Does the segment from a to b, grown by r, cross the space inside all the planes?
static func _segment_in(planes: Array, a: Vector3, b: Vector3, r: float) -> bool:
	var t0 := 0.0
	var t1 := 1.0
	for pl: Array in planes:
		var n: Vector3 = pl[0]
		var fa: float = n.dot(a) - float(pl[1]) + r
		var fb: float = n.dot(b) - float(pl[1]) + r
		if fa < 0.0 and fb < 0.0:
			return false
		if fa < 0.0:
			t0 = maxf(t0, fa / (fa - fb))
		elif fb < 0.0:
			t1 = minf(t1, fa / (fa - fb))
		if t0 > t1:
			return false
	return true


## Does the ball round c of radius r reach inside all the planes?
static func _sphere_in(planes: Array, c: Vector3, r: float) -> bool:
	for pl: Array in planes:
		if (pl[0] as Vector3).dot(c) - float(pl[1]) < -r:
			return false
	return true


## A model's shape for _in_area, unscaled: BANDS slices from its bottom to its top, each the height of its middle and
## the radius of a ball round the trunk there that holds every part of the model in the slice. From its full
## version, which holds the lighter ones.
func _profile(model: String) -> Array[Vector2]:
	if not _profiles.has(model):
		var verts := PackedVector3Array()
		var m := Models.mesh(model)
		for k in m.get_surface_count():
			verts.append_array(m.surface_get_arrays(k)[Mesh.ARRAY_VERTEX])
		var lo := INF
		var hi := -INF
		for v in verts:
			lo = minf(lo, v.y)
			hi = maxf(hi, v.y)
		var step := (hi - lo) / BANDS
		var r2 := PackedFloat32Array()
		r2.resize(BANDS)
		for v in verts:
			var k := clampi(int((v.y - lo) / step), 0, BANDS - 1)
			r2[k] = maxf(r2[k], v.x * v.x + v.z * v.z)
		var out: Array[Vector2] = []
		for k in BANDS:
			out.append(Vector2(lo + (k + 0.5) * step, sqrt(r2[k] + step * step * 0.25)))
		_profiles[model] = out
	return _profiles[model]


## Show the tree's stump in its place, or not, making it the first time.
func _show_stump(tree: Dictionary, show: bool) -> void:
	var rid: RID = tree["stump"]
	if not rid.is_valid():
		var m: String = tree["model"] + "_stump"
		if not show or not Models.has(m):
			return
		rid = RenderingServer.instance_create2(Models.mesh(m).get_rid(), get_world_3d().scenario)
		RenderingServer.instance_set_transform(rid, tree["xf"])
		RenderingServer.instance_geometry_set_cast_shadows_setting(rid, RenderingServer.SHADOW_CASTING_SETTING_OFF)  # the tree's own shadow stays
		tree["stump"] = rid
	RenderingServer.instance_set_visible(rid, show)


## A grid of points over the hero as the camera sees it, on a plane through its middle that faces the camera: four
## across, half either side of the middle, and five from its bottom edge to its top as seen from there, pad beyond
## them. From the side the outline is the hero's height; from above, its footprint.
static func _hero_points(camera_pos: Vector3, hero_pos: Vector3, half: float, pad: float) -> PackedVector3Array:
	var centre := hero_pos + Vector3(0.0, 0.9, 0.0)
	var view := (centre - camera_pos).normalized()
	var side := view.cross(Vector3.UP)
	side = side.normalized() if side.length() > 0.001 else Vector3.RIGHT
	var up := side.cross(view)  # up the screen
	var steep := absf(view.y)  # 0 looking along the ground, 1 straight down
	var tall := 0.9 * sqrt(1.0 - steep * steep) + 0.36 * steep + pad  # half the hero's 1.8 m, or its 0.72 m footprint
	var out := PackedVector3Array()
	for b: float in [-1.0, -0.5, 0.0, 0.5, 1.0]:
		for a: float in [-1.0 / 3.0, 1.0 / 3.0, -1.0, 1.0]:
			out.append(centre + side * (a * half) + up * (b * tall))
	return out


## Is some part of the tree on a line from the camera to one of the points? First the upright cylinder round it, then
## its own shape (_occluder), in its own space.
func _in_way(tree: Dictionary, i: int, camera_pos: Vector3, hero_pos: Vector3, points: PackedVector3Array) -> bool:
	var x := _tree_xz[i].x
	var z := _tree_xz[i].y
	var y := _tree_y[i]
	var bound: Vector3 = tree["bound"]
	# quick test: is the tree anywhere near the lines?
	var c := Vector2(x, z)
	var hero2 := Vector2(hero_pos.x, hero_pos.z)
	if Geometry2D.get_closest_point_to_segment(c, hero2, Vector2(camera_pos.x, camera_pos.z)).distance_to(c) \
			> bound.x + KEEP_HALF + KEEP_PAD + sight_clear + 0.5:
		return false
	var shape: TriangleMesh = null
	var inv: Transform3D = tree["inv"]
	for p in points:
		# from where the fade of what the camera is about to touch ends: nearer than that, nothing shows anyway
		var from := camera_pos + (p - camera_pos).normalized() * NEAR_GONE
		if not _through(p, from, x, z, bound.x, y + bound.y, y + bound.z):
			continue
		if shape == null:
			shape = _occluder(tree)
		if not shape.intersect_segment(inv * from, inv * p).is_empty():
			return true
	return false


## A tree's shape, for finding whether some part of it is in the way: the version drawn near the camera, as
## _apply_trees picks it, always with square leaf cards. Whatever of a card shows is inside its square, even far
## off, where the cards' smaller mipmaps can show a little outside the trimmed outlines.
func _occluder(tree: Dictionary) -> TriangleMesh:
	var m: String = tree["model"]
	if tree["kind"] != "old":
		if tree_lod > 0:
			m += "_%d" % tree_lod
		elif tree["kind"] == "young":
			m += "_1"
		elif fewer:
			m += "_f"
	if not _occluders.has(m):
		_occluders[m] = Models.mesh(m).generate_triangle_mesh()
	return _occluders[m]


## Does the segment from a to b pass through the upright cylinder of radius r round (x, z), between heights y0 and y1?
static func _through(a: Vector3, b: Vector3, x: float, z: float, r: float, y0: float, y1: float) -> bool:
	var ax := a.x - x
	var az := a.z - z
	var ux := b.x - a.x
	var uz := b.z - a.z
	var uu := ux * ux + uz * uz
	var cc := ax * ax + az * az - r * r
	var t0 := 0.0
	var t1 := 1.0
	if uu < 0.000001:
		if cc > 0.0:
			return false
	else:
		var au := ax * ux + az * uz
		var disc := au * au - uu * cc
		if disc < 0.0:
			return false
		var sq := sqrt(disc)
		t0 = maxf((-au - sq) / uu, 0.0)
		t1 = minf((-au + sq) / uu, 1.0)
		if t0 > t1:
			return false
	var ya := a.y + (b.y - a.y) * t0
	var yb := a.y + (b.y - a.y) * t1
	return maxf(ya, yb) > y0 and minf(ya, yb) < y1


## How far the tree has faded out of the way, 0..1 (for the self-test).
func sight_fade(i: int) -> float:
	return _sight.get(i, 0.0)


## The tree nearest a point, or -1 if none is within reach.
func nearest_tree(p: Vector3, reach: float) -> int:
	var best := -1
	var best_d := reach
	for i in _tree_xz.size():
		var d := _tree_xz[i].distance_to(Vector2(p.x, p.z))
		if d < best_d:
			best_d = d
			best = i
	return best


## Draw the tree or not, as its fades ask: not while it is faded out near the camera or out of the way.
func _refresh_drawn(i: int) -> void:
	var want := not (_skipped.has(i) or float(_sight.get(i, 0.0)) >= 1.0)
	if want == (not _undrawn.has(i)):
		return
	if want:
		_undrawn.erase(i)
	else:
		_undrawn[i] = true
	_draw_tree(i, want)


## Draw the version near the camera, or not; the tree's shadow comes from its own instance, so it stays either way.
func _draw_tree(i: int, draw: bool) -> void:
	RenderingServer.instance_set_visible(_tree_sets[_current][i]["draw"][0], draw)


func _unskip() -> void:
	if _current != "":
		for i: int in _undrawn:
			_draw_tree(i, true)
		for i: int in _sight:
			for rid: RID in _tree_sets[_current][i]["draw"]:
				RenderingServer.instance_geometry_set_shader_parameter(rid, "sight_fade", 0.0)
		for i: int in _trunks:
			_show_part(_tree_sets[_current][i], "pole", false)
		for i: int in _stumped:
			_show_stump(_tree_sets[_current][i], false)
		for i: int in _veiled:
			for rid: RID in _tree_sets[_current][i]["draw"]:
				RenderingServer.instance_geometry_set_shader_parameter(rid, "sight_veil", Vector2.ZERO)
			RenderingServer.instance_geometry_set_shader_parameter(_tree_sets[_current][i]["draw"][0], "sight_thin", 0.0)
			_tree_sets[_current][i]["light"] = false  # _apply_trees puts back what it draws
	_trunks.clear()
	_stumped.clear()
	_skipped.clear()
	_undrawn.clear()
	_sight.clear()
	_clear_for.clear()
	_veiled.clear()
	_covering.clear()
	_cover = 0.0
	_veil_for = INF
	_area_age = INF
	area_outline.clear()
	area_points.clear()
	area_covered.clear()


## Change how the trees are drawn, now: any of trimmed, fewer, tree_shadows, shadow_reach, lod_near, lod_far,
## impostors_from, fade_near_camera, cut_trees, leave, cut_by, cut_near.
func set_trees(option: String, value: Variant) -> void:
	_unskip()
	set(option, value)
	if cut_trees != "cone" and _cone > 0.0:  # the cone goes off now, not from the next update_sight
		RenderingServer.global_shader_parameter_set("cone_shape", Vector4(1.0, cone_soft, cone_power, 0.0))
		_cone = 0.0
	_apply_trees()
	_build_occluders()


## Work out the shown trees' shapes for update_sight now (a few tens of milliseconds), rather than the first time each
## kind of tree is near the camera, which would stall a frame.
func _build_occluders() -> void:
	for tree: Dictionary in _tree_sets[_current]:
		_occluder(tree)
		_coverer(tree)
		_profile(tree["model"])
		_samples_of(tree["model"])


## What casts the tree's shadow: the version drawn near the camera (names[0]) for "full", a lighter one for "mid" and
## "far" (old trees have no lighter ones, nor pictures), its picture for "pictures" (the mid version until they're
## baked), or nothing (null).
func _shadow_caster(tree: Dictionary, names: Array) -> Mesh:
	if tree_shadows == "off":
		return null
	if tree_shadows == "full" or tree["kind"] == "old":
		return Models.mesh(names[0])
	if tree_shadows == "pictures" and _shadow_pictures != null:
		return _shadow_pictures.meshes[tree["model"]]
	return Models.mesh(tree["model"] + ("_2" if tree_shadows == "far" else "_1") + ("_t" if trimmed else ""))


## Set a parameter of the ground shader, at every level of detail.
func set_ground_param(param: String, value: Variant) -> void:
	for mat: ShaderMaterial in _ground_materials.values():
		mat.set_shader_parameter(param, value)


## How much small detail the ground draws: 3 high, 4 high from baked textures, 2 medium, 1 low, 0 none (see
## shaders/ground.gdshaderinc). The baked level shows High until its textures are ready, a few frames in.
func set_ground_detail(level: int) -> void:
	ground_detail = level
	var use := 3 if level == BAKED and not _baked_ready else level
	for mi in _ground_meshes:
		mi.material_override = _ground_materials[use]


## How far the paths' wear spreads into the grass, 0 (the mockups') to 1.
func set_path_wear(spread: float) -> void:
	path_wear = spread
	set_ground_param("wear_spread", spread)


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
	for level: int in GROUND_SHADERS:  # the same ground at each level of small detail, to switch between
		var mat := ShaderMaterial.new()
		mat.shader = load(GROUND_SHADERS[level])
		_ground_materials[level] = mat
	set_ground_param("grass_tex", load("res://assets/ground/grass.jpg"))
	set_ground_param("path_noise_tex", load("res://assets/ground/path_noise.png"))
	set_ground_param("masks_tex", load("res://assets/ground/masks.png"))
	set_ground_param("bounds", Vector4(b[0], b[1], b[2], b[3]))
	set_ground_param("wear_spread", path_wear)
	GroundDetail.bake(self, func(layer: String, tex: Texture2D) -> void:
		_ground_materials[BAKED].set_shader_parameter(layer, tex)
		if layer == GroundDetail.LAYERS[-1]:
			_baked_ready = true
			set_ground_detail(ground_detail))
	# the detailed ground, in strips so the camera can skip what it doesn't see
	var strip := 64
	for j0 in range(0, _size.y - 1, strip):
		var mi := MeshInstance3D.new()
		mi.mesh = _grid_mesh(heights, _size, _origin, _grid, j0, mini(j0 + strip, _size.y - 1), Rect2())
		mi.material_override = _ground_materials[ground_detail]
		_ground_meshes.append(mi)
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
			_tree_y.append(p[1])
		# the versions it's drawn in (old trees: one; portfolio trees: full, mid and far; young spruces: the mid and far
		# versions, which are fine for something that small), and one more that casts its shadow
		var kind := "old"
		if Models.has(model + "_1"):
			kind = "young" if t["kind"] == "YoungSpruce" else "full"
		var count: int = {"old": 1, "young": 2, "full": 3}[kind]
		var s := float(t["s_" + which])
		var tree := {"model": model, "kind": kind, "draw": [], "shadow": RID(), "impostor": RID(), "stump": RID(), "pole": RID(),
			"bound": _bound(model) * s, "s": s, "trunk": _trunk(model) * s, "xf": xf, "inv": xf.affine_inverse(),
			"trunk_top": float(Models.info[model + "_trunk"]["height"]) * s if Models.has(model + "_trunk") else 0.0,
			"cut": float(Models.info[model + "_stump"]["cut"]) * s if Models.has(model + "_stump") else 0.5}
		_max_reach = maxf(_max_reach, (tree["bound"] as Vector3).x)
		for i in count:
			var rid := RenderingServer.instance_create2(Models.mesh(model).get_rid(), scenario)
			RenderingServer.instance_set_transform(rid, xf)
			(tree["draw"] as Array).append(rid)
		tree["shadow"] = RenderingServer.instance_create2(Models.mesh(model).get_rid(), scenario)
		RenderingServer.instance_set_transform(tree["shadow"], xf)
		trees.append(tree)
	return trees


## Point every tree of the shown set at the versions the settings ask for, with their distances and shadows.
func _apply_trees() -> void:
	var t_ := "_t" if trimmed else ""
	var pictures := impostors_from > 0.0 and tree_lod == 0
	if pictures and _impostors == null and not _impostors_baking:
		_bake_impostors()
	if tree_shadows == "pictures" and _shadow_pictures == null and not _shadow_pictures_baking:
		_bake_shadow_pictures()
	var far := maxf(impostors_from, lod_near + 2.0 * LOD_MARGIN)  # where the pictures take over
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
		tree["names"] = names
		var ranges: Array = [[0.0, 0.0]] if names.size() == 1 else ([[0.0, lod_far], [lod_far, 0.0]] if names.size() == 2
			else [[0.0, lod_near], [lod_near, lod_far], [lod_far, 0.0]])
		var pictured: bool = pictures and _impostors != null and tree["kind"] != "old"
		if pictured:  # the lightest version gives way to the picture
			ranges = [[0.0, far], [far, far]] if names.size() == 2 else [[0.0, lod_near], [lod_near, far], [far, far]]
		for i in draw.size():
			var rid: RID = draw[i]
			# a see-through tree thinned out (_thin_out) stays so
			var thin: bool = i == 0 and tree.get("light", false) and Models.thinnable(names[0])
			RenderingServer.instance_set_base(rid, (Models.thinned(names[0]) if thin else Models.mesh(names[i])).get_rid())
			RenderingServer.instance_geometry_set_visibility_range(rid, ranges[i][0], ranges[i][1],
				LOD_MARGIN if i > 0 else 0.0, LOD_MARGIN if i < draw.size() - 1 else 0.0,
				RenderingServer.VISIBILITY_RANGE_FADE_DISABLED)  # a dithered cross-fade leaves black holes with alpha-cut leaves
			RenderingServer.instance_geometry_set_cast_shadows_setting(rid, RenderingServer.SHADOW_CASTING_SETTING_OFF)
			RenderingServer.instance_set_visible(rid, ranges[i][0] != ranges[i][1] or ranges[i][0] == 0.0)
		var impostor: RID = tree["impostor"]
		if pictured:
			if not impostor.is_valid():
				impostor = RenderingServer.instance_create2(_impostors.meshes[m].get_rid(), get_world_3d().scenario)
				RenderingServer.instance_set_transform(impostor, tree["xf"])
				RenderingServer.instance_geometry_set_cast_shadows_setting(impostor, RenderingServer.SHADOW_CASTING_SETTING_OFF)
				tree["impostor"] = impostor
			RenderingServer.instance_geometry_set_visibility_range(impostor, far, 0.0, LOD_MARGIN, 0.0,
				RenderingServer.VISIBILITY_RANGE_FADE_DISABLED)
			RenderingServer.instance_set_visible(impostor, true)
		elif impostor.is_valid():
			RenderingServer.instance_set_visible(impostor, false)
		# the shadow comes from one more instance, drawn into the shadow map only: what tree_shadows picks, out to
		# shadow_reach from the camera
		var shadow: RID = tree["shadow"]
		var caster := _shadow_caster(tree, names)
		RenderingServer.instance_set_visible(shadow, caster != null)
		if caster != null:
			RenderingServer.instance_set_base(shadow, caster.get_rid())
			RenderingServer.instance_geometry_set_visibility_range(shadow, 0.0, shadow_reach, 0.0, LOD_MARGIN if shadow_reach > 0.0 else 0.0,
				RenderingServer.VISIBILITY_RANGE_FADE_DISABLED)
			RenderingServer.instance_geometry_set_cast_shadows_setting(shadow, RenderingServer.SHADOW_CASTING_SETTING_SHADOWS_ONLY)
	for i: int in _undrawn:  # those faded out near the camera or out of the way stay undrawn
		_draw_tree(i, false)


## How thick a tree model's trunk is at the ground (its radius, unscaled), from its stump: the model's own footprint
## counts its low branches too.
static func _trunk(model: String) -> float:
	return float(Models.info[model + "_stump"]["foot"]) if Models.has(model + "_stump") else 0.3


## How far a tree model reaches from its trunk, and its bottom and top, unscaled: round the boxes of all its versions,
## from kit.json and trees.json, so whichever is drawn is inside.
func _bound(model: String) -> Vector3:
	if not _bounds.has(model):
		var b := Vector3.ZERO
		for v: String in ["", "_1", "_2", "_f", "_t", "_1_t", "_2_t", "_f_t"]:
			if not Models.has(model + v):
				continue
			var lo: Array = Models.info[model + v]["min"]
			var hi: Array = Models.info[model + v]["max"]
			b.x = maxf(b.x, Vector2(maxf(-lo[0], hi[0]), maxf(-lo[2], hi[2])).length())
			b.y = minf(b.y, lo[1])
			b.z = maxf(b.z, hi[1])
		_bounds[model] = b
	return _bounds[model]


func _instances(tree: Dictionary) -> Array:
	var out: Array = (tree["draw"] as Array).duplicate()
	for k in ["shadow", "impostor", "stump", "pole"]:
		if (tree[k] as RID).is_valid():
			out.append(tree[k])
	return out


## Picture the new trees for their impostors (TreeImpostors), and put them to use once that's done, a frame later.
func _bake_impostors() -> void:
	_impostors_baking = true
	var models := []
	var versions := {}
	for tree: Dictionary in _tree_sets[_current]:
		var m: String = tree["model"]
		if tree["kind"] != "old" and not versions.has(m):
			models.append(m)
			versions[m] = m  # the full version, with square cards, which look the same as the trimmed ones
	if models.is_empty():
		_impostors_baking = false
		return
	var imp := TreeImpostors.new()
	await imp.bake(self, models, versions)
	_impostors = imp
	_impostors_baking = false
	_apply_trees()


## Picture the new trees' leaves for their shadows (TreeShadowPictures), from the full versions, as the day's sun
## sees them (scripts/mood.gd), and put them to use once that's done, a frame later.
func _bake_shadow_pictures() -> void:
	_shadow_pictures_baking = true
	var models := []
	var versions := {}
	for tree: Dictionary in _tree_sets[_current]:
		var m: String = tree["model"]
		if tree["kind"] != "old" and not versions.has(m):
			models.append(m)
			versions[m] = m
	if models.is_empty():
		_shadow_pictures_baking = false
		return
	var pics := TreeShadowPictures.new()
	await pics.bake(self, models, versions, -Mood.sun_direction(Mood.SUN_ROTATION.x, Mood.SUN_ROTATION.y))
	_shadow_pictures = pics
	_shadow_pictures_baking = false
	_apply_trees()


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
