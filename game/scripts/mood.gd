class_name Mood
extends RefCounted
## The light and air of the demo's scenes. "day" matches the mockups' Blender scenes (setup_world_act in
## mockups/act1_shots.py): a sun, a plain ambient colour for the world's light, the gradient sky behind, and haze.
## The others change it for a scene (scripts/scenes.gd): fog rolling in, a low morning sun shining through mist,
## autumn's warmer light; and the water scenes add reflections.
##
## Blender's sun strength is irradiance; Godot multiplies a light's energy by pi, so energy = strength / pi.

const SUN_ROTATION := Vector2(52.0, -120.0)  # the day's sun: Blender's rotation, X and Z, in degrees

## Each mood is the day with these changed: sun (Blender's X and Z rotation), sun_color, sun_strength (Blender's),
## ambient (colour), ambient_energy, sky (its four colour stops, low to high), clouds, fog_density, fog_color,
## fog_sky (how much the haze hides the sky), fog_height (mist lying low: its top, metres) and fog_height_density,
## volumetric (density, or 0 for none) and volumetric_color, grade (the leaves' and ground's saturation and
## brightness: mood_grade), saturation, glow.
const MOODS := {
	"day": {},
	"fog": {"sun": Vector2(38.0, -110.0), "sun_color": Color("#D8DDE0"), "sun_strength": 1.6, "ambient": Color("#AEB8C2"),
		"ambient_energy": 1.25, "sky": [Color("#C9CFD3"), Color("#C4CBD0"), Color("#BCC4CA"), Color("#B4BDC4")], "clouds": 0.0,
		"fog_density": 0.02, "fog_color": Color("#C3CBD1"), "fog_sky": 1.0, "fog_height": 3.0, "fog_height_density": 0.08,
		"grade": Vector2(0.72, 0.92), "saturation": 1.0},
	"morning": {"sun": Vector2(73.0, -95.0), "sun_color": Color("#FFD9A3"), "sun_strength": 5.0, "ambient": Color("#8FA6C2"),
		"ambient_energy": 0.85, "sky": [Color("#F2DCC0"), Color("#E3D8C8"), Color("#B9C9DA"), Color("#93AFCF")], "clouds": 0.4,
		"fog_density": 0.002, "fog_color": Color("#E8D9C4"), "fog_sky": 0.3, "volumetric": 0.012, "volumetric_color": Color("#F2EFE8"),
		"glow": true},
	"autumn": {"sun": Vector2(58.0, -125.0), "sun_color": Color("#FFDDB0"), "sun_strength": 4.4, "ambient": Color("#B5BFD0"),
		"fog_color": Color("#E2DCD2"), "saturation": 1.25},
}

## the sun's rotation in the mood last applied, for what's baked from the sun's side (the trees' shadow pictures)
static var sun_rotation := SUN_ROTATION


static func sun_direction(rot_x: float, rot_z: float) -> Vector3:
	## Where Blender's sun shines, from its rotation, in Godot's axes.
	var rx := deg_to_rad(rot_x)
	var rz := deg_to_rad(rot_z)
	var b := Vector3(-sin(rz) * sin(rx), cos(rz) * sin(rx), -cos(rx))
	return Vector3(b.x, b.z, -b.y)


static func apply_day(world: WorldEnvironment, sun: DirectionalLight3D) -> void:
	apply(world, sun, "day")


## Light the scene in one of MOODS; reflections turns screen-space reflections on, for water.
static func apply(world: WorldEnvironment, sun: DirectionalLight3D, mood: String, reflections := false) -> void:
	var m: Dictionary = MOODS[mood]
	var env := Environment.new()
	var sky := Sky.new()
	var sky_mat := ShaderMaterial.new()
	sky_mat.shader = load("res://shaders/sky.gdshader")
	if m.has("sky"):
		for i in 4:
			sky_mat.set_shader_parameter("stop%d" % i, m["sky"][i])
	sky_mat.set_shader_parameter("clouds", m.get("clouds", 1.0))
	sky.sky_material = sky_mat
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = m.get("ambient", Color("#A9C6E6"))
	env.ambient_light_energy = m.get("ambient_energy", 1.1)
	env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_exposure = 1.0
	env.adjustment_enabled = true
	env.adjustment_saturation = m.get("saturation", 1.2)  # Blender's AgX with its Medium High Contrast look is more saturated than Godot's
	env.ssao_enabled = true
	env.ssao_radius = 0.8
	env.ssao_intensity = 1.6
	env.fog_enabled = true
	env.fog_mode = Environment.FOG_MODE_EXPONENTIAL
	env.fog_light_color = m.get("fog_color", Color("#D5E1EC"))
	env.fog_light_energy = 1.0
	env.fog_density = m.get("fog_density", 0.0028)
	env.fog_sky_affect = m.get("fog_sky", 0.0)
	if m.has("fog_height"):
		env.fog_height = m["fog_height"]
		env.fog_height_density = m["fog_height_density"]
	if m.get("volumetric", 0.0) > 0.0:
		env.volumetric_fog_enabled = true
		env.volumetric_fog_density = m["volumetric"]
		env.volumetric_fog_albedo = m["volumetric_color"]
		env.volumetric_fog_anisotropy = 0.7  # light scatters forward, so the shafts shine towards the sun
		env.volumetric_fog_length = 60.0
		env.volumetric_fog_ambient_inject = 0.0  # lit by the sun alone, so its shafts stand out from the shade
		env.volumetric_fog_sky_affect = 0.0
	if m.get("glow", false):
		env.glow_enabled = true
		env.glow_intensity = 0.5
		env.glow_bloom = 0.05
		env.glow_hdr_threshold = 1.1
	if reflections:
		env.ssr_enabled = true
		env.ssr_max_steps = 128  # long rays, to reach the trees on a lake's far shore
		env.ssr_fade_in = 0.1
		env.ssr_fade_out = 2.0
		env.ssr_depth_tolerance = 2.0
	world.environment = env

	sun_rotation = m.get("sun", SUN_ROTATION)
	var d := sun_direction(sun_rotation.x, sun_rotation.y)
	sun.basis = Basis.looking_at(d, Vector3.UP if absf(d.y) < 0.99 else Vector3.FORWARD)
	sun.light_color = m.get("sun_color", Color("#FFE4BC"))
	sun.light_energy = m.get("sun_strength", 4.2) / PI
	sun.light_angular_distance = 0.6  # the mockups' sun is 2.5 degrees wide; that wide, Godot's soft shadows get grainy
	sun.light_volumetric_fog_energy = 1.0
	sun.shadow_enabled = true
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
	sun.directional_shadow_max_distance = 40.0
	RenderingServer.global_shader_parameter_set("mood_grade", m.get("grade", Vector2(1.0, 1.0)))
