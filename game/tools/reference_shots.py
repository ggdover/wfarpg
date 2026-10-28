"""Renders the play demo's area the way the mockups are rendered, in Blender, for comparing the game with them.

    blender -b --factory-startup -P reference_shots.py -- <out.png> <x,z,yaw,pitch,distance[,facing]> [old|new] [samples]
        [--area=name]

The pose is the demo's --pose: the hero's Godot X and Z, then the camera's yaw, pitch and distance in the mockups'
terms (scripts/camera_rig.gd). It builds the area (storskogen unless --area names another of tools/areas) from its
layout, data/areas/<area>.json, with the mockups' kit and lighting
(setup_world_act in mockups/act1_shots.py), the ground from the ground shader, and the hero as a grey box, then
renders it with Eevee like the mockups. Trees between the camera and the hero are hidden, as in the mockups.
"""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_demo as B  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
B.use_area(next((a[7:] for a in argv if a.startswith("--area=")), "storskogen"))
D = B.D
argv = [a for a in argv if not a.startswith("--area=")]
OUT, POSE = os.path.abspath(argv[0]), [float(v) for v in argv[1].split(",")]  # Blender on Windows saves a relative path under C:\
WHICH = argv[2] if len(argv) > 2 else "old"
SAMPLES = int(argv[3]) if len(argv) > 3 else 48
RADIUS = 160.0  # only what stands this close to the hero goes into the scene

kit = B.load_kit()
hx, hy = POSE[0], -POSE[1]  # Blender's axes
hz = float(D.height(np.array([hx]), np.array([hy]))[0])
kit["setup_render"]()
kit["setup_world_act"]("day", hx, hy)
if os.environ.get("NOBUMP"):
    for n in kit["MAT_GROUND"].node_tree.nodes:
        if n.type == "BUMP":
            n.inputs["Strength"].default_value = 0.0
if os.environ.get("NOHAZE"):
    bpy.data.objects.remove(bpy.data.objects["Haze"])
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = 1600, 900
sc.eevee.taa_render_samples = SAMPLES

B.extend_ground_more(kit)  # the other areas' ground layers
B.ground_mesh("Terrain", D.BAKE, B.GRID, kit)
far = B.ground_mesh("OuterGround", (-B.FAR, B.FAR, -B.FAR, B.FAR), B.FAR_GRID, kit)
far.location.z = -0.06

meshes = {}
for items in B.kit_groups(kit).values():
    for name, make in items:
        meshes[name] = make
if WHICH == "new":
    meshes.update({k: (lambda m=m: m) for k, m in B.tree_meshes().items()})
built = {}


def mesh(name):
    if name not in built:
        built[name] = meshes[name]()
    return built[name]


def place(name, gx, gy, gz, rot, s):
    x, y, z = gx, -gz, gy
    if math.hypot(x - hx, y - hy) > RADIUS:
        return None
    ob = bpy.data.objects.new(name, mesh(name))
    ob.location = (x, y, z)
    ob.rotation_euler = (0, 0, rot)
    ob.scale = (s, s, s)
    sc.collection.objects.link(ob)
    return ob


with open(B.LAYOUT_PATH, encoding="utf-8") as fh:
    layout = json.load(fh)
for t in layout["trees"]:
    ob = place(t[WHICH], *t["p"], t["r"], t["s_" + WHICH])
    if ob:
        kit["TREES"].append(ob)
for name, items in layout["props"].items():
    for gx, gy, gz, rot, s in items:
        place(name, gx, gy, gz, rot, s)

# the hero, the grey box of the game
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(hx, hy, hz + 0.9))
hero = bpy.context.active_object
hero.scale = (0.6, 0.38, 1.8)
m = bpy.data.materials.new("Hero")
m.use_nodes = True
m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = kit["lin"]("#8F8F8C")
hero.data.materials.append(m)
if len(POSE) > 5:
    hero.rotation_euler.z = math.radians(POSE[5]) - math.pi / 2

cam = kit["orbit_camera"]((hx, hy, hz + 1.4), POSE[2], POSE[3], POSE[4])
kit["cull_act"](cam, [Vector((hx, hy, hz + 1.0))], wide=False)
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("REFERENCE", OUT)
