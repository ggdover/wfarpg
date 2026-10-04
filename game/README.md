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
godot --path game res://scenes/demo.tscn -- --theme=Brown_earth   # with one of the path colours (_ for spaces)
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
| P | Change the paths' colours (eight themes, below) |
| F2 | The performance panel (below) |
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
  - Its large-scale colours are baked from Blender into textures: moss, grass patches and the meadow. Where the
    trails wear the grass, the bake keeps the noise and how far each spot is from a trail's centre line
    (`path_noise.png`, `masks.png`) instead of the colours, so the game can paint the trails in any of the path
    colours, and spread their wear further into the grass than the mockups do.
  - `shaders/ground.gdshaderinc` draws the trails and the small things on top with the same formulas, so they stay
    sharp up close: the trampled grass and dirt, gravel and pebbles, grit, and fallen leaves. It uses a port of
    Blender's noise (`shaders/blender_noise.gdshaderinc`), and comes in four levels of detail (below).
- **Light:** `scripts/mood.gd` copies the mockups' daylight: the sun, a plain ambient colour, the gradient sky with
  clouds, haze, and AgX tone mapping.
- **Shading under the trees:** Godot's ambient light isn't blocked by geometry, unlike Eevee's, so the build bakes
  it instead.
  - Into each tree's vertices: how much of the sky each leaf and branch can see.
  - Into the ground: how much the trees shade each spot, separately for each tree set.
- **Trees and the camera:**
  - A tree fades out whole once some part of it, a leaf card, a branch or the trunk, is between the camera and the
    hero, and comes back once it's out of the way; its shadow stays. Not before: the trees the hero walks towards
    stay until they're actually in the way. Lines from the camera to a grid of points over the hero, as the camera
    sees it, are tested against the tree's own triangles, in the version that's drawn, with square leaf cards, which
    contain whatever of a card shows (`update_sight` in `scripts/world.gd`).
  - Whatever the camera is about to touch, within about 2.5 m of it, fades too.
  - The mockups also hide the trees near a high camera. The demo can, with the panel's "Fade trees near camera",
    though never within 6 m of the hero; it's off, as trees should only go once they're in the way.
  - Trees fade in patches a few tenths of a metre across rather than in a dither of single pixels, which the
    ambient occlusion turned into black specks.

Where it differs on purpose:

- **Softer sun:** the sun is 0.6° wide instead of 2.5°, because wider shadows come out grainy in Godot.
- **Saturation:** colours are lifted by 1.2 to match Blender's AgX "Medium High Contrast" look.
- **Leaf texture edges:** Godot's fix for colour bleeding at the leaf edges is turned off (`project.godot`).
  The leaf cards' transparent pixels are black, so in Blender the black seeps into the leaf edges and darkens the
  crowns. With the fix off, Godot shows the trees as you tuned them.

## The performance panel (F2)

A frame-time graph of the last 3 seconds (one bar per frame: green is faster than 60 fps, amber than 30, red
slower), with the frame rate now, on average, and in the slowest 5% and 1% of frames. Below the graph: how long the
graphics card takes per frame, the triangles drawn and the draw calls. Every switch below takes effect at once:

| Switch | What it does |
|---|---|
| Trees | The old or the new trees (as T) |
| Path colours | The paths' colour theme (as P) |
| Path wear spread | How far the paths' wear spreads into the grass: 0 as in the mockups, up to 1 (the default), where the trampled grass, bare patches and stray stones reach further out and break up in patches, so it's less clear exactly where a path runs |
| Leaf cards | Square cards, or cards trimmed to an outline round their leaves: the same look, fewer pixels to draw |
| Cards per clump | As tuned, or about half as many (a little bigger): sparser crowns |
| Tree shadows from | Which version of a new tree casts its shadow: the full one, the mid one, the far one, or none |
| Lighter trees from | Where the new trees switch to their lighter versions |
| Fade trees near camera | The mockups' fade of trees near a high camera, though never within 6 m of the hero. Off by default, as trees should only go once they're in the way |
| Trees in the way | Hide the whole of every tree that's in the way between the camera and the hero (the default), or keep them. **Clear round the hero** also keeps the ground that far round the hero clear of trees; 0 m, the default, is the hero alone |
| Render scale | 100%, 75% or 50% of the window's pixels, scaled up with FSR |
| Antialiasing, VSync, Shadows | Godot's own settings. VSync starts off, so the frame rate isn't held to the screen's |
| Frame rate limit | The most frames a second to draw, from 30 to 250; at the slider's right end, none (the default) |
| Shadow distance | How far from the camera shadows reach. **Fit the view** follows what the camera sees, up to the slider's distance, so the shadows round the hero never go; **Fixed** uses the slider's distance |
| Shadow resolution | The size of the sun's shadow map: less detailed, softer-edged shadows at 1024 and 512, but all of them still there |
| Shadow softness | Hard, low or high: how many samples soften the shadows' edges |
| Shadow cascades | 1, 2 or 4: more cascades keep near shadows sharp while reaching far, for more drawing |
| Ground details | How much the ground shader draws on the paths and the grass (below) |
| Ambient occlusion | Godot's screen-space ambient occlusion: off, or very low to high quality |
| Haze | The fog |

The ground details come at four levels, each its own compiled shader, so a lower level doesn't pay for what it skips:

| Level | What it draws |
|---|---|
| High | Everything: three sizes of stones with exact, slightly wavy outlines, grit between them, fallen leaves, and bumps that catch the light |
| Medium | The small and big stones, with simpler outlines, and the fallen leaves: no flat stones, grit or bumps. It looks almost the same |
| Low | The small stones and the fallen leaves; the bigger stones become an even colour |
| Off | The dirt and grass colours only |

Each level also stops drawing details further from the camera (High at 50 m, Medium 38 m, Low 28 m).

**Walk the trail** walks from the start to the meadow the same way every time and lists the result with the settings,
so runs compare fairly. With VSync off and no frame rate limit (the defaults), the frame rate goes as high as the
graphics card allows. The hero moves in the physics' 60 steps a second and is drawn between them (physics
interpolation, `project.godot`), so walking stays smooth at any frame rate. `--paneltest` presses every switch in turn
and prints what each costs, and checks the frame rate limit.

## Path colours

P (or the panel) cycles through eight colour themes for the paths, from dark brown to sandy. They're in
`scripts/path_themes.gd`: the dirt (and a second soil in patches through it, if any), the trampled grass beside it,
the grit, the gravel's shadow and the stones' colours, how many stones of each size, and how many fallen leaves.
The demo starts with Forest earth.

| Theme | Look |
|---|---|
| Forest soil | Dark, packed forest soil with grey-brown stones and more fallen leaves |
| Forest earth | Forest soil and brown earth mixed: patches of dark, packed soil in medium brown earth, with more of it toward the edges, and grey-brown and pale stones |
| Brown earth | Medium brown earth with pale, sandy stones |
| Iron soil | Warm, rusty brown soil, as where the ground is rich in iron, with grey granite stones |
| Granite gravel | A grey-beige gravel track of crushed granite, grey and pink, with more stones |
| Esker sand | Pale sand and gravel, as on the eskers, with grey-brown pebbles |
| Sandy, mixed stones | The light tan paths' sandy dirt, with stones of mixed browns and greys standing out from it |
| Light tan | The mockups' paths: light tan dirt with gravel in the same tones |

## Speed

The new trees cost much more than the old ones, mostly from overlapping leaf cards. On this laptop's integrated
graphics (Intel Arc 140V) at 1600 × 900, with VSync off, no frame rate limit and nothing else running:

- **Old trees:** about 100 fps at the start, in the thicket.
- **New trees:** about 51 fps at the start. Walking the trail from there to the meadow averages 65 fps, with the
  slowest 1% of frames at 42.

To keep it there:

- **Lighter versions:** each new tree has two, with fewer, bigger leaf cards, used from 45 m and 120 m.
- **Trimmed cards:** every version also comes with its cards cut to the outline round their leaves (`trees_trim.glb`),
  and the full trees come with fewer cards per clump too (`trees_few.glb`), for trying in the performance panel.
- **Shadows:** the full tree casts its shadow from the lighter version.
- **Hidden trees:** trees hidden because they're in the way, or faded out near the camera, aren't drawn at all,
  apart from their shadows. Working out which trees are in the way takes 0.1–0.5 ms a frame in the forest; the
  trees' shapes for it are worked out as they load (about 60 ms for both sets).

The biggest costs after the trees, measured with the panel at the start (time per frame on the graphics card, against
the defaults' 19.1 ms):

- **Ground details:** Medium saves 3.5 ms (63 fps), Low 3.6 and Off 4.2. Medium keeps nearly all of the look, so it
  gets nearly all of Off's speed without losing the gravel and leaves.
- **Shadows:** off saves 5.4 ms (71 fps). A 1024 shadow map saves 2.1 ms against 2048, and 4096 costs 8.7 ms more.
  Fitting the distance to the view saves 1.6 ms against a fixed 70 m. Tree shadows from the far versions save 1.2 ms,
  none at all 4.8.
- **Ambient occlusion:** off saves 3.4 ms (62 fps), very low 0.2; high costs 2.5 ms more.
- **Render scale:** 75% saves 4.0 ms (65 fps), 50% 8.1 (88 fps).
- **Leaf cards:** trimmed cards save 3.0 ms (61 fps), fewer cards per clump 2.2.
- **Fade trees near camera:** on, it costs 1.6 ms, from the trees half faded near the camera.

## Rebuilding the assets

Everything in `assets/kit`, `assets/trees`, `assets/ground` and `data` is generated from code. Rebuild it after
changing the trees, the mockups' kit or the area. Run from `game/tools`, with Blender 5.2:

```sh
blender -b --factory-startup -P build_demo.py -- models   # the old kit and the portfolio trees (.glb), with baked occlusion
blender -b --factory-startup -P build_demo.py -- layout   # where every tree, rock and plant stands
blender -b --factory-startup -P build_demo.py -- ground   # heights, ground textures and the trees' shade (after layout)
blender -b --factory-startup -P build_demo.py -- masks    # only the paths' wear masks (masks.png), in a few seconds
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
| `scripts/perf_panel.gd`, `scripts/trail_walk.gd` | The performance panel, and the walk along the trail it uses |
| `scripts/path_themes.gd` | The paths' colour themes |
| `scripts/models.gd`, `scripts/mood.gd` | Loading the models with the game's materials; the light |
| `scripts/game.gd` | Settings shared by the scenes, and the controls |
| `shaders/` | Ground (`ground.gdshaderinc`, compiled at four levels of detail: `ground`, `ground_medium`, `ground_low`, `ground_flat`), leaves, the low-poly material, sky, Blender's noise |
| `scripts/dev/` | `selftest.gd` (`--selftest` tries every control and checks it), `walktest.gd` (`--walktest` walks the trail and prints the frame times; add `--treelod=1` or `2` to try the lighter trees), `paneltest.gd` (`--paneltest`) and `lineup.gd` (models in rows, for comparing with Blender) |
| `tools/` | The Blender build scripts (Godot ignores this folder) |
| `assets/`, `data/` | Generated models, textures, heights and layout; Cinzel in `assets/fonts` (SIL Open Font License) |
