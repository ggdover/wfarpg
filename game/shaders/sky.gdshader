// The mockups' sky (sky_for_camera in mockups/forest_cam.py): a gradient by height above the horizon, with soft
// noise clouds in the daylight mood. Only the background uses it; the light comes from the environment's ambient
// colour, as in the mockups, where the world lights the scene with a plain colour.
shader_type sky;

#include "res://shaders/blender_noise.gdshaderinc"

uniform vec3 stop0 : source_color = vec3(0.863, 0.898, 0.925);
uniform vec3 stop1 : source_color = vec3(0.769, 0.843, 0.918);
uniform vec3 stop2 : source_color = vec3(0.576, 0.718, 0.878);
uniform vec3 stop3 : source_color = vec3(0.424, 0.604, 0.827);
uniform vec4 stop_at = vec4(0.0, 0.08, 0.35, 0.8);
uniform float clouds = 1.0;

void sky() {
	// Blender's world "Generated" coordinates are the view direction, Z up
	vec3 d = vec3(EYEDIR.x, -EYEDIR.z, EYEDIR.y);
	float z = d.z;
	vec3 c = stop0;
	c = mix(c, stop1, clamp((z - stop_at.x) / (stop_at.y - stop_at.x), 0.0, 1.0));
	c = mix(c, stop2, clamp((z - stop_at.y) / (stop_at.z - stop_at.y), 0.0, 1.0));
	c = mix(c, stop3, clamp((z - stop_at.z) / (stop_at.w - stop_at.z), 0.0, 1.0));
	if (clouds > 0.0 && z > 0.04) {
		float n = noise_fbm3(d * 3.2, 4.0, 0.5);
		float cover = clamp((n - 0.56) / 0.16, 0.0, 1.0) * clamp((z - 0.04) / 0.26, 0.0, 1.0);
		c = mix(c, vec3(0.95, 0.96, 0.97), cover * clouds);
	}
	COLOR = c;
}
