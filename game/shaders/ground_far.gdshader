// The ground beyond the detailed area, out to the distant forest: the same ground shader baked coarsely from above
// (tools/build_demo.py), seen only from low camera angles and far off.
shader_type spatial;
render_mode diffuse_lambert, specular_schlick_ggx;

uniform sampler2D grass_tex : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
uniform vec4 bounds = vec4(-330.0, -330.0, 660.0, 660.0);
global uniform vec2 mood_grade;

varying vec3 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec3 col = texture(grass_tex, (world_pos.xz - bounds.xy) / bounds.zw).rgb;
	float grey = dot(col, vec3(0.2126, 0.7152, 0.0722));
	ALBEDO = mix(vec3(grey), col, mood_grade.x) * mood_grade.y;
	ROUGHNESS = 0.93;
	SPECULAR = 0.2;
	AO = 0.75;  // under the distant forest
}
