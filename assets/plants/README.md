# Plant portfolio

Low-poly bushes and grasses of the Swedish forest, made the way the tree portfolio's trees are (`../trees`): their
leaves, sprigs, fronds and blades are painted cards with alpha, crossed in clumps and tufts, on faceted low-poly stems.
Two variants of each:

| Plant | Swedish | Latin | Kind |
|---|---|---|---|
| Blueberry | Blåbär | Vaccinium myrtillus | dwarf shrub: a low mound of bright green sprigs, dark blue berries |
| Lingonberry | Lingon | Vaccinium vitis-idaea | dwarf shrub: a dense mat of dark, glossy leaves, red berries in clusters |
| Heather | Ljung | Calluna vulgaris | dwarf shrub: wiry sprigs; in flower, small pink-mauve bells, fine rather than in blocks |
| Raspberry | Hallon | Rubus idaeus | bush: arching canes, toothed leaves with pale undersides, red berries |
| Alder buckthorn | Brakved | Frangula alnus | bush: slender dark stems, glossy oval leaves, berries green, red and black at once |
| Hazel | Hassel | Corylus avellana | bush: many stems fanning out like a vase, broad round leaves, nuts in husks |
| Wood fern | Skogsbräken | Dryopteris carthusiana | fern: a ring of fronds rising and arching over |
| Wavy hair-grass | Kruståtel | Avenella flexuosa | grass: the pine forest's, hair-thin curling blades, airy purple-silver flowers |
| Common bent | Rödven | Agrostis capillaris | grass: the meadows', narrow blades, airy reddish flowers |
| Wood small-reed | Piprör | Calamagrostis arundinacea | grass: tall at the forest's edge, broad arching blades |
| Purple moor-grass | Blåtåtel | Molinia caerulea | grass: tussocks on wet ground, gold in autumn, dark purple flowers |
| Common sedge | Hundstarr | Carex nigra | sedge: stiff blue-green blades by water, dark brown spikes |
| Hare's-tail cottongrass | Tuvull | Eriophorum vaginatum | the bog's tussocks, white tufts of cotton |

(The juniper, dropped from the trees, could join them as a bush.)

Open `plant_portfolio.blend` in Blender 5.2 to look at them. It opens on the low plants with Material Preview shading.
The file holds:

- `Bushes` and `Grasses`: one collection per plant with variants A and B, each one object on its own origin.
- `Portfolio`: three rows, the low plants and the fern, the bushes, the grasses, with name signs and a 1.8 m person at
  the start of each; the ground, the sun and the cameras.
- `Forest floor`: a patch of forest floor 16 by 12 m with copies of them all where each grows (blueberry under the
  pines, lingonberry round a boulder, heather in the open, ferns in the spruce's shade, moor-grass, sedge and
  cottongrass by a wet hollow), under four of the tree portfolio's trees, linked from `../trees/tree_portfolio.blend`.
  The plants share their mesh with those in `Bushes` and `Grasses`, so editing a plant changes its copies too. Its
  cameras look at it from the game's high camera and from close by.

## Plant editor

The editor is a **Plants** tab in the 3D viewport's sidebar, as the tree editor is a Trees tab. To get it:

1. Open `plant_portfolio.blend`. Blender warns that the file's scripts were not run: click **Allow Execution**. (Or
   start Blender with `blender plant_portfolio.blend --python plant_editor.py`.)
2. Press **N** in the 3D viewport for the sidebar, and pick the **Plants** tab.

Pick **Bushes** or **Grasses**, a plant, and one of its four cards from the thumbnails, then move the sliders. Both
variants, and their copies on the forest floor, rebuild as you go.

The bushes (blueberry, lingonberry, heather, raspberry, alder buckthorn, hazel) have the trees' clump sliders:

| Setting | What it does |
|---|---|
| Card size | How big each clump's cards are |
| Cards per clump | How many copies of the card cross in each clump; more makes a fuller, rounder clump |
| Clumps | How many clumps grow at each spot; above 1 they gather into patches |
| Patch spread | How far a patch's clumps spread |
| Clump height | Height of the upright cards; lower makes flatter, pad-like clumps |
| Angle randomness | How much the cards' angles vary |
| Flat card on top | One card per clump lies nearly flat, so clumps look full from the high game camera |
| Height, Width | Scale the plant: a dwarf shrub's mound, a bush's stems and branches |
| Stems (Canes) | The bushes: how many stems grow from the foot |
| Berry clumps (Flowering clumps, Clumps with nuts) | The share of clumps with the card's berries, flowers or nuts |

The fern:

| Setting | What it does |
|---|---|
| Frond length | How long the fronds are |
| Fronds | How many fronds stand in the ring |
| Frond angle | How steeply they rise from the ground |
| Arch | How far they arch over (each frond is a card bent in three) |
| Angle randomness | How much the fronds' angles and roll vary |

The grasses:

| Setting | What it does |
|---|---|
| Blade height | How tall the tufts are |
| Tuft width | How wide each card is, for its height |
| Cards per tuft | How many cards cross in each tuft |
| Tufts | How many tufts the clump of grass has |
| Patch spread | How far apart they stand |
| Lean | How far a tuft's cards lean out from upright |
| Bend | How far they bend over halfway up (each card is bent once) |
| Angle randomness | How much the cards' angles vary |
| Tufts in flower | The share of tufts with a card of flowering stalks crossed among them |
| Stalk height | How tall the flowering stalks stand, against the blades |

All of them have **Hue, Saturation, Brightness** (instant: they only change the material) and **Seed**, which grows a
different plant of the same kind. **Frame plant** zooms to the plant, **Reset** goes back to the defaults, and **Save
settings** writes `plant_settings.json`, which the next full build (below) uses. Turn off **Update live** if a setting
makes the sliders slow, and press **Rebuild** instead. The plants are generated, so hand edits to their meshes are lost
when they rebuild.

## How the plants are built

`plantgen.py` builds on the tree generator (`../trees/treegen.py`): its faceted tubes and its crossed clumps.

- **Cards** (`make_plant_cards.py`): four designs per plant, 512 x 512 with alpha, in the tree cards' style: leaves as
  two flat halves, one lighter and one darker, crisp edges, no photographic noise; strokes are kept at least a few
  pixels wide, so thin needles and blades don't break up when the card is cut out. A bush's card is a sprig or a
  cluster round the card's centre; a grass's tuft and the fern's frond grow from the middle of the card's foot. Each
  bush's card has a version with its berries, flowers or nuts drawn on, and a share of its clumps use it (berries in
  patches, sitting on the bushes, as the board asks); a grass's flowers are a card of flowering stalks of their own.
  The transparent pixels carry the card's average colour, so filtered edges don't get dark fringes (unlike the trees'
  cards, see `../trees/README.md`).
- **Dwarf shrubs:** a low mound of crossed clumps over a patch of ground, their feet at the ground toward its edge, a
  few thin stems under them. The cards' normals point out from the mound's foot, so it shades as one rounded mound.
- **Bushes:** stems from the ground, branching, with crossed clumps along and at the ends of the branches, as a small
  tree's crown: the raspberry's canes arch over, the buckthorn holds its branches out level, the hazel's stems fan
  out like a vase.
- **The fern:** a ring of fronds from the middle, each a card bent in three, rising and arching over, its face up.
- **Grasses:** tufts of crossed cards standing on the ground, each bent once halfway up, so it arches, leaning a little
  to one side; a share of the tufts carry two crossed cards of flowering stalks, taller and nearly straight. Their
  normals point mostly up, so a tuft is lit as the ground under it is.
- **Materials:** `Stems <plant>` (the colour attribute, per face), `Leaves <plant>` and `Berries`, `Flowers` or
  `Nuts <plant>`: the card through a hue/saturation/value node (the colour sliders), cut out at alpha 0.5 like alpha
  clip in a game engine, both sides drawn (the trees' leaf material).

## Files

| File | What it is |
|---|---|
| `plantgen.py` | The generator: the thirteen plants, their kinds, the default settings and the materials |
| `plant_editor.py` | The editor panel; the .blend loads it through its `plant_editor_loader.py` text |
| `make_plants.py` | Builds `plant_portfolio.blend` from the settings and renders `previews/` |
| `make_plant_cards.py` | Draws the cards: `textures/<plant>_<n>.png`, their `_berries`, `_flowers` and `_nuts` versions, `textures/cards.json` (the designs' names) and `previews/cards.png` |
| `make_sheet.py` | Lays out the portraits in `previews/tiles/` as `previews/portfolio.png` |
| `plant_settings.json` | The editor's saved settings (written by **Save settings**) |

## Rebuilding

```sh
python3 make_plant_cards.py                         # the cards and previews/cards.png (needs Pillow)
blender -b --factory-startup -P make_plants.py      # plant_portfolio.blend and the renders in previews/
blender -b --factory-startup -P make_plants.py -- --no-render
```

The plants use fixed seeds, so rebuilding gives the same plants. `previews/` holds the latest renders: `portfolio.png`
(both variants of each, captioned), `row_plants.png`, `row_bushes.png` and `row_grasses.png`, `floor_game_view.png`
and `floor_close.png`, and `cards.png`.

## Sizes (variant A, with the saved settings)

| Plant | Height | Across | Cards | Faces |
|---|---|---|---|---|
| Blueberry | 59 cm | 1.3 m | 96 | 152 |
| Lingonberry | 41 cm | 1.0 m | 75 | 96 |
| Heather | 69 cm | 1.3 m | 69 | 132 |
| Raspberry | 1.4 m | 1.9 m | 105 | 280 |
| Alder buckthorn | 2.8 m | 2.6 m | 114 | 459 |
| Hazel | 3.5 m | 4.0 m | 198 | 823 |
| Wood fern | 53 cm | 1.4 m | 27 | 27 |
| Wavy hair-grass | 51 cm | 0.7 m | 42 | 42 |
| Common bent | 52 cm | 0.7 m | 34 | 34 |
| Wood small-reed | 96 cm | 1.0 m | 28 | 28 |
| Purple moor-grass | 67 cm | 0.6 m | 36 | 36 |
| Common sedge | 41 cm | 0.7 m | 32 | 32 |
| Hare's-tail cottongrass | 46 cm | 0.5 m | 40 | 40 |

Heights are to the top of the cards, flowers included. The low plants and grasses are about their real size, a
little more; the bushes, like the trees, a little smaller than life, for the high game camera. They are not in the
play demo yet: its bushes, berries, heather, ferns and grasses are still the mockups' faceted shapes.
