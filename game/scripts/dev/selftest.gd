extends Node
## Dev: drives the demo's controls through Godot's input and checks what they do, then quits.
## godot --path game res://scenes/demo.tscn -- --selftest

var demo: Node
var results := []


func run(d: Node) -> void:
	demo = d
	var hero: Hero = demo.hero
	var rig: CameraRig = demo.rig
	await _frames(30)
	# W walks away from the camera
	var start := hero.global_position
	Input.action_press("move_forward")
	await _seconds(1.0)
	Input.action_release("move_forward")
	await _frames(5)
	var moved := hero.global_position - start
	var fwd := rig.ground_forward()
	_check("W walks away from the camera", Vector2(moved.x, moved.z).dot(Vector2(fwd.x, fwd.z)) > 4.0, "moved %.2f m" % Vector2(moved.x, moved.z).length())
	_check("the hero faces the way it walks", absf(angle_difference(hero.facing, atan2(-fwd.x, -fwd.z))) < 0.2, "facing off by %.2f rad" % angle_difference(hero.facing, atan2(-fwd.x, -fwd.z)))
	# D walks right
	start = hero.global_position
	Input.action_press("move_right")
	await _seconds(0.5)
	Input.action_release("move_right")
	await _frames(5)
	moved = hero.global_position - start
	var right := fwd.cross(Vector3.UP)
	_check("D walks to the right", Vector2(moved.x, moved.z).dot(Vector2(right.x, right.z)) > 1.5, "moved %.2f m" % moved.length())
	# right mouse button + drag orbits
	var yaw0 := rig.yaw
	var pitch0 := rig.pitch
	_mouse_button(MOUSE_BUTTON_RIGHT, true)
	var motion := InputEventMouseMotion.new()
	motion.relative = Vector2(80, -40)
	Input.parse_input_event(motion)
	await _frames(3)
	_mouse_button(MOUSE_BUTTON_RIGHT, false)
	await _frames(3)
	_check("dragging right with the right button turns the camera", absf(angle_difference(deg_to_rad(rig.yaw), deg_to_rad(yaw0 - 20.0))) < 0.01, "yaw %.1f -> %.1f" % [yaw0, rig.yaw])
	_check("dragging up lowers the camera", absf(rig.pitch - (pitch0 - 10.0)) < 0.01, "pitch %.1f -> %.1f" % [pitch0, rig.pitch])
	# the wheel zooms
	var d0 := rig.distance
	_mouse_button(MOUSE_BUTTON_WHEEL_UP, true)
	_mouse_button(MOUSE_BUTTON_WHEEL_UP, false)
	await _frames(2)
	_check("the wheel zooms in", rig.distance < d0, "distance %.1f -> %.1f" % [d0, rig.distance])
	# holding the left button: face the cursor and walk slower
	_mouse_button(MOUSE_BUTTON_LEFT, true)
	start = hero.global_position
	Input.action_press("move_back")
	await _seconds(0.5)
	Input.action_release("move_back")
	await _frames(3)
	var aim := rig.cursor_on_ground() - hero.global_position
	_check("attacking turns the hero to the cursor", absf(angle_difference(hero.facing, atan2(-aim.x, -aim.z))) < 0.25, "off by %.2f rad" % angle_difference(hero.facing, atan2(-aim.x, -aim.z)))
	_check("attacking walks slower", (hero.global_position - start).length() < 0.5 * hero.speed * 0.5 * 1.15, "%.2f m in 0.5 s" % (hero.global_position - start).length())
	_mouse_button(MOUSE_BUTTON_LEFT, false)
	await _sight_checks()
	# T swaps the trees
	var set0: String = Game.tree_set
	_key(KEY_T)
	await _frames(3)
	_check("T swaps the trees", Game.tree_set != set0, "%s -> %s" % [set0, Game.tree_set])
	# P changes the paths' colours
	var theme0: String = Game.path_theme
	_key(KEY_P)
	await _frames(3)
	_check("P changes the paths' colours", Game.path_theme != theme0, "%s -> %s" % [theme0, Game.path_theme])
	await _sight_checks()
	# the walls hold: walk west for a long time from near the west edge
	hero.global_position = Vector3(-74.0, demo.world.height_at(-74.0, 0.0) + 0.2, 0.0)
	hero.reset_physics_interpolation()
	rig.yaw = 0.0  # camera east of the hero: W walks west
	await _frames(3)
	Input.action_press("move_forward")
	await _seconds(2.0)
	Input.action_release("move_forward")
	_check("the walls keep the hero in", hero.global_position.x > -83.0, "x = %.1f" % hero.global_position.x)
	_check("the hero stays on the ground", absf(hero.global_position.y - demo.world.height_at(hero.global_position.x, hero.global_position.z)) < 0.3, "y = %.2f" % hero.global_position.y)
	var failed := results.filter(func(r: String) -> bool: return r.begins_with("FAIL"))
	for r: String in results:
		print(r)
	print("selftest: %d passed, %d failed" % [results.size() - failed.size(), failed.size()])
	demo.get_tree().quit(1 if failed.size() else 0)


## Is a portfolio tree's thinned version (Models.thinned) the same tree with fewer leaf cards? Every surface's vertices
## as its full version's, its triangles some of the full version's: THIN_KEEP of the leaf cards', and all the rest.
## Returns what's wrong, or "" if nothing is.
static func _thinned_in_place(model: String) -> String:
	var full := Models.mesh(model) as ArrayMesh
	var thin := Models.thinned(model) as ArrayMesh
	if full.get_surface_count() != thin.get_surface_count():
		return "%d surfaces, thinned %d" % [full.get_surface_count(), thin.get_surface_count()]
	for s in full.get_surface_count():
		var surface := full.surface_get_name(s)
		var fa := full.surface_get_arrays(s)
		var ta := thin.surface_get_arrays(s)
		for k in [Mesh.ARRAY_VERTEX, Mesh.ARRAY_NORMAL, Mesh.ARRAY_TEX_UV]:
			if fa[k] != ta[k]:
				return "%s: its vertices moved" % surface
		var fi: PackedInt32Array = fa[Mesh.ARRAY_INDEX]
		var ti: PackedInt32Array = ta[Mesh.ARRAY_INDEX]
		var tris := {}
		for t in range(0, fi.size(), 3):
			tris[Vector3i(fi[t], fi[t + 1], fi[t + 2])] = true
		for t in range(0, ti.size(), 3):
			if not tris.has(Vector3i(ti[t], ti[t + 1], ti[t + 2])):
				return "%s: a triangle the full tree hasn't" % surface
		var share := float(ti.size()) / maxf(fi.size(), 1.0)
		if absf(share - (Models.THIN_KEEP if surface.begins_with("Leaves") else 1.0)) > 0.02:
			return "%s: keeps %d%% of its triangles" % [surface, roundi(share * 100.0)]
	return ""


## Trees that block the view. See-through (the default): with the camera low behind a tall tree, the trees covering the
## area round the hero go see-through, all but their stumps, and none goes whole; under the bar they stay see-through
## until what they cover drops below the lower bar, and then they come back; and
## deep in the forest, where the trees cover the bar's share of the area, they go see-through. The cone: no tree is cut
## whole, and the shaders get the cone round the hero. In front of the hero: a tree between the camera and the hero
## goes, leaving its trunk or stump, and comes back once the hero has walked well past it; a tree just ahead of the hero
## stays, and so does one well beyond it, and a tall one beside it; a tree round a low camera isn't cut whole, but its
## trunk stands while the shaders fade the rest near the camera. The x-ray: a tree in front of the hero isn't cut whole,
## and its trunk stands in the window; once the trunk hides the hero, it goes, to its stump. In the lower middle of the
## screen: the tree just ahead of the hero goes too. Only those in the way of the hero ("line"): a tree 5 m ahead of the
## hero stays; with the camera low behind the tree, it's in the way and fades out, and it comes back once it isn't.
const AREA_POINTS_AT_LEAST := 25  # of the 5 by 7 grid across the area round the hero, those inside its rounded outline


func _sight_checks() -> void:
	var hero: Hero = demo.hero
	var rig: CameraRig = demo.rig
	var w: DemoWorld = demo.world
	var set := Game.tree_set
	var trees: Array = w._tree_sets[w._current]
	var tree := w.nearest_tree(hero.global_position, 15.0)
	var record: Dictionary = trees[tree]
	var away := (Vector2(hero.global_position.x, hero.global_position.z) - w._tree_xz[tree]).normalized()
	var yaw_beyond := rad_to_deg(atan2(-away.y, away.x))  # the camera beyond the hero, looking towards the tree
	# a tall tree with a trunk worth keeping (not a spruce), for the trunks
	var pole := -1
	var nearest := INF
	for i in w._tree_xz.size():
		var d := w._tree_xz[i].distance_to(Vector2(hero.global_position.x, hero.global_position.z))
		var rec: Dictionary = trees[i]
		if d < nearest and (rec["bound"] as Vector3).z > 8.0 and not DemoWorld._spruce(rec["model"]):
			nearest = d
			pole = i
	var pole_away := (Vector2(hero.global_position.x, hero.global_position.z) - w._tree_xz[pole]).normalized()
	var pole_side := Vector2(-pole_away.y, pole_away.x)
	var start := Vector2(hero.global_position.x, hero.global_position.z)
	# see-through: right behind the tall tree, the camera low beyond it, the bar low so that it alone is enough, as one
	# tree hiding a point counts
	w.set_trees("cut_trees", "veil")
	rig.yaw = fposmod(rad_to_deg(atan2(-pole_away.y, pole_away.x)) + 180.0, 360.0)
	rig.pitch = 15.0
	rig.distance = 20.0
	var bar := w.veil_cover
	var by := w.veil_by
	w.veil_cover = 0.05
	w.veil_by = "seen"
	_place_hero(w._tree_xz[pole] + pole_away * 5.0)
	await _seconds(0.6)
	var cover := w._cover
	var veil: float = w._veiled.get(pole, 0.0)
	var light: bool = trees[pole].get("light", false) or trees[pole]["kind"] != "full"  # only portfolio trees have fewer cards
	var none_whole := w._sight.is_empty()
	var on_stump: bool = w._stumped.has(pole)
	var drawn := w.area_points.size() >= AREA_POINTS_AT_LEAST and w.area_outline.size() == 28
	# the bar out of reach, but not the lower one for coming back: they stay see-through
	var below := w.veil_solid_below
	w.veil_cover = 2.0
	w.veil_solid_below = 0.05
	await _seconds(0.6)
	var held: float = w._veiled.get(pole, 0.0)
	w.veil_solid_below = 2.0  # and that out of reach too
	await _seconds(0.6)
	var after: float = w._veiled.get(pole, 0.0)
	var stump_gone: bool = not w._stumped.has(pole)
	var heavy: bool = not trees[pole].get("light", false)
	w.veil_cover = bar
	w.veil_solid_below = below
	w.veil_by = by
	_check("%s trees, see-through: the trees covering the area round the hero go see-through, on their stumps, none whole" % set,
		cover > 0.0 and veil >= w.veil_amount and none_whole and on_stump and drawn,
		"they cover %d%% of it, the tree see-through %.2f, %s, %s" % [roundi(cover * 100.0), veil, "on its stump" if on_stump else "no stump",
			"none cut whole" if none_whole else "some cut whole"])
	_check("%s trees, see-through: under the bar but over the lower one, they stay see-through" % set, held >= w.veil_amount,
		"see-through %.2f" % held)
	# a tree standing alone stays solid, as the defaults count only what two trees or more hide: the big pine on the
	# meadow, the camera high beyond it, the hero right behind it
	rig.yaw = 200.0
	rig.pitch = 55.0
	rig.distance = 20.0
	_place_hero(Vector2(31.9, -18.7))
	await _seconds(0.6)
	var alone_solid := w._veiled.is_empty()
	var alone_two := w._cover
	w.veil_by = "seen"  # what it hides alone
	w._measure_area(rig.camera, demo.hero.global_position)
	var alone_one := w._cover
	w.veil_by = by
	await _seconds(0.3)
	_check("%s trees, see-through: a tree alone stays solid, though it hides some of the area round the hero" % set,
		alone_solid and alone_one > 0.1,
		"it alone hides %d%% of the area, two trees %d%%; %s" % [roundi(alone_one * 100.0), roundi(alone_two * 100.0), "solid" if alone_solid else "see-through"])
	_check("%s trees, see-through: below the lower bar, they come back, their stumps gone" % set, after == 0.0 and stump_gone,
		"see-through %.2f, %s" % [after, "stump gone" if stump_gone else "stump still there"])
	_check("%s trees, see-through: drawn with fewer cards while see-through, and all of them again after" % set, light and heavy,
		"%s, then %s" % ["fewer" if light else "all", "all" if heavy else "fewer"])
	if trees[pole]["kind"] == "full":  # the portfolio's trees: the fewer cards are some of its cards, each where it was
		var moved := _thinned_in_place(trees[pole]["names"][0])
		_check("%s trees, see-through: the cards a see-through tree keeps stay where they were" % set, moved == "",
			moved if moved else "%s keeps %d%% of its leaf cards, none moved" % [trees[pole]["names"][0], roundi(Models.THIN_KEEP * 100.0)])
	# deep in the forest, the camera low: somewhere the trees cover enough of the area, and those go see-through
	rig.pitch = 20.0
	rig.distance = 25.0
	var deep := 0.0
	var thinned := 0
	for k in 24:
		_place_hero(start + Vector2(cos(k * 2.4), sin(k * 2.4)) * (4.0 + k * 1.5))
		await _seconds(0.3)
		if w._cover >= w.veil_cover:
			await _seconds(0.3)
			deep = w._cover
			thinned = w._veiled.values().filter(func(g: float) -> bool: return g >= w.veil_amount).size()
			if thinned >= 2 or k == 23:
				break
	_check("%s trees, see-through: deep in the forest, the trees covering the area go see-through" % set, deep >= w.veil_cover and thinned > 0,
		"they cover %d%%, %d see-through" % [roundi(deep * 100.0), thinned])
	# there, keeping only the one nearest the hero see-through, on its stump: the others go whole, leaving nothing, and come back
	w.veil_keep = 1
	await _seconds(0.6)
	var hero2 := Vector2(hero.global_position.x, hero.global_position.z)
	var kept_now: Array = w._veiled.keys().filter(func(i: int) -> bool: return not w._sight.has(i))
	var hid: Array = w._sight.keys().filter(func(i: int) -> bool: return w._sight[i] >= 1.0)
	var hid_bare := hid.all(func(i: int) -> bool: return not w._stumped.has(i) and not w._trunks.has(i)) \
		and kept_now.all(func(i: int) -> bool: return w._stumped.has(i))
	var nearest_kept := kept_now.size() == 1 and hid.all(func(i: int) -> bool:
		return w._tree_xz[i].distance_to(hero2) + DemoWorld.KEEP_MARGIN >= w._tree_xz[kept_now[0]].distance_to(hero2))
	w.veil_keep = 0
	await _seconds(1.2)
	var all_back := w._sight.is_empty()
	_check("%s trees, see-through: keeping the nearest see-through, the others go, leaving nothing, and come back" % set,
		thinned < 2 or (hid.size() == thinned - 1 and hid_bare and nearest_kept and all_back),
		"%d see-through: %d kept, %d gone%s, then %s" % [thinned, kept_now.size(), hid.size(), ", leaving nothing" if hid_bare else ", leaving something",
			"back" if all_back else "still gone"])
	# the cone
	w.set_trees("cut_trees", "cone")
	_place_hero(w._tree_xz[tree] + away * 4.0)
	rig.yaw = fposmod(yaw_beyond + 180.0, 360.0)  # beyond the tree: it stands between the camera and the hero
	rig.pitch = 55.0
	rig.distance = 20.0
	await _seconds(0.6)
	var whole_cone := w.sight_fade(tree)
	var nothing_left := not w._trunks.has(tree) and not w._stumped.has(tree)
	_check("%s trees, the cone: no tree is cut whole, and the shaders get it" % set, w._cone == 1.0 and whole_cone == 0.0 and nothing_left,
		"cone %s, cut whole %.2f" % ["on" if w._cone == 1.0 else "off", whole_cone])
	# in front of the hero, leaving the trees' trunks
	w.set_trees("cut_trees", "front")
	w.set_trees("leave", "trunks")
	_place_hero(w._tree_xz[tree] + away * 4.0)
	rig.yaw = fposmod(yaw_beyond + 180.0, 360.0)  # beyond the tree: it stands between the camera and the hero
	rig.pitch = 55.0
	rig.distance = 20.0
	await _seconds(0.6)
	var cut := w.sight_fade(tree)
	var left := (record["pole"] as RID).is_valid() or (record["stump"] as RID).is_valid()
	_place_hero(w._tree_xz[tree] - away * 14.0)  # well past the tree, which is now far below the hero on the screen
	await _seconds(1.5)
	var back := w.sight_fade(tree)
	_place_hero(w._tree_xz[tree] + away * 3.0)
	rig.yaw = yaw_beyond
	await _seconds(0.6)
	var just_ahead := w.sight_fade(tree)
	_place_hero(w._tree_xz[tree] + away * 12.0)
	await _seconds(0.6)
	var beyond := w.sight_fade(tree)
	_check("%s trees: a tree in front of the hero goes, leaving its trunk or stump, and comes back" % set, cut >= 1.0 and left and back == 0.0,
		"faded %.2f, %s, then %.2f" % [cut, "left standing" if left else "nothing left", back])
	_check("%s trees: a tree just ahead of the hero stays, and one well beyond it" % set, just_ahead == 0.0 and beyond == 0.0,
		"faded %.2f and %.2f" % [just_ahead, beyond])
	# the tall tree round a low camera, the camera 3 m beside its trunk, in its crown; then beside the hero
	rig.pitch = 25.0
	var to_camera := Vector2(cos(deg_to_rad(rig.yaw)), -sin(deg_to_rad(rig.yaw)))  # the camera's side of the hero, in X and Z
	var side := Vector2(-to_camera.y, to_camera.x)
	_place_hero(w._tree_xz[pole] - to_camera * (rig.distance * cos(deg_to_rad(rig.pitch))) + side * 3.0)
	await _seconds(0.6)
	var whole := w.sight_fade(pole)
	var stands: bool = w._trunks.has(pole) and w._trunks[pole] == 0.0
	_check("%s trees: a tree round a low camera fades near it, and its trunk stands" % set, whole == 0.0 and stands,
		"cut whole %.2f, trunk %s" % [whole, "standing" if stands else "not standing"])
	rig.pitch = 40.0
	_place_hero(w._tree_xz[pole] + side * 7.0 - to_camera * 0.5)
	await _seconds(1.5)
	var beside := w.sight_fade(pole)
	_check("%s trees: a tall tree beside the hero stays" % set, beside == 0.0, "faded %.2f" % beside)
	# the x-ray
	w.set_trees("cut_trees", "xray")
	rig.yaw = fposmod(rad_to_deg(atan2(-pole_away.y, pole_away.x)) + 180.0, 360.0)  # the camera beyond the tree
	rig.pitch = 55.0
	_place_hero(w._tree_xz[pole] + pole_away * 5.0 + pole_side * 2.5)  # behind the tree, but not behind its trunk
	await _seconds(0.6)
	var window: float = w._xray  # what the shaders were given (xray_on)
	var standing: bool = w._trunks.has(pole) and w._trunks[pole] == 0.0 and w.sight_fade(pole) == 0.0
	rig.pitch = 15.0
	_place_hero(w._tree_xz[pole] + pole_away * 5.0)  # right behind its trunk, the camera low
	await _seconds(0.6)
	var hidden: float = w._trunks.get(pole, 0.0)
	var stump_too := (trees[pole]["stump"] as RID).is_valid()
	_check("%s trees, x-ray: a tree in front of the hero isn't cut whole, and its trunk stands" % set, window == 1.0 and standing,
		"window %s, trunk %s" % ["on" if window == 1.0 else "off", "standing" if standing else "not standing"])
	_check("%s trees, x-ray: a trunk that hides the hero goes, to its stump" % set, hidden >= 1.0 and stump_too,
		"faded %.2f, %s" % [hidden, "stump" if stump_too else "no stump"])
	# the lower middle of the screen, as before: the tree just ahead of the hero goes too
	w.set_trees("leave", "stumps")
	w.set_trees("cut_trees", "area")
	rig.pitch = 55.0
	_place_hero(w._tree_xz[tree] + away * 3.0)
	rig.yaw = yaw_beyond
	await _seconds(0.6)
	var area_ahead := w.sight_fade(tree)
	_check("%s trees, the lower middle: a tree just ahead of the hero goes" % set, area_ahead >= 1.0, "faded %.2f" % area_ahead)
	# only the trees in the way of the hero
	w.set_trees("cut_trees", "line")
	_place_hero(w._tree_xz[tree] + away * 5.0)
	rig.yaw = yaw_beyond
	await _seconds(0.6)
	var ahead := w.sight_fade(tree)
	rig.yaw = fposmod(rig.yaw + 180.0, 360.0)  # beyond the tree, looking at the hero through it
	rig.pitch = 20.0
	rig.distance = 25.0
	await _seconds(0.6)
	var gone := w.sight_fade(tree)
	rig.yaw = fposmod(rig.yaw + 180.0, 360.0)
	await _seconds(1.5)
	_check("%s trees, only those in the way: a tree ahead of the hero stays" % set, ahead == 0.0, "faded %.2f" % ahead)
	_check("%s trees, only those in the way: they fade out, and back" % set, gone >= 1.0 and w.sight_fade(tree) == 0.0,
		"faded %.2f, then %.2f" % [gone, w.sight_fade(tree)])
	w.set_trees("cut_trees", "veil")
	rig.pitch = 55.0
	rig.distance = 20.0


## Put the hero there, and the camera straight over to it, rather than gliding there past other trees.
func _place_hero(spot: Vector2) -> void:
	var w: DemoWorld = demo.world
	demo.hero.global_position = Vector3(spot.x, w.height_at(spot.x, spot.y) + 0.05, spot.y)
	demo.hero.reset_physics_interpolation()
	demo.rig._pivot = demo.hero.global_position + Vector3(0, 1.4, 0)


func _check(what: String, ok: bool, detail: String) -> void:
	results.append(("PASS  " if ok else "FAIL  ") + what + "  (" + detail + ")")


func _mouse_button(button: MouseButton, pressed: bool) -> void:
	var ev := InputEventMouseButton.new()
	ev.button_index = button
	ev.pressed = pressed
	ev.position = demo.get_viewport().get_visible_rect().size * Vector2(0.7, 0.3)
	ev.global_position = ev.position
	Input.parse_input_event(ev)


func _key(key: Key) -> void:
	for pressed in [true, false]:
		var ev := InputEventKey.new()
		ev.physical_keycode = key
		ev.pressed = pressed
		Input.parse_input_event(ev)


func _frames(n: int) -> void:
	for i in n:
		await demo.get_tree().process_frame


func _seconds(t: float) -> void:
	await demo.get_tree().create_timer(t).timeout
