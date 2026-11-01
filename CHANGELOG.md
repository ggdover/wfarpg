# Changelog

The project's milestones, newest first: the bigger points where a stage of it is done, each tagged in git (`v1.0`,
and so on). The smaller steps between them are in the git history. A new milestone gets a section at the top: its
date and tag, what it brings since the one before, and what's left for later.

## 1.0: the forest demo (1 November 2026, tag `v1.0`)

The first milestone: a play demo of Act 1's Swedish pine forest in Godot 4.7, with its trees and plants made in
Blender, good enough to call a 1.0, though there's polish still to do. It took 59 commits, from 3 October to
1 November 2026.

### The look

- **The look & feel board** settled the art style: low-poly 3D, a smooth painted ground, faceted props, a rustic
  Norse HUD. Its mockups and their scripts are in `mockups/`, every step of the board in its design history, and
  Act 1's layout, from Tallmo through Storskogen to Ödeskogen, is kept as data.
- **Trees:** the tree portfolio, made in Blender by script, with an editor: Scots pine, silver birch, Norway spruce,
  aspen, rowan and alder. Low-poly trunks with painted bark, leaves in clumps of crossed cards, and the spruce's
  needles in sprays along its branches, its top a spire.
- **Plants:** a portfolio of bushes and grasses made the same way. Raspberry, alder buckthorn and hazel stand at the
  forests' edges and in their glades.
- **The ground:** smooth and painted, with moss, grass, gravel and fallen leaves. Paths are worn into the grass with
  no hard edges, in colour themes (Forest earth by default).
- **Grass** covers the green ground in four styles that blend into it (Clumps by default), and folds as the hero
  walks through it. The bog has its own golden sedge.
- **The autumn hollow:** deep piles of leaves part as the hero walks through, leaves are kicked up, and they stay
  where they were moved.
- **Wind:** a gust at least every few seconds, in different strengths, now and then a strong one. The trees and
  bushes sway, the grass waves, and loose leaves shiver.
- **Bushes** let the hero walk into them, a little slower there, and shake slightly as it pushes through.
- **Moods:** day, fog, morning sunbeams and autumn.

### Playing it

- **Twelve scenes**, switched with Tab or the Scenes button: Storskogen, Open forest, Thick forest, Open field,
  Autumn hollow, River and cliffs, Forest lake, Bog, Pine heath, Misty forest, Misty ravine and Sunbeams.
- **The hero** is a grey box for now. WASD walks it relative to the camera, and holding the left mouse button stands
  in for attacking: it faces the cursor and walks slower.
- **The camera** looks down from high up, isometric style. Holding the right mouse button orbits it, and the wheel
  zooms.
- **Trees never block the view:** a tree in the way of the hero goes, down to its stump, and treetops near a high
  camera are cut lower (Clear view). In thick forest, trees in the way turn half see-through instead.
- **The performance panel (F2)** shows a graph of the frame times. Under its advanced settings, every setting sits in
  a category, with a hint on what it does, among them the speed-ups, each with a switch to compare it against how it
  was before.

### Speed

- Leaf cards trimmed to their leaves, lighter spruces, far trees drawn as pictures taken at startup, tree shadows
  from those pictures and only within 60 m, and the ground's details baked into textures. The demo runs with VSync
  off and no frame limit, so its real frame rate shows.

### Tools

- Everything works the same on **Linux and Windows**. The tools are Python scripts: `game/tools/checks.py` runs the
  checks (the import, the selftest, every scene's walk), `game/tools/play.py` starts the demo, and
  `game/tools/export_windows.py` exports it as one file, `dist/wfarpg.exe`. Both of the first two open on the monitor
  the Claude app is on.
- The demo's models, textures and layouts are built in Blender by `game/tools/build_demo.py`.

### Left for later

- Polish, all over.
- The hero is a grey box, and there's no combat, enemies, quests or the mockups' HUD in the game yet.
- Act 1's zones are only begun: a part of Storskogen, and scenes to try out the forest's looks.
- `game/tools/reference_shots.py` has failed on every area since the bushes came into the layouts
  (`KeyError: 'AlderBuckthorn_A'`).
