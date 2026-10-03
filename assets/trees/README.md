# Tree portfolio

Low-poly trees of the Swedish forest, after `ref_imgs/Trees of the Swedish Forest.png`: Scots pine, silver birch,
Norway spruce, aspen, rowan, alder and juniper, two variants of each.

Open `tree_portfolio.blend` in Blender 5.2 to look at them. It opens on the first row with Material Preview shading, so
the leaves show. The file holds:

- `Trees`: one collection per species with variants A and B. Each tree is one object standing on its own origin.
- `Portfolio`: the two rows with name signs, a 1.8 m person beside each tree, the ground, the sun and the cameras.
- `Grove`: about 30 linked copies mixed into a small stand of forest, with a camera at the game's angle. They share
  their mesh with the trees in `Trees`, so editing a tree changes its copies too.

## Tree editor

The editor is a **Trees** tab in the 3D viewport's sidebar. To get it:

1. Open `tree_portfolio.blend`. Blender warns that the file's scripts were not run: click **Allow Execution**. (Or
   start Blender with `blender tree_portfolio.blend --python tree_editor.py`.)
2. Press **N** in the 3D viewport for the sidebar, and pick the **Trees** tab.

Pick a tree at the top and one of its five leaf cards from the thumbnails, then move the sliders. Both variants of the
tree, and their copies in the grove, rebuild as you go:

| Setting | What it does |
|---|---|
| Card size | How big each leaf card is |
| Cards per clump | How many copies of the card cross in each clump; more makes a fuller, rounder clump |
| Clumps | How many clumps grow at each spot on the branches; above 1 they gather into patches |
| Patch spread | How far a patch's clumps spread; 1 fills the space one full-size clump would take |
| Clump height | Height of the upright cards; lower makes flatter, pad-like clumps |
| Angle randomness | How much the cards' angles vary |
| Flat card on top | One card per clump lies nearly flat, so clumps look full from the high game camera |
| Hue, saturation, brightness | The leaves' colour (instant: it only changes the material) |
| Tree height, crown width | Scale the tree and the length of its branches |
| Seed | Grows a different tree of the same kind |
| Berry clumps | Rowan only: the share of clumps with berries |

**Frame tree** zooms to the tree, **Reset** goes back to the defaults, and **Save settings** writes
`tree_settings.json`, which the next full build (below) uses. Turn off **Update live** if a heavy setting makes the
sliders slow, and press **Rebuild** instead. The trees are generated, so hand edits to their meshes are lost when they
rebuild.

## How the trees are built

- **Trunk and branches:** low-poly tubes with 3 to 7 sides, flat shaded and coloured per face through the `Col`
  colour attribute (material `Bark`).
- **Leaf clumps:** crossed planes. Each clump is several copies of the species' leaf card crossing at the clump's
  centre: one lying nearly flat, for the view from above, and the rest standing upright, spread evenly around. The
  leaf materials (`Leaves <tree>`) cut the card out at alpha 0.5, like alpha clip in a game engine, and draw both sides.
- **Shading:** the cards' normals point out from the crown (custom normals), so a crown shades as one rounded volume
  instead of as many flat cards.

## Files

| File | What it is |
|---|---|
| `treegen.py` | The generator: the seven species, the crossed-plane clumps, the materials and the default settings |
| `tree_editor.py` | The editor panel; the .blend loads it through its `tree_editor_loader.py` text |
| `make_trees.py` | Builds `tree_portfolio.blend` from the settings and renders `previews/` |
| `make_leaf_cards.py` | Draws the leaf cards: `textures/<card>_<1-5>.png`, rowan berry versions, `textures/cards.json` with their names |
| `make_sheet.py` | Lays out the portraits in `previews/tiles/` as `previews/portfolio.png` |
| `tree_settings.json` | The editor's saved settings (written by **Save settings**) |

## Rebuilding

```sh
python3 make_leaf_cards.py                          # the leaf cards and previews/leaf_cards.png (needs Pillow)
blender -b --factory-startup -P make_trees.py       # tree_portfolio.blend and the renders in previews/
blender -b --factory-startup -P make_trees.py -- --no-render
```

The trees use fixed seeds, so rebuilding gives the same trees. `previews/` always holds the latest renders; earlier
renders that are on the look & feel board are kept in `previews/v1/` and so on.

## Sizes (variant A, default settings)

| Tree | Height | Leaf cards | Faces |
|---|---|---|---|
| Scots pine | about 17 m | 880 | 1521 |
| Silver birch | about 14 m | 210 | 946 |
| Norway spruce | about 17 m | 1791 | 4580 |
| Aspen | about 15 m | 225 | 683 |
| Rowan | about 10 m | 159 | 487 |
| Alder | about 12 m | 222 | 650 |
| Juniper | about 4 m | 342 | 848 |

Heights are about 70% of real trees, to suit the high game camera. The spruce and the pine are the heaviest; a large
forest would need lighter versions of the trees far from the camera.
