"""Open forest: the forest as most of the game will be, as the user wants it for an ARPG: the trees stand apart, one or
two on the screen at a time from the camera's usual height (one about every 14 m), so that they never crowd the view;
the thick forest only beyond the edges, round the walkable area. Between the trees: moss, blueberries, heather,
rocks, logs and a glade, low rises and hollows, and trails across. About 125 x 100 m to walk.

Coordinates are metres, +X east, +Y north, Z up (Blender's axes), as in storskogen.py.
"""
import numpy as np

from areas.common import (ASPEN, BIRCH, PINE, ROWAN, SPECIES, SPRUCE, catmull_closed, catmull_open, fbm,  # noqa: F401
                          paths_and_outline, smoothstep)

TITLE = "Open forest"
SEED = 91
BOUNDARY = catmull_closed([(-60, -42), (-30, -52), (10, -50), (48, -46), (62, -20), (58, 18), (50, 46), (12, 52),
                           (-28, 48), (-58, 36), (-64, 0)], 5)
BAKE = (-80.0, 80.0, -68.0, 68.0)
FAR_R = 230.0
SPACING = 14.0  # metres between the trees in the walkable area, about: one or two on the screen
START = ((-40.0, -6.0), 10.0)
PATHS = {
    "trail": (catmull_open([(-80, -10), (-58, -8), (-40, -6), (-22, -10), (-6, -4), (10, -6), (26, 2), (42, 0), (58, 6),
                            (80, 4)]), 2.0, "trail"),
    "north": (catmull_open([(-6, -4), (-2, 12), (-8, 28), (-4, 44), (2, 68)]), 1.6, "trail"),
    "south": (catmull_open([(26, 2), (30, -14), (24, -30), (30, -48), (34, -68)]), 1.6, "trail"),
}
GLADE = ((26.0, 22.0), 13.0)  # an open glade, grass and heather
RISES = [((-30, 22), 14.0, 2.4), ((40, -26), 12.0, 1.8), ((-24, -34), 10.0, -1.4)]  # centre, radius, height (- a hollow)
LONE_TREES = []
ERRATICS = [((-16, 14), 1.4), ((12, -24), 1.2), ((44, 30), 1.5)]
LANDMARKS = []
path_dist, inside, boundary_dist = paths_and_outline(PATHS, BOUNDARY)


def height(X, Y):
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    h = 1.4 * fbm(X / 60.0, Y / 60.0, 3, 911) + 0.3 * fbm(X / 12.0, Y / 12.0, 2, 912)
    for (cx, cy), r, kh in RISES:
        d = np.hypot((X - cx) / 1.1, (Y - cy) / 0.9) / r + 0.2 * fbm(X / 10.0, Y / 10.0, 2, 913)
        h = h + kh * (1 - smoothstep(0.2, 1.0, d))
    return h - 0.05 * (1 - smoothstep(0.6, 1.4, path_dist(X, Y)))


def glade(X, Y):
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    d = np.hypot(X - GLADE[0][0], Y - GLADE[0][1]) / GLADE[1] + 0.25 * fbm(X / 8.0, Y / 8.0, 2, 914)
    return 1 - smoothstep(0.7, 1.0, d)


def density(X, Y):
    """The trees standing apart in the walkable area (forest's cell is SPACING); the edges' thick forest is
    edge_density's."""
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    d = 0.85 * smoothstep(2.0, 6.0, boundary_dist(X, Y)) * (1 - glade(X, Y))
    return np.clip(d * smoothstep(1.2, 2.6, path_dist(X, Y)), 0, 1)


def edge_density(X, Y):
    """Thick forest beyond the walkable area's edge, where it closes in."""
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    return np.clip(0.9 * smoothstep(0.0, 4.0, -boundary_dist(X, Y)) * smoothstep(1.2, 2.6, path_dist(X, Y)), 0, 1)


def tree_kind(X, Y, roll):
    return np.where(roll < 0.4, PINE, np.where(roll < 0.68, SPRUCE, np.where(roll < 0.88, BIRCH,
                    np.where(roll < 0.94, ASPEN, ROWAN))))


def ground_masks(X, Y):
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    pathw = np.clip(1 - path_dist(X, Y) / 4.0, 0, 1)
    off_path = 1 - smoothstep(0.0, 0.5, pathw)
    g = glade(X, Y)
    meadow = np.clip(g + 0.6 * smoothstep(0.25, 0.5, fbm(X / 16.0, Y / 16.0, 2, 921)), 0, 1)
    heath = smoothstep(0.2, 0.45, fbm(X / 14.0, Y / 14.0, 2, 922)) * (1 - meadow) * 0.8
    moss = 0.7 * smoothstep(-0.2, 0.3, fbm(X / 12.0, Y / 12.0, 2, 923)) * (1 - meadow) * (1 - heath)
    return dict(pathw=pathw, meadow=meadow * off_path, heath=heath * off_path, moss=moss * off_path)


def populate(L):
    L.clear += [(START[0], 3.5)] + [(p, 2.0 * s + 1.0) for p, s in ERRATICS]
    L.forest(cell=SPACING, saplings=False, keep_off=2.0)
    L.forest(cell=3.4, density=edge_density)
    L.far_forest()
    L.rocks_and_logs(cell=8.0, rates=(0.1, 0.13, 0.16, 0.21, 0.23))
    L.erratics_and_landmarks()

    def cover(i, x, y, r, pick, G, patch, lingon):
        if G["meadow"][i] > 0.5:
            return f"Grass{pick % 4}" if r < 0.14 else (f"TallGrass{pick % 3}" if r < 0.17 else (f"Shrub{pick % 3}" if r < 0.19 else None))
        if G["heath"][i] > 0.5:
            return f"Heather{pick % 3}" if r < 0.35 else (f"Lingonberry{pick % 3}" if r < 0.45 else None)
        if patch[i] > 0.25:
            return (f"Blueberry{pick % 3}" if r < 0.14 else f"Shrub{pick % 3}") if r < 0.4 else None
        if fbm(np.array([x / 9.0]), np.array([y / 9.0]), 2, 79)[0] > 0.35:
            return f"Fern{pick % 3}" if r < 0.25 else None
        if lingon[i] and r < 0.25:
            return f"Lingonberry{pick % 3}"
        return [f"Shrub{pick % 3}", f"Lichen{pick % 3}", f"MossMound{pick % 3}", f"Grass{pick % 4}"][pick % 4] if r < 0.12 else None

    L.ground_cover(pick_model=cover)
    L.trail_edges()
