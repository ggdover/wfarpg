// Trunks, branches and the mockups' trees: see lowpoly.gdshaderinc. They fade out between the camera and the hero.
shader_type spatial;
render_mode diffuse_lambert, specular_schlick_ggx;
#define HERO_FADE
#include "res://shaders/lowpoly.gdshaderinc"
