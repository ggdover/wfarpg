// Water: lakes, the bog's pools and streams (Extras.water in tools/build_demo.py; its colours per kind are
// Models.WATER). Opaque, so that the screen-space reflections the water's scenes turn on (scripts/mood.gd) show the
// trees on the far shore. Its colour goes from the bed's, where it's shallow, to the deep water's, with how deep it is
// over the bed (UV2.x, metres); ripples move with its flow (UV: metres a second along X and Z), and where a stream
// runs fast, it breaks white.
shader_type spatial;
render_mode diffuse_lambert, specular_schlick_ggx;
#include "res://shaders/common.gdshaderinc"

uniform vec3 shallow : source_color = vec3(0.36, 0.33, 0.22);
uniform vec3 deep : source_color = vec3(0.05, 0.07, 0.06);
uniform float clear = 0.6;  // the bed fades into the deep water's colour over this many metres
uniform float ripple = 0.015;  // how high the ripples are (m)
uniform float roughness = 0.04;
uniform float specular = 0.35;  // how much it reflects head on (Godot's specular: 0.5 is 4%)
uniform vec3 foam : source_color = vec3(0.86, 0.89, 0.88);
global uniform vec2 mood_grade;

varying vec3 world;
varying vec2 flow;
varying float depth;

void vertex() {
	world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	flow = UV;
	depth = UV2.x;
}

// ripples: two sizes of smooth noise, slowly changing
float wave(vec2 p, float t) {
	return 0.65 * value_noise3(vec3(p * 1.3, t)) + 0.35 * value_noise3(vec3(p * 3.1 + 7.0, t * 1.4));
}

// the ripples carried along by the flow: two layers of them, each moved with the flow for four seconds and then
// started afresh, cross-fading, so that they never stretch out where the flow changes (a flow map)
float flowing(vec2 p, vec2 f, float t) {
	float a = fract(t * 0.25);
	float b = fract(t * 0.25 + 0.5);
	float w = 1.0 - abs(2.0 * a - 1.0);
	return w * wave(p - f * a * 4.0, t * 0.35) + (1.0 - w) * wave(p - f * b * 4.0 + vec2(3.1, 1.7), t * 0.35);
}

void fragment() {
	vec2 p = world.xz;
	float speed = length(flow);
	float e = 0.05;
	float h = flowing(p, flow, TIME);
	vec2 slope = vec2(flowing(p + vec2(e, 0.0), flow, TIME) - h, flowing(p + vec2(0.0, e), flow, TIME) - h) / e;
	float amp = ripple * (1.0 + 2.5 * smoothstep(0.3, 1.5, speed));  // rougher where it runs fast
	vec3 n = normalize(vec3(-slope.x * amp, 1.0, -slope.y * amp));

	float d = max(depth, 0.0);
	vec3 col = mix(shallow, deep, 1.0 - exp(-d / clear));
	// white water where it runs fast, in streaks along the flow
	vec2 along = speed > 0.01 ? flow / speed : vec2(1.0, 0.0);
	vec2 q = vec2(dot(p, along), dot(p, vec2(-along.y, along.x)) * 3.0);  // stretched along the flow
	float white = smoothstep(0.85, 1.6, speed) * smoothstep(0.45, 0.75, flowing(q * 1.6, vec2(speed * 1.6, 0.0), TIME));
	col = mix(col, foam, white * 0.85);
	float grey = dot(col, vec3(0.2126, 0.7152, 0.0722));
	ALBEDO = mix(vec3(grey), col, mood_grade.x) * mood_grade.y;
	ROUGHNESS = mix(roughness, 0.6, white);
	SPECULAR = specular;
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
}
