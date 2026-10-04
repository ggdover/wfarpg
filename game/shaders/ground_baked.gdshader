// The ground with High's details read from textures baked at startup: see ground.gdshader and ground.gdshaderinc.
shader_type spatial;
render_mode diffuse_lambert, specular_schlick_ggx;

#define DETAIL 3
#define BAKED
#include "res://shaders/ground.gdshaderinc"
