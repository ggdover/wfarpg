class_name PerfPanel
extends PanelContainer
## The performance panel (F2). At the top, a graph of every frame's time over the last few seconds, with the frame rate
## now, on average, and in the slowest 5% and 1% of frames, and what the graphics card spends on a frame. Under
## "Advanced settings", hidden at first, the settings, which take effect at once, so you can flip back and forth and
## watch the numbers. They're sorted into categories, each opened and closed by its header, and every setting has a
## hint, two or three sentences at most on what it does, shown as the mouse rests on it; those that matter only with
## some choice of another (the cone's, with the Cone) show only then (the user asked for it all in better order, with
## hints, 1 November). The first of Trees in the way is its Preset (Clear view, Thick forest, One tree is enough),
## which sets the rest of them at once, the one in use marked until any setting changes; it was at the top, above the
## graph, until the user asked for it in its category, under a name of its own (the same day). "Walk the trail" walks
## the same way every time (scripts/trail_walk.gd) and lists each run with its settings.

const WINDOW := 3.0  ## seconds shown in the graph and counted in the numbers
const GRAPH_MS := 50.0  ## frame time at the graph's top
const INK := Color("#E6E0D2")
const DIM := Color("#B7AE9A")
const BRASS := Color("#C9A24A")
const NO_LIMIT := 250.0  ## the frame rate limit slider's top end, which means no limit
const HINT_WIDTH := 58  ## characters to a line of a hint, at most
## the speed-ups of the performance pass (README.md, Speed), each switch as it was before it and as it is now
const BEFORE := {"trimmed": false, "tree_shadows": "mid", "shadow_reach": 0.0, "impostors": 0.0, "details": 3, "spruce_leaves": "tuned"}
const SPED_UP := {"trimmed": true, "tree_shadows": "pictures", "shadow_reach": 60.0, "impostors": 90.0, "details": 4,
	"spruce_leaves": "lighter"}
## what happens to the trees in the way (DemoWorld): a clear view, for most of the game, as the user wants for an ARPG:
## any tree in the way of the hero goes, down to its stump (cut_trees "line"); trees go see-through only where the
## forest is thick, two trees deep (from the playtests, tools/veiltune.py), as in the thick forest's scenes; or as
## soon as one tree hides most of the hero. With all of them, the crown cut keeps trees from the camera, and the
## spruces have their lighter leaves, which the user chose as the default.
const CLEAR_VIEW := {"sight": "line", "leave": "stumps", "crown": "near", "crown_reach": 0.8, "spruce_leaves": "lighter"}
const THICK_FOREST := {"sight": "veil", "veil_by": "two", "veil_round": 1.5, "veil_cover": 0.4, "veil_solid_below": 0.2,
	"veil_amount": 0.5, "veil_keep": 0, "crown": "near", "crown_reach": 0.8, "spruce_leaves": "lighter"}
const ONE_TREE := {"sight": "veil", "veil_by": "seen", "veil_round": 0.0, "veil_cover": 0.9, "veil_solid_below": 0.5,
	"veil_amount": 0.5, "veil_keep": 0, "crown": "near", "crown_reach": 0.8, "spruce_leaves": "lighter"}
const PRESETS := {"clear": CLEAR_VIEW, "thick": THICK_FOREST, "one": ONE_TREE}

var demo: Node
var _frames: Array[Vector2] = []  # (time in s, frame ms)
var _last := 0
var _gpu: Array[float] = []
var _graph: FrameGraph
var _now_label: Label
var _detail_label: Label
var _runs_label: Label
var _walk_button: Button
var _walk: TrailWalk
var _runs: Array[String] = []
var _choices := {}  # setting -> label of the chosen option, for the run list
var _groups := {}  # setting -> {value: Button}
var _texts := {}  # setting -> its row's text
var _sliders := {}  # setting -> a function that moves its slider and applies the value
var _refresh := 0.0
var _theme_box: OptionButton
var _scroll: ScrollContainer
var _advanced: VBoxContainer  # the settings, hidden at first
var _advanced_button: Button
var _preset_buttons := {}  # preset -> its button (Trees in the way's Preset), pressed while it's the settings in use
var _applying := false  # while a preset sets the settings under Advanced
var _categories := {}  # category -> [its header, the box of its rows, its title]
var _values := {}  # setting -> the value chosen, for the rows shown only with some choices (_when)
var _shown_when := []  # [a row, a setting, the values it's shown with]
var _hints := {}  # setting -> its hint, as written
var _rows := {}  # setting -> its row


func setup(d: Node) -> void:
	demo = d
	var bg := StyleBoxFlat.new()
	bg.bg_color = Color(0.09, 0.08, 0.065, 0.86)
	bg.border_color = Color(0.72, 0.6, 0.38, 0.75)
	bg.set_border_width_all(1)
	bg.set_content_margin_all(12)
	add_theme_stylebox_override("panel", bg)
	_hint_theme()
	custom_minimum_size = Vector2(500, 0)
	_scroll = ScrollContainer.new()  # in a small window, the panel scrolls, with Advanced settings shown
	_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	_scroll.custom_minimum_size.x = 476
	add_child(_scroll)
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 3)
	col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_scroll.add_child(col)
	var title := Label.new()
	title.text = "Performance  ·  F2 hides"
	title.add_theme_font_override("font", load("res://assets/fonts/Cinzel.ttf"))
	title.add_theme_font_size_override("font_size", 17)
	title.add_theme_color_override("font_color", Color("#E8D9B0"))
	col.add_child(title)
	_rule(col)
	_graph = FrameGraph.new()
	_graph.panel = self
	_graph.custom_minimum_size = Vector2(464, 90)
	_graph.tooltip_text = _wrap("How long each frame took over the last 3 seconds: green is faster than 60 frames a second, amber than 30, red slower.")
	col.add_child(_graph)
	_now_label = _label(col, "", 15, INK)
	_now_label.mouse_filter = Control.MOUSE_FILTER_PASS
	_now_label.tooltip_text = _wrap("Frames a second now, on average, and in the slowest 5% and 1% of frames, over the last 3 seconds.")
	_detail_label = _label(col, "", 12, DIM)
	_detail_label.mouse_filter = Control.MOUSE_FILTER_PASS
	_detail_label.tooltip_text = _wrap("How long the graphics card takes to draw a frame, and how many triangles and draw calls it takes.")
	_rule(col)
	_advanced_button = _button(col, "", func() -> void: show_advanced(not _advanced.visible))
	_advanced_button.tooltip_text = _wrap("The settings, sorted into categories. Click a category's name to open or close it.")
	_advanced = VBoxContainer.new()
	_advanced.add_theme_constant_override("separation", 3)
	col.add_child(_advanced)
	col = _advanced  # everything below is under Advanced settings

	var w: DemoWorld = demo.world
	var vp := get_viewport()
	var sun: DirectionalLight3D = demo.get_node("DirectionalLight3D")
	var env: Environment = (demo.get_child(0) as WorldEnvironment).environment
	var percent := func(v: float) -> String: return "%d%%" % roundi(v * 100.0)
	var row_s := HBoxContainer.new()  # all the speed-ups at once; each has its own switch in its category too
	row_s.add_theme_constant_override("separation", 8)
	row_s.tooltip_text = _wrap("Everything changed to raise the frame rate, all at once, to compare. Each also has its own setting below.")
	col.add_child(row_s)
	var ls := _label(row_s, "Speed-ups", 13, INK)
	ls.custom_minimum_size.x = 150
	var before := _button(row_s, "All as before", func() -> void: choose_all(BEFORE))
	before.tooltip_text = _wrap("Turns every speed-up off, to see how the game looked and ran before them.")
	var on := _button(row_s, "All on", func() -> void: choose_all(SPED_UP))
	on.tooltip_text = _wrap("Turns every speed-up on, as the game starts.")

	# the trees in the way, and those near the camera
	var c := _category(col, "view", "Trees in the way", "How trees that hide the hero, or come close to the camera, get out of the way.")
	var row_p := HBoxContainer.new()  # the preset: the rest of these, set one of a few ways at once
	_hints["preset"] = "Sets the settings below one of three ways at once. Each scene starts with its own; changing any setting unmarks it."
	row_p.tooltip_text = _wrap(_hints["preset"])
	_rows["preset"] = row_p
	c.add_child(row_p)
	var lp := _label(row_p, "Preset", 13, INK)
	lp.custom_minimum_size.x = 150
	lp.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	var presets := HFlowContainer.new()  # a long row wraps
	presets.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row_p.add_child(presets)
	for k: String in ["clear", "thick", "one"]:
		var b := _button(presets, {"clear": "Clear view", "thick": "Thick forest", "one": "One tree is enough"}[k], use_preset.bind(k))
		b.toggle_mode = true
		b.add_theme_font_size_override("font_size", 12)
		b.custom_minimum_size = Vector2(46, 22)
		b.tooltip_text = _wrap({"clear": "Any tree in the way of the hero goes, down to its stump, and treetops near a high camera are cut lower. Best for most of the game.",
			"thick": "Trees in the way turn half see-through, but only where the forest is thick enough to hide the hero; a tree standing alone stays solid.",
			"one": "Trees in the way turn half see-through as soon as one tree hides most of the hero."}[k])
		_preset_buttons[k] = b
	_choice(c, "sight", "How they go", [["See-through", "veil"], ["Cone", "cone"], ["Front", "front"], ["X-ray", "xray"], ["Area", "area"],
		["Line", "line"], ["Keep", "off"]], w.cut_trees,
		"How trees that block the view of the hero get out of the way. See-through and Line are the ones in use; Cone, Front, X-ray and Area are earlier tries, and Keep leaves every tree standing.",
		func(v: String) -> void: w.set_trees("cut_trees", v))
	_when(_slider(c, "veil_cover", "  see-through at", 0.05, 1.0, 0.05, w.veil_cover, percent,
		"How much of the hero, and the ground round it, the trees must hide before they turn see-through. Lower makes them turn sooner.",
		func(v: float) -> void: w.veil_cover = v), "sight", ["veil"])
	_when(_slider(c, "veil_solid_below", "  solid again below", 0.05, 1.0, 0.01, w.veil_solid_below, percent,
		"See-through trees turn solid again once they hide less than this. Keeping it below see-through at stops them flickering.",
		func(v: float) -> void: w.veil_solid_below = v), "sight", ["veil"])
	_when(_choice(c, "veil_by", "  cover counts", [["Two trees", "two"], ["Leaves", "seen"], ["Whole cards", "cards"]], w.veil_by,
		"What counts as hiding the hero: only what two trees or more hide, so a tree standing alone stays solid; any leaf; or a leaf card's whole outline.",
		func(v: String) -> void: w.veil_by = v), "sight", ["veil"])
	_when(_slider(c, "veil_round", "  area round hero", 0.0, 2.0, 0.1, w.veil_round, "%.1f m",
		"How far round the hero the ground counts too, not only the hero itself.", func(v: float) -> void: w.veil_round = v), "sight", ["veil"])
	_when(_slider(c, "veil_amount", "  see-through by", 0.0, 0.9, 0.05, w.veil_amount, percent,
		"How see-through the trees in the way turn. 0% keeps them solid.", func(v: float) -> void: w.set_trees("veil_amount", v)), "sight", ["veil"])
	_when(_choice(c, "show_area", "  show the area", [["On", true], ["Off", false]], w.show_area,
		"Draws the area round the hero that the trees mustn't hide, to see how see-through works.",
		func(v: bool) -> void: w.show_area = v), "sight", ["veil"])
	_when(_choice(c, "veil_lighter", "  see-through trees", [["Fewer cards", true], ["All cards", false]], w.veil_lighter,
		"Draws see-through trees with half their leaf cards, much faster in thick forest, or with all of them.",
		func(v: bool) -> void: w.set_trees("veil_lighter", v)), "sight", ["veil"])
	_when(_choice(c, "veil_keep", "  hide all but nearest", [["Off", 0], ["1", 1], ["2", 2]], w.veil_keep,
		"Keeps only the one or two see-through trees nearest the hero; the others in the way go completely.",
		func(v: int) -> void: w.set_trees("veil_keep", v)), "sight", ["veil"])
	_when(_slider(c, "cone_soft", "  cone: soft share", 0.1, 1.0, 0.05, w.cone_soft, percent,
		"How much of the cone, from its edge in, fades gradually rather than cutting off sharply.",
		func(v: float) -> void: w.cone_soft = v), "sight", ["cone"])
	_when(_choice(c, "cone_style", "  cone: fade in", [["Dither", "dither"], ["Patches", "patches"]], w.cone_style,
		"Whether trees fade in the cone as a fine dither or in patches.", func(v: String) -> void: w.cone_style = v), "sight", ["cone"])
	_when(_slider(c, "cone_tip", "  cone: round the hero", 1.0, 6.0, 0.25, w.cone_tip, "%.1f×",
		"How big the cone is round the hero, in the hero's own size.", func(v: float) -> void: w.cone_tip = v), "sight", ["cone"])
	_when(_slider(c, "cone_power", "  cone: wide for longer", 0.5, 3.0, 0.1, w.cone_power, "%.1f",
		"How the cone narrows from the camera to the hero. Higher stays wide for longer.",
		func(v: float) -> void: w.cone_power = v), "sight", ["cone"])
	_when(_choice(c, "leave", "  leave", [["Stumps", "stumps"], ["Trunks", "trunks"], ["Nothing", "nothing"]], w.leave,
		"What's left standing of a tree taken out of the view: its stump, its bare trunk, or nothing.",
		func(v: String) -> void: w.set_trees("leave", v)), "sight", ["front", "xray", "area", "line"])
	_when(_choice(c, "cut_by", "  a tree goes by", [["Its trunk", "trunk"], ["Any part", "any"]], w.cut_by,
		"Whether a tree goes when its trunk stands in the area in front of the hero, or when any part of it does.",
		func(v: String) -> void: w.set_trees("cut_by", v)), "sight", ["front", "area"])
	_when(_slider(c, "cut_width", "  area width", 0.2, 1.0, 0.02, w.cut_half_width * 2.0, percent,
		"How wide the area in front of the hero where trees go is, as a share of the screen.",
		func(v: float) -> void: w.cut_half_width = v * 0.5), "sight", ["front", "xray", "area"])
	_when(_slider(c, "cut_top", "  area from the top", 0.0, 0.5, 0.02, w.cut_top, percent,
		"How far down from the top of the screen that area starts.", func(v: float) -> void: w.cut_top = v), "sight", ["front", "xray", "area"])
	_when(_slider(c, "cut_near", "  near the camera", 0.0, 0.8, 0.05, w.cut_near, percent,
		"Trees nearer the camera than this share of the way to the hero fade out.", func(v: float) -> void: w.cut_near = v),
		"sight", ["front", "xray"])
	_when(_slider(c, "cut_front", "  in front: by at least", 0.0, 5.0, 0.5, w.cut_front, "%.1f m",
		"How far in front of the hero a tree must stand to go.", func(v: float) -> void: w.cut_front = v), "sight", ["front"])
	_when(_slider(c, "cut_behind", "  lower middle: past hero", 0.0, 20.0, 1.0, w.cut_behind, "%d m",
		"How far past the hero the trees in the lower middle of the screen still go.", func(v: float) -> void: w.cut_behind = v),
		"sight", ["area"])
	_when(_slider(c, "sight_clear", "  clear round the hero", 0.0, 8.0, 0.5, w.sight_clear, "%.1f m",
		"The trees that hide the ground this far round the hero go too. 0 m keeps only the hero itself in view.",
		func(v: float) -> void: w.sight_clear = v), "sight", ["front", "area", "line"])
	_choice(c, "crown", "Treetops, camera high", [["Near camera", "near"], ["All trees", "all"], ["Off", "off"]], w.crown_cut,
		"With the camera high, the trees near it end lower the nearer they stand, so no treetop blocks the view. All trees cuts every tree at one height instead.",
		func(v: String) -> void: w.set_trees("crown_cut", v))
	_when(_slider(c, "crown_reach", "  reach", 0.4, 1.0, 0.05, w.crown_reach, percent,
		"How far round the camera the trees are cut, as a share of its distance to the hero.",
		func(v: float) -> void: w.crown_reach = v), "crown", ["near"])
	_when(_slider(c, "crown_height", "  trees end at", 3.0, 16.0, 0.5, w.crown_height, "%.1f m", "The height every tree ends at.",
		func(v: float) -> void: w.crown_height = v), "crown", ["all"])
	_choice(c, "fade", "Fade trees near camera", [["On", true], ["Off", false]], w.fade_near_camera,
		"Fades out the trees near a high camera, as the early mockups did. Off by default: trees should go only when they block the view.",
		func(v: bool) -> void: w.set_trees("fade_near_camera", v))

	# the trees: how they look, and the speed-ups for drawing them
	c = _category(col, "trees", "Trees", "How the trees look, and how they're drawn to keep the frame rate up.")
	_choice(c, "trees", "Which trees (T)", [["Old", "old"], ["New", "new"]], Game.tree_set,
		"The new trees, made in Blender, or the old ones from the early mockups. T swaps them where you stand.",
		func(v: String) -> void: demo.show_tree_set(v))
	_choice(c, "bark", "Bark textures", [["On", true], ["Off", false]], Game.bark,
		"Painted bark on the new trees' trunks, or plain trunks in their bark's colour.", func(v: bool) -> void: Game.bark = v)
	_choice(c, "trimmed", "Leaf cards", [["Square", false], ["Trimmed", true]], w.trimmed,
		"Leaf cards trimmed to the outline of their leaves, or square. Trimmed looks the same and draws faster.",
		func(v: bool) -> void: w.set_trees("trimmed", v))
	_choice(c, "fewer", "Cards per clump", [["As tuned", false], ["Fewer", true]], w.fewer,
		"About half as many leaf cards in each clump, each a little bigger: faster, but the crowns look sparser.",
		func(v: bool) -> void: w.set_trees("fewer", v))
	_choice(c, "spruce_leaves", "Spruce leaves", [["As tuned", "tuned"], ["Light", "light"], ["Lighter", "lighter"]], w.spruce_leaves,
		"How many sprays of needles the spruces draw. Lighter, the default, draws half as many, further apart, for a much better frame rate in the forest.",
		func(v: String) -> void: w.set_trees("spruce_leaves", v))
	_slider(c, "lod_near", "Lighter trees from", 10.0, 110.0, 5.0, w.lod_near, "%d m",
		"How far from the camera the trees switch to their simpler versions.", func(v: float) -> void: w.set_trees("lod_near", v))
	_choice(c, "impostors", "Far trees as pictures", [["Never", 0.0], ["From 120 m", 120.0], ["90 m", 90.0], ["60 m", 60.0]], w.impostors_from,
		"From how far off the trees are drawn as flat pictures, taken as the game starts, which is much faster. Never draws them all in full.",
		func(v: float) -> void: w.set_trees("impostors_from", v))
	_choice(c, "tree_shadows", "Tree shadows from", [["Full", "full"], ["Mid", "mid"], ["Far", "far"], ["Pictures", "pictures"], ["None", "off"]],
		w.tree_shadows,
		"What casts the trees' shadows: one of their versions, or their trunks with a picture of their leaves (Pictures, the default and the fastest). None leaves them without.",
		func(v: String) -> void: w.set_trees("tree_shadows", v))
	_when(_choice(c, "shadow_reach", "  from trees within", [["All", 0.0], ["60 m", 60.0], ["40 m", 40.0], ["25 m", 25.0]], w.shadow_reach,
		"Only the trees within this far of the camera cast shadows.", func(v: float) -> void: w.set_trees("shadow_reach", v)),
		"tree_shadows", ["full", "mid", "far", "pictures"])

	# the grass
	c = _category(col, "grass", "Grass", "The grass on the green ground: which kind, how much of it, and how it's drawn.")
	var styles := GrassField.STYLES.keys().map(func(k: String) -> Array: return [GrassField.STYLES[k], k])
	var grasses := GrassField.STYLES.keys().filter(func(k: String) -> bool: return k != "before")
	_choice(c, "grass", "Which grass (G)", styles, Game.grass,
		"Which grass covers the green ground. G steps through them; As before shows the early mockups' grass tufts instead.",
		func(v: String) -> void: demo.show_grass(v))
	_when(_slider(c, "grass_density", "  strands", 0.25, GrassField.MAX_DENSITY, 0.05, w.grass.density, percent,
		"How many strands of grass there are, against as tuned. More looks thicker, but costs more.",
		func(v: float) -> void: w.set_grass_option("density", v)), "grass", grasses)
	_when(_slider(c, "grass_size", "  strand size", 0.6, GrassField.MAX_SIZE, 0.05, w.grass.strand_size, percent,
		"How big each tuft of grass and its strands are.", func(v: float) -> void: w.set_grass_option("strand_size", v)), "grass", grasses)
	_when(_slider(c, "grass_height", "  how tall", 0.4, 1.6, 0.05, w.grass.height_scale, percent, "How tall the grass grows.",
		func(v: float) -> void: w.set_grass_option("height_scale", v)), "grass", grasses)
	_when(_slider(c, "grass_reach", "  drawn out to", 15.0, 80.0, 5.0, w.grass.reach, "%d m",
		"How far from the camera the grass is drawn; further off, it sinks into the ground.",
		func(v: float) -> void: w.set_grass_option("reach", v)), "grass", grasses)
	_when(_slider(c, "grass_ground", "  ground texture", 0.0, 2.0, 0.1, w.grass.ground_texture, percent,
		"How strongly the strands painted on the ground under the grass show.",
		func(v: float) -> void: w.set_grass_option("ground_texture", v)), "grass", grasses)
	_when(_slider(c, "grass_shade", "  ground in its shade", 0.6, 1.0, 0.05, w.grass.ground_shade, percent,
		"How much the ground among the grass is darkened, so the lighter strands stand out.",
		func(v: float) -> void: w.set_grass_option("ground_shade", v)), "grass", grasses)

	# the bushes, and the autumn hollow's fallen leaves (null elsewhere, where their settings don't show)
	c = _category(col, "plants", "Bushes and fallen leaves", "The bushes, how they react to the hero, and the autumn hollow's piles of leaves.")
	_choice(c, "bushes", "Bushes", [["On", true], ["Off", false]], true,
		"Shows the bushes, raspberry, alder buckthorn and hazel, or hides them.", func(v: bool) -> void: w.set_bushes(v))
	_when(_slider(c, "bush_shake", "  shake as the hero walks in", 0.0, 2.0, 0.05, w.bushes.shake, percent,
		"How much a bush shakes as the hero pushes through it.", func(v: float) -> void: w.bushes.shake = v), "bushes", [true])
	_when(_slider(c, "bush_drag", "  slow the hero by", 0.0, 0.5, 0.01, w.bushes.drag, percent,
		"How much slower the hero walks in the middle of a bush.", func(v: float) -> void: w.bushes.drag = v), "bushes", [true])
	var leaves: LeafLitter = w.leaves
	_when(_choice(c, "leaves", "Fallen leaves", [["Piles", true], ["As before", false]], leaves == null or leaves.shown,
		"In the autumn hollow, deep piles of leaves that part as the hero walks through, or none.",
		func(v: bool) -> void: w.set_leaves(v)), "leaves", [true, false] if leaves else [])
	_when(_slider(c, "leaf_amount", "  in piles", 0.3, 2.0, 0.05, leaves.amount if leaves else 1.0, percent,
		"How much of the fallen leaves lies in piles.", func(v: float) -> void: w.set_leaf_option("amount", v)),
		"leaves", [true] if leaves else [])
	_when(_slider(c, "leaf_stir", "  stirring", 0.0, 2.0, 0.05, leaves.stir if leaves else 1.0, percent,
		"How much the leaves stir as the hero walks through a pile.", func(v: float) -> void: w.set_leaf_option("stir", v)),
		"leaves", [true] if leaves else [])
	_when(_slider(c, "leaf_hop", "  hop", 0.0, 0.2, 0.005, leaves.hop if leaves else 0.08,
		func(v: float) -> String: return "%d cm" % roundi(v * 100.0), "How high the leaves the hero kicks up fly.",
		func(v: float) -> void: w.set_leaf_option("hop", v)), "leaves", [true] if leaves else [])

	# the wind
	c = _category(col, "wind", "Wind", "The gusts that move the trees, the bushes, the grass and the fallen leaves.")
	_choice(c, "wind", "Blowing", [["On", true], ["Off", false]], w.wind.on,
		"Gusts that sway the trees and bushes, wave the grass and ruffle the fallen leaves. Off keeps everything still.",
		func(v: bool) -> void: w.wind.on = v)
	_when(_slider(c, "wind_strength", "  movement", 0.0, 3.0, 0.05, w.wind.strength, percent,
		"How much the wind moves things, in the gusts and between them.", func(v: float) -> void: w.wind.strength = v), "wind", [true])
	_when(_slider(c, "wind_every", "  gusts every", 1.5, 10.0, 0.1, w.wind.every, "%.1f s", "About how many seconds apart the gusts come.",
		func(v: float) -> void: w.wind.every = v), "wind", [true])
	_when(_slider(c, "wind_strong", "  strong gusts", 0.0, 1.5, 0.05, w.wind.strong, func(v: float) -> String: return "+%d%%" % roundi(v * 100.0),
		"How much harder than the rest the odd strong gust blows. +0% makes every gust alike.",
		func(v: float) -> void: w.wind.strong = v), "wind", [true])

	# the ground and the paths
	c = _category(col, "ground", "Ground and paths", "The paths' colours and wear, and how much of the ground's detail is drawn.")
	var row0 := HBoxContainer.new()
	_hints["theme"] = "The colours of the dirt paths. P steps through them."
	row0.tooltip_text = _wrap(_hints["theme"])
	_rows["theme"] = row0
	c.add_child(row0)
	var l0 := _label(row0, "Path colours (P)", 13, INK)
	l0.custom_minimum_size.x = 150
	_theme_box = OptionButton.new()
	_theme_box.focus_mode = Control.FOCUS_NONE
	_theme_box.add_theme_font_size_override("font_size", 12)
	_theme_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_theme_box.tooltip_text = row0.tooltip_text
	for t: String in PathThemes.ORDER:
		_theme_box.add_item(t)
		_theme_box.set_item_tooltip(_theme_box.item_count - 1, PathThemes.THEMES[t]["about"])
	_theme_box.select(PathThemes.ORDER.find(Game.path_theme))
	_theme_box.item_selected.connect(func(i: int) -> void:
		_changed()
		demo.show_path_theme(PathThemes.ORDER[i]))
	row0.add_child(_theme_box)
	_choices["theme"] = "paths " + Game.path_theme.to_lower()
	_slider(c, "path_wear", "Path wear spread", 0.0, 1.0, 0.1, w.path_wear, "%.1f",
		"How far the paths' wear spreads into the grass: trampled grass, bare patches and stray stones.",
		func(v: float) -> void: w.set_path_wear(v))
	_choice(c, "details", "Ground details", [["High", 3], ["Baked", 4], ["Medium", 2], ["Low", 1], ["Off", 0]], w.ground_detail,
		"How the ground's fine detail is drawn. Baked, the default, looks like High but draws faster; Off shows the plain ground.",
		func(v: int) -> void: w.set_ground_detail(v))

	# the light and the shadows
	c = _category(col, "light", "Light and shadows", "The sun's shadows, the soft shade in corners, and the haze.")
	_choice(c, "shadows", "Shadows", [["On", true], ["Off", false]], sun.shadow_enabled, "The sun's shadows, on or off.",
		func(v: bool) -> void: sun.shadow_enabled = v)
	_when(_choice(c, "shadow_fit", "  distance", [["Fit the view", true], ["Fixed", false]], demo.shadow_fit,
		"Fit the view casts shadows as far as the camera sees, up to the distance below; Fixed always casts them that far.",
		func(v: bool) -> void: demo.shadow_fit = v), "shadows", [true])
	_when(_slider(c, "shadow_cap", "  out to", 20.0, 120.0, 5.0, demo.shadow_cap, "%d m", "How far from the camera the shadows reach.",
		func(v: float) -> void: demo.shadow_cap = v), "shadows", [true])
	_when(_choice(c, "shadow_size", "  resolution", [["4096", 4096], ["2048", 2048], ["1024", 1024], ["512", 512]],
		ProjectSettings.get_setting("rendering/lights_and_shadows/directional_shadow/size"),
		"How detailed the sun's shadows are. Lower is blurrier, but faster.",
		func(v: int) -> void: RenderingServer.directional_shadow_atlas_set_size(v, true)), "shadows", [true])
	_when(_choice(c, "shadow_soft", "  softness", [["Hard", RenderingServer.SHADOW_QUALITY_HARD], ["Low", RenderingServer.SHADOW_QUALITY_SOFT_LOW],
		["High", RenderingServer.SHADOW_QUALITY_SOFT_HIGH]], RenderingServer.SHADOW_QUALITY_SOFT_LOW,
		"How soft the shadows' edges are. Hard is the fastest.",
		func(v: int) -> void: RenderingServer.directional_soft_shadow_filter_set_quality(v as RenderingServer.ShadowQuality)), "shadows", [true])
	_when(_choice(c, "cascades", "  cascades", [["1", DirectionalLight3D.SHADOW_ORTHOGONAL], ["2", DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS],
		["4", DirectionalLight3D.SHADOW_PARALLEL_4_SPLITS]], sun.directional_shadow_mode,
		"How many layers the sun's shadows are split into. More keeps the shadows sharp further off, at some cost.",
		func(v: int) -> void: sun.directional_shadow_mode = v as DirectionalLight3D.ShadowMode), "shadows", [true])
	_choice(c, "ssao", "Ambient occlusion", [["Off", -1], ["Very low", RenderingServer.ENV_SSAO_QUALITY_VERY_LOW],
		["Low", RenderingServer.ENV_SSAO_QUALITY_LOW], ["Medium", RenderingServer.ENV_SSAO_QUALITY_MEDIUM], ["High", RenderingServer.ENV_SSAO_QUALITY_HIGH]],
		RenderingServer.ENV_SSAO_QUALITY_MEDIUM if env.ssao_enabled else -1,
		"Soft shade in corners and under things, where light can't reach. Of these it costs the most, more with the camera low.",
		func(v: int) -> void:
			env.ssao_enabled = v >= 0
			if v >= 0:
				RenderingServer.environment_set_ssao_quality(v as RenderingServer.EnvironmentSSAOQuality, v < RenderingServer.ENV_SSAO_QUALITY_HIGH, 0.5,
					1 if v <= RenderingServer.ENV_SSAO_QUALITY_LOW else 2, 50.0, 300.0))
	_choice(c, "fog", "Haze", [["On", true], ["Off", false]], env.fog_enabled, "The faint haze that softens the forest further off.",
		func(v: bool) -> void: env.fog_enabled = v)

	# the screen and the frame rate
	c = _category(col, "screen", "Screen and frame rate", "How many pixels are drawn, how edges are smoothed, and how fast the game may draw.")
	_choice(c, "scale", "Render scale (F4)", [["100%", 1.0], ["75%", 0.75], ["50%", 0.5]], snappedf(vp.scaling_3d_scale, 0.05),
		"Draws the scene with fewer pixels and scales it up to the window: faster, but a little softer. F4 steps through them.",
		func(v: float) -> void:
			vp.scaling_3d_mode = Viewport.SCALING_3D_MODE_FSR if v < 0.99 else Viewport.SCALING_3D_MODE_BILINEAR
			vp.scaling_3d_scale = v)
	_choice(c, "aa", "Antialiasing", [["SMAA", Viewport.SCREEN_SPACE_AA_SMAA], ["FXAA", Viewport.SCREEN_SPACE_AA_FXAA], ["Off", Viewport.SCREEN_SPACE_AA_DISABLED]],
		vp.screen_space_aa, "Smooths jagged edges. SMAA is sharper, FXAA a little cheaper.",
		func(v: int) -> void: vp.screen_space_aa = v as Viewport.ScreenSpaceAA)
	_choice(c, "vsync", "VSync", [["On", true], ["Off", false]], DisplayServer.window_get_vsync_mode() != DisplayServer.VSYNC_DISABLED,
		"Holds the frame rate to the screen's, which stops tearing. Off by default, so you see how fast the game can go.",
		func(v: bool) -> void: DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_ENABLED if v else DisplayServer.VSYNC_DISABLED))
	# the frame rate limit: the slider's top end is none
	var fps_text := func(v: float) -> String: return "none" if v > NO_LIMIT - 1.0 else "%d fps" % roundi(v)
	_choices["fps"] = "limit " + fps_text.call(NO_LIMIT if Engine.max_fps == 0 else float(Engine.max_fps))
	_slider(c, "fps", "Frame rate limit", 30.0, NO_LIMIT, 10.0, NO_LIMIT if Engine.max_fps == 0 else float(Engine.max_fps), fps_text,
		"The most frames a second the game draws. At the right end, no limit.",
		func(v: float) -> void:
			Engine.max_fps = 0 if v > NO_LIMIT - 1.0 else roundi(v)
			_choices["fps"] = "limit " + fps_text.call(v))
	_rule(col)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	col.add_child(row)
	_walk_button = _button(row, "Walk the trail", func() -> void: _toggle_walk())
	_walk_button.tooltip_text = _wrap("Walks the hero from the start to the meadow, the same way every time, and lists the frame rates below, to compare settings.")
	var clear := _button(row, "Clear runs", func() -> void:
		_runs.clear()
		_update_runs())
	clear.tooltip_text = _wrap("Empties the list of runs.")
	_runs_label = _label(col, "", 12, DIM)
	_runs_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_update_runs()
	_refresh_rows()
	show_advanced(false)
	_mark_preset(_matching_preset())
	RenderingServer.viewport_set_measure_render_time(get_viewport().get_viewport_rid(), true)
	_last = Time.get_ticks_usec()


## Show the advanced settings, or hide them, the panel then no taller than the presets and the numbers.
func show_advanced(on: bool) -> void:
	_advanced.visible = on
	_advanced_button.text = "Hide advanced settings" if on else "Show advanced settings"
	_scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_AUTO if on else ScrollContainer.SCROLL_MODE_DISABLED
	_scroll.custom_minimum_size.y = minf(get_viewport().get_visible_rect().size.y - 60.0, 900.0) if on else 0.0
	size.y = 0.0  # as short as it can be


## Set the see-through settings to a preset's (PRESETS), and mark it as the one in use.
func use_preset(preset: String) -> void:
	_applying = true
	choose_settings(PRESETS[preset])
	_applying = false
	_mark_preset(preset)


## Mark the preset in use, or none ("").
func _mark_preset(preset: String) -> void:
	for k: String in _preset_buttons:
		(_preset_buttons[k] as Button).set_pressed_no_signal(k == preset)


## The marked preset, or "" if none is.
func preset_in_use() -> String:
	for k: String in _preset_buttons:
		if (_preset_buttons[k] as Button).button_pressed:
			return k
	return ""


## The preset whose settings are the settings now, or "" (at the start: the defaults are Thick forest's).
func _matching_preset() -> String:
	var w: DemoWorld = demo.world
	var now := {"sight": w.cut_trees, "veil_by": w.veil_by, "veil_round": w.veil_round, "veil_cover": w.veil_cover,
		"veil_solid_below": w.veil_solid_below, "veil_amount": w.veil_amount, "veil_keep": w.veil_keep, "spruce_leaves": w.spruce_leaves,
		"leave": w.leave, "crown": w.crown_cut, "crown_reach": w.crown_reach}
	for k: String in PRESETS:
		var same := true
		for setting: String in PRESETS[k]:
			var a: Variant = PRESETS[k][setting]
			var b: Variant = now[setting]
			if not (is_equal_approx(float(a), float(b)) if (a is float or a is int) else a == b):
				same = false
		if same:
			return k
	return ""


## A setting under Advanced was changed, from the panel or by a key (T, P, F4): the settings may no longer be the
## marked preset's.
func _changed() -> void:
	if not _applying:
		_mark_preset("")


## The frames inside the graph's window: (seconds ago, frame ms).
func frames() -> Array[Vector2]:
	return _frames


func _process(delta: float) -> void:
	var now := Time.get_ticks_usec()
	var ms := (now - _last) / 1000.0
	_last = now
	var t := now / 1000000.0
	_frames.append(Vector2(t, ms))
	while _frames.size() > 0 and _frames[0].x < t - WINDOW:
		_frames.pop_front()
	_gpu.append(RenderingServer.viewport_get_measured_render_time_gpu(get_viewport().get_viewport_rid()))
	if _gpu.size() > 30:
		_gpu.pop_front()
	_graph.queue_redraw()
	_refresh -= delta
	if _refresh <= 0.0 and visible:
		_refresh = 0.2
		_update_numbers()


func _update_numbers() -> void:
	if _frames.size() < 2:
		return
	var ms := PackedFloat32Array()
	var recent := 0.0
	var recent_n := 0
	for f in _frames:
		ms.append(f.y)
		if f.x > _frames[-1].x - 0.25:
			recent += f.y
			recent_n += 1
	var s := TrailWalk.summary(ms)
	var gpu := 0.0
	for g in _gpu:
		gpu += g
	gpu /= maxf(1.0, _gpu.size())
	_now_label.text = "Now %d   Average %d   5%% low %d   1%% low %d  fps" % [roundi(1000.0 * recent_n / maxf(recent, 0.001)),
		roundi(s["fps"]), roundi(s["low5"]), roundi(s["low1"])]
	_detail_label.text = "Graphics card %.1f ms a frame   ·   %.2f M triangles   ·   %d draw calls" % [gpu,
		RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME) / 1000000.0,
		RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME)]


func _toggle_walk() -> void:
	if _walk:
		_walk.stop()
		_walk = null
		_walk_button.text = "Walk the trail"
		return
	_walk = TrailWalk.new()
	demo.add_child(_walk)
	_walk.start(demo)
	_walk.finished.connect(_walk_done)
	_walk_button.text = "Stop walking"


func _walk_done(r: Dictionary) -> void:
	_walk = null
	_walk_button.text = "Walk the trail"
	if r.is_empty():
		return
	var settings := []
	for k in ["trees", "trimmed", "fewer", "spruce_leaves", "tree_shadows", "shadow_reach", "impostors", "sight", "crown", "scale", "shadows", "shadow_size", "details", "ssao", "vsync", "fps"]:
		settings.append(_choices[k])
	_runs.push_front("%d · avg %d, 5%% low %d, 1%% low %d fps%s\n    %s" % [_runs.size() + 1, roundi(r["fps"]), roundi(r["low5"]),
		roundi(r["low1"]), "" if r["completed"] else " (stopped early)", ", ".join(settings)])
	_update_runs()


func _update_runs() -> void:
	_runs_label.text = "\n".join(_runs.slice(0, 6)) if _runs else "Runs show here. VSync and the frame rate limit cap the frame rate; with both off, it goes as high as it can."


# ------------------------------------------------------------------ building the rows
## A category of settings under Advanced: a header, which opens and closes it, and the box its rows go in. Which are
## open is kept while the game runs (Game.open_categories), so they stay open from scene to scene.
func _category(parent: Control, key: String, title: String, hint: String) -> VBoxContainer:
	var head := Button.new()
	head.focus_mode = Control.FOCUS_NONE
	head.alignment = HORIZONTAL_ALIGNMENT_LEFT
	head.add_theme_font_size_override("font_size", 14)
	head.custom_minimum_size = Vector2(0, 30)
	head.tooltip_text = _wrap(hint)
	for state in ["normal", "hover", "pressed", "hover_pressed"]:
		var sb := StyleBoxFlat.new()
		sb.bg_color = Color("#332C22") if (state as String).begins_with("hover") else Color("#221E18")
		sb.border_color = Color("#6E5D3E")
		sb.border_width_bottom = 1
		sb.set_content_margin_all(5)
		head.add_theme_stylebox_override(state, sb)
	for colour in ["font_color", "font_pressed_color", "font_hover_color", "font_hover_pressed_color"]:
		head.add_theme_color_override(colour, BRASS if (colour as String) in ["font_color", "font_pressed_color"] else Color("#E8C870"))
	parent.add_child(head)
	var rows := VBoxContainer.new()
	rows.add_theme_constant_override("separation", 3)
	parent.add_child(rows)
	_categories[key] = [head, rows, title]
	open_category(key, Game.open_categories.get(key, false))
	head.pressed.connect(func() -> void: open_category(key, not rows.visible))
	return rows


## Open every category under Advanced (for pictures of the whole panel: --panel=all).
func open_all() -> void:
	for k: String in _categories:
		open_category(k, true)


## Open one of the categories under Advanced (_category), or close it.
func open_category(key: String, on: bool) -> void:
	var c: Array = _categories[key]
	(c[1] as Control).visible = on
	(c[0] as Button).text = ("–   " if on else "+   ") + c[2]
	Game.open_categories[key] = on


## Show a row only while setting key is one of values, as the cone's settings show only with the Cone.
func _when(row: Control, key: String, values: Array) -> void:
	_shown_when.append([row, key, values])


## Show the rows that matter with the choices made now, and hide the others (_when).
func _refresh_rows() -> void:
	for w: Array in _shown_when:
		(w[0] as Control).visible = (w[2] as Array).has(_values.get(w[1]))


## A hint, broken into lines of at most HINT_WIDTH characters, as a hint shows it.
static func _wrap(text: String) -> String:
	var lines := PackedStringArray()
	var line := ""
	for word in text.split(" "):
		if line != "" and line.length() + 1 + word.length() > HINT_WIDTH:
			lines.append(line)
			line = word
		else:
			line = word if line == "" else line + " " + word
	lines.append(line)
	return "\n".join(lines)


## The hints' look, the panel's own: dark, edged in brass.
func _hint_theme() -> void:
	theme = Theme.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.1, 0.088, 0.07, 0.97)
	sb.border_color = BRASS
	sb.set_border_width_all(1)
	sb.set_content_margin_all(8)
	theme.set_stylebox("panel", "TooltipPanel", sb)
	theme.set_color("font_color", "TooltipLabel", INK)
	theme.set_font_size("font_size", "TooltipLabel", 13)


## A row of buttons to choose one of options ([text, value]) with, current pressed; hint says what it does, as the mouse
## rests on the row.
func _choice(parent: Control, key: String, text: String, options: Array, current: Variant, hint: String, apply: Callable) -> Control:
	var row := HBoxContainer.new()
	row.tooltip_text = _wrap(hint)
	_hints[key] = hint
	_rows[key] = row
	parent.add_child(row)
	var l := _label(row, text, 13, INK)
	l.custom_minimum_size.x = 150
	l.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	var buttons := HFlowContainer.new()  # a long row wraps
	buttons.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(buttons)
	var group := ButtonGroup.new()
	_groups[key] = {}
	_texts[key] = text
	_values[key] = current
	for o: Array in options:
		var b := Button.new()
		b.text = o[0]
		b.toggle_mode = true
		b.button_group = group
		b.focus_mode = Control.FOCUS_NONE
		b.add_theme_font_size_override("font_size", 12)
		b.custom_minimum_size = Vector2(46, 22)
		b.tooltip_text = row.tooltip_text
		_style(b)
		buttons.add_child(b)
		_groups[key][o[1]] = b
		if o[1] == current:
			b.button_pressed = true
			_choices[key] = "%s %s" % [text.strip_edges().to_lower(), o[0].to_lower()]
		b.toggled.connect(func(on: bool) -> void:
			if on:
				_changed()
				_choices[key] = "%s %s" % [text.strip_edges().to_lower(), o[0].to_lower()]
				_values[key] = o[1]
				_refresh_rows()
				apply.call(o[1]))
	return row


## Press one of a row's buttons, as a click would (for --set and the dev panel test). A number matches whichever
## button has the same value, 0 or 0.0.
func choose(key: String, value: Variant) -> void:
	var group: Dictionary = _groups[key]
	if not group.has(value) and (value is int or value is float):
		for k: Variant in group:
			if (k is int or k is float) and is_equal_approx(float(k), float(value)):
				value = k
	(group[value] as Button).button_pressed = true


## Make several choices at once, {setting: value}.
func choose_all(settings: Dictionary) -> void:
	for k: String in settings:
		choose(k, settings[k])


## Set several choices and sliders at once, {setting: value}.
func choose_settings(settings: Dictionary) -> void:
	for k: String in settings:
		if _sliders.has(k):
			slide(k, settings[k])
		else:
			choose(k, settings[k])


func show_theme(theme: String) -> void:
	if _choices["theme"] != "paths " + theme.to_lower():
		_changed()
	_theme_box.select(PathThemes.ORDER.find(theme))
	_choices["theme"] = "paths " + theme.to_lower()


## Mark a choice as made elsewhere (T swaps the trees, F4 the render scale) without applying it again.
func show_choice(key: String, value: Variant) -> void:
	var b: Button = _groups.get(key, {}).get(value)
	if b and not b.button_pressed:
		_changed()
		b.set_pressed_no_signal(true)
		_choices[key] = "%s %s" % [(_texts[key] as String).strip_edges().to_lower(), b.text.to_lower()]
		_values[key] = value
		_refresh_rows()


## Move a slider and apply its value, as letting go of it would (for --set and the dev panel test).
func slide(key: String, value: float) -> void:
	(_sliders[key] as Callable).call(value)


func has_slider(key: String) -> bool:
	return _sliders.has(key)


## A slider row; fmt is a format string for the value, or a function that turns it into text; hint says what it does, as
## the mouse rests on the row.
func _slider(parent: Control, key: String, text: String, lo: float, hi: float, step: float, value: float, fmt: Variant, hint: String,
		apply: Callable) -> Control:
	var row := HBoxContainer.new()
	row.tooltip_text = _wrap(hint)
	_hints[key] = hint
	_rows[key] = row
	parent.add_child(row)
	var l := _label(row, text, 13, INK)
	l.custom_minimum_size.x = 150
	var s := HSlider.new()
	s.min_value = lo
	s.max_value = hi
	s.step = step
	s.value = value
	s.tooltip_text = row.tooltip_text
	s.focus_mode = Control.FOCUS_NONE
	s.scrollable = false  # the wheel scrolls the panel instead: a slider applies its value only when let go
	s.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	s.custom_minimum_size.y = 22
	row.add_child(s)
	var show := func(x: float) -> String: return (fmt as Callable).call(x) if fmt is Callable else (fmt as String) % x
	var v := _label(row, show.call(value), 12, DIM)
	v.custom_minimum_size.x = 48
	s.value_changed.connect(func(x: float) -> void: v.text = show.call(x))
	s.drag_ended.connect(func(_moved: bool) -> void:
		_changed()
		apply.call(s.value))
	_sliders[key] = func(x: float) -> void:
		_changed()
		s.value = x
		apply.call(s.value)
	return row


func _button(parent: Control, text: String, on_press: Callable) -> Button:
	var b := Button.new()
	b.text = text
	b.focus_mode = Control.FOCUS_NONE
	b.add_theme_font_size_override("font_size", 13)
	b.custom_minimum_size = Vector2(0, 28)
	_style(b)
	b.pressed.connect(on_press)
	parent.add_child(b)
	return b


func _style(b: Button) -> void:
	for state in ["normal", "hover", "pressed", "hover_pressed"]:
		var sb := StyleBoxFlat.new()
		var on: bool = (state as String).contains("pressed")
		sb.bg_color = Color("#5A4A2A") if on else (Color("#3A3328") if state == "hover" else Color("#2A2620"))
		sb.border_color = BRASS if on else Color("#6E5D3E")
		sb.set_border_width_all(1)
		sb.set_content_margin_all(4)
		b.add_theme_stylebox_override(state, sb)
	b.add_theme_color_override("font_color", DIM)
	b.add_theme_color_override("font_pressed_color", Color("#FFF1CC"))
	b.add_theme_color_override("font_hover_color", INK)
	b.add_theme_color_override("font_hover_pressed_color", Color("#FFF1CC"))


func _label(parent: Control, text: String, size: int, colour: Color) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", colour)
	parent.add_child(l)
	return l


func _rule(parent: Control) -> void:
	var r := ColorRect.new()
	r.color = Color(0.72, 0.6, 0.38, 0.35)
	r.custom_minimum_size = Vector2(0, 1)
	parent.add_child(r)


## The frame-time graph: one bar per frame over the last few seconds, green under 60 fps' 16.7 ms, amber under
## 30 fps' 33.3 ms, red above, with lines at 120, 60 and 30 fps.
class FrameGraph extends Control:
	var panel: PerfPanel

	func _draw() -> void:
		var w := size.x
		var h := size.y
		draw_rect(Rect2(Vector2.ZERO, size), Color(0, 0, 0, 0.35))
		var frames := panel.frames()
		if frames.is_empty():
			return
		var t1: float = frames[-1].x
		for f in frames:
			var x := w * (1.0 - (t1 - f.x) / PerfPanel.WINDOW)
			var bh := h * minf(f.y / PerfPanel.GRAPH_MS, 1.0)
			var c := Color("#7FB069") if f.y < 17.5 else (Color("#E0B850") if f.y < 34.0 else Color("#D9534F"))
			draw_line(Vector2(x, h), Vector2(x, h - bh), c, 2.0)
		var font := get_theme_default_font()
		for line in [[1000.0 / 120.0, "120 fps"], [1000.0 / 60.0, "60 fps"], [1000.0 / 30.0, "30 fps"]]:
			var y: float = h - h * float(line[0]) / PerfPanel.GRAPH_MS
			draw_line(Vector2(0, y), Vector2(w, y), Color(1, 1, 1, 0.45), 1.0)
			draw_rect(Rect2(2, y - 14, 50, 13), Color(0, 0, 0, 0.6))
			draw_string(font, Vector2(5, y - 4), line[1], HORIZONTAL_ALIGNMENT_LEFT, -1, 11, Color(1, 1, 1, 0.85))
		draw_string(font, Vector2(w - 76, 12), "last %d s" % PerfPanel.WINDOW, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, Color(1, 1, 1, 0.6))
