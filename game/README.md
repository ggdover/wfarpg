# wfarpg: the play demo

A first playable piece of Act 1, in Godot: a small part of Storskogen, about 155 × 110 m to walk.

- **Tätskogen-like forest** in the west: dense pine and spruce, berry bushes, mossy boulders and fallen logs.
  A winding trail runs through it, with a fork to the north.
- **Stora ängen-like meadow** in the east: open grass with lone trees, boulders and a low rise you can walk up.
  Birch, aspen, rowan and alder grow along the forest's edge.
- **Two versions of the same place:**
  - the old trees, the low-poly ones from the mockup screenshots;
  - the new trees, the tree portfolio built in Blender (`assets/trees`).
  - Every tree stands on the same spot in both.
  - Pick a version on the start screen, or press **T** in the game to swap them where you stand.
- **Everything else is shared:** the ground, rocks, bushes, grass and props come from the mockups.
- **The hero** is a grey box for now, with a dark band on its front.

## Running it

It needs Godot 4.7, the standard build without .NET. This machine has it at `~/.local/bin/godot`.

```sh
godot --path game                                  # from the repository root: plays the demo
godot -e --path game                               # opens the project in the editor (F5 plays)
godot --path game res://scenes/demo.tscn -- --trees=old   # straight into the demo, with the old trees
```

The first time, Godot imports the models and textures, which takes a minute. When running it from the command line
without ever opening the editor, run `godot --headless --import --path game` once first.

## Controls

The controls follow the mechanics and camera notes on the look & feel board.

| Key | What it does |
|---|---|
| W, A, S, D | Walk. W walks away from the camera, whichever way it faces |
| Right mouse button + move | Orbit the camera round the hero. Sideways turns the view; up and down changes the angle, from straight down to low behind the hero |
| Mouse wheel | Zoom |
| Left mouse button (hold) | "Attack": the hero turns to face the cursor and walks at 55% speed. There are no attacks yet |
| T | Swap the old and new trees |
| F1 | Show or hide the help |
| F3 | Frame rate |
| F4 | Render scale, 100% / 75% / 50%, for slower graphics cards |
| F12 | Screenshot (Godot's user folder, under `screenshots`) |
| Esc | Back to the start screen |

## How it matches the mockups

The demo reuses the mockups' own data and code wherever it can, and is checked against Blender renders of the same
place (`tools/reference_shots.py`).

- **Models:** exported from Blender as `.glb` by `tools/build_demo.py`, with the same builders that made the mockups
  (`mockups/forest_cam.py`, `act1_shots.py`) and the tree portfolio (`assets/trees/treegen.py`, your
  `tree_settings.json`).
  - Faceted models keep their per-face colours in the vertex colours.
  - Leaf cards use the portfolio's cards, cut out at alpha 0.5 as in Blender.
- **Ground:** the mockups' ground shader in two parts.
  - Its large-scale colours are baked from Blender into textures: moss, grass patches, the meadow, the trampled
    grass beside the trails, and the trails' dirt.
  - `shaders/ground.gdshader` draws the small things on top with the same formulas, so they stay sharp up close:
    gravel and pebbles, grit, and fallen leaves. It uses a port of Blender's noise
    (`shaders/blender_noise.gdshaderinc`).
- **Light:** `scripts/mood.gd` copies the mockups' daylight: the sun, a plain ambient colour, the gradient sky with
  clouds, haze, and AgX tone mapping.
- **Shading under the trees:** Godot's ambient light isn't blocked by geometry, unlike Eevee's, so the build bakes
  it instead.
  - Into each tree's vertices: how much of the sky each leaf and branch can see.
  - Into the ground: how much the trees shade each spot, separately for each tree set.
- **Trees and the camera:**
  - Trees between the camera and the hero get a round hole cut round the hero.
  - With the camera high up, trees near it fade out completely, as the mockups hide them; their shadows stay.

Where it differs on purpose:

- **Softer sun:** the sun is 0.6° wide instead of 2.5°, because wider shadows come out grainy in Godot.
- **Saturation:** colours are lifted by 1.2 to match Blender's AgX "Medium High Contrast" look.
- **Leaf texture edges:** Godot's fix for colour bleeding at the leaf edges is turned off (`project.godot`).
  The leaf cards' transparent pixels are black, so in Blender the black seeps into the leaf edges and darkens the
  crowns. With the fix off, Godot shows the trees as you tuned them.

## Speed

The new trees cost much more than the old ones, mostly from overlapping leaf cards. On this laptop's integrated
graphics (Intel Arc 140V) at 1600 × 900:

- **Old trees:** 60 fps everywhere.
- **New trees:** 45–55 fps in the thicket, 60 fps on the meadow.

To keep it there:

- **Lighter versions:** each new tree has two, with fewer, bigger leaf cards, used from 45 m and 120 m.
- **Shadows:** the full tree casts its shadow from the lighter version.
- **Faded trees:** trees faded out near the camera aren't drawn at all, apart from their shadows.

## Rebuilding the assets

Everything in `assets/kit`, `assets/trees`, `assets/ground` and `data` is generated from code. Rebuild it after
changing the trees, the mockups' kit or the area. Run from `game/tools`, with Blender 5.2:

```sh
blender -b --factory-startup -P build_demo.py -- models   # the old kit and the portfolio trees (.glb), with baked occlusion
blender -b --factory-startup -P build_demo.py -- layout   # where every tree, rock and plant stands
blender -b --factory-startup -P build_demo.py -- ground   # heights, ground textures and the trees' shade (after layout)
blender -b --factory-startup -P build_demo.py            # all three, in that order
```

The area itself, with its outline, trails, meadow, rise and how thick the forest grows, is data in
`tools/demo_area.py`. To compare the game with the mockups, render the same view both ways:

```sh
blender -b --factory-startup -P reference_shots.py -- ref.png -46,-15,225,55,20 old
godot --path .. res://scenes/demo.tscn -- --trees=old --shot=game.png --nohud --pose=-46,-15,225,55,20
```

A pose is the hero's Godot X and Z, then the camera's yaw, pitch and distance, as in the mockups.

## Files

| Path | What it is |
|---|---|
| `scenes/start.tscn`, `scenes/demo.tscn` | The start screen and the demo |
| `scripts/demo.gd` | The demo: builds the scene, the HUD, and the command-line options for checking it |
| `scripts/world.gd` | The area: terrain and collider, trees (with their lighter versions), rocks and plants, colliders, walls |
| `scripts/hero.gd`, `scripts/camera_rig.gd` | The hero and the camera |
| `scripts/models.gd`, `scripts/mood.gd` | Loading the models with the game's materials; the light |
| `scripts/game.gd` | Settings shared by the scenes, and the controls |
| `shaders/` | Ground, leaves, the low-poly material, sky, Blender's noise |
| `scripts/dev/` | `selftest.gd` (`--selftest` tries every control and checks it), `walktest.gd` (`--walktest=40` walks the trail and prints the frame times; add `--disable-vsync` before the scene path, and `--treelod=1` or `2` to try the lighter trees) and `lineup.gd` (models in rows, for comparing with Blender) |
| `tools/` | The Blender build scripts (Godot ignores this folder) |
| `assets/`, `data/` | Generated models, textures, heights and layout; Cinzel in `assets/fonts` (SIL Open Font License) |
