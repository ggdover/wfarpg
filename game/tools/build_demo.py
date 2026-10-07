"""Builds the play demo's assets for the Godot project in game/. Run from this folder with Blender 5.2:

    blender -b --factory-startup -P build_demo.py -- [models] [stumps] [layout] [ground] [--area=name,name]

models  the mockups' low-poly kit (the old trees, rocks, plants and props) and the tree portfolio's trees, built from
        assets/trees/tree_settings.json with two lighter versions each, as .glb files in assets/kit and assets/trees,
        with the leaf cards they use and ambient occlusion baked into them (kit: the kit alone, not the trees)
stumps  every tree's stump, which the game shows in place of a tree in the way, and its bare trunk, which its x-ray
        leaves standing, in assets/trees/stumps.glb
layout  where every tree, rock and plant stands, and an area's other things (walls), in data/areas/<area>.json; and
        its own models (water, stairs, bridges), if it has any, in assets/areas/<area>/extras.glb
ground  the terrain's heights, the mockups' ground shader baked into textures, and the trees' shade on the ground
        (from the layout), in assets/areas/<area>

With no stage named, all four run, in that order; layout and ground for every area in tools/areas (AREAS), or only
for those named with --area. Each area is described by its module there.
"""
import importlib
import json
import math
import os
import random
import shutil
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.dirname(HERE)
ROOT = os.path.dirname(GAME)
MOCKUPS = os.path.join(ROOT, "mockups")
TREES = os.path.join(ROOT, "assets", "trees")
sys.path[:0] = [HERE, MOCKUPS, TREES]
import areas  # noqa: E402  (tools/areas: the demo's areas, one module each)

KIT_DIR = os.path.join(GAME, "assets", "kit")
TREE_DIR = os.path.join(GAME, "assets", "trees")
DATA_DIR = os.path.join(GAME, "data")
# the area the layout and ground stages build (use_area): its module, name, and where its files go
D = None
AREA = None
GROUND_DIR = None
LAYOUT_PATH = None


def use_area(name):
    global D, AREA, GROUND_DIR, LAYOUT_PATH
    D = importlib.import_module("areas." + name)
    AREA = name
    GROUND_DIR = os.path.join(GAME, "assets", "areas", name)
    LAYOUT_PATH = os.path.join(DATA_DIR, "areas", name + ".json")


def extend_ground_more(kit):
    """The other areas' ground layers, on the mockups' ground shader (forest_cam.mat_ground, with act1_shots'
    extend_ground), painted under the paths like the meadow, so they're in the colour the game reads (build_ground):
    moss, a bright, lumpy carpet of it between pines; litter, autumn's fallen leaves; heath, heather; rock, bare
    granite; gravel, a river's banks; sedge, the bog's dry, golden grass; bed, the dark bottom under water."""
    nt = kit["MAT_GROUND"].node_tree
    if nt.nodes.get("MoreLayers"):
        return
    N, L = nt.nodes, nt.links
    lin = kit["lin"]
    pos = N.new("ShaderNodeNewGeometry").outputs["Position"]
    path_in = N["PathIn"]

    def noise(scale, detail=2.0, rough=0.5, off=(0, 0, 0)):
        vm = N.new("ShaderNodeVectorMath")
        vm.operation = "ADD"
        L.new(pos, vm.inputs[0])
        vm.inputs[1].default_value = off
        n = N.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rough
        L.new(vm.outputs[0], n.inputs["Vector"])
        return n.outputs["Fac"]

    def ramp(fac, stops):
        r = N.new("ShaderNodeValToRGB")
        el = r.color_ramp.elements
        el[0].position, el[0].color = stops[0][0], lin(stops[0][1])
        el[1].position, el[1].color = stops[-1][0], lin(stops[-1][1])
        for p_, c_ in stops[1:-1]:
            el.new(p_).color = lin(c_)
        L.new(fac, r.inputs["Fac"])
        return r.outputs["Color"]

    def link(v, sock):
        if hasattr(v, "links") or hasattr(v, "is_output"):
            L.new(v, sock)
        else:
            sock.default_value = v

    def mix(fac, a, b):
        mx = N.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        link(fac, [x for x in mx.inputs if x.name == "Factor" and x.type == "VALUE"][0])
        link(lin(a) if isinstance(a, str) else a, [x for x in mx.inputs if x.name == "A" and x.type == "RGBA"][0])
        link(lin(b) if isinstance(b, str) else b, [x for x in mx.inputs if x.name == "B" and x.type == "RGBA"][0])
        return [x for x in mx.outputs if x.name == "Result" and x.type == "RGBA"][0]

    def math_(op, a, b=0.0):
        mt = N.new("ShaderNodeMath")
        mt.operation = op
        link(a, mt.inputs[0])
        link(b, mt.inputs[1])
        return mt.outputs[0]

    def sstep(v, lo, hi):
        mr = N.new("ShaderNodeMapRange")
        mr.interpolation_type = "SMOOTHSTEP"
        link(v, mr.inputs["Value"])
        mr.inputs["From Min"].default_value = lo
        mr.inputs["From Max"].default_value = hi
        return mr.outputs["Result"]

    def attr(name):
        a = N.new("ShaderNodeAttribute")
        a.attribute_name = name
        a.attribute_type = "GEOMETRY"
        return a.outputs["Fac"]

    def broken(mask, scale, amt, off):  # the mask's edge broken up by noise, as the mockups' layers are
        return sstep(math_("ADD", attr(mask), math_("MULTIPLY", math_("SUBTRACT", noise(scale, 2.0, 0.5, off), 0.5), amt)), 0.42, 0.58)

    col = path_in.inputs["Color"].links[0].from_socket
    moss = ramp(noise(0.9, 3.0, 0.6, (4, 21, 0)), [(0.3, "#4F6E2A"), (0.48, "#6E8F35"), (0.62, "#8BAA42"), (0.78, "#A3BC52")])
    moss = mix(math_("MULTIPLY", sstep(noise(3.2, 2.0, 0.55, (9, 9, 0)), 0.55, 0.7), 0.55), moss, "#3E5A26")  # the dark between cushions
    col = mix(broken("moss", 0.45, 0.45, (21, 4, 0)), col, moss)
    heath = ramp(noise(1.4, 3.0, 0.6, (6, 13, 0)), [(0.3, "#4A4A2E"), (0.5, "#5E4A4A"), (0.68, "#6E5262"), (0.82, "#7A6A4A")])
    col = mix(broken("heath", 0.7, 0.5, (13, 6, 0)), col, heath)
    rock = ramp(noise(1.1, 3.0, 0.55, (2, 31, 0)), [(0.3, "#7D7C76"), (0.55, "#8D8B84"), (0.75, "#9B998F")])
    rock = mix(math_("MULTIPLY", sstep(noise(2.2, 2.0, 0.5, (31, 2, 0)), 0.58, 0.68), 0.7), rock, "#98A189")  # lichen
    col = mix(broken("rock", 0.8, 0.35, (5, 5, 0)), col, rock)
    gravel = ramp(noise(4.0, 2.0, 0.6, (12, 1, 0)), [(0.3, "#7E7466"), (0.55, "#9A8E78"), (0.78, "#B4A68A")])
    col = mix(broken("gravel", 1.0, 0.4, (1, 12, 0)), col, gravel)
    sedge = ramp(noise(1.8, 2.0, 0.6, (14, 7, 0)), [(0.3, "#8A7A44"), (0.5, "#A8914E"), (0.7, "#C2AB5E"), (0.85, "#CDB76A")])
    col = mix(broken("sedge", 0.9, 0.45, (7, 14, 0)), col, sedge)
    litter = ramp(noise(2.6, 3.0, 0.62, (17, 23, 0)), [(0.25, "#5E3A1E"), (0.42, "#8A5428"), (0.56, "#A86A2C"), (0.7, "#BD8A36"), (0.84, "#9A3E22")])
    col = mix(broken("litter", 0.6, 0.3, (23, 17, 0)), col, litter)
    bed = ramp(noise(1.0, 2.0, 0.5, (3, 8, 0)), [(0.3, "#2E3024"), (0.6, "#3A3A2E"), (0.8, "#4A4634")])
    col = mix(sstep(attr("bed"), 0.2, 0.8), col, bed)
    marker = N.new("NodeReroute")
    marker.name = "MoreLayers"
    L.new(col, path_in.inputs["Color"])


def load_kit():
    """The mockups' low-poly kit: forest_cam.py's materials and builders, with act1_shots.py's extra plants and ground
    layers, run the way act1_shots.py runs them, but without rendering any shots."""
    path = os.path.join(MOCKUPS, "act1_shots.py")
    src = open(path).read()
    src = src[:src.index("# ------------------------------------------------------------------ shots")]
    kit = {"__file__": path, "__name__": "kit"}
    exec(compile(src, path, "exec"), kit)
    return kit


def to_godot(p):
    """Blender's axes (Z up) to Godot's (Y up), the way the glTF exporter turns them."""
    return [round(float(p[0]), 3), round(float(p[2]), 3), round(float(-p[1]), 3)]


# ------------------------------------------------------------------ models
def export_glb(objects, path, ao=None):
    """Export the objects as one .glb, each standing on its own origin. Godot keeps vertex colours as 8 bits per
    channel, which bands the dark greens if they are linear, so the colours go out sRGB-encoded in "ColSRGB" and the
    game's shaders decode them. The baked ambient occlusion (ao: object name -> per corner) goes in a second UV map,
    which Godot reads as UV2: Blender's exporter writes real vertex colours for a mesh's first material only, and
    white for the rest, so the leaf cards could not carry it in their colours."""
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objects:
        srgb_colours(ob.data)
        ao_uvs(ob.data, (ao or {}).get(ob.name))
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_yup=True,
                              export_texcoords=True, export_normals=True, export_tangents=False,
                              export_materials="EXPORT", export_image_format="NONE",
                              export_vertex_color="NAME", export_vertex_color_name="ColSRGB", export_all_vertex_colors=False,
                              export_cameras=False, export_lights=False, export_animations=False, export_extras=False)


def ao_uvs(me, ao=None):
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    layer = me.uv_layers.get("AO") or me.uv_layers.new(name="AO")
    uv = np.zeros((len(me.loops), 2), np.float32)
    uv[:, 0] = 1.0 if ao is None else ao
    uv[:, 1] = 1.0  # glTF flips V; Godot reads UV2.y = 0
    layer.data.foreach_set("uv", uv.ravel())


def srgb_colours(me):
    src = me.color_attributes.get("Col")
    if src is None:  # a collider, or water: no colours
        return
    lin = np.zeros(len(src.data) * 4, np.float32)
    src.data.foreach_get("color", lin)
    lin = lin.reshape(-1, 4)
    rgb = np.clip(lin[:, :3], 0, 1)
    lin[:, :3] = np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * np.power(rgb, 1 / 2.4) - 0.055)
    dst = me.color_attributes.get("ColSRGB") or me.color_attributes.new("ColSRGB", "FLOAT_COLOR", src.domain)
    dst.data.foreach_set("color", lin.ravel())


def bake_ao(me, see_through=(), rays=32, reach=2.6, strength=0.95):
    """Ambient occlusion per face corner, by casting rays over the hemisphere round each corner's normal against the
    model itself: how much of the sky a leaf deep in a crown, or a branch under it, cannot see. Eevee darkens the
    insides of crowns this way in the mockups; Godot's ambient light is not blocked by geometry, so the game shades
    with this instead. Faces with a material in see_through (the leaf cards) let half the light through, for the
    holes in their cut-outs."""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    verts = [v.co.copy() for v in me.vertices]
    bvh = BVHTree.FromPolygons(verts, [tuple(p.vertices) for p in me.polygons])
    mats = [p.material_index for p in me.polygons]
    normals = me.corner_normals
    r = random.Random(5)
    dirs = []
    for i in range(rays):  # cosine-weighted, stratified
        u, v = (i + r.random()) / rays, r.random()
        dirs.append(Vector((math.sqrt(u) * math.cos(math.tau * v), math.sqrt(u) * math.sin(math.tau * v), math.sqrt(1 - u))))
    ao = np.ones(len(me.loops), np.float32)
    for poly in me.polygons:
        for li in poly.loop_indices:
            n = normals[li].vector
            q = n.to_track_quat("Z", "Y")
            origin = verts[me.loops[li].vertex_index] + n * 0.02
            occ = 0.0
            for d in dirs:
                w = q @ d
                o, travelled = origin, 0.0
                for _ in range(3):  # pass through the corner's own face
                    hit, _hn, fi, dist = bvh.ray_cast(o, w, reach - travelled)
                    if hit is None or fi != poly.index:
                        break
                    travelled += dist + 0.01
                    o = hit + w * 0.01
                if hit is not None and fi != poly.index:
                    t = (travelled + dist) / reach
                    occ += (0.5 if mats[fi] in see_through else 1.0) * (1 - t * t)
            ao[li] = 1.0 - strength * occ / rays
    return ao


def mesh_info(me, bark_slot=0):
    """Bounds, size and footprint of a mesh, for the layout and the colliders."""
    co = np.zeros(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    lo, hi = co.min(0), co.max(0)
    # the footprint: how far the solid part reaches out near the ground (a trunk, or a rock's flanks)
    solid = co
    if bark_slot is not None and len(me.materials) > 1:
        idx = np.zeros(len(me.polygons), np.int32)
        me.polygons.foreach_get("material_index", idx)
        keep = {v for p, m in zip(me.polygons, idx) if m == bark_slot for v in p.vertices}
        solid = co[sorted(keep)]
    low = solid[(solid[:, 2] > lo[2] + 0.05) & (solid[:, 2] < min(0.6, lo[2] + 0.5 * (hi[2] - lo[2])))]
    foot = float(np.hypot(low[:, 0], low[:, 1]).max()) if len(low) else float(max(hi[0] - lo[0], hi[1] - lo[1]) / 2)
    return {"min": to_godot((lo[0], hi[1], lo[2])), "max": to_godot((hi[0], lo[1], hi[2])), "height": round(float(hi[2]), 3),
            "foot": round(foot, 3), "faces": len(me.polygons)}


def kit_groups(k):
    """The kit's models by .glb file: name -> a function that builds its mesh."""
    k["rng"] = random.Random(7)  # the kit's colour jitter, so every build gives the same models
    return {
        "old_trees": [(f"Pine{s}", lambda s=s: k["pine_mesh"](s)[0]) for s in range(6)]
        + [(f"TallSpruce{s}", lambda s=s: k["tall_spruce_mesh"](150 + s)) for s in range(5)]
        + [(f"Birch{s}", lambda s=s: k["birch_mesh"](170 + s)) for s in range(4)]
        + [(f"YoungSpruce{s}", lambda s=s: k["spruce_mesh"](100 + s)) for s in range(4)],
        "rocks": [(f"Boulder{s}", lambda s=s: k["boulder_mesh"](200 + s)) for s in range(8)]
        + [(f"BigBoulder{s}", lambda s=s: k["boulder_mesh"](300 + s, big=True)) for s in range(4)]
        + [(f"Pebble{s}", lambda s=s: k["boulder_mesh"](950 + s, tones=k["PEBBLE"])) for s in range(3)],
        "plants": [(f"Blueberry{s}", lambda s=s: k["shrub_mesh"](410 + s, "berryblue")) for s in range(3)]
        + [(f"Lingonberry{s}", lambda s=s: k["shrub_mesh"](400 + s, "berryred")) for s in range(3)]
        + [(f"Shrub{s}", lambda s=s: k["shrub_mesh"](420 + s, None)) for s in range(3)]
        + [(f"Lichen{s}", lambda s=s: k["lichen_mesh"](600 + s)) for s in range(3)]
        + [(f"Grass{s}", lambda s=s: k["grass_mesh"](700 + s)) for s in range(4)]
        + [(f"TallGrass{s}", lambda s=s: k["grass_mesh"](720 + s, tall=True)) for s in range(3)],
        "props": [(f"Log{s}", lambda s=s: k["log_mesh"](800 + s, 6.0)) for s in range(2)]
        + [(f"Snag{s}", lambda s=s: k["snag_mesh"](900 + s)) for s in range(3)]
        + [("RuneStone", lambda: k["runestone_mesh"](False)), ("Cairn", lambda: cairn_mesh(k))],
        # for the other areas: heath, rock slabs and moss, ferns, and the water's and the bog's plants
        "nature": [(f"Heather{s}", lambda s=s: k["heather_mesh"](430 + s)) for s in range(3)]
        + [(f"Slab{s}", lambda s=s: slab_mesh(k, 500 + s)) for s in range(4)]
        + [(f"MossMound{s}", lambda s=s: moss_mound_mesh(k, 520 + s)) for s in range(3)]
        + [(f"Fern{s}", lambda s=s: fern_mesh(k, 540 + s)) for s in range(3)]
        + [(f"Reed{s}", lambda s=s: reed_mesh(k, 560 + s)) for s in range(3)]
        + [(f"LilyPad{s}", lambda s=s: lily_pad_mesh(k, 580 + s)) for s in range(3)]
        + [(f"Tussock{s}", lambda s=s: tussock_mesh(k, 600 + s)) for s in range(3)]
        + [(f"Sedge{s}", lambda s=s: sedge_mesh(k, 620 + s)) for s in range(3)]
        + [(f"DryFern{s}", lambda s=s: fern_mesh(k, 640 + s, tones(k, *BRACKEN))) for s in range(3)]
        + [(f"LeafPile{s}", lambda s=s: leaf_pile_mesh(k, 660 + s)) for s in range(3)]
        + [(f"MossBoulder{s}", lambda s=s: moss_boulder_mesh(k, 680 + s)) for s in range(4)]
        + [(f"CliffRock{s}", lambda s=s: cliff_rock_mesh(k, 700 + s)) for s in range(6)]
        + [(f"SteppingStone{s}", lambda s=s: stepping_stone_mesh(k, 720 + s)) for s in range(3)],
    }


# ------------------------------------------------------------------ the other areas' plants and rocks, in the kit's style
AUTUMN = ("#B5762F", "#D39A38", "#8B5A2E", "#A3402A", "#C98A2E", "#7A4A26", "#BFA640")  # fallen leaves
BRACKEN = ("#A0622A", "#B87A34", "#8A5A2A", "#C29044", "#946A30")  # ferns turned in autumn
MOSS = ("#5E7A33", "#6F8B3B", "#4F6B2C", "#7E9A46", "#56722F")  # thick, damp moss on rocks


def tones(k, *hexes):
    """Faces in these colours, jittered like the kit's (its pick takes names from its palette instead)."""
    cols = [k["lin"](h) for h in hexes]
    return lambda f: k["jitter"](k["rng"].choice(cols))


def repaint(me, colour):
    """Paint a built mesh's faces anew: colour(polygon) gives each its colour."""
    col = me.color_attributes["Col"]
    for poly in me.polygons:
        c = colour(poly)
        for li in poly.loop_indices:
            col.data[li].color = c


def slab_mesh(k, seed):
    """A granite slab, a bare rock outcrop worn flat by the ice: a big boulder, pressed low and wide."""
    me = k["boulder_mesh"](seed, big=True)
    for v in me.vertices:
        v.co.x *= 1.7
        v.co.y *= 1.5
        v.co.z = v.co.z * 0.28 - 0.05
    me.update()
    me.name = "Slab%d" % seed
    return me


def moss_mound_mesh(k, seed):
    """Moss cushions, as on the forest floor between the pines: a cluster of small, dark lumps."""
    r = random.Random(seed)
    b = k["Builder"]()
    for _ in range(r.randint(6, 10)):
        c = (r.uniform(-0.45, 0.45), r.uniform(-0.45, 0.45), -0.04)
        b.ico(c, r.uniform(0.14, 0.3), tones(k, *MOSS), sub=1, scale=(1, 1, 0.7), displace=0.04)
    return b.mesh("MossMound%d" % seed)


def leaf_pile_mesh(k, seed):
    """Fallen leaves heaped up a little: a few low lumps in autumn's colours."""
    r = random.Random(seed)
    b = k["Builder"]()
    for _ in range(r.randint(4, 7)):
        c = (r.uniform(-0.6, 0.6), r.uniform(-0.6, 0.6), -0.06)
        b.ico(c, r.uniform(0.3, 0.55), tones(k, *AUTUMN), sub=1, scale=(1, 1, 0.28), displace=0.05)
    return b.mesh("LeafPile%d" % seed)


def moss_boulder_mesh(k, seed):
    """A boulder grown over with thick moss, all but its lower flanks, as in a damp ravine."""
    r = random.Random(seed)
    me = k["boulder_mesh"](seed)
    moss, stone = tones(k, *MOSS), k["pick"]("granite1", "granite2", "granite4")
    repaint(me, lambda poly: moss(poly) if poly.normal.z > r.uniform(-0.35, 0.1) else stone(poly))
    me.name = "MossBoulder%d" % seed
    return me


def stepping_stone_mesh(k, seed):
    """A stepping stone: a block of granite with a flat, worn top at its origin, reaching 0.7 m down into the water."""
    import bmesh
    from mathutils import Vector
    r = random.Random(seed)
    b = k["Builder"]()
    rx, ry = r.uniform(0.42, 0.55), r.uniform(0.34, 0.45)
    pts = []
    for i in range(7):  # the top's rim, and the flanks below it, widening
        a = i / 7 * math.tau + r.uniform(-0.2, 0.2)
        pts.append(Vector((math.cos(a) * rx * r.uniform(0.85, 1.0), math.sin(a) * ry * r.uniform(0.85, 1.0), r.uniform(-0.02, 0.0))))
        pts.append(Vector((math.cos(a) * rx * 1.25, math.sin(a) * ry * 1.25, -r.uniform(0.12, 0.2))))
        pts.append(Vector((math.cos(a) * rx * 1.3, math.sin(a) * ry * 1.3, -0.7)))
    verts = [b.bm.verts.new(p) for p in pts]
    bmesh.ops.convex_hull(b.bm, input=verts)
    loose = [v for v in b.bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(b.bm, geom=loose, context="VERTS")
    bmesh.ops.dissolve_limit(b.bm, angle_limit=math.radians(8), verts=b.bm.verts[:], edges=b.bm.edges[:], delimit=set())
    bmesh.ops.recalc_face_normals(b.bm, faces=b.bm.faces[:])
    b.bm.normal_update()
    stone, lichen = k["pick"]("granite1", "granite2", "granite3"), k["pick"]("lichen", "lichen2")
    b.paint(b.bm.faces[:], lambda f: lichen(f) if f.normal.z > 0.9 and r.random() < 0.3 else stone(f))
    return b.mesh("SteppingStone%d" % seed)


def cliff_rock_mesh(k, seed):
    """A block of a low cliff's face: a tall, angular rock, its face (towards -Y) steep, leaning back a little and
    broken into facets, moss on its top and ledges. Its origin is at the foot of its face, and it reaches back (+Y)
    into the slope behind; 4.6 m high, about 3-4 wide."""
    import bmesh
    from mathutils import Vector
    r = random.Random(seed)
    b = k["Builder"]()
    w, h = r.uniform(3.0, 3.9), 4.6
    pts = []
    for _ in range(r.randint(10, 14)):  # the face
        z = r.uniform(-0.6, h - 0.2)
        pts.append(Vector((r.uniform(-w / 2, w / 2), -0.35 + 0.3 * z / h + r.uniform(-0.25, 0.15), z)))
    for _ in range(r.randint(5, 8)):  # the top, sloping back into the ground behind
        pts.append(Vector((r.uniform(-w / 2, w / 2) * 0.9, r.uniform(0.0, 2.2), h - r.uniform(0.0, 0.5) - 0.25 * r.random())))
    for sx in (-1, 1):  # the sides and the back, buried
        for z in (-0.6, h * 0.5):
            pts.append(Vector((sx * w / 2 * r.uniform(0.85, 1.0), r.uniform(0.3, 1.8), z)))
        pts.append(Vector((sx * w / 2 * 0.8, 2.4, -0.6)))
    verts = [b.bm.verts.new(p) for p in pts]
    bmesh.ops.convex_hull(b.bm, input=verts)
    loose = [v for v in b.bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(b.bm, geom=loose, context="VERTS")
    bmesh.ops.dissolve_limit(b.bm, angle_limit=math.radians(r.uniform(9, 14)), verts=b.bm.verts[:], edges=b.bm.edges[:], delimit=set())
    bmesh.ops.recalc_face_normals(b.bm, faces=b.bm.faces[:])
    b.bm.normal_update()
    moss, stone = tones(k, *MOSS), k["pick"]("granite1", "granite2", "granite3", "granite4")
    lichen = k["pick"]("lichen", "lichen2")

    def col(f):
        if f.normal.z > 0.55 or (f.normal.z > 0.25 and r.random() < 0.5):
            return moss(f)
        return lichen(f) if r.random() < 0.12 else stone(f)

    b.paint(b.bm.faces[:], col)
    return b.mesh("CliffRock%d" % seed)


def blade(b, k, pts, widths, colours, both_sides=True):
    """A flat, tapering blade along pts (a leaf, a frond), its tip a point; with both_sides, faced both ways."""
    from mathutils import Vector
    pts = [Vector(p) for p in pts]
    faces = []
    rows = []
    for i, (p, w) in enumerate(zip(pts, widths)):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        side = Vector((-t.y, t.x, 0.0)).normalized() if abs(t.z) < 0.99 else Vector((1, 0, 0))
        rows.append([b.bm.verts.new(p)] if w <= 0 else [b.bm.verts.new(p - side * w), b.bm.verts.new(p + side * w)])
    for a, c in zip(rows, rows[1:]):
        quad = (a[0], a[1], c[1], c[0]) if len(c) == 2 else (a[0], a[1], c[0])
        faces.append(b.bm.faces.new(quad))
        if both_sides:
            back = [b.bm.verts.new(v.co) for v in quad]
            faces.append(b.bm.faces.new(list(reversed(back))))
    b.paint(faces, colours if callable(colours) else k["pick"](*colours))
    return faces


def fern_mesh(k, seed, colours=("leaf1", "leaf2", "birchleaf3")):
    """A fern: fronds rising from the middle and arching out (in autumn, bracken: colours)."""
    r = random.Random(seed)
    b = k["Builder"]()
    n = r.randint(7, 10)
    for i in range(n):
        a = i / n * math.tau + r.uniform(-0.25, 0.25)
        length = r.uniform(0.55, 0.85)
        lift = r.uniform(0.45, 0.7)
        pts = []
        for j in range(5):
            t = j / 4
            z = lift * length * math.sin(t * math.pi * 0.8) * (1.0 - 0.35 * t)
            pts.append((math.cos(a) * length * t, math.sin(a) * length * t, z))
        blade(b, k, pts, [0.02, 0.085, 0.095, 0.06, 0.0], colours)
    return b.mesh("Fern%d" % seed)


def reed_mesh(k, seed):
    """Reeds at the water's edge: tall, thin blades, and a cattail's brown head or two."""
    r = random.Random(seed)
    b = k["Builder"]()
    for _ in range(r.randint(9, 14)):
        c = (r.uniform(-0.25, 0.25), r.uniform(-0.25, 0.25), 0.0)
        h = r.uniform(1.1, 1.9)
        tip = (c[0] + r.uniform(-0.25, 0.25), c[1] + r.uniform(-0.25, 0.25), h)
        b.limb(c, tip, 0.025, 0.0, k["pick"]("grass1", "grass3", "birchleaf3", "crop2"), segs=3)
    for _ in range(r.randint(1, 3)):
        x, y = r.uniform(-0.15, 0.15), r.uniform(-0.15, 0.15)
        h = r.uniform(1.3, 1.8)
        b.limb((x, y, 0.0), (x, y, h), 0.012, 0.01, k["pick"]("grass3"), segs=3)
        b.ico((x, y, h - 0.12), 0.05, k["pick"]("wood2", "barklow"), sub=1, scale=(1, 1, 3.2))
    return b.mesh("Reed%d" % seed)


def lily_pad_mesh(k, seed):
    """Water lilies: a few round leaves on the water, each with its notch, and now and then a white flower."""
    r = random.Random(seed)
    b = k["Builder"]()
    for _ in range(r.randint(2, 4)):
        cx, cy = r.uniform(-0.5, 0.5), r.uniform(-0.5, 0.5)
        rad = r.uniform(0.14, 0.26)
        notch = r.uniform(0, math.tau)
        rim = []
        for j in range(11):
            a = notch + 0.35 + j / 10 * (math.tau - 0.7)
            rim.append(b.bm.verts.new((cx + math.cos(a) * rad, cy + math.sin(a) * rad, 0.0)))
        mid = b.bm.verts.new((cx, cy, 0.01))
        faces = [b.bm.faces.new((mid, rim[j], rim[j + 1])) for j in range(10)]
        b.paint(faces, k["pick"]("leaf1", "leaf2", "rmoss3"))
        if r.random() < 0.35:
            b.ico((cx + r.uniform(-0.05, 0.05), cy + r.uniform(-0.05, 0.05), 0.04), 0.06, (lambda f: k["P"]["white"]), sub=1, scale=(1, 1, 0.6))
    return b.mesh("LilyPad%d" % seed)


def tussock_mesh(k, seed):
    """A bog tussock: a mound of dry, golden sedge."""
    r = random.Random(seed)
    b = k["Builder"]()
    w = r.uniform(0.45, 0.65)
    b.ico((0, 0, 0.05), w, k["pick"]("hay", "crop2", "bog4"), sub=1, scale=(1, 1, 0.55), displace=0.05)
    for _ in range(r.randint(14, 20)):
        a = r.uniform(0, math.tau)
        d = r.uniform(0, w * 0.8)
        c = (math.cos(a) * d, math.sin(a) * d, 0.2)
        h = r.uniform(0.35, 0.7)
        tip = (c[0] + math.cos(a) * r.uniform(0.1, 0.35), c[1] + math.sin(a) * r.uniform(0.1, 0.35), 0.2 + h)
        b.limb(c, tip, 0.035, 0.0, k["pick"]("hay", "hay2", "crop", "grass2"), segs=3)
    return b.mesh("Tussock%d" % seed)


def sedge_mesh(k, seed):
    """A tuft of the bog's pale, dry grass."""
    r = random.Random(seed)
    b = k["Builder"]()
    for _ in range(r.randint(7, 11)):
        c = (r.uniform(-0.2, 0.2), r.uniform(-0.2, 0.2), 0.0)
        h = r.uniform(0.4, 0.75)
        b.limb(c, (c[0] + r.uniform(-0.2, 0.2), c[1] + r.uniform(-0.2, 0.2), h), 0.035, 0.0, k["pick"]("hay", "hay2", "crop2", "grass2"), segs=3)
    return b.mesh("Sedge%d" % seed)


def build_models(trees=True):
    kit = load_kit()
    os.makedirs(KIT_DIR, exist_ok=True)
    os.makedirs(TREE_DIR, exist_ok=True)
    info = {}
    for group, items in kit_groups(kit).items():
        objs, ao = [], {}
        for name, make in items:
            me = make()
            me.name = name
            ob = bpy.data.objects.new(name, me)
            bpy.context.scene.collection.objects.link(ob)
            objs.append(ob)
            info[name] = dict(mesh_info(me, bark_slot=None), file=f"res://assets/kit/{group}.glb")
            if group == "old_trees":
                ao[name] = bake_ao(me)
        export_glb(objs, os.path.join(KIT_DIR, group + ".glb"), ao)
        for ob in objs:
            bpy.data.objects.remove(ob)
    with open(os.path.join(KIT_DIR, "kit.json"), "w") as fh:
        json.dump(info, fh, indent=1, sort_keys=True)
    print("kit:", len(info), "models")
    if trees:
        build_trees()


def cairn_mesh(kit):
    ob = kit["cairn"]((0.0, 0.0), 0.0)
    me = ob.data
    bpy.data.objects.remove(ob)
    return me


# lighter versions of the portfolio's trees, for distance: fewer, bigger leaf cards, and only the trunk of the bark at
# the furthest level (the branches hide in the crown that far off), and already at the middle one for the spruce
LODS = {1: dict(clumps=0.5, card=1.25, planes=-2, spacing=1.45, spray=1.25, sprays=3),
        2: dict(clumps=0.0, card=1.7, planes=-4, spacing=2.1, spray=1.8, sprays=2)}


def lod_settings(cfg, level):
    """Every clump stays (so the crown keeps its shape) with fewer, bigger cards in it; sprays sit further apart."""
    lod, c = LODS[level], dict(cfg)
    if c["layout"] == "pinnate":
        c["spacing"] = cfg["spacing"] * lod["spacing"]
        c["size"] = cfg["size"] * lod["spray"]
        c["planes"] = min(int(cfg["planes"]), lod["sprays"])
    else:
        c["density"] = max(1.0, cfg["density"] * lod["clumps"])
        c["size"] = cfg["size"] * lod["card"] * (1.0 + 0.25 * max(0.0, cfg["density"] - c["density"]) / max(cfg["density"], 1.0))
        c["planes"] = max(2 if level == 2 else 3, int(cfg["planes"]) + lod["planes"])
    return c


# lighter spruces, for the performance panel's "Spruce leaves", as the spruce costs more to draw than every other tree
# together: two copies of each spray instead of the tuned four, and with "lighter" (2) the sprays further apart along
# the branches too
LIGHT = {1: dict(planes=2, spacing=1.0), 2: dict(planes=2, spacing=1.5)}


def light_settings(cfg, light):
    c = dict(cfg)
    c["planes"] = min(int(cfg["planes"]), LIGHT[light]["planes"])
    c["spacing"] = cfg["spacing"] * LIGHT[light]["spacing"]
    return c


# for trying out in the demo's performance panel: about half the leaf cards per clump, a little bigger
def fewer_settings(cfg):
    c = dict(cfg)
    if c["layout"] == "pinnate":
        c["planes"] = max(1, int(cfg["planes"]) // 2)
        c["size"] = cfg["size"] * 1.08
    else:
        c["planes"] = max(2, round(int(cfg["planes"]) * 0.6))
        c["density"] = max(1.0, cfg["density"] * 0.75)
        c["size"] = cfg["size"] * 1.12
    return c


def clip_polygon(poly, d, limit):
    """The part of a convex polygon where dot(d, p) <= limit (Sutherland-Hodgman)."""
    out = []
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        da = d[0] * a[0] + d[1] * a[1] - limit
        db = d[0] * b[0] + d[1] * b[1] - limit
        if da <= 0:
            out.append(a)
        if (da < 0) != (db < 0):
            t = da / (da - db)
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def card_outline(path, margin_px=6.0, cut=0.02):
    """The octagon round a leaf card's leaves, in its UV space: the square cut at 45 degrees too, with a few pixels
    to spare so filtering and mipmaps never reach past it. Drawing only this part of each card saves pixels: most of
    a card is transparent, and the graphics card works through every pixel of it anyway."""
    img = bpy.data.images.load(path, check_existing=True)
    W, H = img.size
    a = np.array(img.pixels[:], np.float32).reshape(H, W, 4)[..., 3]
    ys, xs = np.nonzero(a > cut)
    u, v = (xs + 0.5) / W, (ys + 0.5) / H
    m = margin_px / W
    poly = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    for k in range(4):
        ang = math.pi * k / 4
        d = (math.cos(ang), math.sin(ang))
        proj = u * d[0] + v * d[1]
        poly = clip_polygon(poly, d, float(proj.max()) + m)
        poly = clip_polygon(poly, (-d[0], -d[1]), -(float(proj.min()) - m))
    return [(max(0.0, min(1.0, x)), max(0.0, min(1.0, y))) for x, y in poly]


def trim_cards(tree, outlines):
    """Cut every leaf card of a treegen.Tree from its square down to the outline round its card's leaves (outlines:
    material slot name -> UV polygon), keeping its UVs, its normals (interpolated) and its winding."""
    nv, nf, nmat, ncol, nuv, nnrm = [], [], [], [], [], []
    remap = {}

    def keep(i):
        if i not in remap:
            remap[i] = len(nv)
            nv.append(tree.v[i])
        return remap[i]

    for i, face in enumerate(tree.f):
        m, uvs = tree.mat[i], tree.uv[i]
        outline = outlines.get(tree.slots[m]) if m > 0 else None
        if outline is None or uvs is None or len(face) != 4:
            nf.append(tuple(keep(j) for j in face))
            nmat.append(m), ncol.append(tree.col[i]), nuv.append(uvs), nnrm.append(tree.nrm[i])
            continue
        at = {(round(u), round(v)): k for k, (u, v) in enumerate(uvs)}
        p00, p10, p01 = (tree.v[face[at[c]]] for c in ((0, 0), (1, 0), (0, 1)))
        n = {c: tree.nrm[i][k] for c, k in at.items()} if tree.nrm[i] else None
        poly = outline
        if sum(uvs[k][0] * uvs[(k + 1) % 4][1] - uvs[(k + 1) % 4][0] * uvs[k][1] for k in range(4)) < 0:
            poly = list(reversed(poly))  # a mirrored card winds the other way round
        idx, puv, pn = [], [], []
        for u, v in poly:
            nv.append(p00 + (p10 - p00) * u + (p01 - p00) * v)
            idx.append(len(nv) - 1)
            puv.append((u, v))
            if n:
                pn.append((n[(0, 0)] * ((1 - u) * (1 - v)) + n[(1, 0)] * (u * (1 - v)) + n[(1, 1)] * (u * v) + n[(0, 1)] * ((1 - u) * v)).normalized())
        nf.append(tuple(idx))
        nmat.append(m), ncol.append(tree.col[i]), nuv.append(puv), nnrm.append(pn or None)
    tree.v, tree.f, tree.mat, tree.col, tree.uv, tree.nrm = nv, nf, nmat, ncol, nuv, nnrm


def build_tree(key, variant, cfg, me, level=0, outlines=None, fewer=False, light=0):
    """treegen.build_into, at a level of detail, optionally with fewer cards per clump or lighter spruce leaves, and with
    the cards trimmed to their leaves (outlines from card_outline, by material slot). Returns (leaf cards, faces)."""
    import treegen
    if fewer:
        cfg = fewer_settings(cfg)
    if level:
        cfg = lod_settings(cfg, level)
    if light:
        cfg = light_settings(cfg, light)
    marks = []
    orig = treegen.Tree.tube

    def tube(self, *a, **kw):  # remember where the trunk's faces end: it is each tree's first tube
        orig(self, *a, **kw)
        marks.append(len(self.f))
    treegen.Tree.tube = tube
    try:
        tree, crown = treegen.BY_KEY[key][1](treegen.seed_for(key, variant, cfg), cfg)
    finally:
        treegen.Tree.tube = orig
    tree.emit_leaves(crown, cfg, key)
    if level == 2 or (level == 1 and cfg["layout"] == "pinnate"):
        keep = [i for i in range(len(tree.f)) if tree.mat[i] > 0 or i < marks[0]]
        for attr in ("f", "mat", "col", "uv", "nrm"):
            setattr(tree, attr, [getattr(tree, attr)[i] for i in keep])
    if outlines:
        trim_cards(tree, outlines)
    tree.to_mesh(me, treegen.materials_for(key, cfg))
    return sum(1 for m in tree.mat if m > 0), len(tree.f)


def tree_meshes():
    """The tree portfolio's trees, as tuned in assets/trees/tree_settings.json: name -> mesh."""
    import treegen
    settings = treegen.load_settings()
    out = {}
    for key, *_ in treegen.SPECIES:
        for variant in "AB":
            me = bpy.data.meshes.new(f"{key}_{variant}")
            treegen.build_into(key, variant, settings[key], me)
            out[me.name] = me
    return out


# the trees' versions, by .glb file: (name suffix, level of detail, trimmed cards, fewer cards, lighter spruce leaves,
# which only the spruce has: LIGHT). In the game, the performance panel switches between them (scripts/world.gd).
TREE_VERSIONS = {
    "trees": [("", 0, False, False, 0), ("_1", 1, False, False, 0), ("_2", 2, False, False, 0)],
    "trees_trim": [("_t", 0, True, False, 0), ("_1_t", 1, True, False, 0), ("_2_t", 2, True, False, 0)],
    "trees_few": [("_f", 0, False, True, 0), ("_f_t", 0, True, True, 0)],
    "trees_light": [("_l", 0, False, False, 1), ("_l_t", 0, True, False, 1), ("_1_l", 1, False, False, 1), ("_1_l_t", 1, True, False, 1),
                    ("_ll", 0, False, False, 2), ("_ll_t", 0, True, False, 2), ("_1_ll", 1, False, False, 2), ("_1_ll_t", 1, True, False, 2)],
}


def transfer_ao(me_square, ao_square, me_trimmed):
    """Ambient occlusion for a tree with trimmed cards, from the same tree with square ones (bake_ao counts a whole
    square as half see-through, so baking the trimmed cards would come out lighter): the bark keeps its values, and
    each trimmed card takes its square's corners' values, interpolated by UV."""
    uv_sq = me_square.uv_layers["UVMap"].data
    uv_t = me_trimmed.uv_layers["UVMap"].data
    out = np.ones(len(me_trimmed.loops), np.float32)
    for fs, ft in zip(me_square.polygons, me_trimmed.polygons):
        ls, lt = list(fs.loop_indices), list(ft.loop_indices)
        if fs.material_index == 0:
            out[lt] = ao_square[ls]
            continue
        c = {(round(uv_sq[l].uv[0]), round(uv_sq[l].uv[1])): ao_square[l] for l in ls}
        for l in lt:
            u, v = uv_t[l].uv
            out[l] = c[(0, 0)] * (1 - u) * (1 - v) + c[(1, 0)] * u * (1 - v) + c[(1, 1)] * u * v + c[(0, 1)] * (1 - u) * v
    return out


def build_trees():
    """The tree portfolio's trees, as tuned in assets/trees/tree_settings.json, two variants of each, each in a full
    and two lighter versions, and each of those with square or trimmed leaf cards; and for trying out, the full
    trees with fewer cards per clump, and the spruce's full and first lighter versions with lighter leaves."""
    import treegen
    settings = treegen.load_settings()
    tex_dir = os.path.join(TREE_DIR, "textures")
    os.makedirs(tex_dir, exist_ok=True)
    info = {}
    files = {group: ([], {}) for group in TREE_VERSIONS}
    for key, *_ in treegen.SPECIES:
        cfg = settings[key]
        card = treegen.BY_KEY[key][6]
        textures = {"leaves": f"{card}_{int(cfg['card'])}"}
        if key == "Rowan":
            textures["berries"] = f"{card}_{int(cfg['card'])}_berries"
        for name in textures.values():
            copy_card(name, cfg, tex_dir)
        outlines = {slot: card_outline(os.path.join(tex_dir, t + ".png")) for slot, t in textures.items()}
        for variant in "AB":
            square = {}  # (level, fewer, light) -> (mesh, ao) of the square-card version, for its trimmed twin
            for group, versions in TREE_VERSIONS.items():
                objs, ao = files[group]
                for suffix, level, trimmed, fewer, light in versions:
                    if light and cfg["layout"] != "pinnate":
                        continue
                    name = f"{key}_{variant}{suffix}"
                    me = bpy.data.meshes.new(name)
                    cards, faces = build_tree(key, variant, cfg, me, level, outlines if trimmed else None, fewer, light)
                    ob = bpy.data.objects.new(name, me)
                    bpy.context.scene.collection.objects.link(ob)
                    objs.append(ob)
                    info[name] = dict(mesh_info(me, bark_slot=0), cards=cards, faces=faces, species=key,
                                      file=f"res://assets/trees/{group}.glb", triangles=sum(len(f.vertices) - 2 for f in me.polygons),
                                      textures={slot: f"res://assets/trees/textures/{t}.png" for slot, t in textures.items()},
                                      materials=[m.name for m in me.materials], thinnable=level == 0 and not fewer)
                    if trimmed:
                        sq_me, sq_ao = square.get((level, fewer, light)) or (None, None)
                        if sq_me is None:  # the square version of the fewer-card tree is built just for this
                            sq_me = bpy.data.meshes.new(name + "_square")
                            build_tree(key, variant, cfg, sq_me, level, None, fewer, light)
                            sq_ao = bake_ao(sq_me, see_through={i for i, m in enumerate(sq_me.materials) if m.name != "Bark"})
                        ao[name] = transfer_ao(sq_me, sq_ao, me)
                    else:
                        ao[name] = bake_ao(me, see_through={i for i, m in enumerate(me.materials) if m.name != "Bark"})
                        square[(level, fewer, light)] = (me, ao[name])
                    print(name, "cards", cards, "triangles", info[name]["triangles"], "mean ao %.2f" % ao[name].mean())
    for group, (objs, ao) in files.items():
        export_glb(objs, os.path.join(TREE_DIR, group + ".glb"), ao)
    with open(os.path.join(TREE_DIR, "trees.json"), "w") as fh:
        json.dump(info, fh, indent=1, sort_keys=True)


def copy_card(name, cfg, tex_dir):
    """Copy a leaf card for the game, with the editor's tint baked in (Blender's hue/saturation/value node)."""
    src = os.path.join(TREES, "textures", name + ".png")
    dst = os.path.join(tex_dir, name + ".png")
    if (cfg["hue"], cfg["saturation"], cfg["brightness"]) == (0.5, 1.0, 1.0):
        shutil.copyfile(src, dst)
        return
    img = bpy.data.images.load(src)
    px = np.array(img.pixels[:], np.float32).reshape(-1, 4)
    rgb = px[:, :3]
    mx, mn = rgb.max(1), rgb.min(1)
    d = mx - mn
    h = np.zeros_like(mx)
    nz = d > 1e-6
    r, g, b = rgb[:, 0], rgb[:, 1], rgb[:, 2]
    hr = np.where(mx == r, ((g - b) / np.where(nz, d, 1)) % 6, np.where(mx == g, (b - r) / np.where(nz, d, 1) + 2, (r - g) / np.where(nz, d, 1) + 4))
    h = np.where(nz, hr / 6.0, 0.0)
    s = np.where(mx > 1e-6, d / np.where(mx > 1e-6, mx, 1), 0.0)
    h = (h + cfg["hue"] - 0.5) % 1.0
    s = np.clip(s * cfg["saturation"], 0, 1)
    v = mx * cfg["brightness"]
    i = np.floor(h * 6).astype(int) % 6
    f = h * 6 - np.floor(h * 6)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    out = np.stack([np.choose(i, [v, q, p, p, t, v]), np.choose(i, [t, v, v, q, p, p]), np.choose(i, [p, p, t, v, v, q])], 1)
    px[:, :3] = out
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = dst
    img.file_format = "PNG"
    img.save()


# ------------------------------------------------------------------ stumps
STUMP_WOOD = "#C9A676"  # the cut: pale, a little weathered wood
STUMP_RING = "#94704C"  # round it, the sapwood under the bark
STUMP_PROUD = 0.015  # how far a stump's sides stand out from its tree's trunk (m)


def hex_linear(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c) + (1.0,)


def trunk_bmesh(src):
    """The tree's trunk alone, as a bmesh: the part of the bark that reaches lowest, as each part (trunk, branch, leaf
    clump) is its own piece of mesh."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(src)
    low = min((v for f in bm.faces if f.material_index == 0 for v in f.verts), key=lambda v: v.co.z)
    trunk, stack, seen = set(), [low], {low}
    while stack:
        for f in stack.pop().link_faces:
            if f not in trunk:
                trunk.add(f)
                for w in f.verts:
                    if w not in seen:
                        seen.add(w)
                        stack.append(w)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f not in trunk], context="FACES")
    return bm


def finish_part(bm, name, src):
    """A mesh from the bmesh, flat-shaded in the tree's bark."""
    for f in bm.faces:
        f.smooth = False
        f.material_index = 0
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if me.has_custom_normals:
        me.normals_split_custom_set([(0.0, 0.0, 0.0)] * len(me.loops))  # the faces' own, flat normals
    bark = src.materials[0]
    me.materials.clear()
    me.materials.append(bark)
    return me


def trunk_mesh(src, name):
    """The tree's trunk alone, without its branches, which the game's x-ray leaves standing (scripts/world.gd). Its
    sides stand STUMP_PROUD out from the tree's own trunk, so that the two don't fight where both show."""
    bm = trunk_bmesh(src)
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * STUMP_PROUD
    return finish_part(bm, name, src)


def stump_mesh(src, name, seed):
    """A tree cut down to its stump, which the game shows in place of a tree that's in the way: the tree's own trunk,
    cut at about knee height (higher for a thick trunk; on a sapling, low on its short trunk), the cut tilted a little
    and capped with pale wood in a ring of sapwood. Its sides stand STUMP_PROUD out from the tree's trunk, so that the
    two don't fight while the tree fades out round it. Returns (mesh, cut height, trunk radius)."""
    import bmesh
    from mathutils import Vector
    rng = random.Random(seed)
    bm = trunk_bmesh(src)
    top = max(v.co.z for v in bm.verts)
    near = [v.co.copy() for v in bm.verts if v.co.z <= 0.5] or [v.co.copy() for v in bm.verts]
    cx = sum(c.x for c in near) / len(near)
    cy = sum(c.y for c in near) / len(near)
    radius = max(math.hypot(c.x - cx, c.y - cy) for c in near)
    cut = min(0.4 + 0.8 * radius + rng.uniform(-0.05, 0.05), 0.6 * top)
    tilt, turn = math.radians(rng.uniform(6.0, 14.0)), rng.uniform(0.0, math.tau)
    normal = Vector((math.sin(tilt) * math.cos(turn), math.sin(tilt) * math.sin(turn), math.cos(tilt)))
    res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=Vector((cx, cy, cut)),
                                 plane_no=normal, clear_outer=True)
    edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    cap = bmesh.ops.contextual_create(bm, geom=edges)["faces"]
    for f in cap:
        if f.normal.dot(normal) < 0:
            f.normal_flip()
    ring = bmesh.ops.inset_region(bm, faces=cap, thickness=0.22 * radius, depth=0.0, use_even_offset=True)["faces"]
    col = bm.loops.layers.float_color.get("Col")
    for faces, colour in ((cap, STUMP_WOOD), (ring, STUMP_RING)):
        for f in faces:
            for loop in f.loops:
                loop[col] = hex_linear(colour)
    grow = 1.0 + STUMP_PROUD / max(radius, 0.02)
    for v in bm.verts:
        v.co.x = cx + (v.co.x - cx) * grow
        v.co.y = cy + (v.co.y - cy) * grow
    return finish_part(bm, name, src), cut, radius


def build_stumps():
    """A stump and a bare trunk for every tree model, old and new (stump_mesh, trunk_mesh), in assets/trees/stumps.glb,
    listed in stumps.json."""
    kit = load_kit()
    meshes = {name: make() for items in kit_groups(kit).values() for name, make in items
              if name.startswith(("Pine", "TallSpruce", "Birch", "YoungSpruce"))}
    meshes.update(tree_meshes())
    objs, ao, info = [], {}, {}
    for i, (model, src) in enumerate(sorted(meshes.items())):
        name = model + "_stump"
        me, cut, radius = stump_mesh(src, name, 1000 + i)
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        objs.append(ob)
        ao[name] = bake_ao(me)
        info[name] = dict(mesh_info(me, bark_slot=None), file="res://assets/trees/stumps.glb", tree=model, cut=round(cut, 3))
        print(name, "cut at %.2f m, trunk %.2f m across, %d faces" % (cut, 2 * radius, len(me.polygons)))
        name = model + "_trunk"
        me = trunk_mesh(src, name)
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        objs.append(ob)
        ao[name] = bake_ao(me)
        info[name] = dict(mesh_info(me, bark_slot=None), file="res://assets/trees/stumps.glb", tree=model)
    export_glb(objs, os.path.join(TREE_DIR, "stumps.glb"), ao)
    with open(os.path.join(TREE_DIR, "stumps.json"), "w") as fh:
        json.dump(info, fh, indent=1, sort_keys=True)


# ------------------------------------------------------------------ layout
# The mockups had pines, spruces and birches only, so the old trees stand in for the other species with birches.
OLD_TREES = {"ScotsPine": ("Pine", 6), "NorwaySpruce": ("TallSpruce", 5), "SilverBirch": ("Birch", 4),
             "Aspen": ("Birch", 4), "Rowan": ("Birch", 4), "Alder": ("Birch", 4)}
# how far each kind of thing sinks into the ground, as in the mockups (act1_shots.populate_act)
SINK = {"tree": 0.15, "sapling": 0.05, "Boulder": 0.25, "BigBoulder": 0.5, "Log": 0.1, "Snag": 0.0, "Pebble": 0.03,
        "plant": 0.03, "RuneStone": 0.1, "Cairn": 0.0}


def load_info():
    info = {}
    for path in (os.path.join(KIT_DIR, "kit.json"), os.path.join(TREE_DIR, "trees.json")):
        with open(path) as fh:
            info.update(json.load(fh))
    return info


def jittered(rng, box, cell):
    x0, x1, y0, y1 = box
    X, Y = np.meshgrid(np.arange(x0, x1, cell), np.arange(y0, y1, cell))
    return (X + rng.uniform(0, cell, X.shape)).ravel(), (Y + rng.uniform(0, cell, Y.shape)).ravel()


class Layout:
    """What an area scatters: its trees, props and solids, and anything else it hands the game (extras: water,
    models of its own; see tools/areas). An area's populate(layout) fills it, with the helpers below; an area without
    one gets populate_default. clear holds (position, radius) spots that nothing is scattered on."""

    def __init__(self, info, rng):
        self.info, self.rng = info, rng
        self.trees, self.props, self.solids, self.clear = [], {}, [], []
        self.extras = {}

    def ground(self, x, y):
        return float(D.height(np.array([x]), np.array([y]))[0])

    def blocked(self, x, y, pad=0.0):
        return any(math.hypot(x - c[0], y - c[1]) < r + pad for c, r in self.clear)

    def add_prop(self, model, x, y, rot, s, sink=None, solid=None, z=None):
        """A prop standing on the ground (or at height z), sunk into it as SINK says, solid out to solid x s."""
        sink = SINK.get(model.rstrip("0123456789"), SINK["plant"]) if sink is None else sink
        z = (self.ground(x, y) if z is None else z) - sink * s
        self.props.setdefault(model, []).append(to_godot((x, y, z)) + [round(float(rot), 3), round(float(s), 3)])
        if solid:
            self.solids.append(to_godot((x, y, z)) + [round(solid * s, 2), round(self.info[model]["height"] * s, 2)])

    def add_solid(self, x, y, radius, height, z=None):
        """Something the hero can't walk through: a cylinder standing on the ground (or at height z)."""
        z = self.ground(x, y) if z is None else z
        self.solids.append(to_godot((x, y, z)) + [round(float(radius), 2), round(float(height), 2)])

    def add_tree(self, kind, x, y, s, rot, ring, sapling=False, tint=None):
        """A tree: the old model and the new one on the same spot. tint, 0..1, turns its leaves to autumn: 0 yellow,
        0.5 orange, 1 red (shaders/leaves.gdshader, autumn); or (turn, tint), only turn of the way there."""
        rng, info = self.rng, self.info
        if sapling:  # a young spruce: the mockups' small spruce, scaled up; the new spruce at the same height
            old = f"YoungSpruce{int(rng.integers(4))}"
            new = f"NorwaySpruce_{'AB'[int(rng.integers(2))]}"
            s_old, s_new = s, s * info[old]["height"] / info[new]["height"]
            sink = SINK["sapling"]
        else:
            base, n = OLD_TREES[kind]
            old, new = f"{base}{int(rng.integers(n))}", f"{kind}_{'AB'[int(rng.integers(2))]}"
            s_old = s_new = s
            sink = SINK["tree"]
        z = self.ground(x, y) - sink
        t = {"kind": "YoungSpruce" if sapling else kind, "old": old, "new": new, "p": to_godot((x, y, z)),
             "r": round(float(rot), 3), "s_old": round(float(s_old), 3), "s_new": round(float(s_new), 3), "ring": ring}
        if tint is not None:
            turn, tint = tint if isinstance(tint, tuple) else (1.0, tint)
            t["tint"] = round(float(tint), 3)
            if turn < 1.0:
                t["turn"] = round(float(turn), 3)
        self.trees.append(t)
        if ring == "near" and D.boundary_dist(np.array([x]), np.array([y]))[0] > -4.0:
            trunk = max(info[old]["foot"] * s_old, min(info[new]["foot"], 0.5) * s_new)
            self.solids.append(to_godot((x, y, z)) + [round(float(np.clip(trunk, 0.22, 0.55)), 2), 4.0])

    def forest(self, cell=3.8, saplings=True, keep_off=2.6, size=(0.85, 1.15), tint=None, density=None, kind=None):
        """Trees on a jittered grid, thinned by the area's density, the big ones keep_off path half-widths from the
        paths' middles; young spruces fill in where it's thick. tint(x, y, kind) gives a tree's autumn, or None;
        density(X, Y) and kind(X, Y, roll) stand in for the area's density and tree_kind."""
        rng = self.rng
        X, Y = jittered(rng, D.BAKE, cell)
        dens, pd = (density or D.density)(X, Y), D.path_dist(X, Y)
        r, roll = rng.uniform(0, 1, len(X)), rng.uniform(0, 1, len(X))
        kinds = (kind or D.tree_kind)(X, Y, roll)
        for x, y, d, p, r_, k in zip(X, Y, dens, pd, r, kinds):
            if p < 1.8 or self.blocked(x, y, 2.0):
                continue
            if saplings and d > 0.62 and d * 0.92 <= r_ < d * 1.35 and not self.blocked(x + 1.3, y - 0.8, 2.0):
                self.add_tree("NorwaySpruce", x + 1.3, y - 0.8, rng.uniform(2.2, 3.6), rng.uniform(0, math.tau), "near", sapling=True)
            elif r_ < d * 0.92 and p > keep_off:  # the big trees keep back from the trails, so the high camera sees them
                kind = D.SPECIES[k]
                self.add_tree(kind, x, y, rng.uniform(*size), rng.uniform(0, math.tau), "near",
                              tint=tint(x, y, kind) if tint else None)

    def lone_trees(self):
        for kind, (x, y) in D.LONE_TREES:
            self.add_tree(kind, x, y, self.rng.uniform(1.0, 1.12), self.rng.uniform(0, math.tau), "near")

    def far_forest(self, cell=9.0, share=0.9, tint=None):
        """The distant forest beyond the detailed ground, out to FAR_R, for low camera angles."""
        rng = self.rng
        X, Y = jittered(rng, (-D.FAR_R, D.FAR_R, -D.FAR_R, D.FAR_R), cell)
        keep = (np.hypot(X, Y) < D.FAR_R) & ~((X > D.BAKE[0]) & (X < D.BAKE[1]) & (Y > D.BAKE[2]) & (Y < D.BAKE[3]))
        X, Y = X[keep], Y[keep]
        r, roll = rng.uniform(0, 1, len(X)), rng.uniform(0, 1, len(X))
        kinds = D.tree_kind(X, Y, roll)
        for x, y, r_, k in zip(X, Y, r, kinds):
            if r_ < share * (D.far_density(x, y) if hasattr(D, "far_density") else 1.0):
                kind = D.SPECIES[k]
                self.add_tree(kind, x, y, rng.uniform(0.95, 1.25), rng.uniform(0, math.tau), "far",
                              tint=tint(x, y, kind) if tint else None)

    def rocks_and_logs(self, cell=7.0, rates=(0.11, 0.14, 0.2, 0.215, 0.222)):
        """Boulders, big boulders, young spruces, logs and snags, the last four off the meadow; rates are the
        running shares of spots that get each."""
        rng, info = self.rng, self.info
        X, Y = jittered(rng, D.BAKE, cell)
        G, pd = D.ground_masks(X, Y), D.path_dist(X, Y)
        r = rng.uniform(0, 1, len(X))
        for x, y, mead, p, r_ in zip(X, Y, G["meadow"], pd, r):
            if p < 1.6 or self.blocked(x, y, 2.5):
                continue
            rot = rng.uniform(0, math.tau)
            if r_ < rates[0]:
                m = f"Boulder{int(rng.integers(8))}"
                self.add_prop(m, x, y, rot, rng.uniform(0.6, 1.4), solid=info[m]["foot"] * 0.85)
            elif r_ < rates[1] and mead < 0.5:
                m = f"BigBoulder{int(rng.integers(4))}"
                self.add_prop(m, x, y, rot, rng.uniform(0.9, 1.5), solid=info[m]["foot"] * 0.85)
            elif r_ < rates[2] and mead < 0.5:
                self.add_tree("NorwaySpruce", x, y, rng.uniform(0.8, 1.3), rot, "near", sapling=True)
            elif r_ < rates[3] and mead < 0.5:
                self.log(f"Log{int(rng.integers(2))}", x, y, rot)
            elif r_ < rates[4] and mead < 0.5:
                m = f"Snag{int(rng.integers(3))}"
                self.add_prop(m, x, y, rot, 1.0, solid=0.3)

    def log(self, m, x, y, rot):
        self.add_prop(m, x, y, rot, 1.0)
        for t in (-2.2, 0.0, 2.2):  # a log is solid along its length
            lx, ly = x + math.cos(rot) * t, y + math.sin(rot) * t
            self.solids.append(to_godot((lx, ly, self.ground(lx, ly) - 0.1)) + [0.36, 0.8])

    def erratics_and_landmarks(self):
        rng, info = self.rng, self.info
        for (x, y), s in D.ERRATICS:
            m = f"BigBoulder{int(rng.integers(4))}"
            self.add_prop(m, x, y, rng.uniform(0, math.tau), s, solid=info[m]["foot"] * 0.85)
        for name, (x, y), rot in D.LANDMARKS:
            self.add_prop(name, x, y, math.radians(rot), 1.0, solid=0.45)

    def ground_cover(self, cell=0.95, pick_model=None, place=None):
        """Plants on a fine jittered grid: by default berry bushes in patches, lingonberry, lichen and grass, and in
        the meadow grass, tall grass and shrubs; pick_model(i, x, y, r, pick, G, patch, lingon) can choose instead,
        returning a model name or None, and place(i, x, y, model) place it itself (returning True), such as on
        water."""
        rng = self.rng
        X, Y = jittered(rng, D.BAKE, cell)
        G, pd = D.ground_masks(X, Y), D.path_dist(X, Y)
        path = 1 - D.smoothstep(0.55, 1.2, pd)
        patch = D.fbm(X / 9.0, Y / 9.0, 2, 33)
        lingon = D.fbm(X / 11.0, Y / 11.0, 2, 44) > 0.35
        r = rng.uniform(0, 1, len(X))
        pick = rng.integers(0, 12, len(X))
        rots, scales = rng.uniform(0, math.tau, len(X)), rng.uniform(0.9, 1.3, len(X))
        for i in range(len(X)):
            x, y, r_ = X[i], Y[i], r[i]
            if path[i] > 0.2 or self.blocked(x, y, 0.5):
                continue
            if pick_model:
                m = pick_model(i, x, y, r_, pick[i], G, patch, lingon)
            elif G["meadow"][i] > 0.5:
                m = f"Grass{pick[i] % 4}" if r_ < 0.12 else (f"TallGrass{pick[i] % 3}" if r_ < 0.14 else (f"Shrub{pick[i] % 3}" if r_ < 0.16 else None))
            elif patch[i] > 0.25:
                m = (f"Blueberry{pick[i] % 3}" if r_ < 0.12 else f"Shrub{pick[i] % 3}") if r_ < 0.42 else None
            elif lingon[i] and r_ < 0.3:
                m = f"Lingonberry{pick[i] % 3}"
            elif r_ < 0.18:
                m = [f"Shrub{pick[i] % 3}", f"Grass{pick[i] % 4}", f"Lichen{pick[i] % 3}"][pick[i] % 3]
            else:
                m = None
            if m and not (place and place(i, x, y, m)):
                self.add_prop(m, x, y, rots[i], scales[i])

    def trail_edges(self):
        """Low grass tufts in the trails' worn edges, and pebbles on and beside them (act1_shots, with its own numbers)."""
        er = np.random.default_rng(4242)
        n = int((D.BAKE[1] - D.BAKE[0]) * (D.BAKE[3] - D.BAKE[2]) * 3.0)
        EX, EY = er.uniform(D.BAKE[0], D.BAKE[1], n), er.uniform(D.BAKE[2], D.BAKE[3], n)
        ed = D.path_dist(EX, EY)
        keep = ed < 1.8
        EX, EY, ed = EX[keep], EY[keep], ed[keep]
        er_r, er_rot, er_s, er_k = (er.uniform(0, 1, len(EX)) for _ in range(4))
        for i, (x, y, d) in enumerate(zip(EX, EY, ed)):
            if self.blocked(x, y, 0.4):
                continue
            if 0.75 < d < 1.7 and er_r[i] < D.smoothstep(0.75, 1.3, d) * 0.65:
                self.add_prop(f"Grass{int(er_k[i] * 4)}", x, y, er_rot[i] * math.tau, 0.45 + 0.4 * er_s[i])
            elif d < 1.35 and er_r[i] > 0.85:
                self.add_prop(f"Pebble{int(er_k[i] * 3)}", x, y, er_rot[i] * math.tau, 0.04 + 0.05 * er_s[i], sink=0.02 / 0.06)


# ------------------------------------------------------------------ an area's own models
class Extras:
    """An area's own models (its module's build_extras(extras)): water, stairs, bridges, jetties and boardwalks, in
    the kit's style, saved together in assets/areas/<area>/extras.glb, where the game finds them (the layout's
    "extras"). A model named <name>-colonly is only something to walk on or bump into: Godot's importer makes it a
    collider, on the ground's layer, and draws nothing. Water is drawn by the game's water shader (shaders/water.gdshader):
    its first UV map holds the flow (metres a second along Godot's X and Z), its second the depth over the bed."""

    def __init__(self, kit):
        self.k = kit
        self.objects = []
        self.depths = {}  # water: object name -> per corner depth, for its second UV map
        self.water_mat = bpy.data.materials.get("Water") or bpy.data.materials.new("Water")

    def _add(self, me, name):
        me.name = name
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        self.objects.append(ob)
        return ob

    def _quads(self, quads, name):
        """An invisible collider of quads (four corners each, anticlockwise from above)."""
        verts, faces = [], []
        for q in quads:
            faces.append([len(verts) + i for i in range(4)])
            verts += [tuple(map(float, v)) for v in q]
        me = bpy.data.meshes.new(name)
        me.from_pydata(verts, [], faces)
        return self._add(me, name + "-colonly")

    def _rails(self, b, pts, half, height=1.1):
        """Invisible walls along both sides of a walkway (pts: its middle line, with heights), on a collider Builder."""
        from mathutils import Matrix
        for (x0, y0, z0), (x1, y1, z1) in zip(pts, pts[1:]):
            ang = math.atan2(y1 - y0, x1 - x0)
            ln = math.hypot(x1 - x0, y1 - y0)
            for side in (-1, 1):
                ox, oy = -math.sin(ang) * side * (half + 0.05), math.cos(ang) * side * (half + 0.05)
                b.box((ln + 0.1, 0.1, height), ((x0 + x1) / 2 + ox, (y0 + y1) / 2 + oy, (z0 + z1) / 2 + height / 2),
                      lambda f: (1, 1, 1, 1), rot=Matrix.Rotation(ang, 4, "Z"))

    def water(self, name, box, level, flow=None, step=1.0):
        """Water over box (x0, x1, y0, y1) wherever level(X, Y) stands above the ground (D.height): a grid at the
        water's level, which slopes with a river's; flow(X, Y) gives its flow (metres a second, Blender's X and Y)."""
        xs, ys = grid_axes(box, step)
        X, Y = np.meshgrid(xs, ys)
        Lv = level(X, Y)
        depth = Lv - D.height(X, Y)
        FX, FY = flow(X, Y) if flow else (np.zeros_like(X), np.zeros_like(X))
        nx, ny = len(xs), len(ys)
        wet = depth > -0.25
        keep = wet[:-1, :-1] | wet[1:, :-1] | wet[:-1, 1:] | wet[1:, 1:]
        J, I = np.nonzero(keep)
        a = J * nx + I
        quads = np.stack([a, a + 1, a + nx + 1, a + nx], -1)
        used = np.unique(quads)
        remap = np.full(nx * ny, -1, np.int64)
        remap[used] = np.arange(len(used))
        me = bpy.data.meshes.new(name)
        me.from_pydata(np.stack([X.ravel()[used], Y.ravel()[used], Lv.ravel()[used]], 1).tolist(), [], remap[quads].tolist())
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        uv = me.uv_layers.new(name="UVMap")
        vi = np.zeros(len(me.loops), np.int64)
        me.loops.foreach_get("vertex_index", vi)
        fx, fy = FX.ravel()[used][vi], FY.ravel()[used][vi]
        uv.data.foreach_set("uv", np.stack([fx, 1.0 + fy], 1).astype(np.float32).ravel())  # Godot reads (x, z)
        me.materials.append(self.water_mat)
        self.depths[name] = np.clip(depth.ravel()[used][vi], -0.25, 8.0).astype(np.float32)
        self._add(me, name)

    def stairs(self, name, p0, p1, width=1.3):
        """Wooden steps up the ground from p0 (the foot, x, y) to p1 (the top): squared logs set into the slope, a
        board along each side and a handrail on the left. They're walked on as the ground, which should rise
        evenly under them, no steeper than the hero can climb (the area's height makes a ramp there)."""
        from mathutils import Matrix
        k = self.k
        b = k["Builder"]()
        (x0, y0), (x1, y1) = p0, p1
        z0, z1 = self_ground(x0, y0), self_ground(x1, y1)
        run, ang = math.hypot(x1 - x0, y1 - y0), math.atan2(y1 - y0, x1 - x0)
        n = max(2, int(round((z1 - z0) / 0.2)))
        rise, tread = (z1 - z0) / n, run / n
        lx, ly = -math.sin(ang), math.cos(ang)  # to the left, going up
        R = Matrix.Rotation(ang, 4, "Z")
        pitch = Matrix.Rotation(-math.atan2(z1 - z0, run), 4, "Y")
        wood, dark = k["pick"]("wood", "wood2", "timber2"), k["pick"]("timber", "timber2")
        for i in range(n):
            t = (i + 0.5) / n
            top = z0 + (i + 1) * rise
            b.box((tread * 0.92, width, rise + 0.3), (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, top - (rise + 0.3) / 2), wood, rot=R)
        slope = math.hypot(run, z1 - z0)
        for side in (-1, 1):
            o = side * (width / 2 + 0.05)
            b.box((slope + 0.3, 0.1, 0.32), ((x0 + x1) / 2 + lx * o, (y0 + y1) / 2 + ly * o, (z0 + z1) / 2 + 0.12), dark, rot=R @ pitch)
        posts = max(2, int(run / 1.7) + 1)
        o = width / 2 + 0.16
        for j in range(posts):
            t = j / (posts - 1)
            b.box((0.11, 0.11, 1.15), (x0 + (x1 - x0) * t + lx * o, y0 + (y1 - y0) * t + ly * o, z0 + (z1 - z0) * t + 0.45), dark, rot=R)
        b.box((slope + 0.1, 0.08, 0.08), ((x0 + x1) / 2 + lx * o, (y0 + y1) / 2 + ly * o, (z0 + z1) / 2 + 1.0), dark, rot=R @ pitch)
        self._add(b.mesh(name), name)

    def bridge(self, name, p0, p1, width=1.5, arch=0.35):
        """A plank footbridge from bank to bank, p0 to p1, arching up arch metres in the middle, with a handrail on
        each side; walked on (its deck a collider), with invisible walls along its rails."""
        from mathutils import Matrix
        k = self.k
        b = k["Builder"]()
        (x0, y0), (x1, y1) = p0, p1
        z0, z1 = self_ground(x0, y0) + 0.08, self_ground(x1, y1) + 0.08
        ln, ang = math.hypot(x1 - x0, y1 - y0), math.atan2(y1 - y0, x1 - x0)
        lx, ly = -math.sin(ang), math.cos(ang)
        R = Matrix.Rotation(ang, 4, "Z")

        def at(t, side=0.0, up=0.0):
            return (x0 + (x1 - x0) * t + lx * side, y0 + (y1 - y0) * t + ly * side, z0 + (z1 - z0) * t + arch * 4 * t * (1 - t) + up)

        wood, dark = k["pick"]("wood", "wood2", "timber2"), k["pick"]("timber", "timber2")
        n = int(ln / 0.3)
        for i in range(n):  # planks across, each tilted with the arch
            t = (i + 0.5) / n
            dz = (at(t + 0.5 / n)[2] - at(t - 0.5 / n)[2])
            tilt = Matrix.Rotation(-math.atan2(dz, ln / n), 4, "Y")
            b.box((ln / n * 0.86, width, 0.07), at(t, up=-0.035), wood, rot=R @ tilt)
        segs = 6
        for side in (-1, 1):  # the beams under, and the posts and rails
            for j in range(segs):
                ta, tb = j / segs, (j + 1) / segs
                pa, pb = at(ta, side * width * 0.38, -0.16), at(tb, side * width * 0.38, -0.16)
                tilt = Matrix.Rotation(-math.atan2(pb[2] - pa[2], ln / segs), 4, "Y")
                b.box((ln / segs + 0.05, 0.16, 0.2), tuple((u + v) / 2 for u, v in zip(pa, pb)), dark, rot=R @ tilt)
                ra, rb = at(ta, side * (width / 2 + 0.05), 0.95), at(tb, side * (width / 2 + 0.05), 0.95)
                b.box((ln / segs + 0.04, 0.08, 0.08), tuple((u + v) / 2 for u, v in zip(ra, rb)), dark, rot=R @ tilt)
            for j in range(segs + 1):
                b.box((0.1, 0.1, 1.05), at(j / segs, side * (width / 2 + 0.05), 0.45), dark, rot=R)
        self._add(b.mesh(name), name)
        deck, mid = [], []
        for j in range(12):
            ta, tb = j / 12 - (0.04 if j == 0 else 0), (j + 1) / 12 + (0.04 if j == 11 else 0)
            a0, a1, b0, b1 = at(ta, -width / 2), at(ta, width / 2), at(tb, -width / 2), at(tb, width / 2)
            deck.append([a0, b0, b1, a1])
            mid.append(at(ta))
        mid.append(at(1.0))
        self._quads(deck, name + "Deck")
        rails = k["Builder"]()
        self._rails(rails, mid, width / 2)
        self._add(rails.mesh(name + "Rails"), name + "Rails-colonly")

    def jetty(self, name, p0, p1, width=1.6, deck=0.45, level=0.0):
        """A wooden jetty from the shore at p0 out over the water to p1, its deck deck metres over the water's level,
        on posts down to the bed; walked on, with invisible walls along its sides and end."""
        from mathutils import Matrix
        k = self.k
        b = k["Builder"]()
        (x0, y0), (x1, y1) = p0, p1
        top = level + deck
        ln, ang = math.hypot(x1 - x0, y1 - y0), math.atan2(y1 - y0, x1 - x0)
        lx, ly = -math.sin(ang), math.cos(ang)
        R = Matrix.Rotation(ang, 4, "Z")
        wood, dark = k["pick"]("wood", "wood2", "timber2", "log"), k["pick"]("timber", "timber2", "log2")
        n = int(ln / 0.28)
        for i in range(n):
            t = (i + 0.5) / n
            b.box((ln / n * 0.86, width, 0.07), (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, top - 0.035), wood, rot=R)
        for side in (-1, 1):
            o = side * width * 0.4
            b.box((ln, 0.14, 0.18), ((x0 + x1) / 2 + lx * o, (y0 + y1) / 2 + ly * o, top - 0.16), dark, rot=R)
            for j in range(int(ln / 2.0) + 1):
                t = min(1.0, j * 2.0 / ln)
                px, py = x0 + (x1 - x0) * t + lx * side * (width / 2 + 0.02), y0 + (y1 - y0) * t + ly * side * (width / 2 + 0.02)
                bed = self_ground(px, py)
                b.limb((px, py, bed - 0.3), (px, py, top + 0.12), 0.09, 0.08, dark, segs=6)
        self._add(b.mesh(name), name)
        a0, a1 = (x0 + lx * width / 2, y0 + ly * width / 2), (x0 - lx * width / 2, y0 - ly * width / 2)
        b0, b1 = (x1 + lx * width / 2, y1 + ly * width / 2), (x1 - lx * width / 2, y1 - ly * width / 2)
        ux, uy = math.cos(ang), math.sin(ang)
        r0, r1 = (a1[0] - ux * 1.4, a1[1] - uy * 1.4), (a0[0] - ux * 1.4, a0[1] - uy * 1.4)  # the ramp's foot, on land
        self._quads([[(*a1, top), (*b1, top), (*b0, top), (*a0, top)],
                     [(*r0, self_ground(*r0) - 0.02), (*a1, top), (*a0, top), (*r1, self_ground(*r1) - 0.02)]], name + "Deck")
        # walls along its sides and across its end, from the bed up, so the hero can neither walk off it nor wade
        # under it into the deep water
        bed = min(self_ground(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t) for t in np.linspace(0, 1, 9)) - 0.5
        hgt = top + 1.1 - bed
        walls = k["Builder"]()
        white = lambda f: (1, 1, 1, 1)  # noqa: E731
        for side in (-1, 1):
            o = side * (width / 2 + 0.05)
            walls.box((ln + 0.1, 0.1, hgt), ((x0 + x1) / 2 + lx * o, (y0 + y1) / 2 + ly * o, bed + hgt / 2), white, rot=R)
        walls.box((0.1, width + 0.3, hgt), (x1 + ux * 0.05, y1 + uy * 0.05, bed + hgt / 2), white, rot=R)
        self._add(walls.mesh(name + "Walls"), name + "Walls-colonly")

    def boardwalk(self, name, pts, width=0.9, lift=0.14, level=None):
        """A boardwalk over wet ground (a spang): two planks side by side, on short cross logs, following pts,
        lift metres over the ground (or the water's level(x, y), where higher), its ends sloping down to the
        ground; walked on."""
        from mathutils import Matrix
        k = self.k
        b = k["Builder"]()
        pts = [tuple(map(float, p)) for p in pts]
        tops = [max(self_ground(x, y), level(x, y) if level else -1e9) + lift for x, y in pts]
        tops[0], tops[-1] = self_ground(*pts[0]) + 0.03, self_ground(*pts[-1]) + 0.03
        plank = k["pick"]("snag", "snag2", "log", "wood")
        dark = k["pick"]("log2", "timber2", "wood2")
        quads = []
        for (xa, ya), (xb, yb), za, zb in zip(pts, pts[1:], tops, tops[1:]):
            ln, ang = math.hypot(xb - xa, yb - ya), math.atan2(yb - ya, xb - xa)
            lx, ly = -math.sin(ang), math.cos(ang)
            R = Matrix.Rotation(ang, 4, "Z") @ Matrix.Rotation(-math.atan2(zb - za, ln), 4, "Y")
            for side in (-1, 1):
                o = side * width * 0.26
                b.box((ln + 0.12, width * 0.46, 0.06), ((xa + xb) / 2 + lx * o, (ya + yb) / 2 + ly * o, (za + zb) / 2 - 0.03), plank, rot=R)
            b.limb((xb - lx * width * 0.65, yb - ly * width * 0.65, zb - 0.1), (xb + lx * width * 0.65, yb + ly * width * 0.65, zb - 0.1), 0.07, 0.06, dark, segs=5)
            quads.append([(xa - lx * width / 2, ya - ly * width / 2, za), (xb - lx * width / 2, yb - ly * width / 2, zb),
                          (xb + lx * width / 2, yb + ly * width / 2, zb), (xa + lx * width / 2, ya + ly * width / 2, za)])
        self._add(b.mesh(name), name)
        self._quads(quads, name + "Deck")

    def save(self, path):
        if not self.objects:
            return None
        export_glb(self.objects, path, self.depths)
        for ob in self.objects:
            bpy.data.objects.remove(ob)
        self.objects = []
        return path


def self_ground(x, y):
    return float(D.height(np.array([x]), np.array([y]))[0])


def populate_default(L):
    """The way the first area (Storskogen) is scattered, the way the mockups do it (act1_shots.populate_act)."""
    L.clear += [(D.START[0], 3.5)] + [(p, 2.5) for _, p, _ in D.LANDMARKS] + [(p, 4.5) for _, p in D.LONE_TREES]
    L.clear += [(p, 2.0 * s + 1.0) for p, s in D.ERRATICS]
    L.forest()
    L.lone_trees()
    L.far_forest()
    L.rocks_and_logs()
    L.erratics_and_landmarks()
    L.ground_cover()
    L.trail_edges()


def build_layout():
    """Scatter the area's trees, rocks and plants (its populate, or populate_default). Every tree spot names the old
    model and the new one, so the two versions of the demo differ only in the trees."""
    L = Layout(load_info(), np.random.default_rng(getattr(D, "SEED", 11)))
    getattr(D, "populate", populate_default)(L)
    (sx, sy), facing = D.START
    layout = {
        "about": "Written by tools/build_demo.py from tools/areas/%s.py. Positions are Godot's (metres, Y up); a prop is "
                 "[x, y, z, rotation about Y in radians, scale]; a solid is [x, y, z, radius, height]." % AREA,
        "title": getattr(D, "TITLE", AREA),
        "start": {"position": to_godot((sx, sy, L.ground(sx, sy))), "facing": facing},
        "boundary": [[round(float(x), 2), round(float(-y), 2)] for x, y in D.BOUNDARY],
        "trees": L.trees, "props": {k: L.props[k] for k in sorted(L.props)}, "solids": L.solids,
    }
    layout.update(L.extras)
    if hasattr(D, "build_extras"):  # the area's own models: water, stairs, bridges (Extras)
        E = Extras(load_kit())
        D.build_extras(E)
        os.makedirs(GROUND_DIR, exist_ok=True)
        if E.save(os.path.join(GROUND_DIR, "extras.glb")):
            layout["extras"] = "res://assets/areas/%s/extras.glb" % AREA
    os.makedirs(os.path.dirname(LAYOUT_PATH), exist_ok=True)
    with open(LAYOUT_PATH, "w") as fh:
        json.dump(layout, fh, separators=(",", ":"))
    near = sum(1 for t in L.trees if t["ring"] == "near")
    print("layout %s: %d trees near, %d far, %d props, %d solids" % (AREA, near, len(L.trees) - near, sum(map(len, L.props.values())), len(L.solids)))


# ------------------------------------------------------------------ ground
GRID = 0.5  # terrain spacing over the detailed ground (m)
FAR = 330.0  # the outer ground reaches this far from the centre
FAR_GRID = 5.0
COLOUR_TEXEL = 0.04  # the ground's colour; the game's shader draws the gravel, grit and fallen leaves on top
MASK_TEXEL = 0.1  # where the paths wear the grass, and the paths' dirt colour
FAR_TEXEL = 0.5  # the outer ground's colour
CANOPY_TEXEL = 0.25  # how much the trees shade the ground from the sky
GROUND_LAYERS = ("pathw", "bog", "shore", "meadow", "field", "fieldbase", "yard", "paving", "ash", "darkfloor",
                 "moss", "litter", "heath", "rock", "gravel", "sedge", "bed")  # the last seven: extend_ground_more


def grid_axes(box, step):
    x0, x1, y0, y1 = box
    return np.arange(x0, x1 + step * 0.5, step), np.arange(y0, y1 + step * 0.5, step)


def ground_mesh(name, box, step, kit):
    """A terrain grid with the layers the ground shader reads, like act1_shots.grid_mesh."""
    xs, ys = grid_axes(box, step)
    X, Y = np.meshgrid(xs, ys)
    Z = D.height(X, Y)
    nx, ny = len(xs), len(ys)
    I, J = np.meshgrid(np.arange(nx - 1), np.arange(ny - 1))
    a = (J * nx + I).ravel()
    me = bpy.data.meshes.new(name)
    me.from_pydata(np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1).tolist(), [],
                   np.stack([a, a + 1, a + nx + 1, a + nx], -1).tolist())
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    G = D.ground_masks(X, Y)
    for k in GROUND_LAYERS:
        at = me.attributes.new(k, "FLOAT", "POINT")
        at.data.foreach_set("value", G.get(k, np.zeros_like(X)).ravel().astype(np.float32))
    me.materials.append(kit["MAT_GROUND"])
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def show(kit, socket_fn):
    """Make the ground shader emit one of its inner values instead of shading, for baking it from above."""
    nt = kit["MAT_GROUND"].node_tree
    out = nt.nodes["Material Output"]
    em = nt.nodes.get("BakeEmit") or nt.nodes.new("ShaderNodeEmission")
    em.name = "BakeEmit"
    nt.links.new(socket_fn(nt), em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])


def mix_input(node, name):
    return [s for s in node.inputs if s.name == name and s.type == "RGBA"][0].links[0].from_socket


def drift_socket(nt):
    """The fallen leaves' drifts (the drift noise in mat_ground), as grey."""
    n = nt.nodes.get("BakeDrift") or nt.nodes.new("ShaderNodeTexNoise")
    n.name = "BakeDrift"
    n.inputs["Scale"].default_value = 0.22
    n.inputs["Detail"].default_value = 2.0
    n.inputs["Roughness"].default_value = 0.5
    vm = nt.nodes.get("BakeDriftOff") or nt.nodes.new("ShaderNodeVectorMath")
    vm.name = "BakeDriftOff"
    vm.operation = "ADD"
    vm.inputs[1].default_value = (17, 29, 0)
    nt.links.new(nt.nodes.new("ShaderNodeNewGeometry").outputs["Position"], vm.inputs[0])
    nt.links.new(vm.outputs[0], n.inputs["Vector"])
    return n.outputs["Fac"]


def path_noise_socket(nt):
    """The noises the path's colours are drawn from, as red (the dirt's) and green (the trampled grass's), so the game
    can colour the path from a palette (scripts/path_themes.gd)."""
    comb = nt.nodes.get("BakePathNoise") or nt.nodes.new("ShaderNodeCombineColor")
    comb.name = "BakePathNoise"
    nt.links.new(nt.nodes["DirtNoise"].outputs["Fac"], comb.inputs[0])
    nt.links.new(nt.nodes["WornNoise"].outputs["Fac"], comb.inputs[1])
    return comb.outputs[0]


def masks_socket(nt):
    """Where the paths wear the grass, for the game to work out the wear itself and spread it further than the
    mockups do (shaders/ground.gdshaderinc): red is the distance from the path's centre line in half-widths, with
    the edges' wobble (PathDist in mat_ground), stored as (d + 0.5) / 5; green a noise for patches of wear a metre or
    two across; blue the tufts' noise + 0.5."""
    comb = nt.nodes.get("BakeMasks") or nt.nodes.new("ShaderNodeCombineColor")
    comb.name = "BakeMasks"
    add = nt.nodes.get("BakeTufts") or nt.nodes.new("ShaderNodeMath")
    add.name = "BakeTufts"
    add.operation = "ADD"
    add.inputs[1].default_value = 0.5
    nt.links.new(nt.nodes["Tufts"].outputs[0], add.inputs[0])
    dist = nt.nodes.get("BakeDist") or nt.nodes.new("ShaderNodeMath")
    dist.name = "BakeDist"
    dist.operation = "MULTIPLY_ADD"
    dist.inputs[1].default_value = 0.2
    dist.inputs[2].default_value = 0.1
    nt.links.new(nt.nodes["PathDist"].outputs[0], dist.inputs[0])
    patches = nt.nodes.get("BakePatches") or nt.nodes.new("ShaderNodeTexNoise")
    patches.name = "BakePatches"
    patches.inputs["Scale"].default_value = 0.55
    patches.inputs["Detail"].default_value = 2.0
    patches.inputs["Roughness"].default_value = 0.5
    off = nt.nodes.get("BakePatchesOff") or nt.nodes.new("ShaderNodeVectorMath")
    off.name = "BakePatchesOff"
    off.operation = "ADD"
    off.inputs[1].default_value = (53, 11, 0)
    nt.links.new(nt.nodes.new("ShaderNodeNewGeometry").outputs["Position"], off.inputs[0])
    nt.links.new(off.outputs[0], patches.inputs["Vector"])
    nt.links.new(dist.outputs[0], comb.inputs[0])
    nt.links.new(patches.outputs["Fac"], comb.inputs[1])
    nt.links.new(add.outputs[0], comb.inputs[2])
    return comb.outputs[0]


def bake_view(box, texel, path, tiles=(1, 1), quality=None):
    """Render the ground straight down, orthographic, texel metres per pixel, in tiles, and save it as one image.
    Pixel values are what the shader emits, sRGB-encoded."""
    sc = bpy.context.scene
    x0, x1, y0, y1 = box
    W, H = int(round((x1 - x0) / texel)), int(round((y1 - y0) / texel))
    tw, th = W // tiles[0], H // tiles[1]
    full = np.zeros((H, W, 4), np.float32)
    cd = bpy.data.cameras.get("BakeCam") or bpy.data.cameras.new("BakeCam")
    cd.type = "ORTHO"
    cd.sensor_fit = "HORIZONTAL"
    cd.ortho_scale = tw * texel
    cd.clip_start, cd.clip_end = 1.0, 500.0
    cam = bpy.data.objects.get("BakeCam") or bpy.data.objects.new("BakeCam", cd)
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = tw, th
    tmp = os.path.join(bpy.app.tempdir, "ground_tile.png")
    for j in range(tiles[1]):
        for i in range(tiles[0]):
            cam.location = (x0 + (i + 0.5) * tw * texel, y0 + (j + 0.5) * th * texel, 200.0)
            cam.rotation_euler = (0, 0, 0)
            sc.render.filepath = tmp
            bpy.ops.render.render(write_still=True)
            img = bpy.data.images.load(tmp)
            px = np.array(img.pixels[:], np.float32).reshape(th, tw, 4)  # rows from the bottom (south)
            full[j * th:(j + 1) * th, i * tw:(i + 1) * tw] = px
            bpy.data.images.remove(img)
    if path:
        save_pixels(full, path, quality)
    return full


def save_pixels(px, path, quality=None, alpha=False):
    """Save rows-from-the-bottom pixels (0..1, already encoded) as PNG, or as JPEG at the given quality."""
    H, W = px.shape[:2]
    img = bpy.data.images.new(os.path.basename(path), W, H, alpha=alpha)
    if px.ndim == 2:
        px = np.dstack([px, px, px, np.ones_like(px)])
    img.pixels.foreach_set(px.astype(np.float32).ravel())
    img.filepath_raw = path
    img.file_format = "JPEG" if quality else "PNG"
    if alpha:
        img.alpha_mode = "STRAIGHT"
    if quality:
        img.save(quality=quality)
    else:
        img.save()
    bpy.data.images.remove(img)


def canopy_kernel(me, see_through, radius=16.0, step=1.0, rays=48):
    """How much of the sky a tree hides from the ground round it: occlusion at each ground point within radius,
    from rays cast up over the hemisphere. Leaf cards stop half the rays, for the holes in their cut-outs."""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [tuple(p.vertices) for p in me.polygons])
    mats = [p.material_index for p in me.polygons]
    r = random.Random(9)
    dirs = []
    for i in range(rays):
        u, v = (i + r.random()) / rays, r.random()
        dirs.append(Vector((math.sqrt(u) * math.cos(math.tau * v), math.sqrt(u) * math.sin(math.tau * v), math.sqrt(1 - u))))
    n = int(round(2 * radius / step)) + 1
    k = np.zeros((n, n), np.float32)
    for j in range(n):
        for i in range(n):
            o = Vector((-radius + i * step, -radius + j * step, 0.1))
            occ = 0.0
            for d in dirs:
                hit, _n, fi, _dist = bvh.ray_cast(o, d, 60.0)
                if hit is not None:
                    occ += 0.5 if mats[fi] in see_through else 1.0
            k[j, i] = occ / rays
    return k


def canopy_map(trees, which, kernels, box, texel, radius=16.0, step=1.0):
    """Sky visibility over the ground (rows from the south) under one tree set: each tree's kernel, turned and
    scaled with the tree, multiplied in."""
    x0, x1, y0, y1 = box
    W, H = int(round((x1 - x0) / texel)), int(round((y1 - y0) / texel))
    vis = np.ones((H, W), np.float32)
    for t in trees:
        model, s = t[which], t["s_" + which]
        gx, _gy, gz = t["p"]
        x, y = gx, -gz
        R = radius * s
        i0, i1 = max(0, int((x - R - x0) / texel)), min(W, int((x + R - x0) / texel) + 1)
        j0, j1 = max(0, int((y - R - y0) / texel)), min(H, int((y + R - y0) / texel) + 1)
        if i0 >= i1 or j0 >= j1:
            continue
        PX, PY = np.meshgrid(x0 + (np.arange(i0, i1) + 0.5) * texel - x, y0 + (np.arange(j0, j1) + 0.5) * texel - y)
        c, sn = math.cos(-t["r"]), math.sin(-t["r"])
        u = (PX * c - PY * sn) / s
        v = (PX * sn + PY * c) / s
        fi, fj = (u + radius) / step, (v + radius) / step
        k = kernels[model]
        n = k.shape[0]
        inside = (fi >= 0) & (fi < n - 1) & (fj >= 0) & (fj < n - 1)
        ii, jj = np.clip(fi.astype(int), 0, n - 2), np.clip(fj.astype(int), 0, n - 2)
        a, b = np.clip(fi - ii, 0, 1), np.clip(fj - jj, 0, 1)
        occ = (k[jj, ii] * (1 - a) * (1 - b) + k[jj, ii + 1] * a * (1 - b) + k[jj + 1, ii] * (1 - a) * b + k[jj + 1, ii + 1] * a * b)
        vis[j0:j1, i0:i1] *= 1.0 - np.where(inside, occ, 0.0)
    return vis


def bake_scene():
    """Set the scene up for baking the ground from above: plain emission, no tone mapping, no dithering."""
    os.makedirs(GROUND_DIR, exist_ok=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure, sc.view_settings.gamma = 0.0, 1.0
    sc.render.dither_intensity = 0.0
    sc.render.filter_size = 1.0
    sc.eevee.taa_render_samples = 16
    sc.world = bpy.data.worlds.new("Black")
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.image_settings.color_depth = "8"


def bake_masks(kit):
    """The masks: where the paths wear the grass (masks_socket), with the fallen leaves' drift noise in alpha."""
    show(kit, masks_socket)
    masks = bake_view(D.BAKE, MASK_TEXEL, None)
    show(kit, drift_socket)
    drift = bake_view(D.BAKE, MASK_TEXEL, None)
    d = drift[..., 0]  # the leaves' drift noise, in alpha: a texture's alpha is never sRGB-decoded, so store it linear
    masks[..., 3] = np.where(d <= 0.04045, d / 12.92, ((d + 0.055) / 1.055) ** 2.4)
    save_pixels(masks, os.path.join(GROUND_DIR, "masks.png"), alpha=True)


def bake_litter(texel=0.25):
    """Where autumn's leaves cover the ground (an area's litter layer), for the game's fallen leaves to cover it too
    (litter in shaders/ground.gdshaderinc): litter.png, only for an area that has the layer."""
    x0, x1, y0, y1 = D.BAKE
    X, Y = np.meshgrid(x0 + (np.arange(int(round((x1 - x0) / texel))) + 0.5) * texel,
                       y0 + (np.arange(int(round((y1 - y0) / texel))) + 0.5) * texel)  # rows from the south
    litter = D.ground_masks(X, Y).get("litter")
    if litter is not None:
        save_pixels(np.clip(litter, 0.0, 1.0), os.path.join(GROUND_DIR, "litter.png"))


def build_masks():
    """Only the masks, after changing how the paths wear the grass (the rest of the ground stays as it is)."""
    kit = load_kit()
    extend_ground_more(kit)
    bake_scene()
    inner = ground_mesh("Ground", D.BAKE, GRID, kit)
    bake_masks(kit)
    bpy.data.objects.remove(inner)
    bake_litter()


def build_ground():
    kit = load_kit()
    extend_ground_more(kit)
    bake_scene()
    sc = bpy.context.scene

    # heights, rows running south (Godot's +Z), for the terrain mesh and its collider
    xs, ys = grid_axes(D.BAKE, GRID)
    X, Y = np.meshgrid(xs, ys[::-1])
    D.height(X, Y).astype("<f4").tofile(os.path.join(GROUND_DIR, "heights.bin"))
    fxs, fys = grid_axes((-FAR, FAR, -FAR, FAR), FAR_GRID)
    FX, FY = np.meshgrid(fxs, fys[::-1])
    D.height(FX, FY).astype("<f4").tofile(os.path.join(GROUND_DIR, "heights_far.bin"))

    # the mockups' ground shader, baked from above: the grass and moss before feet trampled them, the noises the
    # path's colours come from, and the masks; the game paints the trampled grass and the dirt from a palette
    inner = ground_mesh("Ground", D.BAKE, GRID, kit)
    show(kit, lambda nt: mix_input(nt.nodes["WornGrass"], "A"))
    bake_view(D.BAKE, getattr(D, "COLOUR_TEXEL", COLOUR_TEXEL), os.path.join(GROUND_DIR, "grass.jpg"), tiles=(4, 4), quality=92)
    show(kit, path_noise_socket)
    bake_view(D.BAKE, MASK_TEXEL, os.path.join(GROUND_DIR, "path_noise.png"))
    bake_masks(kit)
    bpy.data.objects.remove(inner)
    bake_litter()
    outer = ground_mesh("FarGround", (-FAR, FAR, -FAR, FAR), FAR_GRID, kit)
    show(kit, lambda nt: mix_input(nt.nodes["WornGrass"], "A"))
    bake_view((-FAR, FAR, -FAR, FAR), FAR_TEXEL, os.path.join(GROUND_DIR, "grass_far.jpg"), quality=92)
    bpy.data.objects.remove(outer)

    # the trees' shade on the ground's sky light, for each tree set
    with open(LAYOUT_PATH) as fh:
        trees = json.load(fh)["trees"]
    kit_meshes = {name: make() for items in kit_groups(kit).values() for name, make in items if name.startswith(("Pine", "TallSpruce", "Birch", "YoungSpruce"))}
    new_meshes = tree_meshes()
    kernels = {}
    for name in sorted({t["old"] for t in trees} | {t["new"] for t in trees}):
        me = kit_meshes.get(name) or new_meshes[name]
        kernels[name] = canopy_kernel(me, {i for i, m in enumerate(me.materials) if m.name.startswith(("Leaves", "Berries"))})
        print("canopy kernel", name, "peak %.2f" % kernels[name].max())
    for which in ("old", "new"):
        vis = canopy_map(trees, which, kernels, D.BAKE, CANOPY_TEXEL)
        save_pixels(vis, os.path.join(GROUND_DIR, f"canopy_{which}.png"))
        print("canopy", which, "mean sky %.2f, darkest %.2f" % (vis.mean(), vis.min()))

    res = "res://assets/areas/%s/" % AREA
    info = {
        "about": "Written by tools/build_demo.py. Godot's axes; the images' top edge is the area's north (-Z) edge. The "
                 "ground's textures are in dir: grass.jpg, path_noise.png, masks.png, grass_far.jpg, canopy_old.png and "
                 "canopy_new.png, and litter.png where autumn's leaves cover the ground.",
        "dir": res,
        "bounds": [D.BAKE[0], -D.BAKE[3], D.BAKE[1] - D.BAKE[0], D.BAKE[3] - D.BAKE[2]],  # x, z, width, depth
        "grid": GRID, "size": [len(xs), len(ys)], "heights": res + "heights.bin",
        "far_bounds": [-FAR, -FAR, 2 * FAR, 2 * FAR], "far_grid": FAR_GRID, "far_size": [len(fxs), len(fys)],
        "far_heights": res + "heights_far.bin",
    }
    with open(os.path.join(GROUND_DIR, "ground.json"), "w") as fh:
        json.dump(info, fh, indent=1)
    texel = getattr(D, "COLOUR_TEXEL", COLOUR_TEXEL)
    print("ground %s: %d x %d heights, colour %d x %d" % (AREA, len(xs), len(ys), round((D.BAKE[1] - D.BAKE[0]) / texel), round((D.BAKE[3] - D.BAKE[2]) / texel)))


# ------------------------------------------------------------------ main
if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    names = areas.AREAS
    for a in argv:
        if a.startswith("--area="):
            names = a[7:].split(",")
    stages = [a for a in argv if not a.startswith("--")] or ["models", "stumps", "layout", "ground"]
    for stage in stages:
        if stage in ("models", "kit", "stumps"):  # the same for every area
            {"models": build_models, "kit": lambda: build_models(trees=False), "stumps": build_stumps}[stage]()
            continue
        for name in names:
            use_area(name)
            {"layout": build_layout, "ground": build_ground, "masks": build_masks}[stage]()
