// The long grass over the green ground (scripts/grass.gd): patches of the plant portfolio's long grass, cards of thin
// strands crossing, cut out at alpha 0.5. Every chunk of the area draws the same grid of patches; this shader stands
// each on the ground, turns, moves and sizes it by a random number from where it stands, and keeps it only where the
// ground is green (its baked colour), the paths haven't worn it away (as the ground shader wears them,
// ground.gdshaderinc), nothing lies on it (block_tex: rocks, logs, water, boardwalks), and the ground isn't steep.
// Near the paths it grows shorter. It takes the ground's colour where it stands, its card giving the strands' light
// and dark, so it sits in the ground as painted; it's lit as the ground is. It folds away from the hero's trail
// (trail), over and down, and springs back up in recover seconds. Far off it sinks into the ground, by reach.
shader_type spatial;
render_mode cull_disabled, world_vertex_coords, diffuse_lambert, specular_schlick_ggx;

uniform sampler2D card : source_color, filter_linear_mipmap, repeat_disable;
uniform vec3 card_mean = vec3(0.13, 0.25, 0.05);  // the card's average colour where it's opaque (linear)
uniform float ground_tint = 1.0;  // 1: the ground's colour where the patch stands, with the card's light and dark; 0: the card's own

// the ground's, as the ground shader has them (DemoWorld.set_ground_param)
uniform sampler2D grass_tex : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D masks_tex : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D path_noise_tex : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D canopy_tex : hint_default_white, filter_linear_mipmap, repeat_disable;
uniform vec4 bounds = vec4(-112.0, -88.0, 224.0, 176.0);
uniform float canopy_strength = 0.35;
uniform float wear_spread = 1.0;
uniform vec3 worn0 : source_color = vec3(0.576, 0.565, 0.310);
uniform vec3 worn1 : source_color = vec3(0.671, 0.643, 0.384);

// the terrain's heights (DemoWorld.heights), one texel per point of its grid, as half floats, which the graphics card
// interpolates between the points as DemoWorld.height_at does
uniform sampler2D height_tex : filter_linear, repeat_disable;
uniform vec3 height_grid = vec3(-112.0, -88.0, 0.5);  // x and z of its first point, and the step between points
uniform ivec2 height_size = ivec2(449, 353);
// where something lies on the ground: 1 under rocks, logs, water and the area's own models, over the same bounds
uniform sampler2D block_tex : filter_linear, repeat_disable;

uniform float spacing = 0.5;  // metres between the grid's patches
uniform float density : hint_range(0.0, 1.0) = 1.0;  // the share of the patches drawn
uniform float height_scale = 1.0;
uniform float reach = 45.0;  // metres from the camera where the grass has sunk into the ground

// the hero's trail, newest first: x, z, seconds since the hero was there; the grass folds away from it
const int TRAIL = 24;
uniform vec4 trail[TRAIL];
uniform int trail_count = 0;
uniform float trail_reach = 0.0;  // how far from trail[0] any of it reaches, and the fold's radius
uniform float fold_radius = 0.9;  // patches whose foot is this near the trail fold, fully within fold_inner
uniform float fold_inner = 0.5;
uniform float fold_angle = 1.4;  // radians, at most
uniform float recover = 1.6;  // seconds after the hero has gone until it stands up again
uniform float fold_sheen = 0.3;  // how much lighter folded grass looks, its blades lying flat: a trodden lane

global uniform vec2 mood_grade;
global uniform vec3 main_camera_position;

varying vec3 v_ground;
varying float v_canopy;
varying float v_fold;

uint hash_u(uvec2 v) {
	v = v * uvec2(1597334673u, 3812015801u);
	uint n = (v.x ^ v.y) * 1597334673u;
	return n ^ (n >> 16u);
}

float rnd(uvec2 c, uint k) {
	return float(hash_u(c + uvec2(k * 7919u, k * 104729u)) & 0xFFFFFFu) / 16777215.0;
}

float ground_at(vec2 p) {
	return textureLod(height_tex, ((p - height_grid.xy) / height_grid.z + 0.5) / vec2(height_size), 0.0).r;
}

// How green the ground's baked colour is, 0..1: green to yellow-green, not too grey or dark (water, its bed, rock,
// heather, bog, fallen leaves are not).
float green(vec3 lin) {
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

float map_s(float v, float lo, float hi, float to0, float to1) {
	return mix(to0, to1, smoothstep(lo, hi, v));
}

void vertex() {
	vec3 origin = MODEL_MATRIX[3].xyz;
	uvec2 cell = uvec2(ivec2(floor(origin.xz * 64.0)) + ivec2(1 << 20));
	vec2 foot = origin.xz + (vec2(rnd(cell, 1u), rnd(cell, 2u)) - 0.5) * spacing * 0.6;
	vec2 uv = (foot - bounds.xy) / bounds.zw;
	float far = 1.0 - smoothstep(reach * 0.7, reach, distance(vec3(foot.x, origin.y, foot.y), main_camera_position));
	float pick = rnd(cell, 3u);

	// is there grass here: near enough, on the screen, nothing lying on it, green ground, not worn away by the paths,
	// not steep. Most of the grid is dropped (and its corners all put at one point, so nothing of it is drawn) after
	// reading little: the graphics card's time goes on the patches' corners, every one of which works this out.
	float keep = 0.0;
	float worn = 0.0;
	vec3 ground_col = vec3(0.0);
	float g0 = 0.0;
	vec2 slope = vec2(0.0);
	if (far > 0.0 && pick < density && all(greaterThan(uv, vec2(0.0))) && all(lessThan(uv, vec2(1.0)))) {
		g0 = ground_at(foot);
		vec4 clip = PROJECTION_MATRIX * (VIEW_MATRIX * vec4(foot.x, g0 + 0.25, foot.y, 1.0));
		if (clip.w > 0.0 && all(lessThan(abs(clip.xy), vec2(clip.w * 1.12 + 0.6)))) {  // the patch's reach past the edges
			keep = density * (1.0 - smoothstep(0.03, 0.2, textureLod(block_tex, uv, 0.0).r));
		}
		if (pick < keep) {
			ground_col = textureLod(grass_tex, uv, 3.0).rgb;
			vec4 m = textureLod(masks_tex, uv, 0.0);
			float e = m.r * 5.0 - 0.5;
			float sp = wear_spread;
			float wear = max(map_s(e, 0.45, 1.9, 1.0 - 0.15 * sp, 0.0), 0.55 * sp * map_s(e, 1.0, 1.0 + 2.4 * max(sp, 0.01), 1.0, 0.0));
			worn = map_s(e, 0.7, 2.1 + 1.4 * sp, 1.0, 0.0);
			keep *= green(ground_col) * (1.0 - smoothstep(0.15, 0.55, wear + 2.0 * (m.b - 0.5) + 1.2 * sp * (m.g - 0.5)));
			if (pick < keep) {
				slope = vec2(ground_at(foot + vec2(0.5, 0.0)) - g0, ground_at(foot + vec2(0.0, 0.5)) - g0) / 0.5;
				keep *= 1.0 - smoothstep(0.6, 0.9, length(slope));
			}
		}
	}
	if (pick >= keep) {
		VERTEX = vec3(origin.x, -10000.0, origin.z);
	} else {
		// turned and sized at random; shorter where it's sparse (toward the paths) and trodden; sunk in far off
		float a = rnd(cell, 4u) * TAU;
		mat2 turn = mat2(vec2(cos(a), sin(a)), vec2(-sin(a), cos(a)));
		vec3 local = VERTEX - origin;
		float s = mix(0.85, 1.15, rnd(cell, 5u));
		vec2 xz = turn * local.xz * s;
		float h = max(local.y, 0.0) * s * height_scale * mix(0.55, 1.0, smoothstep(0.0, 0.6, keep / max(density, 0.01))) * (1.0 - 0.45 * worn) * far;

		// folded away from the hero's trail: tipped over about its foot, away from the trail and the way the hero
		// walked, as far as the nearest part of the trail says, which springs back as it ages
		float fold = 0.0;
		vec2 away = vec2(0.0);
		if (trail_count > 1 && distance(foot, trail[0].xy) < trail_reach) {
			for (int i = 0; i + 1 < TRAIL; i++) {
				if (i + 1 >= trail_count) {
					break;
				}
				vec2 p0 = trail[i].xy;
				vec2 p1 = trail[i + 1].xy;
				vec2 seg = p1 - p0;
				float len2 = dot(seg, seg);
				float t = len2 > 1e-6 ? clamp(dot(foot - p0, seg) / len2, 0.0, 1.0) : 0.0;
				vec2 off = foot - (p0 + seg * t);
				float age = mix(trail[i].z, trail[i + 1].z, t);
				float f = (1.0 - smoothstep(fold_inner, fold_radius, length(off))) * (1.0 - smoothstep(recover * 0.35, recover, age));
				if (f > fold) {
					fold = f;
					vec2 walked = len2 > 1e-6 ? -seg / sqrt(len2) : vec2(0.0);
					vec2 dir = off + walked * 0.35;
					away = dot(dir, dir) > 1e-8 ? normalize(dir) : vec2(1.0, 0.0);
				}
			}
		}
		v_fold = fold;
		float bend = fold * fold_angle;
		xz += away * h * sin(bend);
		h *= cos(bend);
		// on the ground: at the foot's height, along its slope
		VERTEX = vec3(foot.x + xz.x, g0 + dot(slope, xz) + h, foot.y + xz.y);
		NORMAL = normalize(vec3(-slope.x, 1.0, -slope.y));  // lit as the ground is
		// the ground's colour where it stands, as the ground shader paints it: trampled toward the paths
		vec2 pn = textureLod(path_noise_tex, uv, 0.0).rg;
		v_ground = mix(ground_col, mix(worn0, worn1, clamp((pn.g - 0.3) / 0.4, 0.0, 1.0)), worn * 0.5);
		v_canopy = mix(1.0, textureLod(canopy_tex, uv, 0.0).r, canopy_strength);
	}
}

void fragment() {
	vec4 c = texture(card, UV);
	// thin strands thin out in the card's smaller mipmaps; making up for it keeps the grass as thick far off
	vec2 texels = UV * vec2(textureSize(card, 0));
	float lod = max(0.0, 0.5 * log2(max(dot(dFdx(texels), dFdx(texels)), dot(dFdy(texels), dFdy(texels)))));
	float a = c.a * (1.0 + 0.25 * lod);
	if (a < 0.5) {
		discard;
	}
	vec3 col = mix(c.rgb, v_ground * c.rgb / card_mean, ground_tint);
	col *= 1.0 + fold_sheen * v_fold * vec3(1.0, 1.0, 0.7);
	float grey = dot(col, vec3(0.2126, 0.7152, 0.0722));
	ALBEDO = mix(vec3(grey), col, mood_grade.x) * mood_grade.y;
	ALPHA = a;
	ALPHA_SCISSOR_THRESHOLD = 0.5;
	ROUGHNESS = 0.93;
	SPECULAR = 0.2;
	AO = v_canopy;
	if (!FRONT_FACING) {  // both sides lit as the ground is, not turned round on the back
		NORMAL = -NORMAL;
	}
}
