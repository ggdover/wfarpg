"""The plant editor: a "Plants" tab in the 3D viewport's sidebar (press N) for tuning the portfolio's bushes and grasses
live, as the tree editor does the trees (../trees/tree_editor.py).

Pick Bushes or Grasses, a plant, and one of its cards, and move the sliders; both variants of the plant (and their
copies on the forest floor) are rebuilt as you go. "Save settings" writes plant_settings.json next to this file, which
make_plants.py uses for the next full build and renders. The plants are generated, so edits made by hand to their
meshes are lost when the plant is rebuilt.

plant_portfolio.blend loads this file by itself once you allow its script to run (Blender asks when you open it). Or
start Blender with:  blender plant_portfolio.blend --python plant_editor.py
"""
import json
import os
import sys

import bpy
import bpy.utils.previews
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import plantgen  # noqa: E402

PREVIEWS = None
CARD_ITEMS = {}   # plant -> enum items; Blender needs these kept alive
PLANT_ITEMS = {}  # group -> enum items
_quiet = False    # set while filling in settings, so that doesn't trigger rebuilds
EXTRA_WORDS = {"berries": "Berry clumps", "flowers": "Flowering clumps", "nuts": "Clumps with nuts"}


def settings(scene, key):
    return scene.plant_editor.plants.get(key)


def as_cfg(s):
    cfg = {name: getattr(s, name) for name in plantgen.BASE}
    cfg["card"] = int(s.card)
    return cfg


def rebuild(key, scene=None):
    scene = scene or bpy.context.scene
    cfg = as_cfg(settings(scene, key))
    for variant in "AB":
        ob = bpy.data.objects.get(f"{key}_{variant}")
        if ob is not None and ob.type == "MESH":
            plantgen.build_into(key, variant, cfg, ob.data)


def _on_shape(self, context):
    if not _quiet and context.scene.plant_editor.live:
        rebuild(self.name, context.scene)


def _on_look(self, context):  # card and colour only touch the materials, so they are instant
    if not _quiet:
        plantgen.materials_for(self.name, as_cfg(self))


def _card_items(self, context):
    return CARD_ITEMS.get(self.name) or [("1", "1", "", 0, 1)]


def _plant_items(self, context):
    return PLANT_ITEMS.get(self.group) or [("Raspberry", "Raspberry", "", 0, 0)]


def _on_group(self, context):
    items = PLANT_ITEMS.get(self.group)
    if items and self.get("plant", -1) not in [i[4] for i in items]:  # by number: the old one isn't in the new list
        self["plant"] = items[0][4]


class PlantSettings(bpy.types.PropertyGroup):
    # name holds the plant's key, e.g. "Hazel"
    card: EnumProperty(name="Card", items=_card_items, update=_on_look,
                       description="Which card the plant's clumps, fronds or tufts use")
    size: FloatProperty(name="Card size", default=1.0, min=0.2, max=3.0, update=_on_shape,
                        description="How big each card is: the clumps' size, the fronds' length, the blades' height")
    planes: IntProperty(name="Cards per clump", default=3, min=1, max=16, update=_on_shape,
                        description="How many copies of the card cross in each clump or tuft (a fern: how many fronds)")
    density: FloatProperty(name="Clumps", default=1.0, min=0.2, max=6.0, update=_on_shape,
                           description="How many clumps grow at each spot. Above 1 they gather into patches (grass: more tufts)")
    spread: FloatProperty(name="Patch spread", default=1.0, min=0.0, max=2.0, update=_on_shape,
                          description="How far a patch's clumps, or a grass's tufts, spread out (long grass: how far "
                                      "apart its patches stand, on the forest floor and in the game, 0.5 m times this)")
    upright: FloatProperty(name="Clump height", default=1.0, min=0.3, max=2.0, update=_on_shape,
                           description="Height of the upright cards. Lower makes flatter, pad-like clumps")
    flat: BoolProperty(name="Flat card on top", default=True, update=_on_shape,
                       description="One card in each clump lies nearly flat, so clumps look full from the high game camera")
    tilt: FloatProperty(name="Angle randomness", default=1.0, min=0.0, max=3.0, update=_on_shape,
                        description="How much the cards' angles vary")
    brightness: FloatProperty(name="Brightness", default=1.0, min=0.4, max=1.6, update=_on_look,
                              description="Lighter or darker")
    hue: FloatProperty(name="Hue", default=0.5, min=0.4, max=0.6, update=_on_look,
                       description="Shifts the colour: below 0.5 toward yellow, above toward blue")
    saturation: FloatProperty(name="Saturation", default=1.0, min=0.0, max=2.0, update=_on_look,
                              description="More or less colourful")
    height: FloatProperty(name="Height", default=1.0, min=0.4, max=2.0, update=_on_shape,
                          description="Scales the plant's height")
    width: FloatProperty(name="Width", default=1.0, min=0.4, max=2.0, update=_on_shape,
                         description="Scales how wide the plant grows (grass: how wide each card is)")
    seed: IntProperty(name="Seed", default=0, min=0, max=999, update=_on_shape,
                      description="Another seed grows a different plant of the same kind")
    extra: FloatProperty(name="Berry clumps", default=0.3, min=0.0, max=1.0, update=_on_shape,
                         description="The share of clumps with berries, flowers or nuts; a grass: of tufts in flower")
    stems: IntProperty(name="Stems", default=5, min=1, max=16, update=_on_shape,
                       description="How many stems or canes grow from the bush's foot")
    lean: FloatProperty(name="Lean", default=0.3, min=0.0, max=1.0, update=_on_shape,
                        description="How far a tuft's cards lean out from upright (radians)")
    bend: FloatProperty(name="Bend", default=0.35, min=-0.3, max=1.2, update=_on_shape,
                        description="How much the cards bend over halfway up (a fern: how far its fronds arch over)")
    rise: FloatProperty(name="Frond angle", default=55.0, min=15.0, max=85.0, update=_on_shape,
                        description="How steeply the fronds rise from the ground, in degrees")
    flower_height: FloatProperty(name="Stalk height", default=1.6, min=0.8, max=2.5, update=_on_shape,
                                 description="How tall the flowering stalks stand, against the leaves")


class PlantEditor(bpy.types.PropertyGroup):
    group: EnumProperty(name="Group", update=_on_group, items=[
        ("BUSHES", "Bushes", "Bushes and the fern"),
        ("GRASSES", "Grasses", "Long grass, the grasses, sedge and cottongrass")])
    plant: EnumProperty(name="Plant", items=_plant_items)
    plants: CollectionProperty(type=PlantSettings)
    live: BoolProperty(name="Update live", default=True,
                       description="Rebuild the plant as you move a slider. Turn off for heavy settings and press Rebuild")


def fill_settings(scene, values=None, only=None):
    """Put settings into the scene's editor, without rebuilding anything."""
    global _quiet
    values = values or plantgen.load_settings()
    ed = scene.plant_editor
    _quiet = True
    try:
        for key, cfg in values.items():
            if only and key != only:
                continue
            s = ed.plants.get(key) or ed.plants.add()
            s.name = key
            for name, v in cfg.items():
                setattr(s, name, str(v) if name == "card" else v)
    finally:
        _quiet = False


class PLANTS_OT_rebuild(bpy.types.Operator):
    bl_idname = "plants.rebuild"
    bl_label = "Rebuild"
    bl_description = "Rebuild the plant from its settings (both variants)"
    every: BoolProperty(default=False)

    def execute(self, context):
        keys = [s[0] for s in plantgen.SPECIES] if self.every else [context.scene.plant_editor.plant]
        for key in keys:
            rebuild(key, context.scene)
        return {"FINISHED"}


class PLANTS_OT_reset(bpy.types.Operator):
    bl_idname = "plants.reset"
    bl_label = "Reset"
    bl_description = "Back to the default settings for this plant"

    def execute(self, context):
        key = context.scene.plant_editor.plant
        fill_settings(context.scene, {key: plantgen.DEFAULTS[key]})
        plantgen.materials_for(key, plantgen.DEFAULTS[key])
        rebuild(key, context.scene)
        return {"FINISHED"}


class PLANTS_OT_save(bpy.types.Operator):
    bl_idname = "plants.save"
    bl_label = "Save settings"
    bl_description = "Write every plant's settings to plant_settings.json, for make_plants.py's next build"

    def execute(self, context):
        out = {s.name: as_cfg(s) for s in context.scene.plant_editor.plants}
        with open(plantgen.SETTINGS, "w") as fh:
            json.dump(out, fh, indent=1)
        self.report({"INFO"}, "Saved " + plantgen.SETTINGS)
        return {"FINISHED"}


class PLANTS_OT_frame(bpy.types.Operator):
    bl_idname = "plants.frame"
    bl_label = "Frame plant"
    bl_description = "Select the plant and zoom the view to it"

    def execute(self, context):
        ob = bpy.data.objects.get(context.scene.plant_editor.plant + "_A")
        if ob is None:
            return {"CANCELLED"}
        for o in context.selected_objects:
            o.select_set(False)
        ob.select_set(True)
        context.view_layer.objects.active = ob
        if context.area and context.area.type == "VIEW_3D":
            bpy.ops.view3d.view_selected()
        return {"FINISHED"}


class PLANTS_OT_setup(bpy.types.Operator):
    bl_idname = "plants.setup"
    bl_label = "Set up the editor"
    bl_description = "Load the saved settings into this file"

    def execute(self, context):
        fill_settings(context.scene)
        return {"FINISHED"}


class VIEW3D_PT_plant_editor(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Plants"
    bl_label = "Plant editor"

    def draw(self, context):
        lay = self.layout
        ed = context.scene.plant_editor
        lay.prop(ed, "group", expand=True)
        lay.prop(ed, "plant", text="")
        s = ed.plants.get(ed.plant)
        if s is None:
            lay.operator("plants.setup", icon="IMPORT")
            return
        key = ed.plant
        kind = plantgen.kind(key)
        sp = plantgen.BY_KEY[key]
        lay.label(text=f"{sp[3]} · {sp[4]}")
        names = plantgen.card_names().get(sp[6], [])
        lay.template_icon_view(s, "card", show_labels=True, scale=6.0, scale_popup=5.0)
        n = int(s.card)
        lay.label(text=f"Card {n}: {names[n - 1]}" if n <= len(names) else f"Card {n}")
        extra = plantgen.extra_of(key)

        box = lay.box()
        col = box.column(align=True)
        if kind == "grass":
            box.label(text="Tufts", icon="OUTLINER_OB_POINTCLOUD")
            col = box.column(align=True)
            col.prop(s, "size", text="Blade height", slider=True)
            col.prop(s, "width", text="Tuft width", slider=True)
            col.prop(s, "planes", text="Cards per tuft", slider=True)
            col.prop(s, "density", text="Tufts", slider=True)
            col.prop(s, "spread", slider=True)
            col.prop(s, "lean", slider=True)
            col.prop(s, "bend", slider=True)
            col.prop(s, "tilt", slider=True)
            box = lay.box()
            box.label(text="Flowers", icon="OUTLINER_OB_FORCE_FIELD")
            col = box.column(align=True)
            col.prop(s, "extra", text="Tufts in flower", slider=True)
            col.prop(s, "flower_height", slider=True)
        elif kind == "patch":
            box.label(text="Patch", icon="OUTLINER_OB_POINTCLOUD")
            col = box.column(align=True)
            col.prop(s, "size", text="Blade height", slider=True)
            col.prop(s, "width", text="Card width", slider=True)
            col.prop(s, "planes", text="Cards per patch", slider=True)
            col.prop(s, "lean", slider=True)
            col.prop(s, "bend", slider=True)
            col.prop(s, "tilt", slider=True)
            col.prop(s, "spread", text="Patch spacing", slider=True)
            box = lay.box()
            box.label(text="Seed heads", icon="OUTLINER_OB_FORCE_FIELD")
            col = box.column(align=True)
            col.prop(s, "extra", text="Patches with seed heads", slider=True)
            col.prop(s, "flower_height", text="Seed head height", slider=True)
        elif kind == "fern":
            box.label(text="Fronds", icon="OUTLINER_OB_POINTCLOUD")
            col = box.column(align=True)
            col.prop(s, "size", text="Frond length", slider=True)
            col.prop(s, "planes", text="Fronds", slider=True)
            col.prop(s, "rise", slider=True)
            col.prop(s, "bend", text="Arch", slider=True)
            col.prop(s, "tilt", slider=True)
        else:
            box.label(text="Leaf clumps", icon="OUTLINER_OB_POINTCLOUD")
            col = box.column(align=True)
            col.prop(s, "size", slider=True)
            col.prop(s, "planes", slider=True)
            col.prop(s, "density", slider=True)
            col.prop(s, "spread", slider=True)
            col.prop(s, "upright", slider=True)
            col.prop(s, "tilt", slider=True)
            box.prop(s, "flat")

        box = lay.box()
        box.label(text="Colour", icon="COLOR")
        col = box.column(align=True)
        col.prop(s, "hue", slider=True)
        col.prop(s, "saturation", slider=True)
        col.prop(s, "brightness", slider=True)

        box = lay.box()
        box.label(text="Plant", icon="OUTLINER_OB_FORCE_FIELD")
        col = box.column(align=True)
        if kind == "bush":
            col.prop(s, "height", slider=True)
            col.prop(s, "width", slider=True)
            col.prop(s, "stems", text="Canes" if key == "Raspberry" else "Stems", slider=True)
            if extra:
                col.prop(s, "extra", text=EXTRA_WORDS.get(extra, "Extra clumps"), slider=True)
        col.prop(s, "seed")

        ob = bpy.data.objects.get(key + "_A")
        if ob is not None and ob.type == "MESH":
            me = ob.data
            cards = sum(1 for p in me.polygons if p.material_index > 0)
            size = ob.dimensions
            lay.label(text=f"{cards} card faces, {len(me.polygons)} faces")
            lay.label(text=f"{size.z:.2f} m tall, {max(size.x, size.y):.2f} m across")
        else:
            lay.label(text="This file has no " + key + "_A to edit", icon="ERROR")
        row = lay.row(align=True)
        row.operator("plants.frame", icon="ZOOM_SELECTED")
        row.operator("plants.rebuild", icon="FILE_REFRESH")
        row = lay.row(align=True)
        row.operator("plants.reset", icon="LOOP_BACK")
        row.operator("plants.save", icon="FILE_TICK")
        lay.prop(ed, "live")


CLASSES = (PlantSettings, PlantEditor, PLANTS_OT_rebuild, PLANTS_OT_reset, PLANTS_OT_save, PLANTS_OT_frame, PLANTS_OT_setup,
           VIEW3D_PT_plant_editor)


@bpy.app.handlers.persistent
def _on_load(_):
    for scene in bpy.data.scenes:
        if hasattr(scene, "plant_editor") and not scene.plant_editor.plants:
            fill_settings(scene)


def register():
    global PREVIEWS
    if hasattr(bpy.types, "VIEW3D_PT_plant_editor"):  # registered before: start clean
        unregister()
    PREVIEWS = bpy.utils.previews.new()
    names = plantgen.card_names()
    for key, *_rest in plantgen.SPECIES:
        card = plantgen.BY_KEY[key][6]
        items = []
        for n, label in enumerate(names.get(card) or [str(n) for n in range(1, 5)], 1):
            path = os.path.join(plantgen.TEXTURES, f"{card}_{n}.png")
            show = os.path.exists(path) and not bpy.app.background  # no thumbnails needed without a window
            icon = PREVIEWS.load(f"{card}_{n}", path, "IMAGE").icon_id if show else 0
            items.append((str(n), f"{n}  {label}", label, icon, n))
        CARD_ITEMS[key] = items
    for group, kinds in plantgen.GROUPS.items():
        PLANT_ITEMS[group] = [(s[0], s[2], f"{s[3]}, {s[4]}", 0, i) for i, s in enumerate(plantgen.SPECIES) if s[7] in kinds]
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.Scene.plant_editor = PointerProperty(type=PlantEditor)
    if _on_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_on_load)
    bpy.app.timers.register(lambda: _on_load(None), first_interval=0.1)  # the open file, once Blender is ready


def unregister():
    global PREVIEWS
    if _on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load)
    if hasattr(bpy.types.Scene, "plant_editor"):
        del bpy.types.Scene.plant_editor
    for name in [c.__name__ for c in reversed(CLASSES)]:
        cls = getattr(bpy.types, name, None)
        if cls is not None:
            bpy.utils.unregister_class(cls)
    if PREVIEWS is not None:
        bpy.utils.previews.remove(PREVIEWS)
        PREVIEWS = None


if __name__ == "__main__":
    register()
