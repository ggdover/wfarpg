// The pebbles along the paths: the low-poly material, recoloured to the path's theme (scripts/path_themes.gd), keeping
// each face's light and dark.
shader_type spatial;
render_mode diffuse_lambert, specular_schlick_ggx;
#define PEBBLE
#include "res://shaders/lowpoly.gdshaderinc"
