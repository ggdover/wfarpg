extends SceneTree
## Dev: the run portfolio in the game (assets/characters: make_runs.py exports each model and rig, with its fifty
## runs and a stand, to assets/characters/build/runs/<model>_<rig>.glb, and the runs' order and names to runs.json
## there). The hero is one of the figures, read straight from its .glb: it runs as it moves, the run sped up or slowed
## to the hero's speed, and stands when it stops. It stays upright through turns: the user didn't want it tilting into
## them (3 November).
##   1-5  model    R / Shift+R  rig    Q / E  run    L  all five models in a slanting line    Z  slow motion
##   (and the demo's own keys)
## python3 game/tools/play.py --script res://scripts/dev/runs.gd -- [--scene=open_forest] [--model=2] [--rig=heat]
##   [--run=heroic] [--all] [--close] [--zoom=10] [--out=shot.png [--for=seconds [--dir=right] [--turn=back]]] [--tour]
##   [--slow=0.25]
## --out: a screenshot and quit, standing, or after running --for seconds to the camera's right or --dir (--turn:
## turning that way for the last fifth of a second); a relative --out is from game/, where Godot runs. --close: the
## camera near and low. --zoom: the game's camera this far (m) from the hero, as the mouse wheel takes it.
## --tour: stand, run a set path and stand, then quit, for recording with Godot's --write-movie.
## --check (with --headless): read every model on every rig and check its skeleton, skin and animations, then quit.

const DIR := "../assets/characters/build/runs"
const MODELS := [["Faceted3000", "Faceted 3000"], ["Faceted1500", "Faceted 1500"], ["Faceted800", "Faceted 800"],
		["Painted1500", "Painted 1500"], ["Retopo", "Retopology"]]
const RIGS := [["tripo", "Tripo weights"], ["smooth", "Smoothed"], ["heat", "Bone heat"], ["rigid", "Rigid"],
		["helpers", "Helper joints"], ["cloth", "Cloth bones"], ["corrective", "Corrective shapes"]]
const SPEED := 5.5  ## m/s: the speed the runs are made for (assets/characters/runs.py)
const ABREAST := Vector3(1.3, 0.0, 1.1)  ## with all five, each this far to the side of and behind the one before
## --tour: [the directions held, seconds], seen from the side, from behind and turning (after standing a moment)
const TOUR := [[["right"], 1.6], [["right", "forward"], 0.7], [["forward"], 0.9], [["left"], 1.4], [["back"], 0.8]]

var demo
var hero: Node3D
var model := 1
var rig := 2  ## bone heat, the rig the portfolio's page shows
var run := 0
var runs: Array = []  ## [[key, name]] in the portfolio's order, from runs.json
var all := false
var figures: Array[Node3D] = []
var players: Array[AnimationPlayer] = []
var stride := 0.0  ## how far through its cycle the run is, so another run or figure goes on from there
var label: Label
var was := {}
var material: Material


func _initialize() -> void:
	var walk := 0.0
	var shot := ""
	var dir := "move_right"
	var turn := ""
	var slow := 1.0
	var zoom := 0.0
	runs = _read_runs()
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--model="):
			model = clampi(int(a.substr(8)) - 1, 0, MODELS.size() - 1)
		elif a.begins_with("--rig="):
			rig = _find(RIGS, a.substr(6), rig)
		elif a.begins_with("--run="):
			run = _find(runs, a.substr(6), run)
		elif a == "--all":
			all = true
		elif a.begins_with("--for="):  # not --walk=, which the demo takes itself
			walk = float(a.substr(6))
		elif a.begins_with("--dir="):
			dir = "move_" + a.substr(6)
		elif a.begins_with("--turn="):  # for the last fifth of a second, toward this too: a screenshot mid-turn
			turn = "move_" + a.substr(7)
		elif a.begins_with("--out="):  # not --shot=, which the demo takes itself
			shot = a.substr(6)
		elif a.begins_with("--slow="):  # slow motion, as Z gives it: 0.5 or 0.25
			slow = clampf(float(a.substr(7)), 0.05, 1.0)
		elif a.begins_with("--zoom="):
			zoom = float(a.substr(7))
	if "--check" in OS.get_cmdline_user_args():
		quit(_check())
		return
	change_scene_to_file("res://scenes/demo.tscn")
	await create_timer(3.0).timeout
	Engine.time_scale = slow  # once the demo is up, so it loads at full speed
	demo = current_scene
	hero = demo.hero
	var touring := "--tour" in OS.get_cmdline_user_args()
	if "--close" in OS.get_cmdline_user_args():  # the camera near and lower, to see the figures well
		demo.rig.pitch = 30.0
		demo.rig.distance = 10.0
	elif zoom > 0.0:  # the game's camera, zoomed in or out
		demo.rig.distance = clampf(zoom, demo.rig.min_distance, demo.rig.max_distance)
	elif touring:  # the game's camera, a little nearer than it starts
		demo.rig.distance = 14.0
	for c in hero.get_children():
		if c is MeshInstance3D:
			(c as MeshInstance3D).visible = false
	material = load("res://scripts/models.gd").lowpoly_material()
	if not touring:
		_make_label()
	_show()
	if touring:  # for a recording (--write-movie): standing, running about, standing
		print("runs: tour starts")
		await create_timer(0.8).timeout
		for leg in TOUR:
			for d in leg[0]:
				Input.action_press("move_" + d)
			await create_timer(leg[1]).timeout
			for d in leg[0]:
				Input.action_release("move_" + d)
		await create_timer(1.0).timeout
		print("runs: tour ends")
		quit()
		return
	if walk > 0.0 or shot != "":  # a screenshot running, or (no --for) standing
		if walk > 0.0:
			Input.action_press(dir)
		if turn != "" and walk > 0.2:
			await create_timer(walk - 0.2).timeout
			Input.action_press(turn)
			await create_timer(0.2).timeout
		else:
			await create_timer(walk if walk > 0.0 else 1.5).timeout
		if shot != "":
			var saved := root.get_texture().get_image().save_png(shot)
			print("runs: saved " if saved == OK else "runs: can't save ", shot)
		if walk > 0.0:
			Input.action_release(dir)
		quit()


## --check: reads every model on every rig and says whether each has its skeleton, skin and all the runs and the
## stand, looping back to its start; 0 if all do.
func _check() -> int:
	var bad := 0
	var want: Array = runs.map(func(r): return r[0]) + ["stand"]
	for m in MODELS.size():
		for g in RIGS.size():
			rig = g
			var path := _glb(m)
			var doc := GLTFDocument.new()
			var state := GLTFState.new()
			if doc.append_from_file(path, state) != OK:
				print("runs check: can't read ", path)
				bad += 1
				continue
			var scene: Node3D = doc.generate_scene(state)
			var sk: Skeleton3D = scene.find_children("*", "Skeleton3D", true, false)[0]
			var mi: MeshInstance3D = scene.find_children("*", "MeshInstance3D", true, false)[0]
			var ap: AnimationPlayer = scene.find_children("*", "AnimationPlayer", true, false)[0]
			var missing := want.filter(func(n): return not ap.has_animation(n))
			var open := []  # runs whose last pose isn't their first: the loop would jump
			for n in want:
				if not ap.has_animation(n):
					continue
				var anim := ap.get_animation(n)
				for t in anim.get_track_count():
					if anim.track_get_type(t) == Animation.TYPE_ROTATION_3D and anim.track_get_key_count(t) > 1:
						var a: Quaternion = anim.track_get_key_value(t, 0)
						var b: Quaternion = anim.track_get_key_value(t, anim.track_get_key_count(t) - 1)
						if absf(a.dot(b)) < 0.9999:
							open.append(n)
							break
			var shapes := 0  # the corrective rig's shapes, each turned by every run
			var unshaped := []
			if RIGS[g][0] == "corrective":
				shapes = mi.mesh.get_blend_shape_count()
				for n in want:
					if not ap.has_animation(n):
						continue
					var anim := ap.get_animation(n)
					var turned := 0
					for t in anim.get_track_count():
						if anim.track_get_type(t) == Animation.TYPE_BLEND_SHAPE:
							turned += 1
					if shapes < 16 or turned < shapes:
						unshaped.append(n)
			var fine := (missing.is_empty() and open.is_empty() and unshaped.is_empty() and mi.skin != null
					and sk.get_bone_count() >= 61)
			if not fine:
				bad += 1
			print("runs check: %s_%s %s: %d bones, %d animations%s%s%s%s" % [MODELS[m][0], RIGS[g][0],
					"ok" if fine else "FAILED", sk.get_bone_count(), ap.get_animation_list().size(),
					(", %d shapes" % shapes) if shapes else "",
					(", missing " + str(missing)) if not missing.is_empty() else "",
					(", not looping " + str(open)) if not open.is_empty() else "",
					(", shapes not turned in " + str(unshaped)) if not unshaped.is_empty() else ""])
			scene.free()
	print("runs check: %d of %d fine" % [MODELS.size() * RIGS.size() - bad, MODELS.size() * RIGS.size()])
	return 1 if bad else 0


## The runs in order with their names, from the build's runs.json: [[key, name]].
func _read_runs() -> Array:
	var path := ProjectSettings.globalize_path("res://").path_join(DIR).path_join("runs.json").simplify_path()
	var list: Array = []
	var got = JSON.parse_string(FileAccess.get_file_as_string(path)) if FileAccess.file_exists(path) else null
	if got is Array:
		for r in got:
			list.append([str(r["key"]), str(r["label"])])
	if list.is_empty():
		print("runs: can't read ", path, ": build it with make_runs.py")
		list.append(["athletic", "Athletic"])
	return list


func _find(list: Array, key: String, fallback: int) -> int:
	for i in list.size():
		if list[i][0] == key:
			return i
	return fallback


func _glb(m: int) -> String:
	return ProjectSettings.globalize_path("res://").path_join(DIR).path_join(
			"%s_%s.glb" % [MODELS[m][0], RIGS[rig][0]]).simplify_path()


## The figure(s) the settings ask for, in place of the ones before.
func _show() -> void:
	for f in figures:
		f.queue_free()
	figures.clear()
	players.clear()
	var which: Array = range(MODELS.size()) if all else [model]
	for i in which:
		var doc := GLTFDocument.new()
		var state := GLTFState.new()
		if doc.append_from_file(_glb(i), state) != OK:
			print("runs: can't read ", _glb(i))
			continue
		var f: Node3D = doc.generate_scene(state)
		hero.add_child(f)
		f.rotation.y = PI  # the figures face +Z, the hero -Z
		f.position = ABREAST * (i - 2) if all else Vector3.ZERO  # a slanting line, seen from behind or the side
		for mi: MeshInstance3D in f.find_children("*", "MeshInstance3D", true, false):
			mi.material_override = material
		var ap: AnimationPlayer = f.find_children("*", "AnimationPlayer", true, false)[0]
		for n in ap.get_animation_list():
			ap.get_animation(n).loop_mode = Animation.LOOP_LINEAR
		figures.append(f)
		players.append(ap)
	_update_label()
	print("runs: %s on %s, running %s" % ["all five" if all else MODELS[model][1], RIGS[rig][1], runs[run][1]])


func _make_label() -> void:
	var layer := CanvasLayer.new()
	layer.layer = 5
	demo.add_child(layer)
	var panel := PanelContainer.new()
	var box := StyleBoxFlat.new()
	box.bg_color = Color(0.08, 0.07, 0.06, 0.78)
	box.border_color = Color("#8C6B3F")
	box.set_border_width_all(1)
	box.set_content_margin_all(10)
	panel.add_theme_stylebox_override("panel", box)
	panel.anchor_left = 1.0
	panel.anchor_right = 1.0
	panel.offset_left = -330
	panel.offset_right = -14
	panel.offset_top = 14
	layer.add_child(panel)
	label = Label.new()
	label.add_theme_color_override("font_color", Color("#E8DFC8"))
	label.add_theme_font_size_override("font_size", 15)
	panel.add_child(label)


func _update_label() -> void:
	if label == null:
		return
	label.text = ("Run portfolio\nRun %d of %d: %s   (Q / E)\nModel: %s   (1-5)\nRig: %s   (R)\n%s   (L)"
			+ "\n%s   (Z)") % [run + 1, runs.size(), runs[run][1], "all five" if all else MODELS[model][1],
			RIGS[rig][1], "One model" if all else "All five",
			{1.0: "Full speed", 0.5: "Half speed", 0.25: "Quarter speed"}.get(Engine.time_scale, "Full speed")]


func _pressed(key: Key) -> bool:
	var down := Input.is_physical_key_pressed(key)
	var fresh: bool = down and not was.get(key, false)
	was[key] = down
	return fresh


func _process(_delta: float) -> bool:
	if hero == null:
		return false
	var changed := false
	for i in MODELS.size():
		if _pressed(KEY_1 + i) and (model != i or all):
			model = i
			all = false
			changed = true
	if _pressed(KEY_R):
		rig = (rig + (RIGS.size() - 1 if Input.is_key_pressed(KEY_SHIFT) else 1)) % RIGS.size()
		changed = true
	if _pressed(KEY_E):
		run = (run + 1) % runs.size()
		_update_label()
	if _pressed(KEY_Q):
		run = (run + runs.size() - 1) % runs.size()
		_update_label()
	if _pressed(KEY_Z):  # slow motion, the whole game, to look at a run in it: a half, a quarter, full speed again
		Engine.time_scale = {0.5: 0.25, 0.25: 1.0}.get(Engine.time_scale, 0.5)
		_update_label()
	if _pressed(KEY_L):
		all = not all
		changed = true
	if changed:
		_show()
	var v := Vector2(hero.velocity.x, hero.velocity.z).length()
	for i in players.size():
		var ap := players[i]
		var want: String = runs[run][0] if v > 0.4 else "stand"
		if ap.current_animation != want:
			ap.play(want, 0.18)
			if want != "stand":  # from the same moment of the stride as the run before, not from its start
				ap.seek(stride * ap.current_animation_length, true)
		ap.speed_scale = v / SPEED if want != "stand" else 1.0
		var f := figures[i]
		if all and demo.world:  # the ones beside the hero on the ground under them
			var p := f.global_position
			f.global_position.y = demo.world.height_at(p.x, p.z)
	if not players.is_empty() and players[0].current_animation not in ["", "stand"]:
		stride = players[0].current_animation_position / maxf(players[0].current_animation_length, 0.001)
	return false
