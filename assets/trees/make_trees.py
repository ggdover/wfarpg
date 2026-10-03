"""Tree portfolio: builds tree_portfolio.blend from treegen.py and the saved settings, and renders previews.

    python3 make_leaf_cards.py                                  leaf textures (once, or after changing them)
    blender -b --factory-startup -P make_trees.py               builds tree_portfolio.blend and renders previews/
    blender -b --factory-startup -P make_trees.py -- --no-render   only the .blend

The trees follow tree_settings.json (written by the tree editor's "Save settings"), or treegen.DEFAULTS where it has
nothing. The .blend has two variants of every species in a row each, with labels and a person for scale, plus a small
mixed grove seen from the game camera; the grove uses linked copies, so editing a tree updates it there too. The file
also carries a small script that registers the tree editor (tree_editor.py) when Blender is allowed to run it.
"""
import json
import math
import os
import random
import subprocess
import sys

import bpy
from mathutils import Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import treegen  # noqa: E402
import tree_editor  # noqa: E402

PREVIEWS = os.path.join(HERE, "previews")
BLEND = os.path.join(HERE, "tree_portfolio.blend")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TAU = math.tau
SPECIES = treegen.SPECIES

LOADER = '''"""Registers the tree editor: the "Trees" tab in the 3D viewport's sidebar (press N).
Its code is tree_editor.py and treegen.py, next to this .blend."""
import importlib
import sys

import bpy

folder = bpy.path.abspath("//")
if folder not in sys.path:
    sys.path.insert(0, folder)
import treegen
import tree_editor

importlib.reload(treegen)
importlib.reload(tree_editor)
tree_editor.register()
'''


def flat_material(name, hexcol, rough=0.9):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = treegen.lin(hexcol)
    b.inputs["Roughness"].default_value = rough
    return m


def collection(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c)
    return c


def text(body, size, loc, coll, mat):
    cu = bpy.data.curves.new("Label", "FONT")
    cu.body = body
    cu.size = size
    cu.align_x = "CENTER"
    cu.materials.append(mat)
    ob = bpy.data.objects.new("Label " + body.split("\n")[0], cu)
    ob.location = loc
    ob.rotation_euler = (math.pi / 2, 0, 0)
    coll.objects.link(ob)
    return ob


def person(loc, coll, mat):
    """A 1.8 m figure for scale."""
    me = bpy.data.meshes.new("Person")
    verts, faces = [], []

    def box(cx, cy, z0, sx, sy, sz):
        o = len(verts)
        for dz in (0, sz):
            for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                verts.append((cx + dx * sx / 2, cy + dy * sy / 2, z0 + dz))
        faces.extend([(o, o + 3, o + 2, o + 1), (o + 4, o + 5, o + 6, o + 7), (o, o + 1, o + 5, o + 4),
                      (o + 1, o + 2, o + 6, o + 5), (o + 2, o + 3, o + 7, o + 6), (o + 3, o, o + 4, o + 7)])

    box(-0.1, 0, 0, 0.16, 0.2, 0.86)
    box(0.1, 0, 0, 0.16, 0.2, 0.86)
    box(0, 0, 0.86, 0.44, 0.24, 0.64)
    box(-0.29, 0, 0.82, 0.12, 0.14, 0.66)
    box(0.29, 0, 0.82, 0.12, 0.14, 0.66)
    box(0, 0, 1.54, 0.22, 0.24, 0.26)
    me.from_pydata(verts, [], faces)
    me.materials.append(mat)
    ob = bpy.data.objects.new("Person for scale", me)
    ob.location = loc
    coll.objects.link(ob)
    return ob


def camera(name, loc, target, coll, lens=50, ortho=None):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_end = 2000
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    ob = bpy.data.objects.new(name, cd)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    coll.objects.link(ob)
    return ob


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    tree_editor.register()  # so the file stores the editor's settings
    settings = treegen.load_settings()
    tree_editor.fill_settings(scene, settings)
    label_mat = flat_material("Label", "#2A2824", 0.6)
    person_mat = flat_material("Person", "#5A6070", 0.8)
    ground_mat = flat_material("Ground", "#7D8C52", 1.0)

    trees_coll = collection("Trees")
    stage = collection("Portfolio")
    trees, extras, rows = {}, {}, {}
    row_len = sum(sp[5] for sp in SPECIES) + 3.0 * (len(SPECIES) - 1)
    for row, variant in enumerate("AB"):  # the two rows side by side, so neither stands behind the other
        x0 = row * (row_len + 60.0)
        x = x0
        for key, fn, eng, swe, latin, width, card in SPECIES:
            sub = bpy.data.collections.get(eng) or collection(eng, trees_coll)
            me = bpy.data.meshes.new(f"{key}_{variant}")
            treegen.build_into(key, variant, settings[key], me)
            ob = bpy.data.objects.new(f"{key}_{variant}", me)
            x += width / 2
            ob.location = (x, 0, 0)
            sub.objects.link(ob)
            trees[(key, variant)] = ob
            extras[(key, variant)] = [text(eng, 0.9, (x, -6.0, 0.9), stage, label_mat),
                                      text(f"{swe} · {latin}", 0.45, (x, -6.0, 0.25), stage, label_mat),
                                      person((x + (width / 2 + 0.6 if width >= 7 else 2.0), 0, 0), stage, person_mat)]  # beside the tree
            x += width / 2 + 3.0
        rows[variant] = x0 + row_len / 2

    # a small mixed grove, as it might stand in Act 1, off to the side of the rows
    grove = collection("Grove")
    gr = random.Random(7)
    mix = (["ScotsPine"] * 9 + ["NorwaySpruce"] * 7 + ["SilverBirch"] * 4 + ["Aspen"] * 2 + ["Rowan"] * 2 + ["Alder"] * 2 + ["Juniper"] * 4)
    gx0 = -150.0
    placed = []
    for key in mix:
        for _ in range(60):
            p = Vector((gx0 + gr.uniform(-22, 22), gr.uniform(-16, 16), 0))
            if all((p - q).length > (2.5 if key == "Juniper" else 4.2) for q in placed):
                break
        placed.append(p)
        src = trees[(key, gr.choice("AB"))]
        ob = bpy.data.objects.new(src.name + " (grove)", src.data)
        ob.location = p
        ob.rotation_euler = (0, 0, gr.uniform(0, TAU))
        sc = gr.uniform(0.85, 1.1)
        ob.scale = (sc, sc, sc)
        grove.objects.link(ob)

    gme = bpy.data.meshes.new("Ground")
    gme.from_pydata([(-350, -250, 0), (350, -250, 0), (350, 250, 0), (-350, 250, 0)], [], [(0, 1, 2, 3)])
    gme.materials.append(ground_mat)
    ground = bpy.data.objects.new("Ground", gme)
    ground.location = (40, 0, 0)
    stage.objects.link(ground)

    sun_data = bpy.data.lights.new("Sun", "SUN")
    sun_data.energy = 3.6
    sun_data.angle = math.radians(2.5)
    sun = bpy.data.objects.new("Sun", sun_data)
    sun.rotation_euler = (math.radians(48), 0, math.radians(-35))
    stage.objects.link(sun)
    world = bpy.data.worlds.new("Sky")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = treegen.lin("#B8C8D6")
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
    scene.world = world

    cams = {}
    for variant, cx in rows.items():  # orthographic and tipped down a little, like a sheet of tree portraits
        cams["Row " + variant] = camera(f"Camera row {variant}", (cx, -60, 21.0), (cx, 0, 8.0), stage, ortho=row_len + 10)
    cams["Grove"] = camera("Camera grove, game view", (gx0 + 6, -30, 32), (gx0, 1, 2), stage, lens=35)
    scene.camera = cams["Row A"]
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 64
    scene.view_settings.view_transform = "AgX"

    loader = bpy.data.texts.new("tree_editor_loader.py")
    loader.write(LOADER)
    loader.use_module = True  # runs when the file opens, if Blender is allowed to run its scripts

    # open the file looking at row A with materials shown (press N for the sidebar and its Trees tab)
    for scr in bpy.data.screens:
        for area in scr.areas:
            if area.type == "VIEW_3D":
                sp = area.spaces[0]
                sp.shading.type = "MATERIAL"
                sp.clip_end = 2000
                r3d = sp.region_3d
                r3d.view_location = (rows["A"], 0, 7)
                r3d.view_distance = 75
                r3d.view_rotation = Quaternion((0.82, 0.57, 0.0, 0.0)).normalized()
    return scene, cams, trees, extras, stage


def render(scene, cams, trees, extras, stage):
    os.makedirs(PREVIEWS, exist_ok=True)
    shots = [("Row A", "row_a.png", (2400, 1000)), ("Row B", "row_b.png", (2400, 1000)), ("Grove", "grove_game_view.png", (1600, 900))]
    for key, file, res in shots:
        scene.camera = cams[key]
        scene.render.resolution_x, scene.render.resolution_y = res
        scene.render.filepath = os.path.join(PREVIEWS, file)
        bpy.ops.render.render(write_still=True)
        print("RENDERED", file)
    # one portrait per species, everything else hidden, then a sheet of them
    info = {}
    tw, th = 600, 750
    scene.render.resolution_x, scene.render.resolution_y = tw, th
    for key, fn, eng, swe, latin, width, card in SPECIES:
        ob = trees[(key, "A")]
        keep = {ob.name, "Ground", "Sun"} | {e.name for e in extras[(key, "A")] if e.type == "MESH"}
        hidden = [o for o in scene.objects if o.type in ("MESH", "FONT") and o.name not in keep and not o.hide_render]
        for o in hidden:
            o.hide_render = True
        h = ob.dimensions.z
        x, y = ob.location.x, ob.location.y
        cam = camera("Camera " + key, (x, y - (h / 2 + 1.3) / math.tan(math.radians(19.8)), h * 0.55), (x, y, h * 0.47), stage)
        scene.camera = cam
        scene.render.filepath = os.path.join(PREVIEWS, "tiles", key + ".png")
        bpy.ops.render.render(write_still=True)
        me = ob.data
        info[key] = dict(name=eng, swedish=swe, latin=latin, height=round(h, 1), faces=len(me.polygons),
                         cards=sum(1 for q in me.polygons if q.material_index > 0))
        for o in hidden:
            o.hide_render = False
        bpy.data.objects.remove(cam, do_unlink=True)
    with open(os.path.join(PREVIEWS, "tiles", "info.json"), "w") as fh:
        json.dump(info, fh, indent=1)
    # the sheet with captions is drawn by make_sheet.py, which needs Pillow, so it runs in the system Python
    done = subprocess.run(["python3", os.path.join(HERE, "make_sheet.py")])
    print("RENDERED portfolio.png" if done.returncode == 0 else "make_sheet.py failed; run it with python3")
    scene.camera = cams["Row A"]
    scene.render.resolution_x, scene.render.resolution_y = 2400, 1000


if __name__ == "__main__":
    scene, cams, trees, extras, stage = build()
    for (key, variant), ob in sorted(trees.items()):
        me = ob.data
        print(f"TREE {ob.name}: {len(me.polygons)} faces, {sum(1 for p in me.polygons if p.material_index > 0)} leaf cards, "
              f"height {ob.dimensions.z:.1f} m")
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, relative_remap=True)
    print("SAVED", BLEND)
    if "--no-render" not in ARGS:
        render(scene, cams, trees, extras, stage)
        bpy.ops.wm.save_as_mainfile(filepath=BLEND, relative_remap=True)
    tree_editor.unregister()
