// The ground: the mockups' ground shader (mat_ground in mockups/forest_cam.py, with the meadow from act1_shots.py).
// Its large-scale colours are baked from Blender into textures by tools/build_demo.py: the grass and moss beside the
// paths, the paths' dirt, and where the paths wear the grass (wear, worn and the tufts' noise). This shader draws the
// small things on top with the same formulas, so they stay sharp up close: where the dirt shows through, the gravel
// and pebbles, the grit, and the fallen leaves, with their bumps. The trees' shade on the sky's light is baked too,
// for each tree set (canopy). Blender's X, Y are Godot's X, -Z.
shader_type spatial;
render_mode diffuse_lambert, specular_schlick_ggx;

#include "res://shaders/common.gdshaderinc"
#include "res://shaders/blender_noise.gdshaderinc"

uniform sampler2D grass_tex : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
uniform sampler2D dirt_tex : source_color, filter_linear_mipmap, repeat_disable;
// wear, worn and the tufts' noise + 0.5, baked as colours (so sRGB-encoded, and decoded by source_color), and the
// fallen leaves' drift noise in alpha (linear)
uniform sampler2D masks_tex : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D canopy_tex : hint_default_white, filter_linear_mipmap, repeat_disable;
uniform vec4 bounds = vec4(-112.0, -88.0, 224.0, 176.0);  // x, z, width, depth of the baked area
uniform float canopy_strength = 0.35;  // how much of the baked shade to use: 0.35 matches the mockups
uniform float bump_strength = 0.5;
global uniform vec2 mood_grade;

const vec3 SHADE = vec3(0.3278, 0.1683, 0.0437);  // #9B723B, the gravel's contact shadow
const vec3 S0 = vec3(0.5647, 0.3140, 0.0865);  // #C69853, small gravel
const vec3 S1 = vec3(0.6308, 0.4020, 0.1500);  // #D0AA6C
const vec3 S2 = vec3(0.6939, 0.5089, 0.2623);  // #D9BD8C
const vec3 B0 = vec3(0.5029, 0.2705, 0.0762);  // #BC8E4E, bigger stones
const vec3 B1 = vec3(0.5711, 0.3419, 0.1170);  // #C79E60
const vec3 B2 = vec3(0.6376, 0.4233, 0.1779);  // #D1AE75
const vec3 B3 = vec3(0.6939, 0.5089, 0.2623);  // #D9BD8C
const vec3 B4 = vec3(0.7305, 0.5711, 0.3564);  // #DEC7A1
const vec3 F0 = vec3(0.5210, 0.3419, 0.1413);  // #BF9E69, flat stones
const vec3 F1 = vec3(0.6308, 0.4735, 0.2582);  // #D0B78B
const vec3 G0 = vec3(0.5711, 0.3231, 0.0953);  // #C79A57, grit
const vec3 G1 = vec3(0.7011, 0.4851, 0.2195);  // #DAB981
const vec3 L0 = vec3(0.2582, 0.1022, 0.0273);  // #8B5A2E, fallen leaves
const vec3 L1 = vec3(0.4621, 0.1812, 0.0284);  // #B5762F
const vec3 L2 = vec3(0.6514, 0.3231, 0.0395);  // #D39A38
const vec3 L3 = vec3(0.7454, 0.4793, 0.0802);  // #E0B850
const vec3 L4 = vec3(0.5210, 0.3813, 0.0513);  // #BFA640
const vec3 L5 = vec3(0.3663, 0.0513, 0.0232);  // #A3402A

varying vec3 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

// Blender's Map Range node, smoothstep, clamped
float map_s(float v, float lo, float hi, float to0, float to1) {
	return mix(to0, to1, smoothstep(lo, hi, v));
}

// Blender's Color Ramp, linear: stops at the given positions
vec3 ramp_seg(float t, float p0, vec3 c0, float p1, vec3 c1) {
	return mix(c0, c1, clamp((t - p0) / (p1 - p0), 0.0, 1.0));
}

vec3 ramp3(float t, float p0, vec3 c0, float p1, vec3 c1, float p2, vec3 c2) {
	return t < p1 ? ramp_seg(t, p0, c0, p1, c1) : ramp_seg(t, p1, c1, p2, c2);
}

vec3 ramp5(float t, vec3 c0, vec3 c1, vec3 c2, vec3 c3, vec3 c4) {  // the big stones' stops: 0, .3, .6, .85, 1
	if (t < 0.3) return ramp_seg(t, 0.0, c0, 0.3, c1);
	if (t < 0.6) return ramp_seg(t, 0.3, c1, 0.6, c2);
	if (t < 0.85) return ramp_seg(t, 0.6, c2, 0.85, c3);
	return ramp_seg(t, 0.85, c3, 1.0, c4);
}

vec3 leaf_ramp(float t) {  // stops 0, .2, .45, .7, .85, 1
	if (t < 0.2) return ramp_seg(t, 0.0, L0, 0.2, L1);
	if (t < 0.45) return ramp_seg(t, 0.2, L1, 0.45, L2);
	if (t < 0.7) return ramp_seg(t, 0.45, L2, 0.7, L3);
	if (t < 0.85) return ramp_seg(t, 0.7, L3, 0.85, L4);
	return ramp_seg(t, 0.85, L4, 1.0, L5);
}

// Gravel (gravel() in mat_ground): Voronoi cells shrunk away from their edges, so each cell that holds a stone is a
// small flat polygon. Returns the stone mask, its colour's random value, the contact shadow round it and its bevel.
// Far off, where a cell gets smaller than a few pixels, the stones fade into their average, so they don't shimmer.
void gravel(vec2 wp, float scale, float gap0, float gap1, float density, out float stone, out float rnd, out float shadow, out float hgt) {
	vec2 q = wp * scale;
	vec3 c;
	float edge;
	voronoi_cell_edge(q, 1.0, c, edge);
	float inset = edge - (c.g * (gap1 - gap0) + gap0);
	float here = smoothstep(-0.01, 0.01, density - c.r);
	float aa = length(fwidth(q));  // cells per pixel
	float w = min(aa * 0.5, 0.2);
	stone = smoothstep(-w, 0.04 + w, inset) * here;
	shadow = (smoothstep(-0.07 - w, 0.0, inset) - smoothstep(-w, 0.04 + w, inset)) * here;
	hgt = smoothstep(0.0, 0.16, inset) * here;
	rnd = c.b;
	float far_off = smoothstep(0.25, 0.7, aa);
	stone = mix(stone, 0.45 * density, far_off);
	shadow = mix(shadow, 0.12 * density, far_off);
	hgt *= 1.0 - far_off;
	rnd = mix(rnd, 0.5, far_off);
}

void fragment() {
	vec2 uv = (world_pos.xz - bounds.xy) / bounds.zw;
	vec3 col = texture(grass_tex, uv).rgb;
	vec3 dirt = texture(dirt_tex, uv).rgb;
	vec4 m = texture(masks_tex, uv);
	float wear = m.r;
	float worn = m.g;
	float tufts = m.b - 0.5;
	vec2 p = vec2(world_pos.x, -world_pos.z);  // Blender's X, Y
	float hgt = 0.0;

	// near the paths: where feet have worn the grass away, the dirt shows, with gravel densest in the middle and
	// thinning out into the grass, and grit in the dirt
	if (wear + worn > 0.0005) {
		float fine = noise_fbm2((p + vec2(13.0, 3.0)) * 7.0, 2.0, 0.6) - 0.5;
		float bare = smoothstep(0.35, 0.7, wear + 2.0 * tufts + 0.5 * fine);
		col = mix(col, dirt, bare);
		float spread = wear + 0.3 * fine;
		float small_d = map_s(spread, 0.15, 0.75, 0.0, 0.6) + 0.08 * worn;
		float big_d = map_s(spread, 0.25, 0.85, 0.0, 0.45) + 0.05 * worn;
		float flat_d = map_s(spread, 0.5, 0.9, 0.0, 0.06);
		vec2 warped = p + vec2(noise_fbm2((p + vec2(31.7, 5.3)) * 9.0, 2.0, 0.5), noise_fbm2((p + vec2(7.1, 71.3)) * 9.0, 2.0, 0.5)) * 0.07;
		float s_st, s_r, s_sh, s_h, b_st, b_r, b_sh, b_h, f_st, f_r, f_sh, f_h;
		gravel(warped, 13.0, 0.12, 0.24, small_d, s_st, s_r, s_sh, s_h);
		gravel(warped + vec2(3.7, 1.3), 5.5, 0.14, 0.26, big_d, b_st, b_r, b_sh, b_h);
		gravel(warped + vec2(5.1, 2.3), 1.7, 0.16, 0.3, flat_d, f_st, f_r, f_sh, f_h);
		float gd;
		vec3 gc;
		vec2 gp;
		voronoi_f1(warped * 30.0, 1.0, gd, gc, gp);
		float grit_lod = 1.0 - smoothstep(0.3, 0.8, length(fwidth(warped * 30.0)));
		float grit = mix(0.5, dot(gc, vec3(0.2126, 0.7152, 0.0722)), grit_lod);
		col = mix(col, ramp_seg(grit, 0.2, G0, 0.8, G1), bare * 0.35);
		col = mix(col, SHADE, min(0.3 * s_sh + 0.5 * b_sh + 0.5 * f_sh, 0.5));
		col = mix(col, ramp3(s_r, 0.0, S0, 0.5, S1, 1.0, S2), s_st);
		col = mix(col, ramp5(b_r, B0, B1, B2, B3, B4), b_st);
		col = mix(col, ramp_seg(f_r, 0.0, F0, 1.0, F1), f_st);
		hgt += 0.5 * s_h + b_h + 1.3 * f_h;
	}

	// fallen leaves: small ellipses, each turned its own way, in loose drifts over the grass and the paths
	vec2 lv = p + vec2(2.3, 7.7);
	float ld;
	vec3 lc;
	vec2 lp;
	voronoi_f1(lv * 4.5, 0.75, ld, lc, lp);
	vec2 rel = lv - lp / 4.5;
	float ang = lc.g * 6.2832;
	vec2 tr = vec2(rel.x * cos(ang) - rel.y * sin(ang), rel.x * sin(ang) + rel.y * cos(ang));
	float size = fract(lc.b * 5.7) * 0.5 + 0.75;
	float qd = pow(tr.x / (size * 0.05), 2.0) + pow(tr.y / (size * 0.025), 2.0);
	float drift = 0.12 + map_s(m.a, 0.5, 0.75, 0.0, 0.2);
	float edge_w = min(fwidth(qd), 0.5);
	float leaf = (1.0 - smoothstep(0.75 - edge_w, 1.0 + edge_w, qd)) * smoothstep(-0.01, 0.01, drift - lc.r);
	leaf *= 1.0 - smoothstep(0.3, 0.9, length(fwidth(lv * 4.5)) * 4.0);  // too small to see far off
	col = mix(col, leaf_ramp(lc.b), leaf);
	float grain = noise_fbm2((p + vec2(2.0, 2.0)) * 6.0, 1.0, 0.65);  // for the bumps only (one octave fewer)
	hgt += 0.12 * grain + 0.3 * leaf;

	float grey = dot(col, vec3(0.2126, 0.7152, 0.0722));
	ALBEDO = mix(vec3(grey), col, mood_grade.x) * mood_grade.y;
	ROUGHNESS = 0.93;
	SPECULAR = 0.2;
	AO = mix(1.0, texture(canopy_tex, uv).r, canopy_strength);

	// the bumps, like Blender's Bump node (strength 0.5, distance 0.03), from the height's screen-space slope
	vec3 n = normalize((INV_VIEW_MATRIX * vec4(NORMAL, 0.0)).xyz);
	vec3 dpdx = dFdx(world_pos);
	vec3 dpdy = dFdy(world_pos);
	float h = hgt * 0.03;
	vec3 r1 = cross(dpdy, n);
	vec3 r2 = cross(n, dpdx);
	float det = dot(dpdx, r1);
	vec3 grad = sign(det) * (dFdx(h) * r1 + dFdy(h) * r2);
	vec3 bumped = normalize(abs(det) * n - grad);
	n = normalize(mix(n, bumped, bump_strength));
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
}
