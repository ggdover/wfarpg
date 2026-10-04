"""Builds the play demo's assets for the Godot project in game/. Run from this folder with Blender 5.2:

    blender -b --factory-startup -P build_demo.py -- [models] [stumps] [layout] [ground]

models  the mockups' low-poly kit (the old trees, rocks, plants and props) and the tree portfolio's trees, built from
        assets/trees/tree_settings.json with two lighter versions each, as .glb files in assets/kit and assets/trees,
        with the leaf cards they use and ambient occlusion baked into them
stumps  every tree's stump, which the game shows in place of a tree in the way, and its bare trunk, which its x-ray
        leaves standing, in assets/trees/stumps.glb
layout  where every tree, rock and plant stands, in data/demo_layout.json
ground  the terrain's heights, the mockups' ground shader baked into textures, and the trees' shade on the ground
        (from the layout), in assets/ground

With no stage named, all four run, in that order. The area itself is described in demo_area.py.
"""
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
import demo_area as D  # noqa: E402

KIT_DIR = os.path.join(GAME, "assets", "kit")
TREE_DIR = os.path.join(GAME, "assets", "trees")
GROUND_DIR = os.path.join(GAME, "assets", "ground")
DATA_DIR = os.path.join(GAME, "data")


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
    src = me.color_attributes["Col"]
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
    }


def build_models():
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


def build_tree(key, variant, cfg, me, level=0, outlines=None, fewer=False):
    """treegen.build_into, at a level of detail, optionally with fewer cards per clump and with the cards trimmed to
    their leaves (outlines from card_outline, by material slot). Returns (leaf cards, faces)."""
    import treegen
    if fewer:
        cfg = fewer_settings(cfg)
    if level:
        cfg = lod_settings(cfg, level)
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


# the trees' versions, by .glb file: (name suffix, level of detail, trimmed cards, fewer cards). In the game, the
# performance panel switches between them (scripts/world.gd).
TREE_VERSIONS = {
    "trees": [("", 0, False, False), ("_1", 1, False, False), ("_2", 2, False, False)],
    "trees_trim": [("_t", 0, True, False), ("_1_t", 1, True, False), ("_2_t", 2, True, False)],
    "trees_few": [("_f", 0, False, True), ("_f_t", 0, True, True)],
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
    trees with fewer cards per clump."""
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
            square = {}  # (level, fewer) -> (mesh, ao) of the square-card version, for its trimmed twin
            for group, versions in TREE_VERSIONS.items():
                objs, ao = files[group]
                for suffix, level, trimmed, fewer in versions:
                    name = f"{key}_{variant}{suffix}"
                    me = bpy.data.meshes.new(name)
                    cards, faces = build_tree(key, variant, cfg, me, level, outlines if trimmed else None, fewer)
                    ob = bpy.data.objects.new(name, me)
                    bpy.context.scene.collection.objects.link(ob)
                    objs.append(ob)
                    info[name] = dict(mesh_info(me, bark_slot=0), cards=cards, faces=faces, species=key,
                                      file=f"res://assets/trees/{group}.glb", triangles=sum(len(f.vertices) - 2 for f in me.polygons),
                                      textures={slot: f"res://assets/trees/textures/{t}.png" for slot, t in textures.items()},
                                      materials=[m.name for m in me.materials])
                    if trimmed:
                        sq_me, sq_ao = square.get((level, fewer)) or (None, None)
                        if sq_me is None:  # the square version of the fewer-card tree is built just for this
                            sq_me = bpy.data.meshes.new(name + "_square")
                            build_tree(key, variant, cfg, sq_me, level, None, fewer)
                            sq_ao = bake_ao(sq_me, see_through={i for i, m in enumerate(sq_me.materials) if m.name != "Bark"})
                        ao[name] = transfer_ao(sq_me, sq_ao, me)
                    else:
                        ao[name] = bake_ao(me, see_through={i for i, m in enumerate(me.materials) if m.name != "Bark"})
                        square[(level, fewer)] = (me, ao[name])
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


def build_layout():
    """Scatter the trees, rocks and plants the way the mockups do (act1_shots.populate_act), over the demo area.
    Every tree spot names the old model and the new one, so the two versions of the demo differ only in the trees."""
    info = load_info()
    rng = np.random.default_rng(11)
    clear = [(D.START[0], 3.5)] + [(p, 2.5) for _, p, _ in D.LANDMARKS] + [(p, 4.5) for _, p in D.LONE_TREES]
    clear += [(p, 2.0 * s + 1.0) for p, s in D.ERRATICS]

    def blocked(x, y, pad=0.0):
        return any(math.hypot(x - c[0], y - c[1]) < r + pad for c, r in clear)

    trees, props, solids = [], {}, []

    def ground(x, y):
        return float(D.height(np.array([x]), np.array([y]))[0])

    def add_prop(model, x, y, rot, s, sink=None, solid=None):
        sink = SINK.get(model.rstrip("0123456789"), SINK["plant"]) if sink is None else sink
        z = ground(x, y) - sink * s
        props.setdefault(model, []).append(to_godot((x, y, z)) + [round(float(rot), 3), round(float(s), 3)])
        if solid:
            solids.append(to_godot((x, y, z)) + [round(solid * s, 2), round(info[model]["height"] * s, 2)])

    def add_tree(kind, x, y, s, rot, ring, sapling=False):
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
        z = ground(x, y) - sink
        trees.append({"kind": "YoungSpruce" if sapling else kind, "old": old, "new": new, "p": to_godot((x, y, z)),
                      "r": round(float(rot), 3), "s_old": round(float(s_old), 3), "s_new": round(float(s_new), 3), "ring": ring})
        if ring == "near" and D.boundary_dist(np.array([x]), np.array([y]))[0] > -4.0:
            trunk = max(info[old]["foot"] * s_old, min(info[new]["foot"], 0.5) * s_new)
            solids.append(to_godot((x, y, z)) + [round(float(np.clip(trunk, 0.22, 0.55)), 2), 4.0])

    # trees: a jittered grid, thinned by the forest's density; young spruces fill in where it is thick
    X, Y = jittered(rng, D.BAKE, 3.8)
    dens, pd = D.density(X, Y), D.path_dist(X, Y)
    r, roll = rng.uniform(0, 1, len(X)), rng.uniform(0, 1, len(X))
    kinds = D.tree_kind(X, Y, roll)
    for x, y, d, p, r_, k in zip(X, Y, dens, pd, r, kinds):
        if p < 1.8 or blocked(x, y, 2.0):
            continue
        if d > 0.62 and d * 0.92 <= r_ < d * 1.35 and not blocked(x + 1.3, y - 0.8, 2.0):
            add_tree("NorwaySpruce", x + 1.3, y - 0.8, rng.uniform(2.2, 3.6), rng.uniform(0, math.tau), "near", sapling=True)
        elif r_ < d * 0.92 and p > 2.6:  # the big trees keep back from the trails, so the high camera sees them
            add_tree(D.SPECIES[k], x, y, rng.uniform(0.85, 1.15), rng.uniform(0, math.tau), "near")
    for kind, (x, y) in D.LONE_TREES:
        add_tree(kind, x, y, rng.uniform(1.0, 1.12), rng.uniform(0, math.tau), "near")
    # the distant forest, for low camera angles
    X, Y = jittered(rng, (-D.FAR_R, D.FAR_R, -D.FAR_R, D.FAR_R), 9.0)
    keep = (np.hypot(X, Y) < D.FAR_R) & ~((X > D.BAKE[0]) & (X < D.BAKE[1]) & (Y > D.BAKE[2]) & (Y < D.BAKE[3]))
    X, Y = X[keep], Y[keep]
    r, roll = rng.uniform(0, 1, len(X)), rng.uniform(0, 1, len(X))
    kinds = D.tree_kind(X, Y, roll)
    for x, y, r_, k in zip(X, Y, r, kinds):
        if r_ < 0.9:
            add_tree(D.SPECIES[k], x, y, rng.uniform(0.95, 1.25), rng.uniform(0, math.tau), "far")

    # boulders, logs, snags and more young spruces
    X, Y = jittered(rng, D.BAKE, 7.0)
    G, pd = D.ground_masks(X, Y), D.path_dist(X, Y)
    r = rng.uniform(0, 1, len(X))
    for x, y, mead, p, r_ in zip(X, Y, G["meadow"], pd, r):
        if p < 1.6 or blocked(x, y, 2.5):
            continue
        rot = rng.uniform(0, math.tau)
        if r_ < 0.11:
            m = f"Boulder{int(rng.integers(8))}"
            add_prop(m, x, y, rot, rng.uniform(0.6, 1.4), solid=info[m]["foot"] * 0.85)
        elif r_ < 0.14 and mead < 0.5:
            m = f"BigBoulder{int(rng.integers(4))}"
            add_prop(m, x, y, rot, rng.uniform(0.9, 1.5), solid=info[m]["foot"] * 0.85)
        elif r_ < 0.2 and mead < 0.5:
            add_tree("NorwaySpruce", x, y, rng.uniform(0.8, 1.3), rot, "near", sapling=True)
        elif r_ < 0.215 and mead < 0.5:
            m = f"Log{int(rng.integers(2))}"
            add_prop(m, x, y, rot, 1.0)
            for t in (-2.2, 0.0, 2.2):  # a log is solid along its length
                lx, ly = x + math.cos(rot) * t, y + math.sin(rot) * t
                solids.append(to_godot((lx, ly, ground(lx, ly) - 0.1)) + [0.36, 0.8])
        elif r_ < 0.222 and mead < 0.5:
            m = f"Snag{int(rng.integers(3))}"
            add_prop(m, x, y, rot, 1.0, solid=0.3)
    for (x, y), s in D.ERRATICS:
        m = f"BigBoulder{int(rng.integers(4))}"
        add_prop(m, x, y, rng.uniform(0, math.tau), s, solid=info[m]["foot"] * 0.85)
    for name, (x, y), rot in D.LANDMARKS:
        add_prop(name, x, y, math.radians(rot), 1.0, solid=0.45)

    # ground cover: berry bushes in patches, lichen, grass; tall grass and grass tufts in the meadow
    X, Y = jittered(rng, D.BAKE, 0.95)
    G, pd = D.ground_masks(X, Y), D.path_dist(X, Y)
    path = 1 - D.smoothstep(0.55, 1.2, pd)
    patch = D.fbm(X / 9.0, Y / 9.0, 2, 33)
    lingon = D.fbm(X / 11.0, Y / 11.0, 2, 44) > 0.35
    r = rng.uniform(0, 1, len(X))
    pick = rng.integers(0, 12, len(X))
    rots, scales = rng.uniform(0, math.tau, len(X)), rng.uniform(0.9, 1.3, len(X))
    for i in range(len(X)):
        x, y, r_ = X[i], Y[i], r[i]
        if path[i] > 0.2 or blocked(x, y, 0.5):
            continue
        if G["meadow"][i] > 0.5:
            m = f"Grass{pick[i] % 4}" if r_ < 0.12 else (f"TallGrass{pick[i] % 3}" if r_ < 0.14 else (f"Shrub{pick[i] % 3}" if r_ < 0.16 else None))
        elif patch[i] > 0.25:
            m = (f"Blueberry{pick[i] % 3}" if r_ < 0.12 else f"Shrub{pick[i] % 3}") if r_ < 0.42 else None
        elif lingon[i] and r_ < 0.3:
            m = f"Lingonberry{pick[i] % 3}"
        elif r_ < 0.18:
            m = [f"Shrub{pick[i] % 3}", f"Grass{pick[i] % 4}", f"Lichen{pick[i] % 3}"][pick[i] % 3]
        else:
            m = None
        if m:
            add_prop(m, x, y, rots[i], scales[i])

    # low grass tufts in the trails' worn edges, and pebbles on and beside them (act1_shots, with its own numbers)
    er = np.random.default_rng(4242)
    n = int((D.BAKE[1] - D.BAKE[0]) * (D.BAKE[3] - D.BAKE[2]) * 3.0)
    EX, EY = er.uniform(D.BAKE[0], D.BAKE[1], n), er.uniform(D.BAKE[2], D.BAKE[3], n)
    ed = D.path_dist(EX, EY)
    keep = ed < 1.8
    EX, EY, ed = EX[keep], EY[keep], ed[keep]
    er_r, er_rot, er_s, er_k = (er.uniform(0, 1, len(EX)) for _ in range(4))
    for i, (x, y, d) in enumerate(zip(EX, EY, ed)):
        if blocked(x, y, 0.4):
            continue
        if 0.75 < d < 1.7 and er_r[i] < D.smoothstep(0.75, 1.3, d) * 0.65:
            add_prop(f"Grass{int(er_k[i] * 4)}", x, y, er_rot[i] * math.tau, 0.45 + 0.4 * er_s[i])
        elif d < 1.35 and er_r[i] > 0.85:
            add_prop(f"Pebble{int(er_k[i] * 3)}", x, y, er_rot[i] * math.tau, 0.04 + 0.05 * er_s[i], sink=0.02 / 0.06)

    (sx, sy), facing = D.START
    layout = {
        "about": "Written by tools/build_demo.py from tools/demo_area.py. Positions are Godot's (metres, Y up); a prop is "
                 "[x, y, z, rotation about Y in radians, scale]; a solid is [x, y, z, radius, height].",
        "start": {"position": to_godot((sx, sy, ground(sx, sy))), "facing": facing},
        "boundary": [[round(float(x), 2), round(float(-y), 2)] for x, y in D.BOUNDARY],
        "trees": trees, "props": {k: props[k] for k in sorted(props)}, "solids": solids,
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "demo_layout.json"), "w") as fh:
        json.dump(layout, fh, separators=(",", ":"))
    near = sum(1 for t in trees if t["ring"] == "near")
    print("layout: %d trees near, %d far, %d props, %d solids" % (near, len(trees) - near, sum(map(len, props.values())), len(solids)))


# ------------------------------------------------------------------ ground
GRID = 0.5  # terrain spacing over the detailed ground (m)
FAR = 330.0  # the outer ground reaches this far from the centre
FAR_GRID = 5.0
COLOUR_TEXEL = 0.04  # the ground's colour; the game's shader draws the gravel, grit and fallen leaves on top
MASK_TEXEL = 0.1  # where the paths wear the grass, and the paths' dirt colour
FAR_TEXEL = 0.5  # the outer ground's colour
CANOPY_TEXEL = 0.25  # how much the trees shade the ground from the sky
GROUND_LAYERS = ("pathw", "bog", "shore", "meadow", "field", "fieldbase", "yard", "paving", "ash", "darkfloor")


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


def build_masks():
    """Only the masks, after changing how the paths wear the grass (the rest of the ground stays as it is)."""
    kit = load_kit()
    bake_scene()
    inner = ground_mesh("Ground", D.BAKE, GRID, kit)
    bake_masks(kit)
    bpy.data.objects.remove(inner)


def build_ground():
    kit = load_kit()
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
    bake_view(D.BAKE, COLOUR_TEXEL, os.path.join(GROUND_DIR, "grass.jpg"), tiles=(4, 4), quality=92)
    show(kit, path_noise_socket)
    bake_view(D.BAKE, MASK_TEXEL, os.path.join(GROUND_DIR, "path_noise.png"))
    bake_masks(kit)
    bpy.data.objects.remove(inner)
    outer = ground_mesh("FarGround", (-FAR, FAR, -FAR, FAR), FAR_GRID, kit)
    show(kit, lambda nt: mix_input(nt.nodes["WornGrass"], "A"))
    bake_view((-FAR, FAR, -FAR, FAR), FAR_TEXEL, os.path.join(GROUND_DIR, "grass_far.jpg"), quality=92)
    bpy.data.objects.remove(outer)

    # the trees' shade on the ground's sky light, for each tree set
    with open(os.path.join(DATA_DIR, "demo_layout.json")) as fh:
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

    info = {
        "about": "Written by tools/build_demo.py. Godot's axes; the images' top edge is the area's north (-Z) edge.",
        "bounds": [D.BAKE[0], -D.BAKE[3], D.BAKE[1] - D.BAKE[0], D.BAKE[3] - D.BAKE[2]],  # x, z, width, depth
        "grid": GRID, "size": [len(xs), len(ys)], "heights": "res://assets/ground/heights.bin",
        "far_bounds": [-FAR, -FAR, 2 * FAR, 2 * FAR], "far_grid": FAR_GRID, "far_size": [len(fxs), len(fys)],
        "far_heights": "res://assets/ground/heights_far.bin",
    }
    with open(os.path.join(GROUND_DIR, "ground.json"), "w") as fh:
        json.dump(info, fh, indent=1)
    print("ground: %d x %d heights, colour %d x %d" % (len(xs), len(ys), round((D.BAKE[1] - D.BAKE[0]) / COLOUR_TEXEL), round((D.BAKE[3] - D.BAKE[2]) / COLOUR_TEXEL)))


# ------------------------------------------------------------------ main
if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    stages = argv or ["models", "stumps", "layout", "ground"]
    for stage in stages:
        {"models": build_models, "stumps": build_stumps, "layout": build_layout, "ground": build_ground, "masks": build_masks}[stage]()
