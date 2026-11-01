// Trees' bare trunks, which the x-ray leaves standing (scripts/world.gd): see lowpoly.gdshaderinc. The x-ray doesn't
// cut them, but they fade out when they hide the hero. They sway in the wind as the whole trees do.
shader_type spatial;
render_mode diffuse_lambert, specular_schlick_ggx;
#define HERO_FADE
#define NO_XRAY
#define SWAY
#include "res://shaders/lowpoly.gdshaderinc"
