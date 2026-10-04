// The ground with low detail: see ground.gdshader and ground.gdshaderinc.
shader_type spatial;
render_mode diffuse_lambert, specular_schlick_ggx;

#define DETAIL 1
#include "res://shaders/ground.gdshaderinc"
