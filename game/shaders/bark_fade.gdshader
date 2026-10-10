// A portfolio tree's trunk and branches: see lowpoly.gdshaderinc, BARK. They fade out when they're in the way of the
// camera.
shader_type spatial;
render_mode diffuse_lambert, specular_schlick_ggx;
#define HERO_FADE
#define BARK
#include "res://shaders/lowpoly.gdshaderinc"
