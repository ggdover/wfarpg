class_name Mood
extends RefCounted
## The light and air of Act 1's moods, matched to the mockups' Blender scenes (setup_world_act in
## mockups/act1_shots.py): a sun, a plain ambient colour for the world's light, the gradient sky behind, and haze.
##
## Blender's sun strength is irradiance; Godot multiplies a light's energy by pi, so energy = strength / pi.

const SUN_ROTATION := Vector2(52.0, -120.0)  # Blender's sun rotation: X and Z, in degrees


static func sun_direction(rot_x: float, rot_z: float) -> Vector3:
	## Where Blender's sun shines, from its rotation, in Godot's axes.
	var rx := deg_to_rad(rot_x)
	var rz := deg_to_rad(rot_z)
	var b := Vector3(-sin(rz) * sin(rx), cos(rz) * sin(rx), -cos(rx))
	return Vector3(b.x, b.z, -b.y)


static func apply_day(world: WorldEnvironment, sun: DirectionalLight3D) -> void:
	var env := Environment.new()
	var sky := Sky.new()
	var sky_mat := ShaderMaterial.new()
	sky_mat.shader = load("res://shaders/sky.gdshader")
	sky.sky_material = sky_mat
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color("#A9C6E6")
	env.ambient_light_energy = 1.1
	env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_exposure = 1.0
	env.adjustment_enabled = true
	env.adjustment_saturation = 1.2  # Blender's AgX with its Medium High Contrast look is more saturated than Godot's
	env.ssao_enabled = true
	env.ssao_radius = 0.8
	env.ssao_intensity = 1.6
	env.fog_enabled = true
	env.fog_mode = Environment.FOG_MODE_EXPONENTIAL
	env.fog_light_color = Color("#D5E1EC")
	env.fog_light_energy = 1.0
	env.fog_density = 0.0028
	env.fog_sky_affect = 0.0
	world.environment = env

	var d := sun_direction(SUN_ROTATION.x, SUN_ROTATION.y)
	sun.basis = Basis.looking_at(d, Vector3.UP if absf(d.y) < 0.99 else Vector3.FORWARD)
	sun.light_color = Color("#FFE4BC")
	sun.light_energy = 4.2 / PI
	sun.light_angular_distance = 0.6  # the mockups' sun is 2.5 degrees wide; that wide, Godot's soft shadows get grainy
	sun.shadow_enabled = true
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
	sun.directional_shadow_max_distance = 40.0
	RenderingServer.global_shader_parameter_set("mood_grade", Vector2(1.0, 1.0))
