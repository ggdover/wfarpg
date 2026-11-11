"""The run editor: a "Runs" tab in the 3D viewport's sidebar (press N) of run_portfolio.blend, for tuning a run live,
as the plant editor does the plants (../plants/plant_editor.py).

Pick a run and move its sliders: the run is keyed again as you go (Update live), on the skeleton most of the rigs share,
and every figure in the file runs it; "Key on every rig" keys the helper joints', the cloth bones' and the corrective
shapes' too. The panel says how the run measures (steps a minute, bounce, time on the ground) and, after "Check", what
check_runs.py finds wrong with it. "Save settings" writes run_settings.json next to this file, which runs.py reads over
its own numbers: make_runs.py's next build (the clips, the game's files, the rating page) and the play demo then run the
tuned runs. "Reset" goes back to the run as made. Press play in the timeline (Space) to see it move.

run_portfolio.blend loads this file by itself once you allow its script to run (Blender asks when you open it). Or start
Blender with:  blender run_portfolio.blend --python run_editor.py
"""
import contextlib
import io
import json
import os
import sys

import bpy
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty
from bpy.props import StringProperty
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import check_runs  # noqa: E402
import make_runs  # noqa: E402
import runs  # noqa: E402

_quiet = False  # set while filling in settings, so that doesn't key anything
# each setting: (label, least, most, what it does), in the panel's groups
GROUPS = [
    ("Rhythm", "TIME", [
        ("frames", "Frames a cycle", 24, 64, "Keys in a cycle, two steps, at 60 a second: fewer is a quicker rhythm (40 is "
                                            "180 steps a minute). The ground still goes by at the hero's 5.5 m/s"),
        ("stance", "On the ground", 0.10, 0.35, "The share of the cycle each foot is on the ground; less is more time in "
                                               "the air"),
    ]),
    ("Feet", "MOD_DYNAMICPAINT", [
        ("land", "Lands ahead", 0.10, 0.45, "How far ahead of its hip a foot lands (m)"),
        ("track", "Track width", 0.0, 0.35, "How far apart the lines are that the feet land on (m)"),
        ("toe_out", "Toes out", -5.0, 20.0, "How far the feet turn out (degrees)"),
        ("knee_out", "Knees out", -5.0, 20.0, "How far the knees point out (degrees)"),
        ("strike", "Foot strike", -20.0, 15.0, "The foot's pitch as it lands: below 0 heel first, above 0 on the forefoot"),
        ("dorsi", "Toes up", 0.0, 25.0, "How far the foot comes up, the toes toward the shin, late in the swing, so "
                                       "the heel leads it down (degrees)"),
        ("flat_at", "Flat by", 0.05, 0.6, "The share of the time on the ground by which the foot is flat: the "
                                          "forefoot comes down this long after the heel"),
        ("heel_at", "Heel rises at", 0.1, 0.8, "The share of the time on the ground at which the heel starts to rise"),
        ("push", "Push-off", 10.0, 80.0, "How far the heel is up as the foot leaves the ground (degrees): a runner's "
                                         "is 50 to 70"),
    ]),
    ("Hips", "BONE_DATA", [
        ("hip", "Hip height", 0.78, 0.92, "The hip joints' height as a foot lands (m; standing, 0.918): lower is a "
                                          "crouched run"),
        ("sink", "Sink", 0.0, 0.08, "How far the hips sink on the ground, on top of what landing gives (m)"),
        ("float", "Float", 0.2, 1.5, "How high the hips rise between steps, of what gravity gives: the bounce"),
    ]),
    ("Leg in the air", "CON_FOLLOWPATH", [
        ("back1", "Kicks back", 0.2, 0.5, "How far behind the hip the ankle is, a fifth into the swing (m)"),
        ("z1", "Kick height", 0.15, 0.6, "How high the ankle is then (m)"),
        ("back2", "Heel behind", -0.05, 0.35, "How far behind the hip the ankle passes under it (m)"),
        ("z2", "Heel kick", 0.2, 0.7, "How high the heel kicks up as it passes (m): to the seat is about 0.6"),
        ("fwd3", "Knee drive ahead", 0.0, 0.35, "How far ahead of the hip the ankle is, three quarters into the swing (m)"),
        ("z3", "Knee drive", 0.2, 0.6, "How high the ankle is then (m): high knees lift it"),
        ("reach", "Reach past", -0.05, 0.15, "How far past the landing spot the foot reaches before it comes down (m)"),
        ("z4", "Foot before landing", 0.08, 0.3, "How high the ankle is just before landing (m)"),
        ("bow", "Bow out", 0.0, 0.1, "How far the swinging foot bows out round the other leg (m)"),
        ("catch", "Catch", 0.0, 1.0, "How fast the foot already goes back as it lands, of the ground's speed: less is a "
                                     "harder landing"),
        ("land_drop", "Landing drop", 0.0, 2.0, "How fast the foot comes down as it lands (m/s)"),
    ]),
    ("Trunk", "ARMATURE_DATA", [
        ("lean", "Lean", -5.0, 35.0, "How far the trunk leans forward (degrees)"),
        ("hunch", "Hunch", -10.0, 15.0, "How far more the upper back rounds forward, the head pushed out ahead "
                                        "(degrees): below 0 the chest out"),
        ("pelvis_tilt", "Pelvis tilt", -5.0, 15.0, "How far the pelvis tips forward (degrees)"),
        ("tilt_swing", "Pelvis tilt swing", 0.0, 6.0, "How much more it tips as a foot pushes off, and less as one lands"),
        ("pelvis_yaw", "Hip turn", 0.0, 20.0, "How far the pelvis turns each way with the legs (degrees)"),
        ("pelvis_drop", "Hip drop", 0.0, 12.0, "How far the side of the leg in the air drops (degrees)"),
        ("sway", "Sway", 0.0, 0.08, "How far the hips move over the foot on the ground (m)"),
        ("rock", "Rock", 0.0, 10.0, "How far the shoulders roll toward the foot on the ground (degrees): a waddle"),
        ("twist", "Shoulder turn", 0.0, 25.0, "How far the shoulders turn each way against the hips (degrees)"),
        ("bounce_lean", "Landing dip", 0.0, 8.0, "How far the trunk dips forward after each landing (degrees)"),
    ]),
    ("Arms", "VIEW_PAN", [
        ("arm_swing", "Arm swing", 0.0, 70.0, "How far the arms swing each way at the shoulder (degrees)"),
        ("arm_mean", "Arm middle", -30.0, 40.0, "The middle of the swing (degrees): below 0 behind, above in front"),
        ("arm_out", "Arms out", 0.0, 40.0, "How far the arms are held out from the sides (degrees)"),
        ("back_out", "Out going back", 0.0, 25.0, "How much further out an arm swings as it goes back (degrees)"),
        ("arm_loop", "Hand loop", 0.0, 0.2, "How far the arm's in and out lead its swing: the hand goes round a loop"),
        ("arm_across", "Across the body", 0.0, 25.0, "How far the forearms turn in across the body (degrees)"),
        ("elbow", "Elbow bend", 10.0, 130.0, "How far the elbows bend on average (degrees): low is nearly straight arms"),
        ("elbow_swing", "Elbow swing", 0.0, 30.0, "How much more they bend in front, and less behind (degrees)"),
        ("arm_lag", "Arm lag", 0.0, 0.1, "The share of a cycle the arms lag the legs"),
        ("shrug", "Shrug", 0.0, 10.0, "How far the shoulders rise as an arm swings forward (degrees)"),
        ("protract", "Shoulder reach", 0.0, 15.0, "How far the shoulders go forward with the arm (degrees)"),
        ("shoulders", "Shoulders up", -6.0, 12.0, "How far the shoulders are held up all along (degrees): tense; below "
                                                  "0 dropped and loose"),
        ("wrist", "Wrist bend", -10.0, 30.0, "How far the wrists bend in (degrees)"),
        ("wrist_swing", "Wrist flop", 0.0, 15.0, "How far the hands flop after the forearms, each way (degrees)"),
        ("fist", "Fist", 0.0, 1.0, "0 an open hand, 1 a tight fist"),
        ("snap", "Snap", 0.0, 1.0, "0 smooth swings; above 0 the arms are held at the ends and snap through the middle"),
    ]),
    ("Head and cloth", "USER", [
        ("head_pitch", "Chin down", -10.0, 20.0, "How far the head tips down, looking ahead (degrees)"),
        ("head_steady", "Head steady", 0.0, 1.0, "How much the head holds still against the shoulders' turning"),
        ("head_nod", "Head nod", 0.0, 8.0, "How far the head dips after each landing (degrees)"),
        ("skirt_push", "Skirt push", 0.0, 1.2, "How far the thighs push the tunic's skirt (the cloth bones' rig), of how "
                                              "far they swing"),
        ("skirt_flutter", "Hem flutter", 0.0, 10.0, "How far the hem swings on after each landing (degrees)"),
    ]),
]
SETTING = {name: (label, lo, hi, text) for _g, _i, items in GROUPS for name, label, lo, hi, text in items}
RUN_ITEMS = [(k, s["label"], s["text"], 0, i) for i, (k, s) in enumerate(runs.STYLES.items())]


def _on_change(self, context):
    if not _quiet and context.scene.run_editor.live:
        key_run(self.name, context.scene, every=False)


def _setting_props():
    props = {}
    for name, (label, lo, hi, text) in SETTING.items():
        if name == "frames":
            props[name] = IntProperty(name=label, min=int(lo), max=int(hi), default=int(runs.DEFAULTS[name]),
                                      update=_on_change, description=text)
        else:
            props[name] = FloatProperty(name=label, min=lo, max=hi, default=float(runs.DEFAULTS[name]),
                                        update=_on_change, description=text, precision=3)
    return props


# a run's settings (name holds its key, e.g. "athletic"), one property for each of runs.DEFAULTS
RunSettings = type("RunSettings", (bpy.types.PropertyGroup,), {"__annotations__": _setting_props()})


class RunEditor(bpy.types.PropertyGroup):
    run: EnumProperty(name="Run", items=RUN_ITEMS, update=lambda self, context: show_run(self.run, context.scene))
    runs: CollectionProperty(type=RunSettings)
    live: BoolProperty(name="Update live", default=True,
                       description="Key the run again as a slider moves. Turn off to move several, then press Key")
    found: StringProperty(name="Check", default="",
                          description="What check_runs.py found, the last time Check was pressed")


def spec_of(s):
    """A run's settings (a RunSettings) as runs.Run takes them."""
    return {name: getattr(s, name) for name in SETTING}


def fill_settings(scene, values=None):
    """Put runs' settings into the scene's editor ({run: {setting: value}}; the tuned runs if none), keying nothing."""
    global _quiet
    values = values or runs.tuned()
    ed = scene.run_editor
    _quiet = True
    try:
        for key, cfg in values.items():
            s = ed.runs.get(key) or ed.runs.add()
            s.name = key
            for name in SETTING:
                setattr(s, name, int(cfg[name]) if name == "frames" else float(cfg[name]))
    finally:
        _quiet = False


def figure(vkey, model=0):
    """A rig's figure in the file: (rig, mesh), or Nones."""
    m = make_runs.MODELS[model][0]
    return bpy.data.objects.get(f"{m}_{vkey}_rig"), bpy.data.objects.get(f"{m}_{vkey}")


def rest_of(kind):
    """The run's view of a skeleton in the file (base, helpers or cloth), from its first figure, with the feet's heel
    and toe points the build left on the skeleton."""
    rig = figure(make_runs.FIRST[kind])[0]
    arm = rig.data
    heel = {s: Vector(arm[f"heel_{s}"]) for s in "lr"}
    toe = {s: Vector(arm[f"toe_{s}"]) for s in "lr"}
    return runs.Rest(rig, heel, toe)


def emptied(name):
    """The action called name with its keys taken out (so a shorter cycle leaves none behind), or None."""
    act = bpy.data.actions.get(name)
    if act is not None:
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    while bag.fcurves:
                        bag.fcurves.remove(bag.fcurves[0])
    return act


def key_run(key, scene, every=True):
    """Key a run from the editor's settings: on the shared skeleton, and with every, on the helper joints' and cloth
    bones' skeletons and the corrective shapes too; then every figure runs it."""
    spec = spec_of(scene.run_editor.runs[key])
    kinds = list(make_runs.FIRST) if every else ["base"]
    base_run = None
    for kind in kinds:
        rig = figure(make_runs.FIRST[kind])[0]
        if rig is None:
            continue
        rest = rest_of(kind)
        run = runs.Run(rest, spec)
        name = key if kind == "base" else f"{key}_{kind}"
        emptied(name)
        runs.key_action(rig, name, run, rest)
        if kind == "base":
            base_run = run
    _rig, mesh = figure("corrective")
    if every and mesh is not None and mesh.data.shape_keys is not None and base_run is not None:
        emptied(f"{key}_shapes")
        make_runs.key_shapes(f"{key}_shapes", base_run, mesh.data.shape_keys)
    show_run(key, scene)


def show_run(key, scene):
    """Every figure in the file running a run (as last keyed), the timeline one cycle of it."""
    for vkey, _label, _text in make_runs.rigs.VARIANTS:
        for m in range(len(make_runs.MODELS)):
            rig, mesh = figure(vkey, m)
            if rig is None:
                continue
            kind = make_runs.kind_of(vkey)
            act = bpy.data.actions.get(key if kind == "base" else f"{key}_{kind}")
            if act is not None and act.slots:
                make_runs.use(rig, act)
            shapes = bpy.data.actions.get(f"{key}_shapes")
            if vkey == "corrective" and shapes is not None and shapes.slots and mesh.data.shape_keys is not None:
                make_runs.use(mesh.data.shape_keys, shapes)
    s = scene.run_editor.runs.get(key)
    if s is not None:
        scene.frame_start, scene.frame_end = 0, s.frames - 1


def measures(spec):
    """How a run measures, as the page says: steps a minute, m a step, ms on the ground and in the air, cm bounce."""
    rest = rest_of("base")
    run = runs.Run(rest, spec)
    zs = [run.hip_height(i / 200) for i in range(200)]
    return (7200 / run.frames, runs.SPEED * run.T / 2, run.D * run.T * 1000, (0.5 - run.D) * run.T * 1000,
            (max(zs) - min(zs)) * 100)


class RUNS_OT_key(bpy.types.Operator):
    bl_idname = "runs.key"
    bl_label = "Key on every rig"
    bl_description = ("Key the run on every skeleton in the file, the helper joints', the cloth bones' and the "
                      "corrective shapes' too, and have every figure run it")

    def execute(self, context):
        key_run(context.scene.run_editor.run, context.scene, every=True)
        return {"FINISHED"}


class RUNS_OT_check(bpy.types.Operator):
    bl_idname = "runs.check"
    bl_label = "Check"
    bl_description = ("Check the run as check_runs.py does: the feet on the ground stay put, none goes into the ground, "
                      "no leg overstretches, nothing jerks, the hands keep off the body's middle")

    def execute(self, context):
        ed = context.scene.run_editor
        rest = rest_of("base")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            fine = check_runs.check(ed.run, runs.Run(rest, spec_of(ed.runs[ed.run])), rest)
        ed.found = out.getvalue().strip()
        self.report({"INFO"} if fine else {"WARNING"}, ed.found.splitlines()[0] if ed.found else "Checked")
        return {"FINISHED"}


class RUNS_OT_reset(bpy.types.Operator):
    bl_idname = "runs.reset"
    bl_label = "Reset"
    bl_description = "Back to the run as made (runs.py), and keyed so"

    def execute(self, context):
        key = context.scene.run_editor.run
        fill_settings(context.scene, {key: runs.AS_MADE[key]})
        context.scene.run_editor.found = ""
        key_run(key, context.scene, every=True)
        return {"FINISHED"}


class RUNS_OT_save(bpy.types.Operator):
    bl_idname = "runs.save"
    bl_label = "Save settings"
    bl_description = ("Write the runs' settings where they differ from the runs as made to run_settings.json, which "
                      "runs.py reads: make_runs.py's next build and the play demo use them")

    def execute(self, context):
        out = {}
        for s in context.scene.run_editor.runs:
            made = runs.AS_MADE.get(s.name)
            if made is None:
                continue
            changed = {n: round(v, 4) for n, v in spec_of(s).items() if abs(float(v) - float(made[n])) > 1e-4}
            if changed:
                out[s.name] = changed
        with open(runs.SETTINGS, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, indent=1, sort_keys=True)
        self.report({"INFO"}, f"Saved {runs.SETTINGS} ({len(out)} runs tuned)")
        return {"FINISHED"}


class RUNS_OT_setup(bpy.types.Operator):
    bl_idname = "runs.setup"
    bl_label = "Set up the editor"
    bl_description = "Load the runs' settings (as made, with any saved tuning) into this file"

    def execute(self, context):
        fill_settings(context.scene)
        return {"FINISHED"}


class VIEW3D_PT_run_editor(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Runs"
    bl_label = "Run editor"

    def draw(self, context):
        lay = self.layout
        ed = context.scene.run_editor
        lay.prop(ed, "run", text="")
        s = ed.runs.get(ed.run)
        if s is None:
            lay.operator("runs.setup", icon="IMPORT")
            return
        if figure(make_runs.FIRST["base"])[0] is None:
            lay.label(text="This file has no run portfolio figures", icon="ERROR")
            return
        col = lay.column(align=True)
        for line in _wrap(runs.STYLES[ed.run]["text"], 42):
            col.label(text=line)
        spm, step, ground, air, bob = measures(spec_of(s))
        box = lay.box()
        col = box.column(align=True)
        col.label(text=f"{spm:.0f} steps a minute, {step:.2f} m a step", icon="INFO")
        col.label(text=f"{ground:.0f} ms on the ground, {air:.0f} in the air")
        col.label(text=f"{bob:.0f} cm bounce")
        for title, icon, items in GROUPS:
            box = lay.box()
            box.label(text=title, icon=icon)
            col = box.column(align=True)
            for name, *_rest in items:
                col.prop(s, name, slider=True)
        if ed.found:
            box = lay.box()
            for i, line in enumerate(ed.found.splitlines()):
                for part in _wrap(line.strip(), 46):
                    box.label(text=part, icon=("CHECKMARK" if " ok:" in line else "ERROR") if i == 0 else "NONE")
                    i = 1
        lay.prop(ed, "live")
        row = lay.row(align=True)
        row.operator("runs.key", icon="FILE_REFRESH")
        row.operator("runs.check", icon="VIEWZOOM")
        row = lay.row(align=True)
        row.operator("runs.reset", icon="LOOP_BACK")
        row.operator("runs.save", icon="FILE_TICK")


def _wrap(text, width):
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}" if line else word
    return lines + ([line] if line else [])


CLASSES = (RunSettings, RunEditor, RUNS_OT_key, RUNS_OT_check, RUNS_OT_reset, RUNS_OT_save, RUNS_OT_setup,
           VIEW3D_PT_run_editor)


@bpy.app.handlers.persistent
def _on_load(_):
    for scene in bpy.data.scenes:
        if hasattr(scene, "run_editor") and not scene.run_editor.runs:
            fill_settings(scene)
            if figure(make_runs.FIRST["base"])[0] is not None:  # the timeline one cycle of the run shown
                show_run(scene.run_editor.run, scene)


def register():
    if hasattr(bpy.types, "VIEW3D_PT_run_editor"):  # registered before: start clean
        unregister()
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.Scene.run_editor = PointerProperty(type=RunEditor)
    if _on_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_on_load)
    bpy.app.timers.register(lambda: _on_load(None), first_interval=0.1)  # the open file, once Blender is ready


def unregister():
    if _on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load)
    if hasattr(bpy.types.Scene, "run_editor"):
        del bpy.types.Scene.run_editor
    for name in [c.__name__ for c in reversed(CLASSES)]:
        cls = getattr(bpy.types, name, None)
        if cls is not None:
            bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
