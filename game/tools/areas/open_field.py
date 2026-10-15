"""Open field: a very big, gently rolling meadow, a few copses of birch and aspen, lone trees and boulders the ice left,
a faint track across, and the forest only far off at the edges (the low-density references). About 210 m across.

Coordinates are metres, +X east, +Y north, Z up (Blender's axes), as in storskogen.py.
"""
import numpy as np

from areas.common import (ASPEN, BIRCH, PINE, ROWAN, SPECIES, SPRUCE, catmull_closed, catmull_open, fbm,  # noqa: F401
                          paths_and_outline, smoothstep)

TITLE = "Open field"
SEED = 31
BOUNDARY = catmull_closed([(-100, -80), (-60, -100), (0, -104), (60, -98), (100, -70), (108, 0), (98, 70), (50, 102),
                           (-20, 100), (-80, 90), (-106, 30), (-108, -30)], 5)
BAKE = (-125.0, 125.0, -125.0, 125.0)
COLOUR_TEXEL = 0.07  # a wide, even meadow: coarser than the forests' ground
FAR_R = 300.0
START = ((-4.0, -12.0), 80.0)
PATHS = {
    "track": (catmull_open([(-125, -40), (-80, -30), (-40, -12), (0, -9), (40, 4), (80, 20), (125, 30)]), 2.0, "trail"),
}
LONE_TREES = [("ScotsPine", (30, 42)), ("ScotsPine", (-70, -52)), ("ScotsPine", (82, -40)), ("SilverBirch", (-42, 30)),
              ("SilverBirch", (-37, 35)), ("Rowan", (55, -35)), ("Aspen", (70, 52)), ("Aspen", (75, 47)),
              ("SilverBirch", (12, -60)), ("ScotsPine", (-20, 70))]
COPSES = [((-55, 55), 11.0), ((48, 72), 9.0), ((-80, -10), 10.0), ((35, -70), 8.0), ((85, 15), 7.0)]
ERRATICS = [((15, 25), 1.6), ((-30, -40), 1.8), ((60, 10), 1.4), ((-60, 62), 1.5), ((-10, 48), 1.2), ((90, -60), 1.7)]
LANDMARKS = [("Cairn", (20.0, 30.0), 0.0)]
BUSH_OPTIONS = dict(rate=1.0)  # round its copses
path_dist, inside, boundary_dist = paths_and_outline(PATHS, BOUNDARY)


def height(X, Y):
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    h = 4.0 * fbm(X / 110.0, Y / 110.0, 3, 261) + 1.0 * fbm(X / 40.0, Y / 40.0, 2, 262)
    return h - 0.04 * (1 - smoothstep(0.6, 1.4, path_dist(X, Y)))


def copse(X, Y):
    """1 in a copse's middle, fading out at its edge."""
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    c = np.zeros_like(X)
    for (cx, cy), r in COPSES:
        c = np.maximum(c, 1 - smoothstep(0.5 * r, r, np.hypot(X - cx, Y - cy)))
    return c


def density(X, Y):
    return np.clip(0.85 * copse(X, Y) * smoothstep(1.2, 2.6, path_dist(X, Y)), 0, 1)


def far_density(x, y):
    """The forest closes in only far off."""
    return float(smoothstep(150.0, 190.0, np.hypot(x, y)))


def tree_kind(X, Y, roll):
    X = np.asarray(X, dtype=float)
    far = np.hypot(X, np.asarray(Y, dtype=float)) > 140.0
    near = np.where(roll < 0.45, BIRCH, np.where(roll < 0.7, ASPEN, np.where(roll < 0.8, ROWAN, PINE)))
    return np.where(far, np.where(roll < 0.45, SPRUCE, np.where(roll < 0.85, PINE, BIRCH)), near)


def ground_masks(X, Y):
    pathw = np.clip(1 - path_dist(X, Y) / 4.0, 0, 1)
    return dict(pathw=pathw, meadow=np.ones_like(pathw))


def populate(L):
    L.clear += [(START[0], 3.5)] + [(p, 4.5) for _, p in LONE_TREES] + [(p, 2.0 * s + 1.0) for p, s in ERRATICS]
    L.clear += [(p, 2.5) for _, p, _ in LANDMARKS]
    L.forest(cell=3.6, saplings=False)
    L.lone_trees()
    L.far_forest(cell=8.0)
    L.rocks_and_logs(cell=11.0, rates=(0.06, 0.06, 0.06, 0.06, 0.06))  # boulders only, here and there
    L.erratics_and_landmarks()

    def cover(i, x, y, r, pick, G, patch, lingon):  # meadow grass, tall grass in drifts, now and then a shrub
        if patch[i] > 0.3:
            return f"TallGrass{pick % 3}" if r < 0.2 else (f"Grass{pick % 4}" if r < 0.3 else None)
        return f"Grass{pick % 4}" if r < 0.1 else (f"Shrub{pick % 3}" if r < 0.11 else None)

    L.ground_cover(cell=1.3, pick_model=cover)
    L.trail_edges()
