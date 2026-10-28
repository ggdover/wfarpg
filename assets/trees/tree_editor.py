"""The tree editor: a "Trees" tab in the 3D viewport's sidebar (press N) for tuning the portfolio trees live.

Pick a tree, pick one of its leaf cards, and move the sliders; both variants of the tree (and their copies in the
grove) are rebuilt as you go. "Save settings" writes tree_settings.json next to this file, which make_trees.py uses
for the next full build and renders. The trees are generated, so edits made by hand to their meshes are lost when the
tree is rebuilt.

tree_portfolio.blend loads this file by itself once you allow its script to run (Blender asks when you open it). Or
start Blender with:  blender tree_portfolio.blend --python tree_editor.py
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
import treegen  # noqa: E402

PREVIEWS = None
CARD_ITEMS = {}  # species -> enum items; Blender needs these kept alive
_quiet = False   # set while filling in settings, so that doesn't trigger rebuilds


def settings(scene, key):
    return scene.tree_editor.trees.get(key)


def as_cfg(s):
    cfg = {name: getattr(s, name) for name in treegen.BASE}
    cfg["card"] = int(s.card)
    return cfg


def rebuild(key, scene=None):
    scene = scene or bpy.context.scene
    cfg = as_cfg(settings(scene, key))
    for variant in "AB":
        ob = bpy.data.objects.get(f"{key}_{variant}")
        if ob is not None and ob.type == "MESH":
            treegen.build_into(key, variant, cfg, ob.data)


def _on_shape(self, context):
    if not _quiet and context.scene.tree_editor.live:
        rebuild(self.name, context.scene)


def _on_look(self, context):  # card and colour only touch the material, so they are instant
    if not _quiet:
        treegen.materials_for(self.name, as_cfg(self))


def _card_items(self, context):
    return CARD_ITEMS.get(self.name) or [("1", "1", "", 0, 1)]


class TreeSettings(bpy.types.PropertyGroup):
    # name holds the species key, e.g. "ScotsPine"
    card: EnumProperty(name="Leaf card", items=_card_items, update=_on_look,
                       description="Which leaf card the clumps or sprays use")
    layout: EnumProperty(name="Layout", update=_on_shape, items=[
        ("crossed", "Crossed clumps", "Clumps of cards crossing at their centre"),
        ("pinnate", "Pinnate sprays", "Spray cards set along each branch on alternate sides, their twigs' bases on the branch")])
    size: FloatProperty(name="Card size", default=1.0, min=0.2, max=3.0, update=_on_shape,
                        description="How big each leaf card is")
    planes: IntProperty(name="Cards per clump", default=3, min=1, max=10, update=_on_shape,
                        description="How many copies of the card cross in each clump. More makes a fuller, rounder clump")
    density: FloatProperty(name="Clumps", default=1.0, min=0.2, max=6.0, update=_on_shape,
                           description="How many clumps grow at each spot on the branches. Above 1 they gather into patches")
    spread: FloatProperty(name="Patch spread", default=1.0, min=0.0, max=2.0, update=_on_shape,
                          description="How far the clumps in a patch spread out: 1 fills the space one full-size clump would take")
    upright: FloatProperty(name="Clump height", default=1.0, min=0.3, max=2.0, update=_on_shape,
                           description="Height of the upright cards. Lower makes flatter, pad-like clumps")
    flat: BoolProperty(name="Flat card on top", default=True, update=_on_shape,
                       description="One card in each clump lies nearly flat, so clumps look full from the high game camera")
    tilt: FloatProperty(name="Angle randomness", default=1.0, min=0.0, max=3.0, update=_on_shape,
                        description="How much the cards' angles vary")
    brightness: FloatProperty(name="Brightness", default=1.0, min=0.4, max=1.6, update=_on_look,
                              description="Lighter or darker leaves")
    hue: FloatProperty(name="Hue", default=0.5, min=0.4, max=0.6, update=_on_look,
                       description="Shifts the leaves' colour: below 0.5 toward yellow, above toward blue")
    saturation: FloatProperty(name="Saturation", default=1.0, min=0.0, max=2.0, update=_on_look,
                              description="More or less colourful leaves")
    height: FloatProperty(name="Tree height", default=1.0, min=0.5, max=1.6, update=_on_shape,
                          description="Scales the tree's height")
    width: FloatProperty(name="Crown width", default=1.0, min=0.5, max=1.8, update=_on_shape,
                         description="Scales the branches' length")
    seed: IntProperty(name="Seed", default=0, min=0, max=999, update=_on_shape,
                      description="Another seed grows a different tree of the same kind")
    berries: FloatProperty(name="Berry clumps", default=0.3, min=0.0, max=1.0, update=_on_shape,
                           description="Share of the rowan's clumps that carry berries")
    spacing: FloatProperty(name="Spacing", default=0.28, min=0.08, max=1.0, unit="LENGTH", update=_on_shape,
                           description="Distance between sprays along a branch")
    spray_angle: FloatProperty(name="Spray angle", default=55.0, min=10.0, max=90.0, update=_on_shape,
                               description="How far the sprays turn out from the branch, in degrees")
    droop: FloatProperty(name="Droop", default=0.25, min=-0.5, max=1.5, update=_on_shape,
                         description="How much the sprays hang down (below 0 they lift)")


class TreeEditor(bpy.types.PropertyGroup):
    species: EnumProperty(name="Tree", items=[(s[0], s[2], f"{s[3]}, {s[4]}") for s in treegen.SPECIES])
    trees: CollectionProperty(type=TreeSettings)
    live: BoolProperty(name="Update live", default=True,
                       description="Rebuild the tree as you move a slider. Turn off for heavy settings and press Rebuild")


def fill_settings(scene, values=None, only=None):
    """Put settings into the scene's editor, without rebuilding anything."""
    global _quiet
    values = values or treegen.load_settings()
    ed = scene.tree_editor
    _quiet = True
    try:
        for key, cfg in values.items():
            if only and key != only:
                continue
            s = ed.trees.get(key) or ed.trees.add()
            s.name = key
            for name, v in cfg.items():
                setattr(s, name, str(v) if name == "card" else v)
    finally:
        _quiet = False


class TREES_OT_rebuild(bpy.types.Operator):
    bl_idname = "trees.rebuild"
    bl_label = "Rebuild"
    bl_description = "Rebuild the tree from its settings (both variants)"
    every: BoolProperty(default=False)

    def execute(self, context):
        keys = [s[0] for s in treegen.SPECIES] if self.every else [context.scene.tree_editor.species]
        for key in keys:
            rebuild(key, context.scene)
        return {"FINISHED"}


class TREES_OT_reset(bpy.types.Operator):
    bl_idname = "trees.reset"
    bl_label = "Reset"
    bl_description = "Back to the default settings for this tree"

    def execute(self, context):
        key = context.scene.tree_editor.species
        fill_settings(context.scene, {key: treegen.DEFAULTS[key]})
        treegen.materials_for(key, treegen.DEFAULTS[key])
        rebuild(key, context.scene)
        return {"FINISHED"}


class TREES_OT_save(bpy.types.Operator):
    bl_idname = "trees.save"
    bl_label = "Save settings"
    bl_description = "Write every tree's settings to tree_settings.json, for make_trees.py's next build"

    def execute(self, context):
        out = {s.name: as_cfg(s) for s in context.scene.tree_editor.trees}
        with open(treegen.SETTINGS, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(out, fh, indent=1)
        self.report({"INFO"}, "Saved " + treegen.SETTINGS)
        return {"FINISHED"}


class TREES_OT_frame(bpy.types.Operator):
    bl_idname = "trees.frame"
    bl_label = "Frame tree"
    bl_description = "Select the tree and zoom the view to it"

    def execute(self, context):
        ob = bpy.data.objects.get(context.scene.tree_editor.species + "_A")
        if ob is None:
            return {"CANCELLED"}
        for o in context.selected_objects:
            o.select_set(False)
        ob.select_set(True)
        context.view_layer.objects.active = ob
        if context.area and context.area.type == "VIEW_3D":
            bpy.ops.view3d.view_selected()
        return {"FINISHED"}


class TREES_OT_setup(bpy.types.Operator):
    bl_idname = "trees.setup"
    bl_label = "Set up the editor"
    bl_description = "Load the saved settings into this file"

    def execute(self, context):
        fill_settings(context.scene)
        return {"FINISHED"}


class VIEW3D_PT_tree_editor(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Trees"
    bl_label = "Tree editor"

    def draw(self, context):
        lay = self.layout
        ed = context.scene.tree_editor
        lay.prop(ed, "species", text="")
        s = ed.trees.get(ed.species)
        if s is None:
            lay.operator("trees.setup", icon="IMPORT")
            return
        names = treegen.card_names().get(treegen.BY_KEY[ed.species][6], [])
        lay.template_icon_view(s, "card", show_labels=True, scale=6.0, scale_popup=5.0)
        n = int(s.card)
        lay.label(text=f"Card {n}: {names[n - 1]}" if n <= len(names) else f"Card {n}")

        sprays = ed.species in treegen.PINNATE and s.layout == "pinnate"
        if ed.species in treegen.PINNATE:
            lay.prop(s, "layout", expand=True)
        box = lay.box()
        if sprays:
            box.label(text="Sprays along the branches", icon="OUTLINER_OB_POINTCLOUD")
            col = box.column(align=True)
            col.prop(s, "size", text="Spray length", slider=True)
            col.prop(s, "planes", text="Cards per spray", slider=True)
            col.prop(s, "spacing", slider=True)
            col.prop(s, "spray_angle", slider=True)
            col.prop(s, "droop", slider=True)
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
        box.label(text="Leaf colour", icon="COLOR")
        col = box.column(align=True)
        col.prop(s, "hue", slider=True)
        col.prop(s, "saturation", slider=True)
        col.prop(s, "brightness", slider=True)

        box = lay.box()
        box.label(text="Tree", icon="OUTLINER_OB_FORCE_FIELD")
        col = box.column(align=True)
        col.prop(s, "height", slider=True)
        col.prop(s, "width", slider=True)
        if ed.species == "Rowan":
            col.prop(s, "berries", slider=True)
        col.prop(s, "seed")

        ob = bpy.data.objects.get(ed.species + "_A")
        if ob is not None and ob.type == "MESH":
            me = ob.data
            leaves = sum(1 for p in me.polygons if p.material_index > 0)
            lay.label(text=f"{leaves} leaf cards, {len(me.polygons)} faces, {ob.dimensions.z:.1f} m tall")
        else:
            lay.label(text="This file has no " + ed.species + "_A to edit", icon="ERROR")
        row = lay.row(align=True)
        row.operator("trees.frame", icon="ZOOM_SELECTED")
        row.operator("trees.rebuild", icon="FILE_REFRESH")
        row = lay.row(align=True)
        row.operator("trees.reset", icon="LOOP_BACK")
        row.operator("trees.save", icon="FILE_TICK")
        lay.prop(ed, "live")


CLASSES = (TreeSettings, TreeEditor, TREES_OT_rebuild, TREES_OT_reset, TREES_OT_save, TREES_OT_frame, TREES_OT_setup, VIEW3D_PT_tree_editor)


@bpy.app.handlers.persistent
def _on_load(_):
    for scene in bpy.data.scenes:
        if hasattr(scene, "tree_editor") and not scene.tree_editor.trees:
            fill_settings(scene)


def register():
    global PREVIEWS
    if hasattr(bpy.types, "VIEW3D_PT_tree_editor"):  # registered before: start clean
        unregister()
    PREVIEWS = bpy.utils.previews.new()
    names = treegen.card_names()
    for key, *_rest in treegen.SPECIES:
        card = treegen.BY_KEY[key][6]
        items = []
        labels = names.get(card) or [str(n) for n in range(1, 6)]
        for n, label in enumerate(labels, 1):
            path = os.path.join(treegen.TEXTURES, f"{card}_{n}.png")
            show = os.path.exists(path) and not bpy.app.background  # no thumbnails needed without a window
            icon = PREVIEWS.load(f"{card}_{n}", path, "IMAGE").icon_id if show else 0
            items.append((str(n), f"{n}  {label}", label, icon, n))
        CARD_ITEMS[key] = items
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.Scene.tree_editor = PointerProperty(type=TreeEditor)
    if _on_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_on_load)
    bpy.app.timers.register(lambda: _on_load(None), first_interval=0.1)  # the open file, once Blender is ready


def unregister():
    global PREVIEWS
    if _on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load)
    if hasattr(bpy.types.Scene, "tree_editor"):
        del bpy.types.Scene.tree_editor
    for name in [c.__name__ for c in reversed(CLASSES)]:
        cls = getattr(bpy.types, name, None)
        if cls is not None:
            bpy.utils.unregister_class(cls)
    if PREVIEWS is not None:
        bpy.utils.previews.remove(PREVIEWS)
        PREVIEWS = None


if __name__ == "__main__":
    register()
