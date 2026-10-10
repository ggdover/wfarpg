// The mockups' low-poly material: faceted shapes coloured per face through the vertex colours, like LowPoly in
// mockups/forest_cam.py and Bark in assets/trees/treegen.py. Define HERO_FADE before including it for things that
// fade out when they're in the way of the camera, like trees, and NO_XRAY too for those the x-ray leaves alone; and
// BARK for a portfolio tree's bark (its trunk, stump and bare trunk), which textures the trunk. The including shader
// declares the shader type.
#include "res://shaders/common.gdshaderinc"

uniform float roughness = 0.88;
uniform float specular_level = 0.25;
// the second UV map carries ambient occlusion baked in Blender (1 where none is baked); how much it also dims the
// sun, for the insides of crowns that the shadow maps miss
uniform float ao_light_affect = 0.2;
// the mood's grade: saturation and value, like the Grade node in the mockups
global uniform vec2 mood_grade;
#ifdef HERO_FADE
instance uniform float sight_fade = 0.0;  // fading out of the way (tree_fade in shaders/common.gdshaderinc)
#ifndef NO_XRAY
instance uniform vec2 sight_veil = vec2(0.0);  // how see-through, and from how high (veil_fade)
#endif
#endif
#ifdef PEBBLE
global uniform vec3 pebble_colour;
#endif
#ifdef BARK
// The species' bark (assets/trees/make_bark.py), on the trunk's facets: each shows its own window of it, at its real
// size (assets/trees/treegen.py, Tree.tube); the branches' faces sit at UV (-10, -10) and keep their colour. bark_foot
// is the rougher bark of the trunk's foot, blended in by the colour's alpha, through its own alpha, a noise, so the
// edge is ragged; the colour tints it, 0.5 for none.
uniform sampler2D bark_upper : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D bark_foot : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
global uniform float bark_on;  // 0: the trunks plain, as before the bark (F2's Bark textures)
#endif

void fragment() {
#ifdef HERO_FADE
	float fade = tree_fade(sight_fade, VERTEX, NODE_POSITION_WORLD, CAMERA_POSITION_WORLD);
	float soft = 0.0;  // the cone's, or the veil's
	vec3 world = (INV_VIEW_MATRIX * vec4(VERTEX, 1.0)).xyz;
#ifndef NO_XRAY
	fade = max(fade, xray_fade(SCREEN_UV, VIEWPORT_SIZE, VERTEX, VIEW_MATRIX, CAMERA_POSITION_WORLD));
	soft = max(cone_fade(SCREEN_UV, VERTEX, CAMERA_POSITION_WORLD),
			veil_fade(sight_veil, world.y - NODE_POSITION_WORLD.y, CAMERA_POSITION_WORLD));  // the stump stays
	soft = max(soft, crown_fade(world, NODE_POSITION_WORLD, CAMERA_POSITION_WORLD));
#endif
	if (faded_out(fade, world) || faded_fine(soft, world, FRAGCOORD.xy)) {
		discard;
	}
#endif
	vec3 c = srgb_to_linear(COLOR.rgb);
#ifdef BARK
	if (UV.x > -5.0 && bark_on > 0.5) {
		vec4 foot = texture(bark_foot, UV);
		float below = smoothstep(0.4, 0.6, COLOR.a + (foot.a - 0.5) * 0.6);
		c *= 2.0 * mix(texture(bark_upper, UV).rgb, foot.rgb, below);
	} else if (UV.x > -5.0) {  // plain, in the barks' average colours, their smallest mipmaps
		c *= 2.0 * mix(textureLod(bark_upper, UV, 12.0).rgb, textureLod(bark_foot, UV, 12.0).rgb, smoothstep(0.4, 0.6, COLOR.a));
	}
#endif
#ifdef PEBBLE
	c = pebble_colour * dot(c, vec3(0.2126, 0.7152, 0.0722)) / 0.42;  // 0.42: the pebbles' average brightness
#endif
	float grey = dot(c, vec3(0.2126, 0.7152, 0.0722));
	ALBEDO = mix(vec3(grey), c, mood_grade.x) * mood_grade.y;
	ROUGHNESS = roughness;
	SPECULAR = specular_level;
	AO = UV2.x;
	AO_LIGHT_AFFECT = ao_light_affect;
}
