# Mockups

Concept tools for working out how wfarpg should look and feel before production starts. Nothing here is game code: the
game will be built in Godot, with assets made in Blender.

Everything is generated from code. Each scene script starts Blender in the background, builds the scene from scratch
(terrain, low-poly trees, rocks, buildings, characters, lighting, camera), renders it and exits without saving, so there
are no `.blend` files. Rerunning a script gives the same picture, apart from faint render noise.

## The look & feel board

- Live board: <https://claude.ai/artifact/Q7Crs9hY9EhaN47YRE2YrP> (a private claude.ai artifact)
- `board/wfarpg-board.html`: source of the board page. The page only draws what is in the artifact's database.
- `board/items.json`: snapshot of that database: every note, section and image, with position, text and the
  Want / Maybe / Avoid mark.
- `board/assets.json`: which file under `renders/` each image on the board is.

## Design history

`HISTORY.html` logs every step of the board, from the first sketch to the newest mockups. Each step shows the request,
what changed, the images, any earlier attempts, and the board's notes word for word as they read at the end of that
step. Open it in a browser from this folder. A private copy is published at
<https://claude.ai/artifact/L74mBkoQbstMGxKg7S1cND>.

- `board/history.json`: the history data. Each step lists the board items it added or changed, as they read at the end
  of the step, and its earlier attempts.
- `history_log.py`: builds the page from it.
- `renders/wip/`: in-between renders shown as earlier attempts.

After a step that changes the board:

1. Refresh `board/items.json` and `board/assets.json` from the live board.
2. Run `python3 history_log.py --record <step-id>`. It appends a step with every item added, changed or removed since
   the last step.
3. In `board/history.json`, fill in that step's `asked_at`, `title`, `section`, `asked` and `changed`. List any
   in-between renders saved to `renders/wip/` under `wip`.
4. Run `python3 history_log.py` to rebuild `HISTORY.html`, and `python3 history_log.py --web build/history_web` for the
   web copy. Publish `build/history_web/index.html` to the URL above, together with its `img/` and `fonts/` files.

## Act 1 pipeline

| Script | What it does |
|---|---|
| `act1_world.py` | Act 1 as data: zone outlines traced from `ref_imgs/act1_layout.png` (1 sketch unit is about 1.2 m), terrain height, forest density, roads, water, quests, waystones and the screenshot cameras A–J. The other scripts read from here. |
| `act1_check.py` | Checks the layout: roads, quests and cameras on walkable ground, steepest slope. |
| `act1_dump.py` | Exports the world data to JSON for the blueprint script. |
| `act1_maps.py` | Bakes the map layers: shaded terrain, contours, tree positions, the height profile. |
| `act1_blueprint.py` | Draws the act blueprint and the Storskogen blueprint from the baked layers. |
| `act1_shots.py` | Builds and renders the 3D screenshots A–J. |
| `hud_act.py` | Paints the HUD over rendered screenshots. |
| `forest_cam.py` | The low-poly kit (plants, rocks, hero, wraiths, ground material, lighting, orbit camera) plus the earlier forest close-ups and camera-angle shots. `act1_shots.py` builds on it. |

Requirements, on Linux or Windows: Blender 5.2 and Python 3 with Pillow, as `blender` and `python3` on PATH (the
repository's `README.md`), and Google Chrome or Chromium, which renders the HUD and blueprint labels (`chrome.py`
finds it; `CHROME` points it at another). Run from this folder. Output goes to `build/`, which git ignores.

```sh
blender -b --factory-startup --python act1_check.py
blender -b --factory-startup --python act1_dump.py
blender -b --factory-startup --python act1_maps.py
python3 act1_blueprint.py

# screenshots: use `preview` instead of `final` for quick low-resolution frames
blender -b --factory-startup -P act1_shots.py -- build/act1/shots final tallmo angen tatskogen utsikten trollgrytan
python3 hud_act.py build/act1/shots build/act1/final tallmo angen tatskogen utsikten trollgrytan
```

Shot ids: `tallmo`, `angen`, `tatskogen`, `utsikten`, `trollgrytan`, `harddalen`, `gamlagarden`, `dimskogen`,
`dimmyren`, `odeskogen`.

The forest close-ups and camera angles work the same way:

```sh
blender -b --factory-startup -P forest_cam.py -- build/forest final day_path day_tarn fog_path fog_bog cam_behind
python3 hud_act.py build/forest build/forest/hud day_path day_tarn fog_path fog_bog cam_behind
```

Shot ids: `day_path`, `day_tarn`, `fog_path`, `fog_bog`, `cam_default`, `cam_topdown`, `cam_side`, `cam_behind`,
`cam_tarn`, `cam_fogbehind`.

## Renders

The final images shown on the board, by board section:

| Folder | Board section |
|---|---|
| `renders/forest_v1`, `forest_v2`, `forest_v3` | Act 1: Pine forest (versions 1–3 of the close-ups) |
| `renders/camera` | Camera control |
| `renders/hud_v1`, `renders/hud_v2` | HUD style |
| `renders/act1` | Act 1: the whole act (`*_first.jpg` are the blueprints as first published) |
| `renders/diagrams` | Game mechanics |
| `renders/reference_copies` | Smaller copies of `ref_imgs/` used on the board |
| `renders/worn_paths`, `renders/worn_paths_v2` | Worn paths, versions 1 and 2 (before/after pairs; each "before" is the previous render) |
| `renders/town_square` | Tallmo's square |
| `renders/play_demo` | Play demo (Godot): screenshots from the game |
| `renders/play_demo_paths` | Play demo: path colours and speed (the path colour themes, shadow options, ground detail levels and the performance panel) |
| `renders/play_demo_sight` | Play demo: worn paths, trees out of the way, frame rate (Forest earth, the wider wear, the first hiding of trees in the way, the panel) |
| `renders/play_demo_in_the_way` | Play demo: trees go once they're in the way (walking up to a pine, low cameras) |
| `renders/play_demo_speed` | Play demo: speed (all the speed-ups as before and on, and before and after each one) |
| `renders/play_demo_stumps` | Play demo: trees cut to stumps (before and now, the stumps close up, by the trunk or by any part) |
| `renders/play_demo_in_front` | Play demo: trees in front of the hero (the three ways of cutting trees on a walk, camera low and high) |
| `renders/play_demo_beside` | Play demo: trees beside the hero stay (the meadow pine, before and now) |
| `renders/play_demo_trunks` | Play demo: trunks stay, and an x-ray (the meadow pine again; the ways of cutting trees on a walk, camera low and high) |
| `renders/play_demo_cone` | Play demo: the cone (the camera_view sketch beside it in the thicket, walking in behind a spruce, the ways of cutting trees on a walk, camera low and high, the dither close up) |
| `renders/play_demo_trunk` | Play demo: hiding in the leaves (walking in behind a spruce, Trunk and the cone; the ways of cutting trees on a walk, camera high and low) |
| `renders/play_demo_veil` | Play demo: see-through spruces (walking in behind a spruce, before and now; close up) |
| `renders/play_demo_see_through` | Play demo: see-through, faster see-through, without the shift, and only where the forest is thick (a birch and a pine before and after; the trail with the area shown; the thicket with the camera low; the slowest low-camera views, all cards and fewer, and all see-through or all but the nearest hidden; see-through trees on their stumps; a pine going see-through before and now, `no_shift.webp` animated; the slowest views with half the cards; walking past the lone pine, and thick forest, before and now) |
| `renders/play_demo_spruce_top` | Trees: the spruce's top (the forest's edge from the meadow and the default camera, before and now; the portfolio's before and now sheet is `../assets/trees/previews/v4/spruce_top_before_after.png`) |
| `renders/play_demo_spruce_light` | Play demo: lighter spruces (as tuned, Light and Lighter in the forest, and the trees side by side) |
| `renders/play_demo_scenes` | Play demo: scenes (each scene as it opens, and close-ups) |
| `renders/play_demo_bark` | Trees: bark (before and now, close up and in the scenes; the bark textures) |
| `renders/play_demo_clear_view` | Play demo: trees out of the way (four scenes as they open, before and now; behind a pine; the open forest) |
| `renders/play_demo_grass_size` | Plants: bigger grass, and natural path edges (strand sizes and counts, walking through, the user's marked screenshot, the dirt's edges before and now) |
| `renders/play_demo_bog_grass` | Plants: Clumps, no green balls, and grass for the bog (the bog before and now, close up and walking; the bog grass in the portfolio and its cards; the open forest and the meadow without the green balls) |
| `renders/play_demo_leaves` | Autumn hollow: leaf-filled ground, and leaves that stir (the hollow before and now, closer; walking into a pile, `walking_through_leaves.webp` animated; standing in a deep pile; the stronger stirring, `stirring_game_camera.webp` and `stirring_close.webp` animated) |
| `renders/play_demo_bushes` | Leaves that stay put, more piles, room between the trees, and bushes (the lasting lane, `lasting_lane_game_camera.webp` and `lasting_lane_close.webp` animated; the autumn hollow before and now; bushes in four scenes and the open forest) |
| `renders/wip` | Not on the board: in-between renders shown in the design history |

## History

Earlier versions of the scripts, kept for reference. Each produced an earlier section of the board.

| Script | Produced |
|---|---|
| `history/forest.py` | Forest close-ups, version 1 (faceted ground) |
| `history/forest_v2.py` | Version 2 (smooth, textured ground) |
| `history/forest_v3.py` | Version 3 (winding paths, chunky rocks, one-piece trunks) |
| `history/hud.py`, `history/hud_cam.py` | The first placeholder HUD |
| `history/hud_fantasy.py` | HUD style, version 1 |
| `history/hud_sharp.py` | HUD style, version 2, before `hud_act.py` generalised it for Act 1 |

The camera, HUD and Act 1 renders were made before the worn paths changed the ground shader. To reproduce them
exactly, run `forest_cam.py` and `act1_shots.py` from commit `ce42951`.

## Fonts

Cinzel and Cinzel Decorative by Natanael Gama, under the SIL Open Font License (`fonts/OFL-Cinzel.txt`).
