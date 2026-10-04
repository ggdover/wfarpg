// Shared by the game's shaders.

// The hero and the main camera, set every frame by the camera rig (scripts/camera_rig.gd).
global uniform vec3 hero_position;
global uniform vec3 main_camera_position;
global uniform float hero_fade_on;
// trees whose trunks stand closer than this to the camera (along the ground) fade out (scripts/camera_rig.gd)
global uniform float tree_fade_radius;

// The models' vertex colours are stored sRGB-encoded (see tools/build_demo.py); this decodes them.
vec3 srgb_to_linear(vec3 c) {
	return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), c));
}

// A random number, 0..1, for a cell of a 3D grid.
float hash_cell3(vec3 c) {
	uvec3 v = uvec3(ivec3(c)) * uvec3(1597334673u, 3812015801u, 2798796415u);
	return float((v.x ^ v.y ^ v.z) * 1597334673u) / 4294967295.0;
}

// Smooth value noise in 3D, 0..1, with features about a cell across.
float value_noise3(vec3 p) {
	vec3 i = floor(p);
	vec3 f = p - i;
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(mix(hash_cell3(i), hash_cell3(i + vec3(1, 0, 0)), f.x),
			mix(hash_cell3(i + vec3(0, 1, 0)), hash_cell3(i + vec3(1, 1, 0)), f.x), f.y),
			mix(mix(hash_cell3(i + vec3(0, 0, 1)), hash_cell3(i + vec3(1, 0, 1)), f.x),
			mix(hash_cell3(i + vec3(0, 1, 1)), hash_cell3(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}

// Whether a pixel of something fading out (fade 0..1) is gone. It goes in patches that grow as it fades, a few
// tenths of a metre across, rather than in a dither of single pixels: the ambient occlusion (SSAO, worked out at
// half resolution) turns the ground between single dithered pixels black.
bool faded_out(float fade, vec3 world) {
	if (fade <= 0.0) {
		return false;
	}
	float n = 0.65 * value_noise3(world * 3.0) + 0.35 * value_noise3(world * 8.0 + 17.0);
	return fade > clamp((n - 0.5) * 1.7 + 0.5, 0.001, 0.999);
}

// How much to fade a pixel of something standing between the camera and the hero, so trees never hide it: a round,
// dithered hole about the hero's size, and everything much nearer the camera than the hero (a crown right under a
// high camera). 0 elsewhere, and in the shadow pass, so the shadows stay whole.
float hero_fade(vec3 vertex_view, mat4 view_matrix, mat4 projection_matrix, vec3 camera_world, vec2 viewport) {
	if (hero_fade_on < 0.5 || distance(camera_world, main_camera_position) > 0.05) {
		return 0.0;
	}
	vec3 hero_view = (view_matrix * vec4(hero_position + vec3(0.0, 0.9, 0.0), 1.0)).xyz;
	float hero_depth = -hero_view.z;
	float depth = -vertex_view.z;
	float in_front = hero_depth - depth;
	if (in_front < 0.5) {
		return 0.0;
	}
	vec4 hc = projection_matrix * vec4(hero_view, 1.0);
	vec4 fc = projection_matrix * vec4(vertex_view, 1.0);
	vec2 d = (fc.xy / fc.w - hc.xy / hc.w) * vec2(viewport.x / viewport.y, 1.0);
	float radius = 3.5 * abs(projection_matrix[1][1]) / max(hero_depth, 1.0);  // about 3.5 m round the hero (Vulkan flips Y)
	float hole = (1.0 - smoothstep(radius * 0.7, radius, length(d))) * smoothstep(0.5, 2.5, in_front);
	float near = 1.0 - smoothstep(0.15, 0.3, depth / hero_depth);
	return max(hole, near);
}

// How much a whole tree fades: those standing near a high camera fade out, as the mockups hide them, so the camera
// looks down on the forest floor. node is the tree's position (NODE_POSITION_WORLD). Not in the shadow pass.
float tree_fade(vec3 node, vec3 camera_world) {
	if (hero_fade_on < 0.5 || distance(camera_world, main_camera_position) > 0.05) {
		return 0.0;
	}
	return 1.0 - smoothstep(tree_fade_radius - 2.5, tree_fade_radius, distance(node.xz, main_camera_position.xz));
}
