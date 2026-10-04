// Noise like Blender's shader nodes, so the game's shaders can paint what the mockups' node trees paint: Blender's
// Perlin noise and fBm (the Noise Texture node, normalized, lacunarity 2), and its Voronoi cells (F1 and distance to
// edge), with Bob Jenkins' lookup3 hash as Blender uses it. Ported from Blender's GPU shader library; values follow
// the same distribution, though the 2D versions draw different patterns than Blender's 3D ones.
//
// Define BN_FAST_HASH before including this for the 2D functions to use the PCG hash instead (Jarzynski and Olano,
// "Hash Functions for GPU Rendering", 2020): a few times cheaper, just as random, with different patterns.

uint bn_rot(uint x, uint k) {
	return (x << k) | (x >> (32u - k));
}

uint bn_final(uint a, uint b, uint c) {
	c ^= b; c -= bn_rot(b, 14u);
	a ^= c; a -= bn_rot(c, 11u);
	b ^= a; b -= bn_rot(a, 25u);
	c ^= b; c -= bn_rot(b, 16u);
	a ^= c; a -= bn_rot(c, 4u);
	b ^= a; b -= bn_rot(a, 14u);
	c ^= b; c -= bn_rot(b, 24u);
	return c;
}

uint hash_uint2(uint kx, uint ky) {
	uint a = 0xdeadbeefu + (2u << 2u) + 13u;
	uint b = a;
	uint c = a;
	b += ky;
	a += kx;
	return bn_final(a, b, c);
}

uint hash_uint3(uint kx, uint ky, uint kz) {
	uint a = 0xdeadbeefu + (3u << 2u) + 13u;
	uint b = a;
	uint c = a;
	c += kz;
	b += ky;
	a += kx;
	return bn_final(a, b, c);
}

float hash_uint2_to_float(uint kx, uint ky) {
	return float(hash_uint2(kx, ky)) / 4294967295.0;
}

float hash_uint3_to_float(uint kx, uint ky, uint kz) {
	return float(hash_uint3(kx, ky, kz)) / 4294967295.0;
}

uvec3 pcg3d(uvec3 v) {
	v = v * 1664525u + 1013904223u;
	v.x += v.y * v.z;
	v.y += v.z * v.x;
	v.z += v.x * v.y;
	v = v ^ (v >> uvec3(16u));
	v.x += v.y * v.z;
	v.y += v.z * v.x;
	v.z += v.x * v.y;
	return v;
}

// a random number for a 2D lattice point (the Perlin gradients' choice)
uint hash_point2(uint x, uint y) {
#ifdef BN_FAST_HASH
	return pcg3d(uvec3(x, y, 0u)).x;
#else
	return hash_uint2(x, y);
#endif
}

// a random vector for a 2D cell, each part 0..1
vec3 hash_cell2(ivec2 c) {
	uint x = uint(c.x);
	uint y = uint(c.y);
#ifdef BN_FAST_HASH
	return vec3(pcg3d(uvec3(x, y, 0x9e3779b9u))) / 4294967295.0;
#else
	return vec3(hash_uint2_to_float(x, y), hash_uint3_to_float(x, y, 1u), hash_uint3_to_float(x, y, 2u));
#endif
}

// ------------------------------------------------------------------ Perlin noise
float bn_fade(float t) {
	return t * t * t * (t * (t * 6.0 - 15.0) + 10.0);
}

float bn_grad2(uint hash, float x, float y) {
	uint h = hash & 7u;
	float u = h < 4u ? x : y;
	float v = 2.0 * (h < 4u ? y : x);
	return ((h & 1u) != 0u ? -u : u) + ((h & 2u) != 0u ? -v : v);
}

float bn_grad3(uint hash, float x, float y, float z) {
	uint h = hash & 15u;
	float u = h < 8u ? x : y;
	float vt = (h == 12u || h == 14u) ? x : z;
	float v = h < 4u ? y : vt;
	return ((h & 1u) != 0u ? -u : u) + ((h & 2u) != 0u ? -v : v);
}

// signed Perlin noise, about -1..1
float snoise2(vec2 p) {
	vec2 fl = floor(p);
	vec2 f = p - fl;
	uint X = uint(int(fl.x));
	uint Y = uint(int(fl.y));
	float u = bn_fade(f.x);
	float v = bn_fade(f.y);
	float a = bn_grad2(hash_point2(X, Y), f.x, f.y);
	float b = bn_grad2(hash_point2(X + 1u, Y), f.x - 1.0, f.y);
	float c = bn_grad2(hash_point2(X, Y + 1u), f.x, f.y - 1.0);
	float d = bn_grad2(hash_point2(X + 1u, Y + 1u), f.x - 1.0, f.y - 1.0);
	return 0.6616 * mix(mix(a, b, u), mix(c, d, u), v);
}

float snoise3(vec3 p) {
	vec3 fl = floor(p);
	vec3 f = p - fl;
	uint X = uint(int(fl.x));
	uint Y = uint(int(fl.y));
	uint Z = uint(int(fl.z));
	float u = bn_fade(f.x);
	float v = bn_fade(f.y);
	float w = bn_fade(f.z);
	float r0 = mix(mix(bn_grad3(hash_uint3(X, Y, Z), f.x, f.y, f.z), bn_grad3(hash_uint3(X + 1u, Y, Z), f.x - 1.0, f.y, f.z), u),
			mix(bn_grad3(hash_uint3(X, Y + 1u, Z), f.x, f.y - 1.0, f.z), bn_grad3(hash_uint3(X + 1u, Y + 1u, Z), f.x - 1.0, f.y - 1.0, f.z), u), v);
	float r1 = mix(mix(bn_grad3(hash_uint3(X, Y, Z + 1u), f.x, f.y, f.z - 1.0), bn_grad3(hash_uint3(X + 1u, Y, Z + 1u), f.x - 1.0, f.y, f.z - 1.0), u),
			mix(bn_grad3(hash_uint3(X, Y + 1u, Z + 1u), f.x, f.y - 1.0, f.z - 1.0), bn_grad3(hash_uint3(X + 1u, Y + 1u, Z + 1u), f.x - 1.0, f.y - 1.0, f.z - 1.0), u), v);
	return 0.9820 * mix(r0, r1, w);
}

// The Noise Texture node's Fac (fBm, normalized, lacunarity 2): detail octaves past the first, roughness the gain.
float noise_fbm2(vec2 p, float detail, float roughness) {
	float fscale = 1.0;
	float amp = 1.0;
	float maxamp = 0.0;
	float sum = 0.0;
	int n = int(detail);
	for (int i = 0; i <= n; i++) {
		sum += snoise2(fscale * p) * amp;
		maxamp += amp;
		amp *= roughness;
		fscale *= 2.0;
	}
	float rmd = detail - floor(detail);
	if (rmd > 0.0) {
		float sum2 = sum + snoise2(fscale * p) * amp;
		return mix(0.5 * sum / maxamp + 0.5, 0.5 * sum2 / (maxamp + amp) + 0.5, rmd);
	}
	return 0.5 * sum / maxamp + 0.5;
}

float noise_fbm3(vec3 p, float detail, float roughness) {
	float fscale = 1.0;
	float amp = 1.0;
	float maxamp = 0.0;
	float sum = 0.0;
	int n = int(detail);
	for (int i = 0; i <= n; i++) {
		sum += snoise3(fscale * p) * amp;
		maxamp += amp;
		amp *= roughness;
		fscale *= 2.0;
	}
	return 0.5 * sum / maxamp + 0.5;
}

// ------------------------------------------------------------------ Voronoi (2D, Euclidean)
// F1: the nearest cell's distance, its random vector (the node's Color) and its point (the node's Position, in
// cell units). p is already multiplied by the node's Scale.
void voronoi_f1(vec2 p, float randomness, out float dist, out vec3 colour, out vec2 point) {
	vec2 cell_f = floor(p);
	vec2 local = p - cell_f;
	ivec2 cell = ivec2(cell_f);
	dist = 1e9;
	colour = vec3(0.0);
	point = vec2(0.0);
	for (int j = -1; j <= 1; j++) {
		for (int i = -1; i <= 1; i++) {
			ivec2 off = ivec2(i, j);
			vec3 h = hash_cell2(cell + off);
			vec2 pt = vec2(off) + h.xy * randomness;
			float d = distance(pt, local);
			if (d < dist) {
				dist = d;
				colour = h;
				point = pt + cell_f;
			}
		}
	}
}

// F1 and the distance to the cell's edge together (the node's Distance to Edge output, in cell units)
void voronoi_cell_edge(vec2 p, float randomness, out vec3 colour, out float edge) {
	vec2 cell_f = floor(p);
	vec2 local = p - cell_f;
	ivec2 cell = ivec2(cell_f);
	vec2 to_closest = vec2(0.0);
	ivec2 closest = ivec2(0);
	float best = 1e9;
	for (int j = -1; j <= 1; j++) {
		for (int i = -1; i <= 1; i++) {
			ivec2 off = ivec2(i, j);
			vec2 to_pt = vec2(off) + hash_cell2(cell + off).xy * randomness - local;
			float d = dot(to_pt, to_pt);
			if (d < best) {
				best = d;
				to_closest = to_pt;
				closest = off;
			}
		}
	}
	colour = hash_cell2(cell + closest);
	edge = 1e9;
	for (int j = -1; j <= 1; j++) {
		for (int i = -1; i <= 1; i++) {
			ivec2 off = closest + ivec2(i, j);
			vec2 to_pt = vec2(off) + hash_cell2(cell + off).xy * randomness - local;
			vec2 perp = to_pt - to_closest;
			if (dot(perp, perp) > 0.0001) {
				edge = min(edge, dot((to_closest + to_pt) * 0.5, normalize(perp)));
			}
		}
	}
}

// F1 and F2 in one pass, and the nearest cell's random vector: (F2 - F1) / 2 is a cheap stand-in for the distance to
// the cell's edge (exact on the line between the two points, a little short elsewhere, which rounds the corners).
void voronoi_f1f2(vec2 p, float randomness, out vec3 colour, out float f1, out float f2) {
	vec2 cell_f = floor(p);
	vec2 local = p - cell_f;
	ivec2 cell = ivec2(cell_f);
	f1 = 1e9;
	f2 = 1e9;
	colour = vec3(0.0);
	for (int j = -1; j <= 1; j++) {
		for (int i = -1; i <= 1; i++) {
			ivec2 off = ivec2(i, j);
			vec3 h = hash_cell2(cell + off);
			float d = distance(vec2(off) + h.xy * randomness, local);
			if (d < f1) {
				f2 = f1;
				f1 = d;
				colour = h;
			} else if (d < f2) {
				f2 = d;
			}
		}
	}
}
