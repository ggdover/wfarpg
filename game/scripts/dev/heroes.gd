extends SceneTree
## Dev: the hero portfolio's low-poly figures in the game (assets/characters: make_heroes.py exports them to
## assets/characters/build/heroes.glb), standing in a row where the hero stands in one of the demo's scenes, in its
## light and the game's low-poly material, read straight from the .glb; takes a screenshot and quits.
## python3 game/tools/play.py --script res://scripts/dev/heroes.gd -- --out=out.png [--scene=open_forest]
##   [--glb=path] [--close] (--close: the camera near and low; otherwise as the game has it; a relative --out is
##   from game/, where Godot runs)

const ROW := 1.25  ## metres between the figures, as in the portfolio


func _initialize() -> void:
	var shot := ""
	var glb := ProjectSettings.globalize_path("res://").path_join("../assets/characters/build/heroes.glb").simplify_path()
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):  # not --shot=, which the demo takes itself
			shot = a.substr(6)
		elif a.begins_with("--glb="):
			glb = a.substr(6)
	change_scene_to_file("res://scenes/demo.tscn")
	await create_timer(4.0).timeout
	var demo = current_scene
	var doc := GLTFDocument.new()
	var state := GLTFState.new()
	if doc.append_from_file(glb, state) != OK:
		print("heroes: can't read ", glb)
		quit(1)
		return
	var figures: Node3D = doc.generate_scene(state)
	demo.add_child(figures)
	var material: Material = load("res://scripts/models.gd").lowpoly_material()
	for mi: MeshInstance3D in figures.find_children("*", "MeshInstance3D", true, false):
		mi.material_override = material
	# the row, centred where the hero stands, each figure on the ground under it
	var hero: Node3D = demo.hero
	hero.visible = false
	var at := hero.global_position
	figures.global_position = Vector3(at.x, 0.0, at.z)
	for f: Node3D in figures.get_children():
		var p := f.global_position
		f.global_position = Vector3(p.x, demo.world.height_at(p.x, p.z), p.z)
	print("heroes: %d figures from %s" % [figures.get_child_count(), glb])
	if "--close" in OS.get_cmdline_user_args():
		demo.rig.pitch = 22.0
		demo.rig.distance = 9.0
	await create_timer(2.5).timeout
	if shot != "":
		var saved := root.get_texture().get_image().save_png(shot)
		print("heroes: saved " if saved == OK else "heroes: can't save ", shot)
	quit()
