extends Node3D
## Dev: the old and new trees and the props in rows, lit like the mockups, for comparing with Blender renders.
## godot --path game res://scenes/dev/lineup.tscn -- --shot=out.png [--crown=0] [--models=Fern0,Reed0,...]
## (--models: those models alone, in a row, the camera close; with --trunks, 3 m apart, the camera low on their trunks)

const LINEUP := [  # model, Blender x, y, scale
	["ScotsPine_A", 0.0, 0.0, 1.0], ["NorwaySpruce_A", 9.0, 0.0, 1.0], ["SilverBirch_A", 18.0, 0.0, 1.0],
	["Aspen_A", 27.0, 0.0, 1.0], ["Rowan_A", 36.0, 0.0, 1.0], ["Alder_A", 45.0, 0.0, 1.0],
	["Pine0", 0.0, 14.0, 1.0], ["TallSpruce0", 9.0, 14.0, 1.0], ["Birch0", 18.0, 14.0, 1.0], ["Birch1", 27.0, 14.0, 1.0],
	["YoungSpruce0", 36.0, 14.0, 3.0], ["Pine1", 45.0, 14.0, 1.0],
	["BigBoulder0", 2.0, -9.0, 1.3], ["Boulder0", 8.0, -9.0, 1.0], ["MossMound0", 13.0, -9.0, 1.4], ["Heather0", 16.0, -9.0, 1.4],
	["Lichen0", 18.0, -9.0, 1.4], ["Grass0", 20.0, -9.0, 1.2], ["TallGrass0", 22.0, -9.0, 1.2],
	["Log0", 28.0, -9.0, 1.0], ["RuneStone", 34.0, -9.0, 1.0], ["Cairn", 37.0, -9.0, 1.0], ["Snag0", 41.0, -9.0, 1.0],
]

var frames := 0
var shot := ""


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--shot="):
			shot = a.substr(7)
		elif a == "--crown=0":
			Models._leaf_material("x")  # placeholder so the cache exists
	var world := WorldEnvironment.new()
	add_child(world)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	Mood.apply_day(world, sun)
	if "--nofog" in OS.get_cmdline_user_args():
		world.environment.fog_enabled = false
	for a in OS.get_cmdline_user_args():  # --env:property=value, --sun:property=value
		for prefix in ["--env:", "--sun:"]:
			if a.begins_with(prefix):
				var kv := a.substr(prefix.length()).split("=")
				var target: Object = world.environment if prefix == "--env:" else sun
				target.set(kv[0], str_to_var(kv[1]))
	var ground := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(400, 400)
	ground.mesh = plane
	var gm := StandardMaterial3D.new()
	gm.albedo_color = Color("#66833A")
	gm.roughness = 0.93
	gm.metallic_specular = 0.2
	gm.diffuse_mode = BaseMaterial3D.DIFFUSE_LAMBERT
	ground.material_override = gm
	add_child(ground)
	var rows: Array = LINEUP
	var pivot := Vector3(22.5, 0.0, -3.0)
	var reach := 52.0
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--models="):
			rows = []
			var x := 0.0
			for m: String in a.substr(9).split(","):
				var w := maxf(1.2, (Models.mesh(m).get_aabb().size.x + Models.mesh(m).get_aabb().size.z) * 0.6)
				rows.append([m, x + w * 0.5, 0.0, 1.0])
				x += w + 0.4
			pivot = Vector3(x * 0.5, 0.0, 0.0)
			reach = x * 0.75 + 2.0
			if "--trunks" in OS.get_cmdline_user_args():
				for k in rows.size():
					rows[k][1] = k * 3.0
				pivot = Vector3((rows.size() - 1) * 1.5, 1.6, 0.0)
				reach = rows.size() * 1.9 + 2.0
	for row in rows:
		var mi := MeshInstance3D.new()
		mi.mesh = Models.mesh(row[0])
		mi.position = Vector3(row[1], 0.0, -row[2])
		mi.scale = Vector3.ONE * row[3]
		if "--noshadow" in OS.get_cmdline_user_args():
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(mi)
	if "--crown=0" in OS.get_cmdline_user_args():
		for m in Models._materials.values():
			if m is ShaderMaterial and (m as ShaderMaterial).shader.resource_path.ends_with("leaves.gdshader"):
				(m as ShaderMaterial).set_shader_parameter("crown_normals", false)
	var cam := Camera3D.new()
	add_child(cam)
	cam.keep_aspect = Camera3D.KEEP_WIDTH
	cam.fov = rad_to_deg(2.0 * atan(18.0 / 35.0))
	cam.far = 600.0
	var yaw := deg_to_rad(250.0)
	var pitch := deg_to_rad(8.0 if "--trunks" in OS.get_cmdline_user_args() else 24.0)
	var off_b := Vector3(cos(yaw) * cos(pitch), sin(yaw) * cos(pitch), sin(pitch)) * reach
	cam.position = pivot + Vector3(off_b.x, off_b.z, -off_b.y)
	cam.look_at(pivot + Vector3(0, reach / 13.0, 0))


func _process(_d: float) -> void:
	frames += 1
	if shot != "" and frames == 40:
		get_viewport().get_texture().get_image().save_png(shot)
		print("saved ", shot)
		get_tree().quit()
