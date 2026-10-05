class_name SightArea
extends Control
## The area round the hero that decides when the trees in front of it go see-through (DemoWorld, cut_trees "veil"),
## drawn over the view while the performance panel's "show the area" is on: its outline, red once the trees cover
## enough of it, and the points across it that lines from the camera are tested to, red where some tree covers them;
## with how much of it the trees cover.

const CLEAR := Color(1.0, 1.0, 1.0, 0.75)
const COVERED := Color(1.0, 0.32, 0.2, 0.95)

var world: DemoWorld
var camera: Camera3D


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _process(_delta: float) -> void:
	visible = world != null and world.show_area and world.cut_trees == "veil"
	if visible:
		queue_redraw()


func _draw() -> void:
	if world.area_outline.is_empty():
		return
	var outline := PackedVector2Array()
	for p in world.area_outline:
		if camera.is_position_behind(p):
			return
		outline.append(camera.unproject_position(p))
	outline.append(outline[0])
	var over := world._cover >= world.veil_cover
	draw_polyline(outline, COVERED if over else CLEAR, 2.0, true)
	for k in world.area_points.size():
		var covered := k < world.area_covered.size() and world.area_covered[k] == 1
		draw_circle(camera.unproject_position(world.area_points[k]), 4.0, COVERED if covered else CLEAR)
	var top := outline[0]
	for q in outline:
		if q.y < top.y:
			top = q
	var text := "trees cover %d%%, see-through from %d%%" % [roundi(world._cover * 100.0), roundi(world.veil_cover * 100.0)]
	var font := get_theme_default_font()
	var width := font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, 14).x
	draw_string_outline(font, top + Vector2(-width * 0.5, -10.0), text, HORIZONTAL_ALIGNMENT_LEFT, -1, 14, 4, Color(0, 0, 0, 0.7))
	draw_string(font, top + Vector2(-width * 0.5, -10.0), text, HORIZONTAL_ALIGNMENT_LEFT, -1, 14, COVERED if over else CLEAR)
