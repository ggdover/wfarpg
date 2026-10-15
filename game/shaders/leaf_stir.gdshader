// The fallen leaves' disturbance (scripts/leaf_litter.gd): a map over the piles where the leaves have been moved to,
// which keeps it, so they stay where they were pushed and kicked until something moves into them again (the user,
// 15 October: they shouldn't move back by themselves). This brush paints it round someone walking through the leaves
// (the hero, at the moment), every frame, reading the map as it is (the screen texture, the map's own render target,
// which is never cleared). Texel by texel, for the leaves lying there:
//   red, green: how far they've been pushed, metres along x and z, as 0.5 + d / (2 * max_push)
//   blue: how trodden the pile is there, 0..1, which presses it down and has the leaves that were kicked up land a
//         little way off
// As the walker comes alongside them, the leaves move toward the new push: sideways out of the walker's way, more the
// nearer it (those right in it to one side or the other), so a lane opens along the way and the leaves crowd into
// banks at its sides. They move only where the step is near, or pushes further than it did before, and are never
// pulled back toward where they lay.
shader_type canvas_item;
render_mode blend_disabled;

uniform sampler2D map : hint_screen_texture, filter_nearest;
uniform vec2 rect_origin;  // world x and z of the brush's corner (it's drawn as a square round the walker)
uniform vec2 rect_size;  // and its size, metres
uniform vec2 walker;  // world x and z of whoever walks through the leaves
uniform vec2 heading = vec2(1.0, 0.0);  // which way they're going
uniform float radius = 0.75;  // metres round them the leaves move
uniform float lane = 0.3;  // metres a leaf right at the step is pushed: none is left closer
uniform float max_push = 0.5;  // metres the map can hold
uniform float rate = 0.3;  // how far toward the new push this frame, 0..1

void fragment() {
	vec4 old = texture(map, SCREEN_UV);
	vec2 at = rect_origin + UV * rect_size;
	vec2 off = at - walker;
	float along = dot(off, heading);
	vec2 side = off - along * heading;
	float d = length(side);  // how far to the side of the walker's way
	float flip = fract(sin(dot(floor(at * 10.0), vec2(12.9898, 78.233))) * 43758.5453) < 0.5 ? -1.0 : 1.0;
	vec2 out_dir = d > 0.02 ? side / d : vec2(-heading.y, heading.x) * flip;
	vec2 was = (old.rg - 0.5) * 2.0 * max_push;
	float near = (1.0 - smoothstep(0.2, 0.45, abs(along))) * (1.0 - smoothstep(radius * 0.6, radius, d));
	vec2 push = out_dir * lane * (1.0 - smoothstep(0.0, radius, d));
	float k = (d < radius * 0.5 || length(push) > length(was)) ? rate * near : 0.0;
	vec2 now = mix(was, push, k);
	COLOR = vec4(clamp(now / (2.0 * max_push) + 0.5, 0.0, 1.0), max(old.b, near), 1.0);
}
