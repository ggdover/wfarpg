// The mockups' low-poly material: faceted shapes coloured per face through the vertex colours, like LowPoly in
// mockups/forest_cam.py and Bark in assets/trees/treegen.py. Define HERO_FADE before including it for things that
// fade out when they're in the way of the camera, like trees, and NO_XRAY too for those the x-ray leaves alone. The
// including shader declares the shader type.
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

void fragment() {
#ifdef HERO_FADE
	float fade = tree_fade(sight_fade, VERTEX, NODE_POSITION_WORLD, CAMERA_POSITION_WORLD);
	float soft = 0.0;  // the cone's, or the veil's
	vec3 world = (INV_VIEW_MATRIX * vec4(VERTEX, 1.0)).xyz;
#ifndef NO_XRAY
	fade = max(fade, xray_fade(SCREEN_UV, VIEWPORT_SIZE, VERTEX, VIEW_MATRIX, CAMERA_POSITION_WORLD));
	soft = max(cone_fade(SCREEN_UV, VERTEX, CAMERA_POSITION_WORLD),
			veil_fade(sight_veil, world.y - NODE_POSITION_WORLD.y, CAMERA_POSITION_WORLD));  // the stump stays
#endif
	if (faded_out(fade, world) || faded_fine(soft, world, FRAGCOORD.xy)) {
		discard;
	}
#endif
	vec3 c = srgb_to_linear(COLOR.rgb);
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
