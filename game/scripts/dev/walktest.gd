extends Node
## Dev: walks the trail (scripts/trail_walk.gd) and prints the frame times, then quits.
## godot --path game res://scenes/demo.tscn -- --walktest [--trees=old|new] [--treelod=1|2]


func run(demo: Node) -> void:
	for i in 30:  # let the first frames settle
		await demo.get_tree().process_frame
	print("walktest starts with the ", Game.tree_set, " trees")
	var walk := TrailWalk.new()
	demo.add_child(walk)
	walk.start(demo)
	var r: Dictionary = await walk.finished
	print("walktest %s: %d frames in %.1f s%s" % [Game.tree_set, r["frames"], r["seconds"], "" if r["completed"] else " (stopped before the end)"])
	print("  frame ms: mean %.1f  median %.1f  95%% %.1f  worst %.1f" % [r["mean_ms"], r["median_ms"], r["p95_ms"], r["worst_ms"]])
	print("  fps: %.0f on average, %.0f in the slowest 5%% of frames, %.0f in the slowest 1%%" % [r["fps"], r["low5"], r["low1"]])
	demo.get_tree().quit()
