class_name PathThemes
extends RefCounted
## Colour themes for the paths, from dark forest soil to light sand, for trying out in the play demo: the dirt (and
## optionally a second soil in patches through it), the trampled grass along the paths, the grit, the gravel's
## contact shadow and the three sizes of stones, how much of each there is, and the pebbles along the edges. The
## ground shader paints them (shaders/ground.gdshaderinc). "Forest earth", a mix of forest soil and brown earth, is the
## one you liked best; "Light tan" is the mockups' paths.

const ORDER := ["Forest soil", "Forest earth", "Brown earth", "Iron soil", "Granite gravel", "Esker sand", "Sandy, mixed stones", "Light tan"]

const THEMES := {
	"Forest soil": {
		"about": "Dark, packed forest soil with grey-brown stones and more fallen leaves",
		"dirt": ["#735639", "#806244", "#8D6F50"], "verge": "#6F6C3E", "worn": ["#7E8445", "#979A54"],
		"grit": ["#6E5640", "#8E785F"], "shade": "#3A2A1C",
		"small": ["#7E7364", "#92877A", "#A69B8C"], "big": ["#66625C", "#7B746C", "#8F867C", "#A39A8E", "#B8AFA2"],
		"flat": ["#7D776E", "#958D82"], "stones": [0.7, 0.75, 1.0], "grit_amount": 0.9, "leaves": 1.3,
	},
	"Forest earth": {
		"about": "Forest soil and brown earth mixed: patches of dark, packed soil in medium brown earth, with grey-brown and pale stones",
		"dirt": ["#8C6B46", "#987752", "#A4845E"], "soil": ["#735639", "#806244", "#8D6F50"], "soil_mix": 0.5,
		"verge": "#7A7640", "worn": ["#838A46", "#9B9F56"], "grit": ["#775D44", "#988064"], "shade": "#3F2D1C",
		"small": ["#7E7364", "#9A8C78", "#C2B39C"], "big": ["#6E6860", "#8A8073", "#A39A8E", "#B4A690", "#CFC4B0"],
		"flat": ["#857E74", "#ACA392"], "stones": [0.85, 0.85, 1.0], "grit_amount": 0.95, "leaves": 1.25,
	},
	"Brown earth": {
		"about": "Medium brown earth with pale, sandy stones",
		"dirt": ["#8C6B46", "#987752", "#A4845E"], "verge": "#847F42", "worn": ["#879048", "#9FA458"],
		"grit": ["#806448", "#A2886A"], "shade": "#44301C",
		"small": ["#A28E72", "#B6A388", "#C8B8A0"], "big": ["#877D71", "#9E9282", "#B4A690", "#C7B9A2", "#D7CCB8"],
		"flat": ["#9C9283", "#B8AE9D"], "stones": [1.0, 1.0, 1.0], "grit_amount": 1.0, "leaves": 1.15,
	},
	"Iron soil": {
		"about": "Warm, rusty brown soil, as where the ground is rich in iron, with grey granite stones",
		"dirt": ["#98694A", "#A47554", "#B08362"], "verge": "#8F7F42", "worn": ["#8C8C4A", "#A4A25A"],
		"grit": ["#8A6244", "#AC8462"], "shade": "#4C301E",
		"small": ["#8E877F", "#A69D93", "#BDB3A8"], "big": ["#79746F", "#908A84", "#A99F97", "#BFB5AB", "#D1C9BF"],
		"flat": ["#938B83", "#ADA59B"], "stones": [0.9, 1.0, 1.0], "grit_amount": 1.0, "leaves": 1.0,
	},
	"Granite gravel": {
		"about": "A grey-beige gravel track of crushed granite, grey and pink, with more stones",
		"dirt": ["#B09B7B", "#BCA786", "#C7B493"], "verge": "#A09862", "worn": ["#8F9452", "#A7A964"],
		"grit": ["#968670", "#C5B398"], "shade": "#5C4C38",
		"small": ["#A89782", "#BEAC96", "#D1C1AA"], "big": ["#8C8176", "#A69686", "#C0A390", "#D1C2AE", "#DFD4C2"],
		"flat": ["#9C9282", "#B8AC99"], "stones": [1.3, 1.25, 1.2], "grit_amount": 1.2, "leaves": 0.8,
	},
	"Esker sand": {
		"about": "Pale sand and gravel, as on the eskers, with grey-brown pebbles",
		"dirt": ["#D3AF74", "#DBBB82", "#E2C692"], "verge": "#ADA05C", "worn": ["#99985A", "#B1AD6A"],
		"grit": ["#B29464", "#D6BE8E"], "shade": "#765A32",
		"small": ["#AE9A7C", "#C2AD8E", "#D4C2A4"], "big": ["#8F8270", "#A99780", "#C0AA8A", "#D1BD9C", "#E0D1B5"],
		"flat": ["#AC9B82", "#C6B497"], "stones": [0.9, 0.95, 0.8], "grit_amount": 1.0, "leaves": 0.9,
	},
	"Sandy, mixed stones": {
		"about": "The light tan paths' sandy dirt, with stones of mixed browns and greys standing out from it",
		"dirt": ["#D2A35A", "#D9B06C", "#DEBB80"], "verge": "#B0A45A", "worn": ["#93904F", "#ABA462"],
		"grit": ["#B8925E", "#D6B98A"], "shade": "#7E5A30",
		"small": ["#A88A66", "#C2A77E", "#D8C29C"], "big": ["#8C7A68", "#A8916F", "#C4A77B", "#D6BE94", "#E2D2B2"],
		"flat": ["#A49278", "#C4B092"], "stones": [1.1, 1.15, 1.0], "grit_amount": 1.0, "leaves": 1.0,
	},
	"Light tan": {
		"about": "The mockups' paths: light tan dirt, between wheat and desert sand, with gravel in the same tones",
		"dirt": ["#D6A151", "#DDAF64", "#E0BB7B"], "verge": "#B3A456", "worn": ["#93904F", "#ABA462"],
		"grit": ["#C79A57", "#DAB981"], "shade": "#9B723B",
		"small": ["#C69853", "#D0AA6C", "#D9BD8C"], "big": ["#BC8E4E", "#C79E60", "#D1AE75", "#D9BD8C", "#DEC7A1"],
		"flat": ["#BF9E69", "#D0B78B"], "stones": [1.0, 1.0, 1.0], "grit_amount": 1.0, "leaves": 1.0,
	},
}


static func apply(world: DemoWorld, theme: String) -> void:
	var t: Dictionary = THEMES[theme]
	for key: String in ["dirt", "worn", "grit", "small", "big", "flat"]:
		var colours: Array = t[key]
		for i in colours.size():
			world.set_ground_param("%s%d" % [key, i], Color(colours[i]))
	var soil: Array = t.get("soil", t["dirt"])
	for i in soil.size():
		world.set_ground_param("soil%d" % i, Color(soil[i]))
	world.set_ground_param("soil_mix", t.get("soil_mix", 0.0))
	world.set_ground_param("verge", Color(t["verge"]))
	world.set_ground_param("shade", Color(t["shade"]))
	world.set_ground_param("stones", Vector3(t["stones"][0], t["stones"][1], t["stones"][2]))
	world.set_ground_param("grit_amount", t["grit_amount"])
	world.set_ground_param("leaf_amount", t["leaves"])
	# the pebbles along the paths' edges take the small gravel's middle colour
	var c := Color(t["small"][1]).srgb_to_linear()
	RenderingServer.global_shader_parameter_set("pebble_colour", Vector3(c.r, c.g, c.b))
