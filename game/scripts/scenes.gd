class_name Scenes
extends RefCounted
## The demo's scenes. Each shows one of the areas tools/build_demo.py builds (tools/areas), in one of the moods
## (scripts/mood.gd); two scenes may share an area in different moods. The start screen lists them, and in the game
## the Scenes button switches between them (Game.scene).
##
## A scene: id, title, area, mood, about (a line for the lists), and optionally reflections (screen-space
## reflections, for water), ground (the ground shader's parameters for it, such as leaf_amount) and pose (where it
## starts, if not at its area's start with the camera high: the hero's X and Z, the camera's yaw, pitch and distance,
## as the demo's --pose; for a mood seen best from low down).

const LIST := [
	{"id": "storskogen", "title": "Storskogen", "area": "storskogen", "mood": "day",
		"about": "The first demo: pine and spruce, a winding trail, a meadow"},
	{"id": "thick_forest", "title": "Thick forest", "area": "thick_forest", "mood": "day",
		"about": "Dense spruce and pine, one winding path cleared through"},
	{"id": "open_field", "title": "Open field", "area": "open_field", "mood": "day",
		"about": "A big, rolling meadow: copses, lone trees and boulders"},
	{"id": "autumn_hollow", "title": "Autumn hollow", "area": "autumn_hollow", "mood": "autumn",
		"about": "A grove sunk in a hollow, turning yellow, orange and red"},
	{"id": "river_cliffs", "title": "River and cliffs", "area": "river_cliffs", "mood": "day", "reflections": true,
		"about": "A little river under low cliffs: steps up, a footbridge over"},
	{"id": "forest_lake", "title": "Forest lake", "area": "forest_lake", "mood": "day", "reflections": true,
		"about": "A still lake in the forest: reeds, water lilies, a jetty"},
	{"id": "bog", "title": "Bog", "area": "bog", "mood": "day", "reflections": true,
		"about": "Golden tussocks between dark pools, a boardwalk across"},
	{"id": "pine_heath", "title": "Pine heath", "area": "pine_heath", "mood": "day",
		"about": "Tall pines standing apart over moss, heather and granite"},
	{"id": "misty_forest", "title": "Misty forest", "area": "thick_forest", "mood": "fog", "pose": "-46,-2,180,12,10",
		"about": "The thick forest with fog rolling in"},
	{"id": "misty_ravine", "title": "Misty ravine", "area": "river_cliffs", "mood": "fog", "reflections": true,
		"pose": "10,12,270,15,14", "about": "The river and the cliffs in grey, damp mist"},
	{"id": "sunbeams", "title": "Sunbeams", "area": "pine_heath", "mood": "morning", "pose": "-20,-14,5,12,16",
		"about": "Early morning: a low sun shining through mist"},
]


static func find(id: String) -> Dictionary:
	for s: Dictionary in LIST:
		if s["id"] == id:
			return s
	return LIST[0]
