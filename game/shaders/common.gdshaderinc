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

// How green a colour of the ground is, 0..1 (linear colour in): green to yellow-green, not too grey or dark, as
// water, its bed, rock, heather, the bog and fallen leaves aren't. The long grass grows where the ground is green
// (shaders/grass.gdshader), and its ground texture lies there (ground.gdshaderinc).
float ground_green(vec3 lin) {
	vec3 c = pow(max(lin, vec3(0.0)), vec3(1.0 / 2.2));
	float mx = max(c.r, max(c.g, c.b));
	float d = mx - min(c.r, min(c.g, c.b));
	if (d < 1e-4) {
		return 0.0;
	}
	float h = mx == c.r ? mod((c.g - c.b) / d, 6.0) : (mx == c.g ? (c.b - c.r) / d + 2.0 : (c.r - c.g) / d + 4.0);
	h *= 60.0;
	return smoothstep(45.0, 55.0, h) * (1.0 - smoothstep(140.0, 150.0, h)) * smoothstep(0.15, 0.25, d / mx)
			* smoothstep(0.28, 0.34, mx);
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

// Like faded_out, but for a fade that changes across a tree, so that it reads as the tree's opacity changing (the
// cone): with cone_style 0, in patches a few centimetres across; with 1, in a fine even dither on the screen, in
// blocks of two pixels, which the ambient occlusion, worked out at half resolution, leaves alone.
global uniform float cone_style;

bool faded_fine(float fade, vec3 world, vec2 pixel) {
	if (fade <= 0.0) {
		return false;
	}
	if (cone_style > 0.5) {
		vec2 b = floor(pixel * 0.5);
		float n = fract(52.9829189 * fract(0.06711056 * b.x + 0.00583715 * b.y));  // interleaved gradient noise
		return fade > clamp(n, 0.001, 0.999);
	}
	float n = 0.6 * value_noise3(world * 11.0) + 0.4 * value_noise3(world * 27.0 + 9.0);
	return fade > clamp((n - 0.5) * 1.7 + 0.5, 0.001, 0.999);
}

// The cone (cut_trees "cone" in scripts/world.gd): from the edges of the screen at the camera to the hero, whatever of
// a tree is inside it fades away, wholly at its middle and less and less towards its edges. On the screen it shrinks
// with depth, from the whole screen at the camera to round the hero at the hero's depth, and stops a little past the
// hero. cone_hero: where it ends round the hero, its middle and half its size (screen UV); cone_shape: the hero's depth
// from the camera (metres), the share of the cone, from its edge in, that fades gradually, how its size goes with depth
// (1: evenly), and how strongly it's on, 0..1 (1 with cut_trees "cone", 0 otherwise).
global uniform vec4 cone_hero;
global uniform vec4 cone_shape;

float cone_fade(vec2 screen_uv, vec3 vertex_view, vec3 camera_world) {
	if (cone_shape.w <= 0.0 || distance(camera_world, main_camera_position) > 0.05) {
		return 0.0;
	}
	float depth = -vertex_view.z;
	float s = pow(clamp(depth / cone_shape.x, 0.0, 1.0), cone_shape.z);
	vec2 d = abs(screen_uv - mix(vec2(0.5), cone_hero.xy, s)) / mix(vec2(0.5), cone_hero.zw, s);
	float q = pow(pow(d.x, 4.0) + pow(d.y, 4.0), 0.25);  // 0 at the cone's middle, 1 at its edge; its corners round
	float past = smoothstep(cone_shape.x + 0.5, cone_shape.x + 1.5, depth);  // past the hero's far side
	return cone_shape.w * (1.0 - smoothstep(1.0 - cone_shape.y, 1.0, q)) * (1.0 - past);
}

// How see-through a tree is (sight_veil.x, which scripts/world.gd sets in _cut_veil while the trees in front of the
// hero cover enough of the area round it): the share of its pixels that let what's behind it through, evenly over the
// whole tree, with faded_fine; but not below height (metres above its foot, sight_veil.y), which stays solid, for a
// tree without a stump to stand on (_leave; 0 for one with). Never in the shadow pass.
float veil_fade(vec2 veil, float height, vec3 camera_world) {
	return height < veil.y || distance(camera_world, main_camera_position) > 0.05 ? 0.0 : veil.x;
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

// The crown cut (crown_cut in scripts/world.gd, set every frame): with the camera high, no tree comes near it, nor
// stands tall in front of the hero. Each tree ends below a ball round the camera, crown_cut.x metres across (its
// radius; 0 for none): one whose trunk enters the ball ends where its trunk does, so the nearer the camera a tree
// stands, the lower it ends, and nothing of it is left floating; or every tree ends crown_cut.y metres above its foot
// (0 for no such limit). Its top dissolves over crown_cut.z metres up to the cut. crown_cut.w is how strongly it's on,
// 0..1, from the camera's pitch: as it falls, the cut rises out of the way, so the trees grow back as the camera comes
// down. Never in the shadow pass, so the shadows stay whole. node is the tree's foot (NODE_POSITION_WORLD).
global uniform vec4 crown_cut;

float crown_fade(vec3 world, vec3 node, vec3 camera_world) {
	if (crown_cut.w <= 0.0 || distance(camera_world, main_camera_position) > 0.05) {
		return 0.0;
	}
	float cut = 1e6;
	float d = distance(node.xz, main_camera_position.xz);
	if (crown_cut.x > d) {
		cut = main_camera_position.y - node.y - sqrt(crown_cut.x * crown_cut.x - d * d);
	}
	if (crown_cut.y > 0.0) {
		cut = min(cut, crown_cut.y);
	}
	cut += (1.0 - crown_cut.w) * 40.0;
	return smoothstep(cut - crown_cut.z, cut, world.y - node.y);
}

// Autumn: a leaf's green turned yellow, orange or red, as scripts/world.gd sets it per tree (autumn, from the tree's
// tint in its area's layout): x how far, 0..1, y which way, 0 yellow, 0.5 orange, 1 red. Brighter greens turn
// brighter, so the leaves keep their light and shade.
vec3 autumn_tint(vec3 c, vec2 autumn) {
	if (autumn.x <= 0.0) {
		return c;
	}
	vec3 yellow = vec3(0.80, 0.50, 0.035);
	vec3 orange = vec3(0.70, 0.20, 0.02);
	vec3 red = vec3(0.42, 0.035, 0.012);
	vec3 tone = autumn.y < 0.5 ? mix(yellow, orange, autumn.y * 2.0) : mix(orange, red, autumn.y * 2.0 - 1.0);
	float lum = dot(c, vec3(0.2126, 0.7152, 0.0722));
	return mix(c, tone * clamp(lum * 7.0, 0.2, 1.4), autumn.x);
}
