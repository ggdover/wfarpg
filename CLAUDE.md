# wfarpg

An action RPG, built from scratch in this folder.

## Ground rule: this project is self-contained

Do not take inspiration from, or reuse anything from, any other project under `~/repos`.
This applies to every session and every agent (including subagents) working in this folder.

- Do not read, list, search, or open files in any other directory under `~/repos`.
  Keep searches (`grep`, `find`, `ls`, glob patterns) scoped to this folder. Never run them on `~/repos` or `..`.
- Do not copy, adapt, or reference code, assets, configs, data, docs, or design ideas from those projects.
- Do not use knowledge of those projects from past sessions or memory when designing or writing code here.
- If a task seems to call for something from another local project, stop and ask the user first.
- When spawning a subagent, include this rule in its prompt.

General knowledge, public documentation, and third-party libraries and engines are fine to use.

## Project basics

- Engine: Godot 4.7 (`~/.local/bin/godot`). 3D models: made in Blender 5.2. Art style: low-poly 3D.
- Ground is a smooth, flat surface with painted textures (moss, grass patches, gravel on dirt paths, scattered small
  fallen leaves). Grass runs right up to the trees: no brown patches under them.
  Props such as trees, bushes and rocks are faceted low-poly shapes.
- Paths are worn into the grass by feet, so they never end in a hard line: the grass thins out and turns trampled toward
  them, and the wear spreads out in patches, so it isn't clear exactly where a path runs. The mockups' dirt is a light
  tan (between wheat and desert sand), with gravel and pebbles in the same tones, so they read as texture rather than
  contrasting spots. The user found that too much like sand. Of the play demo's path colour themes (P;
  `game/scripts/path_themes.gd`) they liked forest soil and brown earth best, and asked for a mix of the two: the
  demo's default, "Forest earth", not yet confirmed. Avoid hard edges between ground textures in general.
- Trees: Scots pine, silver birch, Norway spruce, aspen, rowan and alder (`ref_imgs/Trees of the Swedish Forest.png`;
  the user dropped the juniper). Low-poly trunks and branches; leaf clumps are crossed planes (copies of a leaf card
  with alpha, crossing at the clump's centre). The spruce instead has pinnate sprays: spray cards along each branch
  on alternate sides, their twigs' bases on the branch. The user isn't happy with the mockups' current trees and
  wants to swap them for these.
- Open trodden ground, like Tallmo's square, is worn the same way as the paths: an uneven, asymmetric outline (no clean
  ovals or other geometric shapes) and the same dirt, gravel and edges.
- Camera: a high, isometric-style view by default. Holding the right mouse button orbits it around the hero (WoW style),
  sideways and up/down, from straight down to low behind the hero. WASD is assumed to move relative to the camera
  (not yet confirmed by the user). Trees in the way, the user's design, shadows kept: a tree goes to its stump only
  once its trunk is in front of the hero; its leaves and branches stay, so the hero can hide in them, until the hero
  is behind the leaves of three trees or more, when the cone fades in and shows it through them; and spruces, whose
  needles are thick, go evenly half see-through while they cover most of the hero (the user's exception). The cone
  (`ref_imgs/tree_disappear/camera_view.png`) fades whatever of a tree is inside it, wholly in its middle and
  gradually, as a changing opacity, towards its edges: the whole screen at the camera, round the hero at its depth,
  nothing past it. No bare sticks, no hard x-ray edges. The user's earlier ideas and complaints are in
  `ref_imgs/tree_disappear/`; the earlier ways of cutting trees are in F2 to compare.
- HUD: rustic Norse ARPG style (hammered iron, brass, runes, knotwork) with a red life orb, a blue mana orb, painted
  ability icons and fantasy lettering (Cinzel in the mockups). Keep it sharp and detailed, not smooth or cartoonish:
  hard edges and cut corners instead of rounded ones, fine texture instead of soft gradients, slim orb rims.
- Act 1 is set in a Swedish pine forest, with a daylight mood and a fog mood. Reference images are in `ref_imgs/`.
- Act 1 layout follows `ref_imgs/act1_layout.png` (about 1.2 m per sketch unit): the town Tallmo opens onto the hub zone
  Storskogen (the user's name for "the fairmeadow"), which branches to Härddalen (Hearthvale), Gamla gården (the Old
  Courtyard) and Dimskogen (the Misty Woods); Dimskogen leads to Dimmyren (the Misty Swamp), then Ödeskogen (the Forsaken
  Forest). Names other than Storskogen are suggestions the user has not confirmed. Target: 10–15 quests, 1–2 hours.
  Storskogen mixes open plains, dense forest, raised ground and hollows; every slope must be walkable (no ropes or ladders).

## Look & feel board

The game's look and feel is being worked out on a shared whiteboard artifact:
https://claude.ai/artifact/Q7Crs9hY9EhaN47YRE2YrP

- Read it before planning or making design decisions. The user's choices there take precedence over your own ideas.
- Content lives in the artifact's database, collection `items` (read it with the ArtifactData tool). Each document has a
  `type` (`note`, `frame`, `image`, `video`, `link`, `swatch`), a position (`x`, `y`, `w`, `h`, `z`), and type-specific
  fields: `text`, `title`, `caption`, `url`, `hex`, `name`, `color`, `assetId` (uploaded file; fetch it with the Artifact
  tool's `read` and `path` set to the id).
- `stance` is the user's verdict on an item: `want`, `maybe` or `avoid`. Treat `avoid` items as things the game must not look or feel like.
- Items you add must set `author: "claude"`. Items without it were added by the user.
- `mockups/board/items.json` is a snapshot of the board's database and `mockups/board/assets.json` maps each image id to
  its file under `mockups/renders/`. The live board is the source of truth; refresh the snapshot after changing the board.
- The design history logs every step of the board, with notes word for word as they read at each step:
  `mockups/HISTORY.html`, built from `mockups/board/history.json` and published at
  https://claude.ai/artifact/L74mBkoQbstMGxKg7S1cND. After a step that changes the board, record it and republish the
  page to that URL, as described in `mockups/README.md`. Keep in-between renders worth showing in `mockups/renders/wip/`.

## Repository layout

- `ref_imgs/`: the user's reference images, the Act 1 layout sketch and the tree reference sheet.
- `assets/`: game assets. `assets/trees/` is the tree portfolio: low-poly Swedish forest trees built in Blender by
  Python scripts, saved in `tree_portfolio.blend`, with a tree editor (a Trees tab in Blender's sidebar) for tuning
  leaf cards and clumps. The user's tuned settings are in `assets/trees/tree_settings.json`; build from them, not
  from the defaults in `treegen.py`. See its README.
- `game/`: the Godot project. For now a play demo: a small part of Storskogen (dense forest, a trail, a meadow with
  a rise) with the old mockup trees or the new portfolio trees, a grey-box hero, the camera and controls. It runs with
  VSync off and no frame rate limit, as the user asked; its performance panel (F2) has a frame rate limit. The user
  wants a before and after switch in F2 for every optimization, to judge what it costs the look; the speed-ups (ground
  details baked into textures, tree shadows and far trees from pictures baked at startup, shadows only from trees
  within 60 m, trimmed leaf cards) each have one, and "All as before" / "All on" flips them together. Its models,
  ground textures and layout are generated in Blender by `game/tools/build_demo.py` from the mockups' kit, the tree
  portfolio and `game/tools/demo_area.py`; rebuild them after changing any of those. See `game/README.md`.
- `mockups/`: concept tools, not game code. Python scripts generate every mockup screenshot and blueprint by building
  scenes in Blender in background mode. `mockups/act1_world.py` holds the Act 1 layout as data. See `mockups/README.md`
  for how to rerun them. Generated output goes to `mockups/build/` (ignored by git); curated final images live in
  `mockups/renders/`.
- Save new work in this repository rather than only in a session's temporary folder, so it ends up under version control.
