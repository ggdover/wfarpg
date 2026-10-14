#include "res://shaders/common.gdshaderinc"
#define BN_FAST_HASH
#include "res://shaders/blender_noise.gdshaderinc"

uniform sampler2D grass_tex : source_color, filter_linear_mipmap_anisotropic, repeat_disable;
// the noises the path's colours come from: red the dirt's, green the trampled grass's (baked like the masks)
uniform sampler2D path_noise_tex : source_color, filter_linear_mipmap, repeat_disable;
// where the paths wear the grass (tools/build_demo.py, masks_socket): the distance from the path's centre line in
// half-widths, with the edges' wobble, as (d + 0.5) / 5; a noise for patches of wear; the tufts' noise + 0.5. All
// baked as colours (so sRGB-encoded, and decoded by source_color), and the fallen leaves' drift noise in alpha (linear).
uniform sampler2D masks_tex : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D canopy_tex : hint_default_white, filter_linear_mipmap, repeat_disable;
uniform vec4 bounds = vec4(-112.0, -88.0, 224.0, 176.0);  // x, z, width, depth of the baked area
uniform float canopy_strength = 0.35;  // how much of the baked shade to use: 0.35 matches the mockups
uniform float bump_strength = 0.5;
// How much small detail the including shader draws on top of the baked colours, its DETAIL: 3 high (everything),
// 2 medium (no flat stones, grit or grain bumps, cheaper noise), 1 low (the small gravel and the leaves), 0 none. However
// high, the details fade into their average further off than DETAIL_FAR metres from the camera, where they would be too
// small to see, and are not worked out at all beyond. With BAKED defined too, High's details come from tiling textures
// baked once at startup (shaders/detail_bake.gdshader, scripts/ground_detail.gd), instead of being worked out for
// every pixel: the same stones, grit, leaves and grain, at a fraction of the cost.
uniform float leaf_amount = 1.0;  // more or fewer fallen leaves
// where autumn's fallen leaves cover the ground, two layers of them (an autumn grove): the area's litter.png, if it has
// one, times litter
uniform sampler2D litter_tex : hint_default_black, filter_linear, repeat_disable;
uniform float litter = 1.0;
#ifdef BAKED
uniform sampler2D detail_small : hint_default_black, filter_linear_mipmap_anisotropic, repeat_enable;  // 4 m tile
uniform sampler2D detail_big : hint_default_black, filter_linear_mipmap_anisotropic, repeat_enable;  // 4 m tile
uniform sampler2D detail_flat : hint_default_black, filter_linear_mipmap_anisotropic, repeat_enable;  // 10 m tile
uniform sampler2D detail_leaves : hint_default_black, filter_linear_mipmap_anisotropic, repeat_enable;  // 4 m tile
#endif
// How far the paths' wear spreads into the grass: 0 is the mockups', where the dirt gives way to trampled grass
// within about two half-widths of the path's centre line. Up to 1, the trampled grass, bare patches and stray stones
// reach further out, the dirt and grass break up in patches a metre or two across, and more grass tufts grow in the
// path, so it's less clear exactly where the path runs.
uniform float wear_spread : hint_range(0.0, 1.0) = 0.0;
// The grass's ground (scripts/grass.gd): a grass style's strands lying flat, as seen from above, laid over the green
// ground (ground_green), its colour against its average (strokes_mean, linear), so the ground keeps its own colours
// and gains the grass's texture, which its cards match. strokes_amount 0 leaves it off, as before the grass.
uniform sampler2D strokes_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform vec3 strokes_mean = vec3(1.0);
uniform float strokes_metres = 4.0;  // how far the texture reaches before it repeats
uniform float strokes_amount = 0.0;
uniform float strokes_shade = 1.0;  // the ground under the grass, darker in its shade, so its lighter strands show
// The bog's grass's ground (scripts/grass.gd, its field on the bog): its strands lying flat, laid over the ground where
// bog_tex says (the area's bog_grass.png), as the green ground's is; bog_strokes_amount 0 leaves it off.
uniform sampler2D bog_tex : hint_default_black, filter_linear, repeat_disable;
uniform sampler2D bog_strokes_tex : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform vec3 bog_strokes_mean = vec3(1.0);
uniform float bog_strokes_metres = 4.0;
uniform float bog_strokes_amount = 0.0;
uniform float bog_strokes_shade = 1.0;
const float DETAIL_FAR[4] = float[](0.0, 28.0, 38.0, 50.0);
global uniform vec2 mood_grade;

// The path's palette and how much gravel, grit and leaves it has: scripts/path_themes.gd sets them. The defaults
// are the mockups' light tan paths. Colours at the mockups' ramp stops: dirt at 0.3, 0.5 and 0.72 of its noise,
// fading to "verge" near the edges; trampled grass at 0.3 and 0.7; grit at 0.2 and 0.8; small stones at 0, 0.5
// and 1; bigger stones at 0, 0.3, 0.6, 0.85 and 1; flat stones at 0 and 1.
group_uniforms path;
uniform vec3 dirt0 : source_color = vec3(0.839, 0.631, 0.318);
uniform vec3 dirt1 : source_color = vec3(0.867, 0.686, 0.392);
uniform vec3 dirt2 : source_color = vec3(0.878, 0.733, 0.482);
uniform vec3 verge : source_color = vec3(0.702, 0.643, 0.337);
// a second soil for the dirt, in patches, more of it toward the edges: soil_mix 0 has none, 0.5 about half
uniform vec3 soil0 : source_color = vec3(0.839, 0.631, 0.318);
uniform vec3 soil1 : source_color = vec3(0.867, 0.686, 0.392);
uniform vec3 soil2 : source_color = vec3(0.878, 0.733, 0.482);
uniform float soil_mix = 0.0;
uniform vec3 worn0 : source_color = vec3(0.576, 0.565, 0.310);
uniform vec3 worn1 : source_color = vec3(0.671, 0.643, 0.384);
uniform vec3 grit0 : source_color = vec3(0.780, 0.604, 0.341);
uniform vec3 grit1 : source_color = vec3(0.855, 0.725, 0.506);
uniform vec3 shade : source_color = vec3(0.608, 0.447, 0.231);
uniform vec3 small0 : source_color = vec3(0.776, 0.596, 0.325);
uniform vec3 small1 : source_color = vec3(0.816, 0.667, 0.424);
uniform vec3 small2 : source_color = vec3(0.851, 0.741, 0.549);
uniform vec3 big0 : source_color = vec3(0.737, 0.557, 0.306);
uniform vec3 big1 : source_color = vec3(0.780, 0.620, 0.376);
uniform vec3 big2 : source_color = vec3(0.820, 0.682, 0.459);
uniform vec3 big3 : source_color = vec3(0.851, 0.741, 0.549);
uniform vec3 big4 : source_color = vec3(0.871, 0.780, 0.631);
uniform vec3 flat0 : source_color = vec3(0.749, 0.620, 0.412);
uniform vec3 flat1 : source_color = vec3(0.816, 0.718, 0.545);
uniform vec3 stones = vec3(1.0);  // how much small, bigger and flat gravel
uniform float grit_amount = 1.0;
group_uniforms;

// the fallen leaves' colours, at 0, 0.2, 0.45, 0.7, 0.85 and 1
const vec3 L0 = vec3(0.2582, 0.1022, 0.0273);  // #8B5A2E
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
// Far off (less detail), and where a cell gets smaller than a few pixels, the stones fade into their average, so they
// don't shimmer.
void gravel_average(float density, out float stone, out float rnd, out float shadow, out float hgt) {
	stone = 0.45 * density;
	shadow = 0.12 * density;
	hgt = 0.0;
	rnd = 0.5;
}

void gravel(vec2 wp, float scale, float gap0, float gap1, float density, float detail, bool exact, out float stone, out float rnd, out float shadow, out float hgt) {
	if (detail <= 0.0 || density <= 0.0) {
		gravel_average(density, stone, rnd, shadow, hgt);
		return;
	}
	vec2 q = wp * scale;
	vec3 c;
	float edge;
	if (exact) {
		voronoi_cell_edge(q, 1.0, c, edge);
	} else {
		float f1, f2;
		voronoi_f1f2(q, 1.0, c, f1, f2);
		edge = 0.5 * (f2 - f1);
	}
	float inset = edge - (c.g * (gap1 - gap0) + gap0);
	float here = smoothstep(-0.01, 0.01, density - c.r);
	float aa = length(fwidth(q));  // cells per pixel
	float w = min(aa * 0.5, 0.2);
	stone = smoothstep(-w, 0.04 + w, inset) * here;
	shadow = (smoothstep(-0.07 - w, 0.0, inset) - smoothstep(-w, 0.04 + w, inset)) * here;
	hgt = smoothstep(0.0, 0.16, inset) * here;
	rnd = c.b;
	float far_off = max(smoothstep(0.25, 0.7, aa), 1.0 - detail);
	stone = mix(stone, 0.45 * density, far_off);
	shadow = mix(shadow, 0.12 * density, far_off);
	hgt *= 1.0 - far_off;
	rnd = mix(rnd, 0.5, far_off);
}

#ifdef BAKED
// gravel() from a baked layer t (detail_bake.gdshader): its inset, the density at which its stone is there, and its
// colour's random value. aa is how many of the layer's cells a pixel spans.
void gravel_baked(vec4 t, float aa, float density, float detail, out float stone, out float rnd, out float shadow, out float hgt) {
	if (detail <= 0.0 || density <= 0.0) {
		gravel_average(density, stone, rnd, shadow, hgt);
		return;
	}
	float inset = t.r - 0.3;
	float here = smoothstep(-0.01, 0.01, density - t.g);
	float w = min(aa * 0.5, 0.2);
	stone = smoothstep(-w, 0.04 + w, inset) * here;
	shadow = (smoothstep(-0.07 - w, 0.0, inset) - smoothstep(-w, 0.04 + w, inset)) * here;
	hgt = smoothstep(0.0, 0.16, inset) * here;
	rnd = t.b;
	float far_off = max(smoothstep(0.25, 0.7, aa), 1.0 - detail);
	stone = mix(stone, 0.45 * density, far_off);
	shadow = mix(shadow, 0.12 * density, far_off);
	hgt *= 1.0 - far_off;
	rnd = mix(rnd, 0.5, far_off);
}
#endif

void fragment() {
	vec2 uv = (world_pos.xz - bounds.xy) / bounds.zw;
	vec3 col = texture(grass_tex, uv).rgb;
	if (strokes_amount > 0.0) {  // the grass's ground, on green ground
		col *= mix(vec3(1.0), texture(strokes_tex, world_pos.xz / strokes_metres).rgb / strokes_mean * strokes_shade,
				strokes_amount * ground_green(col));
	}
	vec4 m = texture(masks_tex, uv);
	if (bog_strokes_amount > 0.0) {  // the bog's grass's ground, where it grows, darker in the wet hollows between tussocks
		float bog = bog_strokes_amount * texture(bog_tex, uv).r;
		col *= mix(vec3(1.0), texture(bog_strokes_tex, world_pos.xz / bog_strokes_metres).rgb / bog_strokes_mean * bog_strokes_shade, bog)
				* mix(1.0, 0.72, min(bog, 1.0) * (1.0 - tussock_at(m)));
	}
	float e = m.r * 5.0 - 0.5;  // half-widths from the path's centre line
	float patches = m.g - 0.5;
	float tufts = m.b - 0.5;
	// feet trample the grass along the paths, and the path's dirt shows where they wear it away (mat_ground): wear
	// and worn as the mockups have them at wear_spread 0, and with a long, thin tail of wear out into the grass
	float sp = wear_spread;
	float wear = max(map_s(e, 0.45, 1.9, 1.0 - 0.15 * sp, 0.0), 0.55 * sp * map_s(e, 1.0, 1.0 + 2.4 * max(sp, 0.01), 1.0, 0.0));
	float worn = map_s(e, 0.7, 2.1 + 1.4 * sp, 1.0, 0.0);
	vec2 pn = texture(path_noise_tex, uv).rg;
	col = mix(col, ramp_seg(pn.g, 0.3, worn0, 0.7, worn1), worn * 0.5);
	vec3 dirt = ramp3(pn.r, 0.3, dirt0, 0.5, dirt1, 0.72, dirt2);
	if (soil_mix > 0.0) {
		float soil = smoothstep(-0.06, 0.06, patches + 0.3 * (soil_mix - 0.5) + 0.05 * (e - 1.0));
		dirt = mix(dirt, ramp3(pn.r, 0.3, soil0, 0.5, soil1, 0.72, soil2), soil);
	}
	dirt = mix(dirt, verge, map_s(wear, 0.35, 0.85, 0.4, 0.0));
	vec2 p = vec2(world_pos.x, -world_pos.z);  // Blender's X, Y
	float hgt = 0.0;
#ifdef BAKED
	// the baked details' texture coordinates and their slopes, worked out here, where every pixel of a quad runs, so
	// the textures can be read inside the branches below at the right mipmap level
	vec2 t4 = p / 4.0;
	vec2 t4x = dFdx(t4);
	vec2 t4y = dFdy(t4);
	vec2 t10 = p / 10.0;
	vec4 flat_grain = textureGrad(detail_flat, t10, dFdx(t10), dFdy(t10));
	float px = length(fwidth(p));  // metres a pixel spans
#endif

	// near the paths: where feet have worn the grass away, the dirt shows, with gravel densest in the middle and
	// thinning out into the grass, and grit in the dirt
	float level = float(DETAIL);
	float detail = DETAIL > 0 ? 1.0 - smoothstep(0.7 * DETAIL_FAR[DETAIL], DETAIL_FAR[DETAIL], length(VERTEX)) : 0.0;
	if (worn > 0.0005) {
#ifdef BAKED
		vec4 big = textureGrad(detail_big, t4, t4x, t4y);
		float fine = detail > 0.0 ? big.a - 0.5 : 0.0;
#else
		float fine = detail > 0.0 ? noise_fbm2((p + vec2(13.0, 3.0)) * 7.0, level >= 3.0 ? 2.0 : 1.0, 0.6) - 0.5 : 0.0;
#endif
		float bare = smoothstep(0.35, 0.7, wear + 2.0 * tufts + 0.5 * fine + 1.2 * sp * patches);
		col = mix(col, dirt, bare);
		float strewn = wear + 0.3 * fine;
		float small_d = (map_s(strewn, 0.15, 0.75, 0.0, 0.6) + 0.08 * worn) * stones.x;
		float big_d = (map_s(strewn, 0.25, 0.85, 0.0, 0.45) + 0.05 * worn) * stones.y;
		float flat_d = map_s(strewn, 0.5, 0.9, 0.0, 0.06) * stones.z;
		float s_st, s_r, s_sh, s_h, b_st, b_r, b_sh, b_h, f_st, f_r, f_sh, f_h;
#ifdef BAKED
		vec4 small = textureGrad(detail_small, t4, t4x, t4y);
		gravel_baked(small, px * 13.0, small_d, detail, s_st, s_r, s_sh, s_h);
		gravel_baked(big, px * 5.5, big_d, detail, b_st, b_r, b_sh, b_h);
		gravel_baked(flat_grain, px * 1.7, flat_d, detail, f_st, f_r, f_sh, f_h);
		float grit = mix(small.a, 0.5, max(smoothstep(0.3, 0.8, px * 30.0), 1.0 - detail));
#else
		vec2 warped = p;
#if DETAIL >= 3
		if (detail > 0.0) {
			float d = level >= 3.0 ? 2.0 : 1.0;
			warped += vec2(noise_fbm2((p + vec2(31.7, 5.3)) * 9.0, d, 0.5), noise_fbm2((p + vec2(7.1, 71.3)) * 9.0, d, 0.5)) * 0.07;
		}
#endif
		bool exact = DETAIL >= 3;
#if DETAIL >= 1
		gravel(warped, 13.0, 0.12, 0.24, small_d, detail, exact, s_st, s_r, s_sh, s_h);
#else
		gravel_average(small_d, s_st, s_r, s_sh, s_h);
#endif
#if DETAIL >= 2
		gravel(warped + vec2(3.7, 1.3), 5.5, 0.14, 0.26, big_d, detail, exact, b_st, b_r, b_sh, b_h);
#else
		gravel_average(big_d, b_st, b_r, b_sh, b_h);
#endif
#if DETAIL >= 3
		gravel(warped + vec2(5.1, 2.3), 1.7, 0.16, 0.3, flat_d, detail, exact, f_st, f_r, f_sh, f_h);
#else
		gravel_average(flat_d, f_st, f_r, f_sh, f_h);
#endif
		float grit = 0.5;
#if DETAIL >= 3
		if (detail > 0.0) {
			float gd;
			vec3 gc;
			vec2 gp;
			voronoi_f1(warped * 30.0, 1.0, gd, gc, gp);
			float grit_lod = max(smoothstep(0.3, 0.8, length(fwidth(warped * 30.0))), 1.0 - detail);
			grit = mix(dot(gc, vec3(0.2126, 0.7152, 0.0722)), 0.5, grit_lod);
		}
#endif
#endif
		col = mix(col, ramp_seg(grit, 0.2, grit0, 0.8, grit1), min(bare * 0.35 * grit_amount, 1.0));
		col = mix(col, shade, min(0.3 * s_sh + 0.5 * b_sh + 0.5 * f_sh, 0.5));
		col = mix(col, ramp3(s_r, 0.0, small0, 0.5, small1, 1.0, small2), s_st);
		col = mix(col, ramp5(b_r, big0, big1, big2, big3, big4), b_st);
		col = mix(col, ramp_seg(f_r, 0.0, flat0, 1.0, flat1), f_st);
		hgt += 0.5 * s_h + b_h + 1.3 * f_h;
	}

#if DETAIL >= 1
	// fallen leaves: small ellipses, each turned its own way, in loose drifts over the grass and the paths. One leaf
	// may lie at each Voronoi cell's point (scale 4.5), and a leaf is far smaller than its cell, so only the 2 x 2
	// cells round this spot can hold a leaf that covers it.
	if (detail > 0.0) {
		vec2 lv = (p + vec2(2.3, 7.7)) * 4.5;
		float lit = litter * texture(litter_tex, uv).r;
		float drift = mix((0.12 + map_s(m.a, 0.5, 0.75, 0.0, 0.2)) * leaf_amount, 0.97, lit);
		float fade = (1.0 - smoothstep(0.3, 0.9, length(fwidth(lv)) * 4.0)) * detail;  // too small to see far off
		float covered = 0.0;
		// with litter, a second layer on top, turned and at another scale, so the leaves cover the ground
		for (int layer = 0; layer < (lit > 0.0 ? 2 : 1); layer++) {
			mat2 turn = layer == 0 ? mat2(1.0) : mat2(vec2(0.8, 0.6), vec2(-0.6, 0.8));
			float scale = layer == 0 ? 4.5 : 3.4;
			vec2 q = turn * p + (layer == 0 ? vec2(2.3, 7.7) : vec2(13.1, 3.7));
			vec2 lq = q * scale;
			float leaf = 0.0;
			float tone = 0.0;
#ifdef BAKED
			vec2 tq = q / 4.0;
			vec4 baked_leaf = textureGrad(detail_leaves, layer == 0 ? t4 : tq, turn * t4x, turn * t4y);
			leaf = baked_leaf.r * smoothstep(-0.01, 0.01, drift - baked_leaf.g);
			tone = baked_leaf.b;
#else
			vec2 lbase = floor(lq - 0.5);
			float aa = min(fwidth(lq.x) * 20.0, 0.5);
			for (int j = 0; j < 2; j++) {
				for (int i = 0; i < 2; i++) {
					ivec2 cell = ivec2(lbase) + ivec2(i, j);
					vec3 h = hash_cell2(cell + ivec2(layer * 97, layer * 31));
					if (h.r >= drift) {
						continue;
					}
					vec2 rel = (lq - (vec2(cell) + h.xy * 0.75)) / scale;  // metres from the leaf's centre
					float size = (fract(h.b * 5.7) * 0.5 + 0.75) * (layer == 0 ? 1.0 : 1.25);
					if (dot(rel, rel) > 0.0045 * size * size) {
						continue;
					}
					float ang = h.g * 6.2832;
					vec2 tr = vec2(rel.x * cos(ang) - rel.y * sin(ang), rel.x * sin(ang) + rel.y * cos(ang));
					float qd = pow(tr.x / (size * 0.05), 2.0) + pow(tr.y / (size * 0.025), 2.0);
					float l = 1.0 - smoothstep(0.75 - aa, 1.0 + aa, qd);
					if (l > leaf) {
						leaf = l;
						tone = h.b;
					}
				}
			}
#endif
			leaf *= fade * (layer == 0 ? 1.0 : lit);
			col = mix(col, leaf_ramp(tone), leaf);
			covered = max(covered, leaf);
		}
		hgt += 0.3 * covered;
#if DETAIL >= 3
#ifdef BAKED
		hgt += 0.12 * flat_grain.a;  // the grass's grain, for the bumps
#else
		hgt += 0.12 * noise_fbm2((p + vec2(2.0, 2.0)) * 6.0, 1.0, 0.65);  // the grass's grain, for the bumps
#endif
#endif
	}
#endif

	float grey = dot(col, vec3(0.2126, 0.7152, 0.0722));
	ALBEDO = mix(vec3(grey), col, mood_grade.x) * mood_grade.y;
	ROUGHNESS = 0.93;
	SPECULAR = 0.2;
	AO = mix(1.0, texture(canopy_tex, uv).r, canopy_strength);

#if DETAIL >= 3
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
#endif
}
