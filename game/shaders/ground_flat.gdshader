// The ground with no small detail: see ground.gdshader and ground.gdshaderinc.
shader_type spatial;
render_mode diffuse_lambert, specular_schlick_ggx;

#define DETAIL 0
#include "res://shaders/ground.gdshaderinc"
