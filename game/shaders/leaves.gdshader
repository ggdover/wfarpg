// The tree portfolio's leaf cards: the card's colour, cut out at alpha 0.5 like the leaf materials in
// assets/trees/treegen.py, drawn on both sides. They fade out when they're in the way of the camera. As a tree goes
// see-through, the cards its thinned version leaves out (scripts/models.gd, Models.thinned; UV2.y = 1) go first.
shader_type spatial;
render_mode cull_disabled, diffuse_lambert, specular_schlick_ggx;

#include "res://shaders/common.gdshaderinc"

uniform sampler2D card : source_color, filter_linear_mipmap, repeat_disable;
uniform float roughness = 0.75;
instance uniform float sight_fade = 0.0;  // fading out of the way (tree_fade in shaders/common.gdshaderinc)
instance uniform vec2 sight_veil = vec2(0.0);  // how see-through, and from how high (veil_fade)
instance uniform float sight_thin = 0.0;  // how see-through the cards its thinned version leaves out are
uniform float specular_level = 0.25;
// ambient occlusion baked in Blender, in UV2.x (see tools/build_demo.py, bake_ao)
uniform float ao_light_affect = 0.2;
// The cards' normals point out from the crown, so a crown shades as one volume. Like Blender, Godot turns the normal
// round on a card's back face, which darkens the cards that face into the crown; true keeps the crown's normal on both
// faces instead, for brighter, flatter crowns than in the mockups.
uniform bool crown_normals = false;
global uniform vec2 mood_grade;

void fragment() {
	float fade = max(tree_fade(sight_fade, VERTEX, NODE_POSITION_WORLD, CAMERA_POSITION_WORLD),
			xray_fade(SCREEN_UV, VIEWPORT_SIZE, VERTEX, VIEW_MATRIX, CAMERA_POSITION_WORLD));
	vec3 world = (INV_VIEW_MATRIX * vec4(VERTEX, 1.0)).xyz;
	vec2 veil = vec2(UV2.y > 0.5 ? max(sight_veil.x, sight_thin) : sight_veil.x, sight_veil.y);
	float soft = max(cone_fade(SCREEN_UV, VERTEX, CAMERA_POSITION_WORLD), veil_fade(veil, 1e6, CAMERA_POSITION_WORLD));  // leaves all the way down
	if (faded_out(fade, world) || faded_fine(soft, world, FRAGCOORD.xy)) {
		discard;
	}
	vec4 c = texture(card, UV);
	float grey = dot(c.rgb, vec3(0.2126, 0.7152, 0.0722));
	ALBEDO = mix(vec3(grey), c.rgb, mood_grade.x) * mood_grade.y;
	ALPHA = c.a;
	ALPHA_SCISSOR_THRESHOLD = 0.5;
	ROUGHNESS = roughness;
	SPECULAR = specular_level;
	AO = UV2.x;
	AO_LIGHT_AFFECT = ao_light_affect;
	if (crown_normals && !FRONT_FACING) {
		NORMAL = -NORMAL;
	}
}
