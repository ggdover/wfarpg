class_name CameraRig
extends Node3D
## The camera. By default it looks down on the hero from high up, at an isometric-style angle. Hold the right mouse
## button and move the mouse to orbit it round the hero, WoW style: sideways turns the view, up and down changes the
## angle, from straight down to low behind the hero. The mouse wheel zooms. The cursor hides while you orbit and comes
## back where it was; the camera stays where you leave it.
##
## The angles are the mockups' (orbit_camera in mockups/forest_cam.py): yaw is the direction from the hero to the
## camera in Blender's terms (degrees anticlockwise from east, so 225 is south-west), pitch the camera's height in
## degrees above the horizon, with a 35 mm lens.

@export var yaw := 225.0
@export var pitch := 55.0
@export var distance := 20.0
@export var min_pitch := 8.0
@export var max_pitch := 89.0
@export var min_distance := 7.0
@export var max_distance := 34.0
@export var sensitivity := 0.25  ## degrees per pixel of mouse movement
## how far short of the hero (along the ground) the fade of trees near a high camera stops, in metres
const HERO_GAP := 6.0

var hero: Node3D
var world: DemoWorld
## false holds the camera where it is while the hero walks on (the demo's --still, for recording)
var follow := true
var camera: Camera3D
var orbiting := false
var _cursor := Vector2.ZERO
var _pivot := Vector3.ZERO


func _ready() -> void:
	# the rig moves every frame, not every physics tick, so it isn't interpolated; it follows where the hero is drawn,
	# which is (physics interpolation, in project.godot, keeps the hero smooth above the physics' 60 ticks a second)
	physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF
	camera = Camera3D.new()
	camera.keep_aspect = Camera3D.KEEP_WIDTH
	camera.fov = rad_to_deg(2.0 * atan(18.0 / 35.0))  # a 35 mm lens on a 36 mm wide sensor, like Blender's
	camera.near = 0.2
	camera.far = 900.0
	add_child(camera)
	if not "--nofade" in OS.get_cmdline_user_args():
		RenderingServer.global_shader_parameter_set("hero_fade_on", 1.0)


func snap() -> void:
	_pivot = _hero_at() + Vector3(0, 1.4, 0)
	_place()
	if world:
		world.update_sight(camera, _hero_at(), 10.0)


## Where the hero is drawn this frame, between its last two physics ticks.
func _hero_at() -> Vector3:
	return hero.get_global_transform_interpolated().origin


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_RIGHT:
			orbiting = mb.pressed
			if mb.pressed:
				_cursor = get_viewport().get_mouse_position()
				Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
			else:
				Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
				Input.warp_mouse(_cursor)
		elif mb.pressed and mb.button_index == MOUSE_BUTTON_WHEEL_UP:
			distance = clampf(distance / 1.1, min_distance, max_distance)
		elif mb.pressed and mb.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			distance = clampf(distance * 1.1, min_distance, max_distance)
	elif event is InputEventMouseMotion and orbiting:
		var mm := event as InputEventMouseMotion
		yaw = fposmod(yaw - mm.relative.x * sensitivity, 360.0)
		pitch = clampf(pitch + mm.relative.y * sensitivity, min_pitch, max_pitch)


func _process(delta: float) -> void:
	if follow:
		_pivot = _pivot.lerp(_hero_at() + Vector3(0, 1.4, 0), 1.0 - exp(-14.0 * delta))
	_place()
	if world:
		world.update_sight(camera, _hero_at(), delta)


func _place() -> void:
	var p := deg_to_rad(pitch)
	var y := deg_to_rad(yaw)
	var offset := Vector3(cos(y) * cos(p), sin(p), -sin(y) * cos(p)) * distance  # Blender's (x, y, z) in Godot's axes
	var pos := _pivot + offset
	if world:
		pos.y = maxf(pos.y, world.height_at(pos.x, pos.z) + 0.8)  # never under the ground on a slope
	camera.global_position = pos
	camera.look_at(_pivot + Vector3(0, 0.9 * (1.0 - pitch / 90.0), 0))
	RenderingServer.global_shader_parameter_set("hero_position", _hero_at())
	RenderingServer.global_shader_parameter_set("main_camera_position", pos)
	# trees near a high camera fade out, as the mockups hide them; low behind the hero, only those right at the camera.
	# Never near the hero, though: there trees only go once they block the view (DemoWorld.update_sight)
	var above := pos.y - (world.height_at(pos.x, pos.z) if world else 0.0)
	var radius := clampf(above * 0.85, 2.5, 15.0) if (world == null or world.fade_near_camera) else 0.0
	radius = maxf(0.0, minf(radius, Vector2(pos.x - _pivot.x, pos.z - _pivot.z).length() - HERO_GAP))
	RenderingServer.global_shader_parameter_set("tree_fade_radius", radius)
	if world:
		world.skip_faded(pos, radius)


## The direction W walks: away from the camera, along the ground.
func ground_forward() -> Vector3:
	var y := deg_to_rad(yaw)
	return Vector3(-cos(y), 0.0, sin(y))


## Where the mouse cursor points on the ground.
func cursor_on_ground() -> Vector3:
	var m := get_viewport().get_mouse_position()
	var from := camera.project_ray_origin(m)
	var to := from + camera.project_ray_normal(m) * 400.0
	var q := PhysicsRayQueryParameters3D.create(from, to, DemoWorld.LAYER_GROUND)
	var hit := get_world_3d().direct_space_state.intersect_ray(q)
	return hit["position"] if hit else hero.global_position
