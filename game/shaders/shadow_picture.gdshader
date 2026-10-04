// A tree's leaves casting their shadow as one picture (scripts/tree_shadow_pictures.gd): a quad that faces the sun
// through the middle of the crown, cut out to the leaves as the sun sees them, from the picture taken from the side
// nearest the sun's, in the atlas the game bakes at startup. Drawn into the shadow map only. The quad's corners are
// in the picture's own coordinates, in the model's metres about the foot of the trunk; the instance's transform is the
// tree's own.
shader_type spatial;
render_mode skip_vertex_transform, cull_disabled, unshaded;

uniform sampler2D atlas : filter_linear_mipmap, repeat_disable;  // white where a leaf is
uniform float frames = 16.0;  // pictures round each tree, the first from the tree's +Z, then turning
uniform float frame_u = 0.0625;  // a picture's width in the atlas
uniform vec2 row = vec2(0.0, 1.0);  // the model's row in the atlas, top and bottom
uniform vec3 to_light = vec3(0.0, 1.0, 0.0);  // towards the sun, as the pictures were taken
uniform float crown_mid = 0.0;  // the height up the trunk of the crown's middle, in the model's metres

varying float frame;

void vertex() {
	vec3 foot = MODEL_MATRIX[3].xyz;
	float s = length(MODEL_MATRIX[0].xyz);
	vec3 right = normalize(cross(vec3(0.0, 1.0, 0.0), to_light) + vec3(0.0001, 0.0, 0.0));
	vec3 up = cross(to_light, right);
	vec3 world = foot + (right * VERTEX.x + up * VERTEX.y + to_light * (crown_mid * to_light.y)) * s;
	// which picture: the sun's side of the tree, in the tree's own space (as in impostor.gdshader)
	vec3 local = (inverse(MODEL_MATRIX) * vec4(to_light, 0.0)).xyz;
	frame = mod(round(fract(-atan(local.x, local.z) / 6.2831853) * frames), frames);
	VERTEX = (VIEW_MATRIX * vec4(world, 1.0)).xyz;
}

void fragment() {
	ALPHA = texture(atlas, vec2((frame + UV.x) * frame_u, mix(row.x, row.y, UV.y))).r;
	ALPHA_SCISSOR_THRESHOLD = 0.5;
}
