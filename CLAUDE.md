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
  on alternate sides, their twigs' bases on the branch. Its top must end in a cone, a spire of short, upturned shoots
  round the leader, not a spray lying loose on top (the user's request). The trunks carry painted bark textures
  (`assets/trees/make_bark.py`), as the user asked for bark more like the real thing while keeping the low-poly feel:
  after the reference sheet's bark swatches, in flat plates and crisp marks, each facet its own window of the texture,
  with the rougher bark of the foot below (the birch's black, the pine's grey plates under its orange). They cost nothing
  measurable (F2's "Bark textures" turns them off to compare). The user isn't happy with the mockups' current trees
  and wants to swap them for these.
- Open trodden ground, like Tallmo's square, is worn the same way as the paths: an uneven, asymmetric outline (no clean
  ovals or other geometric shapes) and the same dirt, gravel and edges.
- Camera: a high, isometric-style view by default. Holding the right mouse button orbits it around the hero (WoW style),
  sideways and up/down, from straight down to low behind the hero. WASD is assumed to move relative to the camera (not
  yet confirmed by the user). It's an ARPG, so trees must never get in the way of the view (the user, 8 October): no
  tree crown ever just in front of the camera, and a tree the hero walks behind goes completely, all but its stump;
  shadows stay. So by default (F2's "Clear view") any tree in the way of the hero goes to its stump, and with the camera
  high the crown cut ends the trees near the camera lower the nearer they stand (none tall in front of the hero; one cut
  below its leaves goes to its stump); the user wondered about cutting the top off all trees, as Path of Exile 2 does,
  so that's in F2 too ("All trees"). For most of the game, trees should stand so far apart that one or two are on the
  screen at a time (the open forest scene); a path through thick forest, as in the thick forest scene, is cinematic,
  and there the earlier see-through stays, which the user was happy with: once the trees in front of the hero cover
  enough of it, each goes evenly half see-through, all but its stump; a tree standing alone stays solid; a point round
  the hero counts as covered once two trees each hide it through the gaps between their leaves, over the hero and 1.5 m
  round it, see-through at 40%, solid again below 20% (from playtests, `game/scripts/dev/veiltune.gd`,
  `game/tools/veiltune.py`; F2's "Thick forest" and "One tree is enough" presets, and sliders). A see-through tree's
  leaves must not move as it fades: it keeps half of its own cards where they are and the rest dissolve. The user's
  earlier ideas and complaints are in `ref_imgs/tree_disappear/`; the cone (`camera_view.png`) and the earlier ways of
  cutting trees are in F2 to compare.
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
- `game/`: the Godot project. For now a play demo with the old mockup trees or the new portfolio trees, a grey-box
  hero, the camera and controls, in twelve scenes the user asked for (`game/scripts/scenes.gd`; Tab or the Scenes
  button switches): a small part of Storskogen (dense forest, a trail, a meadow with a rise), an open forest spaced as
  most of the game should be, a thick forest with one path cleared, a very big open field, an autumn hollow (a grove sunk in the ground, trees 1-4 m apart turning
  yellow, orange and red, the ground full of leaves), a river under 3-4 m cliffs with paths up and down to it, and, for
  the rest of `ref_imgs2/`, a forest lake, a bog, a pine heath, and fog and morning sunbeams. It runs with
  VSync off and no frame rate limit, as the user asked; its performance panel (F2) has a frame rate limit. The user
  wants a before and after switch in F2 for every optimization, to judge what it costs the look; the speed-ups (ground
  details baked into textures, tree shadows and far trees from pictures baked at startup, shadows only from trees
  within 60 m, trimmed leaf cards) each have one, and "All as before" / "All on" flips them together. The
  see-through trees drawn with half their cards have one too (Fewer cards or All cards). The spruce costs more to draw
  than every other tree together; for more frames in the forest, which the user asked for as a new setting that leaves
  the others as they are, F2's "Spruce leaves" has Light and Lighter (two copies of each spray instead of four, and
  further apart). The user found the spruces look really good with Lighter, so it's the default, and both see-through
  presets and "All on" set it. At the top of F2 are the
  see-through presets, the one in use marked until a setting changes; the user wants every other setting hidden under
  "Advanced settings", so new ones go there. Its models,
  ground textures and layouts are generated in Blender by `game/tools/build_demo.py` from the mockups' kit, the tree
  portfolio and the areas in `game/tools/areas/` (one module each); rebuild them after changing any of those. See
  `game/README.md`.
- `mockups/`: concept tools, not game code. Python scripts generate every mockup screenshot and blueprint by building
  scenes in Blender in background mode. `mockups/act1_world.py` holds the Act 1 layout as data. See `mockups/README.md`
  for how to rerun them. Generated output goes to `mockups/build/` (ignored by git); curated final images live in
  `mockups/renders/`.
- Save new work in this repository rather than only in a session's temporary folder, so it ends up under version control.
