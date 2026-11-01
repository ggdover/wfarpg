// Trunks, branches and the mockups' trees: see lowpoly.gdshaderinc. They fade out when they're in the way of the camera,
// and sway in the wind.
shader_type spatial;
render_mode diffuse_lambert, specular_schlick_ggx;
#define HERO_FADE
#define SWAY
#include "res://shaders/lowpoly.gdshaderinc"
