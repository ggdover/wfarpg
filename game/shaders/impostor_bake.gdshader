// Pictures a tree for its impostor (scripts/tree_impostors.gd): its colours as they are, unlit, the leaf cards cut out
// at alpha 0.5 like the leaves' shader, darkened by the occlusion baked into the tree (UV2.x) about as much as the
// game's light shows it. The impostor's own shader lights the picture (impostor.gdshader). With silhouette, only the
// leaves, in white, for the pictures its shadow is cast from (scripts/tree_shadow_pictures.gd).
shader_type spatial;
render_mode unshaded, cull_disabled;

#include "res://shaders/common.gdshaderinc"

uniform sampler2D card : source_color, filter_linear_mipmap, repeat_disable;
uniform bool leaf = false;
uniform bool silhouette = false;

void fragment() {
	vec4 c = leaf ? texture(card, UV) : vec4(srgb_to_linear(COLOR.rgb), silhouette ? 0.0 : 1.0);
	ALBEDO = silhouette ? vec3(1.0) : c.rgb * mix(1.0, UV2.x, 0.6);
	ALPHA = c.a;
	ALPHA_SCISSOR_THRESHOLD = 0.5;
}
