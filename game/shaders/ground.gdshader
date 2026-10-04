// The ground: the mockups' ground shader (mat_ground in mockups/forest_cam.py, with the meadow from act1_shots.py).
// Its large-scale colours are baked from Blender into textures by tools/build_demo.py: the grass and moss beside the
// paths, the paths' dirt, and where the paths wear the grass (wear, worn and the tufts' noise). This shader draws the
// small things on top with the same formulas, so they stay sharp up close: where the dirt shows through, the gravel
// and pebbles, the grit, and the fallen leaves, with their bumps. The trees' shade on the sky's light is baked too,
// for each tree set (canopy). Blender's X, Y are Godot's X, -Z.
shader_type spatial;
render_mode diffuse_lambert, specular_schlick_ggx;

#define DETAIL 3
#include "res://shaders/ground.gdshaderinc"
