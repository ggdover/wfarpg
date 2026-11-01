// A portfolio tree's trunk and branches: see lowpoly.gdshaderinc, BARK. They fade out when they're in the way of the
// camera, and sway in the wind with the leaves.
shader_type spatial;
render_mode diffuse_lambert, specular_schlick_ggx;
#define HERO_FADE
#define BARK
#define SWAY
#include "res://shaders/lowpoly.gdshaderinc"
