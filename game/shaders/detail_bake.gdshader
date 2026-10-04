// Bakes the ground's small details into tiling textures, for its "Baked" level (ground_baked.gdshader): the same noise
// that ground.gdshaderinc works out for every pixel at High, worked out once, with the Voronoi cells and the noise's
// lattice wrapped so that each texture tiles. scripts/ground_detail.gd renders each layer once, at startup.
//   layer 0, a 4 m tile: the small stones (scale 13) and, in alpha, the grit (scale 30)
//   layer 1, a 4 m tile: the bigger stones (scale 5.5) and, in alpha, the fine noise that breaks up the dirt
//   layer 2, a 10 m tile: the flat stones (scale 1.7) and, in alpha, the grass's grain for the bumps
//   layer 3, a 4 m tile: the fallen leaves
// A stone layer holds in red how far inside its cell's stone a point is (inset + 0.3, in cell units, so 0.3 is the
// stone's edge), in green the cell's random number that decides at which gravel density its stone is there, and in
// blue the one that picks the stone's colour. The leaves hold how much of a leaf covers the point, the leaf's own
// random number that decides at which drift it's there (1 where no leaf is), and the one that picks its colour.
shader_type canvas_item;
render_mode blend_disabled, unshaded;

#define BN_FAST_HASH
#include "res://shaders/blender_noise.gdshaderinc"

uniform int layer = 0;

int wrap_int(int a, int n) {
	return a - n * int(floor(float(a) / float(n)));
}

ivec2 wrap_cell(ivec2 c, int n) {
	return ivec2(wrap_int(c.x, n), wrap_int(c.y, n));
}

// snoise2 with its lattice wrapped every n cells
float snoise2_wrapped(vec2 p, int n) {
	vec2 fl = floor(p);
	vec2 f = p - fl;
	ivec2 c0 = wrap_cell(ivec2(fl), n);
	ivec2 c1 = wrap_cell(ivec2(fl) + ivec2(1), n);
	float u = bn_fade(f.x);
	float v = bn_fade(f.y);
	float a = bn_grad2(hash_point2(uint(c0.x), uint(c0.y)), f.x, f.y);
	float b = bn_grad2(hash_point2(uint(c1.x), uint(c0.y)), f.x - 1.0, f.y);
	float c = bn_grad2(hash_point2(uint(c0.x), uint(c1.y)), f.x, f.y - 1.0);
	float d = bn_grad2(hash_point2(uint(c1.x), uint(c1.y)), f.x - 1.0, f.y - 1.0);
	return 0.6616 * mix(mix(a, b, u), mix(c, d, u), v);
}

// noise_fbm2 with whole octaves, wrapped every n lattice cells at the first octave (2n at the second, and so on)
float fbm2_wrapped(vec2 p, int detail, float roughness, int n) {
	float fscale = 1.0;
	float amp = 1.0;
	float maxamp = 0.0;
	float sum = 0.0;
	int period = n;
	for (int i = 0; i <= detail; i++) {
		sum += snoise2_wrapped(fscale * p, period) * amp;
		maxamp += amp;
		amp *= roughness;
		fscale *= 2.0;
		period *= 2;
	}
	return 0.5 * sum / maxamp + 0.5;
}

// voronoi_cell_edge with the cells wrapped every n
void voronoi_cell_edge_wrapped(vec2 p, int n, out vec3 colour, out float edge) {
	vec2 cell_f = floor(p);
	vec2 local = p - cell_f;
	ivec2 cell = ivec2(cell_f);
	vec2 to_closest = vec2(0.0);
	ivec2 closest = ivec2(0);
	float best = 1e9;
	for (int j = -1; j <= 1; j++) {
		for (int i = -1; i <= 1; i++) {
			ivec2 off = ivec2(i, j);
			vec2 to_pt = vec2(off) + hash_cell2(wrap_cell(cell + off, n)).xy - local;
			float d = dot(to_pt, to_pt);
			if (d < best) {
				best = d;
				to_closest = to_pt;
				closest = off;
			}
		}
	}
	colour = hash_cell2(wrap_cell(cell + closest, n));
	edge = 1e9;
	for (int j = -1; j <= 1; j++) {
		for (int i = -1; i <= 1; i++) {
			ivec2 off = closest + ivec2(i, j);
			vec2 to_pt = vec2(off) + hash_cell2(wrap_cell(cell + off, n)).xy - local;
			vec2 perp = to_pt - to_closest;
			if (dot(perp, perp) > 0.0001) {
				edge = min(edge, dot((to_closest + to_pt) * 0.5, normalize(perp)));
			}
		}
	}
}

// the nearest cell's random vector, with the cells wrapped every n (voronoi_f1's colour)
vec3 voronoi_colour_wrapped(vec2 p, int n) {
	vec2 cell_f = floor(p);
	vec2 local = p - cell_f;
	ivec2 cell = ivec2(cell_f);
	float best = 1e9;
	vec3 colour = vec3(0.0);
	for (int j = -1; j <= 1; j++) {
		for (int i = -1; i <= 1; i++) {
			ivec2 off = ivec2(i, j);
			vec3 h = hash_cell2(wrap_cell(cell + off, n));
			float d = distance(vec2(off) + h.xy, local);
			if (d < best) {
				best = d;
				colour = h;
			}
		}
	}
	return colour;
}

// the gravel's domain warp over a tile of so many metres (as at High in ground.gdshaderinc)
vec2 warp(vec2 q, float tile) {
	int n = int(round(9.0 * tile));
	return vec2(fbm2_wrapped((q + vec2(31.7, 5.3)) * 9.0, 2, 0.5, n), fbm2_wrapped((q + vec2(7.1, 71.3)) * 9.0, 2, 0.5, n)) * 0.07;
}

// one layer of stones: x in cells, wrapped every n; the stones are inset from their cells' edges by gap0..gap1
vec3 stones(vec2 x, int n, float gap0, float gap1) {
	vec3 c;
	float edge;
	voronoi_cell_edge_wrapped(x, n, c, edge);
	float inset = edge - (c.g * (gap1 - gap0) + gap0);
	return vec3(clamp(inset + 0.3, 0.0, 1.0), c.r, c.b);
}

void fragment() {
	if (layer == 0) {
		vec2 q = UV * 4.0;
		vec2 w = q + warp(q, 4.0);
		float grit = dot(voronoi_colour_wrapped(w * 30.0, 120), vec3(0.2126, 0.7152, 0.0722));
		COLOR = vec4(stones(w * 13.0, 52, 0.12, 0.24), grit);
	} else if (layer == 1) {
		vec2 q = UV * 4.0;
		vec2 w = q + warp(q, 4.0);
		float fine = fbm2_wrapped((q + vec2(13.0, 3.0)) * 7.0, 2, 0.6, 28);
		COLOR = vec4(stones((w + vec2(3.7, 1.3)) * 5.5, 22, 0.14, 0.26), fine);
	} else if (layer == 2) {
		vec2 q = UV * 10.0;
		vec2 w = q + warp(q, 10.0);
		float grain = fbm2_wrapped((q + vec2(2.0, 2.0)) * 6.0, 1, 0.65, 60);
		COLOR = vec4(stones((w + vec2(5.1, 2.3)) * 1.7, 17, 0.16, 0.3), grain);
	} else {
		// the leaves, as in ground.gdshaderinc: at most one per cell (scale 4.5), each an ellipse turned its own way.
		// Round each leaf, its random numbers fill the space nearer it than any other leaf, so that the smaller
		// mipmaps, which average a leaf with what's round it, still know whether it's there and what colour it is.
		vec2 lv = (UV * 4.0 + vec2(2.3, 7.7)) * 4.5;
		vec2 base = floor(lv - 0.5);
		float leaf = 0.0;
		float nearest = 1e9;
		float there = 1.0;
		float tone = 0.0;
		for (int j = -1; j < 3; j++) {
			for (int i = -1; i < 3; i++) {
				ivec2 cell = ivec2(base) + ivec2(i, j);
				vec3 h = hash_cell2(wrap_cell(cell, 18));
				vec2 rel = (lv - (vec2(cell) + h.xy * 0.75)) / 4.5;  // metres from the leaf's centre
				float size = fract(h.b * 5.7) * 0.5 + 0.75;
				if (dot(rel, rel) < nearest) {
					nearest = dot(rel, rel);
					there = h.r;
					tone = h.b;
				}
				if (dot(rel, rel) > 0.0045 * size * size) {
					continue;
				}
				float ang = h.g * 6.2832;
				vec2 tr = vec2(rel.x * cos(ang) - rel.y * sin(ang), rel.x * sin(ang) + rel.y * cos(ang));
				float qd = pow(tr.x / (size * 0.05), 2.0) + pow(tr.y / (size * 0.025), 2.0);
				leaf = max(leaf, 1.0 - smoothstep(0.7, 1.05, qd));
			}
		}
		COLOR = vec4(leaf, there, tone, 1.0);
	}
}
