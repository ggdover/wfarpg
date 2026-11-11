# Hero portfolio

The player character: the user's Tripo3D models of an ARPG's starting hero, a man in a linen tunic, trousers and boots
without much gear or armour, and low-poly versions of them, made from the models or after them, to judge which way the
game's characters should go (1 November). The user's plan for every character in the game is a detailed model, from
Tripo3D for now, made low-poly by decimation or retopology, so `lowpoly.py` is meant for all of them.

| Figure | Triangles | Made by |
|---|---|---|
| Tripo3D 20k, as made | 19,844 | The user's 20k model with its texture, only made matte |
| Tripo3D 5k, as made | 4,903 | The user's 5k model, the same |
| Faceted 3000 | 2,996 | The 20k model decimated (its edges collapsed, mirrored across the middle) to that many triangles; each face one flat colour, the average of the texture under it |
| Faceted 1500 | 1,494 | The same, to 1500 |
| Faceted 800 | 794 | The same, to 800 |
| Painted 1500, 12 colours | 1,494 | Faceted 1500 with its colours brought down to 12, so it reads painted rather than photographed |
| Retopology: even quads | 2,626 | A new mesh of even quads over the 20k model (a voxel remesh, then QuadriFlow), its colours blended with their neighbours', then brought down to 10 |
| Our own: wanderer | 1,468 | Built from scratch by script after the Tripo model (`herogen.py`): a tunic with a ragged hem and a rope belt, trousers, wrapped shins, boots, stubble and hair; each face a flat colour from the model's palette, a little lighter or darker at random, as the trees' faces are |
| Our own: light gear | 1,611 | The wanderer with a shoulder guard, a strap across the chest, bracers and a belt pouch |

All the low-poly ones are 1.8 m tall and stand on the 20k model's skeleton, each on a copy of its own, with the 20k
model's bone weights: decimating keeps them, and the retopology and our own get theirs carried over from the 20k model,
face by face. So any of them can take the same animations. The skeleton is Tripo's auto-rig, with Unreal-style names:
61 bones (`root`, `pelvis`, `spine_01` to `spine_03`, `neck_01`, `head`, and on each side the `clavicle`, `upperarm`,
`lowerarm` and `hand` with fingers, the `thigh`, `calf`, `foot` and `ball`, and twist bones). The 5k model came with a
skeleton of its own, Mixamo's (65 bones, `mixamorig:Hips` and on).

Open `hero_portfolio.blend` in Blender 5.2 to look at them. It holds:

- `Heroes`: the figures standing as they were made, arms out, each with its skeleton (`Faceted1500` on
  `Faceted1500Rig`, and so on).
- `Walking`: a second row 3 m behind, the same meshes on copies of their skeletons, taking a step, to see how each
  bends at the shoulders, elbows, hips and knees.
- `Portfolio`: the name signs with the triangle counts, the ground, the sun and the camera.

The Tripo models' textures are in `build/`, which isn't kept in git: if they show pink, rebuild (below).

## Previews

`previews/` holds the latest renders:

- `heroes_front.png`, `heroes_three_quarter.png` (turned 35°) and `heroes_back.png`: the first row, captioned.
- `heroes_walking.png`: the second row, taking a step.
- `heroes_game_view.png`: the second row from the game's high camera, 55° down from 16 m, on grass.
- `heroes_in_game.png` and `heroes_in_game_close.png`: the low-poly ones in the play demo itself, on the open forest's
  path, in its light and with the game's low-poly material, from the game's camera and from near and low (In the game,
  below). From the front of the row, lower left, to its back: Faceted 3000, 1500 and 800, Painted 1500, Retopology,
  the wanderer, with light gear.

## How they differ

- Decimating keeps the model's shape best for its triangles: from the game's camera even Faceted 800 reads much as the
  original does. Close up, its colours, taken from a photographic texture, look mottled, and the face is a few big
  triangles.
- Painting with fewer colours tidies the mottling into areas of colour, as a hand-painted model has them, but keeps
  some stains.
- The retopology's quads are all one size, the kind of mesh that's easiest to work on by hand afterwards, but at a
  budget like the others' it blurs the face, the hands and the folds into soft lumps, coloured like a mosaic. Asked
  for 800 quads, QuadriFlow lost a forearm, so it has about 1300.
- Our own are the cleanest and simplest: flat colours in clear parts, the joints where they bend, gear that is easy to
  add or swap. They're plainer than the Tripo model, more stylized than it.

## Rebuilding

In this folder:

```sh
blender -b --factory-startup -P make_heroes.py                  # hero_portfolio.blend, previews/ and build/heroes.glb
blender -b --factory-startup -P make_heroes.py -- --no-render   # without the renders
```

The same on Linux and Windows. It extracts the Tripo3D exports, `ref_model/default/20k_triangle_with_rig.zip` and
`5k_triangle_with_rig.zip` (each a rigged .fbx with its textures), into `build/Tripo20k/` and `build/Tripo5k/`, where
the .blend finds their textures. The building is in:

- `lowpoly.py`: from a detailed model to low-poly ones. `import_tripo` brings a Tripo3D export in at its height,
  `decimate` and `retopo` make the low-poly meshes, `face_colours` and `reduce_colours` colour them, and `pose` puts a
  skeleton in a test pose.
- `herogen.py`: our own hero, lofted in rings of faces along the 20k model's skeleton.
- `make_heroes.py`: the portfolio, its renders and the export.

The seeds are fixed, so rebuilding gives the same figures.

## In the game

`make_heroes.py` exports the low-poly figures (not the Tripo models as made), standing as made on their skeletons, to
`build/heroes.glb`, as the game's models are made (`game/tools/build_demo.py`): the faces' colours sRGB-encoded in
`COLOR_0` and a second UV map of 1s for the ambient occlusion, which the game's low-poly material reads. The demo
doesn't use them yet; to see them in it:

```sh
python3 game/tools/play.py --script res://scripts/dev/heroes.gd -- --scene=open_forest --nohud --out=out.png
```

stands them in a row where the hero stands, the hero hidden, takes a screenshot and quits (`--close` for the camera
near and low; a relative `--out` is from `game/`). It reads the .glb as the game runs, so nothing is imported into
`game/`.

## Run portfolio

Of the hero portfolio the user kept five models, Faceted 3000, 1500 and 800, Painted 1500 and Retopology, and asked
for rigging and a running animation for them, about fifty combinations to look through and narrow down (2 November):
ten runs on seven rigs, each on all five models. Looking through them, the user found that all ten seemed to run on
their toes, the front of the foot, where they wanted each foot planted heel first, the forefoot coming down only a
moment after; asked for forty more runs, fifty in all, to narrow down; and found the page for them too complicated,
wanting each run shown clearly once from the side and once in the play demo (the same day). So there are now fifty
runs, every one landing heel first, in six families, on the same seven rigs and five models. Having marked fifteen of
them Want, Maybe or Avoid in a gallery of them all, the user asked for a page that shows one run at a time to rate
from 1 (I don't like it) to 10 (I really like it), with a comment if they like, the ratings kept for Claude to make the
next attempt from, round after round, until a run is right; and easy to use from a phone, stopping and picking up
later (11 November): the rating page.

Open `run_portfolio.blend` to look at them: a row for each rig, the five models in each, all running Athletic; pick
another run in the Action editor (each skeleton has an action per run, named after it; the helper joints' and the cloth
bones' skeletons have their own, ending in `_helpers` and `_cloth`, and the corrective shapes theirs, ending in
`_shapes`, on the figures' shape keys). `stand` is the hero standing at ease when it stops, its weight on one leg: a 4 s
loop of a slow breath, a little sway and a look to either side.

In short:

- To rate the runs: the rating page, https://claude.ai/artifact/Y7LgDQNjNfHqi4Dy1CHBcF, where the ratings are kept
  (The rating page, below).
- To run as them in the play demo: `python3 game/tools/play.py --script res://scripts/dev/runs.gd` (from the
  repository's root; Clips and the game, below). It reads the game's files from `build/runs/`, which isn't
  kept in git: on a fresh checkout, `make_heroes.py -- --no-render` and then `make_runs.py -- --no-render` make them,
  rendering nothing.
- To tune a run: `run_portfolio.blend`'s Runs tab (below); after changing a run, `check_runs.py`.
- To build it all again: `blender -b --factory-startup -P make_runs.py`, then `python3 record_runs.py` for the
  recordings in the game and `make_runs.py -- --page` to put them on the page.

### The runs

All run at the hero's speed in the demo, 5.5 m/s, in place, for the game to carry the hero along: each foot on the
ground moves back under it at that speed, so it stays put on the ground as the hero moves. They differ in rhythm,
posture and character, and come in six families (`runs.py`, `STYLES`, in the order of `FAMILIES`), numbered as the
rating page numbers them:

**The first ten**: the runs from before, now planting the heel first.

| # | Run | Steps a minute | Step | On the ground | In the air | Bounce | What it's like |
|---|---|---|---|---|---|---|---|
| 1 | Athletic | 180 | 1.83 m | 147 ms | 187 ms | 7 cm | A strong, even run: a firm lean, the knees driving, the arms pumping at the elbow. |
| 2 | Sprinter | 225 | 1.47 m | 131 ms | 136 ms | 3 cm | Quick and all-out: high knees, heels kicked up, quick light heel-to-toe steps, the body level, the arms pumping hard with open hands. |
| 3 | Easy stride | 157 | 2.11 m | 169 ms | 215 ms | 7 cm | Relaxed and upright: low knees, a low heel kick, the arms hanging loose and low, the head riding along. |
| 4 | Heroic | 164 | 2.02 m | 143 ms | 224 ms | 10 cm | Chest up and chin high, long floating strides, the arms long and swinging high, fists closed. |
| 5 | Heavy | 150 | 2.20 m | 192 ms | 208 ms | 9 cm | A big man in armour: wide feet, low heavy landings heel first, long on the ground, rocking side to side, the arms held out and swinging little. |
| 6 | Nimble | 240 | 1.38 m | 155 ms | 95 ms | 2 cm | Low, quick and light: short fast steps rolling heel to toe, the body level, the arms tucked in tight, the head still. |
| 7 | Guarded | 200 | 1.65 m | 171 ms | 129 ms | 3 cm | Ready to fight: crouched, fists up by the chin, the elbows in, short steps, chin down. |
| 8 | Bounding | 138 | 2.38 m | 143 ms | 290 ms | 19 cm | Long, floating leaps: fewer steps, the legs spread wide in the air, the arms swinging long. |
| 9 | Snappy | 212 | 1.56 m | 133 ms | 150 ms | 12 cm | Cartoon energy: a big bounce, heels to the seat, knees high, arms flung wide, the poses held and snapped between, readable from far away. |
| 10 | Natural | 189 | 1.74 m | 162 ms | 155 ms | 6 cm | As a real runner moves at this speed: a slight lean, quick light steps landing nearly in line, heel first, each foot on the ground about as long as it's in the air, relaxed hands crossing a little in front, the head still. |

**Runners**: real runners' forms, from the marathon to the trail.

| # | Run | Steps a minute | Step | On the ground | In the air | Bounce | What it's like |
|---|---|---|---|---|---|---|---|
| 11 | Marathoner | 200 | 1.65 m | 159 ms | 141 ms | 3 cm | Economical over long miles: a slight lean, quick short steps with little bounce, low knees and a low heel kick, the hands low and loose, swinging close by the waist. |
| 12 | Miler | 212 | 1.56 m | 147 ms | 136 ms | 4 cm | A middle-distance racer: tall and quick, the knees coming well up, the arms swinging fully at a right angle, loose shoulders and relaxed hands. |
| 13 | Trail runner | 212 | 1.56 m | 159 ms | 125 ms | 3 cm | Sure-footed over roots and stones: a little crouched, the feet a touch apart, short quick steps, the arms held out a little for balance, the eyes on the ground ahead. |
| 14 | Long strider | 144 | 2.29 m | 142 ms | 275 ms | 8 cm | Long, reaching strides at an unhurried rhythm: each foot reaching far out and planting, the body passing smoothly over it, the arms swinging long and low. |
| 15 | Quick feet | 232 | 1.42 m | 140 ms | 119 ms | 2 cm | Short, quick, light steps, the feet barely leaving the ground, little bounce, the arms making small quick swings, the body level and calm above them. |
| 16 | Glide | 164 | 2.02 m | 154 ms | 213 ms | 3 cm | Smooth as if on rails: the head and hips hardly rising or falling, long flowing steps on soft knees, the arms swinging long and easy, the head quite still. |
| 17 | Springy | 164 | 2.02 m | 143 ms | 224 ms | 19 cm | Every step a spring: the hips sinking into each landing and bouncing high off it, the heels kicking up, the arms lifting with the bounce. |
| 18 | Courier | 212 | 1.56 m | 147 ms | 136 ms | 4 cm | A messenger with news to carry: quick and set on getting there, a steady forward lean, the arms swinging briskly but low, the head up. |

**Fighters**: fighting men on the move, from the charge to the soldier's double time.

| # | Run | Steps a minute | Step | On the ground | In the air | Bounce | What it's like |
|---|---|---|---|---|---|---|---|
| 19 | Charge | 189 | 1.74 m | 168 ms | 149 ms | 5 cm | Head down and driving forward: a deep lean from the hips, the fists pumping hard, the knees punching forward, each foot dug in. |
| 20 | Barbarian | 164 | 2.02 m | 154 ms | 213 ms | 10 cm | A big, wild-strong man: chest out, the arms swinging wide and high with the fists closed, heavy driving steps, the shoulders rolling. |
| 21 | Brawler | 180 | 1.83 m | 153 ms | 180 ms | 7 cm | A street fighter on the move: fists loose in front of the chest, the shoulders rolling side to side, a bouncing, swaggering step, the chin tucked. |
| 22 | Berserker | 200 | 1.65 m | 159 ms | 141 ms | 6 cm | Wild fury: a deep lean, the arms flung out and round with the fists clenched, the head down, the knees and heels high, every step a lunge. |
| 23 | Double time | 171 | 1.92 m | 144 ms | 207 ms | 6 cm | A soldier's double time: upright and square, a strict rhythm, the fists swinging straight forward and back on nearly straight arms, the eyes front. |
| 24 | Knight | 157 | 2.11 m | 146 ms | 238 ms | 9 cm | As if in mail: the trunk held stiff and upright and hardly turning, the arms a little out from the body and swinging short, heavy, deliberate steps. |
| 25 | Bull | 157 | 2.11 m | 161 ms | 222 ms | 10 cm | Massive and unstoppable: the head and shoulders down and forward, the shoulders hunched up, wide heavy steps, the arms swinging low and wide. |
| 26 | Stomper | 157 | 2.11 m | 150 ms | 234 ms | 13 cm | Pounding the ground: each heel planted hard and far out in front, the body jolting down onto it, upright, the arms swinging stiffly. |
| 27 | Roadwork | 200 | 1.65 m | 141 ms | 159 ms | 6 cm | A boxer out on a morning run: light and springy, the fists up near the chest swinging short, the shoulders loose, the chin tucked in. |
| 28 | Veteran | 180 | 1.83 m | 143 ms | 190 ms | 4 cm | An old campaigner saving his strength: upright and stiff, short low strides, hardly turning, the arms bent and swinging only a little. |
| 29 | Ducking | 189 | 1.74 m | 177 ms | 139 ms | 3 cm | Running low under flying arrows: the knees deeply bent and the hips low but the back kept upright, the head drawn down between raised shoulders, the arms tight. |

**The wilds**: stealth and the hunt: low, quiet and watchful.

| # | Run | Steps a minute | Step | On the ground | In the air | Bounce | What it's like |
|---|---|---|---|---|---|---|---|
| 30 | Prowler | 189 | 1.74 m | 165 ms | 152 ms | 3 cm | Stalking at speed: low and hunched, the head pushed forward but the eyes level, the arms low and a little out, soft, quiet landings. |
| 31 | Rogue | 225 | 1.47 m | 160 ms | 107 ms | 2 cm | Quick and sly: bent forward, short fast steps, the arms swept low and back with the hands open, the head up and alert. |
| 32 | Scout | 212 | 1.56 m | 159 ms | 125 ms | 3 cm | Light and watchful: short quick steps a little crouched, the arms close and swinging small, the head up and steady, looking far ahead. |
| 33 | Ranger | 157 | 2.11 m | 157 ms | 226 ms | 8 cm | A woodsman covering ground: long easy strides with the knees coming forward, a forward lean, the arms low and loose with the hands half open, steady and tireless. |
| 34 | Hunter | 180 | 1.83 m | 153 ms | 180 ms | 4 cm | Closing on quarry: leaning in, the head dead still and level, compact arms pumping short and quick, long low strides. |
| 35 | Lope | 138 | 2.38 m | 152 ms | 282 ms | 7 cm | A long, easy lope that could go on all day: unhurried, little bounce, long strides on soft knees, the arms hanging loose and swinging low. |

**Moods and people**: how a mood, or a kind of man, runs.

| # | Run | Steps a minute | Step | On the ground | In the air | Bounce | What it's like |
|---|---|---|---|---|---|---|---|
| 36 | Swagger | 164 | 2.02 m | 143 ms | 224 ms | 8 cm | Cocky and loose: chest out and chin up, the hips rolling, the open hands swinging across the body, taking his time about it. |
| 37 | Weary | 171 | 1.92 m | 150 ms | 200 ms | 7 cm | Running on his last legs: the head hanging forward, the shoulders slumped, the arms swinging low and heavy, the feet kept low and landing heavily. |
| 38 | Fleeing | 189 | 1.74 m | 142 ms | 174 ms | 7 cm | Running for his life: upright, leaning back a little with the head up, the arms flailing wide with open hands, long panicked strides. |
| 39 | Eager squire | 225 | 1.47 m | 149 ms | 117 ms | 9 cm | Young and keen: bouncing along on quick steps, the arms pumping a little too high with open hands, the head bobbing. |
| 40 | Farmhand | 171 | 1.92 m | 150 ms | 200 ms | 7 cm | Gangly and loose-limbed: the feet turned out, the elbows flapping out to the sides, floppy wrists, the head nodding along. |
| 41 | Monk | 200 | 1.65 m | 141 ms | 159 ms | 4 cm | Calm and contained: very upright, the arms bent tight and close and barely swinging, quick light steps, the head quite still. |
| 42 | Dancer | 180 | 1.83 m | 120 ms | 213 ms | 10 cm | Light and graceful: the feet landing on one line, the hips swaying, the arms floating out with soft hands, the chin lifted. |

**Arms and rhythm**: ways with the arms, and with the beat.

| # | Run | Steps a minute | Step | On the ground | In the air | Bounce | What it's like |
|---|---|---|---|---|---|---|---|
| 43 | Straight arms | 180 | 1.83 m | 143 ms | 190 ms | 8 cm | The arms swinging nearly straight from the shoulders, like a boy at play: long arcs forward and back with open hands, an upright, bouncy run. |
| 44 | Wide arms | 180 | 1.83 m | 150 ms | 183 ms | 7 cm | The arms swinging long and wide, out to the sides and round, the hands passing far from the body: a broad, open run. |
| 45 | Cross-body | 171 | 1.92 m | 147 ms | 203 ms | 8 cm | The shoulders turning far against the hips, the arms swinging round in front of the chest with them, the whole trunk winding and unwinding with each step. |
| 46 | Piston arms | 189 | 1.74 m | 149 ms | 168 ms | 6 cm | The arms driving straight forward and back like pistons, close by the sides, the fists punching ahead and pulling hard behind, a strong upright run. |
| 47 | High stepper | 171 | 1.92 m | 136 ms | 214 ms | 9 cm | The knees lifted high in front with every stride and the feet stepping down onto the heel, the body tall, the arms pumping to match. |
| 48 | Gazelle | 150 | 2.20 m | 136 ms | 264 ms | 18 cm | Light, leaping strides: a quick spring off each foot into a long float, the knees lifting, the arms swinging light and high, the body tall. |
| 49 | Drumbeat | 157 | 2.11 m | 146 ms | 238 ms | 12 cm | A marked, even beat: each landing punctuated by a dip of the head and body, the arms snapping through their swing and holding at the ends. |
| 50 | Fluid | 171 | 1.92 m | 144 ms | 207 ms | 8 cm | Soft and flowing: the arms trailing the legs and swinging in loose loops, the wrists relaxed, every step easing into the next. |

Natural has the rhythm measured in runners at this speed (20 km/h, Hanley et al. 2022: 3.2 steps a second of 1.74 m, a
foot on the ground for 166-178 ms and in the air for 133-150 ms, the hips going 7-8 cm up and down), as near as the
hero's legs, shorter than theirs, reach; the Marathoner and the Miler keep close to it too. The others are styled, most
of them longer in the air than a runner is at this speed, so they float more. The Sprinter runs tall and drives off a
nearly straight leg, as sprinters do, its knees no higher than its hips and its hands rising beside the chin without
crossing the body.

### Heel first

The user found the first runs seemed to run on the front of the foot: each heel touched down for a frame, the foot
nearly flat as it came in, and the heel was up again for most of the time the foot was on the ground. Every run now
plants its foot as a runner landing on the heel does:

- Late in the swing the foot comes up, the toes toward the shin (`dorsi`), and by three quarters of the swing it has
  the pitch it lands with, which it holds as it comes down, so the heel leads.
- The heel lands first, the toes 10-20° up (`strike`), ahead of the knee, the shin leaning forward.
- The forefoot comes down a moment after, by a fifth of the time on the ground (`flat_at`): two frames at 60 a second.
- The foot stays planted flat until well past the hips going over it (`heel_at`, 60% of the time on the ground), and
  only then does the heel rise and the toes push off.

Landing on the heel ahead of the body costs reach behind it, so each run's landing reach and time on the ground
(`land`, `stance`) were worked out together, for the knee bend wanted as the heel lands (12-34°: a nearly straight
leg, bent more in the crouched runs) and as the foot leaves (19-42°), so the heel plants with the shin leaning forward
and the push-off still comes off a nearly straight leg, the knee bent some 20-30°, as a runner's is, but in the
crouched runs (Nimble, Snappy, Guarded, Ducking, the Prowler and the Rogue), which keep it bent more.

### How a run is made

A run is a handful of numbers (`DEFAULTS` in `runs.py`), and every frame is worked out from them:

- The hips sink into each landing and fly between steps as a runner's do: gravity's arc in the air, a spring's dip on
  the ground, tied so the speed carries over at both ends.
- A foot on the ground stays put on it, rolling from the heel to flat, then onto the ball as the heel rises, the toes
  bending on the ground. The legs reach it by IK, the knees toward the front.
- In the air the ankle follows a curve through a few points: kicking back and up, passing under the hips, swinging out
  in front and coming down, still going back as it lands, so it plants. The curve keeps within the leg's reach, and
  meets the foot on the ground at the speed it left it.
- The pelvis turns, tips and sways with the legs, the shoulders turn against it and roll a little toward the foot on
  the ground, the trunk leans and dips after each landing, the head holds still and nods a little. The upper back can
  round, the head pushed out ahead (`hunch`; below 0, the chest out), and the shoulders be held up or let drop
  (`shoulders`).
- The arms swing against the legs, the elbows bending more in front, the wrists trailing, the hands loosely closed,
  the thumb across the fingers.

Every bone's turn is worked out in the armature's space and only then put into the bone's own axes, so Tripo's bone
rolls don't matter, and any skeleton with these bone names can run them. `check_runs.py` checks every run over its cycle
(and the stand): the feet on the ground stay where they landed (to within a millimetre), no foot goes into the ground or
hangs over it, no leg stretches past its length, nothing in the body jerks (its turning speed changing at once) but the
leg as the foot lands, which is meant to, and the hands keep off the body's middle, below the shoulders and clear of the
hips and thighs as they swing past, the forearms out of the chest (on Faceted 1500's mesh); that every foot lands heel
first, its toes up, and is flat on the ground for at least 30% of its time down; that no two runs look nearly the same
(every two runs' joints at least 4 cm apart on average over a cycle, or their rhythms a tenth apart); and that every
run's numbers lie within the run editor's sliders, so the editor shows each as made. After changing a run:

```sh
blender -b --factory-startup -P check_runs.py                   # every run; exits 1 if one fails
```

To tune a run, open `run_portfolio.blend` and let it run its script (Blender asks): the run editor is in the 3D
view's sidebar (N), its Runs tab. Pick a run and move its sliders, grouped as above (rhythm, feet, hips, the leg in the
air, trunk, arms, head and cloth), each with a hint; every figure in the file runs it as you go (press Space to play),
the panel says how it measures, and Check says what `check_runs.py` would find wrong. Key on every rig keys the helper
joints', cloth bones' and corrective shapes' actions too, and Reset goes back to the run as made. Save settings writes
the runs you changed, where they differ, to `run_settings.json`, which `runs.py` reads over its own numbers, so the next
`make_runs.py` build and the play demo run them as tuned (`run_editor.py`; start Blender with
`blender run_portfolio.blend --python run_editor.py` if the file's script isn't allowed to run).

### The rigs

`rigs.py` binds each model's mesh to the skeleton seven ways, with at most four bones on a vertex, as the game takes
them:

| Rig | How |
|---|---|
| Tripo weights | The weights Tripo3D's auto-rig gave the 20k model, carried over as the models were made |
| Smoothed | Those, smoothed across the mesh: softer, wider bends |
| Bone heat | Blender's own automatic weights, from bones running joint to joint (Tripo's stop short of the next joint), worked out on a closed copy of the 20k model and carried over |
| Rigid | Each vertex on one bone only: sharp folds at the joints, as in early 3D games |
| Helper joints | Bone heat's weights, with helper bones at the hips, knees, shoulders and elbows that turn half as far as the joint: the vertices round a bend ride on them, so a bent knee or elbow keeps its thickness instead of pinching |
| Cloth bones | Bone heat's weights, with four cloth bones in the tunic's skirt, at its front, back and sides, hanging from the belt: the skirt rides on them more the nearer the hem, so it drapes over a knee driving forward instead of clinging to the thigh, and its hem swings on after each landing |
| Corrective shapes | Bone heat's weights, with sixteen corrective shapes, at two bends of each knee, hip and elbow and one of each shoulder forward and back: each is the difference, at that bend alone, between plain skinning, which thins a bend, and Blender's volume-keeping (dual quaternion) skinning, which the game can't do, carried back to the rest pose. Each run turns them on as far as it bends each joint, blending between a joint's two shapes, so the game gets the fuller bends from shapes and plain skinning |

The skeleton is the 20k model's, its pelvis freed from the root so the hips can rise and fall while the root stays at
the feet; the helper joints' skeleton has eight more bones, the cloth bones' four. The skirt is told from the trousers
by colour (the tunic's light faces, between the belt and the hem, clear of the thighs and on the hips' bones, so not
the hands hanging beside them); each run turns the cloth bones from how far the thighs swing (`runs.py`, `skirt`).
The corrective shapes (`rigs.add_correctives`, `CORRECTIVES`) are played by an action of their own for each run
(`<run>_shapes`, on the figures' shape keys), and go into the game's files with the runs, merged into the same
animations; `rigs.corrective_weights` says how far each is on for any pose.

How they deform, measured over the athletic and snappy runs on all five models (`measure_rigs.py`, below): for each
model the mesh's edges at their worst, the longest one in a thousand, and the least volume the mesh keeps, against the
model as made, standing; the ranges run over the five models:

| Rig | Edges stretch to | Volume kept, at least |
|---|---|---|
| Tripo weights | 2.1-3.7× | 86-90% |
| Smoothed | 2.4-3.9× | 84-89% |
| Bone heat | 2.0-2.4× | 86-89% |
| Rigid | 7.4-9.2× | 91-94% |
| Helper joints | 2.0-2.4× | 88-91% |
| Cloth bones | 2.5-4.3× | 87-89% |
| Corrective shapes | 2.3-2.7× | 92-95% |

```sh
blender -b run_portfolio.blend -P measure_rigs.py               # the table again, after changing a rig
```

Bone heat spreads each bend the widest, so it stretches the skin least; Rigid keeps each part whole and so more volume
than the blended weights, but stretches the skin across each joint the furthest; the helper joints keep more volume than
bone heat's weights they're built on, and the corrective shapes the most of all, as the volume-keeping skinning they're
made from would, both stretching the skin hardly more than bone heat itself. The helper joints, cloth bones and
corrective shapes were first built on the smoothed weights: there the helper joints stretched the skin further (to
4.1×), the cloth bones further on most models (3.5-4.1×), and the corrective shapes, though they kept a little more
volume (95-97%), swelled Faceted 800's knees and elbows, spreading far over its few big faces (its edges to 4.6×). All
but the corrective shapes pinch the back of the knee at its deepest bend, as plain skinning does. The tunic's skirt is
short, its hem about 10 cm below the hips, so the cloth bones show most between the legs and as the hem swings. The
tunic and the trousers are one surface in every model, so where the hem swings off the thigh the faces between them fold
and stretch, a few small facets at the back of the hem at the deepest bends (where the cloth bones' edges stretch to
4.3×); easing the cloth bones' share toward the skirt's edge doesn't help, since that's the fold, not a seam in the
weights.

### Clips and the game

```sh
blender -b --factory-startup -P make_runs.py                  # the .blend, game files, side clips, sheets, page
blender -b --factory-startup -P make_runs.py -- --no-render   # without the clips and sheets
blender -b --factory-startup -P make_runs.py -- --export      # only the game's files
blender -b --factory-startup -P make_runs.py -- --side        # only the side clips (and the page)
blender -b --factory-startup -P make_runs.py -- --sheets      # only the contact sheets
blender -b --factory-startup -P make_runs.py -- --page        # only the rating page
blender -b --factory-startup -P make_runs.py -- --side --only=heroic,lope              # only those runs' side clips
blender -b --factory-startup -P make_runs.py -- --export --side --models=Faceted1500 --rigs=heat   # one figure
```

It needs `hero_portfolio.blend` (and its textures in `build/`, so `make_heroes.py` first on a fresh checkout). With
`--models` or `--rigs` it builds only those figures, which is much quicker, and leaves `run_portfolio.blend` as it was.
Each run is filmed from the side on the page's figure, Faceted 1500 on bone heat's rig, alone and large, on a ground
that moves back under it at its speed (`build/runs/side/<run>.mp4`, not kept in git): its cycle rendered once and
repeated to about three seconds, so the moment a browser loses each time it loops a clip back to its start comes
seldom. `previews/runs_<family>.png` show each family's runs at eight moments of their cycles (from the left foot
landing), from the side, on the same figure.

Each model on each rig, with its runs and the stand as animations named after them, goes to
`build/runs/<model>_<rig>.glb`, as the game's models are made, and the runs in order with their names to
`build/runs/runs.json`, for the play demo's run viewer. Each run is also recorded in the play demo itself, the hero as
Faceted 1500 on bone heat's rig running about the open field, starting, turning and stopping, in the game's light, from
the game's camera zoomed in to 10 m, as the player can with the mouse wheel:

```sh
python3 record_runs.py                                          # build/runs/game/<run>.mp4
blender -b --factory-startup -P make_runs.py -- --page          # the page again, with them
```

(`record_runs.py` runs the demo with Godot's `--write-movie` and `runs.gd --tour`, and `movie_to_mp4.py` turns each
recording into an .mp4 in Blender; `--runs=heroic,lope` records only those, `--views=near` from nearer and lower,
`--screen=1` opens the demo's window on that screen.)

To run as them in the play demo yourself:

```sh
python3 game/tools/play.py --script res://scripts/dev/runs.gd -- --run=heroic
```

The hero is the figure, read from its .glb as the game runs: it runs as it moves, the run sped up or slowed to the
hero's speed, and stands when it stops. It stays upright through turns: it used to lean into them, up to 14°, which the
user didn't like (3 November). Q and E step through the fifty runs (going on from the same moment of the stride), 1-5
picks the model, R the rig (Shift+R back; it starts on bone heat, as the rating page does), L all five models in a
slanting line beside the hero, Z slow motion, the whole game at a half or a quarter of its speed (`game/README.md` has
its options for screenshots; `--zoom=10` sets the game's camera's distance; `--headless ... -- --check` reads every .glb
and checks its skeleton, skin and animations, and the corrective rig's shapes).

### The rating page

`build/runs/ratings.html` (made from `run_ratings.html` by `make_runs.py -- --page`) is published, privately to the
user, at https://claude.ai/artifact/Y7LgDQNjNfHqi4Dy1CHBcF, with the clips (`side/` and `game/`). It shows one run at a
time, from the side or in the game (a tap switches; a wide screen shows both), with its name and what it's like, to
rate from 1 (I don't like it) to 10 (I really like it), with a comment if the user likes. Previous and Next stay at the
bottom of the screen (a swipe across the clip does the same; on a keyboard 1-9 and 0 rate and the arrow keys move), All
runs lists every run with its rating to jump to, and the speed buttons slow the clips to a half or a quarter. A rating
is written the moment it's given, a comment once the user pauses typing, leaves the box, changes runs or puts the phone
away, so they can stop anywhere: the page opens again at the first run not rated yet (or the one a link names,
`#heroic`). One that can't be written yet is kept in the browser and sent on the next visit. The clips are fetched
whole and played from memory, as the page's files are served without the byte ranges a video asks for (phones won't
play one without them), the next run's while this one plays.

The ratings are kept in the page's database, collection `ratings`, a document for each run and round named
`r<round>-<run>` (`r1-heroic`): `round`, `run` (its key), `n`, `label`, `rating` (1-10, or null for a comment alone),
`comment` and `at` (when it was given). Read them with the ArtifactData tool (`query` on `ratings`, `round` equal to
the round). Round 1 is the fifty runs as committed in 6e81ace (2 November). The marks from the first gallery are in
`runs`, a document for each run marked (`stance`: want, maybe or avoid, and `note`): the user marked runs 1-15 there
on 11 November, and in round 1 the page shows each mark and offers its note as the run's comment.

For the next round: read the round's ratings and keep a copy here in `ratings/round<N>.json`, make the new runs from
what they say, raise `ROUND` in `make_runs.py` (keeping the new ratings apart from the old), film and record the runs
and rebuild and publish the page. A version of the page holds at most 256 MB, and round 1's clips take about 215 MB
(the game's about 4 MB each), so the next round's game clips must be smaller (cropped round the hero, say) or round
1's let go.

## Left for later

- The run the user picks, with what it needs in the game: a walk for moving while attacking (forward, back and to the
  sides, as the board says), starting and stopping (the viewer only blends between the run and the stand), and the
  feet kept on the ground through sharp turns (the figure turns about its middle, so a planted foot slides a little).
- The model and rig to go with it: the rating page shows every run on Faceted 1500 with bone heat's weights, the rig
  that stretches the skin least; the other models and rigs run them all in the game's files and the run viewer (1-5,
  R).
- The hero portfolio's low-poly figures have more than four bones on some vertices (their weights carried over from
  the 20k model), which the glTF export cuts to the four strongest, as games take them; the run portfolio's rigs
  have four at most.
