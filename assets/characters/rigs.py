"""Rig variants (Blender): seven ways of binding a low-poly hero's mesh to the skeleton, for the run portfolio
(2 November). Every one keeps at most four bones on a vertex, as the game takes them.

- tripo: the weights Tripo3D's auto-rig gave the 20k model, carried over as the meshes were made.
- smooth: those weights smoothed across the mesh, so the bends spread wider and softer.
- heat: Blender's own weights, worked out by heat from bones that run joint to joint, on a closed copy of the 20k
  model, and carried over.
- rigid: every vertex on one bone only, as old games' models were: sharp folds at the joints, nothing between.
- helpers: bone heat's weights, with helper bones at the hips, knees, shoulders and elbows that turn half as far as
  the joint, carrying the vertices round the bend, so a bent knee or elbow keeps its thickness.
- cloth: bone heat's weights, with four cloth bones in the tunic's skirt (front, back, sides) that the thighs push and
  the hem swings on.
- corrective: bone heat's weights, with corrective shapes at the knees, hips, elbows and shoulders: at a few bends of
  each joint, the difference between plain skinning, which thins a bend, and Blender's volume-keeping (dual
  quaternion) skinning, which the game can't do, made into a shape the run turns on as far as the joint bends.
The last three were first made on the smoothed weights; on bone heat's, which spread each bend wider, they stretch the
skin less, and the corrective shapes no longer swell Faceted 800's knees and elbows.
"""
import math

import bpy
from mathutils import Matrix, Vector

import runs

VARIANTS = [
    ("tripo", "Tripo weights", "The weights Tripo3D's auto-rig gave the model, as they came."),
    ("smooth", "Smoothed", "Tripo's weights smoothed across the mesh: softer, wider bends."),
    ("heat", "Bone heat", "Blender's own automatic weights, from bones running joint to joint."),
    ("rigid", "Rigid", "Each vertex on one bone: crisp folds at the joints, like early 3D games."),
    ("helpers", "Helper joints", "Bone heat's weights plus half-turning helper bones at the hips, knees, shoulders "
     "and elbows, which keep the bends from pinching."),
    ("cloth", "Cloth bones", "Bone heat's weights plus four cloth bones in the tunic's skirt: the knees push it out "
     "and the hem swings with every step."),
    ("corrective", "Corrective shapes", "Bone heat's weights plus shapes that keep the knees, hips, elbows and "
     "shoulders full as they bend, made from volume-keeping skinning and played with each run."),
]
TWIST = {"thigh": "thigh_twist_01", "calf": "calf_twist_01", "upperarm": "upperarm_twist_01",
         "lowerarm": "lowerarm_twist_01"}
# helper bone: (joint bone, the bones on the joint's near side, on its far side, the helper's parent)
HELPERS = {
    "knee": ("calf", ("thigh", "thigh_twist_01"), ("calf", "calf_twist_01"), "thigh"),
    "elbow": ("lowerarm", ("upperarm", "upperarm_twist_01"), ("lowerarm", "lowerarm_twist_01"), "upperarm"),
    "hip": ("thigh", ("pelvis",), ("thigh", "thigh_twist_01"), "pelvis"),
    "shoulder": ("upperarm", ("clavicle",), ("upperarm", "upperarm_twist_01"), "clavicle"),
}


# cloth bones in the tunic's skirt: name -> which way round the body they hang (x, y)
SKIRT = {"skirt_f": (0.0, -1.0), "skirt_b": (0.0, 1.0), "skirt_l": (1.0, 0.0), "skirt_r": (-1.0, 0.0)}
BELT, HEM = 0.99, 0.78  # m: the skirt hangs from the belt to the hem


# corrective shapes: name -> (the bone that bends, the bone it bends from, which way it bends from its rest (the
# figures face -Y: forward or back), the angles (degrees) a shape is made at; between them, and from none, the shapes
# blend)
CORRECTIVES = {
    "knee": ("calf", "thigh", (0.0, 1.0, 0.0), (75.0, 150.0)),
    "hip": ("thigh", "pelvis", (0.0, -1.0, 0.0), (50.0, 100.0)),
    "elbow": ("lowerarm", "upperarm", (0.0, -1.0, 0.0), (60.0, 120.0)),
    "shoulder_fwd": ("upperarm", "clavicle", (0.0, -1.0, 0.0), (60.0,)),
    "shoulder_back": ("upperarm", "clavicle", (0.0, 1.0, 0.0), (60.0,)),
}


def side_name(base, s):
    return base if base == "pelvis" else f"{base}_{s}"


def read(ob):
    """[{group name: weight}] per vertex."""
    names = {g.index: g.name for g in ob.vertex_groups}
    return [{names[g.group]: g.weight for g in v.groups if g.weight > 0.0} for v in ob.data.vertices]


def write(ob, W):
    """Puts weights W ([{group name: weight}]) in place of ob's, making groups as needed."""
    for vg in ob.vertex_groups:
        vg.remove(range(len(ob.data.vertices)))
    for i, w in enumerate(W):
        for name, x in w.items():
            vg = ob.vertex_groups.get(name) or ob.vertex_groups.new(name=name)
            vg.add([i], x, "REPLACE")


def tidy(W, most=4, least=0.01):
    """At most `most` bones a vertex, none under `least`, adding up to 1."""
    out = []
    for w in W:
        top = sorted(w.items(), key=lambda kv: -kv[1])[:most]
        top = [(n, x) for n, x in top if x >= least] or top[:1]
        s = sum(x for _, x in top)
        out.append({n: x / s for n, x in top})
    return out


def neighbours(ob):
    nb = [set() for _ in ob.data.vertices]
    for e in ob.data.edges:
        a, b = e.vertices
        nb[a].add(b)
        nb[b].add(a)
    return nb


def smoothed(ob, W, times=4, amount=0.5):
    """W smoothed across the mesh's edges, times over: each vertex part way to the mean of its neighbours."""
    nb = neighbours(ob)
    for _ in range(times):
        new = []
        for i, w in enumerate(W):
            if not nb[i]:
                new.append(dict(w))
                continue
            mean = {}
            for j in nb[i]:
                for n, x in W[j].items():
                    mean[n] = mean.get(n, 0.0) + x / len(nb[i])
            keys = set(w) | set(mean)
            new.append({n: (1 - amount) * w.get(n, 0.0) + amount * mean.get(n, 0.0) for n in keys})
        W = new
    return tidy(W, most=8, least=0.001)


def rigid(W):
    """Each vertex on its strongest bone only (a bone and its twist bone count as one)."""
    out = []
    for w in W:
        merged = {}
        for n, x in w.items():
            base = n.replace("_twist_01", "")
            merged[base] = merged.get(base, 0.0) + x
        out.append({max(merged, key=merged.get): 1.0})
    return out


def heat_weights(source, rig, voxel=0.012):
    """Weights by bone heat on a closed copy of source (the detailed model), from a skeleton whose bones run from
    joint to joint (Tripo's stop short of the next joint): {vertex of the copy: weights}, and the copy."""
    proxy = source.copy()
    proxy.data = source.data.copy()
    proxy.name = "HeatProxy"
    proxy.parent = None
    proxy.matrix_world = rig.matrix_world.inverted() @ source.matrix_world
    proxy.modifiers.clear()
    proxy.vertex_groups.clear()
    bpy.context.scene.collection.objects.link(proxy)
    rem = proxy.modifiers.new("Remesh", "REMESH")
    rem.mode = "VOXEL"
    rem.voxel_size = voxel
    dec = proxy.modifiers.new("Decimate", "DECIMATE")
    dec.ratio = 0.35
    for m in ("Remesh", "Decimate"):
        bpy.context.view_layer.objects.active = proxy
        bpy.ops.object.modifier_apply(modifier=m)
    # the joint-to-joint skeleton, without the twist bones (their parents take their share)
    arm = bpy.data.armatures.new("HeatBones")
    tmp = bpy.data.objects.new("HeatBones", arm)
    bpy.context.scene.collection.objects.link(tmp)
    bpy.context.view_layer.objects.active = tmp
    bpy.ops.object.mode_set(mode="EDIT")
    rest = {b.name: b for b in rig.data.bones}
    made = {}
    for b in rig.data.bones:
        if "twist" in b.name or b.name == "root":
            continue
        kids = [c for c in b.children if "twist" not in c.name]
        main = {"pelvis": "spine_01", "spine_03": "neck_01", "hand_l": "middle_01_l", "hand_r": "middle_01_r"}
        tail = None
        if b.name in main:
            tail = rest[main[b.name]].head_local
        elif len(kids) == 1:
            tail = kids[0].head_local
        if tail is None or (tail - b.head_local).length < 0.01:
            tail = b.tail_local
        eb = arm.edit_bones.new(b.name)
        eb.head, eb.tail = b.head_local, tail
        made[b.name] = eb
    for b in rig.data.bones:
        if b.name in made and b.parent:
            p = b.parent.name.replace("_twist_01", "")
            if p in made:
                made[b.name].parent = made[p]
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    proxy.select_set(True)
    tmp.select_set(True)
    bpy.context.view_layer.objects.active = tmp
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    W = read(proxy)
    bpy.data.objects.remove(tmp)
    bpy.data.armatures.remove(arm)
    print(f"heat: proxy {len(proxy.data.vertices)} vertices, {sum(1 for w in W if not w)} without weights")
    return proxy


def transferred(dst, proxy):
    """dst's weights taken from proxy's, by the nearest face, and tidied."""
    dst.vertex_groups.clear()
    for g in proxy.vertex_groups:
        dst.vertex_groups.new(name=g.name)
    m = dst.modifiers.new("Weights", "DATA_TRANSFER")
    m.object = proxy
    m.use_object_transform = False  # both in the armature's space, wherever the figures stand
    m.use_vert_data = True
    m.data_types_verts = {"VGROUP_WEIGHTS"}
    m.vert_mapping = "POLYINTERP_NEAREST"
    m.layers_vgroup_select_src = "ALL"
    m.layers_vgroup_select_dst = "NAME"
    bpy.context.view_layer.objects.active = dst
    bpy.ops.object.modifier_move_to_index(modifier="Weights", index=0)
    bpy.ops.object.modifier_apply(modifier="Weights")
    return tidy(read(dst))


def add_helpers(rig):
    """Helper bones (HELPERS) on rig's armature, at each joint, on the joint's parent: names like knee_l."""
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    eb = rig.data.edit_bones
    for s in "lr":
        for name, (joint, _near, _far, parent) in HELPERS.items():
            j = eb[side_name(joint, s)]
            h = eb.new(f"{name}_{s}")
            h.head = j.head.copy()
            h.tail = j.head + (j.tail - j.head).normalized() * 0.06
            h.roll = j.roll
            h.parent = eb[side_name(parent, s)]
            h.use_deform = True
    bpy.ops.object.mode_set(mode="OBJECT")


def with_helpers(W):
    """Weights with each joint's blend between its two sides moved onto its helper: a vertex half on each side goes
    wholly to the helper, which turns half as far, so it stays at the joint's surface instead of cutting the corner."""
    out = []
    for w in W:
        w = dict(w)
        for s in "lr":
            for name in ("knee", "elbow", "hip", "shoulder"):
                _joint, near, far, _parent = HELPERS[name]
                near = [side_name(n, s) for n in near]
                far = [side_name(n, s) for n in far]
                a = sum(w.get(n, 0.0) for n in near)
                b = sum(w.get(n, 0.0) for n in far)
                m = min(a, b)
                if m < 0.02:
                    continue
                for group, total in ((near, a), (far, b)):
                    for n in group:
                        if n in w:
                            w[n] -= m * w[n] / total
                w[f"{name}_{s}"] = w.get(f"{name}_{s}", 0.0) + 2 * m
        out.append(w)
    return tidy(out)


def add_skirt(rig):
    """The cloth bones (SKIRT) on rig's armature, on the pelvis, round the body at the belt, hanging to the hem."""
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    eb = rig.data.edit_bones
    c = (eb["thigh_l"].head + eb["thigh_r"].head) / 2
    for name, (dx, dy) in SKIRT.items():
        b = eb.new(name)
        b.head = Vector((c.x + dx * 0.15, c.y + dy * 0.11, BELT))
        b.tail = Vector((c.x + dx * 0.18, c.y + dy * 0.14, HEM))
        b.parent = eb["pelvis"]
        b.use_deform = True
    bpy.ops.object.mode_set(mode="OBJECT")


def with_skirt(mesh, rig, W):
    """Weights with the tunic's skirt on the cloth bones: the light vertices (the tunic, not the dark trousers) between
    the belt and the hem, clear of the thighs, the more the nearer the hem, each bone by how far round the body it
    hangs."""
    me = mesh.data
    col = me.color_attributes["Col"]
    lum, n = [0.0] * len(me.vertices), [0] * len(me.vertices)
    for li, loop in enumerate(me.loops):
        c = col.data[li].color
        lum[loop.vertex_index] += 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
        n[loop.vertex_index] += 1
    bones = rig.data.bones
    middle = (bones["thigh_l"].head_local + bones["thigh_r"].head_local) / 2
    thighs = [(bones[f"thigh_{s}"].head_local, bones[f"calf_{s}"].head_local) for s in "lr"]

    def from_thigh(p):
        return min((p - (a + (b - a) * max(0.0, min(1.0, (p - a).dot(b - a) / (b - a).length_squared)))).length
                   for a, b in thighs)
    hips = ("pelvis", "spine_01", "thigh_l", "thigh_r", "thigh_twist_01_l", "thigh_twist_01_r")
    out = []
    for i, v in enumerate(me.vertices):
        w = dict(W[i])
        z = v.co.z
        on_hips = bool(w) and max(w, key=w.get) in hips  # not the hands, which hang at the hips' height
        near = (v.co - middle).xy.length < 0.27
        if HEM - 0.04 < z < BELT and on_hips and near and lum[i] / max(n[i], 1) > 0.09 and from_thigh(v.co) > 0.08:
            t = min(max((BELT - z) / (BELT - HEM), 0.0), 1.0)
            share = 0.9 * t * t * (3 - 2 * t)
            d = v.co - middle
            ang = math.atan2(d.y, d.x)
            round_ = {name: max(0.0, math.cos(ang - math.atan2(dy, dx))) ** 2 for name, (dx, dy) in SKIRT.items()}
            total = sum(round_.values()) or 1.0
            w = {k: x * (1 - share) for k, x in w.items()}
            for name, r in round_.items():
                w[name] = w.get(name, 0.0) + share * r / total
        out.append(w)
    return tidy(out)


def corrective_axes(rest):
    """{(corrective, side): (bone, parent, the axis it bends about)}, in the armature's space at rest: square to the
    bone and the way it bends, so turning about it carries the bone that way."""
    out = {}
    nxt = {"thigh": "calf", "calf": "foot", "upperarm": "lowerarm", "lowerarm": "hand"}  # the joint at its far end
    for name, (bone, parent, way, _angles) in CORRECTIVES.items():
        for s in "lr":
            b, pa = f"{bone}_{s}", side_name(parent, s)
            along = (rest.head[f"{nxt[bone]}_{s}"] - rest.head[b]).normalized()
            out[(name, s)] = (b, pa, along.cross(Vector(way)).normalized())
    return out


def corrective_weights(rest, P):
    """{shape name: weight} for a pose (P, as runs.posed takes it): how far each joint bends the way of its correctives,
    shared out between the shapes made at the angles on either side."""
    turns = {}
    for n in rest.order:
        p = rest.parent[n]
        turns[n] = P[n] if n in P else (turns[p] if p else Matrix.Identity(3))
    out = {}
    for (name, s), (b, pa, axis) in corrective_axes(rest).items():
        q = (turns[pa].transposed() @ turns[b]).to_quaternion()
        bend = math.degrees(q.angle) * q.axis.dot(axis) if q.angle > 1e-6 else 0.0
        angles = CORRECTIVES[name][3]
        for i, a in enumerate(angles):
            lo = angles[i - 1] if i else 0.0
            hi = angles[i + 1] if i + 1 < len(angles) else None
            if bend <= lo:
                w = 0.0
            elif bend <= a:
                w = (bend - lo) / (a - lo)
            else:
                w = 1.0 if hi is None else max(0.0, (hi - bend) / (hi - a))
            out[f"{name}_{s}_{int(a)}"] = w
    return out


def add_correctives(mesh, rig, rest):
    """The corrective shapes on mesh (bound to rig, at rest): for each joint and angle, the joint alone bent so far,
    the mesh under plain skinning and under Blender's volume-keeping skinning, and the difference carried back to the
    rest pose (through each vertex's blend of the bones' turns), as a shape key."""
    arm = next(m for m in mesh.modifiers if m.type == "ARMATURE")
    me = mesh.data
    if me.shape_keys is None:
        mesh.shape_key_add(name="Basis")
    names = {g.index: g.name for g in mesh.vertex_groups}
    weights = [{names[g.group]: g.weight for g in v.groups if g.weight > 0.0} for v in me.vertices]
    kids = {n: [c for c in rest.order if rest.parent[c] == n] for n in rest.order}

    def below(n):
        out = {n}
        for c in kids[n]:
            out |= below(c)
        return out
    dg = bpy.context.evaluated_depsgraph_get()

    def evaluated():
        dg.update()
        ev = mesh.evaluated_get(dg)
        m = ev.to_mesh()
        co = [v.co.copy() for v in m.vertices]
        ev.to_mesh_clear()
        return co
    made = []
    for (name, s), (b, _pa, axis) in corrective_axes(rest).items():
        moved = below(b)
        for a in CORRECTIVES[name][3]:
            R = Matrix.Rotation(math.radians(a), 3, axis)
            for n, (loc, q) in runs.bases(rest, runs.posed(rest, {b: R}, {})).items():
                pb = rig.pose.bones[n]
                pb.rotation_mode = "QUATERNION"
                pb.rotation_quaternion = q
                pb.location = loc if n == "pelvis" else (0.0, 0.0, 0.0)
            arm.use_deform_preserve_volume = False
            plain = evaluated()
            arm.use_deform_preserve_volume = True
            full = evaluated()
            arm.use_deform_preserve_volume = False
            key = mesh.shape_key_add(name=f"{name}_{s}_{int(a)}", from_mix=False)
            for i, v in enumerate(me.vertices):
                d = full[i] - plain[i]
                if d.length < 1e-5:
                    continue
                w = sum(x for g, x in weights[i].items() if g in moved)
                M = Matrix.Identity(3) * (1.0 - w) + R * w  # how plain skinning moves an offset at this vertex
                key.data[i].co = v.co + M.inverted_safe() @ d
            made.append(key.name)
    for pb in rig.pose.bones:
        pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        pb.location = (0.0, 0.0, 0.0)
    return made


def heat(mesh, source, proxy):
    """Bone heat's weights for mesh (from proxy, rigs.heat_weights), Tripo's on the odd vertex the heat didn't reach."""
    W = transferred(mesh, proxy)
    tripo = tidy(read(source))
    return [w or tripo[i] for i, w in enumerate(W)]


def apply(variant, mesh, source, rig, proxy=None):
    """Binds mesh (a copy, on rig) the variant's way; source is the figure as made (with Tripo's weights)."""
    W = read(source)
    if variant == "tripo":
        W = tidy(W)
    elif variant == "smooth":
        W = tidy(smoothed(mesh, W))
    elif variant == "rigid":
        W = rigid(smoothed(mesh, W, times=2))
    elif variant in ("heat", "corrective"):  # the corrective's shapes come after, once the weights are on
        W = heat(mesh, source, proxy)
    elif variant == "helpers":
        W = with_helpers(heat(mesh, source, proxy))
    elif variant == "cloth":
        W = with_skirt(mesh, rig, heat(mesh, source, proxy))
    write(mesh, W)
    return W


def counts(ob):
    """How many vertices have 1, 2, 3, 4 bones."""
    c = {}
    for v in ob.data.vertices:
        n = len([g for g in v.groups if g.weight > 0.0])
        c[n] = c.get(n, 0) + 1
    return dict(sorted(c.items()))

