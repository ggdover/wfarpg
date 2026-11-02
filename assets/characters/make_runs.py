"""Run portfolio: the five low-poly heroes the user kept (Faceted 3000, 1500 and 800, Painted 1500, Retopology), each
rigged seven ways and running fifty ways (2 November). Builds run_portfolio.blend from hero_portfolio.blend's figures,
exports each figure on each rig with its runs for the game (build/runs/*.glb), and films each run from the side on one
of them (DEMO) for the portfolio's page, build/runs/gallery.html, which shows it beside a recording of the run in the
play demo (record_runs.py).

    blender -b --factory-startup -P make_runs.py                  all of it
    blender -b --factory-startup -P make_runs.py -- --no-render   all but the clips and sheets
    blender -b --factory-startup -P make_runs.py -- --export      only the game's files
    blender -b --factory-startup -P make_runs.py -- --side        only the side clips (and the gallery)
    blender -b --factory-startup -P make_runs.py -- --sheets      only the contact sheets
    blender -b --factory-startup -P make_runs.py -- --gallery     only the gallery page (after record_runs.py, say)
    ... -- --side --only=natural,heroic                           only those runs' side clips
    ... -- --export --models=Faceted1500 --rigs=heat              only those figures: quicker (the .blend isn't saved)
"""
import glob
import json
import math
import os
import shutil
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_heroes  # noqa: E402  (its build only runs as a script)
import rigs  # noqa: E402
import runs  # noqa: E402

HEROES = os.path.join(HERE, "hero_portfolio.blend")
BLEND = os.path.join(HERE, "run_portfolio.blend")
BUILD = os.path.join(HERE, "build", "runs")
PREVIEWS = os.path.join(HERE, "previews")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MODELS = [("Faceted3000", "Faceted 3000"), ("Faceted1500", "Faceted 1500"), ("Faceted800", "Faceted 800"),
          ("Painted1500", "Painted 1500"), ("Retopo", "Retopology")]
DEMO = ("Faceted1500", "heat")  # the figure and rig the portfolio's page shows every run on
NUMBER = {k: i + 1 for i, k in enumerate(runs.STYLES)}  # each run's number on the page
SPACING = 1.25  # m between the figures in a row
ROW = 3.0  # m between the rows, one a rig
GAME_PITCH, GAME_DISTANCE, GAME_YAW = 55.0, 14.0, 225.0  # the game's camera angle (game/scripts/camera_rig.gd), nearer
# the skeletons: Tripo's (its pelvis freed) for most rigs, and with helper bones or cloth bones for those rigs
SKELETONS = {"base": "Hero", "helpers": "HeroHelpers", "cloth": "HeroCloth"}
FIRST = {"base": "tripo", "helpers": "helpers", "cloth": "cloth"}  # the rig whose first figure sets each up
SIDE = (720, 540)  # the side clips' size
SIDE_VIEW = (2.9, 0.92)  # m across a side clip, and the height its middle is at: the figure most of its height
CLIP = 3.0  # s: about how long a side clip is, its cycle repeated, so a browser's hitch as it loops comes seldom
LOADER = '''"""Registers the run editor: the "Runs" tab in the 3D viewport's sidebar (press N).
Its code is run_editor.py, runs.py and the rest next to this .blend."""
import importlib
import sys

import bpy

folder = bpy.path.abspath("//")
if folder not in sys.path:
    sys.path.insert(0, folder)
import runs
import run_editor

importlib.reload(runs)
importlib.reload(run_editor)
run_editor.register()
'''


def kind_of(vkey):
    """Which skeleton a rig is on."""
    return vkey if vkey in ("helpers", "cloth") else "base"


def load_figures(names=None):
    """The figures (and the Tripo 20k model, the source of their weights) appended from hero_portfolio.blend, standing
    at the origin on their skeletons: {name: (rig, mesh)}."""
    names = list(names or [m for m, _ in MODELS]) + ["Tripo20k"]
    want = names + [n + "Rig" for n in names]
    with bpy.data.libraries.load(HEROES, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in want]
    coll = bpy.data.collections.get("Figures") or bpy.data.collections.new("Figures")
    if coll.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(coll)
    out = {}
    for n in names:
        rig, mesh = bpy.data.objects[n + "Rig"], bpy.data.objects[n]
        for ob in (rig, mesh):
            coll.objects.link(ob)
        rig.location = (0.0, 0.0, 0.0)
        out[n] = (rig, mesh)
    return out


def free_pelvis(rig):
    """The pelvis comes off the root (Tripo joins them), so the hips can rise and fall while the root stays at the
    feet, where the game's root motion would look for it."""
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    rig.data.edit_bones["pelvis"].use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")


def foot_points(rig, mesh):
    """{side: the back of the heel on the ground}, {side: the tip of the toes}, in the armature's space, from the
    vertices the foot and toe bones carry."""
    to_arm = rig.matrix_world.inverted() @ mesh.matrix_world
    heel, toe = {}, {}
    for s in "lr":
        groups = {mesh.vertex_groups[f"foot_{s}"].index, mesh.vertex_groups[f"ball_{s}"].index}
        pts = [to_arm @ v.co for v in mesh.data.vertices
               if sum(g.weight for g in v.groups if g.group in groups) > 0.5]
        low = [p for p in pts if p.z < 0.05]
        back = max(low, key=lambda p: p.y)
        front = min(pts, key=lambda p: p.y)
        heel[s] = Vector((back.x, back.y, 0.0))
        toe[s] = front.copy()
    return heel, toe


def rest_of(rig, source):
    """The run's view of rig's skeleton, with the heels and toes of source (rig, mesh)."""
    heel, toe = foot_points(*source)
    return runs.Rest(rig, heel, toe)


def collection(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


def build(models=None, vkeys=None):
    """The portfolio: every model on every rig (or only models and vkeys), the runs keyed on each skeleton (and on the
    corrective shapes), a stage to film them on."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = runs.FPS
    names = [m for m, _ in MODELS if not models or m in models]
    figs = load_figures(names)
    src_rig, src_mesh = figs["Tripo20k"]
    heel, toe = foot_points(src_rig, src_mesh)
    proxy = rigs.heat_weights(src_mesh, src_rig)
    skeletons = {}
    for kind, name in SKELETONS.items():
        skeletons[kind] = figs[names[0]][0].data.copy()
        skeletons[kind].name = name
        for s in "lr":  # the feet as the runs were made on them, for the run editor to make them again
            skeletons[kind][f"heel_{s}"] = list(heel[s])
            skeletons[kind][f"toe_{s}"] = list(toe[s])
    ink = make_heroes.plain_material("Ink", "#2E2A24")
    signs = collection("Signs")
    rows, ready = {}, set()
    for vi, (vkey, vlabel, _text) in enumerate(v for v in rigs.VARIANTS if not vkeys or v[0] in vkeys):
        coll = collection(vlabel)
        kind = kind_of(vkey)
        rows[vkey] = []
        for mi, mname in enumerate(names):
            fig = figs[mname][1]
            rig = bpy.data.objects.new(f"{mname}_{vkey}_rig", skeletons[kind])
            coll.objects.link(rig)
            if kind not in ready:  # once for each skeleton
                ready.add(kind)
                free_pelvis(rig)
                if kind == "helpers":
                    rigs.add_helpers(rig)
                elif kind == "cloth":
                    rigs.add_skirt(rig)
            mesh = fig.copy()
            mesh.data = fig.data.copy()
            mesh.name = mesh.data.name = f"{mname}_{vkey}"
            coll.objects.link(mesh)
            mesh.parent = rig
            mesh.matrix_parent_inverse.identity()
            mesh.location = (0.0, 0.0, 0.0)
            for m in mesh.modifiers:
                if m.type == "ARMATURE":
                    m.object = rig
            rig.location = ((mi - (len(names) - 1) / 2) * SPACING, vi * ROW, 0.0)
            rows[vkey].append((rig, mesh, mname))
        make_heroes.label(vlabel, (-(len(names) + 1) / 2 * SPACING - 0.4, vi * ROW - 0.45, -0.08), signs, ink, 0.12)
    for mi, mname in enumerate(names):
        make_heroes.label(dict(MODELS)[mname], ((mi - (len(names) - 1) / 2) * SPACING, -0.9, -0.08), signs, ink, 0.1)
    for vkey, row in rows.items():
        for rig, mesh, mname in row:
            rigs.apply(vkey, mesh, figs[mname][1], rig, proxy)
    bpy.data.objects.remove(proxy)
    for name, (rig, mesh) in figs.items():
        bpy.data.objects.remove(mesh)
        bpy.data.objects.remove(rig)
    for c in [c for c in bpy.data.collections if c.name == "Figures"]:
        bpy.data.collections.remove(c)
    rests = {}
    for vkey, row in rows.items():
        rests.setdefault(kind_of(vkey), runs.Rest(row[0][0], heel, toe))
    loader = bpy.data.texts.new("run_editor_loader.py")
    loader.write(LOADER)
    loader.use_module = True  # registers the run editor when the file opens, if Blender is allowed to run its scripts
    for rig, mesh, _ in rows.get("corrective", []):
        rigs.add_correctives(mesh, rig, rests["base"])
    actions = key_all(rows, rests)
    stage = make_stage(scene)
    return scene, rows, rests, actions, stage


def key_all(rows, rests):
    """Every run (and the stand) keyed on each skeleton, on its first figure, and on the corrective shapes: {(style,
    kind or "shapes"): (action, run)}; each rig then on athletic."""
    actions = {}
    firsts = {}
    for vkey, row in rows.items():
        firsts.setdefault(kind_of(vkey), row[0][0])
    for kind, first in firsts.items():
        rest = rests[kind]
        for style in list(runs.STYLES) + ["stand"]:
            run = runs.Stand(rest) if style == "stand" else runs.Run(rest, runs.STYLES[style])
            name = style if kind == "base" else f"{style}_{kind}"
            actions[(style, kind)] = (runs.key_action(first, name, run, rest), run)
    if "corrective" in rows:  # the corrective shapes' weights, keyed on the first figure's shapes, shared by all
        keys = rows["corrective"][0][1].data.shape_keys
        for style in list(runs.STYLES) + ["stand"]:
            run = actions[(style, "base")][1]
            actions[(style, "shapes")] = (key_shapes(f"{style}_shapes", run, keys), run)
    for vkey, row in rows.items():
        for rig, mesh, mname in row:
            use_run(vkey, rig, mesh, actions, "athletic")
    return actions


def key_shapes(name, run, keys):
    """An action turning the corrective shapes (rigs.add_correctives) as far as a run bends each joint, one key a frame
    from 0 to run.frames (the last as the first), looping, keyed on keys (a figure's shape keys)."""
    act = bpy.data.actions.get(name) or bpy.data.actions.new(name)
    act.use_fake_user = True
    keys.animation_data_create()
    keys.animation_data.action = act  # its slot comes with the first key
    first = None
    for f in range(run.frames + 1):
        P, _off, _ = run.pose(f / run.frames)
        w = rigs.corrective_weights(run.rest, P)
        if f == 0:
            first = w
        if f == run.frames:
            w = first
        for kb in keys.key_blocks[1:]:
            kb.value = w.get(kb.name, 0.0)
            kb.keyframe_insert("value", frame=f)
    if keys.animation_data.action_slot is None:
        keys.animation_data.action_slot = act.slots[0]
    for fc in runs.channelbag(act, keys).fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
        fc.modifiers.new("CYCLES")
    return act


def use(owner, act):
    """owner (a rig, or a figure's shape keys) playing act."""
    owner.animation_data_create()
    owner.animation_data.action = act
    owner.animation_data.action_slot = act.slots[0]


def use_run(vkey, rig, mesh, actions, style):
    """A figure on a rig running style: its skeleton's action, and with the corrective shapes theirs too."""
    use(rig, actions[(style, kind_of(vkey))][0])
    if vkey == "corrective":
        use(mesh.data.shape_keys, actions[(style, "shapes")][0])


def make_stage(scene):
    """A treadmill of ground (checks that move back under the runners at their speed), a sun and a fill light, and two
    cameras: from the side, and the game's from high."""
    coll = collection("Stage")
    ground = bpy.data.objects.new("Ground", bpy.data.meshes.new("Ground"))
    s = 60.0
    ground.data.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    mat = bpy.data.materials.new("Checks")
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.9
    tc = nt.nodes.new("ShaderNodeTexCoord")
    chk = nt.nodes.new("ShaderNodeTexChecker")
    chk.name = "Checks"
    chk.inputs["Color1"].default_value = (0.108, 0.140, 0.052, 1)
    chk.inputs["Color2"].default_value = (0.135, 0.170, 0.068, 1)
    nt.links.new(tc.outputs["Object"], chk.inputs["Vector"])
    nt.links.new(chk.outputs["Color"], bsdf.inputs["Base Color"])
    ground.data.materials.append(mat)
    coll.objects.link(ground)
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 3.4
    sun.data.angle = math.radians(2)
    sun.rotation_euler = (math.radians(48), 0, math.radians(-32))
    coll.objects.link(sun)
    fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill", "SUN"))  # on the side the side camera sees
    fill.data.energy = 1.3
    fill.data.use_shadow = False
    fill.rotation_euler = (math.radians(55), 0, math.radians(65))
    coll.objects.link(fill)
    world = bpy.data.worlds.new("World")
    scene.world = world
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.42, 0.45, 0.5, 1.0)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.9
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 16
    scene.view_settings.view_transform = "Standard"
    scene.render.dither_intensity = 0.0  # no noise: the clips and sheets stay small
    side = bpy.data.objects.new("SideCamera", bpy.data.cameras.new("SideCamera"))
    side.data.type = "ORTHO"
    side.data.ortho_scale = 5 * 1.7  # the five models of a row, each in a fifth of the picture
    tilt = math.radians(12)  # looking a little down, so the ground shows under and behind the feet
    side.location = (14.0, 0.0, 1.05 + 14.0 * math.tan(tilt))
    side.rotation_euler = (math.radians(90) - tilt, 0, math.radians(90))
    coll.objects.link(side)
    game = bpy.data.objects.new("GameCamera", bpy.data.cameras.new("GameCamera"))
    game.data.lens = 35.0
    p, y = math.radians(GAME_PITCH), math.radians(GAME_YAW)
    target = Vector((0.0, 0.0, 0.9 * (1 - GAME_PITCH / 90)))
    game.location = target + Vector((math.cos(y) * math.cos(p), math.sin(y) * math.cos(p), math.sin(p))) * GAME_DISTANCE
    game.rotation_euler = (target - game.location).to_track_quat("-Z", "Y").to_euler()
    coll.objects.link(game)
    scene.camera = side
    for area in (a for w in bpy.data.screens for a in w.areas if a.type == "VIEW_3D"):
        for sp in area.spaces:
            if sp.type == "VIEW_3D":
                sp.shading.type = "MATERIAL"
    return dict(ground=ground, checks=chk, side=side, game=game)


def treadmill(stage, run):
    """The ground moving back under the runners at their speed over a cycle, and its checks sized so a cycle moves it
    a whole number of them: the clip loops without a jump."""
    ground = stage["ground"]
    dist = runs.SPEED * run.T
    pair = dist / max(1, round(dist / 1.0))  # a light and a dark check, about 1 m
    stage["checks"].inputs["Scale"].default_value = 2.0 / pair
    ground.animation_data_clear()
    ground.location = (0.0, 0.0, 0.0)
    ground.keyframe_insert("location", index=1, frame=0)
    ground.location = (0.0, dist, 0.0)
    ground.keyframe_insert("location", index=1, frame=run.frames)
    ad = ground.animation_data
    for fc in ad.action.layers[0].strips[0].channelbag(ad.action_slot).fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
        fc.modifiers.new("CYCLES")


def encode(frames, repeats, dst, size):
    """An H.264 clip, dst, of a cycle's frames (PNG files, in order) played repeats times over, made in the video
    editor of a scene of its own, the colours left as they were rendered."""
    enc = bpy.data.scenes.get("Encode") or bpy.data.scenes.new("Encode")
    enc.view_settings.view_transform = "Standard"
    ed = enc.sequence_editor or enc.sequence_editor_create()
    for strip in list(ed.strips):
        ed.strips.remove(strip)
    strip = ed.strips.new_image("Cycle", frames[0], 1, 1)
    for i in range(1, repeats * len(frames)):
        strip.elements.append(os.path.basename(frames[i % len(frames)]))
    r = enc.render
    r.fps = runs.FPS
    r.resolution_x, r.resolution_y = size
    r.resolution_percentage = 100
    r.use_sequencer = True
    enc.frame_start, enc.frame_end = 1, repeats * len(frames)
    r.image_settings.media_type = "VIDEO"
    r.image_settings.file_format = "FFMPEG"
    r.ffmpeg.format, r.ffmpeg.codec = "MPEG4", "H264"
    r.ffmpeg.constant_rate_factor, r.ffmpeg.ffmpeg_preset = "MEDIUM", "GOOD"
    base = dst[:-4] + "_"
    for old in glob.glob(base + "*.mp4"):
        os.remove(old)
    r.filepath = base
    bpy.ops.render.render(animation=True, scene=enc.name)
    made = glob.glob(base + "*.mp4")
    if made:
        os.replace(made[0], dst)


def export_glbs(rows, actions):
    """Each model on each rig, with its runs and the stand, to build/runs/<model>_<rig>.glb for the game: the runs as
    animations named after their styles; and build/runs/runs.json, the runs in order with their names, for the game's
    run viewer (game/scripts/dev/runs.gd) and record_runs.py."""
    os.makedirs(BUILD, exist_ok=True)
    with open(os.path.join(BUILD, "runs.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump([dict(key=k, label=s["label"]) for k, s in runs.STYLES.items()], f, ensure_ascii=False, indent=1)
    for vkey, row in rows.items():
        kind = kind_of(vkey)
        for rig, mesh, mname in row:
            owners = [(rig.animation_data, kind)]
            if vkey == "corrective":
                owners.append((mesh.data.shape_keys.animation_data, "shapes"))
            kept = []
            for ad, which in owners:
                kept.append(ad.action)
                ad.action = None
                for style in list(runs.STYLES) + ["stand"]:
                    act = actions[(style, which)][0]
                    track = ad.nla_tracks.new()
                    track.name = style
                    strip = track.strips.new(style, 0, act)
                    strip.action_slot = act.slots[0]
            make_heroes.game_colours(mesh.data)
            home = rig.location.copy()
            rig.location = (0.0, 0.0, 0.0)  # at the origin, not where the portfolio has it standing
            bpy.context.view_layer.update()
            bpy.ops.object.select_all(action="DESELECT")
            rig.select_set(True)
            mesh.select_set(True)
            bpy.context.view_layer.objects.active = rig
            path = os.path.join(BUILD, f"{mname}_{vkey}.glb")
            bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_yup=True,
                                      export_texcoords=True, export_normals=True, export_skins=True,
                                      export_animations=True, export_animation_mode="NLA_TRACKS",
                                      export_force_sampling=True, export_optimize_animation_size=False,
                                      export_def_bones=False, export_materials="NONE", export_vertex_color="NAME",
                                      export_vertex_color_name="ColSRGB", export_all_vertex_colors=False,
                                      export_cameras=False, export_lights=False)
            make_heroes.drop_game_colours(mesh.data)
            rig.location = home
            for (ad, _which), keep in zip(owners, kept):
                while ad.nla_tracks:
                    ad.nla_tracks.remove(ad.nla_tracks[0])
                ad.action = keep
                ad.action_slot = keep.slots[0]
            print("exported", path)


def alone(rows, model, vkey):
    """Only model on vkey's rig shown, at the origin, the signs hidden; a function that puts everything back."""
    shown = {ob: ob.hide_render for ob in bpy.context.scene.objects}
    homes = {rig: rig.location.copy() for row in rows.values() for rig, _, _ in row}
    for row in rows.values():
        for rig, mesh, _ in row:
            rig.hide_render = mesh.hide_render = True
    bpy.data.collections["Signs"].hide_render = True
    rig, mesh, _ = next(r for r in rows[vkey] if r[2] == model)
    rig.hide_render = mesh.hide_render = False
    rig.location = (0.0, 0.0, 0.0)

    def back():
        for ob, hidden in shown.items():
            ob.hide_render = hidden
        for r, loc in homes.items():
            r.location = loc
        bpy.data.collections["Signs"].hide_render = False
    return rig, mesh, back


def render_side(scene, rows, actions, stage, only=None, model=DEMO[0], vkey=DEMO[1]):
    """build/runs/side/<run>.mp4: each run on one model and rig, alone and large, from the side, the ground going back
    under it at its speed; its cycle repeated to about CLIP seconds. only: those runs."""
    if vkey not in rows or not any(r[2] == model for r in rows[vkey]):
        print("side clips: this build has no", model, "on", vkey)
        return
    out = os.path.join(BUILD, "side")
    frames_dir = os.path.join(BUILD, "frames")
    os.makedirs(out, exist_ok=True)
    ims = scene.render.image_settings
    ims.media_type = "IMAGE"
    ims.file_format = "PNG"
    ims.color_mode = "RGB"
    rig, mesh, back = alone(rows, model, vkey)
    cam = stage["side"]
    kept = cam.data.sensor_fit, cam.data.ortho_scale, cam.location.copy()
    width, middle = SIDE_VIEW
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.ortho_scale = width
    cam.location.z = middle + cam.location.x * math.tan(math.radians(90) - cam.rotation_euler.x)
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = SIDE
    for style in runs.STYLES:
        if only and style not in only:
            continue
        run = actions[(style, kind_of(vkey))][1]
        use_run(vkey, rig, mesh, actions, style)
        treadmill(stage, run)
        scene.frame_start, scene.frame_end = 0, run.frames - 1
        shutil.rmtree(frames_dir, ignore_errors=True)
        os.makedirs(frames_dir)
        scene.render.filepath = os.path.join(frames_dir, "f_####")
        bpy.ops.render.render(animation=True, scene=scene.name)
        encode(sorted(glob.glob(os.path.join(frames_dir, "f_*.png"))), max(2, round(CLIP / run.T)),
               os.path.join(out, f"{style}.mp4"), SIDE)
        print("side", style)
    shutil.rmtree(frames_dir, ignore_errors=True)
    cam.data.sensor_fit, cam.data.ortho_scale, cam.location = kept
    use_run(vkey, rig, mesh, actions, "athletic")
    treadmill(stage, actions[("athletic", kind_of(vkey))][1])
    back()
    ims.color_mode = "RGBA"


def slug(title):
    return "".join(c if c.isalnum() else "_" for c in title.lower()).strip("_")


def render_sheets(scene, rows, rests, stage, model=DEMO[0], vkey=DEMO[1], phases=8):
    """previews/runs_<family>.png: each family's runs at eight moments of their cycles (from the left foot landing),
    from the side, a row each, on one model and rig, to see them all at once without the clips."""
    if vkey not in rows or not any(r[2] == model for r in rows[vkey]):
        print("sheets: this build has no", model, "on", vkey)
        return
    for old in glob.glob(os.path.join(PREVIEWS, "runs_*.png")):
        os.remove(old)
    rig0, mesh0, _ = next(r for r in rows[vkey] if r[2] == model)
    rest = rests[kind_of(vkey)]
    ink = bpy.data.materials["Ink"]
    hidden = [ob for ob in scene.objects if not ob.hide_render and ob.type != "LIGHT" and ob.name != "Ground"]
    for ob in hidden:
        ob.hide_render = True
    stage["ground"].hide_render = True
    cam = bpy.data.objects.new("SheetCamera", bpy.data.cameras.new("SheetCamera"))
    scene.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.sensor_fit = "HORIZONTAL"
    scene.camera = cam
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    row_h, gap = 2.3, 1.45
    for title, _text, keys in runs.FAMILIES:
        coll = collection("Sheet")
        for r, style in enumerate(keys):
            run = runs.Run(rest, runs.STYLES[style])
            for c in range(phases):
                rig = rig0.copy()
                rig.animation_data_clear()
                mesh = mesh0.copy()
                coll.objects.link(rig)
                coll.objects.link(mesh)
                mesh.parent = rig
                mesh.hide_render = False
                for m in mesh.modifiers:
                    if m.type == "ARMATURE":
                        m.object = rig
                P, off, _ = run.pose(c / phases)
                for n, (loc, q) in runs.bases(rest, runs.posed(rest, P, off)).items():
                    pb = rig.pose.bones[n]
                    pb.rotation_mode = "QUATERNION"
                    pb.rotation_quaternion = q
                    pb.location = loc if n == "pelvis" else (0.0, 0.0, 0.0)
                rig.location = (0.0, gap * c, -r * row_h)  # seen from the left, running to the left of the picture
            sign = make_heroes.label(f"{NUMBER[style]}. {runs.STYLES[style]['label']}", (0, 0, 0), coll, ink,
                                     0.2)
            sign.location = (0.0, -1.7, -r * row_h + 0.85)
            sign.rotation_euler = (math.radians(90), 0, math.radians(90))
        width = gap * phases + 2.4
        height = row_h * len(keys)
        cam.data.ortho_scale = width
        cam.location = (20.0, (gap * (phases - 1) - 2.6) / 2, -height / 2 + row_h - 0.15)
        cam.rotation_euler = (math.radians(90), 0, math.radians(90))
        scene.render.resolution_x = 2000
        scene.render.resolution_y = round(2000 * height / width)
        scene.render.filepath = os.path.join(PREVIEWS, f"runs_{slug(title)}.png")
        bpy.ops.render.render(write_still=True)
        print("sheet", scene.render.filepath)
        for ob in list(coll.objects):
            bpy.data.objects.remove(ob)
        bpy.data.collections.remove(coll)
    for ob in hidden:
        ob.hide_render = False
    stage["ground"].hide_render = False
    bpy.data.objects.remove(cam)
    scene.render.image_settings.color_mode = "RGBA"
    scene.camera = stage["side"]


def write_gallery(actions, kind=kind_of(DEMO[1])):
    """build/runs/gallery.html: run_gallery.html with the runs filled in, in their families, each with its side clip
    (side/<run>.mp4) and its recording in the play demo (game/<run>.mp4), where there are."""
    def bob(run):
        zs = [run.hip_height(i / 200) for i in range(200)]
        return round((max(zs) - min(zs)) * 100)

    data = {
        "speed": runs.SPEED,
        "model": dict(MODELS)[DEMO[0]],
        "rig": next(label for k, label, _ in rigs.VARIANTS if k == DEMO[1]),
        "families": [dict(title=t, text=x, runs=keys) for t, x, keys in runs.FAMILIES],
        "runs": [dict(key=k, n=NUMBER[k], label=s["label"], text=s["text"], spm=round(7200 / run.frames),
                      step=round(runs.SPEED * run.T / 2, 2), contact=round(run.D * run.T * 1000),
                      flight=round((0.5 - run.D) * run.T * 1000), bob=bob(run),
                      side=os.path.exists(os.path.join(BUILD, "side", k + ".mp4")),
                      game=os.path.exists(os.path.join(BUILD, "game", k + ".mp4")))
                 for k, s in runs.STYLES.items() for run in [actions[(k, kind)][1]]],
    }
    with open(os.path.join(HERE, "run_gallery.html"), encoding="utf-8") as f:
        page = f.read().replace("/*DATA*/", json.dumps(data, ensure_ascii=False))
    path = os.path.join(BUILD, "gallery.html")
    os.makedirs(BUILD, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(page)
    print("gallery", path)


if __name__ == "__main__":
    opts = dict(a.split("=", 1) for a in ARGS if "=" in a)
    only = set(opts["--only"].split(",")) if "--only" in opts else None
    models = opts["--models"].split(",") if "--models" in opts else None
    vkeys = opts["--rigs"].split(",") if "--rigs" in opts else None
    parts = [p for p in ("--export", "--side", "--sheets", "--gallery") if p in ARGS]
    scene, rows, rests, actions, stage = build(models, vkeys)
    kind = "base" if "base" in rests else next(iter(rests))
    if not parts or "--export" in parts or "--side" in parts:
        # the runs' own checks (check_runs.py) first: no clips or files of a run that slides, sinks, overreaches or
        # jerks
        import check_runs  # noqa: E402
        fine = [check_runs.check(name, actions[(name, kind)][1], rests[kind]) for name in runs.STYLES]
        fine.append(check_runs.check("stand", actions[("stand", kind)][1], rests[kind], still=True))
        if not all(fine):
            sys.exit("make_runs: a run fails its checks (above); nothing saved")
    whole = not models and not vkeys  # the .blend only from a whole build
    if not parts:
        for vkey, row in rows.items():
            for rig, mesh, mname in row:
                print(f"{mesh.name:22s} {len(mesh.data.vertices):5d} vertices, bones a vertex {rigs.counts(mesh)}")
        if whole:
            bpy.ops.wm.save_as_mainfile(filepath=BLEND, relative_remap=True)
        export_glbs(rows, actions)
        if "--no-render" not in ARGS:
            render_side(scene, rows, actions, stage, only)
            render_sheets(scene, rows, rests, stage)
        write_gallery(actions)
        if whole:
            bpy.ops.wm.save_as_mainfile(filepath=BLEND, relative_remap=True)
    else:
        if "--export" in parts:
            export_glbs(rows, actions)
        if "--side" in parts:
            render_side(scene, rows, actions, stage, only)
        if "--sheets" in parts:
            render_sheets(scene, rows, rests, stage)
        if "--side" in parts or "--gallery" in parts:
            write_gallery(actions)
