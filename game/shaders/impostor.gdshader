// A distant tree as an impostor (scripts/tree_impostors.gd): one quad that turns about its upright axis to face the
// camera, showing the pictures of the tree taken from the two sides nearest the camera's, blended, from the atlas the
// game bakes at startup. It's lit like the leaf cards' crowns, with a normal that bulges out from the middle of the
// picture, and takes the mood's grade. The quad's mesh holds its size and its row in the atlas, and its material the
// pictures' width; the instance's transform is the tree's own, so the pictures follow the tree's turn.
shader_type spatial;
render_mode skip_vertex_transform, cull_disabled, diffuse_lambert, specular_schlick_ggx;

#include "res://shaders/common.gdshaderinc"

uniform sampler2D atlas : source_color, filter_linear_mipmap, repeat_disable;
uniform float frames = 8.0;  // pictures round each tree, the first from the tree's +Z, then turning
uniform float frame_u = 0.125;  // a picture's width in the atlas
instance uniform vec2 autumn = vec2(0.0);  // the tree's leaves turned (autumn_tint in common.gdshaderinc)
global uniform vec2 mood_grade;

varying vec3 pick;  // the two pictures' columns and how far between them
varying vec2 bulge;  // where on the quad, -1..1 across and up, for the normal

void vertex() {
	vec3 centre = MODEL_MATRIX[3].xyz;
	float s = length(MODEL_MATRIX[0].xyz);
	vec3 to_cam = CAMERA_POSITION_WORLD - centre;
	vec3 face = normalize(vec3(to_cam.x, 0.0, to_cam.z) + vec3(0.0001, 0.0, 0.0));
	vec3 right = vec3(face.z, 0.0, -face.x);
	vec3 world = centre + right * (VERTEX.x * s) + vec3(0.0, VERTEX.y * s, 0.0);
	// which side of the tree the camera is on, in the tree's own space: the pictures are taken turning the tree
	// by 1/frames of a turn each, so picture f looks from the tree's direction at -f/frames of a turn from +Z
	vec3 local = (inverse(MODEL_MATRIX) * vec4(CAMERA_POSITION_WORLD, 1.0)).xyz;
	float f = fract(-atan(local.x, local.z) / 6.2831853) * frames;
	float a = floor(f);
	pick = vec3(a, mod(a + 1.0, frames), f - a);
	bulge = vec2(UV2.x * 2.0 - 1.0, 1.0 - UV2.y * 2.0);
	VERTEX = (VIEW_MATRIX * vec4(world, 1.0)).xyz;
	NORMAL = (VIEW_MATRIX * vec4(face, 0.0)).xyz;
}

void fragment() {
	vec4 c = mix(texture(atlas, vec2((pick.x + UV.x) * frame_u, UV.y)), texture(atlas, vec2((pick.y + UV.x) * frame_u, UV.y)), pick.z);
	vec3 col = c.rgb / max(c.a, 0.002);  // the pictures' empty parts are black, which their smaller mipmaps mix in
	col = mix(col, autumn_tint(col, autumn), smoothstep(0.0, 0.02, col.g - max(col.r, col.b)));  // the leaves, not the bark
	float grey = dot(col, vec3(0.2126, 0.7152, 0.0722));
	ALBEDO = mix(vec3(grey), col, mood_grade.x) * mood_grade.y;
	ALPHA = c.a;
	ALPHA_SCISSOR_THRESHOLD = 0.5;
	NORMAL = normalize(vec3(bulge.x, bulge.y * 0.7, sqrt(max(1.0 - dot(bulge, bulge), 0.1))));
	ROUGHNESS = 0.75;
	SPECULAR = 0.25;
}
