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

// The x-ray (cut_trees "xray" in scripts/world.gd, with xray_on): in a window in the lower middle of the screen,
// whatever of a tree is nearer the camera than the hero is cut away, and only that, so you see the hero and the ground
// round and in front of it. The window, xray_rect: half its width, as a fraction of the screen's; how far down its top
// is; how soft its edges are; and how round its top corners, as fractions of the screen's height. It reaches down past
// the bottom of the screen. And with "front" too: whatever of a tree comes within xray_near of the camera (from and to,
// metres; 0 for none) fades away, so its branches don't sweep across the screen.
global uniform float xray_on;
global uniform vec4 xray_rect;
global uniform vec2 xray_near;

// How much of a tree's pixel the x-ray cuts away, 0..1: in the window, softly at its edges, and nearer the camera
// than the hero's far side, so the branches it stands in go too, softly over a metre beyond that; and near the
// camera. Never in the shadow pass.
float xray_fade(vec2 screen_uv, vec2 viewport, vec3 vertex_view, mat4 view, vec3 camera_world) {
	if (distance(camera_world, main_camera_position) > 0.05) {
		return 0.0;
	}
	float near = xray_near.y > 0.0 ? 1.0 - smoothstep(xray_near.x, xray_near.y, length(vertex_view)) : 0.0;
	if (xray_on < 0.5) {
		return near;
	}
	float aspect = viewport.x / viewport.y;
	vec2 p = vec2((screen_uv.x - 0.5) * aspect, screen_uv.y);  // in screen heights, across from the middle and down
	float r = xray_rect.w;
	vec2 q = abs(p - vec2(0.0, (xray_rect.y + 4.0) * 0.5)) - vec2(xray_rect.x * aspect, (4.0 - xray_rect.y) * 0.5) + r;
	float d = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;  // from the window's edge, below 0 inside
	float inside = 1.0 - smoothstep(-xray_rect.z, xray_rect.z, d);
	float hero = -(view * vec4(hero_position + vec3(0.0, 0.9, 0.0), 1.0)).z;
	return max(inside * (1.0 - smoothstep(hero + 0.5, hero + 1.5, -vertex_view.z)), near);
}

// How much a pixel of a tree fades out, 0..1. A tree in the way between the camera and the hero fades out whole
// (sight: the tree's instance uniform, which scripts/world.gd sets in update_sight), and so do trees standing near
// a high camera, as the mockups hide them (within tree_fade_radius of it along the ground, which stops well short of
// the hero); and whatever the camera is about to touch, such as a branch right in front of a low camera. Never in the
// shadow pass, so the shadows stay whole. node is the tree's position (NODE_POSITION_WORLD).
float tree_fade(float sight, vec3 vertex_view, vec3 node, vec3 camera_world) {
	if (hero_fade_on < 0.5 || distance(camera_world, main_camera_position) > 0.05) {
		return 0.0;
	}
	float near = 1.0 - smoothstep(1.0, 2.5, -vertex_view.z);
	float camera = 1.0 - smoothstep(tree_fade_radius - 2.5, tree_fade_radius, distance(node.xz, main_camera_position.xz));
	return max(sight, max(near, camera));
}
