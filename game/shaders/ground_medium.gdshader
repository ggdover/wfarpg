// The ground with medium detail: see ground.gdshader and ground.gdshaderinc.
shader_type spatial;
render_mode diffuse_lambert, specular_schlick_ggx;

#define DETAIL 2
#include "res://shaders/ground.gdshaderinc"
