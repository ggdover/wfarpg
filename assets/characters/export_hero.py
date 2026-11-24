"""Exports the hero as the rating page shows it, packed as the user's Tripo3D exports in ref_model/ are (the user asked
for it, 19 November): a .zip holding a rigged .fbx with its base colour, metallic, roughness and normal maps in it,
beside a .fbm folder of those and the two packed as rm (red 1, green the roughness, blue the metallic), as PNGs 2048
pixels square like Tripo's.

The figure is make_runs.py's DEMO, Faceted 1500 on bone heat's rig, from run_portfolio.blend: at the origin, in metres,
its skeleton Tripo's (an armature called Armature with the same 61 bones and names as the 20k model's; the root
bone's tip turned 1 cm aside, so Blender's importer leaves the pelvis free to move), at most four bones on a vertex.
Its faces' flat colours are baked into the base colour texture on an unwrap of its own, and kept as vertex colours
too. It's matte, as in the game: no metal, the roughness even, the normal map flat. Two .zip files: the model on its
rig with no animations, as Tripo's, and the same with the runs and the stand as animations (a take each, named after
the run, at 60 frames a second).

    blender -b --factory-startup -P export_hero.py [-- --model=Faceted1500 --rig=heat --runs=all|2|athletic|none]

--runs, for the second: every run and the stand (all, the default), one round's runs and the stand (a round's
number), those named and the stand, or none (no second .zip). The corrective rig's shapes aren't carried, only its
bones. Writes build/export/<model>_<rig>/<triangles>_triangle_with_rig.zip and ..._with_rig_and_runs.zip
(1.5k_triangle_with_rig.zip for Faceted 1500, as Tripo's are 20k_ and 5k_), not kept in git.
"""
import os
import sys
import tempfile
import zipfile

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_runs  # noqa: E402
import runs  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OPTS = dict(a[2:].split("=", 1) for a in ARGS if a.startswith("--") and "=" in a)
SIZE = 2048  # pixels square, each texture, as Tripo's
OUT = os.path.join(HERE, "build", "export")


def triangles_label(n):
    """A triangle count as Tripo names its exports: 20k, 5k; 1.5k."""
    return f"{round(n / 1000, 1):g}k" if n >= 1000 else str(n)


def wanted_runs(which):
    if which == "none":
        return []
    if which == "all":
        keys = list(runs.STYLES)
    elif which.isdigit():
        keys = runs.round_runs(int(which))
    else:
        keys = [k for k in which.split(",") if k != "stand"]
        unknown = [k for k in keys if k not in runs.STYLES]
        if unknown:
            sys.exit(f"export_hero: no such runs: {', '.join(unknown)}")
    return keys + ["stand"]


def uniform(name, rgba):
    """A SIZE-square image of one colour (0-1 values), as data, not colour."""
    img = bpy.data.images.new(name, SIZE, SIZE, alpha=True)
    img.colorspace_settings.name = "Non-Color"
    img.pixels.foreach_set(np.tile(np.array(rgba, dtype=np.float32), SIZE * SIZE))
    return img


def bake_colours(mesh, uv, name):
    """The mesh's flat face colours (its Col attribute) baked on the UV map named uv into a new SIZE-square image."""
    scene = bpy.context.scene
    img = bpy.data.images.new(name, SIZE, SIZE, alpha=True)
    mat = bpy.data.materials.new("Bake")
    nt = mat.node_tree
    nt.nodes.clear()
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_name = "Col"
    emit = nt.nodes.new("ShaderNodeEmission")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    nt.links.new(attr.outputs["Color"], emit.inputs["Color"])
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    nt.nodes.active = tex
    kept = list(mesh.data.materials)
    mesh.data.materials.clear()
    mesh.data.materials.append(mat)
    layer = mesh.data.uv_layers[uv]
    mesh.data.uv_layers.active = layer
    layer.active_render = True
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 1
    scene.render.bake.margin = 16
    scene.render.bake.target = "IMAGE_TEXTURES"
    select(mesh)
    bpy.ops.object.bake(type="EMIT")
    px = np.empty(SIZE * SIZE * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    px[3::4] = 1.0  # opaque everywhere, as Tripo's base colour is, not only where the bake drew
    img.pixels.foreach_set(px)
    mesh.data.materials.clear()
    for m in kept:
        mesh.data.materials.append(m)
    bpy.data.materials.remove(mat)
    return img


def select(*obs):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in obs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]


def main():
    model, vkey = OPTS.get("model", make_runs.DEMO[0]), OPTS.get("rig", make_runs.DEMO[1])
    keys = wanted_runs(OPTS.get("runs", "all"))
    kind = make_runs.kind_of(vkey)
    bpy.ops.wm.open_mainfile(filepath=make_runs.BLEND)
    rig, mesh = bpy.data.objects.get(f"{model}_{vkey}_rig"), bpy.data.objects.get(f"{model}_{vkey}")
    if rig is None or mesh is None:
        sys.exit(f"export_hero: no {model} on {vkey}'s rig in {make_runs.BLEND}")
    tris = sum(len(p.vertices) - 2 for p in mesh.data.polygons)
    name = f"hero_{model.lower()}_{vkey}"
    folder = os.path.join(OUT, f"{model}_{vkey}")
    os.makedirs(folder, exist_ok=True)
    tmp = tempfile.TemporaryDirectory(prefix="export_hero_")  # the .zip's files, removed when done or stopped
    work = tmp.name
    os.makedirs(os.path.join(work, name + ".fbm"))
    scene = bpy.context.scene
    scene.render.fps = runs.FPS

    # the figure alone, at the origin, in its rest pose, its skeleton named as Tripo's is
    for ob in list(scene.objects):
        if ob not in (rig, mesh):
            ob.hide_set(True)
    rig.location = (0.0, 0.0, 0.0)
    rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
    rig.name, mesh.name = "Armature", name
    # Blender's FBX importer joins a bone to its one child when the bone points straight at it, as the root does at
    # the pelvis: joined, the pelvis can't move on its own, and the runs lose their bounce and sway there. So the root
    # points 1 cm (0.6°) aside; it never moves, so nothing else changes.
    select(rig)
    bpy.ops.object.mode_set(mode="EDIT")
    root = rig.data.edit_bones["root"]
    if not rig.data.edit_bones["pelvis"].use_connect:
        root.tail += runs.FWD * 0.01
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()

    # an unwrap of its own (the decimated model's is the 20k model's texture's, its pieces overlapping here and there),
    # and the flat colours baked onto it
    me = mesh.data
    for layer in list(me.uv_layers):
        me.uv_layers.remove(layer)
    me.uv_layers.new(name="UVMap")
    select(mesh)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.01, scale_to_bounds=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    base = bake_colours(mesh, "UVMap", f"{name}_basecolor")
    rough = mesh.data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value
    maps = {
        "basecolor": base,
        "metallic": uniform(f"{name}_metallic", (0.0, 0.0, 0.0, 1.0)),
        "roughness": uniform(f"{name}_roughness", (rough, rough, rough, 1.0)),
        "rm": uniform(f"{name}_rm", (1.0, rough, 0.0, 1.0)),
        "normal": uniform(f"{name}_normal", (0.5, 0.5, 1.0, 1.0)),
    }
    for key, img in maps.items():
        img.filepath_raw = os.path.join(work, name + ".fbm", f"{name}_{key}.PNG")
        img.file_format = "PNG"
        img.save()

    # the material the .fbx carries: the maps on the unwrap, as Tripo's
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]

    def texture(key, socket, colour=False):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = maps[key]
        if not colour:
            t.image.colorspace_settings.name = "Non-Color"
        nt.links.new(t.outputs["Color"], socket)
        return t
    texture("basecolor", bsdf.inputs["Base Color"], colour=True)
    texture("metallic", bsdf.inputs["Metallic"])
    texture("roughness", bsdf.inputs["Roughness"])
    normal = nt.nodes.new("ShaderNodeNormalMap")
    texture("normal", normal.inputs["Color"])
    nt.links.new(normal.outputs["Normal"], bsdf.inputs["Normal"])
    me.materials.clear()
    me.materials.append(mat)

    # each run, and the stand, a take of its own: an NLA track each, as the game's .glb files have them
    ad = rig.animation_data
    while ad.nla_tracks:
        ad.nla_tracks.remove(ad.nla_tracks[0])
    for key in keys:
        act = bpy.data.actions.get(key if kind == "base" else f"{key}_{kind}")
        if act is None:
            sys.exit(f"export_hero: {model} on {vkey} has no action for {key}: rebuild run_portfolio.blend")
        track = ad.nla_tracks.new()
        track.name = key
        strip = track.strips.new(key, int(act.frame_range[0]), act)
        strip.action_slot = act.slots[0]
        strip.name = key
        track.mute = True  # till the second .fbx: the first, as Tripo's, has no takes

    # two .zip files: the model on its rig as Tripo's are, and with the runs too
    fbx = os.path.join(work, name + ".fbx")
    label = triangles_label(tris)
    for suffix, takes in (("", False), ("_and_runs", bool(keys))):
        if suffix and not takes:
            break
        print("export_hero: writing the model on its rig"
              + (f" with {len(keys)} takes, up to a minute" if takes else "") + " ...", flush=True)
        for track in ad.nla_tracks:
            track.mute = not takes
        select(rig, mesh)
        bpy.ops.export_scene.fbx(
            filepath=fbx, use_selection=True, object_types={"ARMATURE", "MESH"}, apply_scale_options="FBX_SCALE_ALL",
            add_leaf_bones=False, use_armature_deform_only=False, mesh_smooth_type="FACE", colors_type="SRGB",
            path_mode="COPY", embed_textures=True, bake_anim=takes, bake_anim_use_nla_strips=True,
            bake_anim_use_all_actions=False, bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0)
        path = os.path.join(folder, f"{label}_triangle_with_rig{suffix}.zip")
        with zipfile.ZipFile(path + ".part", "w", zipfile.ZIP_DEFLATED) as z:
            for d, _, files in os.walk(work):
                for f in sorted(files):
                    full = os.path.join(d, f)
                    z.write(full, os.path.relpath(full, work).replace(os.sep, "/"))
        os.replace(path + ".part", path)  # only once it's whole: stopped partway, the .zip from before stays
        print(f"export_hero: {path}: {model} on {vkey}'s rig, {tris} triangles, {len(rig.data.bones)} bones, "
              + (f"{len(keys)} takes ({', '.join(keys[:3])}, ...), " if takes else "no takes, ")
              + f"{os.path.getsize(path) / 1e6:.1f} MB")
    tmp.cleanup()


if __name__ == "__main__":
    main()
