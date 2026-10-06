"""Plays settings for when trees go see-through over the playtests of scripts/dev/veiltune.gd.

For each way of measuring how much of the area round the hero the trees cover ("cards", "seen", "trees2" or "layersN",
for each size of the area; see scripts/dev/veiltune.gd),
and each pair of thresholds (see-through at, solid again below), it runs the game's rule along every walk, as
DemoWorld._cut_veil has it, and reports:

- under trees standing alone: how many walks had the trees go see-through at all, how often they went (on and off is
  the flicker), and the share of the time they were see-through. The aim is none.
- along the trail and at random spots in the forest: where nothing of the hero shows ("hidden": under 15% of it, through
  the gaps between the leaves), the share of the time the trees were see-through, split by how many trees are on the
  line to the hero's middle (two or more: thick forest; one: a single tree); where much of it shows ("shows": over
  40%), the share they needlessly were; and how often they went see-through along the trail.

python3 veiltune.py rows.csv [--top=20]
"""
import csv
import sys
from collections import defaultdict

STEP = 0.2 / 5.5  # seconds between steps: 0.2 m at walking speed
VEIL_HOLD = 0.1  # seconds the trees stay see-through after they no longer cover enough (DemoWorld.VEIL_HOLD)
HIDDEN, SHOWS = 0.15, 0.40


def load(path):
    walks = defaultdict(list)
    with open(path) as fh:
        for row in csv.DictReader(fh):
            walks[(row["scenario"], int(row["walk"]))].append(row)
    return walks


def play(covers, on_at, off_below):
    """Which steps the trees are see-through at, by the game's rule (DemoWorld._cut_veil)."""
    veil_for = float("inf")
    out = []
    for cover in covers:
        veiling = veil_for <= VEIL_HOLD
        veil_for = 0.0 if cover >= (min(off_below, on_at) if veiling else on_at) else veil_for + STEP
        out.append(veil_for <= VEIL_HOLD)
    return out


def score(walks, measure, on_at, off_below):
    alone = dict(walks=0, any=0, goes=0, steps=0, on=0)
    trail = dict(goes=0, steps=0)
    hid = [0, 0]  # see-through, of hidden steps with two trees or more on the line to the hero
    hid1 = [0, 0]  # and with one
    showed = [0, 0]  # see-through, of steps where the hero shows
    for (scenario, _walk), rows in walks.items():
        covers = [float(r[measure]) for r in rows]
        on = play(covers, on_at, off_below) if len(rows) > 1 else [c >= on_at for c in covers]
        goes = sum(1 for k in range(len(on)) if on[k] and (k == 0 or not on[k - 1]))
        if scenario.startswith("alone"):
            alone["walks"] += 1
            alone["any"] += goes > 0
            alone["goes"] += goes
            alone["steps"] += len(on)
            alone["on"] += sum(on)
            continue
        if scenario == "trail":
            trail["goes"] += goes
            trail["steps"] += len(on)
        for r, o in zip(rows, on):
            v = float(r["visible"])
            if v < HIDDEN:
                h = hid if int(r["on_line"]) >= 2 else hid1
                h[1] += 1
                h[0] += o
            elif v > SHOWS:
                showed[1] += 1
                showed[0] += o
    return alone, trail, hid, hid1, showed


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    top = 20
    for a in sys.argv[1:]:
        if a.startswith("--top="):
            top = int(a[6:])
    walks = load(args[0])
    measures = [k for k in next(iter(walks.values()))[0].keys() if k.startswith(("cards_", "seen_", "trees2_", "layers"))]
    results = []
    for m in measures:
        for on_at in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0):
            for off_below in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.72, 0.8, 0.85, 0.9, 0.95, 1.0):
                if off_below > on_at:
                    continue
                results.append((m, on_at, off_below) + score(walks, m, on_at, off_below))
    print("measure      at  below | alone: walks see-through, times, share | hidden, 2+ trees | hidden, 1 tree | shows | trail: times")
    # the user's aim first: nothing under trees alone, then as much as can be where the hero is hidden, then the least
    # needless see-through and flicker
    results.sort(key=lambda r: (r[3]["any"], -r[5][0] / max(r[5][1], 1), r[7][0] / max(r[7][1], 1), r[4]["goes"]))
    for r in results[:top]:
        line(r)
    print("\nnow (cards_0.0, 0.90, 0.72):")
    for r in results:
        if r[0] == "cards_0.0" and r[1] == 0.9 and r[2] == 0.72:
            line(r)


def line(r):
    m, on_at, off_below, alone, trail, hid, hid1, showed = r
    print("%-11s %4.2f %5.2f | %3d of %3d, %4d, %5.1f%% | %5.1f%% of %4d | %5.1f%% of %4d | %5.1f%% of %4d | %3d" % (
        m, on_at, off_below, alone["any"], alone["walks"], alone["goes"], 100.0 * alone["on"] / max(alone["steps"], 1),
        100.0 * hid[0] / max(hid[1], 1), hid[1], 100.0 * hid1[0] / max(hid1[1], 1), hid1[1],
        100.0 * showed[0] / max(showed[1], 1), showed[1], trail["goes"]))


if __name__ == "__main__":
    main()
