extends Node
## Game-wide settings and the controls (an autoload, "Game").
##
## The controls are registered here rather than in the project settings, by physical key, so WASD stays where it is
## on any keyboard layout.

## which trees the demo shows: "old" (the mockups' trees) or "new" (the tree portfolio's)
var tree_set := "new"
## the paths' colour theme (scripts/path_themes.gd)
var path_theme := "Light tan"

const KEYS := {
	"move_forward": [KEY_W, KEY_UP], "move_back": [KEY_S, KEY_DOWN],
	"move_left": [KEY_A, KEY_LEFT], "move_right": [KEY_D, KEY_RIGHT],
	"swap_trees": [KEY_T], "path_theme": [KEY_P], "toggle_help": [KEY_F1, KEY_H], "perf_panel": [KEY_F2], "toggle_fps": [KEY_F3], "render_scale": [KEY_F4],
	"screenshot": [KEY_F12], "menu": [KEY_ESCAPE],
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
		elif a.begins_with("--theme="):
			path_theme = a.substr(8).replace("_", " ")
