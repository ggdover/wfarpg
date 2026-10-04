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

// How much a pixel of a tree fades out, 0..1. A tree in the way between the camera and the hero fades out whole
// (sight: the tree's instance uniform, which scripts/world.gd sets in update_sight), and so do trees standing near
// a high camera, as the mockups hide them (within tree_fade_radius of it along the ground); and anything much nearer
// the camera than the hero fades too, such as branches right in front of a low camera. Never in the shadow pass, so
// the shadows stay whole. node is the tree's position (NODE_POSITION_WORLD).
float tree_fade(float sight, vec3 vertex_view, mat4 view_matrix, vec3 node, vec3 camera_world) {
	if (hero_fade_on < 0.5 || distance(camera_world, main_camera_position) > 0.05) {
		return 0.0;
	}
	float hero_depth = -(view_matrix * vec4(hero_position + vec3(0.0, 0.9, 0.0), 1.0)).z;
	float near = 1.0 - smoothstep(0.15, 0.3, -vertex_view.z / max(hero_depth, 1.0));
	float camera = 1.0 - smoothstep(tree_fade_radius - 2.5, tree_fade_radius, distance(node.xz, main_camera_position.xz));
	return max(sight, max(near, camera));
}
