// A portfolio tree's stump: its bark textured (see lowpoly.gdshaderinc, BARK), its cut top plain wood.
shader_type spatial;
render_mode diffuse_lambert, specular_schlick_ggx;
#define BARK
#include "res://shaders/lowpoly.gdshaderinc"
