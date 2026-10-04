"""Low-poly Act 1 pine-forest mockup scene for wfarpg.

Run:  blender -b --factory-startup -P forest.py -- <outdir> <quality: preview|final> <shot> [<shot> ...]
Shots: day_path, day_tarn, fog_path, fog_bog
"""
import bpy, bmesh, math, random, sys, json, os
from mathutils import Vector, Matrix, noise
from bpy_extras.object_utils import world_to_camera_view

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else os.path.join(os.path.dirname(os.path.abspath(__file__)), "build", "forest")
QUALITY = argv[1] if len(argv) > 1 else "preview"
SHOTS = argv[2:] or ["day_path"]

RES = (1600, 900) if QUALITY in ("final", "json") else (800, 450)
SAMPLES = 96 if QUALITY == "final" else 24

rng = random.Random(7)


# ---------------------------------------------------------------- colors
def lin(hexstr):
    h = hexstr.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c) + (1.0,)


def jitter(col, amt=0.035):
    f = 1 + rng.uniform(-amt, amt)
    return (min(1, col[0] * f), min(1, col[1] * f), min(1, col[2] * f), col[3])


P = {k: lin(v) for k, v in {
    "moss1": "#6E8A3A", "moss2": "#7C9642", "moss3": "#627D36", "moss4": "#8AA24C", "mossdark": "#506A30",
    "lingon": "#4A6630", "lichen": "#8E9880", "lichen2": "#98A189", "litter": "#7A6040",
    "dirt1": "#7A5A3C", "dirt2": "#8A6644", "dirt3": "#6B4E33", "dirt4": "#94714C",
    "grass1": "#8E9A48", "grass2": "#A3A653", "grass3": "#7F8F42",
    "bog1": "#4F5A33", "bog2": "#5A4A33", "bog3": "#3B3A2C", "bog4": "#625A3A",
    "bed": "#3A3A2E",
    "granite1": "#8D8B84", "granite2": "#7D7C76", "granite3": "#9B998F", "granite4": "#6F6F6A",
    "rmoss1": "#6F8B3B", "rmoss2": "#7E9A46", "rmoss3": "#5E7A33",
    "barklow": "#5E5248", "barklow2": "#6B5D50", "barkhi": "#B5653A", "barkhi2": "#C27A45", "barkmid": "#8E5A3A",
    "pine1": "#2F4A2A", "pine2": "#375533", "pine3": "#41603A", "pine4": "#283F25",
    "spruce1": "#2F4F2A", "spruce2": "#3A5E31",
    "leaf1": "#3F6B2F", "leaf2": "#4E7A35", "berryred": "#B3202A", "berryblue": "#2B3A6B",
    "heath1": "#8E5A88", "heath2": "#A06C98", "heathbase": "#4A5A2E",
    "log": "#6A5A4A", "log2": "#5C4E40", "snag": "#7A7166", "snag2": "#8A8276",
    "wood": "#7B5B3A", "wood2": "#6A4C30", "carve": "#2E2418",
    "tunic": "#8E3B2E", "tunic2": "#7A3127", "cloak": "#5E2A24", "trouser": "#3E3A33", "boot": "#2E2219",
    "belt": "#2A2018", "skin": "#D9A07A", "hair": "#6A4A2A", "beard": "#8A6A3A", "bracer": "#4A3828",
    "steel": "#C8CCD0", "steeldark": "#7E848A", "shieldpaint": "#B89A5A", "gold": "#C9A24A",
    "stone": "#80807A", "stone2": "#6E6E68",
    "peb1": "#C39755", "peb2": "#CDA76A", "peb3": "#B98946", "peb4": "#D5B681",
}.items()}
PEBBLE = ("peb1", "peb2", "peb3", "peb4")  # path stones, in the path's own tan


# ---------------------------------------------------------------- scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
COLL = scene.collection


def safe(obj, attr, val):
    try:
        setattr(obj, attr, val)
    except Exception as e:  # API differences between versions
        print("skip", attr, e)


# ---------------------------------------------------------------- materials
def mat_lowpoly():
    m = bpy.data.materials.new("LowPoly")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    a = nt.nodes.new("ShaderNodeAttribute")
    a.attribute_name = "Col"
    a.attribute_type = "GEOMETRY"
    hs = nt.nodes.new("ShaderNodeHueSaturation")
    hs.name = "Grade"
    nt.links.new(a.outputs["Color"], hs.inputs["Color"])
    nt.links.new(hs.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.88
    try:
        bsdf.inputs["Specular IOR Level"].default_value = 0.25
    except Exception:
        pass
    return m


def mat_emit(name, hexcol, strength, alpha=None, use_attr_alpha=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = lin(hexcol)
    em.inputs["Strength"].default_value = strength
    if alpha is None and not use_attr_alpha:
        nt.links.new(em.outputs[0], out.inputs["Surface"])
        return m
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    if use_attr_alpha:
        a = nt.nodes.new("ShaderNodeAttribute")
        a.attribute_name = "Col"
        a.attribute_type = "GEOMETRY"
        nt.links.new(a.outputs["Alpha"], mix.inputs["Fac"])
    else:
        mix.inputs["Fac"].default_value = alpha
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    safe(m, "surface_render_method", "BLENDED")
    safe(m, "blend_method", "BLEND")
    safe(m, "use_transparency_overlap", True)
    return m


def mat_water():
    m = bpy.data.materials.new("Water")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = lin("#2C5463")
    b.inputs["Roughness"].default_value = 0.02
    b.inputs["IOR"].default_value = 1.33
    try:
        b.inputs["Specular IOR Level"].default_value = 1.0
    except Exception:
        pass
    return m


def mat_dark(name, hexcol):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = lin(hexcol)
    b.inputs["Roughness"].default_value = 0.9
    return m


MAT = mat_lowpoly()


def mat_ground():
    """Smooth ground with procedural 'painted' layers: forest floor with grass patches, bog mud, shore grass,
    a worn gravel path and scattered fallen leaves."""
    m = bpy.data.materials.new("Ground")
    m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    bsdf = N["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.93
    try:
        bsdf.inputs["Specular IOR Level"].default_value = 0.2
    except Exception:
        pass
    pos = N.new("ShaderNodeNewGeometry").outputs["Position"]

    def link(v, sock):
        if hasattr(v, "is_output") or hasattr(v, "links"):
            L.new(v, sock)
        else:
            sock.default_value = v

    def offs(v):
        vm = N.new("ShaderNodeVectorMath")
        vm.operation = "ADD"
        L.new(pos, vm.inputs[0])
        vm.inputs[1].default_value = v
        return vm.outputs[0]

    def noise(scale, detail=2.0, rough=0.5, distort=0.0, off=(0, 0, 0)):
        n = N.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rough
        n.inputs["Distortion"].default_value = distort
        L.new(offs(off), n.inputs["Vector"])
        return n.outputs["Fac"]

    def ramp(fac, stops):
        r = N.new("ShaderNodeValToRGB")
        el = r.color_ramp.elements
        el[0].position, el[0].color = stops[0][0], lin(stops[0][1])
        el[1].position, el[1].color = stops[-1][0], lin(stops[-1][1])
        for p_, c_ in stops[1:-1]:
            e = el.new(p_)
            e.color = lin(c_)
        L.new(fac, r.inputs["Fac"])
        return r.outputs["Color"]

    def mix(fac, a, b, blend="MIX"):
        mx = N.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        mx.blend_type = blend
        fin = [x for x in mx.inputs if x.name == "Factor" and x.type == "VALUE"][0]
        ain = [x for x in mx.inputs if x.name == "A" and x.type == "RGBA"][0]
        bin_ = [x for x in mx.inputs if x.name == "B" and x.type == "RGBA"][0]
        link(fac, fin)
        link(lin(a) if isinstance(a, str) else a, ain)
        link(lin(b) if isinstance(b, str) else b, bin_)
        return [x for x in mx.outputs if x.name == "Result" and x.type == "RGBA"][0]

    def math(op, a, b=0.0):
        mt = N.new("ShaderNodeMath")
        mt.operation = op
        link(a, mt.inputs[0])
        link(b, mt.inputs[1])
        return mt.outputs[0]

    def sstep(v, lo, hi, to0=0.0, to1=1.0):
        mr = N.new("ShaderNodeMapRange")
        mr.interpolation_type = "SMOOTHSTEP"
        link(v, mr.inputs["Value"])
        mr.inputs["From Min"].default_value = lo
        mr.inputs["From Max"].default_value = hi
        mr.inputs["To Min"].default_value = to0
        mr.inputs["To Max"].default_value = to1
        return mr.outputs["Result"]

    def attr(name):
        a = N.new("ShaderNodeAttribute")
        a.attribute_name = name
        a.attribute_type = "GEOMETRY"
        return a.outputs["Fac"]

    def broken(mask, scale, amt, lo=0.42, hi=0.58, off=(0, 0, 0)):
        return sstep(math("ADD", mask, math("MULTIPLY", math("SUBTRACT", noise(scale, 2.0, 0.5, 0, off), 0.5), amt)), lo, hi)

    # forest floor: moss zones, grass patches, dark berry-scrub patches, lichen blotches, fine grain
    floor = ramp(noise(0.16, 3.0, 0.55), [(0.32, "#4E6B2D"), (0.47, "#66833A"), (0.6, "#7B9743"), (0.74, "#90A64D")])
    grass = ramp(noise(2.4, 2.0, 0.6, 0, (3, 7, 0)), [(0.35, "#98A84E"), (0.65, "#B2B65C")])
    floor = mix(math("MULTIPLY", sstep(noise(0.5, 2.0, 0.5, 0, (11, 2, 0)), 0.55, 0.63), 0.9), floor, grass)
    floor = mix(math("MULTIPLY", sstep(noise(0.3, 2.0, 0.5, 0, (5, 19, 0)), 0.58, 0.66), 0.75), floor, "#3D5827")
    hs = N.new("ShaderNodeHueSaturation")
    L.new(floor, hs.inputs["Color"])
    grain = noise(6.0, 2.0, 0.65, 0, (2, 2, 0))
    clump = noise(1.3, 2.0, 0.5, 0, (29, 13, 0))
    L.new(math("MULTIPLY", sstep(grain, 0.3, 0.7, 0.84, 1.12), sstep(clump, 0.35, 0.65, 0.9, 1.08)), hs.inputs["Value"])
    col = hs.outputs["Color"]
    # bog mud
    bog = ramp(noise(0.5, 3.0, 0.5, 0, (7, 3, 0)), [(0.35, "#30301E"), (0.55, "#45452B"), (0.72, "#585233")])
    col = mix(broken(attr("bog"), 0.6, 0.4, 0.4, 0.6, (13, 1, 0)), col, bog)
    # shore grass
    shore = ramp(noise(1.8, 2.0, 0.5, 0, (1, 17, 0)), [(0.4, "#8B9A44"), (0.65, "#A8AE57")])
    col = mix(broken(attr("shore"), 1.2, 0.4, 0.4, 0.6, (17, 3, 0)), col, shore)
    # Act 1 paints its area layers (meadow grass) onto the colour here, under the path; see act1_shots.extend_ground
    path_in = N.new("ShaderNodeHueSaturation")
    path_in.name = "PathIn"
    L.new(col, path_in.inputs["Color"])
    col = path_in.outputs["Color"]
    # worn path: feet wear the grass down, so the middle is packed dirt and gravel, and toward the edges the grass
    # thins out in clumps, dry and trampled, with stray pebbles kicked into it. The "pathw" attribute is 1 - d / 4,
    # where d is the distance from the path's centre line in half-widths (1 at its nominal edge); 0 means no path.
    pd = math("MULTIPLY", math("SUBTRACT", 1.0, attr("pathw")), 4.0)
    e = math("ADD", pd, math("MULTIPLY", math("SUBTRACT", noise(0.35, 2.0, 0.5, 0, (41, 5, 0)), 0.5), 0.7))
    e.node.name = "PathDist"  # d with the edges' wobble
    wear = sstep(e, 0.45, 1.9, 1.0, 0.0)
    wear.node.name = "Wear"  # named nodes are where the play demo's ground bake taps in (game/tools/build_demo.py)
    fine = math("SUBTRACT", noise(7.0, 2.0, 0.6, 0, (13, 3, 0)), 0.5)
    tufts = math("SUBTRACT", noise(1.5, 3.0, 0.6, 0, (7, 43, 0)), 0.5)
    tufts.node.name = "Tufts"
    bare = sstep(math("ADD", wear, math("ADD", math("MULTIPLY", tufts, 2.0), math("MULTIPLY", fine, 0.5))), 0.35, 0.7)
    worn = sstep(e, 0.7, 2.1, 1.0, 0.0)
    worn.node.name = "Worn"
    worn_noise = noise(3.0, 2.0, 0.6, 0, (23, 7, 0))
    worn_noise.node.name = "WornNoise"
    worn_grass = ramp(worn_noise, [(0.3, "#93904F"), (0.7, "#ABA462")])
    col = mix(math("MULTIPLY", worn, 0.5), col, worn_grass)
    col.node.name = "WornGrass"  # A: the grass before feet trampled it
    dirt_noise = noise(0.9, 3.0, 0.5, 0, (3, 29, 0))
    dirt_noise.node.name = "DirtNoise"
    dirt = ramp(dirt_noise, [(0.3, "#D6A151"), (0.5, "#DDAF64"), (0.72, "#E0BB7B")])
    dirt = mix(sstep(wear, 0.35, 0.85, 0.4, 0.0), dirt, "#B3A456")
    col = mix(bare, col, dirt)
    col.node.name = "PathDirt"  # A: the grass beside the path, B: the path's dirt, Factor: where the dirt shows
    warp_n = N.new("ShaderNodeTexNoise")
    warp_n.inputs["Scale"].default_value = 9.0
    L.new(pos, warp_n.inputs["Vector"])
    warp_s = N.new("ShaderNodeVectorMath")
    warp_s.operation = "SCALE"
    L.new(warp_n.outputs["Color"], warp_s.inputs[0])
    warp_s.inputs["Scale"].default_value = 0.07
    warped = N.new("ShaderNodeVectorMath")
    warped.operation = "ADD"
    L.new(pos, warped.inputs[0])
    L.new(warp_s.outputs[0], warped.inputs[1])

    def gravel(scale, gap0, gap1, density, stops, off):
        """Stones as Voronoi cells shrunk away from their edges: small flat polygons, in keeping with the faceted
        props. A cell holds a stone when its random value is under the local density. Returns the stone mask,
        its colour, a contact shadow just outside it and a bevelled height."""
        vec = N.new("ShaderNodeVectorMath")
        vec.operation = "ADD"
        L.new(warped.outputs[0], vec.inputs[0])
        vec.inputs[1].default_value = off
        cells = N.new("ShaderNodeTexVoronoi")
        cells.inputs["Scale"].default_value = scale
        L.new(vec.outputs[0], cells.inputs["Vector"])
        edges = N.new("ShaderNodeTexVoronoi")
        edges.feature = "DISTANCE_TO_EDGE"
        edges.inputs["Scale"].default_value = scale
        L.new(vec.outputs[0], edges.inputs["Vector"])
        rnd = N.new("ShaderNodeSeparateColor")
        L.new(cells.outputs["Color"], rnd.inputs["Color"])
        inset = math("SUBTRACT", edges.outputs["Distance"], math("ADD", math("MULTIPLY", rnd.outputs["Green"], gap1 - gap0), gap0))
        here = sstep(math("SUBTRACT", density, rnd.outputs["Red"]), -0.01, 0.01)
        stone = math("MULTIPLY", sstep(inset, 0.0, 0.04), here)
        shadow = math("MULTIPLY", math("SUBTRACT", sstep(inset, -0.07, 0.0), sstep(inset, 0.0, 0.04)), here)
        return stone, ramp(rnd.outputs["Blue"], stops), shadow, math("MULTIPLY", sstep(inset, 0.0, 0.16), here)

    # gravel is densest in the middle and thins out into the grass, with a few strays out in the trampled verge
    spread = math("ADD", wear, math("MULTIPLY", fine, 0.3))
    small_d = math("ADD", sstep(spread, 0.15, 0.75, 0.0, 0.6), math("MULTIPLY", worn, 0.08))
    big_d = math("ADD", sstep(spread, 0.25, 0.85, 0.0, 0.45), math("MULTIPLY", worn, 0.05))
    s_stone, s_col, s_shadow, s_hgt = gravel(13.0, 0.12, 0.24, small_d, [(0.0, "#C69853"), (0.5, "#D0AA6C"), (1.0, "#D9BD8C")], (0, 0, 0))
    b_stone, b_col, b_shadow, b_hgt = gravel(5.5, 0.14, 0.26, big_d, [(0.0, "#BC8E4E"), (0.3, "#C79E60"), (0.6, "#D1AE75"),
                                                                      (0.85, "#D9BD8C"), (1.0, "#DEC7A1")], (3.7, 1.3, 0))
    f_stone, f_col, f_shadow, f_hgt = gravel(1.7, 0.16, 0.3, sstep(spread, 0.5, 0.9, 0.0, 0.06), [(0.0, "#BF9E69"), (1.0, "#D0B78B")], (5.1, 2.3, 0))
    grit = N.new("ShaderNodeTexVoronoi")
    grit.inputs["Scale"].default_value = 30.0
    L.new(warped.outputs[0], grit.inputs["Vector"])
    grit_bw = N.new("ShaderNodeRGBToBW")
    L.new(grit.outputs["Color"], grit_bw.inputs[0])
    col = mix(math("MULTIPLY", bare, 0.35), col, ramp(grit_bw.outputs[0], [(0.2, "#C79A57"), (0.8, "#DAB981")]))
    shade = math("ADD", math("MULTIPLY", s_shadow, 0.3), math("ADD", math("MULTIPLY", b_shadow, 0.5), math("MULTIPLY", f_shadow, 0.5)))
    col = mix(math("MINIMUM", shade, 0.5), col, "#9B723B")
    col = mix(s_stone, col, s_col)
    col = mix(b_stone, col, b_col)
    col = mix(f_stone, col, f_col)
    # fallen leaves: small ellipses, each turned its own way, scattered over the grass and the path in loose drifts
    lv_in = offs((2.3, 7.7, 0))
    lv = N.new("ShaderNodeTexVoronoi")
    lv.inputs["Scale"].default_value = 4.5
    lv.inputs["Randomness"].default_value = 0.75
    L.new(lv_in, lv.inputs["Vector"])
    lrnd = N.new("ShaderNodeSeparateColor")
    L.new(lv.outputs["Color"], lrnd.inputs["Color"])
    rel = N.new("ShaderNodeVectorMath")
    rel.operation = "SUBTRACT"
    L.new(lv_in, rel.inputs[0])
    L.new(lv.outputs["Position"], rel.inputs[1])
    turn = N.new("ShaderNodeVectorRotate")
    turn.rotation_type = "Z_AXIS"
    L.new(rel.outputs[0], turn.inputs["Vector"])
    L.new(math("MULTIPLY", lrnd.outputs["Green"], 6.2832), turn.inputs["Angle"])
    lxy = N.new("ShaderNodeSeparateXYZ")
    L.new(turn.outputs["Vector"], lxy.inputs["Vector"])
    size = math("ADD", math("MULTIPLY", math("FRACT", math("MULTIPLY", lrnd.outputs["Blue"], 5.7)), 0.5), 0.75)
    q = math("ADD", math("POWER", math("DIVIDE", lxy.outputs["X"], math("MULTIPLY", size, 0.05)), 2.0),
             math("POWER", math("DIVIDE", lxy.outputs["Y"], math("MULTIPLY", size, 0.025)), 2.0))
    drift = math("ADD", 0.12, sstep(noise(0.22, 2.0, 0.5, 0, (17, 29, 0)), 0.5, 0.75, 0.0, 0.2))
    leaf = math("MULTIPLY", sstep(q, 0.75, 1.0, 1.0, 0.0), sstep(math("SUBTRACT", drift, lrnd.outputs["Red"]), -0.01, 0.01))
    leaf_col = ramp(lrnd.outputs["Blue"], [(0.0, "#8B5A2E"), (0.2, "#B5762F"), (0.45, "#D39A38"), (0.7, "#E0B850"),
                                           (0.85, "#BFA640"), (1.0, "#A3402A")])
    col = mix(leaf, col, leaf_col)
    # Act 1 paints its layers that sit on top of paths (fields, yards, cobbles, ash) after this
    path_out = N.new("ShaderNodeHueSaturation")
    path_out.name = "PathOut"
    L.new(col, path_out.inputs["Color"])
    grade = N.new("ShaderNodeHueSaturation")
    grade.name = "Grade"
    L.new(path_out.outputs["Color"], grade.inputs["Color"])
    L.new(grade.outputs["Color"], bsdf.inputs["Base Color"])
    # relief: bevelled gravel, the larger flat stones, the grass grain and the leaves
    hgt = math("ADD", math("ADD", math("MULTIPLY", s_hgt, 0.5), b_hgt), math("ADD", math("MULTIPLY", f_hgt, 1.3), math("MULTIPLY", grain, 0.12)))
    hgt = math("ADD", hgt, math("MULTIPLY", leaf, 0.3))
    bump = N.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.5
    bump.inputs["Distance"].default_value = 0.03
    L.new(hgt, bump.inputs["Height"])
    L.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m


MAT_GROUND = mat_ground()
MAT_WATER = mat_water()
def mat_ghost(name, hexcol, strength, edge=0.85, core=0.12):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = lin(hexcol)
    em.inputs["Strength"].default_value = strength
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.45
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = core
    mr.inputs["To Max"].default_value = edge
    nt.links.new(lw.outputs["Facing"], mr.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(mr.outputs[0], mix.inputs["Fac"])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    safe(m, "surface_render_method", "BLENDED")
    safe(m, "blend_method", "BLEND")
    safe(m, "use_backface_culling", False)
    return m


MAT_GHOST = mat_ghost("Ghost", "#A9DCF7", 2.4)
MAT_GHOST_CORE = mat_emit("GhostCore", "#E8F8FF", 6.0, alpha=0.8)
MAT_RUNE_DAY = mat_dark("RuneDay", "#3A3A36")
MAT_RUNE_FOG = mat_emit("RuneFog", "#8FD8FF", 9.0)
MAT_FLAME = mat_emit("Flame", "#FFB24A", 14.0)
MAT_WISP = mat_emit("Wisp", "#E2F6FF", 25.0)
MAT_SWING = mat_emit("Swing", "#FFF1D0", 3.0, use_attr_alpha=True)
MAT_CARVE = mat_dark("Carve", "#2E2418")


# ---------------------------------------------------------------- mesh building helpers
class Builder:
    def __init__(self):
        self.bm = bmesh.new()
        self.col = self.bm.loops.layers.float_color.new("Col")

    def _faces(self, verts):
        found = {}  # in a fixed order (a set's order changes from run to run, and with it each face's colour jitter)
        for v in verts:
            for f in v.link_faces:
                found.setdefault(f, None)
        return list(found)

    def paint(self, faces, colfn, mat_index=0):
        for f in faces:
            c = colfn(f)
            f.material_index = mat_index
            for l in f.loops:
                l[self.col] = c

    def ico(self, center, radius, color, sub=1, scale=(1, 1, 1), rot=None, displace=0.0, mat_index=0):
        m = Matrix.Translation(Vector(center))
        if rot is not None:
            m = m @ rot
        m = m @ Matrix.Diagonal(Vector(scale + (1,) if len(scale) == 3 else scale))
        r = bmesh.ops.create_icosphere(self.bm, subdivisions=sub, radius=radius, matrix=m)
        verts = r["verts"]
        if displace:
            for v in verts:
                n = (v.co - Vector(center)).normalized()
                v.co += n * rng.uniform(-displace, displace)
        faces = self._faces(verts)
        self.paint(faces, color if callable(color) else (lambda f: jitter(color)), mat_index)
        return faces

    def box(self, size, center, color, top_scale=1.0, rot=None, mat_index=0):
        sx, sy, sz = size
        m = Matrix.Translation(Vector(center))
        if rot is not None:
            m = m @ rot
        r = bmesh.ops.create_cube(self.bm, size=1.0, matrix=m @ Matrix.Diagonal(Vector((sx, sy, sz, 1))))
        verts = r["verts"]
        if top_scale != 1.0:
            # scale the top face around the box axis (in local space before rotation)
            inv = m.inverted()
            for v in verts:
                lc = inv @ v.co
                if lc.z > 0:
                    lc.x *= top_scale
                    lc.y *= top_scale
                    v.co = m @ lc
        faces = self._faces(verts)
        self.paint(faces, color if callable(color) else (lambda f: jitter(color, 0.03)), mat_index)
        return faces

    def limb(self, p0, p1, r0, r1, color, segs=6, mat_index=0):
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        L = d.length
        q = d.normalized().to_track_quat("Z", "Y")
        m = Matrix.Translation((p0 + p1) / 2) @ q.to_matrix().to_4x4()
        r = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=segs,
                                  radius1=r0, radius2=r1, depth=L, matrix=m)
        faces = self._faces(r["verts"])
        self.paint(faces, color if callable(color) else (lambda f: jitter(color, 0.04)), mat_index)
        return faces, r["verts"]

    def mesh(self, name, mats=None):
        me = bpy.data.meshes.new(name)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in (mats or [MAT]):
            me.materials.append(m)
        return me


def place(me, loc, rot_z=0.0, scale=1.0, name=None, parent=None, coll=None):
    ob = bpy.data.objects.new(name or me.name, me)
    ob.location = loc
    ob.rotation_euler = (0, 0, rot_z)
    ob.scale = (scale, scale, scale) if not isinstance(scale, tuple) else scale
    (coll or COLL).objects.link(ob)
    if parent:
        ob.parent = parent
    return ob


def pick(*keys):
    return lambda f: jitter(P[rng.choice(keys)])


# ---------------------------------------------------------------- world layout
def catmull(pts, n=16):
    out = []
    pts = [Vector(p) for p in pts]
    for i in range(len(pts) - 1):
        p0 = pts[max(0, i - 1)]; p1 = pts[i]; p2 = pts[i + 1]; p3 = pts[min(len(pts) - 1, i + 2)]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(pts[-1])
    return out


MAIN_PATH = catmull([(-46, -36), (-35, -25), (-28, -22.5), (-21, -14), (-14.5, -11.5), (-9, -5.5), (-4.2, -3.8), (0, 0),
                     (3.4, 4.6), (7.6, 5.4), (11.2, 9.6), (14.6, 10.5), (18.2, 10.0), (22.4, 12.9), (27, 13.2), (33, 16.8), (44, 19)])
SIDE_PATH = catmull([(2.4, 3.3), (1.0, 5.6), (-1.0, 6.6), (-3.4, 8.9), (-6.2, 9.3), (-8.6, 11.7), (-11.0, 11.2)])
PATHS = [(MAIN_PATH, 1.0), (SIDE_PATH, 0.75)]
TARN_C, TARN_R = Vector((18.0, 18.8)), 4.3
BOG_C, BOG_R = Vector((-14.5, 13.5)), 7.5


def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (a + ab * t - p).length


def path_dist(x, y):
    p = Vector((x, y))
    wv = 0.82 + 0.4 * noise.noise(Vector((x * 0.13, y * 0.13, 4.2))) + 0.12 * noise.noise(Vector((x * 0.5, y * 0.5, 8.8)))
    best = 1e9
    for pts, w in PATHS:
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            if abs(a.x - x) > 6 and abs(b.x - x) > 6:
                continue
            best = min(best, seg_dist(p, a, b) / (w * wv))
    return best


def tarn_r(theta):
    return TARN_R + 0.9 * math.sin(3 * theta + 1.0) + 0.5 * math.cos(5 * theta)


def tarn_frac(x, y):
    d = Vector((x, y)) - TARN_C
    return d.length / tarn_r(math.atan2(d.y, d.x))


def base_h(x, y):
    return (0.6 * noise.noise(Vector((x * 0.045, y * 0.045, 0.3)))
            + 0.12 * noise.noise(Vector((x * 0.13, y * 0.13, 1.7))))


WATER_Z = min(base_h(TARN_C.x + math.cos(a) * tarn_r(a) * f, TARN_C.y + math.sin(a) * tarn_r(a) * f)
              for a in [k * math.tau / 48 for k in range(48)] for f in (1.0, 1.15, 1.3)) - 0.12
BOG_Z = base_h(*BOG_C) - 0.1


def smooth(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def height(x, y):
    h = base_h(x, y)
    tf = tarn_frac(x, y)
    if tf < 1.25:
        k = smooth(1.15, 0.7, tf)
        h = h * (1 - k) + (WATER_Z - 0.9) * k
        if tf >= 1.0:
            h = min(h, WATER_Z + 0.25 + (tf - 1.0) * 1.5)
    bd = (Vector((x, y)) - BOG_C).length / BOG_R
    if bd < 1.3:
        k = smooth(1.3, 0.75, bd)
        h = h * (1 - k) + (BOG_Z + 0.06 * noise.noise(Vector((x * 0.7, y * 0.7, 5.0)))) * k
    d = path_dist(x, y)
    if d < 1.4:
        h -= 0.04 * (1 - d / 1.4)
    return h


# puddles in the bog
PUDDLES = []
for i in range(9):
    a = rng.uniform(0, math.tau)
    r = rng.uniform(0.5, 5.8)
    c = BOG_C + Vector((math.cos(a), math.sin(a))) * r
    PUDDLES.append((c, rng.uniform(0.7, 1.6)))


def in_puddle(x, y, pad=0.0):
    for c, r in PUDDLES:
        if (Vector((x, y)) - c).length < r + pad:
            return True
    return False


TREE_PTS = []
TREE_CELL = {}


def near_tree(x, y, r):
    ci, cj = int(x // 4), int(y // 4)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            for (px, py) in TREE_CELL.get((ci + di, cj + dj), ()):
                if (x - px) ** 2 + (y - py) ** 2 < r * r:
                    return True
    return False


# ---------------------------------------------------------------- terrain
def _replay_v1_terrain_rng():
    b = Builder()
    bm = b.bm
    x0, x1, y0, y1, s = -48.0, 48.0, -38.0, 42.0, 0.85
    nx, ny = int((x1 - x0) / s) + 1, int((y1 - y0) / s) + 1
    grid = []
    for j in range(ny):
        row = []
        for i in range(nx):
            x = x0 + i * s + (rng.uniform(-0.35, 0.35) * s if 0 < i < nx - 1 else 0)
            y = y0 + j * s + (rng.uniform(-0.35, 0.35) * s if 0 < j < ny - 1 else 0)
            row.append(bm.verts.new((x, y, height(x, y))))
        grid.append(row)
    faces = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            a, bb, c, d = grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]
            if (i + j) % 2:
                faces += [bm.faces.new((a, bb, c)), bm.faces.new((a, c, d))]
            else:
                faces += [bm.faces.new((a, bb, d)), bm.faces.new((bb, c, d))]

    def color(f):
        cpos = f.calc_center_median()
        x, y = cpos.x, cpos.y
        tf = tarn_frac(x, y)
        if tf < 0.98:
            return jitter(P["bed"])
        if tf < 1.25:
            return jitter(P[rng.choice(["grass1", "grass2", "grass3", "grass1"])])
        d = path_dist(x, y)
        if d < 0.9:
            return jitter(P[rng.choice(["dirt1", "dirt2", "dirt3", "dirt4"])], 0.05)
        if d < 1.5 and rng.random() < 0.45:
            return jitter(P[rng.choice(["dirt3", "litter", "dirt1"])])
        bd = (Vector((x, y)) - BOG_C).length / BOG_R
        if bd < 1.0 or (bd < 1.25 and rng.random() < 0.5):
            if in_puddle(x, y, 0.4):
                return jitter(P["bog3"])
            return jitter(P[rng.choice(["bog1", "bog2", "bog4", "bog1", "heathbase"])])
        if near_tree(x, y, 1.7) and rng.random() < 0.75:
            return jitter(P[rng.choice(["litter", "dirt3", "litter", "dirt1"])])
        n = noise.noise(Vector((x * 0.18, y * 0.18, 9.0)))
        if n > 0.35:
            return jitter(P[rng.choice(["lingon", "mossdark", "moss3"])])
        if rng.random() < 0.06:
            return jitter(P["litter"])
        return jitter(P[rng.choice(["moss1", "moss2", "moss3", "moss4", "moss2"])])

    b.paint(faces, color)
    b.bm.free()


def tree_dist(x, y):
    best = 99.0
    ci, cj = int(x // 4), int(y // 4)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            for (px, py) in TREE_CELL.get((ci + di, cj + dj), ()):
                best = min(best, math.hypot(x - px, y - py))
    return best


def build_outer_ground():
    bm = bmesh.new()
    x0, x1, s = -130.0, 130.0, 2.5
    n = int((x1 - x0) / s) + 1
    grid = [[bm.verts.new((x0 + i * s, x0 + j * s, height(x0 + i * s, x0 + j * s) - 0.08)) for i in range(n)] for j in range(n)]
    for j in range(n - 1):
        for i in range(n - 1):
            cx, cy = x0 + (i + 0.5) * s, x0 + (j + 0.5) * s
            if -46.5 < cx < 46.5 and -36.5 < cy < 40.5:
                continue
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            f.smooth = True
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    me = bpy.data.meshes.new("OuterGround")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(MAT_GROUND)
    place(me, (0, 0, 0), name="OuterGround")


def build_terrain():
    bm = bmesh.new()
    x0, x1, y0, y1, s = -48.0, 48.0, -38.0, 42.0, 0.6
    nx, ny = int((x1 - x0) / s) + 1, int((y1 - y0) / s) + 1
    grid = [[bm.verts.new((x0 + i * s, y0 + j * s, height(x0 + i * s, y0 + j * s))) for i in range(nx)] for j in range(ny)]
    for j in range(ny - 1):
        for i in range(nx - 1):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            f.smooth = True
    me = bpy.data.meshes.new("Terrain")
    bm.to_mesh(me)
    bm.free()
    masks = {"pathw": [], "bog": [], "shore": []}
    for v in me.vertices:
        x, y = v.co.x, v.co.y
        masks["pathw"].append(max(0.0, 1.0 - path_dist(x, y) / 0.875 / 4.0))  # path_dist is 0.875 at the edge
        masks["bog"].append(1.0 - smooth(0.8, 1.15, (Vector((x, y)) - BOG_C).length / BOG_R))
        tf = tarn_frac(x, y)
        masks["shore"].append(1.0 - smooth(1.12, 1.45, tf))
    for name, vals in masks.items():
        a = me.attributes.new(name, "FLOAT", "POINT")
        a.data.foreach_set("value", vals)
    me.materials.append(MAT_GROUND)
    return place(me, (0, 0, 0), name="Terrain")


# ---------------------------------------------------------------- props
def pine_mesh(seed):
    r = random.Random(seed)
    b = Builder()
    H = r.uniform(8.5, 12.0)
    a_lean = r.uniform(0, math.tau)
    lean = Vector((math.cos(a_lean), math.sin(a_lean), 0)) * (r.uniform(0.0, 0.3) if r.random() < 0.8 else r.uniform(0.3, 0.55))
    # one continuous trunk: rings along a gentle curve, coloured grey low and orange higher up
    rings, sides = 9, 7
    rot0 = r.uniform(0, math.tau)
    ring_verts = []
    for k in range(rings + 1):
        t = k / rings
        c = Vector((0, 0, -0.4 + t * (H + 0.4))) + lean * t * t
        rad = 0.34 * (1 - t * 0.7)
        ring_verts.append([b.bm.verts.new(c + Vector((math.cos(rot0 + j * math.tau / sides) * rad, math.sin(rot0 + j * math.tau / sides) * rad, 0)))
                           for j in range(sides)])
    for k in range(rings):
        t = (k + 0.5) / rings
        key = ("barklow", "barklow2") if t < 0.2 else (("barkmid",) if t < 0.32 else ("barkhi", "barkhi2"))
        faces = [b.bm.faces.new((ring_verts[k][j], ring_verts[k][(j + 1) % sides], ring_verts[k + 1][(j + 1) % sides], ring_verts[k + 1][j]))
                 for j in range(sides)]
        b.paint(faces, pick(*key))
    b.paint([b.bm.faces.new(list(reversed(ring_verts[-1])))], pick("barkhi"))
    pts = [Vector((0, 0, H)) + lean]
    # a few bare branch stubs low on the trunk
    for k in range(r.randint(1, 3)):
        z = r.uniform(3.0, H * 0.55)
        a = r.uniform(0, math.tau)
        p0 = Vector((0, 0, z)) + lean * (z / H) ** 2
        b.limb(p0, p0 + Vector((math.cos(a) * 0.9, math.sin(a) * 0.9, 0.25)), 0.05, 0.02, pick("snag", "barklow"), segs=4)
    # crown: flattened clumps near the top
    n = r.randint(3, 5)
    for k in range(n):
        t = r.uniform(0.66, 1.0)
        z = t * H
        a = r.uniform(0, math.tau)
        rad = (1.0 - t) * 2.2 + 0.35
        c = Vector((math.cos(a) * rad, math.sin(a) * rad, z)) + lean * t * t
        size = r.uniform(0.75, 1.15) * (1.1 - 0.3 * t)
        b.ico(c, size, pick("pine1", "pine2", "pine3", "pine4"), sub=1, scale=(1.3, 1.3, 0.55), displace=0.1)
        p0 = Vector((0, 0, z - 0.3)) + lean * t * t
        b.limb(p0, c, 0.07, 0.04, pick("barkhi"), segs=4)
    b.ico(pts[-1] + Vector((0, 0, 0.3)), 0.75, pick("pine2", "pine3"), sub=1, scale=(1.1, 1.1, 0.7), displace=0.08)
    return b.mesh("Pine%d" % seed), H


def spruce_mesh(seed):
    r = random.Random(seed)
    b = Builder()
    H = r.uniform(1.0, 2.8)
    b.limb((0, 0, -0.1), (0, 0, H * 0.25), 0.05, 0.04, pick("barklow"), segs=5)
    tiers = 3 if H < 1.8 else 4
    for k in range(tiers):
        t = k / tiers
        z0 = H * (0.15 + t * 0.75)
        rad = H * 0.38 * (1 - t * 0.7)
        b.limb((0, 0, z0), (0, 0, z0 + H * 0.38), rad, 0.0, pick("spruce1", "spruce2"), segs=6)
    return b.mesh("Spruce%d" % seed)


def boulder_mesh(seed, big=False, tones=None):
    r = random.Random(seed)
    b = Builder()
    rs = Vector((r.uniform(1.0, 1.6), r.uniform(0.9, 1.4), r.uniform(0.8, 1.2)))
    if big:
        rs = Vector((r.uniform(1.6, 2.4), r.uniform(1.3, 1.9), r.uniform(0.8, 1.2)))
    pts = []
    for i in range(r.randint(11, 16) if not big else r.randint(14, 19)):
        z = r.uniform(-0.25, 1.0)
        a = r.uniform(0, math.tau)
        rr = math.sqrt(max(0.0, 1 - z * z))
        pts.append(Vector((rr * math.cos(a) * rs.x, rr * math.sin(a) * rs.y, z * rs.z)) * r.uniform(0.82, 1.12))
    for k in range(6):
        a = k / 6 * math.tau + r.uniform(-0.35, 0.35)
        pts.append(Vector((math.cos(a) * rs.x * r.uniform(0.8, 1.0), math.sin(a) * rs.y * r.uniform(0.8, 1.0), -0.5 * rs.z)))
    verts = [b.bm.verts.new(p) for p in pts]
    res = bmesh.ops.convex_hull(b.bm, input=verts)
    loose = [v for v in b.bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(b.bm, geom=loose, context="VERTS")
    bmesh.ops.dissolve_limit(b.bm, angle_limit=math.radians(r.uniform(10, 17)), verts=b.bm.verts[:], edges=b.bm.edges[:], delimit=set())
    bmesh.ops.recalc_face_normals(b.bm, faces=b.bm.faces[:])
    b.bm.normal_update()

    def col(f):
        if tones:  # plain stone in the given colours, no moss or lichen
            return jitter(P[r.choice(tones)], 0.04)
        if f.normal.z > 0.8 and r.random() < 0.5:
            return jitter(P[r.choice(["rmoss1", "rmoss3"])])
        if f.calc_area() < 0.35 * rs.x * rs.y and r.random() < 0.15:
            return jitter(P["lichen"])
        return jitter(P[r.choice(["granite1", "granite2", "granite3", "granite4"])], 0.05)

    b.paint(b.bm.faces[:], col)
    return b.mesh("Boulder%d" % seed)


def shrub_mesh(seed, berry):
    r = random.Random(seed)
    b = Builder()
    clumps = []
    for k in range(r.randint(3, 5)):
        c = Vector((r.uniform(-0.35, 0.35), r.uniform(-0.35, 0.35), r.uniform(0.12, 0.3)))
        rad = r.uniform(0.18, 0.3)
        b.ico(c, rad, pick("leaf1", "leaf2", "lingon"), sub=1, scale=(1, 1, 0.75), displace=0.03)
        clumps.append((c, rad))
    if berry:
        for k in range(r.randint(2, 4)):
            c, rad = r.choice(clumps)
            d = Vector((r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(0.15, 0.9))).normalized()
            p = c + Vector((d.x * rad, d.y * rad, d.z * rad * 0.75)) * 0.9
            b.ico(p, 0.048, (lambda f: P[berry]), sub=1)
    return b.mesh("Shrub%d" % seed)


def heather_mesh(seed):
    r = random.Random(seed)
    b = Builder()
    for k in range(r.randint(3, 5)):
        c = Vector((r.uniform(-0.35, 0.35), r.uniform(-0.35, 0.35), r.uniform(0.1, 0.2)))
        b.ico(c, r.uniform(0.14, 0.22), pick("heathbase", "leaf1"), sub=1, scale=(1, 1, 0.7), displace=0.03)
        b.ico(c + Vector((0, 0, 0.1)), r.uniform(0.1, 0.16), pick("heath1", "heath2"), sub=1, scale=(1, 1, 0.8), displace=0.03)
    return b.mesh("Heather%d" % seed)


def lichen_mesh(seed):
    r = random.Random(seed)
    b = Builder()
    for k in range(r.randint(3, 6)):
        c = Vector((r.uniform(-0.3, 0.3), r.uniform(-0.3, 0.3), 0.05))
        b.ico(c, r.uniform(0.12, 0.2), pick("lichen", "lichen2"), sub=1, scale=(1, 1, 0.55), displace=0.03)
    return b.mesh("Lichen%d" % seed)


def grass_mesh(seed, tall=False):
    r = random.Random(seed)
    b = Builder()
    for k in range(r.randint(6, 10)):
        c = Vector((r.uniform(-0.2, 0.2), r.uniform(-0.2, 0.2), 0))
        h = r.uniform(0.4, 0.8) * (1.6 if tall else 1.0)
        tip = c + Vector((r.uniform(-0.15, 0.15), r.uniform(-0.15, 0.15), h))
        b.limb(c, tip, 0.04, 0.0, pick("grass1", "grass2", "grass3"), segs=3)
    return b.mesh("Grass%d" % seed)


def log_mesh(seed, length=6.0):
    r = random.Random(seed)
    b = Builder()

    def col(f):
        if f.normal.z > 0.5 and r.random() < 0.6:
            return jitter(P[r.choice(["rmoss1", "rmoss3"])])
        return jitter(P[r.choice(["log", "log2", "snag"])])

    faces, _ = b.limb((-length / 2, 0, 0.25), (length / 2, 0, 0.3), 0.32, 0.24, col, segs=7)
    for k in range(3):
        a = r.uniform(0, math.tau)
        p0 = Vector((r.uniform(-length / 2, length / 2), 0, 0.35))
        b.limb(p0, p0 + Vector((r.uniform(-0.3, 0.3), math.cos(a) * 0.7, abs(math.sin(a)) * 0.6 + 0.2)), 0.05, 0.02, pick("snag"), segs=4)
    # root plate at one end
    b.ico((-length / 2 - 0.1, 0, 0.5), 0.8, pick("log2", "dirt3", "snag"), sub=1, scale=(0.35, 1.1, 1.0), displace=0.12)
    return b.mesh("Log%d" % seed)


def snag_mesh(seed):
    r = random.Random(seed)
    b = Builder()
    H = r.uniform(3.0, 5.5)
    faces, verts = b.limb((0, 0, -0.2), (0, 0, H), 0.3, 0.18, pick("snag", "snag2"), segs=6)
    top = max(v.co.z for v in verts)
    for v in verts:
        if v.co.z > top - 0.01:
            v.co.z += r.uniform(-0.9, 0.4)
    for k in range(r.randint(2, 4)):
        z = r.uniform(1.5, H - 0.5)
        a = r.uniform(0, math.tau)
        L = r.uniform(0.6, 1.3)
        b.limb((0, 0, z), (math.cos(a) * L, math.sin(a) * L, z + r.uniform(0.2, 0.6)), 0.05, 0.015, pick("snag2"), segs=4)
    return b.mesh("Snag%d" % seed)


def runestone_mesh(glow):
    b = Builder()
    m = Matrix.Diagonal(Vector((0.62, 0.3, 1.25, 1))) @ Matrix.Translation((0, 0, 1.0))
    res = bmesh.ops.create_cube(b.bm, size=1.0, matrix=Matrix.Translation((0, 0, 0.75)) @ Matrix.Diagonal(Vector((1.1, 0.5, 1.9, 1))))
    bmesh.ops.subdivide_edges(b.bm, edges=b.bm.edges[:], cuts=1, use_grid_fill=True)
    for v in b.bm.verts:
        if v.co.z > 1.3:
            v.co.x *= 0.7
            v.co.y *= 0.85
        if v.co.z > 1.65:
            v.co.x *= 0.7
        v.co += Vector((rng.uniform(-0.04, 0.04), rng.uniform(-0.03, 0.03), rng.uniform(-0.04, 0.04)))
    b.bm.normal_update()

    def col(f):
        if f.normal.z > 0.6:
            return jitter(P["rmoss1"])
        if rng.random() < 0.2:
            return jitter(P["lichen"])
        return jitter(P[rng.choice(["granite1", "granite2", "granite4"])], 0.04)

    b.paint(b.bm.faces[:], col)
    # carved tree-rune on the front (-Y) face, as thin raised strips
    y = -0.27
    strips = [((0, y, 0.95), (0.05, 0.03, 0.95)),
              ((-0.12, y, 1.18), (0.045, 0.03, 0.34)), ((0.12, y, 1.18), (0.045, 0.03, 0.34)),
              ((-0.12, y, 0.82), (0.045, 0.03, 0.3)), ((0.12, y, 0.82), (0.045, 0.03, 0.3))]
    rots = [None, Matrix.Rotation(0.6, 4, "Y"), Matrix.Rotation(-0.6, 4, "Y"), Matrix.Rotation(0.6, 4, "Y"), Matrix.Rotation(-0.6, 4, "Y")]
    for (c, s), ro in zip(strips, rots):
        b.box(s, c, lambda f: P["stone2"], rot=ro, mat_index=1)
    return b.mesh("RuneStone", mats=[MAT, MAT_RUNE_FOG if glow else MAT_RUNE_DAY])


def text_obj(body, loc, rot, size=0.13, parent=None):
    cu = bpy.data.curves.new("txt_" + body, "FONT")
    cu.body = body
    cu.size = size
    cu.extrude = 0.004
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    ob = bpy.data.objects.new("txt_" + body, cu)
    ob.data.materials.append(MAT_CARVE)
    ob.location = loc
    ob.rotation_euler = rot
    COLL.objects.link(ob)
    if parent:
        ob.parent = parent
    return ob


def signpost(loc, ground, rot_z, signs, lantern=False):
    b = Builder()
    b.box((0.13, 0.13, 2.3), (0, 0, 1.05), pick("wood2"))
    for (h, ang, _) in signs:
        rot = Matrix.Rotation(ang, 4, "Z")
        center = rot @ Vector((0.42, 0.08, h))
        b.box((0.95, 0.06, 0.22), center, pick("wood", "wood2"), rot=rot)
        tip = rot @ Vector((0.95, 0.08, h))
        b.box((0.16, 0.055, 0.16), tip, pick("wood"), rot=rot @ Matrix.Rotation(math.radians(45), 4, "Y"))
    me = b.mesh("Signpost")
    ob = place(me, (loc[0], loc[1], ground), rot_z)
    for (h, ang, txt) in signs:
        rot = Matrix.Rotation(ang, 4, "Z")
        c = rot @ Vector((0.42, 0.115, h))
        text_obj(txt, c, (math.radians(90), 0, ang + math.pi), size=0.15, parent=ob)
        # text facing -Y side as well (towards camera side)
        c2 = rot @ Vector((0.42, 0.045, h))
        text_obj(txt, c2, (math.radians(90), 0, ang), size=0.15, parent=ob)
    if lantern:
        lb = Builder()
        lb.box((0.05, 0.5, 0.05), (0, 0.25, 2.05), pick("wood2"))
        lb.box((0.2, 0.2, 0.06), (0, 0.5, 1.72), pick("belt"))
        lb.box((0.2, 0.2, 0.06), (0, 0.5, 1.42), pick("belt"))
        lb.box((0.14, 0.14, 0.24), (0, 0.5, 1.57), lambda f: P["gold"], mat_index=1)
        lb.limb((0, 0.5, 1.75), (0, 0.5, 2.03), 0.01, 0.01, pick("belt"), segs=3)
        lme = lb.mesh("Lantern", mats=[MAT, MAT_FLAME])
        lo = place(lme, (0, 0, 0), parent=ob)
        add_point(ob.matrix_world @ Vector((0, 0.5, 1.57)) if False else None, None, 0, parent=ob, local=(0, 0.5, 1.57), color="#FFA040", power=140, radius=0.12)
    return ob


def cairn(loc, ground, candle=False):
    b = Builder()
    z = 0.0
    r = 0.42
    for k in range(5):
        h = r * 0.55
        b.ico((rng.uniform(-0.04, 0.04), rng.uniform(-0.04, 0.04), z + h * 0.5), r, pick("granite1", "granite2", "granite3"), sub=1, scale=(1, 1, 0.55), displace=0.03)
        z += h * 0.95
        r *= 0.78
    if candle:
        b.limb((0.0, 0, z), (0.0, 0, z + 0.14), 0.035, 0.035, lambda f: lin("#E8DFC8"), segs=6)
        b.limb((0.0, 0, z + 0.14), (0.0, 0, z + 0.24), 0.025, 0.0, lambda f: P["gold"], segs=5, mat_index=1)
    ob = place(b.mesh("Cairn", mats=[MAT, MAT_FLAME]), (loc[0], loc[1], ground))
    if candle:
        add_point(None, None, 0, parent=ob, local=(0, 0, z + 0.3), color="#FF9A3C", power=45, radius=0.05)
    return ob


def totem(loc, ground, rot_z):
    b = Builder()
    b.limb((0, 0, -0.2), (0, 0, 2.6), 0.2, 0.16, pick("snag", "log"), segs=6)
    b.box((0.36, 0.3, 0.42), (0, 0.04, 2.75), pick("snag2", "snag"), top_scale=0.8)
    b.box((0.06, 0.04, 0.06), (-0.08, -0.12, 2.8), lambda f: P["carve"])
    b.box((0.06, 0.04, 0.06), (0.08, -0.12, 2.8), lambda f: P["carve"])
    for s in (-1, 1):
        p0 = Vector((0.14 * s, 0, 2.95))
        p1 = p0 + Vector((0.45 * s, -0.05, 0.55))
        p2 = p1 + Vector((0.35 * s, 0.05, 0.5))
        b.limb(p0, p1, 0.04, 0.03, pick("lichen2"), segs=4)
        b.limb(p1, p2, 0.03, 0.01, pick("lichen2"), segs=4)
        b.limb(p1, p1 + Vector((0.05 * s, -0.25, 0.3)), 0.025, 0.005, pick("lichen2"), segs=4)
        b.limb(p0 + (p1 - p0) * 0.4, p0 + (p1 - p0) * 0.4 + Vector((0.3 * s, -0.1, 0.2)), 0.025, 0.005, pick("lichen2"), segs=4)
    # cross-bar with hanging charms
    b.box((1.2, 0.08, 0.08), (0, 0, 2.0), pick("snag"))
    for s in (-0.5, 0.0, 0.5):
        b.limb((s, 0, 1.96), (s, 0, 1.6), 0.008, 0.008, pick("belt"), segs=3)
        b.ico((s, 0, 1.55), 0.07, pick("lichen2", "granite3"), sub=1)
    return place(b.mesh("Totem"), (loc[0], loc[1], ground), rot_z)


# ---------------------------------------------------------------- lights
def add_point(loc, _unused, _u2, parent=None, local=None, color="#FFFFFF", power=50, radius=0.1):
    ld = bpy.data.lights.new("pt", "POINT")
    ld.energy = power
    ld.color = lin(color)[:3]
    ld.shadow_soft_size = radius
    ob = bpy.data.objects.new("pt", ld)
    COLL.objects.link(ob)
    if parent:
        ob.parent = parent
        ob.location = local
    else:
        ob.location = loc
    return ob


# ---------------------------------------------------------------- characters
def player(loc, ground, facing, pose="walk"):
    root = bpy.data.objects.new("Player", None)
    root.location = (loc[0], loc[1], ground)
    root.rotation_euler = (0, 0, facing)
    COLL.objects.link(root)

    def part(name, build, pivot, rot=(0, 0, 0)):
        b = Builder()
        build(b)
        ob = place(b.mesh(name), pivot, parent=root, name=name)
        ob.rotation_euler = rot
        return ob

    attack = pose == "attack"
    hip = (0, 0, 0.95)
    torso = part("Torso", lambda b: (
        b.box((0.44, 0.26, 0.6), (0, 0, 0.3), pick("tunic", "tunic2"), top_scale=1.12),
        b.box((0.47, 0.29, 0.08), (0, 0, 0.05), pick("belt")),
        b.box((0.08, 0.1, 0.08), (0.1, 0.13, 0.05), lambda f: P["gold"]),
        b.box((0.12, 0.12, 0.1), (0, 0, 0.63), pick("skin")),
        b.box((0.5, 0.3, 0.12), (0, -0.01, 0.56), pick("bracer")),
    ), hip, rot=(0, 0, math.radians(-25) if attack else 0))
    head = part("Head", lambda b: (
        b.ico((0, 0, 0.17), 0.15, pick("skin"), sub=1, scale=(0.95, 1.0, 1.1)),
        b.ico((0, -0.035, 0.22), 0.155, pick("hair"), sub=1, scale=(1.0, 1.0, 0.85)),
        b.box((0.15, 0.07, 0.1), (0, 0.12, 0.08), pick("beard")),
    ), (0, 0, 0.66))
    head.parent = torso
    leg_sw = math.radians(28)
    for side, sw in ((1, -leg_sw), (-1, leg_sw)):
        part("Leg", lambda b: (
            b.box((0.17, 0.19, 0.62), (0, 0, -0.33), pick("trouser")),
            b.box((0.19, 0.27, 0.32), (0, 0.035, -0.8), pick("boot")),
        ), (0.11 * side, 0, 0.95), rot=(sw * (0.8 if attack else 1.0), 0, 0))
    # arms: right arm (+x) holds the sword, left arm the shield
    def right_arm(b):
        b.box((0.14, 0.14, 0.32), (0, 0, -0.16), pick("tunic"))
        b.box((0.13, 0.13, 0.28), (0, 0, -0.44), pick("bracer"))
        b.box((0.11, 0.11, 0.1), (0, 0, -0.63), pick("skin"))
        d = Vector((0, 0.45, -0.9)).normalized() if not attack else Vector((0, 1.0, 0.15)).normalized()
        h0 = Vector((0, 0, -0.63))
        b.limb(h0 - d * 0.1, h0 + d * 0.12, 0.03, 0.03, pick("belt"), segs=4)
        side = Vector((1, 0, 0))
        g = h0 + d * 0.13
        b.box((0.28, 0.05, 0.05), g, pick("gold"), rot=d.to_track_quat("Z", "Y").to_matrix().to_4x4())
        b.limb(g, g + d * 0.85, 0.045, 0.012, pick("steel"), segs=4)

    def left_arm(b):
        b.box((0.14, 0.14, 0.32), (0, 0, -0.16), pick("tunic"))
        b.box((0.13, 0.13, 0.28), (0, 0, -0.44), pick("bracer"))
        b.box((0.11, 0.11, 0.1), (0, 0, -0.63), pick("skin"))
        rot = Matrix.Rotation(math.radians(90), 4, "Y")
        res = bmesh.ops.create_cone(b.bm, cap_ends=True, cap_tris=False, segments=10, radius1=0.33, radius2=0.33, depth=0.05,
                                    matrix=Matrix.Translation((-0.11, 0.05, -0.42)) @ rot)
        fs = b._faces(res["verts"])
        cnt = [0]

        def sc(f):
            cnt[0] += 1
            return jitter(P["shieldpaint"] if cnt[0] % 2 else P["wood"])
        b.paint(fs, sc)
        b.ico((-0.15, 0.05, -0.42), 0.08, pick("steeldark"), sub=1)

    rarm = (math.radians(100), math.radians(-35), 0) if attack else (math.radians(-22), 0, math.radians(4))
    larm = (math.radians(45), 0, math.radians(-10)) if attack else (math.radians(22), 0, math.radians(-6))
    ra = part("ArmR", right_arm, (0.29, 0, 0.55), rot=rarm)
    ra.parent = torso
    la = part("ArmL", left_arm, (-0.29, 0, 0.55), rot=larm)
    la.parent = torso
    ck = part("Cloak", lambda b: b.box((0.5, 0.04, 0.95), (0, 0, -0.47), pick("cloak"), top_scale=0.82),
              (0, -0.16, 0.55), rot=(math.radians(-20 if not attack else -14), 0, 0))
    ck.parent = torso
    return root


def swing_arc(center, ground, facing):
    b = Builder()
    bm = b.bm
    a0, a1 = math.radians(-55), math.radians(50)
    n = 18
    verts = []
    for k in range(n + 1):
        t = k / n
        a = a0 + (a1 - a0) * t
        for rr in (1.05, 1.32):
            ca = a + math.pi / 2
            v = bm.verts.new((math.cos(ca) * rr, math.sin(ca) * rr, 1.35 - 0.55 * t))
            verts.append((v, t, rr))
    faces = []
    for k in range(n):
        q = [verts[2 * k][0], verts[2 * k + 1][0], verts[2 * k + 3][0], verts[2 * k + 2][0]]
        faces.append((bm.faces.new(q), k / n))
    for f, t in faces:
        for l in f.loops:
            l[b.col] = (1, 1, 1, min(0.55, 0.0 + t * t * 0.7))
    ob = place(b.mesh("Swing", mats=[MAT_SWING]), (center[0], center[1], ground), facing)
    return ob


def wraith(loc, ground, facing, antlers=False, scale=1.0):
    b = Builder()
    res = bmesh.ops.create_cone(b.bm, cap_ends=False, cap_tris=False, segments=9, radius1=0.6, radius2=0.2, depth=1.7,
                                matrix=Matrix.Translation((0, 0, 1.15)))
    for v in res["verts"]:
        if v.co.z < 0.5:
            v.co.z += rng.uniform(-0.3, 0.15)
            v.co.x *= rng.uniform(0.8, 1.25)
            v.co.y *= rng.uniform(0.8, 1.25)
    b.paint(b._faces(res["verts"]), lambda f: (1, 1, 1, 1))
    b.ico((0, 0.03, 2.15), 0.2, lambda f: (1, 1, 1, 1), sub=1, scale=(0.9, 1.0, 1.25))
    b.limb((0, -0.05, 2.0), (0, 0.12, 2.55), 0.3, 0.02, lambda f: (1, 1, 1, 1), segs=8)
    for s in (-1, 1):
        b.limb((0.24 * s, 0, 1.85), (0.36 * s, 0.6, 1.1), 0.07, 0.015, lambda f: (1, 1, 1, 1), segs=5)
    if antlers:
        for s in (-1, 1):
            p0 = Vector((0.12 * s, 0.0, 2.45))
            p1 = p0 + Vector((0.35 * s, -0.05, 0.45))
            b.limb(p0, p1, 0.03, 0.02, lambda f: (1, 1, 1, 1), segs=4)
            b.limb(p1, p1 + Vector((0.3 * s, 0.05, 0.35)), 0.02, 0.005, lambda f: (1, 1, 1, 1), segs=4)
            b.limb(p1, p1 + Vector((0.0, -0.1, 0.35)), 0.02, 0.005, lambda f: (1, 1, 1, 1), segs=4)
    ob = place(b.mesh("Wraith", mats=[MAT_GHOST]), (loc[0], loc[1], ground + 0.15), facing, scale=scale)
    add_point(None, None, 0, parent=ob, local=(0, 0.2, 1.4), color="#9FD8FF", power=90, radius=0.4)
    return ob


def stag(loc, ground, facing, scale=1.3):
    b = Builder()
    W = lambda f: (1, 1, 1, 1)
    b.ico((0, 0, 1.65), 1.0, W, sub=1, scale=(0.5, 1.15, 0.52))
    b.limb((0, 0.85, 1.8), (0, 1.35, 2.55), 0.3, 0.17, W, segs=7)
    b.ico((0, 1.62, 2.55), 1.0, W, sub=1, scale=(0.19, 0.42, 0.21), rot=Matrix.Rotation(math.radians(25), 4, "X"))
    for sx in (-1, 1):
        for sy, ln in ((1, 0.8), (-1, 0.75)):
            top = Vector((0.27 * sx, 0.7 * sy, 1.45))
            knee = Vector((0.27 * sx, 0.7 * sy + 0.08 * sy, 0.75))
            b.limb(top, knee, 0.12, 0.07, W, segs=5)
            b.limb(knee, Vector((0.27 * sx, 0.7 * sy, 0.0)), 0.07, 0.04, W, segs=5)
    for s in (-1, 1):
        p0 = Vector((0.1 * s, 1.5, 2.8))
        p1 = p0 + Vector((0.4 * s, -0.25, 0.65))
        p2 = p1 + Vector((0.35 * s, -0.35, 0.6))
        p3 = p2 + Vector((0.15 * s, -0.25, 0.45))
        b.limb(p0, p1, 0.06, 0.05, W, segs=5)
        b.limb(p1, p2, 0.05, 0.035, W, segs=5)
        b.limb(p2, p3, 0.035, 0.01, W, segs=5)
        for pa, d in ((p1, Vector((0.05 * s, 0.35, 0.35))), (p2, Vector((0.1 * s, 0.3, 0.35))), (p0 + (p1 - p0) * 0.4, Vector((0.0, 0.4, 0.2)))):
            b.limb(pa, pa + d, 0.03, 0.005, W, segs=4)
    b.limb((0, -1.05, 1.9), (0, -1.25, 1.6), 0.1, 0.02, W, segs=5)
    ob = place(b.mesh("Stag", mats=[MAT_GHOST]), (loc[0], loc[1], ground), facing, scale=scale)
    add_point(None, None, 0, parent=ob, local=(0, 0.3, 1.8), color="#A8DCFF", power=260, radius=0.8)
    return ob


def wisp(loc):
    b = Builder()
    b.ico((0, 0, 0), 0.06, lambda f: (1, 1, 1, 1), sub=1)
    ob = place(b.mesh("Wisp", mats=[MAT_WISP]), loc)
    add_point(None, None, 0, parent=ob, local=(0, 0, 0), color="#D0EEFF", power=12, radius=0.05)
    return ob


# ---------------------------------------------------------------- populate
def blocked_for_props(x, y, pad):
    if path_dist(x, y) < 1.25 + pad:
        return True
    if tarn_frac(x, y) < 1.02 + pad * 0.15:
        return True
    if in_puddle(x, y, 0.2 + pad):
        return True
    return False


KEEP_CLEAR = [  # spots where characters stand in the shots
    (Vector((0.0, 0.0)), 2.6), (Vector((0.4, 0.2)), 2.6), (Vector((3.8, 4.6)), 2.0), (Vector((6.0, 2.0)), 1.8),
    (Vector((-1.8, 5.6)), 1.8), (Vector((14.6, 10.5)), 2.5), (Vector((-12.0, 11.0)), 2.4), (Vector((-16.0, 16.0)), 3.5),
]


def near_clear(x, y, extra=0.0):
    for c, r in KEEP_CLEAR:
        if (Vector((x, y)) - c).length < r + extra:
            return True
    return False


def poisson(region, count, mindist, accept, tries=12):
    x0, x1, y0, y1 = region
    pts = []
    cell = {}
    md2 = mindist * mindist
    for _ in range(count * tries):
        if len(pts) >= count:
            break
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        ci, cj = int(x // mindist), int(y // mindist)
        clash = False
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for (px, py) in cell.get((ci + di, cj + dj), ()):
                    if (x - px) ** 2 + (y - py) ** 2 < md2:
                        clash = True
                        break
                if clash:
                    break
            if clash:
                break
        if clash or not accept(x, y):
            continue
        pts.append((x, y))
        cell.setdefault((ci, cj), []).append((x, y))
    return pts


REGION = (-40, 40, -30, 38)
TREES = []
ROOTS = {}
SPECIAL = {}


def populate(mode):
    fog = mode == "fog"

    def tree_ok(x, y):
        if blocked_for_props(x, y, 0.4) or near_clear(x, y, 0.6):
            return False
        bd = (Vector((x, y)) - BOG_C).length / BOG_R
        if bd < 0.8 and rng.random() < 0.85:
            return False
        return tarn_frac(x, y) > 1.25

    TREE_PTS[:] = poisson(REGION, 240, 4.2, tree_ok)
    TREE_CELL.clear()
    for (x, y) in TREE_PTS:
        TREE_CELL.setdefault((int(x // 4), int(y // 4)), []).append((x, y))
    build_terrain()
    build_outer_ground()
    # water
    wb = Builder()
    bm = wb.bm
    vs = [bm.verts.new((TARN_C.x + math.cos(a) * tarn_r(a) * 1.08, TARN_C.y + math.sin(a) * tarn_r(a) * 1.08, WATER_Z))
          for a in [k * math.tau / 32 for k in range(32)]]
    f = bm.faces.new(vs)
    wb.paint([f], lambda f: (1, 1, 1, 1))
    place(wb.mesh("Tarn", mats=[MAT_WATER]), (0, 0, 0))
    for c, r in PUDDLES:
        pb = Builder()
        vs = [pb.bm.verts.new((c.x + math.cos(a) * r * rng.uniform(0.8, 1.15), c.y + math.sin(a) * r * rng.uniform(0.8, 1.15), BOG_Z + 0.05))
              for a in [k * math.tau / 9 for k in range(9)]]
        pf = pb.bm.faces.new(vs)
        pb.paint([pf], lambda f: (1, 1, 1, 1))
        place(pb.mesh("Puddle", mats=[MAT_WATER]), (0, 0, 0))

    pines = [pine_mesh(s) for s in range(8)]
    spruces = [spruce_mesh(100 + s) for s in range(5)]
    boulders = [boulder_mesh(200 + s) for s in range(8)]
    bigs = [boulder_mesh(300 + s, big=True) for s in range(4)]
    shrubs_r = [shrub_mesh(400 + s, "berryred") for s in range(3)]
    shrubs_b = [shrub_mesh(410 + s, "berryblue") for s in range(3)]
    shrubs = [shrub_mesh(420 + s, None) for s in range(3)]
    heathers = [heather_mesh(500 + s) for s in range(4)]
    lichens = [lichen_mesh(600 + s) for s in range(3)]
    grasses = [grass_mesh(700 + s) for s in range(4)]
    reeds = [grass_mesh(720 + s, tall=True) for s in range(3)]
    logs = [log_mesh(800 + s, rng.uniform(5, 7)) for s in range(3)]
    snags = [snag_mesh(900 + s) for s in range(4)]

    for (x, y) in TREE_PTS:
        me, H = rng.choice(pines)
        ob = place(me, (x, y, height(x, y) - 0.15), rng.uniform(0, math.tau), rng.uniform(0.85, 1.12))
        TREES.append(ob)
    for (x, y) in poisson(REGION, 120, 2.2, lambda x, y: not blocked_for_props(x, y, 0.2) and not near_clear(x, y, -0.6)):
        ob = place(rng.choice(spruces), (x, y, height(x, y) - 0.05), rng.uniform(0, math.tau), rng.uniform(0.8, 1.2))
        TREES.append(ob)
    for (x, y) in poisson(REGION, 190, 2.8, lambda x, y: not blocked_for_props(x, y, 0.6) and not near_clear(x, y, -0.4) and not near_tree(x, y, 1.2)):
        place(rng.choice(boulders), (x, y, height(x, y) - 0.25), rng.uniform(0, math.tau), rng.uniform(0.6, 1.4))
    for (x, y) in poisson(REGION, 45, 6.0, lambda x, y: not blocked_for_props(x, y, 1.6) and not near_clear(x, y, 1.0) and not near_tree(x, y, 2.0)):
        place(rng.choice(bigs), (x, y, height(x, y) - 0.5), rng.uniform(0, math.tau), rng.uniform(1.0, 1.7))
    for k, (x, y, s) in enumerate([(-5.4, 0.2, 1.5), (6.8, -0.8, 1.2), (-1.8, -4.6, 1.3), (2.6, 9.2, 1.5), (-5.2, 8.6, 1.2), (8.6, 4.2, 1.1)]):
        place(bigs[k % len(bigs)], (x, y, height(x, y) - 0.55), rng.uniform(0, math.tau), s)
    # rocky outcrop on the far shore of the tarn
    for k, (dx, dy, s) in enumerate([(2.2, 3.4, 2.0), (4.2, 1.6, 1.7), (0.2, 4.6, 1.5), (5.2, 3.8, 1.3), (2.8, 5.6, 1.2)]):
        x, y = TARN_C.x + dx, TARN_C.y + dy
        place(bigs[k % len(bigs)], (x, y, height(x, y) - 0.6), rng.uniform(0, math.tau), s)
    # ground cover
    def gc_ok(x, y):
        return not blocked_for_props(x, y, -0.15)
    for (x, y) in poisson(REGION, 2500, 0.85, gc_ok):
        bd = (Vector((x, y)) - BOG_C).length / BOG_R
        tf = tarn_frac(x, y)
        r = rng.random()
        if tf < 1.4:
            me = rng.choice(reeds if tf < 1.2 else grasses)
        elif bd < 1.1:
            me = rng.choice(grasses + grasses + shrubs) if r < 0.8 else rng.choice(lichens)
        else:
            n = noise.noise(Vector((x * 0.18, y * 0.18, 9.0)))
            blue = noise.noise(Vector((x * 0.11, y * 0.11, 21.0))) > 0.32
            red = noise.noise(Vector((x * 0.11, y * 0.11, 33.0))) > 0.42
            if n > 0.2:
                me = rng.choice(shrubs_b if blue and r < 0.6 else (shrubs_r if red and r < 0.6 else shrubs))
            elif n < -0.4:
                me = rng.choice(lichens + shrubs)
            elif r < 0.5:
                me = rng.choice(shrubs_b if blue and r < 0.3 else shrubs)
            elif r < 0.66:
                me = rng.choice(grasses)
            else:
                continue
        place(me, (x, y, height(x, y) - 0.03), rng.uniform(0, math.tau), rng.uniform(1.0, 1.7))
    # distant forest beyond the play area
    far_ok = lambda x, y: not (REGION[0] < x < REGION[1] and REGION[2] < y < REGION[3])
    for (x, y) in poisson((-125, 125, -125, 125), 2600, 4.6, far_ok):
        me, H = rng.choice(pines)
        place(me, (x, y, height(x, y) - 0.15), rng.uniform(0, math.tau), rng.uniform(0.85, 1.15))
    for (x, y) in poisson((-125, 125, -125, 125), 700, 6.0, far_ok):
        if rng.random() < 0.5:
            place(rng.choice(spruces), (x, y, height(x, y) - 0.05), rng.uniform(0, math.tau), rng.uniform(1.0, 1.8))
        else:
            place(rng.choice(boulders + bigs), (x, y, height(x, y) - 0.4), rng.uniform(0, math.tau), rng.uniform(0.6, 1.4))
    # small stones on the path
    stones = [boulder_mesh(950 + s, tones=PEBBLE) for s in range(3)]
    for pts, w in PATHS:
        for i in range(0, len(pts) - 1, 3):
            if rng.random() < 0.35:
                p = pts[i] + Vector((rng.uniform(-0.8, 0.8), rng.uniform(-0.8, 0.8)))
                if near_clear(p.x, p.y, -1.6):
                    continue
                place(rng.choice(stones), (p.x, p.y, height(p.x, p.y) - 0.05), rng.uniform(0, math.tau), rng.uniform(0.12, 0.25))
    # roots crossing the path near trees
    for t in TREES[:260]:
        x, y = t.location.x, t.location.y
        if 1.2 < path_dist(x, y) < 3.4 and rng.random() < 0.7:
            rb = Builder()
            for k in range(rng.randint(2, 4)):
                a = rng.uniform(0, math.tau)
                L = rng.uniform(1.2, 2.6)
                p0 = Vector((x, y, height(x, y) + 0.05))
                pe = Vector((x + math.cos(a) * L, y + math.sin(a) * L, 0))
                pe.z = height(pe.x, pe.y) + 0.02
                rb.limb(p0, pe, 0.09, 0.025, pick("barklow", "log2", "snag"), segs=4)
            ROOTS[t.name] = place(rb.mesh("Roots"), (0, 0, 0))

    # bog dressing
    for k, (dx, dy) in enumerate([(2.5, 2.5), (-3.5, 1.5), (1.0, -4.0), (-4.5, -3.0), (4.6, -1.0)]):
        x, y = BOG_C.x + dx, BOG_C.y + dy
        TREES.append(place(snags[k % len(snags)], (x, y, height(x, y)), rng.uniform(0, math.tau)))
    for (dx, dy, a) in [(3.2, -2.3, 0.4), (-2.0, 4.8, 2.0), (-6.0, -1.0, 1.1)]:
        x, y = BOG_C.x + dx, BOG_C.y + dy
        place(rng.choice(logs), (x, y, height(x, y) - 0.1), a)
    for (x, y, a) in [(-4.0, 4.2, 0.9), (7.5, -2.5, 2.4)]:
        place(rng.choice(logs), (x, y, height(x, y) - 0.1), a)

    # landmarks
    rs = place(runestone_mesh(fog), (-2.9, 2.0, height(-2.9, 2.0) - 0.1), math.radians(-50), 1.0)
    SPECIAL["runestone"] = rs
    if fog:
        add_point((-2.9 + 0.8, 2.0 - 0.9, height(-2.9, 2.0) + 1.0), None, 0, color="#8FD8FF", power=70, radius=0.3)
    signpost((3.9, 2.0), height(3.9, 2.0), math.radians(10),
             [(1.85, math.radians(35), "SJÖN"), (1.55, math.radians(150), "MYREN")], lantern=fog)
    cairn((-10.2, 12.8), height(-10.2, 12.8), candle=fog)
    cairn((4.8, -2.2), height(4.8, -2.2), candle=fog)
    totem((-18.0, 10.8), height(-18.0, 10.8), math.radians(40))
    dress_path_edges(grasses, stones)


def dress_path_edges(grasses, stones):
    """Low grass tufts in the worn edges of the paths, and pebbles kicked about on and beside them. Uses its own
    random numbers, so the rest of the scene keeps its layout."""
    er = random.Random(4242)
    x0, x1, y0, y1 = REGION
    for _ in range(26000):
        x, y = er.uniform(x0, x1), er.uniform(y0, y1)
        d = path_dist(x, y) / 0.875  # half-widths from the centre line, 1 at the path's nominal edge
        if d > 1.8 or near_clear(x, y, -0.6) or tarn_frac(x, y) < 1.05 or in_puddle(x, y, 0.2):
            continue
        r = er.random()
        if 0.75 < d < 1.7 and r < smooth(0.75, 1.3, d) * 0.65:
            place(er.choice(grasses), (x, y, height(x, y) - 0.03), er.uniform(0, math.tau), er.uniform(0.45, 0.85))
        elif d < 1.35 and r > 0.85:
            place(er.choice(stones), (x, y, height(x, y) - 0.02), er.uniform(0, math.tau), er.uniform(0.04, 0.09))


# ---------------------------------------------------------------- lighting & render setup
def setup_world(mode):
    w = bpy.data.worlds.new("World")
    scene.world = w
    safe(w, "use_nodes", True)
    nt = w.node_tree
    bg = nt.nodes.get("Background") or nt.nodes.new("ShaderNodeBackground")
    out = nt.nodes.get("World Output") or nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    sun_d = bpy.data.lights.new("Sun", "SUN")
    sun = bpy.data.objects.new("Sun", sun_d)
    COLL.objects.link(sun)
    if mode == "day":
        bg.inputs["Color"].default_value = lin("#A9C6E6")
        bg.inputs["Strength"].default_value = 1.1
        sky_for_camera(nt, bg, out, [(0.0, "#DCE5EC"), (0.08, "#C4D7EA"), (0.35, "#93B7E0"), (0.8, "#6C9AD3")], clouds=True)
        sun_d.energy = 4.2
        sun_d.color = lin("#FFE4BC")[:3]
        sun_d.angle = math.radians(2.5)
        sun.rotation_euler = (math.radians(52), 0, math.radians(-120))
        haze_box(0.003, "#DDE8F2")
    else:
        bg.inputs["Color"].default_value = lin("#98A5B2")
        bg.inputs["Strength"].default_value = 0.9
        sky_for_camera(nt, bg, out, [(0.0, "#A9B4BE"), (0.25, "#9AA6B2"), (0.8, "#7F8B98")], clouds=False)
        sun_d.energy = 1.1
        sun_d.color = lin("#C4D2E0")[:3]
        sun_d.angle = math.radians(8)
        sun.rotation_euler = (math.radians(40), 0, math.radians(-120))
        haze_box(0.028, "#C3CDD6", 0.3)
        ground_fog()


def sky_for_camera(nt, bg, out, stops, clouds):
    N, L = nt.nodes, nt.links
    tc = N.new("ShaderNodeTexCoord")
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(tc.outputs["Generated"], sep.inputs[0])
    rp = N.new("ShaderNodeValToRGB")
    el = rp.color_ramp.elements
    el[0].position, el[0].color = stops[0][0], lin(stops[0][1])
    el[1].position, el[1].color = stops[-1][0], lin(stops[-1][1])
    for p_, c_ in stops[1:-1]:
        el.new(p_).color = lin(c_)
    L.new(sep.outputs["Z"], rp.inputs["Fac"])
    col = rp.outputs["Color"]
    if clouds:
        nz = N.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 3.2
        nz.inputs["Detail"].default_value = 4.0
        L.new(tc.outputs["Generated"], nz.inputs["Vector"])
        cm = N.new("ShaderNodeMapRange")
        cm.inputs["From Min"].default_value = 0.56
        cm.inputs["From Max"].default_value = 0.72
        L.new(nz.outputs["Fac"], cm.inputs["Value"])
        hm = N.new("ShaderNodeMapRange")
        hm.inputs["From Min"].default_value = 0.04
        hm.inputs["From Max"].default_value = 0.3
        L.new(sep.outputs["Z"], hm.inputs["Value"])
        mul = N.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        L.new(cm.outputs[0], mul.inputs[0])
        L.new(hm.outputs[0], mul.inputs[1])
        mx = N.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        L.new(mul.outputs[0], [x for x in mx.inputs if x.name == "Factor" and x.type == "VALUE"][0])
        L.new(col, [x for x in mx.inputs if x.name == "A" and x.type == "RGBA"][0])
        [x for x in mx.inputs if x.name == "B" and x.type == "RGBA"][0].default_value = (0.95, 0.96, 0.97, 1)
        col = [x for x in mx.outputs if x.name == "Result" and x.type == "RGBA"][0]
    skybg = N.new("ShaderNodeBackground")
    skybg.inputs["Strength"].default_value = 1.0
    L.new(col, skybg.inputs["Color"])
    lp = N.new("ShaderNodeLightPath")
    mix = N.new("ShaderNodeMixShader")
    L.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    L.new(bg.outputs[0], mix.inputs[1])
    L.new(skybg.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], out.inputs["Surface"])


def haze_box(density, hexcol, aniso=0.0):
    """Uniform haze in a big box (an Eevee world volume would also block the sun)."""
    me = bpy.data.meshes.new("HazeBox")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bm.to_mesh(me)
    bm.free()
    m = bpy.data.materials.new("Haze")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Density"].default_value = density
    vol.inputs["Color"].default_value = lin(hexcol)
    try:
        vol.inputs["Anisotropy"].default_value = aniso
    except Exception:
        pass
    nt.links.new(vol.outputs[0], out.inputs["Volume"])
    me.materials.append(m)
    ob = bpy.data.objects.new("Haze", me)
    ob.location = (0, 0, 24)
    ob.scale = (140, 140, 30)
    COLL.objects.link(ob)


def ground_fog():
    me = bpy.data.meshes.new("FogBox")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bm.to_mesh(me)
    bm.free()
    m = bpy.data.materials.new("GroundFog")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = lin("#D3DBE2")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    hmap = nt.nodes.new("ShaderNodeMapRange")
    hmap.inputs["From Min"].default_value = -1.0
    hmap.inputs["From Max"].default_value = 1.0
    hmap.inputs["To Min"].default_value = 1.0
    hmap.inputs["To Max"].default_value = 0.0
    nt.links.new(sep.outputs["Z"], hmap.inputs["Value"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 9.0
    try:
        nz.inputs["Detail"].default_value = 3.0
    except Exception:
        pass
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    nmap = nt.nodes.new("ShaderNodeMapRange")
    nmap.inputs["From Min"].default_value = 0.38
    nmap.inputs["From Max"].default_value = 0.68
    nt.links.new(nz.outputs["Fac"], nmap.inputs["Value"])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    nt.links.new(hmap.outputs[0], mul.inputs[0])
    nt.links.new(nmap.outputs[0], mul.inputs[1])
    mul2 = nt.nodes.new("ShaderNodeMath")
    mul2.operation = "MULTIPLY"
    mul2.inputs[1].default_value = 1.1
    nt.links.new(mul.outputs[0], mul2.inputs[0])
    pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    pw.inputs[1].default_value = 1.6
    nt.links.new(mul2.outputs[0], pw.inputs[0])
    nt.links.new(pw.outputs[0], vol.inputs["Density"])
    nt.links.new(vol.outputs[0], out.inputs["Volume"])
    me.materials.append(m)
    ob = bpy.data.objects.new("GroundFog", me)
    ob.location = (0, 0, 0.6)
    ob.scale = (130, 130, 2.4)
    COLL.objects.link(ob)


def setup_render():
    r = scene.render
    r.engine = "BLENDER_EEVEE"
    r.resolution_x, r.resolution_y = RES
    r.resolution_percentage = 100
    e = scene.eevee
    safe(e, "taa_render_samples", SAMPLES)
    safe(e, "use_shadows", True)
    safe(e, "use_raytracing", True)
    safe(e, "ray_tracing_method", "SCREEN")
    safe(e, "use_volumetric_shadows", True)
    safe(e, "volumetric_tile_size", "4" if QUALITY == "final" else "8")
    safe(e, "volumetric_samples", 64 if QUALITY == "final" else 32)
    safe(e, "volumetric_start", 1.0)
    safe(e, "volumetric_end", 90.0)
    safe(e, "use_gtao", True)
    safe(e, "shadow_ray_count", 2)
    safe(e, "shadow_step_count", 8)
    vs = scene.view_settings
    safe(vs, "view_transform", "AgX")
    for look in ("AgX - Medium High Contrast", "Medium High Contrast", "AgX - Punchy", "Punchy"):
        try:
            vs.look = look
            break
        except Exception:
            continue


def camera_for(target, dist=27.0, pitch=55.0, yaw=225.0, lens=50):
    cd = bpy.data.cameras.new("Cam")
    cd.lens = lens
    cd.clip_end = 300
    cam = bpy.data.objects.new("Cam", cd)
    COLL.objects.link(cam)
    t = Vector(target)
    p = math.radians(pitch)
    y = math.radians(yaw)
    off = Vector((math.cos(y) * math.cos(p), math.sin(y) * math.cos(p), math.sin(p))) * dist
    cam.location = t + off
    cam.rotation_euler = (t - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    bpy.context.view_layer.update()
    return cam


def orbit_camera(pivot, yaw, pitch, dist, lens=35):
    pv = Vector(pivot)
    look = pv + Vector((0, 0, 0.9 * (1 - pitch / 90.0)))
    cd = bpy.data.cameras.new("Cam")
    cd.lens = lens
    cd.clip_start = 0.2
    cd.clip_end = 400
    cam = bpy.data.objects.new("Cam", cd)
    COLL.objects.link(cam)
    p, y = math.radians(pitch), math.radians(yaw)
    cam.location = pv + Vector((math.cos(y) * math.cos(p), math.sin(y) * math.cos(p), math.sin(p))) * dist
    cam.rotation_euler = (look - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    bpy.context.view_layer.update()
    # nothing may sit right in front of the lens
    for ob in scene.objects:
        if ob.type == "MESH" and ob.name not in ("Terrain", "OuterGround", "Haze", "GroundFog", "Tarn") and not ob.name.startswith("Puddle"):
            if (ob.matrix_world.translation - cam.location).length < 2.2 and ob.parent is None and ob.name not in ("Wraith", "Stag"):
                ob.hide_render = True
    return cam


def cull_occluders(cam, subjects):
    """Hide trees that would cover the characters (games fade these out)."""
    bpy.context.view_layer.update()
    cpos = cam.matrix_world.translation
    subj = [(world_to_camera_view(scene, cam, s), (s - cpos).length) for s in subjects]
    hidden = 0
    for t in TREES:
        base = t.matrix_world.translation
        dims = t.dimensions
        hgt = dims.z
        samples = [base + Vector((0, 0, hgt * f)) for f in (0.1, 0.35, 0.6, 0.8, 0.95)]
        rad = max(dims.x, dims.y) * 0.5
        hide = False
        for s2, sd in subj:
            for sp in samples:
                p = world_to_camera_view(scene, cam, sp)
                rr = 0.07 + (rad / max(0.1, (sp - cpos).length)) * 1.1
                if (sp - cpos).length < sd - 0.5 and abs(p.x - s2.x) < rr and abs(p.y - s2.y) < rr * 1.8:
                    hide = True
                    break
            if hide:
                break
        if not hide and hgt > 3:
            # tall trees between the camera and the play area (games fade these out)
            top = world_to_camera_view(scene, cam, base + Vector((0, 0, hgt * 0.85)))
            if (base - cpos).length < subj[0][1] - 2 and abs(top.x - 0.5) < 0.3 and top.y < 0.5:
                hide = True
        if hide:
            t.hide_render = True
            if t.name in ROOTS:
                ROOTS[t.name].hide_render = True
            hidden += 1
    print("culled", hidden)


def screen(cam, v):
    p = world_to_camera_view(scene, cam, Vector(v))
    return [round(p.x * RES[0], 1), round((1 - p.y) * RES[1], 1)]


def g(x, y):
    return height(x, y)


# ---------------------------------------------------------------- shots
def run(shot):
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    TREES.clear()
    ROOTS.clear()
    global rng
    rng = random.Random(7)
    mode = "fog" if (shot.startswith("fog") or "fog" in shot) else "day"
    setup_render()
    setup_world(mode)
    grade = MAT.node_tree.nodes["Grade"]
    grade.inputs["Saturation"].default_value = 1.0 if mode == "day" else 0.62
    grade.inputs["Value"].default_value = 1.0 if mode == "day" else 0.92
    gg = MAT_GROUND.node_tree.nodes["Grade"]
    gg.inputs["Saturation"].default_value = 1.0 if mode == "day" else 0.62
    gg.inputs["Value"].default_value = 1.0 if mode == "day" else 0.92
    populate(mode)
    hud = {"shot": shot, "res": RES}
    subjects = []
    if shot in ("day_path", "fog_path"):
        if shot == "day_path":
            px, py = 0.0, 0.0
            face = math.atan2(4.6, 3.4) - math.pi / 2
            player((px, py), g(px, py), face, "walk")
            cam = camera_for((px + 0.9, py + 0.9, g(px, py) + 0.8))
            hud["cursor"] = screen(cam, (3.6, 4.0, g(3.6, 4.0) + 0.3))
        else:
            px, py = 0.4, 0.2
            tx, ty = 3.8, 4.6
            face = math.atan2(ty - py, tx - px) - math.pi / 2
            player((px, py), g(px, py), face, "attack")
            swing_arc((px, py), g(px, py), face)
            w1 = wraith((tx, ty), g(tx, ty), math.atan2(py - ty, px - tx) - math.pi / 2, antlers=True)
            wraith((6.2, 1.8), g(6.2, 1.8), math.radians(150), scale=0.95)
            wraith((-1.8, 5.6), g(-1.8, 5.6), math.radians(-120), scale=1.05)
            wraith((8.8, 7.5), g(8.8, 7.5), math.radians(160), antlers=True, scale=1.1)
            for (x, y, z) in [(2.0, 6.5, 1.6), (-4.0, 4.0, 2.2), (7.5, 3.5, 1.2), (-0.5, -3.0, 1.8), (5.0, 9.0, 2.0)]:
                wisp((x, y, g(x, y) + z))
            cam = camera_for((px + 1.7, py + 1.9, g(px, py) + 0.8))
            hud["cursor"] = screen(cam, (tx, ty, g(tx, ty) + 1.4))
            hud["target_head"] = screen(cam, (tx, ty, g(tx, ty) + 3.1))
            hud["damage"] = screen(cam, (tx + 1.1, ty - 0.7, g(tx, ty) + 1.9))
            subjects += [Vector((tx, ty, g(tx, ty) + 1.2)), Vector((6.2, 1.8, g(6.2, 1.8) + 1.2)), Vector((-1.8, 5.6, g(-1.8, 5.6) + 1.2))]
    elif shot == "day_tarn":
        px, py = 14.6, 10.5
        face = math.atan2(TARN_C.y - py, TARN_C.x - px) - math.pi / 2
        player((px, py), g(px, py), face, "walk")
        cam = camera_for((16.0, 14.0, WATER_Z + 0.6))
        hud["cursor"] = screen(cam, (17.8, 11.6, g(17.8, 11.6) + 0.2))
    elif shot == "fog_bog":
        px, py = -12.0, 11.0
        sx, sy = -16.0, 16.0
        face = math.atan2(sy - py, sx - px) - math.pi / 2
        player((px, py), g(px, py), face, "walk")
        stag((sx, sy), g(sx, sy), math.atan2(py - sy, px - sx) - math.pi / 2)
        wraith((-10.0, 17.2), g(-10.0, 17.2), math.radians(200), scale=0.9)
        wraith((-19.5, 14.0), g(-19.5, 14.0), math.radians(-60), antlers=True)
        for (x, y, z) in [(-13.5, 12.0, 1.4), (-15.0, 10.5, 2.0), (-11.0, 14.5, 1.7), (-17.0, 13.0, 1.2), (-14.0, 17.5, 2.6), (-9.5, 10.0, 1.5), (-18.5, 17.0, 1.9)]:
            wisp((x, y, g(x, y) + z))
        cam = camera_for((-13.0, 13.4, BOG_Z + 0.8))
        hud["cursor"] = screen(cam, (-14.6, 14.2, BOG_Z + 0.5))
        subjects += [Vector((sx, sy, g(sx, sy) + 2.5)), Vector((sx, sy, g(sx, sy) + 4.5))]
    elif shot.startswith("cam_"):
        CAMS = {
            "cam_default": ("day", (0.0, 0.0), 225.0, 55.0, 20.0),
            "cam_topdown": ("day", (0.0, 0.0), 225.0, 84.0, 22.0),
            "cam_side": ("day", (0.0, 0.0), 315.0, 38.0, 15.0),
            "cam_behind": ("day", (0.0, 0.0), 233.5, 16.0, 8.5),
            "cam_tarn": ("day", (14.6, 10.5), 247.7, 22.0, 10.0),
            "cam_fogbehind": ("fog", (0.4, 0.2), 232.3, 13.0, 8.0),
        }
        _, (px, py), yaw, pitch, dist = CAMS[shot]
        if shot == "cam_fogbehind":
            tx, ty = 3.8, 4.6
            face = math.atan2(ty - py, tx - px) - math.pi / 2
            player((px, py), g(px, py), face, "attack")
            swing_arc((px, py), g(px, py), face)
            wraith((tx, ty), g(tx, ty), math.atan2(py - ty, px - tx) - math.pi / 2, antlers=True)
            wraith((6.2, 1.8), g(6.2, 1.8), math.radians(150), scale=0.95)
            wraith((-1.8, 5.6), g(-1.8, 5.6), math.radians(-120), scale=1.05)
            wraith((8.8, 7.5), g(8.8, 7.5), math.radians(160), antlers=True, scale=1.1)
            for (x, y, z) in [(2.0, 6.5, 1.6), (-4.0, 4.0, 2.2), (7.5, 3.5, 1.2), (5.0, 9.0, 2.0), (1.0, 3.0, 2.4)]:
                wisp((x, y, g(x, y) + z))
            cam = orbit_camera((px, py, g(px, py) + 1.4), yaw, pitch, dist)
            hud["cursor"] = screen(cam, (tx, ty, g(tx, ty) + 1.4))
            hud["target_head"] = screen(cam, (tx, ty, g(tx, ty) + 3.1))
            hud["damage"] = screen(cam, (tx + 0.9, ty - 0.6, g(tx, ty) + 2.0))
            subjects += [Vector((tx, ty, g(tx, ty) + 1.2))]
        else:
            if shot == "cam_tarn":
                face = math.atan2(TARN_C.y - py, TARN_C.x - px) - math.pi / 2
            else:
                face = math.atan2(4.6, 3.4) - math.pi / 2
            player((px, py), g(px, py), face, "walk")
            cam = orbit_camera((px, py, g(px, py) + 1.4), yaw, pitch, dist)
            f = face + math.pi / 2
            aim = (px + math.cos(f) * 5.0, py + math.sin(f) * 5.0)
            hud["cursor"] = screen(cam, (aim[0], aim[1], g(*aim) + 0.3))
        hud["yaw"], hud["pitch"] = yaw, pitch
    subjects.insert(0, Vector((px, py, g(px, py) + 1.0)))
    if mode == "fog":
        add_point((px, py, g(px, py) + 3.2), None, 0, color="#FFE2B8", power=320, radius=1.0)
    cull_occluders(cam, subjects)
    hud["player_head"] = screen(cam, (px, py, g(px, py) + 2.2))
    hud["player_feet"] = screen(cam, (px, py, g(px, py)))
    hud["player_world"] = [px, py]
    hud["facing"] = face
    hud["mode"] = mode
    # path polylines for the minimap
    hud["paths"] = [[[round(p.x, 2), round(p.y, 2)] for p in pts[::2]] for pts, _ in PATHS]
    hud["tarn"] = [[round(TARN_C.x + math.cos(a) * tarn_r(a), 2), round(TARN_C.y + math.sin(a) * tarn_r(a), 2)] for a in [k * math.tau / 24 for k in range(24)]]
    hud["bog"] = [round(BOG_C.x, 2), round(BOG_C.y, 2), BOG_R]
    scene.render.filepath = os.path.join(OUT, shot + ".png")
    if QUALITY != "json":
        bpy.ops.render.render(write_still=True)
    with open(os.path.join(OUT, shot + ".json"), "w") as fh:
        json.dump(hud, fh)
    print("RENDERED", shot)


for s in SHOTS:
    run(s)
