# wfarpg: the play demo

A first playable piece of Act 1, in Godot: twelve scenes, each an area of Swedish forest in a mood of its own, about
125 × 100 m to walk (Storskogen 155 × 110 m, the open field 210 m across). Pick one on the start screen, or switch in
the game with the Scenes button or **Tab**.

| Scene | What it shows |
|---|---|
| Storskogen | The first demo, a small part of Storskogen: dense pine and spruce in the west, like Tätskogen, with a winding trail and a fork to the north; an open meadow with lone trees and a low rise in the east, like Stora ängen |
| Open forest | The forest as most of the game should be, for an ARPG: the trees stand about 14 m apart, so one or two are on the screen at a time from the usual camera, the thick forest only beyond the edges; moss, heather, a glade, rocks and logs between, low rises and a hollow |
| Thick forest | Dense spruce and pine all round, with one winding path cleared through it, like where Storskogen starts; its trees go see-through rather than to their stumps |
| Open field | A very big, rolling meadow: copses of birch and aspen, lone trees, boulders, the forest only far off |
| Autumn hollow | A grove of birch, aspen, rowan and alder in a hollow 2.8 m deep, 4–6 m between the trees, turning yellow, orange and red, hazel and buckthorn among them turning too, no paths, only leaf-filled ground: the leaves lie thick, in some 200 piles that stir as the hero walks through them and stay where they were moved; the forest round it still mostly green |
| River and cliffs | A little river, with a rapid, under a band of mossy cliffs 3.5–4 m high: wooden steps up them, a path up where they peter out, a path along the top, a footbridge over the river, and stepping stones from a gravel bank |
| Forest lake | A still, dark lake with reflections: reeds, water lilies in a bay, a jetty, an island with pines. The hero can wade in the shallows |
| Bog | An open wetland: tussocks of golden sedge (its own grass, folding as the hero walks through) between wet hollows and dark pools, stunted pines and birches, grey snags, a boardwalk across |
| Pine heath | Tall pines standing apart over moss, heather and bare granite knolls |
| Misty forest | The thick forest, with fog rolling in |
| Misty ravine | The river and cliffs, in grey, damp mist |
| Sunbeams | The pine heath early in the morning: a low sun shining through mist between the trunks |

The new areas follow the reference images in `ref_imgs2/`: the forest densities (thick forest, pine heath, open
field), fog, sun rays, leaves on the ground (the autumn hollow), the hike trail (the river and cliffs), the lake, and
the wetland (the bog).

- **Two versions of the trees:**
  - the old trees, the low-poly ones from the mockup screenshots;
  - the new trees, the tree portfolio built in Blender (`assets/trees`).
  - Every tree stands on the same spot in both.
  - Pick a version on the start screen, or press **T** in the game to swap them where you stand.
- **The grass** covers the green ground, outside the paths, and folds as the hero walks through it (below): four
  styles that blend into the ground (Clumps, the user's choice, by default), the first try and the mockups' tufts,
  which G steps through; and the bog has its own, golden sedge.
- **Everything else is shared:** the ground, rocks, heather, ferns, logs and props come from the mockups. Their shrubs
  and blueberry and lingonberry bushes, small faceted green balls (some with berries), are gone: the user found they
  didn't fit beside the grass's strands (14 October). The areas still pick them where they did, so everything else
  stands where it stood, but the layout leaves them out (`DROPPED` in `tools/build_demo.py`).
- **Bushes:** the plant portfolio's raspberry, alder buckthorn and hazel (`assets/plants`), which the user asked to
  see in the scenes (15 October): at the forests' edges and in their glades, where the trees stand neither thick nor
  far apart, and along the paths, off them, on dry ground, clear of trunks and rocks (`Layout.bushes` in
  `tools/build_demo.py`), from 7 in the thick forest to 145 by the river; across the open forest's glades, among the
  autumn hollow's trees, turning yellow and red there, and mostly buckthorn by the lake and in the bog. They're placed
  last, on random numbers of their own, so nothing else moved. Each is solid at its middle. Exported by the plants
  stage with their cards and the shade inside them baked, like the trees' (`assets/plants/bushes.glb`), and drawn
  with the trees' leaf shader, but none of the trees' fades (`tree_fades`): they're low enough not to be in the way.
  F2's **Bushes** turns them off; they cost 0.5–0.6 ms a frame where there are many (the open forest, the river).
- **The hero** is a grey box for now, with a dark band on its front.

## Running it

It needs Godot 4.7, the standard build without .NET, as `godot` on PATH. It runs the same on Linux and Windows, with
the same commands (the repository's `README.md` has the setup for each):

```sh
godot --path game                                  # from the repository root: plays the demo
godot -e --path game                               # opens the project in the editor (F5 plays)
godot --path game res://scenes/demo.tscn -- --trees=old   # straight into the demo, with the old trees
godot --path game res://scenes/demo.tscn -- --theme=Brown_earth   # with one of the path colours (_ for spaces)
godot --path game res://scenes/demo.tscn -- --grass=GrassClumps    # with one of the grasses (GrassField.STYLES)
godot --path game res://scenes/demo.tscn -- --scene=forest_lake   # straight into a scene (its id in scripts/scenes.gd)
```

The first time, Godot imports the models and textures, which takes a minute. When running it from the command line
without ever opening the editor, run `godot --headless --import --path game` once first.

To check it after a change, `python3 game/tools/checks.py` runs Godot's import, which must leave every file in the
repository as it was, then the selftest and each scene's scenetest (`scripts/dev/`, below), each in the demo's
window, a few minutes in all. It prints what failed, ends with how many checks passed, and exits with 1 if one
failed. Name some to run only those: `import`, `selftest` or scene ids, e.g. `python3 game/tools/checks.py selftest bog`.

### The Windows build

`tools/export_windows.py` (run it from anywhere, on Linux or Windows: `python3 game/tools/export_windows.py`) exports
the whole demo for Windows as one file, `dist/wfarpg.exe` at the repository's root, about 300 MB, with everything
packed into it (`export_presets.cfg`, the Windows preset). Copy it to a Windows computer and double-click it. It
installs nothing; its settings, shader cache and F12 screenshots go to `%APPDATA%\Godot\app_userdata\wfarpg`. It
needs a graphics card with Vulkan, which Windows drivers have had for years. Without Vulkan it falls back to Direct3D
12, which hasn't been tried. Windows may warn at the first run that the publisher is unknown (the file isn't signed):
More info, then Run anyway.

- **Export templates:** the first time, the script fetches Godot's export templates for the version it runs (1.3 GB),
  checks them against the release's SHA-512, and keeps only the Windows ones, where Godot looks for them:
  `~/.local/share/godot/export_templates/` on Linux, `%APPDATA%\Godot\export_templates\` on Windows.
- **Rebuild after changes:** the exe is a snapshot, so run the script again after changing the demo.
- **Shader baker:** off. It bakes only when the editor has a GPU, not in a headless export, and a cold shader cache
  costs only about 2 s at the first run.
- **Tested under Wine:** the exe ran here under Wine 10, on Vulkan. The start screen and the demo looked the same as
  the project run in Godot, at the same frame rate, and `--selftest` passed 59 of 59.
- **Built and tested on Windows:** on Windows 11 (an RTX 4070 SUPER, on Vulkan), `export_windows.py` fetched the
  templates and built the exe, and `wfarpg.exe -- --play --selftest` passed 62 of 62 (28 October).
- **No scene path:** the exported game always opens on the start screen, as Godot's export templates won't take a
  scene to start in. So `--play` goes straight into the demo, with the other options as above:

```bat
wfarpg.exe -- --play --scene=forest_lake --trees=old
```

## Controls

The controls follow the mechanics and camera notes on the look & feel board.

| Key | What it does |
|---|---|
| W, A, S, D | Walk. W walks away from the camera, whichever way it faces |
| Right mouse button + move | Orbit the camera round the hero. Sideways turns the view; up and down changes the angle, from straight down to low behind the hero |
| Mouse wheel | Zoom |
| Left mouse button (hold) | "Attack": the hero turns to face the cursor and walks at 55% speed. There are no attacks yet |
| Tab | The scenes, to switch to another (or click Scenes, top left) |
| T | Swap the old and new trees |
| P | Change the paths' colours (eight themes, below) |
| G | Change the grass: Wisps, Tufts, Clumps, Short, the first try, or as before (below) |
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
  - Those two are imported losslessly, every texel as it was baked (`mipmapped` in `tools/build_demo.py`). Compressed
    for the graphics card, as Godot imports a texture by default, each block of 4 × 4 texels (40 cm across) got two
    colours to mix between, which three unrelated noises packed in one texture can't share; the dirt, drawn where
    their sum crosses a threshold, then showed its edges in straight lines along the blocks, at right angles, which
    the user found looked machine-made (14 October). Lossless, the edges are ragged. It costs about 0.2 ms a frame
    on the meadow path (6.1 ms against 5.9, three pairs back to back, each the same way).
  - `shaders/ground.gdshaderinc` draws the trails and the small things on top with the same formulas, so they stay
    sharp up close: the trampled grass and dirt, gravel and pebbles, grit, and fallen leaves. It uses a port of
    Blender's noise (`shaders/blender_noise.gdshaderinc`), and comes in four levels of detail (below).
- **Light:** `scripts/mood.gd` copies the mockups' daylight: the sun, a plain ambient colour, the gradient sky with
  clouds, haze, and AgX tone mapping. The other moods change it for a scene: **fog** (a grey sky, the sun dimmed, thick
  haze and mist lying low), **morning** (a low, warm sun and volumetric fog, lit by the sun alone, so its shafts show
  between the trunks) and **autumn** (a warmer sun, more saturated). The water's scenes turn on screen-space
  reflections, so the water mirrors the trees on its far shore when the camera is low.
- **Autumn:** a tree in an area's layout can carry a tint, which turns its leaves yellow, orange or red, and how far
  (`autumn` in `shaders/leaves.gdshader` and `impostor.gdshader`); an area with an autumn ground (`litter.png`) has
  its fallen leaves cover the ground in two layers there.
- **Shading under the trees:** Godot's ambient light isn't blocked by geometry, unlike Eevee's, so the build bakes
  it instead.
  - Into each tree's vertices: how much of the sky each leaf and branch can see.
  - Into the ground: how much the trees shade each spot, separately for each tree set.
- **Trees and the camera, a clear view:** it's an ARPG, so trees must never get in the way of the view (the user).
  In most scenes (**Clear view**, the panel's first preset), any tree in the way of the hero goes, down to its stump
  (Trees in the way: **Line**; `_cut_whole` and `_in_way` in `scripts/world.gd`): as soon as any part of it is on a line
  from the camera to the hero, and back once it's off the lines to a wider hero, so it doesn't flicker. Their shadows
  stay.
  - **The crown cut**, with the camera high (from 45° above the horizon, coming in from 30°): no tree crown is ever just
    in front of the camera. Each tree ends below a ball round the camera, 80% as far across as the camera is from the
    hero (**Crown cut, camera high**: Near camera, and its reach): one whose trunk enters the ball ends where its trunk
    does, so the nearer the camera it stands, the lower it ends, and nothing of it is left floating. With the default
    camera, the trees in front of the hero end 2–5 m up, those beside it about 7 m, those a few metres beyond it 8–12
    m; further off they stand whole. The top dissolves over the last 1.5 m in the fine dither. A tree cut below its
    lowest leaves, or lower than 2 m, goes to its stump rather than stand there a bare pole (`crown_fade` in
    `shaders/common.gdshaderinc`, `_update_crown` in `scripts/world.gd`). As the camera comes down, the cut rises and
    the trees grow back. **All trees** ends every tree at a height instead, as the user wondered (Path of Exile 2 cuts
    most of its trees' crowns); Off as before.
  - The thick forest's scenes keep the see-through below (**Thick forest**), which the user found cinematic there,
    with the crown cut too; **One tree is enough** is the third preset. A scene's preset is in `scripts/scenes.gd`
    (view).
- **See-through, in the thick forest:** once the trees in front of the hero cover enough of the area round it, two
  trees deep, each of them goes evenly see-through, standing on its stump (**See-through** in the panel;
  `update_sight`, `_cut_veil` and `_measure_area` in `scripts/world.gd`). No tree goes whole. Their shadows stay.
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
  - At the top of the panel, **Trees in the way** sets them all at once: **Clear view** (above), **Thick forest** (these) or **One
    tree is enough** (one tree's leaves hiding 90% of the hero alone; solid again below 50%: from the same playtests, one
    tree hiding the hero goes see-through 98% of the time, and needlessly half as often as the way before), the one in
    use marked. Under its advanced settings, each on its own: **see-through at** (40%),
    **solid again below** (20%), **cover counts** (Two trees, Leaves or Whole cards), **area round hero** (1.5 m), **see-through by** (50%; 0% for never), **show the area**, which draws it over
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

## The grass

Grass wherever the ground is green, outside the paths, which folds as the hero walks through it, as the user asked
(10 October). The first try, thick, semi-long grass, didn't blend into the ground: its cards showed as crossed planes,
in colours of their own, over a smooth ground. So there are now four styles to choose from, each blending into the
ground, with the first try and the mockups' tufts to compare. **G** steps through them, and so does F2's **Grass**.
Of them, the user liked Clumps best (14 October), so it's the default:

| Grass | What it is |
|---|---|
| **Wisps** | The subtlest: sparse long strands, a patch every 0.9 m, over a ground of fine loose strands |
| **Tufts** | Tufts of strands fanning from their feet, a patch every 0.65 m, over a ground of flattened tufts |
| **Clumps** (the default) | The thickest: a meadow of strands, a patch every 0.5 m, over a ground of strands combed one way a clump at a time |
| **Short** | A short lawn, 22 cm, a patch every 0.45 m, over a ground of short strokes |
| **First try** | The long grass as it first was: thick and semi-long, a patch every 0.5 m, some with seed heads |
| **As before** | The mockups' faceted grass tufts, and the ground as it was (and in the bog, its faceted tussocks and sedge) |

All are the plant portfolio's grasses (`assets/plants`): patches of two or three cards of strands crossing, built from
the plant editor's settings by `tools/build_demo.py`'s plants stage into `assets/plants`.

- **Blending in:** each style comes with a ground texture, its strands lying flat as seen from above, in the same
  colours as its cards, which the ground shader lays over the green ground (`strokes` in `shaders/ground.gdshaderinc`).
  Each pixel of a strand takes the ground's own colour just under it; the card only makes it lighter toward its tips.
  Up from its foot, the card turns from the ground itself, texture and all, into its strands, so there's no line where
  they meet. The ground among the grass is a little darker, in its shade, so the lighter strands show against it
  (`shaders/grass.gdshader`).
- **Fewer strands, fewer patches, every card its own way:** a style's cards have fewer strands than the first try's,
  more of each card clear, and its patches stand further apart. Every card of every patch is turned and leaned at
  random, about the patch's middle (the plant editor's **Card turn randomness**; each card's number is in its corners'
  second UV map).
- **Where it grows** (`scripts/grass.gd`): every 16 m square of the area draws the same grid of patches, and the
  graphics card stands each on the ground, turns, moves and sizes it by where it stands, and keeps it only where the
  ground's baked colour is green (so not on heather, rock, the bog, water or the autumn hollow's fallen leaves), out of
  the paths' wear (as the ground shader wears them, so **Path wear spread** moves it too; it grows shorter and thinner
  toward them), off slopes steeper than about 35°, and where nothing lies: a mask made as the area loads covers the
  rocks and logs and the area's own models above the ground (water, boardwalks, the jetty, steps, bridges). So placing
  it takes no time as the area loads (making the mask a tenth of a second, a third in the bog with its boardwalk), and
  a patch that isn't there, or isn't on the screen, is dropped before it reads much.
- **Folding:** the hero's last 18 m, a point every 0.75 m it walks, go to the shader every frame. A patch within
  0.5 m of that trail lies over, up to 80°, away from it and the way the hero walked, and less out to 0.9 m; folded
  grass is a little lighter, as a trodden lane through a meadow is. It springs back up within 1.6 s of the hero
  passing, so a lane follows the hero as it walks and closes behind.
- **Far off** it sinks into the ground, from 70% of its distance (**drawn out to**, 45 m) to all of it.
- **Bigger strands:** the user asked for them a bit taller and wider, so it's easier to see the hero walking through
  them while they still blend in (14 October). F2's **strand size** makes every card that much taller and wider, its
  strands with it, and the strands lying flat in the style's ground texture as much bigger, so they still match: 140%
  by default, against the portfolio as tuned. The sizes in the table above are as tuned.
- **More or fewer strands:** F2's **strands** (25% to 300%, against the style's as tuned) stands the patches closer
  together or further apart: the grid every 16 m square draws is laid out anew, as many patches as it takes, the
  shader drawing the share of them that makes the number exact. Each patch is as it was, so the strands keep their
  colours, as the user asked; the ground among them shows less, so the whole looks a shade lighter, 2% at 300%.
- F2 also has **how tall** (on top of the size), **drawn out to**, **ground texture** (how strongly the style's ground
  texture shows, 100%) and **ground in its shade** (85%). All of them set the bog's grass too (below).
- **The bog's grass:** the user asked for a yellow grass that fits the bog, blending in and folding as the grass
  does (14 October). It's the plant portfolio's Grass: bog (`GrassBog`): golden sedge, fine strands fanning from a
  tussock's foot and arching over, a few pale and dry, a few still green, on a ground of the same strands lying in
  stars, all painted round a golden colour. A second field of grass (`bog_grass` in `scripts/world.gd`) grows it the
  same way as the green ground's, with the same folding, but where the area's `bog_grass.png` says rather than where
  the ground is green: wherever the ground shows the bog's golden sedge, not under its pools (baked from the ground's
  own layers by `tools/build_demo.py`, `bake_bog_grass`, with the masks; only an area with a sedge layer has it). Its
  chunks are only those the bog reaches. Its ground texture lies there in the ground shader as the green ground's
  does (`bog_strokes_*` in `shaders/ground.gdshaderinc`). It grows in tussocks, thick and tall in clumps half a metre
  to a metre across and thin and low between them, where the ground is darker, a wet hollow (`tussock_at` in
  `shaders/common.gdshaderinc`, from the masks' noises). In its place the bog's faceted tussocks and sedge, the
  mockups', are hidden, as the mockups' grass tufts are by the grass; As before shows them, and no bog grass.
- **Cost**, against As before, measured back to back in the open forest while the machine was busy with other
  programs (so all about 1.5 times the usual): Wisps 0.5 ms, Tufts 1.0, Clumps 1.8, Short 1.9, the first try 2.1. Most
  of it is the cards' pixels, drawn once in the depth pass and again lit, layer behind layer: the cut-out keeps the
  graphics card from skipping hidden layers early. The corners cost little, and the trail nothing measurable. Strands
  at 140% the size cost 0.3 ms more than at 100% in the open forest, 0.5 on the meadow; twice as many strands 0.8 ms
  more in the open forest, three times 1.4 (`scripts/dev/abbench.gd`, on 14 October, with the machine quiet).
  Clumps, now the default, costs 0.35 ms more than Tufts at the start, 0.5 in the open forest; at the bog's start,
  its grass on the green ground and the bog's together cost 1.3 ms (9.4 ms against 8.1 as before).

## The fallen leaves

In the autumn hollow, the user asked for no paths, only leaf-filled ground and trees, and for the leaves to lie in a
thick layer, thin in places but now and then deep in piles, which stir as the hero walks through them, the way leaves
shift round your feet in a pile, a few hopping up a centimetre or two and falling back (14 October). So the hollow has
no paths, nor the mockups' faceted bracken and leaf piles in its grove (`tools/areas/autumn_hollow.py`), and its
ground has piles of leaves of their own (`scripts/leaf_litter.gd`, `shaders/leaf_litter.gdshader`):

- **The thin layer** is the ground shader's fallen leaves, painted, two layers of them where the litter is.
- **The piles** lie over it where the litter is, in piles a metre or two across (the masks' patches noise), more of
  them where the leaves' drift noise runs high, their edges broken up: about 200 piles over 40% of the grove (the user
  asked for a lot more of them, 15 October; there were about 80, over a third), and now and then a thin one up round
  the hollow. Their leaves are small faceted kites, 10–15 cm, folded along the midrib so their two halves catch the
  light differently, in the ground's leaf colours, a little darker the deeper in the pile; up to 12 cm deep in a
  pile's middle, fewer and flatter at its edges, and the ground under a pile darker, in its shade.
- **How they're laid:** at every point of a 0.4 m grid that's in a pile, a patch of 48 leaves; each patch carries the
  pile's depth there and the ground's height and slope, worked out as the area loads (0.2 s), so its leaves read no
  textures but the trees' shade.
- **Stirring:** the first try, a few leaves hopping 1–2 cm, was too slight to notice, the user found (15 October);
  the stronger one after it was right, but its leaves slid back to where they'd lain, which they shouldn't: they
  should move only when someone moves into them (the user, the same day). So where they've been moved is kept, in a
  disturbance map over the piles (a 2D render target, 10 cm a texel, never cleared), which a brush paints round the
  hero every frame (`shaders/leaf_stir.gdshader`; `LeafLitter.stir_at`, which could take anyone else walking
  through them too), and the leaves read:
  - **A lane:** as the hero comes alongside them, the leaves are swept sideways out of its way, none left within
    0.3 m of it, crowding toward its edges into low banks, and the pile pressed down; those right in its way go to
    one side or the other. It shows from the game's camera, and stays: the map only ever pushes leaves further, or
    the other way where the hero walks through again, never back.
  - **Kicked up:** about half of those near the step, more of those on top, are kicked up, most about 8 cm and a
    few higher, and out 6–20 cm; they flutter, turn over once or twice, catch the light as they go, and land a little
    way off, where they stay.
  - **Shaken** back and forth, dying away. The flight and the shaking come from the hero's trail
    (`scripts/hero_trail.gd`, which the grass folds round too), within 0.75 m of it, and die away within 1.5 s.
  - The deeper the pile, the more; at a thin edge, hardly at all.
- **F2:** **Fallen leaves**, Piles or As before (none); **in piles**, how much of the litter lies in piles (100%, about
  40% of the grove's, in about 200 piles); **stirring**, how much they stir, all of it (100%); **hop**, how high a kicked leaf flies
  (8 cm).
- **Cost:** 1.4 ms a frame at the hollow's start (measured on 15 October, the machine quiet), with its 200 piles; with
  the 80 before, 0.4–0.6. The disturbance map costs nothing measurable.

## The performance panel (F2)

At the top, three presets for the trees in the way: **Clear view** (the default in most scenes: any tree in the way goes to
its stump, and the crown cut), **Thick forest** (see-through, the thick forest's scenes' default) and **One tree is
enough** (under Trees in the way, above), all with the crown cut and the spruces' leaves Lighter (below). Each scene
starts with its own (`scripts/scenes.gd`, view). The one in use is marked, from the start, until any setting under the advanced
settings changes, from the panel or by T, P or F4: the settings are then no longer the preset's. Then a frame-time
graph of the last 3 seconds (one bar per frame: green is faster than 60 fps, amber than 30, red slower), with the frame
rate now, on average, and in the slowest 5% and 1% of frames, and below it how long the graphics card takes per frame,
the triangles drawn and the draw calls. Every other setting is under **Show advanced settings**, hidden at first, and
takes effect at once:

| Switch | What it does |
|---|---|
| Speed-ups | **All as before** and **All on** flip every speed-up (below, under Speed) between how it was before it and now, to compare the look and the frame rate |
| Trees | The old or the new trees (as T) |
| Path colours | The paths' colour theme (as P) |
| Path wear spread | How far the paths' wear spreads into the grass: 0 as in the mockups, up to 1 (the default), where the trampled grass, bare patches and stray stones reach further out and break up in patches, so it's less clear exactly where a path runs |
| Leaf cards | Square cards, or cards trimmed to an outline round their leaves (the default): the same look, fewer pixels to draw |
| Cards per clump | As tuned, or about half as many (a little bigger): sparser crowns |
| Spruce leaves | **As tuned**, **Light** or **Lighter** (the default, chosen as the spruces still look really good so; also with the presets, and among the speed-ups): the spruces with two copies of each spray instead of four, near and in their first lighter version, and their shadows cast by their trunks alone, with the picture of their leaves; Lighter also sets the sprays half as far again apart along the branches. The spruce costs more to draw than every other tree together (below, under Speed) |
| Tree shadows from | What casts a new tree's shadow: one of its versions (the full, mid or far one), its trunk and branches with a picture of its leaves as the sun sees them (**Pictures**, the default; under Speed), or nothing |
| from trees within | Only the trees within this far of the camera cast shadows: all, 60 m (the default), 40 m or 25 m |
| Lighter trees from | Where the new trees switch to their lighter versions |
| Far trees as pictures | From how far the new trees are drawn as pictures (under Speed): never, 120 m, 90 m (the default) or 60 m |
| Fade trees near camera | The mockups' fade of trees near a high camera, though never within 6 m of the hero. Off by default, as trees should only go once they block the view |
| Bark textures | **On** (the default), or **Off**: the trunks plain, each in its bark's average colour, to see what the bark costs (nothing measurable, below) |
| Grass (G) | **Wisps**, **Tufts**, **Clumps** (the default) or **Short**, the plant portfolio's grass styles over the green ground, each on its ground texture, folding as the hero walks through them; the **First try**; or **As before**: the mockups' grass tufts (above), and in the bog its faceted tussocks and sedge instead of its grass. The sliders below set the bog's grass too. **strands**: how many, against the style's as tuned, its patches closer together or further apart (25% to 300%; 100%); **strand size**: the cards and the strands in the ground texture alike (140%); **how tall** (100%); **drawn out to**: where it has sunk into the ground (45 m); **ground texture**: how strongly its ground texture shows (100%); **ground in its shade**: how light the ground among the grass stays (85%) |
| Bushes | **On** (the default) or **Off**: the plant portfolio's bushes (above) |
| Fallen leaves | In the autumn hollow: **Piles** (the default), its leaves lying deep here and there, a lane opening through a pile as the hero walks through and leaves kicked up, or **As before** (none). **in piles**: how much of the litter lies in piles (100%); **stirring**: how much they stir (100%); **hop**: how high a kicked leaf flies (8 cm). Above, The fallen leaves |
| Crown cut, camera high | **Near camera** (the default): the trees near a high camera end lower the nearer they stand, out to a ball round the camera **reach** times as far across as the camera is from the hero (80%); **All trees**: every tree ends at a height (**trees end at**, 8 m), as the user wondered; or **Off**. Above |
| Trees in the way | How trees get out of the way (above): **Line** in Clear view, the default in most scenes; **See-through** in Thick forest, with the presets at the panel's top to set what follows at once (**Thick forest**, the defaults, or **One tree is enough**: Leaves, the hero alone, 90% and 50%; both see-through by 50%, none hidden), how much of the area round the hero the trees must cover (**see-through at**, 40%) and how little before see-through trees turn solid again (**solid again below**, 20%, so they don't flicker), what covers it (**cover counts**: two trees or more hiding a point through the gaps between their leaves, the default, so a tree alone never goes see-through; one tree; or any part of a leaf card, as before), how far round the hero the area reaches (**area round hero**, 1.5 m), how see-through they go (**see-through by**, 50%; 0% for never), **show the area** on the screen, whether **see-through trees** are drawn with half their cards, each where it was (Fewer cards, the default, much faster deep in the forest) or all of them, and whether to **hide all but** the 1 or 2 see-through trees **nearest** the hero (off by default); the **Cone**, with sliders for its **soft share** (30%), how big it is **round the hero** (2.5 times the hero) and how long it stays **wide** (1, evenly), and whether it **fades in** a dither (the default) or patches; whole trees in **Front** of the hero; the **X-ray**'s window; the lower middle up to 6 m past the hero (**Area**, **past hero**); only those in the way of the hero (**Line**); or none. With Front, **leave** their stumps (the default), their trunks, or nothing. **A tree goes by** where it stands in the area (the default) or any part of it. Sliders: the area's **width** and how far **from the top** it starts; how far from the camera trees fade (**near the camera**, a share of the way to the hero); and for In front, how far in front of the hero they must stand (**by at least**). **Clear round the hero** also keeps the ground that far round the hero clear of trees in the way; 0 m, the default, is the hero alone |
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
and prints what each costs, then the speed-ups all as before and all on, and checks the frame rate limit. For a
screenshot of the panel, `--panel` opens it and `--panel=advanced` with its advanced settings shown; `--set:preset=one`
presses a preset.

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

- **Lighter versions:** each new tree has two, with fewer, bigger leaf cards, used from 45 m and 120 m. At the start,
  using them nearer saves at most 1 ms, as their bigger cards cover about as many pixels; in the forest with the
  camera low, from 20 m it saves 2.7 ms and from 10 m 5.2, as the spruce's first lighter version has no branches and
  its sprays further apart.
- **Trimmed and fewer cards:** every version also comes with its cards cut to the outline round their leaves
  (`trees_trim.glb`), the full trees with fewer cards per clump (`trees_few.glb`), and the spruce's full and first
  lighter versions with lighter leaves (`trees_light.glb`). As the models load, each full tree also gets its thinned
  version, for while it's see-through (above), in about 65 ms for all of them.
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
- **What the trees cost:** the spruces cost more to draw than every other tree together. Hidden (with `--hide=NorwaySpruce,YoungSpruce`,
  one of the options for measuring listed in `scripts/demo.gd`), the forest with the camera low takes 9.7 ms a frame instead of 21, and from above 7.2 instead of 14.6; hiding the
  pines or the other trees changes nothing, as the spruces behind them fill in. Most of it is the area of their leaf
  cards, layer behind layer, which the depth prepass tests pixel by pixel (half the frame with the camera low): even
  trimmed, two thirds of a spray card is clear. So:
  - **A card's clear pixels go first** (always; it looks the same): the leaf shader lets them go before it works out
    the fades (`shaders/leaves.gdshader`), which saves 1.4 ms in the forest with the camera low and 0.3 to 0.6 from
    above.
  - **Spruce leaves** (the panel; Lighter by default since 7 October, the user's choice, and among the speed-ups, so
    All as before puts them back as tuned): Light and Lighter, against As tuned, measured back to back:

    | View | As tuned | Light | Lighter |
    |---|---|---|---|
    | The forest, camera low | 19.5 ms (49 fps) | 14.7 ms (65 fps) | 13.4 ms (72 fps) |
    | The forest, camera low, further west | 16.3 ms (60 fps) | 13.2 ms (74 fps) | 11.7 ms (83 fps) |
    | The forest from the default camera | 14.5 ms (65 fps) | 10.8 ms (88 fps) | 9.8 ms (98 fps) |
    | The same, zoomed out | 17.8 ms (54 fps) | 14.1 ms (67 fps) | 13.1 ms (73 fps) |
    | Walking the trail: slowest 5% and 1% of frames | 47–49, 39 fps | 58–59, 49–51 fps | 62, 53–54 fps |
    | The same with the camera low (12°) | 31, 28 fps | 41, 38 fps | 45, 41 fps |

    In the game's views the crowns look much the same; close up, Lighter shows more of a spruce's branches. Fewer
    copies of each spray save more than fewer sprays, and the branches cost nothing (they were tried without).
- **Tried, and not worth it:** a draw distance for the bushes and berries (under 1 ms with the camera low), skipping
  the shadows of trees behind the camera (Godot already does), and moving where the near shadow cascade ends (Godot's
  10% is the fastest).

What costs the most, measured with the panel at the start (against the defaults' 10.4 ms then, when the trees in front
of the hero went whole there; with See-through, the defaults take 11.6 ms):

- **Shadows:** off saves 2.7 ms (126 fps); the trees' shadows alone 2.2. A 1024 shadow map saves 1.0 ms against
  2048, and 4096 costs 2.4 ms more.
- **Render scale:** 75% saves 2.2 ms (119 fps), 50% 4.2 (156 fps).
- **Leaf cards:** fewer cards per clump save 2.0 ms (116 fps). Spruce leaves Light saves 2.4 ms and Lighter 3.0
  (measured on 7 October, against the defaults' 12.8 ms then); with Lighter the default, the start takes 9.8 ms.
- **Ambient occlusion:** off saves 1.9 ms (115 fps), with the camera low up to 3.7; very low saves 0.4; high costs
  1.8 ms more.
- **Fade trees near camera:** on, it costs 1.1 ms, from the trees half faded near the camera.
- **Ground details:** below Baked, Off saves 0.8 ms and Medium and Low 0.5.
- **Grass:** measured on 10 October with `scripts/dev/abbench.gd` while the machine was busy with other programs (so
  the times are about 1.5 times the usual). The styles, against the mockups' tufts as before, in the open forest
  (9.5 ms): Wisps 0.5 ms more, Tufts 1.0, Clumps 1.8, Short 1.9, the first try 2.1. The first try at the start, 1.2 ms
  (17.1 ms against 18.2), and in the open field, all grass, 2.4 (7.7 against 10.1); half as thick saves about 0.6 ms
  there; drawing it out to 25 m instead of 45 hardly anything, as the near grass covers the most of the screen.
- **Bark textures:** nothing measurable. On 10 October, flipped on and off every second in one run
  (`scripts/dev/abbench.gd`), on and off took the same to within half a millisecond either way, in six views: the
  thick forest with the camera low among the trunks (33.6 ms against 33.4), the start, the start with the camera low,
  the bog, the open forest and the autumn hollow. The machine was busy with other programs then, so the times were two
  or three times the usual; at quieter moments, the build before the bark and the one after took the same too (14.2
  ms against 14.6 at the start, 6.3 against 6.5 in the open forest). Other programs using the graphics card (a game,
  other Godot projects) slow the demo that much or more; see what runs before measuring.

## Rebuilding the assets

Everything in `assets/kit`, `assets/trees`, `assets/plants`, `assets/areas` and `data` is generated from code. Rebuild
it after changing the trees, the grasses (the plant editor's settings), the mockups' kit or an area. Run from `game/tools`, with Blender 5.2:

```sh
blender -b --factory-startup -P build_demo.py -- models   # the old kit and the portfolio trees (.glb), with baked occlusion
blender -b --factory-startup -P build_demo.py -- kit      # only the kit (rocks, plants, the areas' own pieces), in seconds
blender -b --factory-startup -P build_demo.py -- stumps   # every tree's stump and bare trunk (stumps.glb), in a few seconds
blender -b --factory-startup -P build_demo.py -- plants   # the grasses and their grounds, from assets/plants, in seconds
blender -b --factory-startup -P build_demo.py -- layout   # where every tree, rock and plant stands; water, steps, bridges
blender -b --factory-startup -P build_demo.py -- ground   # heights, ground textures and the trees' shade (after layout)
blender -b --factory-startup -P build_demo.py -- masks    # only the paths' wear masks (masks.png, and the bog's bog_grass.png), in a few seconds
blender -b --factory-startup -P build_demo.py            # models, stumps, plants, layout and ground, in that order
blender -b --factory-startup -P build_demo.py -- layout ground --area=bog,forest_lake   # only these areas
```

Layout and ground run for every area in `tools/areas` (its `AREAS`) unless `--area` names some; ground takes a few
minutes an area. Each area is a module there: its outline, paths, heights, how thick the forest grows and of what
trees, its ground's layers (moss, heather, rock, gravel, sedge, the bog's mud, autumn's fallen leaves, the bed under
water), and what it scatters (`populate`); `storskogen.py` is the first demo's. An area with water, steps, a bridge, a
jetty or a boardwalk builds them in `build_extras`, into `assets/areas/<area>/extras.glb`: the models named
`-colonly` there are colliders the importer makes, to walk on or bump into. Its layout goes to
`data/areas/<area>.json`, its ground to `assets/areas/<area>`. A scene (`scripts/scenes.gd`) shows an area in a
mood (`scripts/mood.gd`); several scenes can share one.

To compare the game with the mockups, render the same view both ways (`--area=name` for another area):

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
| `scripts/scenes.gd`, `scripts/scene_picker.gd` | The scenes (an area in a mood each), and the list to pick one from, on the start screen and in the game |
| `scripts/world.gd` | The area: terrain and collider, trees (with their lighter versions, and their stumps for when they're cut), rocks and plants, its own models (water, steps, bridges), colliders, walls |
| `scripts/ground_detail.gd` | Bakes the ground's details into tiling textures at startup, for the Baked level |
| `scripts/grass.gd`, `shaders/grass.gdshader` | The grass over the green ground, its styles, and its folding round the hero's trail; and the bog's grass, a second field of it |
| `scripts/leaf_litter.gd`, `shaders/leaf_litter.gdshader`, `shaders/leaf_stir.gdshader` | The autumn hollow's piles of fallen leaves, their stirring along the hero's trail, and the disturbance map that keeps where they've been moved |
| `scripts/hero_trail.gd` | The hero's trail, which the grass folds round and the leaves stir along |
| `scripts/tree_impostors.gd`, `scripts/tree_shadow_pictures.gd` | Picture the new trees at startup: from the side, for the far trees, and their leaves from the sun, for their shadows |
| `scripts/hero.gd`, `scripts/camera_rig.gd` | The hero and the camera |
| `scripts/perf_panel.gd`, `scripts/trail_walk.gd` | The performance panel, and the walk along the trail it uses |
| `scripts/path_themes.gd` | The paths' colour themes |
| `scripts/models.gd`, `scripts/mood.gd` | Loading the models with the game's materials, and the trees' thinned versions; the light |
| `scripts/game.gd` | Settings shared by the scenes, and the controls |
| `shaders/` | Water (`water`: its colour from its depth, ripples moving with its flow, white water where it runs fast), the portfolio trees' bark (`bark_fade`, `bark` for stumps, `bark_trunk` for bare trunks: the species' bark texture on each facet of the trunk, the foot's blended in below, `BARK` in `lowpoly.gdshaderinc`; textures from `assets/trees/make_bark.py`), ground (`ground.gdshaderinc`, compiled at five levels of detail: `ground`, `ground_baked`, `ground_medium`, `ground_low`, `ground_flat`; `detail_bake` bakes the details), leaves, the low-poly material (and `lowpoly_trunk` for the bare trunks trees leave, which neither the x-ray nor the fade near the camera touch), the trees' pictures (`impostor`, `shadow_picture`, and `impostor_bake`, which takes them), sky, Blender's noise |
| `scripts/dev/` | `selftest.gd` (`--selftest` tries every control and checks it, and that the grass follows the hero's trail, keeps off the rocks and logs, changes with its F2 switch and G, and that F2's strands and strand size do what they say), `scenetest.gd` (`--scene=river_cliffs --scenetest`: walks the hero up the river's steps, over its bridge, out on the lake's jetty and into its shallows, along the bog's boardwalk and down into the autumn hollow, between its trees, and checks it gets there on what it walks on, in the bog that its grass grows there in place of the faceted tussocks and follows the hero, and in the hollow that its leaves lie in piles and stir along the hero's trail), `walktest.gd` (`--walktest` walks the trail and prints the frame times; add `--treelod=1` or `2` to try the lighter trees, `--pitch=12` for the camera low), `paneltest.gd` (`--paneltest`), `veilbench.gd` (`godot --path game --script res://scripts/dev/veilbench.gd`: at random spots in the forest with the camera low, the slowest views, and what the see-through trees cost there with all their cards, half, or hidden; add `-- --poses=x,z,yaw,pitch,distance;...` for set views), `abbench.gd` (`godot --path game --script res://scripts/dev/abbench.gd -- --ab=bark=true,false`: one of the panel's settings at two values or more, a slider's too (`--ab=grass_density=1.0,0.5`), flipped every second in one run, so whatever else the machine is doing weighs on each alike; add `--scene=`, `--pose=` and `--set:` as for the demo, `--spells=24` for longer), `veiltune.gd` (`godot --headless --path game --script res://scripts/dev/veiltune.gd -- --out=rows.csv`: playtests for when trees go see-through, walking the hero under every tree standing alone, along the trail and to random forest spots, writing for each step how much of the area round the hero each way of measuring covers, and how much of the hero shows; `python3 tools/veiltune.py rows.csv` plays the settings over them), `sightaudit.gd` (`godot --path game --script res://scripts/dev/sightaudit.gd`: at random spots and camera angles, how much of the hero the trees still cover, and how early hidden trees go, from their pixels; add `-- --mode=veil` or another way of cutting trees) and `lineup.gd` (models in rows, for comparing with Blender; `-- --models=Rowan_A,Alder_A --trunks` for trunks close up) |
| `tools/` | The Blender build scripts, the areas (`tools/areas`), `veiltune.py` (above), `checks.py` (Running it, above) and `export_windows.py` (The Windows build, above) (Godot ignores this folder) |
| `export_presets.cfg` | The Windows export: one .exe with the game packed in |
| `assets/`, `data/` | Generated models, textures, heights and layout; Cinzel in `assets/fonts` (SIL Open Font License) |
