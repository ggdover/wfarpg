// The mockups' low-poly material: faceted shapes coloured per face through the vertex colours, like LowPoly in
// mockups/forest_cam.py and Bark in assets/trees/treegen.py. Define HERO_FADE before including it for things that
// should fade out between the camera and the hero, like trees. The including shader declares the shader type.
#include "res://shaders/common.gdshaderinc"

uniform float roughness = 0.88;
uniform float specular_level = 0.25;
// the second UV map carries ambient occlusion baked in Blender (1 where none is baked); how much it also dims the
// sun, for the insides of crowns that the shadow maps miss
uniform float ao_light_affect = 0.2;
// the mood's grade: saturation and value, like the Grade node in the mockups
global uniform vec2 mood_grade;

void fragment() {
#ifdef HERO_FADE
	float fade = max(hero_fade(VERTEX, VIEW_MATRIX, PROJECTION_MATRIX, CAMERA_POSITION_WORLD, VIEWPORT_SIZE),
			tree_fade(NODE_POSITION_WORLD, CAMERA_POSITION_WORLD));
	if (fade > bayer4(FRAGCOORD.xy)) {
		discard;
	}
#endif
	vec3 c = srgb_to_linear(COLOR.rgb);
	float grey = dot(c, vec3(0.2126, 0.7152, 0.0722));
	ALBEDO = mix(vec3(grey), c, mood_grade.x) * mood_grade.y;
	ROUGHNESS = roughness;
	SPECULAR = specular_level;
	AO = UV2.x;
	AO_LIGHT_AFFECT = ao_light_affect;
}
