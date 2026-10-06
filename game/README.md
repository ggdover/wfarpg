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
- **Trees and the camera:** once the trees in front of the hero cover enough of the area round it, two trees deep, each
  of them goes evenly see-through, standing on its stump (**See-through** in the panel; `update_sight`, `_cut_veil` and
  `_measure_area` in `scripts/world.gd`). No tree goes whole. Their shadows stay.
  - The area is the hero as the camera sees it, on a plane through its middle facing the camera (its width and height,
    or from above its footprint), and **area round hero** round that, its corners rounded: 1.5 m. Lines from the
    camera go to a grid of points across it (5 by 7, those inside its outline). A point is covered once two trees or
    more each hide it (**cover counts**: Two trees): by their bark, or by their leaves, where a leaf card's picture has
    a leaf, not by the gaps between the leaves (`_blocks`, against each card's picture at 128 pixels across). Once 40%
    of the points are covered (**see-through at**), every tree whose shape is on a line to any of them goes see-through
    over 0.15 s, and back as quickly once none is (after a quarter of a second) or the trees cover less than 20%
    (**solid again below**, at most see-through at; after a tenth). That margin keeps them from flickering while what
    they cover hovers round the bar as the hero walks. It's measured 30 times a second.
  - So a tree standing alone never goes see-through, however much of the hero it hides, while thick forest does, as
    the user asked: walking past a lone pine on the meadow, its crown passes close to the camera and hides the hero and
    much round it for a moment, which used to flip it see-through and back. These settings came from playtests
    (`scripts/dev/veiltune.gd` and `tools/veiltune.py`, below): along 160 walks under the trees standing alone, at
    four sides and two heights of the camera, the trees went see-through in 7 (in 154 before: 269 times, 47% of the
    time), all with the camera lower, where a tree further off makes a second layer; along the trail, at three heights
    of the camera, they were see-through about as much of the time as nothing of the hero showed (11% against 14%, 41%
    against 43%, 45% against 44%), going 11 times rather than 22; and of the moments where two trees or more hid the
    hero, they were see-through in 98%. Counting one tree's leaves (Leaves) or any part of a card (Whole cards, the
    way before, with 0 m, 90% and 72%) is in the panel to compare.
  - See-through is the cone's dither (below) evenly over the whole tree: half its pixels let through what's behind it,
    however many layers of leaves there are, where blending at half opacity would stack up over the overlapping leaf
    cards and stay nearly solid; and as every see-through tree lets the same pixels through, two in a row are as
    see-through as one. A see-through tree stands on its stump, the stump model with its pale cut top drawn at its foot
    (`_leave`), and its own bark goes see-through right down (`sight_veil` and `veil_fade` in the shaders): kept solid
    up to the cut, it would stand above the stump's slanted top on its low side.
  - A see-through tree is drawn near the camera with half its leaf cards (**see-through trees** in the panel, Fewer
    cards or All cards): the same cards, each where it was, with every other one, picked at random, left out. This
    thinned version is made as the models load, from the tree's own data byte for byte (`Models.thinned` in
    `scripts/models.gd`), so not a vertex moves. As the tree goes see-through, the cards it leaves out go first, twice
    as fast as the rest (`sight_thin` in `shaders/leaves.gdshader`; the full version marks them in UV2.y), so by the
    time it's as see-through as it goes they've gone, and drawing it as the thinned version from then on changes no
    pixel (`_thin_out` in `scripts/world.gd`); going back, the other way round. Its leaves never shift.
  - Why fewer cards: where a tree lets what's behind it through, each of its cards still runs its shader before it's
    thrown away, layer on layer, and with nothing in front to stop them, every see-through tree's do. Deep in the
    forest with the camera low, 6 to 10 trees see-through cost 7 to 10 ms a frame with all their cards, 4 to 6 with
    half (`scripts/dev/veilbench.gd`). It looks a touch more see-through than with all of them.
  - Before, a see-through tree swapped to its `_f` version, built anew with fewer, bigger cards per clump, which all
    stood in other places, so its leaves jumped as it went see-through. It cost the same. Leaving out the cards deepest
    in the crown rather than random ones would cost 2 to 3 ms less still, but bares the branches a spruce's inner
    sprays hide. And Godot's stencil, which could skip the let-through pixels before the cards' shaders run, can't be
    read in its depth prepass, where that cost lies; drawing the see-through trees in the transparent pass to read it
    cost as much as it saved.
  - **Hide all but nearest** (in the panel, off by default; `veil_keep`): keep only the one or two see-through trees
    nearest the hero see-through, and the rest go whole over 0.15 s, leaving only their shadows, no stump, until they no
    longer cover the hero. A hidden tree comes back as one of the nearest only once it's 1.5 m nearer the hero than
    one kept, so two about as near don't keep swapping. Hidden trees cost nothing to draw: in the slowest low-camera
    views, 16 to 17 ms a frame instead of 22 to 24 (keeping 2, about the same), and the stipple over most of the screen
    goes, but the trees in the way vanish rather than stay half there. Walking the trail with the camera low, keeping 1
    takes the slowest 5% of frames from 44-46 fps to 50-51 and the slowest 1% from 40-43 to 46, hiding 2.8 trees a
    frame on average.
  - In the panel: **see-through at** (40%), **solid again below** (20%), **cover counts** (Two trees, Leaves or Whole
    cards), **area round hero** (1.5 m), **see-through by** (50%; 0% for never), **show the area**, which draws it over
    the view with its points, red where the trees cover them, and how much of it they cover, with how much they must
    cover to go see-through, or, once they are (its outline red), how little before they come back
    (`scripts/sight_area.gd`), and **see-through trees** (Fewer cards).
  - **The cone** (also on its own, **Cone** in the panel): whatever of a tree is inside a cone from the edges of the
    screen to the hero fades away, wholly in the cone's middle and gradually towards its edges
    (`ref_imgs/tree_disappear/camera_view.png`; `cone_fade` in `shaders/common.gdshaderinc`).
  - On the screen the cone shrinks with depth: the whole screen at the camera, and round the hero, at 2.5 times its
    size, at the hero's depth; it stops just past the hero's far side. So trees near the camera fade wherever they are
    on the screen, and their branches don't sweep in from its edges; those in front of the hero fade only round the
    way to it, so a spruce whose outer branches cover the hero fades there, more the nearer the hero; and the trees
    beside and past the hero stay.
  - The cone takes no tree whole, so nothing pops, and nothing is left as a bare stick. The fade is a fine dither in
    blocks of two pixels, which reads as the trees' opacity changing and which the ambient occlusion, worked out at
    half resolution, leaves alone; the outer 30% of the cone fades gradually.
  - The panel has the earlier ways too, to compare: **Front**, whole trees in front of the hero (where they stand, in
    the lower middle of the screen, at least 1 m in front of it) and any in the way of the hero go, leaving their
    stumps (built from each tree's own trunk, `stumps.glb`) or their bare trunks; **X-ray**, a soft-edged window in
    the lower middle of the screen; **Area**, the lower middle up to 6 m past the hero; **Line**, only the trees in
    the way of the hero. With Front and X-ray, whatever of a tree comes near the camera fades too.
  - Whatever the camera is about to touch, within about 2.5 m of it, fades too.
  - The mockups also hide the trees near a high camera. The demo can, with the panel's "Fade trees near camera",
    though never within 6 m of the hero; it's off, as trees should only go once they block the view.
  - Whole trees fade in patches a few tenths of a metre across rather than in a dither of single pixels, which the
    ambient occlusion turned into black specks; the cone's dither, in blocks of two pixels, it leaves alone.

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
| Speed-ups | **All as before** and **All on** flip every speed-up (below, under Speed) between how it was before it and now, to compare the look and the frame rate |
| Trees | The old or the new trees (as T) |
| Path colours | The paths' colour theme (as P) |
| Path wear spread | How far the paths' wear spreads into the grass: 0 as in the mockups, up to 1 (the default), where the trampled grass, bare patches and stray stones reach further out and break up in patches, so it's less clear exactly where a path runs |
| Leaf cards | Square cards, or cards trimmed to an outline round their leaves (the default): the same look, fewer pixels to draw |
| Cards per clump | As tuned, or about half as many (a little bigger): sparser crowns |
| Tree shadows from | What casts a new tree's shadow: one of its versions (the full, mid or far one), its trunk and branches with a picture of its leaves as the sun sees them (**Pictures**, the default; under Speed), or nothing |
| from trees within | Only the trees within this far of the camera cast shadows: all, 60 m (the default), 40 m or 25 m |
| Lighter trees from | Where the new trees switch to their lighter versions |
| Far trees as pictures | From how far the new trees are drawn as pictures (under Speed): never, 120 m, 90 m (the default) or 60 m |
| Fade trees near camera | The mockups' fade of trees near a high camera, though never within 6 m of the hero. Off by default, as trees should only go once they block the view |
| Trees in the way | How trees get out of the way (above): **See-through** (the default), with how much of the area round the hero the trees must cover (**see-through at**, 40%) and how little before see-through trees turn solid again (**solid again below**, 20%, so they don't flicker), what covers it (**cover counts**: two trees or more hiding a point through the gaps between their leaves, the default, so a tree alone never goes see-through; one tree; or any part of a leaf card, as before), how far round the hero the area reaches (**area round hero**, 1.5 m), how see-through they go (**see-through by**, 50%; 0% for never), **show the area** on the screen, whether **see-through trees** are drawn with half their cards, each where it was (Fewer cards, the default, much faster deep in the forest) or all of them, and whether to **hide all but** the 1 or 2 see-through trees **nearest** the hero (off by default); the **Cone**, with sliders for its **soft share** (30%), how big it is **round the hero** (2.5 times the hero) and how long it stays **wide** (1, evenly), and whether it **fades in** a dither (the default) or patches; whole trees in **Front** of the hero; the **X-ray**'s window; the lower middle up to 6 m past the hero (**Area**, **past hero**); only those in the way of the hero (**Line**); or none. With Front, **leave** their stumps (the default), their trunks, or nothing. **A tree goes by** where it stands in the area (the default) or any part of it. Sliders: the area's **width** and how far **from the top** it starts; how far from the camera trees fade (**near the camera**, a share of the way to the hero); and for In front, how far in front of the hero they must stand (**by at least**). **Clear round the hero** also keeps the ground that far round the hero clear of trees in the way; 0 m, the default, is the hero alone |
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

The ground details come at five levels, each its own compiled shader, so a lower level doesn't pay for what it skips:

| Level | What it draws |
|---|---|
| High | Everything: three sizes of stones with exact, slightly wavy outlines, grit between them, fallen leaves, and bumps that catch the light |
| Baked | The same as High, but its stones, grit, leaves and the grass's grain are worked out once at startup into tiling textures, rather than for every pixel of every frame (the default; under Speed). It looks the same |
| Medium | The small and big stones, with simpler outlines, and the fallen leaves: no flat stones, grit or bumps. It looks almost the same |
| Low | The small stones and the fallen leaves; the bigger stones become an even colour |
| Off | The dirt and grass colours only |

Each level also stops drawing details further from the camera (High and Baked at 50 m, Medium 38 m, Low 28 m).

**Walk the trail** walks from the start to the meadow the same way every time and lists the result with the settings,
so runs compare fairly. With VSync off and no frame rate limit (the defaults), the frame rate goes as high as the
graphics card allows. The hero moves in the physics' 60 steps a second and is drawn between them (physics
interpolation, `project.godot`), so walking stays smooth at any frame rate. `--paneltest` presses every switch in turn
and prints what each costs, then the speed-ups all as before and all on, and checks the frame rate limit.

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

The new trees cost much more than the old ones, mostly from overlapping leaf cards, and so did the ground's details
on the paths. On this laptop's integrated graphics (Intel Arc 140V) at 1600 × 900, with VSync off, no frame rate limit
and nothing else running, the graphics card's time per frame, before the speed-ups below and now:

| View | Before | Now |
|---|---|---|
| The start | 19.3 ms (52 fps) | 10.4 ms (96 fps) |
| The start, camera low | 26.0 ms (38 fps) | 13.5 ms (74 fps) |
| Dense forest, camera low | 26.5 ms (38 fps) | 14.2 ms (70 fps) |
| The thicket | 19.6 ms (51 fps) | 11.0 ms (91 fps) |
| The meadow path | 12.3 ms (81 fps) | 5.2 ms (192 fps) |
| The meadow, camera low | 16.3 ms (61 fps) | 7.3 ms (137 fps) |
| The forest from straight above | 17.2 ms (58 fps) | 11.4 ms (88 fps) |

Walking the trail from the start to the meadow averages 131 fps, with the slowest 1% of frames at 74 (before: 65 and
42). The old trees take 4.8 ms at the start.

The speed-ups, each with its switch in the panel, so you can flip back and forth and judge what it costs the look
(**All as before** and **All on** flip them all), and what undoing each one alone costs:

- **Ground details: Baked** (before: High). The stones, grit, fallen leaves and the grass's grain, which High works
  out from noise for every pixel, are worked out once at startup into four tiling textures of 1024 × 1024
  (`scripts/ground_detail.gd`, `shaders/detail_bake.gdshader`, with the noise's cells wrapped so they tile), which
  the ground shader reads (`shaders/ground_baked.gdshader`). It looks the same. High costs 6.7 ms more on the meadow
  path, 5.0 on the meadow with the camera low, 4.1 at the start.
- **Tree shadows from pictures** (before: the mid versions' leaf cards). At startup, each new tree model's leaves are
  pictured as the sun sees them, from 16 sides round it, white where a leaf is, into one atlas
  (`scripts/tree_shadow_pictures.gd`). A tree's shadow is then cast by its trunk and branches as they are, and by one
  quad that faces the sun through the middle of its crown, cut out to the picture from the side nearest the sun's
  (`shaders/shadow_picture.gdshader`), instead of by hundreds of leaf cards. The shadows on the ground and on the hero
  are much the same; the crowns shade themselves a little more simply. Leaf-card shadows cost 1.8–3.7 ms more in the
  forest. If the sun moves, the pictures must be taken again.
- **Far trees as pictures from 90 m** (before: never). At startup, each new tree model is pictured from 8 sides a
  little from above (`scripts/tree_impostors.gd`), and from 90 m a tree is drawn as one quad turned to the camera,
  showing the two pictures nearest the camera's side, blended and lit like the crowns (`shaders/impostor.gdshader`).
  Drawing them as trees costs 2.5–3.1 ms more with the camera low; at the start, where little is that far, nothing.
  The pictures look a little fuller than the lightest versions they replace.
- **Shadows from trees within 60 m** (before: all). Only the trees within 60 m of the camera cast shadows; the shadows
  reach at most 70 m from it anyway. All of them cost up to 1.1 ms more with the camera low. 40 m saves a few tenths
  more, but low over the meadow it loses a big tree's shadow.
- **Trimmed leaf cards** (before: square). The same look, fewer pixels to draw: square cards cost up to 1.7 ms more.

Also:

- **Lighter versions:** each new tree has two, with fewer, bigger leaf cards, used from 45 m and 120 m. Using them
  nearer saves at most 1 ms, as their bigger cards cover about as many pixels.
- **Trimmed and fewer cards:** every version also comes with its cards cut to the outline round their leaves
  (`trees_trim.glb`), and the full trees with fewer cards per clump (`trees_few.glb`). As the models load, each full
  tree also gets its thinned version, for while it's see-through (above), in about 65 ms for all of them.
- **Hidden trees:** with See-through, the start runs as fast as with no tree hidden (11.6 ms), as no tree covers the
  hero there. Walking the trail with the camera low (10°), it's 76 fps on average, 45 in the slowest 5% of frames and
  42 in the slowest 1%; with the see-through trees on all their cards, 72, 38 and 35 (with the earlier fewer cards,
  which cost the same as the thinned trees: measured back to back on a warmer day, all cards against thinned took
  the slowest 5% from 33 fps to 38 and from 30 to 34, the slowest 1% from 30 to 34 and from 27 to 31). The slowest
  views there, deep in the forest looking through 6 to 10 see-through trees, take 21 to 22 ms a frame instead of 25 to
  28; the rest is the
  forest itself, where ambient occlusion and shadows cost 3 to 4 ms each, and the lighter trees from 30 m instead of
  45 m would save at most 1.5. Measuring the area costs 3 to 4.5 ms deep in the forest, 30 times a second (two trees
  deep over 1.5 m; the way before, 1 ms); the frame rate there didn't change, as the graphics card takes the time. The cone, which takes no tree whole, costs about 0.5 ms a frame more at the start, and 2 ms more than Front,
  where the trees that go aren't drawn at all, apart from their shadows and what's left of them. Working out which
  trees go takes 0.2–0.7 ms a frame in the forest; the trees' shapes for it are worked out as they load (about 60 ms for
  both sets).
- **The depth prepass** (Godot's own, on): without it, the forest takes twice as long.
- **Tried, and not worth it:** a draw distance for the bushes and berries (under 1 ms with the camera low), skipping
  the shadows of trees behind the camera (Godot already does), and moving where the near shadow cascade ends (Godot's
  10% is the fastest).

What costs the most, measured with the panel at the start (against the defaults' 10.4 ms then, when the trees in front
of the hero went whole there; with See-through, the defaults take 11.6 ms):

- **Shadows:** off saves 2.7 ms (126 fps); the trees' shadows alone 2.2. A 1024 shadow map saves 1.0 ms against
  2048, and 4096 costs 2.4 ms more.
- **Render scale:** 75% saves 2.2 ms (119 fps), 50% 4.2 (156 fps).
- **Leaf cards:** fewer cards per clump save 2.0 ms (116 fps).
- **Ambient occlusion:** off saves 1.9 ms (115 fps), with the camera low up to 3.7; very low saves 0.4; high costs
  1.8 ms more.
- **Fade trees near camera:** on, it costs 1.1 ms, from the trees half faded near the camera.
- **Ground details:** below Baked, Off saves 0.8 ms and Medium and Low 0.5.

## Rebuilding the assets

Everything in `assets/kit`, `assets/trees`, `assets/ground` and `data` is generated from code. Rebuild it after
changing the trees, the mockups' kit or the area. Run from `game/tools`, with Blender 5.2:

```sh
blender -b --factory-startup -P build_demo.py -- models   # the old kit and the portfolio trees (.glb), with baked occlusion
blender -b --factory-startup -P build_demo.py -- stumps   # every tree's stump and bare trunk (stumps.glb), in a few seconds
blender -b --factory-startup -P build_demo.py -- layout   # where every tree, rock and plant stands
blender -b --factory-startup -P build_demo.py -- ground   # heights, ground textures and the trees' shade (after layout)
blender -b --factory-startup -P build_demo.py -- masks    # only the paths' wear masks (masks.png), in a few seconds
blender -b --factory-startup -P build_demo.py            # all four, in that order
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
| `scripts/world.gd` | The area: terrain and collider, trees (with their lighter versions, and their stumps for when they're cut), rocks and plants, colliders, walls |
| `scripts/ground_detail.gd` | Bakes the ground's details into tiling textures at startup, for the Baked level |
| `scripts/tree_impostors.gd`, `scripts/tree_shadow_pictures.gd` | Picture the new trees at startup: from the side, for the far trees, and their leaves from the sun, for their shadows |
| `scripts/hero.gd`, `scripts/camera_rig.gd` | The hero and the camera |
| `scripts/perf_panel.gd`, `scripts/trail_walk.gd` | The performance panel, and the walk along the trail it uses |
| `scripts/path_themes.gd` | The paths' colour themes |
| `scripts/models.gd`, `scripts/mood.gd` | Loading the models with the game's materials, and the trees' thinned versions; the light |
| `scripts/game.gd` | Settings shared by the scenes, and the controls |
| `shaders/` | Ground (`ground.gdshaderinc`, compiled at five levels of detail: `ground`, `ground_baked`, `ground_medium`, `ground_low`, `ground_flat`; `detail_bake` bakes the details), leaves, the low-poly material (and `lowpoly_trunk` for the bare trunks trees leave, which neither the x-ray nor the fade near the camera touch), the trees' pictures (`impostor`, `shadow_picture`, and `impostor_bake`, which takes them), sky, Blender's noise |
| `scripts/dev/` | `selftest.gd` (`--selftest` tries every control and checks it), `walktest.gd` (`--walktest` walks the trail and prints the frame times; add `--treelod=1` or `2` to try the lighter trees), `paneltest.gd` (`--paneltest`), `veilbench.gd` (`godot --path game --script res://scripts/dev/veilbench.gd`: at random spots in the forest with the camera low, the slowest views, and what the see-through trees cost there with all their cards, half, or hidden; add `-- --poses=x,z,yaw,pitch,distance;...` for set views), `veiltune.gd` (`godot --headless --path game --script res://scripts/dev/veiltune.gd -- --out=rows.csv`: playtests for when trees go see-through, walking the hero under every tree standing alone, along the trail and to random forest spots, writing for each step how much of the area round the hero each way of measuring covers, and how much of the hero shows; `python3 tools/veiltune.py rows.csv` plays the settings over them), `sightaudit.gd` (`godot --path game --script res://scripts/dev/sightaudit.gd`: at random spots and camera angles, how much of the hero the trees still cover, and how early hidden trees go, from their pixels; add `-- --mode=veil` or another way of cutting trees) and `lineup.gd` (models in rows, for comparing with Blender) |
| `tools/` | The Blender build scripts, and `veiltune.py` (above) (Godot ignores this folder) |
| `assets/`, `data/` | Generated models, textures, heights and layout; Cinzel in `assets/fonts` (SIL Open Font License) |
