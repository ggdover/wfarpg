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

- Engine: Godot. 3D models: made in Blender. Art style: low-poly 3D.
- Ground is a smooth, flat surface with painted textures (moss, grass patches, needle litter, gravel on dirt paths).
  Props such as trees, bushes and rocks are faceted low-poly shapes.
- Paths are worn into the grass by feet, so they never end in a hard line: the grass thins out and turns trampled toward
  them, and gravel and pebbles show in the dirt. Avoid hard edges between ground textures in general.
- Camera: a high, isometric-style view by default. Holding the right mouse button orbits it around the hero (WoW style),
  sideways and up/down, from straight down to low behind the hero. WASD is assumed to move relative to the camera
  (not yet confirmed by the user).
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

- `ref_imgs/`: the user's reference images and the Act 1 layout sketch.
- `mockups/`: concept tools, not game code. Python scripts generate every mockup screenshot and blueprint by building
  scenes in Blender in background mode. `mockups/act1_world.py` holds the Act 1 layout as data. See `mockups/README.md`
  for how to rerun them. Generated output goes to `mockups/build/` (ignored by git); curated final images live in
  `mockups/renders/`.
- Save new work in this repository rather than only in a session's temporary folder, so it ends up under version control.
