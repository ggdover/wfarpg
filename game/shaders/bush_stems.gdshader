// A bush's stems (the plant portfolio's bushes): see lowpoly.gdshaderinc. They sway in the wind with the bush's leaves,
// and shake as the hero pushes through it (scripts/bushes.gd).
shader_type spatial;
render_mode diffuse_lambert, specular_schlick_ggx;
#define BUSH
#include "res://shaders/lowpoly.gdshaderinc"
