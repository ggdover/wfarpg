"""Hero portfolio: the player character, as the user's Tripo3D models and as low-poly versions of them, to judge
(1 November). Builds hero_portfolio.blend, renders previews/, and exports the low-poly ones, standing as made, on
their skeletons, to build/heroes.glb, for game/scripts/dev/heroes.gd to stand them in the game.

    blender -b --factory-startup -P make_heroes.py                  all of it
    blender -b --factory-startup -P make_heroes.py -- --no-render   no renders

The Tripo3D exports are ref_model/default/*_with_rig.zip (a rigged .fbx with its textures each); they're extracted into
build/ (not kept in git), where the .blend finds their textures. The low-poly versions are made from the 20k model
(lowpoly.py) or built from scratch after it (herogen.py), all 1.8 m tall on the 20k model's skeleton, each on a copy
of it, so they can all be posed and animated alike. The first row stands as the models were made, arms out; the
second, behind it, takes a step, to see how each bends at the shoulders, elbows, hips and knees.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import herogen  # noqa: E402
import lowpoly  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
TRIPO = os.path.join(ROOT, "ref_model", "default")
PREVIEWS = os.path.join(HERE, "previews")
BLEND = os.path.join(HERE, "hero_portfolio.blend")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SPACING = 1.25  # metres between the figures in a row
WALK_ROW = 3.0  # metres behind the first row, the walking one
# a step, the left leg forward and the right arm with it: [bone (the 20k model's names), axis in the world, degrees]
WALK = [("upperarm_l", (0, 1, 0), 22), ("upperarm_l", (1, 0, 0), 16), ("lowerarm_l", (1, 0, 0), -12),
        ("upperarm_r", (0, 1, 0), -22), ("upperarm_r", (1, 0, 0), -18), ("lowerarm_r", (1, 0, 0), -26),
        ("thigh_l", (1, 0, 0), -24), ("calf_l", (1, 0, 0), 12), ("thigh_r", (1, 0, 0), 18), ("calf_r", (1, 0, 0), 32)]
MIXAMO = {"upperarm_l": "mixamorig:LeftArm", "lowerarm_l": "mixamorig:LeftForeArm", "upperarm_r": "mixamorig:RightArm",
          "lowerarm_r": "mixamorig:RightForeArm", "thigh_l": "mixamorig:LeftUpLeg", "calf_l": "mixamorig:LeftLeg",
          "thigh_r": "mixamorig:RightUpLeg", "calf_r": "mixamorig:RightLeg"}


def collection(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


def move_to(ob, coll):
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    coll.objects.link(ob)


def flat_material():
    """The faces' own colours (the "Col" attribute), matte, as the game's low-poly material shows them."""
    m = bpy.data.materials.new("Faceted")
    m.use_nodes = True
    nodes, links = m.node_tree.nodes, m.node_tree.links
    attr = nodes.new("ShaderNodeAttribute")
    attr.attribute_name = "Col"
    bsdf = nodes["Principled BSDF"]
    links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.88
    bsdf.inputs["Specular IOR Level"].default_value = 0.25
    return m


def plain_material(name, hexcol):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = herogen.lin(hexcol) + (1.0,)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.95
    return m


def matte(ob):
    """The Tripo model's own material, but matte: as imported, its metal and roughness maps make it look wet."""
    for m in ob.data.materials:
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        for key in ("Metallic", "Roughness", "Specular IOR Level"):
            for link in list(bsdf.inputs[key].links):
                m.node_tree.links.remove(link)
        bsdf.inputs["Metallic"].default_value = 0.0
        bsdf.inputs["Roughness"].default_value = 0.85
        bsdf.inputs["Specular IOR Level"].default_value = 0.3


def on_rig(ob, rig, coll):
    """ob, deformed by rig and parented to it, in coll."""
    move_to(ob, coll)
    ob.parent = rig
    ob.matrix_parent_inverse.identity()
    for m in ob.modifiers:
        if m.type == "ARMATURE":
            m.object = rig


def label(text, loc, coll, mat, size=0.085):
    cu = bpy.data.curves.new("Label", "FONT")
    cu.body = text
    cu.size = size
    cu.align_x = "CENTER"
    cu.align_y = "TOP"
    ob = bpy.data.objects.new("Label " + text.split("\n")[0], cu)
    ob.location = loc
    ob.rotation_euler = (math.radians(90), 0, 0)
    ob.data.materials.append(mat)
    coll.objects.link(ob)
    return ob


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    heroes, walking, stage = collection("Heroes"), collection("Walking"), collection("Portfolio")
    arm20, src20 = lowpoly.import_tripo(os.path.join(TRIPO, "20k_triangle_with_rig.zip"), "Tripo20k")
    arm5, src5 = lowpoly.import_tripo(os.path.join(TRIPO, "5k_triangle_with_rig.zip"), "Tripo5k")
    for ob in (src20, src5):
        matte(ob)
    sampler = lowpoly.Sampler(src20)
    flat = flat_material()

    def faceted(ob):
        cols = lowpoly.face_colours(ob, sampler)
        ob.data.materials.clear()
        ob.data.materials.append(flat)
        return cols

    figures = [(arm20, src20, "Tripo3D 20k, as made"), (arm5, src5, "Tripo3D 5k, as made")]
    for target in (3000, 1500, 800):
        ob = lowpoly.decimate(src20, target, f"Faceted{target}")
        faceted(ob)
        figures.append((None, ob, f"Faceted {target}"))
    ob = lowpoly.decimate(src20, 1500, "Painted1500")
    cols = faceted(ob)
    lowpoly.set_face_colours(ob, lowpoly.reduce_colours(cols, 12, weights=[p.area for p in ob.data.polygons]))
    figures.append((None, ob, "Painted 1500, 12 colours"))
    ob = lowpoly.retopo(src20, 1600, "Retopo")  # fewer, and QuadriFlow loses a forearm
    cols = lowpoly.blend_colours(ob, faceted(ob))  # its quads are all one size: a mosaic, with every face its own
    lowpoly.set_face_colours(ob, lowpoly.reduce_colours(cols, 10, weights=[p.area for p in ob.data.polygons]))
    figures.append((None, ob, "Retopology: even quads"))
    for name, text, gear in (("Wanderer", "Our own: wanderer", False), ("WandererGear", "Our own: light gear", True)):
        ob = herogen.build(arm20, name, heroes, flat, gear=gear)
        lowpoly.transfer_weights(ob, src20)
        figures.append((None, ob, text))

    ink = plain_material("Ink", "#2E2A24")
    first_x = -(len(figures) - 1) * SPACING / 2
    rows = []
    for i, (rig, ob, text) in enumerate(figures):
        if rig is None:  # a copy of the 20k model's skeleton of its own
            rig = arm20.copy()
            rig.name = ob.name + "Rig"
        move_to(rig, heroes)
        on_rig(ob, rig, heroes)
        rig.location.x = first_x + i * SPACING
        tris = lowpoly.triangles(ob)
        label(f"{text}\n{tris:,} triangles", (rig.location.x, -0.45, -0.08), stage, ink)
        rows.append((rig, ob, text, tris))
    # the second row: the same meshes on copies of their skeletons, taking a step
    walkers = []
    for rig, ob, text, tris in rows:
        r2 = rig.copy()
        r2.name = rig.name + "Walk"
        walking.objects.link(r2)
        o2 = ob.copy()  # the same mesh
        o2.name = ob.name + "Walk"
        on_rig(o2, r2, walking)
        r2.location = (rig.location.x, WALK_ROW, 0.0)
        bpy.context.view_layer.update()
        steps = [(MIXAMO.get(b, b) if r2.data == arm5.data else b, a, d) for b, a, d in WALK]
        lowpoly.pose(r2, steps)
        walkers.append((r2, o2))
        label(f"{text}\n{tris:,} triangles", (rig.location.x, WALK_ROW - 0.45, -0.08), stage, ink)

    # the stage: a ground for the game's view, light, cameras
    ground = bpy.data.objects.new("Ground", bpy.data.meshes.new("Ground"))
    s = 40.0
    ground.data.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    ground.data.materials.append(plain_material("Grass", "#5D6B3E"))
    stage.objects.link(ground)
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 48
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.42, 0.45, 0.5, 1.0)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.9
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 3.3
    sun.data.angle = math.radians(2)
    sun.rotation_euler = (math.radians(48), 0, math.radians(-32))
    stage.objects.link(sun)
    cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    stage.objects.link(cam)
    scene.camera = cam
    width = len(figures) * SPACING + 0.3
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = width
    cam.location = (0.0, -12.0, 0.72)
    cam.rotation_euler = (math.radians(90), 0, 0)
    for area in (a for w in bpy.data.screens for a in w.areas if a.type == "VIEW_3D"):
        for sp in area.spaces:
            if sp.type == "VIEW_3D":
                sp.shading.type = "MATERIAL"
    return scene, cam, rows, walkers, ground, stage


def render(scene, cam, rows, walkers, ground, stage):
    os.makedirs(PREVIEWS, exist_ok=True)
    width = len(rows) * SPACING + 0.3
    labels = [o for o in stage.objects if o.type == "FONT"]

    def shoot(name, res, front_row, back_row, show_ground, turn=0.0, show_labels=True):
        for rig, ob, *_ in rows:
            rig.hide_render = ob.hide_render = not front_row
            rig.rotation_euler.z = math.radians(turn)
        for rig, ob in walkers:
            rig.hide_render = ob.hide_render = not back_row
            rig.rotation_euler.z = math.radians(turn)
        ground.hide_render = not show_ground
        for lab in labels:
            lab.hide_render = not show_labels or (lab.location.y > 1.0) != back_row
        scene.render.resolution_x, scene.render.resolution_y = res
        scene.render.filepath = os.path.join(PREVIEWS, name)
        bpy.ops.render.render(write_still=True)
        print("rendered", name)

    res = (3000, int(3000 * 2.55 / width))
    cam.data.type = "ORTHO"
    cam.location = (0.0, -12.0, 0.72)
    cam.rotation_euler = (math.radians(90), 0, 0)
    shoot("heroes_front.png", res, True, False, False)
    shoot("heroes_three_quarter.png", res, True, False, False, turn=35)
    shoot("heroes_back.png", res, True, False, False, turn=180)
    cam.location = (0.0, WALK_ROW - 12.0, 0.72)
    shoot("heroes_walking.png", res, False, True, False, turn=28)
    # the game's view: high, looking down at 55 degrees from 16 m, on grass
    cam.data.type = "PERSP"
    cam.data.lens = 50
    a = math.radians(55)
    cam.location = (0.0, WALK_ROW - 16 * math.cos(a), 1.0 + 16 * math.sin(a))
    cam.rotation_euler = (math.radians(90) - a, 0, 0)
    shoot("heroes_game_view.png", (2400, 1350), False, True, True, show_labels=False)
    # back as it was, for the .blend
    for rig, ob, *_ in rows:
        rig.hide_render = ob.hide_render = False
        rig.rotation_euler.z = 0.0
    for rig, ob in walkers:
        rig.hide_render = ob.hide_render = False
        rig.rotation_euler.z = 0.0
    for lab in labels:
        lab.hide_render = False
    ground.hide_render = False
    cam.data.type = "ORTHO"
    cam.location = (0.0, -12.0, 0.72)
    cam.rotation_euler = (math.radians(90), 0, 0)


def export_glb(rows, path):
    """The low-poly figures (not the Tripo models as made), each on its skeleton, standing as made, into one .glb, as
    the game reads models (tools/build_demo.py): the faces' colours sRGB-encoded in COLOR_0, which the game's low-poly
    shader decodes, and a second UV map of 1s for its ambient occlusion (none baked yet). Exported from a copy of the
    .blend's data, which then goes."""
    keep = []
    for rig, ob, text, tris in rows:
        if ob.name.startswith("Tripo"):
            continue
        game_colours(ob.data)
        keep += [rig, ob]
    lowpoly.select(*keep)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_yup=True,
                              export_texcoords=True, export_normals=True, export_skins=True, export_animations=False,
                              export_materials="NONE", export_vertex_color="NAME", export_vertex_color_name="ColSRGB",
                              export_all_vertex_colors=False, export_cameras=False, export_lights=False)
    for ob in keep[1::2]:  # the .blend as it was
        drop_game_colours(ob.data)
    print("exported", path)


def game_colours(me):
    """The mesh's "Col" colours (linear) sRGB-encoded into "ColSRGB", which the exporter writes as COLOR_0, and the
    second UV map of 1s ("AO") the game's low-poly shader reads its ambient occlusion from."""
    src = me.color_attributes["Col"]
    rgb = [0.0] * (len(src.data) * 4)
    src.data.foreach_get("color", rgb)
    enc = [c if i % 4 == 3 else (c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055)
           for i, c in enumerate(min(max(v, 0.0), 1.0) for v in rgb)]
    dst = me.color_attributes.get("ColSRGB") or me.color_attributes.new("ColSRGB", "FLOAT_COLOR", "CORNER")
    dst.data.foreach_set("color", enc)
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    ao = me.uv_layers.get("AO") or me.uv_layers.new(name="AO")
    ao.data.foreach_set("uv", [1.0] * (len(me.loops) * 2))


def drop_game_colours(me):
    me.color_attributes.remove(me.color_attributes["ColSRGB"])
    me.uv_layers.remove(me.uv_layers["AO"])


if __name__ == "__main__":
    scene, cam, rows, walkers, ground, stage = build()
    for rig, ob, text, tris in rows:
        print(f"{ob.name:14s} {tris:6d} triangles, {len(ob.data.vertices):6d} vertices, {len(ob.vertex_groups)} bone groups: {text}")
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, relative_remap=True)
    export_glb(rows, os.path.join(lowpoly.BUILD, "heroes.glb"))
    if "--no-render" not in ARGS:
        render(scene, cam, rows, walkers, ground, stage)
        bpy.ops.wm.save_as_mainfile(filepath=BLEND, relative_remap=True)
