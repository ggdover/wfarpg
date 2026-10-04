// Trees' bare trunks, which the x-ray leaves standing (scripts/world.gd): see lowpoly.gdshaderinc. The x-ray doesn't
// cut them, but they fade out when they hide the hero.
shader_type spatial;
render_mode diffuse_lambert, specular_schlick_ggx;
#define HERO_FADE
#define NO_XRAY
#include "res://shaders/lowpoly.gdshaderinc"
