// Autumn's fallen leaves lying thick in drifts and piles (scripts/leaf_litter.gd), where an area's litter covers the
// ground and the leaves' drift noise runs high: the user asked for a thick layer of leaves, thin in places, now and
// then deep in piles, which stir as the hero steps through them (14 October). Each leaf is a small faceted kite,
// folded along its midrib, in the grove's autumn colours; a patch of them lies at every point of the field's grid
// that's in a pile, stacked from the ground up to the pile's depth there, so a pile rises toward its middle, and at
// its thin edges fewer of them lie, flat on the ground. The patch carries the pile's depth there (0..1), the ground's
// height and its slope (INSTANCE_CUSTOM, worked out as the area loads), so its leaves read no textures but the
// trees' shade. Leaf by leaf: its middle in CUSTOM0.xz, how deep in the pile it lies in CUSTOM0.y (0 at the bottom,
// 1 on top), its own random number in CUSTOM0.w; its shape about its middle in VERTEX.
//
// Stirring: within stir_radius of the hero's trail (scripts/hero_trail.gd), the leaves are pushed aside and the pile
// pressed down by the step, shaken back and forth, and a few of them hop up (hop, 1-2 cm) and fall back, turning over;
// it all dies away and settles as the trail there ages. The nearer the step and the deeper the pile, the more.
shader_type spatial;
render_mode cull_disabled, world_vertex_coords, diffuse_lambert, specular_schlick_ggx;

#include "res://shaders/common.gdshaderinc"

// the trees' shade on the ground, as the ground shader has it (DemoWorld.set_ground_param)
uniform sampler2D canopy_tex : hint_default_white, filter_linear_mipmap, repeat_disable;
uniform float canopy_strength = 0.35;
uniform vec4 bounds = vec4(-80.0, -68.0, 160.0, 136.0);

uniform float spacing = 0.4;  // metres between the grid's patches
uniform float depth = 0.12;  // metres deep at a pile's thickest
uniform float reach = 32.0;  // metres from the camera where the last of them has gone
uniform float hop = 0.02;  // metres a stirred leaf hops, at most

const int TRAIL = 24;
uniform vec4 trail[TRAIL];
uniform int trail_count = 0;
uniform float trail_reach = 0.0;
uniform float stir_radius = 0.5;  // metres from the step a leaf still stirs
uniform float settle = 1.5;  // seconds until it's all still again

global uniform vec2 mood_grade;

// the fallen leaves' colours, the ground shader's (ground.gdshaderinc): 0, 0.2, 0.45, 0.7, 0.85 and 1
const vec3 L0 = vec3(0.2582, 0.1022, 0.0273);
const vec3 L1 = vec3(0.4621, 0.1812, 0.0284);
const vec3 L2 = vec3(0.6514, 0.3231, 0.0395);
const vec3 L3 = vec3(0.7454, 0.4793, 0.0802);
const vec3 L4 = vec3(0.5210, 0.3813, 0.0513);
const vec3 L5 = vec3(0.3663, 0.0513, 0.0232);

varying vec3 v_col;
varying float v_canopy;

uint hash_u(uvec2 v) {
	v = v * uvec2(1597334673u, 3812015801u);
	uint n = (v.x ^ v.y) * 1597334673u;
	return n ^ (n >> 16u);
}

float rnd(uvec2 c, uint k) {
	return float(hash_u(c + uvec2(k * 7919u, k * 104729u)) & 0xFFFFFFu) / 16777215.0;
}

vec3 seg(float t, float p0, vec3 c0, float p1, vec3 c1) {
	return mix(c0, c1, clamp((t - p0) / (p1 - p0), 0.0, 1.0));
}

vec3 leaf_colour(float t) {
	if (t < 0.2) return seg(t, 0.0, L0, 0.2, L1);
	if (t < 0.45) return seg(t, 0.2, L1, 0.45, L2);
	if (t < 0.7) return seg(t, 0.45, L2, 0.7, L3);
	if (t < 0.85) return seg(t, 0.7, L3, 0.85, L4);
	return seg(t, 0.85, L4, 1.0, L5);
}

// v turned by angle about the unit axis k (Rodrigues)
vec3 turned(vec3 v, vec3 k, float angle) {
	float c = cos(angle);
	float s = sin(angle);
	return v * c + cross(k, v) * s + k * dot(k, v) * (1.0 - c);
}

void vertex() {
	vec3 origin = MODEL_MATRIX[3].xyz;
	uvec2 cell = uvec2(ivec2(floor(origin.xz * 64.0)) + ivec2(1 << 20));
	float pa = rnd(cell, 1u) * TAU;  // the patch turned its own way
	mat2 turn = mat2(vec2(cos(pa), sin(pa)), vec2(-sin(pa), cos(pa)));
	vec2 c = origin.xz + (vec2(rnd(cell, 2u), rnd(cell, 3u)) - 0.5) * spacing * 0.6 + turn * CUSTOM0.xz;  // its middle
	float deep = CUSTOM0.y;
	uint leaf = uint(CUSTOM0.w * 16777215.0);
	float p = INSTANCE_CUSTOM.r;  // the pile's depth here
	vec2 slope = INSTANCE_CUSTOM.ba;
	float g0 = INSTANCE_CUSTOM.g + dot(slope, c - origin.xz);  // the ground under the leaf's middle
	float far = 1.0 - smoothstep(reach * 0.6, reach, distance(vec3(c.x, g0, c.y), main_camera_position));
	// at a pile's thin edge fewer leaves lie; far off they thin out till they've gone
	if (rnd(cell, 10u + leaf) >= smoothstep(0.0, 0.3, p) * far) {
		VERTEX = vec3(origin.x, -10000.0, origin.z);
	} else {
		vec3 shape = VERTEX - origin - vec3(CUSTOM0.x, 0.0, CUSTOM0.z);
		shape.xz = turn * shape.xz;
		shape.y += dot(slope, shape.xz);  // lying along the slope
		float y = g0 + 0.006 + deep * depth * p;

		// stirred by the hero's steps: the newest part of the trail within stir_radius, and how long ago it was there
		float s = 0.0;
		float t = 0.0;
		vec2 away = vec2(0.0);
		if (trail_count > 1 && distance(c, trail[0].xy) < trail_reach) {
			for (int i = 0; i + 1 < TRAIL; i++) {
				if (i + 1 >= trail_count) {
					break;
				}
				vec2 p0 = trail[i].xy;
				vec2 sg = trail[i + 1].xy - p0;
				float len2 = dot(sg, sg);
				float f = len2 > 1e-6 ? clamp(dot(c - p0, sg) / len2, 0.0, 1.0) : 0.0;
				vec2 off = c - (p0 + sg * f);
				float d = length(off);
				if (d < stir_radius) {
					s = 1.0 - smoothstep(0.12, stir_radius, d);
					t = mix(trail[i].z, trail[i + 1].z, f);
					away = d > 1e-4 ? off / d : vec2(1.0, 0.0);
					break;
				}
			}
		}
		s *= smoothstep(0.05, 0.4, p) * (1.0 - smoothstep(settle * 0.6, settle, t));  // more in a deep pile; dying away
		vec3 lift = vec3(0.0);
		if (s > 0.0) {
			float r1 = rnd(cell, 20u + leaf);
			float r2 = rnd(cell, 21u + leaf);
			float r3 = rnd(cell, 22u + leaf);
			float ra = rnd(cell, 23u + leaf) * TAU;
			vec3 axis = vec3(cos(ra), 0.0, sin(ra));
			float back = 1.0 - smoothstep(0.3, settle, t);  // pushed and pressed, then settling back
			// pushed aside, the pile pressed down where stepped, and shaken back and forth, less and less
			lift.xz = away * 0.035 * s * back * (0.4 + 0.6 * deep);
			lift.y = -depth * p * deep * 0.5 * s * back;
			float angle = s * 0.5 * sin(t * 24.0 + r1 * TAU) * exp(-t * 3.0);
			// a few of them, more the nearer the step, hop up and fall back, turning over as they go
			if (r2 < 0.35 * s) {
				float u = clamp((t - 0.12 * r3) / (0.3 + 0.15 * r1), 0.0, 1.0);
				float arc = 4.0 * u * (1.0 - u);
				lift.y += hop * mix(0.6, 1.0, r3) * arc;
				lift.xz += away * 0.02 * u;
				angle += arc * (1.0 + 1.5 * r2 / max(0.35 * s, 1e-3));
			}
			shape = turned(shape, axis, angle);
		}
		VERTEX = vec3(c.x, y, c.y) + shape + lift;
		// the colours of the leaves on the ground, a little darker the deeper in the pile, in its shade
		float tone = rnd(cell, 30u + leaf);
		v_col = leaf_colour(tone) * mix(0.8, 1.15, rnd(cell, 31u + leaf)) * mix(0.55, 1.0, deep);
		v_canopy = mix(1.0, textureLod(canopy_tex, (c - bounds.xy) / bounds.zw, 0.0).r, canopy_strength);
	}
}

void fragment() {
	// faceted: each half of the folded leaf flat, lit on whichever side faces the camera
	vec3 n = normalize(cross(dFdx(VERTEX), dFdy(VERTEX)));
	NORMAL = dot(n, VIEW) < 0.0 ? -n : n;
	float grey = dot(v_col, vec3(0.2126, 0.7152, 0.0722));
	ALBEDO = mix(vec3(grey), v_col, mood_grade.x) * mood_grade.y;
	ROUGHNESS = 0.85;
	SPECULAR = 0.25;
	AO = v_canopy;
}
