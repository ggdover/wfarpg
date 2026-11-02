"""Low-poly characters from detailed ones (Blender, in the background): the user's plan for every character in the game
(1 November) is a detailed model, from Tripo3D for now, turned into the game's faceted low-poly style. This module
brings such a model in at its height and does the turning:

- import_tripo: a Tripo3D export (a .zip with its rigged .fbx and textures), extracted into build/, standing on the
  ground at its height, its armature and mesh with clean transforms.
- decimate: fewer triangles, by collapsing edges, mirrored, keeping the model's bone weights.
- retopo: a new, even mesh of quads over the model (a voxel remesh, then QuadriFlow), its weights carried over.
- Sampler and face_colours: each face one flat colour, the average of the model's texture under it, as the game's
  low-poly shapes are coloured (the "Col" attribute, linear; tools/build_demo.py writes it out as sRGB).
- reduce_colours: those colours brought down to a small palette, for a cleaner, hand-painted look.
- pose: turns bones about axes in the world, for test poses, whatever their rolls.
"""
import math
import os
import zipfile

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "build")


def select(*obs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]


def triangles(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def import_tripo(zip_path, name, height=1.8):
    """A Tripo3D export's armature and mesh, named name and name + "Rig", standing on the ground at height metres, with
    clean transforms (Tripo's are a hundredth scale on the armature and a turn on the mesh); its textures stay where
    the .zip is extracted to, build/<name>/."""
    out = os.path.join(BUILD, name)
    with zipfile.ZipFile(zip_path) as z:
        for i in z.infolist():  # nothing outside the folder
            if os.path.isabs(i.filename) or ".." in i.filename.replace("\\", "/").split("/"):
                raise ValueError(f"{zip_path}: unsafe path {i.filename}")
        if not os.path.isdir(out):
            z.extractall(out)
        fbx = next(f for f in z.namelist() if f.lower().endswith(".fbx"))
    before = set(bpy.data.objects)
    images = set(bpy.data.images)
    bpy.ops.import_scene.fbx(filepath=os.path.abspath(os.path.join(out, fbx)))
    new = [o for o in bpy.data.objects if o not in before]
    # the importer packs the textures the .fbx carries into the .blend (tens of MB): use the extracted files instead
    files = {f.lower(): os.path.join(d, f) for d, _, fs in os.walk(out) for f in fs}
    for img in set(bpy.data.images) - images:
        found = files.get(os.path.basename(img.filepath.replace("\\", "/")).lower())
        if found:
            img.filepath = os.path.abspath(found)
            if img.packed_file:
                img.unpack(method="USE_ORIGINAL")
    arm = next(o for o in new if o.type == "ARMATURE")
    mesh = next(o for o in new if o.type == "MESH")
    select(mesh)
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    select(mesh, arm)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    k = height / max(v.co.z for v in mesh.data.vertices)
    for o in (mesh, arm):
        o.scale = (k, k, k)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    mesh.parent = arm
    arm.name, mesh.name = name + "Rig", name
    arm.data.name, mesh.data.name = name + "Rig", name
    return arm, mesh


def copy(src, name, arm=None):
    """A copy of src with a mesh of its own, linked into src's collections, deformed by arm (src's if None)."""
    ob = src.copy()
    ob.data = src.data.copy()
    ob.name = ob.data.name = name
    for c in src.users_collection:
        c.objects.link(ob)
    for m in ob.modifiers:
        if m.type == "ARMATURE" and arm:
            m.object = arm
    return ob


def decimate(src, target, name):
    """A copy of src brought down to about target triangles by collapsing edges, mirrored across x so it stays
    symmetric. The bone weights come along, blended where vertices merge."""
    ob = copy(src, name)
    d = ob.modifiers.new("Decimate", "DECIMATE")
    d.decimate_type = "COLLAPSE"
    d.ratio = min(1.0, target / triangles(src))
    d.use_symmetry = True
    d.symmetry_axis = "X"
    select(ob)
    bpy.ops.object.modifier_move_to_index(modifier="Decimate", index=0)
    bpy.ops.object.modifier_apply(modifier="Decimate")
    ob.data.validate()  # collapsing leaves the odd doubled edge, which the glTF exporter warns of
    return ob


def retopo(src, faces, name, voxel=0.012):
    """A new mesh over src: a voxel remesh, which closes it into one shell (the shirt over the trousers and all), then
    QuadriFlow's even quads, about faces of them, mirrored, as a modeller would lay them out for animation. The bone
    weights are carried over from src, face by face."""
    ob = copy(src, name)
    ob.modifiers.clear()
    select(ob)
    ob.data.remesh_voxel_size = voxel
    ob.data.remesh_voxel_adaptivity = 0.0
    bpy.ops.object.voxel_remesh()
    bpy.ops.object.mode_set(mode="EDIT")  # QuadriFlow wants it whole, its faces all facing out
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.0005)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.quadriflow_remesh(target_faces=faces, use_mesh_symmetry=True, seed=0)
    transfer_weights(ob, src)
    return ob


def transfer_weights(dst, src):
    """dst's bone weights from src's, by the nearest face, and the same armature deforming it."""
    dst.vertex_groups.clear()
    for g in src.vertex_groups:
        dst.vertex_groups.new(name=g.name)
    dt = dst.modifiers.new("Weights", "DATA_TRANSFER")
    dt.object = src
    dt.use_vert_data = True
    dt.data_types_verts = {"VGROUP_WEIGHTS"}
    dt.vert_mapping = "POLYINTERP_NEAREST"
    dt.layers_vgroup_select_src = "ALL"
    dt.layers_vgroup_select_dst = "NAME"
    select(dst)
    bpy.ops.object.modifier_apply(modifier="Weights")
    arm = next((m.object for m in src.modifiers if m.type == "ARMATURE"), None)
    if arm and not any(m.type == "ARMATURE" for m in dst.modifiers):
        dst.modifiers.new("Armature", "ARMATURE").object = arm


class Sampler:
    """The colour of a model's texture at points near its surface: the nearest point on it, and the base colour there
    (linear). The model in its rest pose."""

    def __init__(self, ob):
        me = ob.data
        node = next(n for m in me.materials for n in m.node_tree.nodes
                    if n.type == "TEX_IMAGE" and n.image and "basecolor" in n.image.filepath.lower())
        img = node.image
        w, h = img.size
        px = np.array(img.pixels[:], np.float32).reshape(h, w, 4)[:, :, :3]
        # the PNG's values are sRGB: linear, as colours are kept
        self.pix = np.where(px <= 0.04045, px / 12.92, ((px + 0.055) / 1.055) ** 2.4)
        self.size = (w, h)
        me.calc_loop_triangles()
        mw = ob.matrix_world
        co = [mw @ v.co for v in me.vertices]
        uv = me.uv_layers.active.data
        self.tri = [(co[t.vertices[0]], co[t.vertices[1]], co[t.vertices[2]]) for t in me.loop_triangles]
        self.uv = [(Vector(uv[t.loops[0]].uv), Vector(uv[t.loops[1]].uv), Vector(uv[t.loops[2]].uv)) for t in me.loop_triangles]
        self.bvh = BVHTree.FromPolygons(co, [t.vertices[:] for t in me.loop_triangles])

    def at(self, p):
        loc, _n, i, _d = self.bvh.find_nearest(p)
        a, b, c = self.tri[i]
        v0, v1, v2 = b - a, c - a, loc - a
        d00, d01, d11, d20, d21 = v0.dot(v0), v0.dot(v1), v1.dot(v1), v2.dot(v0), v2.dot(v1)
        den = d00 * d11 - d01 * d01 or 1e-12
        v = (d11 * d20 - d01 * d21) / den
        w = (d00 * d21 - d01 * d20) / den
        ua, ub, uc = self.uv[i]
        uv = ua * (1 - v - w) + ub * v + uc * w
        x = min(self.size[0] - 1, max(0, int(uv.x % 1.0 * self.size[0])))
        y = min(self.size[1] - 1, max(0, int(uv.y % 1.0 * self.size[1])))
        return self.pix[y, x]


def face_colours(ob, sampler, inset=0.6):
    """Every face of ob one flat colour: the average of sampler's texture at its middle and at points toward its
    corners. Flat shaded, coloured by the "Col" attribute; the faces are taken in ob's rest pose."""
    me = ob.data
    mw = ob.matrix_world
    cols = np.zeros((len(me.polygons), 3), np.float32)
    for f in me.polygons:
        c = mw @ f.center
        pts = [c] + [c.lerp(mw @ me.vertices[i].co, inset) for i in f.vertices]
        cols[f.index] = np.mean([sampler.at(p) for p in pts], axis=0)
    set_face_colours(ob, cols)
    return cols


def set_face_colours(ob, cols):
    """Writes one colour per face (linear rgb rows) into ob's "Col" attribute, every corner of a face alike, and
    shades it flat."""
    me = ob.data
    for a in list(me.color_attributes):
        me.color_attributes.remove(a)
    col = me.color_attributes.new("Col", "FLOAT_COLOR", "CORNER")
    data = np.ones((len(me.loops), 4), np.float32)
    starts = np.zeros(len(me.polygons), np.int64)
    totals = np.zeros(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_start", starts)
    me.polygons.foreach_get("loop_total", totals)
    face_of = np.repeat(np.arange(len(me.polygons)), totals)
    data[:, :3] = np.asarray(cols)[face_of]
    col.data.foreach_set("color", data.ravel())
    me.color_attributes.active_color = col
    me.polygons.foreach_set("use_smooth", [False] * len(me.polygons))


def blend_colours(ob, cols, times=3):
    """Each face's colour blended with its neighbours' (those sharing an edge), times over: the texture's stains and
    seams evened out into patches, for meshes whose faces are all one size, where every face showing its own sample
    looks like a mosaic."""
    me = ob.data
    faces_of = {}
    for f in me.polygons:
        for k in f.edge_keys:
            faces_of.setdefault(k, []).append(f.index)
    near = [set() for _ in me.polygons]
    for fs in faces_of.values():
        for a in fs:
            near[a].update(x for x in fs if x != a)
    c = np.asarray(cols, np.float32)
    for _ in range(times):
        c = np.array([(c[i] * 2 + c[list(n)].sum(axis=0)) / (2 + len(n)) for i, n in enumerate(near)], np.float32)
    return c


def reduce_colours(cols, n, seed=1, weights=None):
    """The face colours brought down to n of them, by k-means in a perceptual space (cube roots of linear rgb, near
    enough to lightness), so the steps between them look even: a cleaner, hand-painted look than the texture's every
    stain. weights: each face's area, so big faces count for more."""
    x = np.cbrt(np.clip(np.asarray(cols, np.float64), 0, None))
    wts = np.ones(len(x)) if weights is None else np.asarray(weights, np.float64)
    rng = np.random.default_rng(seed)
    centres = x[rng.choice(len(x), n, replace=False, p=wts / wts.sum())]
    for _ in range(40):
        d = ((x[:, None, :] - centres[None, :, :]) ** 2).sum(axis=2)
        lab = d.argmin(axis=1)
        for k in range(n):
            m = lab == k
            if m.any():
                centres[k] = np.average(x[m], axis=0, weights=wts[m])
    return (centres ** 3)[lab].astype(np.float32)


def turn(arm, bone, axis, degrees):
    """Turns a pose bone of arm about an axis in the world (through its head), on top of its pose: for test poses,
    whatever way the bone was rolled when it was rigged."""
    pb = arm.pose.bones[bone]
    bpy.context.view_layer.update()
    m = arm.matrix_world @ pb.matrix
    r = Matrix.Translation(m.translation) @ Matrix.Rotation(math.radians(degrees), 4, Vector(axis)) \
        @ Matrix.Translation(-m.translation)
    pb.matrix = arm.matrix_world.inverted() @ r @ m
    bpy.context.view_layer.update()


def pose(arm, steps):
    """Puts arm in a pose: steps are [bone, world axis, degrees], parents before their children."""
    for bone, axis, degrees in steps:
        if bone in arm.pose.bones:
            turn(arm, bone, axis, degrees)
