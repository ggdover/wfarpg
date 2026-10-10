"""Plant portfolio: builds plant_portfolio.blend from plantgen.py and the saved settings, and renders previews.

    python3 make_plant_cards.py                                  the cards (once, or after changing them)
    blender -b --factory-startup -P make_plants.py               builds plant_portfolio.blend and renders previews/
    blender -b --factory-startup -P make_plants.py -- --no-render   only the .blend

The plants follow plant_settings.json (written by the plant editor's "Save settings"), or plantgen.DEFAULTS where it
has nothing. The .blend has both variants of every plant side by side, in three rows (the bushes, the long grass and
the fern, the grasses) with name signs and a person for scale, plus a patch of forest floor covered in the long grass,
as the game's green ground is, with copies of the rest under a few of the tree portfolio's trees, seen from the game
camera and from close by. The floor's plants are linked
copies, so editing a plant updates them too; its trees are linked from ../trees/tree_portfolio.blend. The file also
carries a small script that registers the plant editor (plant_editor.py) when Blender is allowed to run it.
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
import plantgen  # noqa: E402  (puts ../trees on the path)
import plant_editor  # noqa: E402
from make_trees import camera, collection, flat_material, person, text  # noqa: E402
from treegen import lin  # noqa: E402

PREVIEWS = os.path.join(HERE, "previews")
BLEND = os.path.join(HERE, "plant_portfolio.blend")
TREES = os.path.join(HERE, "..", "trees", "tree_portfolio.blend")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TAU = math.tau
ROWS = [  # name, plants, the camera's pitch down (degrees), its picture in previews/
    ("Bushes", ["Raspberry", "AlderBuckthorn", "Hazel"], 10, "row_bushes.png"),
    ("Grass for the ground, and the fern", ["LongGrass", "GrassWisps", "GrassTufts", "GrassClumps", "GrassShort", "WoodFern"], 24,
     "row_grass_fern.png"),
    ("Grasses", [s[0] for s in plantgen.SPECIES if s[7] == "grass"], 20, "row_grasses.png"),
]
FLOOR = Vector((-60.0, 0.0, 0.0))  # the forest floor's middle
FLOOR_GRASS = "GrassTufts"  # the grass covering the forest floor, on its ground

LOADER = '''"""Registers the plant editor: the "Plants" tab in the 3D viewport's sidebar (press N).
Its code is plant_editor.py and plantgen.py, next to this .blend (and ../trees/treegen.py)."""
import importlib
import sys

import bpy

folder = bpy.path.abspath("//")
if folder not in sys.path:
    sys.path.insert(0, folder)
import plantgen
import plant_editor

importlib.reload(plantgen.treegen)
importlib.reload(plantgen)
importlib.reload(plant_editor)
plant_editor.register()
'''


def ground_material():
    """Moss and grass, in soft patches of two greens."""
    m = bpy.data.materials.new("Forest floor")
    m.use_nodes = True
    nt = m.node_tree
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.35
    noise.inputs["Detail"].default_value = 3.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = 0.4, 0.62
    ramp.color_ramp.elements[0].color = lin("#56663A")
    ramp.color_ramp.elements[1].color = lin("#76854A")
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    bsdf = nt.nodes["Principled BSDF"]
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 1.0
    return m


def boulder(name, loc, size, coll, mat, seed):
    """A faceted granite boulder: an icosphere, squashed and pushed about."""
    r = random.Random(seed)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=size)
    ob = bpy.context.active_object
    ob.name = name
    for v in ob.data.vertices:
        v.co *= r.uniform(0.82, 1.12)
        v.co.z *= 0.6
    ob.location = loc
    ob.rotation_euler = (0, 0, r.uniform(0, TAU))
    ob.data.materials.append(mat)
    for c in ob.users_collection:
        c.objects.unlink(ob)
    coll.objects.link(ob)
    return ob


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    plant_editor.register()  # so the file stores the editor's settings
    settings = plantgen.load_settings()
    plant_editor.fill_settings(scene, settings)
    label_mat = flat_material("Label", "#2A2824", 0.6)
    person_mat = flat_material("Person", "#5A6070", 0.8)
    stage = collection("Portfolio")
    groups = {g: collection(g.capitalize()) for g in plantgen.GROUPS}
    plants, rows = {}, {}
    x = 0.0
    for name, keys, pitch, _file in ROWS:
        x0 = x
        person((x, 0, 0), stage, person_mat)
        x += 1.6
        for key in keys:
            sp = plantgen.BY_KEY[key]
            group = next(g for g, kinds in plantgen.GROUPS.items() if sp[7] in kinds)
            sub = bpy.data.collections.get(sp[2]) or collection(sp[2], groups[group])
            w = sp[5]
            for variant in "AB":
                me = bpy.data.meshes.new(f"{key}_{variant}")
                plantgen.build_into(key, variant, settings[key], me)
                ob = bpy.data.objects.new(f"{key}_{variant}", me)
                ob.location = (x + w / 2, 0, 0)
                ob.visible_shadow = sp[7] != "patch"  # the game's grass casts none
                sub.objects.link(ob)
                plants[(key, variant)] = ob
                x += w + 0.3
            mid = x - w - 0.45
            tall = max(plants[(key, v)].dimensions.z for v in "AB")
            size = max(0.16, min(0.42, 0.55 * tall))
            a = math.radians(pitch)
            front = -(tall * 0.3 * math.cos(a) + size * 1.6) / math.sin(a)  # far enough in front to show below the plants
            text(sp[2], size, (mid, front, size * 0.6), stage, label_mat)
            text(f"{sp[3]} · {sp[4]}", size * 0.45, (mid, front, size * 0.05), stage, label_mat)
            x += 0.6
        rows[name] = (x0, x, pitch, max(plants[(k, "A")].dimensions.z for k in keys))
        x += 12.0

    floor = collection("Forest floor")
    trees = forest_floor(plants, floor)
    gme = bpy.data.meshes.new("Ground")
    gme.from_pydata([(-140, -80, 0), (140, -80, 0), (140, 80, 0), (-140, 80, 0)], [], [(0, 1, 2, 3)])
    gme.materials.append(ground_material())
    ground = bpy.data.objects.new("Ground", gme)
    ground.location = (20, 0, 0)
    stage.objects.link(ground)

    sun_data = bpy.data.lights.new("Sun", "SUN")
    sun_data.energy = 3.6
    sun_data.angle = math.radians(2.5)
    sun = bpy.data.objects.new("Sun", sun_data)
    sun.rotation_euler = (math.radians(48), 0, math.radians(-35))
    stage.objects.link(sun)
    world = bpy.data.worlds.new("Sky")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = lin("#B8C8D6")
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
    scene.world = world

    cams = {}
    for name, (x0, x1, pitch, tall) in rows.items():  # orthographic, tipped down, like a sheet of portraits
        cx, length = (x0 + x1) / 2, x1 - x0
        a = math.radians(pitch)
        size = max(0.16, min(0.42, 0.55 * tall))  # the signs', as above
        target = Vector((cx, 0, (0.7 * tall * math.cos(a) - 1.6 * size) / 2 / math.cos(a)))  # halfway from the signs to the tops
        cams[name] = camera(f"Camera {name.lower()}", target + Vector((0, -math.cos(a), math.sin(a))) * 60, target, stage,
                            ortho=length + 1.0)
    f = FLOOR
    cams["Floor game"] = camera("Camera forest floor, game view", f + Vector((0, -11.5, 16.4)), f + Vector((0, 0.5, 0)), stage, lens=35)
    cams["Floor close"] = camera("Camera forest floor, close", f + Vector((1.0, -7.5, 1.5)), f + Vector((0, -1.0, 0.25)), stage, lens=30)
    scene.camera = cams["Bushes"]
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 64
    scene.view_settings.view_transform = "AgX"

    loader = bpy.data.texts.new("plant_editor_loader.py")
    loader.write(LOADER)
    loader.use_module = True  # runs when the file opens, if Blender is allowed to run its scripts

    # open the file looking at the bushes with materials shown (press N for the sidebar and its Plants tab)
    x0, x1, _, _ = rows["Bushes"]
    for scr in bpy.data.screens:
        for area in scr.areas:
            if area.type == "VIEW_3D":
                sp = area.spaces[0]
                sp.shading.type = "MATERIAL"
                sp.clip_end = 2000
                r3d = sp.region_3d
                r3d.view_location = ((x0 + x1) / 2, 0, 1.2)
                r3d.view_distance = 22
                r3d.view_rotation = Quaternion((0.82, 0.57, 0.0, 0.0)).normalized()
    return scene, cams, plants, rows, stage, trees


def forest_floor(plants, coll):
    """A patch of forest floor, 16 by 12 m, under a few of the portfolio's trees, covered in long grass as the game's
    green ground is (its patches as far apart as its Patch spacing says, a share with seed heads), but in the pool and
    under the boulders: ferns in the spruce's shade, raspberry and buckthorn at the edge, hazel in a corner, hair-grass
    and bent here and there, small-reed along the edge, and moor-grass, sedge and cottongrass by a wet hollow. Linked
    copies: they change with the plants."""
    r = random.Random(17)
    f = FLOOR
    rock = flat_material("Granite", "#8C8A82", 0.85)
    water = flat_material("Pool", "#2E3A34", 0.15)
    placed = []

    def put(key, centre, radius, n, gap, scale=(0.85, 1.15)):
        for _ in range(n):
            for _try in range(40):
                p = Vector((centre[0] + r.uniform(-radius, radius), centre[1] + r.uniform(-radius, radius), 0))
                if (p.xy - Vector(centre)).length <= radius and all((p - q).length > max(gap, g) for q, g in placed):
                    break
            else:
                continue
            placed.append((p, gap))
            src = plants[(key, r.choice("AB"))]
            ob = bpy.data.objects.new(src.name + " (floor)", src.data)
            ob.location = f + p
            ob.rotation_euler = (0, 0, r.uniform(0, TAU))
            s = r.uniform(*scale)
            ob.scale = (s, s, s)
            coll.objects.link(ob)

    trees = []
    if os.path.exists(TREES):  # a few of the tree portfolio's trees, linked: they change when it's rebuilt
        want = [("ScotsPine_A", (-5.5, 6.5)), ("NorwaySpruce_B", (6.0, 8.0)), ("SilverBirch_A", (-0.5, 8.0)), ("ScotsPine_B", (2.5, 10.5))]
        with bpy.data.libraries.load(TREES, link=True, relative=True) as (src, dst):
            dst.meshes = [n for n, _ in want if n in src.meshes]
        for name, (x, y) in want:
            me = bpy.data.meshes.get((name, bpy.data.libraries[0].filepath)) if bpy.data.libraries else None
            me = me or next((m for m in bpy.data.meshes if m.name == name and m.library), None)
            if me is None:
                continue
            ob = bpy.data.objects.new(name + " (floor)", me)
            ob.location = f + Vector((x, y, 0))
            ob.rotation_euler = (0, 0, r.uniform(0, TAU))
            coll.objects.link(ob)
            placed.append((Vector((x, y, 0)), 1.2))
            trees.append(ob)
    boulders = [(1.8, -0.6, 0.9), (-6.8, -4.2, 0.7), (6.6, 2.2, 0.6)]
    for i, (x, y, s) in enumerate(boulders):
        boulder(f"Boulder {i}", f + Vector((x, y, s * 0.15)), s, coll, rock, 30 + i)
        placed.append((Vector((x, y, 0)), s + 0.3))
    pool = bpy.data.meshes.new("Pool")
    pts = [(math.cos(a) * 1.3 * r.uniform(0.85, 1.1), math.sin(a) * 0.9 * r.uniform(0.85, 1.1), 0.02) for a in [k * TAU / 14 for k in range(14)]]
    pool.from_pydata(pts, [], [list(range(14))])
    pool.materials.append(water)
    ob = bpy.data.objects.new("Pool", pool)
    ob.location = f + Vector((1.5, -4.2, 0))
    coll.objects.link(ob)
    placed.append((Vector((1.5, -4.2, 0)), 1.2))

    put("Hazel", (-6.0, 3.6), 0.4, 1, 2.0)
    put("AlderBuckthorn", (6.4, -0.6), 0.5, 1, 1.5)
    put("Raspberry", (-6.2, -1.6), 0.5, 1, 1.3)
    put("WoodFern", (4.5, 4.0), 2.0, 7, 0.9)
    put("PurpleMoorGrass", (1.5, -4.2), 2.1, 4, 0.45)
    put("CommonSedge", (1.5, -4.2), 1.9, 5, 0.4)
    put("Cottongrass", (2.4, -4.4), 2.0, 4, 0.4)
    put("WoodSmallReed", (7.2, -4.0), 1.2, 4, 0.55)
    put("CommonBent", (-3.0, -3.8), 2.0, 6, 0.35)
    put("WavyHairGrass", (0.0, 1.0), 7.5, 12, 0.4)
    lawn(plants, coll, r, [(Vector((1.5, -4.2, 0)), 1.25)] + [(Vector(b[:2] + (0,)), b[2] + 0.1) for b in boulders])
    return trees


def lawn(plants, coll, r, keep_out, key=FLOOR_GRASS):
    """A grass for the ground over the whole floor, as in the game, on its ground texture: a patch at every point of a
    jittered grid as far apart as its Patch spacing says, turned and sized at random, a share of them variant B (with
    seed heads, if it has them), none in the pool or under the boulders."""
    cfg = bpy.context.scene.plant_editor.plants[key]
    mat = plantgen.ground_material(key, plant_editor.as_cfg(cfg))
    if mat:
        me = bpy.data.meshes.new("Forest floor ground")
        me.from_pydata([(-8, -6, 0), (8, -6, 0), (8, 6, 0), (-8, 6, 0)], [], [(0, 1, 2, 3)])
        me.materials.append(mat)
        ob = bpy.data.objects.new("Forest floor ground", me)
        ob.location = FLOOR + Vector((0, 0, 0.004))
        coll.objects.link(ob)
    step = 0.5 * max(0.3, cfg.spread)
    nx, ny = int(16 / step), int(12 / step)
    for i in range(nx):
        for j in range(ny):
            p = Vector((-8 + (i + 0.5 + r.uniform(-0.4, 0.4)) * step, -6 + (j + 0.5 + r.uniform(-0.4, 0.4)) * step, 0))
            if any((p - c).length < rad for c, rad in keep_out):
                continue
            src = plants[(key, "B" if r.random() < (cfg.extra if plantgen.extra_of(key) else 0.5) else "A")]
            ob = bpy.data.objects.new(key + " (lawn)", src.data)
            ob.visible_shadow = False
            ob.location = FLOOR + p
            ob.rotation_euler = (0, 0, r.uniform(0, TAU))
            s = r.uniform(0.85, 1.15)
            ob.scale = (s, s, s)
            coll.objects.link(ob)


def frame_pair(scene, key, plants, stage, pitch, obs=None):
    """A camera framing both variants of a plant (or the objects obs), from the front and pitch degrees above."""
    obs = obs or [plants[(key, v)] for v in "AB"]
    lo = Vector((min(o.location.x - o.dimensions.x / 2 for o in obs), min(o.location.y for o in obs), 0))
    hi = Vector((max(o.location.x + o.dimensions.x / 2 for o in obs), max(o.location.y for o in obs), max(o.dimensions.z for o in obs)))
    centre = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, hi.z * 0.42))
    width, height = hi.x - lo.x, hi.z + (hi.y - lo.y) * math.sin(math.radians(pitch))
    a = math.radians(pitch)
    fov = 2 * math.atan(36 / 2 / 50)  # a 50 mm lens on a 36 mm sensor, across
    dist = max(width * 1.04, height * 1.25 * 1.3) / 2 / math.tan(fov / 2) + 0.3
    return camera("Camera " + key, centre + Vector((0, -math.cos(a), math.sin(a))) * dist, centre, stage)


def render(scene, cams, plants, rows, stage):
    os.makedirs(os.path.join(PREVIEWS, "tiles"), exist_ok=True)
    shots = [("Floor game", "floor_game_view.png", (1600, 900)), ("Floor close", "floor_close.png", (1600, 900))]
    files = {name: file for name, _keys, _pitch, file in ROWS}
    for name, (x0, x1, pitch, tall) in rows.items():  # as tall as the row's plants and signs need
        size = max(0.16, min(0.42, 0.55 * tall))
        high = 1.3 * tall * math.cos(math.radians(pitch)) + 1.6 * size + 0.15 * tall + 0.25
        shots.append((name, files[name], (3200, max(480, min(1400, round(3200 * high / (x1 - x0 + 1.0)))))))
    for key, file, res in shots:
        scene.camera = cams[key]
        scene.render.resolution_x, scene.render.resolution_y = res
        scene.render.filepath = os.path.join(PREVIEWS, file)
        bpy.ops.render.render(write_still=True)
        print("RENDERED", file)
    # both variants of each plant, everything else hidden, then a sheet of them
    info = {}
    scene.render.resolution_x, scene.render.resolution_y = 700, 560
    for key, fn, eng, swe, latin, width, card, kind in plantgen.SPECIES:
        keep = {plants[(key, v)].name for v in "AB"} | {"Ground", "Sun"}
        hidden = [o for o in scene.objects if o.type in ("MESH", "FONT") and o.name not in keep and not o.hide_render]
        for o in hidden:
            o.hide_render = True
        a, b = plants[(key, "A")], plants[(key, "B")]
        home = b.location.copy()
        lawn_obs, under = [], []
        if kind == "patch":  # a patch alone says little: a small lawn of them, as they're used, B among A, on its ground
            cfg = scene.plant_editor.plants[key]
            step = 0.5 * max(0.3, cfg.spread)
            r = random.Random(5)
            mat = plantgen.ground_material(key, plant_editor.as_cfg(cfg))
            if mat:
                me = bpy.data.meshes.new("Tile ground")
                me.from_pydata([(-0.6, -0.6, 0), (3.6, -0.6, 0), (3.6, 2.6, 0), (-0.6, 2.6, 0)], [], [(0, 1, 2, 3)])
                me.materials.append(mat)
                ground = bpy.data.objects.new("Tile ground", me)
                ground.location = a.location + Vector((0, 0, 0.004))
                stage.objects.link(ground)
                under.append(ground)
            for i in range(int(3.0 / step)):
                for j in range(int(2.0 / step)):
                    src = b if r.random() < (cfg.extra if plantgen.extra_of(key) else 0.5) else a
                    ob = bpy.data.objects.new(src.name + " (tile)", src.data)
                    ob.visible_shadow = False
                    ob.location = a.location + Vector(((i + r.uniform(-0.3, 0.3)) * step, (j + r.uniform(-0.3, 0.3)) * step, 0))
                    ob.rotation_euler = (0, 0, r.uniform(0, TAU))
                    s = r.uniform(0.85, 1.15)
                    ob.scale = (s, s, s)
                    stage.objects.link(ob)
                    lawn_obs.append(ob)
            for o in (a, b):
                o.hide_render = True
            bpy.context.view_layer.update()  # their sizes, for framing them
        elif kind != "bush":  # the low ones: B behind A and to its right, so the two fill the picture
            b.location = a.location + Vector((width * 0.75, width * 0.7, 0))
        cam = frame_pair(scene, key, plants, stage, 22 if kind == "bush" else 36, lawn_obs or None)
        scene.camera = cam
        scene.render.filepath = os.path.join(PREVIEWS, "tiles", key + ".png")
        bpy.ops.render.render(write_still=True)
        ob = plants[(key, "A")]
        me = ob.data
        info[key] = dict(name=eng, swedish=swe, latin=latin, kind=kind, height=round(ob.dimensions.z, 2),
                         across=round(max(ob.dimensions.x, ob.dimensions.y), 1), faces=len(me.polygons),
                         cards=sum(1 for q in me.polygons if q.material_index > 0))
        for o in hidden:
            o.hide_render = False
        b.location = home
        for o in lawn_obs + under:
            bpy.data.objects.remove(o, do_unlink=True)
        a.hide_render = b.hide_render = False
        bpy.data.objects.remove(cam, do_unlink=True)
    with open(os.path.join(PREVIEWS, "tiles", "info.json"), "w") as fh:
        json.dump(info, fh, indent=1)
    done = subprocess.run(["python3", os.path.join(HERE, "make_sheet.py")])  # Pillow: the system Python
    print("RENDERED portfolio.png" if done.returncode == 0 else "make_sheet.py failed; run it with python3")
    scene.camera = cams["Bushes"]


if __name__ == "__main__":
    scene, cams, plants, rows, stage, trees = build()
    for (key, variant), ob in sorted(plants.items()):
        me = ob.data
        print(f"PLANT {ob.name}: {len(me.polygons)} faces, {sum(1 for p in me.polygons if p.material_index > 0)} card faces, "
              f"{ob.dimensions.z:.2f} m tall, {max(ob.dimensions.x, ob.dimensions.y):.2f} m across")
    print("TREES linked:", [t.name for t in trees])
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, relative_remap=True)
    print("SAVED", BLEND)
    if "--no-render" not in ARGS:
        render(scene, cams, plants, rows, stage)
        bpy.ops.wm.save_as_mainfile(filepath=BLEND, relative_remap=True)
    plant_editor.unregister()
