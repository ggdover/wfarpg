// A portfolio tree's bare trunk, which the x-ray leaves standing (scripts/world.gd): see lowpoly.gdshaderinc, BARK. The
// x-ray doesn't cut it, but it fades out when it hides the hero.
shader_type spatial;
render_mode diffuse_lambert, specular_schlick_ggx;
#define HERO_FADE
#define NO_XRAY
#define BARK
#include "res://shaders/lowpoly.gdshaderinc"
