class_name Hero
extends CharacterBody3D
## The hero, for now a grey box with a darker band across its front, so you can see which way it faces.
##
## As on the look & feel board: WASD walks it, relative to the camera (W away from it), and it faces the way it walks.
## Holding the left mouse button stands in for attacking: the hero turns to face the cursor and walks slower, in any
## direction, so the facing and the speeds can be tried out before there are attacks.

@export var speed := 5.5
@export var attack_speed := 0.55  ## share of the speed while attacking
@export var turn_rate := 14.0
@export var gravity := 24.0

var camera_rig: CameraRig
var attacking := false
var facing := 0.0  ## radians about Y; 0 faces -Z (north)


func _ready() -> void:
	var body := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = Vector3(0.6, 1.8, 0.38)
	body.mesh = box
	body.position.y = 0.9
	var grey := StandardMaterial3D.new()
	grey.albedo_color = Color("#8F8F8C")
	grey.roughness = 0.85
	body.material_override = grey
	add_child(body)
	var band := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = Vector3(0.46, 0.12, 0.06)
	band.mesh = bm
	band.position = Vector3(0, 1.52, -0.2)
	var dark := StandardMaterial3D.new()
	dark.albedo_color = Color("#3E3E3C")
	band.material_override = dark
	add_child(band)
	var shape := CapsuleShape3D.new()
	shape.radius = 0.34
	shape.height = 1.8
	var cs := CollisionShape3D.new()
	cs.shape = shape
	cs.position.y = 0.9
	add_child(cs)
	collision_layer = 4
	collision_mask = DemoWorld.LAYER_GROUND | DemoWorld.LAYER_SOLID
	floor_max_angle = deg_to_rad(40.0)
	floor_snap_length = 0.6


func _physics_process(delta: float) -> void:
	var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var forward := camera_rig.ground_forward()
	var right := forward.cross(Vector3.UP)
	var dir := (right * input.x - forward * input.y)
	if dir.length() > 1.0:
		dir = dir.normalized()
	attacking = Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT) and not camera_rig.orbiting \
		and get_viewport().gui_get_hovered_control() == null  # not while clicking the HUD
	var spd := speed * (attack_speed if attacking else 1.0)
	velocity.x = dir.x * spd
	velocity.z = dir.z * spd
	if is_on_floor():
		velocity.y = -0.5
	else:
		velocity.y -= gravity * delta
	move_and_slide()

	var want := facing
	if attacking:
		var aim := camera_rig.cursor_on_ground()
		var to := aim - global_position
		if Vector2(to.x, to.z).length() > 0.2:
			want = atan2(-to.x, -to.z)
	elif dir.length() > 0.05:
		want = atan2(-dir.x, -dir.z)
	facing = lerp_angle(facing, want, 1.0 - exp(-turn_rate * delta))
	rotation.y = facing
