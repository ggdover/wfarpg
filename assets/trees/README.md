# Tree portfolio

Low-poly trees of the Swedish forest, after `ref_imgs/Trees of the Swedish Forest.png`: Scots pine, silver birch,
Norway spruce, aspen, rowan, alder and juniper, two variants of each.

Open `tree_portfolio.blend` in Blender 5.2 to look at them. It opens on the first row with Material Preview shading, so
the leaves show. The file holds:

- `Trees`: one collection per species with variants A and B. Each tree is one object standing on its own origin.
- `Portfolio`: the two rows with name signs, a 1.8 m person beside each tree, the ground, the sun and the cameras.
- `Grove`: about 30 linked copies mixed into a small stand of forest, with a camera at the game's angle. They share
  their mesh with the trees in `Trees`, so editing a tree changes its copies too.

## How the trees are built

- **Trunk and branches:** low-poly tubes with 3 to 7 sides, flat shaded and coloured per face through the `Col`
  colour attribute (material `Bark`).
- **Leaf clumps:** crossed planes. Each clump is three copies of the species' leaf card crossing at the clump's
  centre: one lying nearly flat, for the view from above, and two upright at right angles to each other. The leaf
  materials (`Leaves_<card>`) cut the card out at alpha 0.5, like alpha clip in a game engine, and draw both sides.
- **Shading:** the cards' normals point out from the crown (custom normals), so a crown shades as one rounded
  volume instead of as many flat cards.

## Rebuilding

```sh
python3 make_leaf_cards.py                          # textures/*.png and previews/leaf_cards.png (needs Pillow)
blender -b --factory-startup -P make_trees.py       # tree_portfolio.blend and the renders in previews/
blender -b --factory-startup -P make_trees.py -- --no-render
```

`make_trees.py` runs `make_sheet.py` (system Python with Pillow) to lay out the portraits in `previews/tiles/` as
`previews/portfolio.png`. The trees use fixed seeds, so rebuilding gives the same trees.

## Sizes (variant A)

| Tree | Height | Leaf cards | Faces |
|---|---|---|---|
| Scots pine | about 18 m | 117 | 758 |
| Silver birch | about 14 m | 210 | 946 |
| Norway spruce | about 17 m | 1791 | 4580 |
| Aspen | about 15 m | 225 | 683 |
| Rowan | about 10 m | 159 | 487 |
| Alder | about 12 m | 222 | 650 |
| Juniper | about 4 m | 342 | 848 |

Heights are about 70% of real trees, to suit the high game camera. The spruce is by far the heaviest; a large forest
would need lighter versions of it (and the others) for trees far from the camera.
