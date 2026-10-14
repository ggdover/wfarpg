# Plant portfolio

Low-poly bushes and grasses of the Swedish forest, made the way the tree portfolio's trees are (`../trees`): their
leaves, fronds, strands and blades are painted cards with alpha, crossed in clumps, patches and tufts, on faceted
low-poly stems. Two variants of each:

| Plant | Swedish | Latin | Kind |
|---|---|---|---|
| Raspberry | Hallon | Rubus idaeus | bush: a thicket of arching canes, toothed leaves with pale undersides, red berries |
| Alder buckthorn | Brakved | Frangula alnus | bush: slender dark stems, glossy oval leaves, berries green, red and black at once |
| Hazel | Hassel | Corylus avellana | bush: many stems from one wide foot, a full mass of broad round leaves, nuts in husks |
| Wood fern | Skogsbräken | Dryopteris carthusiana | fern: a ring of fronds rising and arching over |
| Long grass | Långt gräs | Poa, Festuca, Agrostis | a patch of thick, semi-long grass: cards of thin strands; B with seed heads. The game's first try |
| Grass: wisps | Gräs: glesa strån | Poa, Festuca, Agrostis | the game's subtlest grass: sparse long strands, on a ground of fine loose strands |
| Grass: tufts | Gräs: tuvor | Poa, Festuca, Agrostis | tufts of strands fanning from their feet, on a ground of flattened tufts |
| Grass: clumps | Gräs: klungor | Poa, Festuca, Agrostis | the thickest: a meadow of strands, on a ground combed one way a clump at a time |
| Grass: short | Gräs: kort | Poa, Festuca, Agrostis | a short lawn, on a ground of short strokes |
| Grass: bog | Gräs: myr | Carex, Trichophorum, Molinia | the bog's golden sedge: fine strands fanning from a tussock's foot and arching over, a few pale and dry, a few still green, on a ground of them lying in stars |
| Wavy hair-grass | Kruståtel | Avenella flexuosa | grass: the pine forest's, hair-thin curling blades, airy purple-silver flowers |
| Common bent | Rödven | Agrostis capillaris | grass: the meadows', narrow blades, airy reddish flowers |
| Wood small-reed | Piprör | Calamagrostis arundinacea | grass: tall at the forest's edge, broad arching blades |
| Purple moor-grass | Blåtåtel | Molinia caerulea | grass: tussocks on wet ground, gold in autumn, dark purple flowers |
| Common sedge | Hundstarr | Carex nigra | sedge: stiff blue-green blades by water, dark brown spikes |
| Hare's-tail cottongrass | Tuvull | Eriophorum vaginatum | the bog's tussocks, white tufts of cotton |

What the user made of the first version (10 October): the wood fern can work in occasional places; blueberry,
lingonberry and heather didn't represent anything they wanted, so they're gone; the buckthorn and the hazel were fine
but thin at the bottom, so they're now much fuller, widest at the foot, about as big as before; the raspberry was too
small to count as a bush, so it's now a thicket nearly 3 m across. And they missed plain strands of grass, thick and
semi-long, to cover the green ground in the game and fold as the hero walks through: the long grass, which the game
now has (`game/scripts/grass.gd`, below). (The juniper, dropped from the trees, could join the bushes.)

The long grass in the game didn't blend into the ground, the user found: its cards showed as crossed planes, in
colours of their own, over a ground too smooth. They asked for the grass in the ground's own colour, fewer strands
a card so more of it is clear and the ground shows through, fewer patches, each card at its own angle, and the ground
textured to match, and for a few versions to try. So there are four grass styles (wisps, tufts, clumps, short), each
with a ground texture of its strands lying flat as seen from above, in the same colours as its cards: the game lays it
over its green ground and colours both by the ground's own colour (`game/README.md`, The grass). The long grass stays
as the first try, to compare. The user liked clumps best (14 October), so the game has it by default, and the forest
floor here is covered in it. They also asked for a yellow grass that fits the bog, made the same way: the bog grass,
golden sedge, painted round a golden colour instead of the green, which the game grows on the bog's golden ground, in
tussocks.

Open `plant_portfolio.blend` in Blender 5.2 to look at them. It opens on the bushes with Material Preview shading.
The file holds:

- `Bushes` and `Grasses`: one collection per plant with variants A and B, each one object on its own origin.
- `Portfolio`: three rows, the bushes, the long grass and the fern, the grasses, with name signs and a 1.8 m person at
  the start of each; the ground, the sun and the cameras.
- `Forest floor`: a patch of forest floor 16 by 12 m covered in grass, as the game's green ground is: Clumps, on its
  ground texture (a patch as far apart as its Patch spacing says), with copies of the rest where each grows
  (ferns in the spruce's shade, the bushes at the edges, moor-grass, sedge and cottongrass by a wet hollow), under four
  of the tree portfolio's trees, linked from `../trees/tree_portfolio.blend`. The plants share their mesh with those
  in `Bushes` and `Grasses`, so editing a plant changes its copies too. Its cameras look at it from the game's high
  camera and from close by.

## Plant editor

The editor is a **Plants** tab in the 3D viewport's sidebar, as the tree editor is a Trees tab. To get it:

1. Open `plant_portfolio.blend`. Blender warns that the file's scripts were not run: click **Allow Execution**. (Or
   start Blender with `blender plant_portfolio.blend --python plant_editor.py`.)
2. Press **N** in the 3D viewport for the sidebar, and pick the **Plants** tab.

Pick **Bushes** or **Grasses**, a plant, and one of its four cards from the thumbnails, then move the sliders. Both
variants, and their copies on the forest floor, rebuild as you go.

The bushes (raspberry, alder buckthorn, hazel) have the trees' clump sliders:

| Setting | What it does |
|---|---|
| Card size | How big each clump's cards are |
| Cards per clump | How many copies of the card cross in each clump; more makes a fuller, rounder clump |
| Clumps | How many clumps grow at each spot; above 1 they gather into patches |
| Patch spread | How far a patch's clumps spread |
| Clump height | Height of the upright cards; lower makes flatter, pad-like clumps |
| Angle randomness | How much the cards' angles vary |
| Flat card on top | One card per clump lies nearly flat, so clumps look full from the high game camera |
| Height, Width | Scale the bush: how high and how far out its dome reaches |
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

The long grass, a patch of it:

| Setting | What it does |
|---|---|
| Blade height | How tall the strands stand |
| Card width | How wide each card of strands is |
| Cards per patch | How many cards cross in the patch |
| Lean | How far its cards lean out from upright |
| Bend | How far they bend over halfway up (each card is bent once) |
| Angle randomness | How much the cards' angles vary |
| Card turn randomness | How far each card is turned its own way rather than spread evenly round (1: anywhere); the game turns and leans every card of every patch at random by as much again |
| Patch spacing | How far apart the patches stand, on the forest floor and in the game: 0.5 m times this |
| Patches with seed heads | The long grass: the share of the patches that are variant B, with a card of seed heads, on the floor and in the game |
| Seed head height | The long grass: how tall the seed heads stand, against the strands |

The grass styles have no seed heads: their variant B is another patch of the same kind. Their colour sliders tint
their ground texture as they do their cards.

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
  cluster round the card's centre; a grass's tuft and the fern's frond grow from the middle of the card's foot; the
  long grass's thin strands stand in a row all along it, each darker at its foot and lighter toward its tip, so
  crossed copies make a patch rather than a star. Its cards are cropped to their strands (the empty top, and the
  seed heads' empty sides), as every pixel of a card costs the game, empty or not; `cards.json` keeps how much each
  kept, and the patch sizes its cards by that. Each
  bush's card has a version with its berries, flowers or nuts drawn on, and a share of its clumps use it (berries in
  patches, sitting on the bushes, as the board asks); a grass's flowers are a card of flowering stalks of their own.
  The transparent pixels carry the card's average colour, so filtered edges don't get dark fringes (unlike the trees'
  cards, see `../trees/README.md`).
- **Bushes:** stems from a wide foot, leaning out, branching all the way down, with crossed clumps along and at the
  ends of the branches, filling a dome widest at its foot: the lowest branches are the longest, nearly level and
  drooping to the ground, the higher ones shorter and rising, each as long as reaches the dome's outline at its tip's
  height. The raspberry's canes arch up and over, and short new shoots round its edge fill it down to the ground. The
  cards' normals point out from the bush's foot, so it shades as one rounded mass.
- **The long grass:** a patch of three cards of strands crossing near its middle (their feet a little apart, so it's
  no star from above), each leaning a little and bent once halfway up; variant B has two cards of seed heads across
  each other among them. Its normals point mostly up.
- **The grass styles:** patches as the long grass's, of two or three cards with fewer strands (12 to 30 a card, wider,
  so they still show from the game's camera), each card turned its own way (Card turn randomness). Their cards and
  their ground texture (`textures/<style>_ground.jpg`, 4 m across, seamless) are painted round one base colour, the
  strands' feet in it and their tips about 1.5 times as light: the ground is the same strands lying flat as seen from
  above (loose, as tufts, or combed in clumps), on lighter and darker blotches a clump of grass across, so it has
  texture at the size the game's camera sees.
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
| `plantgen.py` | The generator: the eleven plants, their kinds, the default settings and the materials |
| `plant_editor.py` | The editor panel; the .blend loads it through its `plant_editor_loader.py` text |
| `make_plants.py` | Builds `plant_portfolio.blend` from the settings and renders `previews/` |
| `make_plant_cards.py` | Draws the cards: `textures/<plant>_<n>.png`, their `_berries`, `_flowers` and `_nuts` versions, the grass styles' grounds (`textures/<style>_ground.jpg`), `textures/cards.json` (the designs' names, the grass cards' crops and the grounds) and `previews/cards.png`, `previews/grounds.png` |
| `make_sheet.py` | Lays out the portraits in `previews/tiles/` as `previews/portfolio.png` |
| `plant_settings.json` | The editor's saved settings (written by **Save settings**) |

## Rebuilding

```sh
python3 make_plant_cards.py                         # the cards and previews/cards.png (needs Pillow)
blender -b --factory-startup -P make_plants.py      # plant_portfolio.blend and the renders in previews/
blender -b --factory-startup -P make_plants.py -- --no-render
```

The plants use fixed seeds, so rebuilding gives the same plants (those left from the first version still grow as
they did). `previews/` holds the latest renders: `portfolio.png` (both variants of each, captioned), `row_bushes.png`,
`row_grass_fern.png` and `row_grasses.png`, `floor_game_view.png` and `floor_close.png`, `cards.png` and
`grounds.png` (the grass styles' grounds, each with a card on it).

The game builds its long grass from these settings too: after changing them, save, and rebuild the game's plants
(`blender -b --factory-startup -P build_demo.py -- plants` in `game/tools`).

## Sizes (variant A, with the saved settings)

| Plant | Height | Across | Cards | Faces |
|---|---|---|---|---|
| Raspberry | 1.7 m | 3.0 m | 312 | 848 |
| Alder buckthorn | 2.8 m | 2.9 m | 309 | 1020 |
| Hazel | 3.6 m | 4.4 m | 591 | 1764 |
| Wood fern | 53 cm | 1.4 m | 27 | 27 |
| Long grass, a patch | 37 cm | 0.8 m | 6 | 6 |
| Grass: wisps, a patch | 37 cm | 0.7 m | 6 | 6 |
| Grass: tufts, a patch | 34 cm | 0.5 m | 6 | 6 |
| Grass: clumps, a patch | 43 cm | 0.6 m | 6 | 6 |
| Grass: short, a patch | 26 cm | 0.4 m | 6 | 6 |
| Grass: bog, a patch | 42 cm | 0.7 m | 6 | 6 |
| Wavy hair-grass | 51 cm | 0.7 m | 42 | 42 |
| Common bent | 52 cm | 0.7 m | 34 | 34 |
| Wood small-reed | 96 cm | 1.0 m | 28 | 28 |
| Purple moor-grass | 67 cm | 0.6 m | 36 | 36 |
| Common sedge | 41 cm | 0.7 m | 32 | 32 |
| Hare's-tail cottongrass | 46 cm | 0.5 m | 40 | 40 |

Heights are to the top of the cards, flowers included (the long grass's patch without its seed heads). The grasses
are about their real size, a little more; the bushes, like the trees, a little smaller than life, for the high game
camera (the hazel and the buckthorn about as big as in the first version, but full down to the ground). Only the grass
styles are in the play demo so far, covering its green ground, and the bog grass its bog: its heather and ferns are
still the mockups' faceted shapes, and its faceted shrubs and berry bushes are gone.
