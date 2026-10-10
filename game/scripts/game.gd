extends Node
## Game-wide settings and the controls (an autoload, "Game").
##
## The controls are registered here rather than in the project settings, by physical key, so WASD stays where it is
## on any keyboard layout.

## which trees the demo shows: "old" (the mockups' trees) or "new" (the tree portfolio's)
var tree_set := "new"
## which of the demo's scenes it shows (scripts/scenes.gd)
var scene := "storskogen"
## the paths' colour theme (scripts/path_themes.gd)
var path_theme := "Forest earth"
## the grass over the green ground (scripts/grass.gd, GrassField.STYLES; G and F2 change it)
var grass := "GrassTufts"
## the portfolio trees' bark textures, or their trunks plain as before them (F2's Bark textures)
var bark := true:
	set(v):
		bark = v
		RenderingServer.global_shader_parameter_set("bark_on", 1.0 if v else 0.0)

const KEYS := {
	"move_forward": [KEY_W, KEY_UP], "move_back": [KEY_S, KEY_DOWN],
	"move_left": [KEY_A, KEY_LEFT], "move_right": [KEY_D, KEY_RIGHT],
	"swap_trees": [KEY_T], "path_theme": [KEY_P], "grass_style": [KEY_G], "toggle_help": [KEY_F1, KEY_H], "perf_panel": [KEY_F2], "toggle_fps": [KEY_F3], "render_scale": [KEY_F4],
	"screenshot": [KEY_F12], "menu": [KEY_ESCAPE], "scene_menu": [KEY_TAB],
}


func _ready() -> void:
	for action: String in KEYS:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		for key: Key in KEYS[action]:
			var ev := InputEventKey.new()
			ev.physical_keycode = key
			InputMap.action_add_event(action, ev)
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--trees="):
			tree_set = a.substr(8)
		elif a.begins_with("--scene="):
			scene = a.substr(8)
		elif a.begins_with("--theme="):
			path_theme = a.substr(8).replace("_", " ")
		elif a.begins_with("--grass="):
			grass = a.substr(8)
