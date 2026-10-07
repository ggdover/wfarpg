"""Forest lake: a still, dark lake in the forest, birches and alders leaning over it, reeds along its shores, water
lilies in a bay and a wooden jetty out into it; a small island with a few pines (the lake references). A path goes
round it. The water is drawn with reflections (the forest_lake scene). About 125 x 100 m to walk; the hero can wade
in along the shore, but walls keep it out of the deep water.

Coordinates are metres, +X east, +Y north, Z up (Blender's axes), as in storskogen.py.
"""
import math

import numpy as np

from areas.common import (ALDER, ASPEN, BIRCH, PINE, ROWAN, SPECIES, SPRUCE, catmull_closed, catmull_open, fbm,  # noqa: F401
                          in_poly, paths_and_outline, seg_dist, smoothstep)

TITLE = "Forest lake"
SEED = 71
BOUNDARY = catmull_closed([(-60, -42), (-30, -50), (10, -48), (48, -44), (62, -20), (60, 18), (52, 46), (14, 54),
                           (-28, 52), (-58, 38), (-64, 0)], 5)
BAKE = (-80.0, 80.0, -68.0, 72.0)
FAR_R = 230.0
LEVEL = 0.0  # the lake's surface
LAKE = catmull_closed([(-30, 2), (-18, -6), (0, -8), (14, -5), (24, -9), (35, -6), (38, 6), (29, 15), (31, 29), (15, 38),
                       (-6, 37), (-24, 31), (-34, 18)], 6)
BAY = ((30.0, 0.0), 9.0)  # shallow, with the water lilies
ISLAND = ((8.0, 22.0), 5.0)
WADE = 3.4  # how far in from the shore the walls keep the hero: where the water is about 0.55 m deep
JETTY = ((0.0, -9.8), (0.0, 0.5))
START = ((0.0, -12.5), 90.0)  # in the meadow by the jetty, the lake ahead
PATHS = {
    "shore": (catmull_closed([(-36, -14), (-20, -15), (-6, -15), (6, -14), (18, -14), (32, -17), (44, -8), (46, 8),
                              (40, 24), (38, 38), (24, 45), (4, 45), (-16, 44), (-34, 38), (-42, 24), (-44, 8), (-42, -6)], 5),
              2.0, "trail"),
    "west": (catmull_open([(-80, -6), (-64, -9), (-50, -11), (-40, -10), (-38, -12)]), 2.0, "trail"),
    "jetty": (catmull_open([(0.0, -14.5), (0.0, -11.5), JETTY[0]]), 1.6, "trail"),
    "east": (catmull_open([(46, 2), (60, 4), (80, 0)]), 1.8, "trail"),
}
LONE_TREES = []
ERRATICS = [((-28, -24), 1.4), ((40, -30), 1.2), ((-50, 30), 1.3)]
LANDMARKS = []
path_dist, inside, boundary_dist = paths_and_outline(PATHS, BOUNDARY)


def into_lake(X, Y):
    """Metres in from the lake's shore line (below 0 on land)."""
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    d = seg_dist(X, Y, LAKE + LAKE[:1])
    return np.where(in_poly(X, Y, LAKE), d, -d)


def height(X, Y):
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    t = into_lake(X, Y)
    bay = 1 - smoothstep(0.5 * BAY[1], BAY[1], np.hypot(X - BAY[0][0], Y - BAY[0][1]))
    deep = 2.2 * (1 - 0.75 * bay)
    g = 0.45 - 0.55 * smoothstep(-3.0, 1.5, t) - deep * smoothstep(0.5, 10.0, t)
    rolling = 1.4 * fbm(X / 60.0, Y / 60.0, 3, 711) + 0.25 * fbm(X / 9.0, Y / 9.0, 2, 712)
    g = g + np.maximum(rolling + 0.6, 0.0) * smoothstep(-2.0, -14.0, t)
    isl = np.hypot(X - ISLAND[0][0], Y - ISLAND[0][1]) / ISLAND[1] + 0.2 * fbm(X / 3.0, Y / 3.0, 2, 713)
    g = np.maximum(g, 0.7 - 3.5 * smoothstep(0.3, 1.4, isl))  # the island, sloping down below the lake's deepest
    return g - 0.05 * (1 - smoothstep(0.6, 1.4, path_dist(X, Y)))


def water_level(X, Y):
    return np.where(into_lake(X, Y) > -3.0, LEVEL, -100.0)


def offset_outline(pts, d, step=0.5):
    """A closed outline moved d metres inwards (it runs anticlockwise or clockwise; inwards is towards the inside),
    resampled every step metres."""
    p = np.asarray(pts, dtype=float)
    q = np.roll(p, -1, 0) - np.roll(p, 1, 0)
    n = np.stack([-q[:, 1], q[:, 0]], 1) / np.hypot(q[:, 0], q[:, 1])[:, None]
    probe = p + n * 0.5
    sign = np.where(in_poly(probe[:, 0], probe[:, 1], pts), 1.0, -1.0)
    moved = p + n * sign[:, None] * d
    closed = np.vstack([moved, moved[:1]])
    seg = np.hypot(*np.diff(closed, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    u = np.arange(0, s[-1], step)
    return np.stack([np.interp(u, s, closed[:, 0]), np.interp(u, s, closed[:, 1])], 1)


def walls():
    """The wall round the deep water, as one line, open where the jetty crosses it (the jetty has its own)."""
    ring = offset_outline(LAKE, WADE)
    (jx, _y0), (_x1, _y1) = JETTY
    gap = (np.abs(ring[:, 0] - jx) < 0.95) & (ring[:, 1] < 0)
    k = int(np.argmax(gap))
    ring = np.roll(ring, -k, 0)
    gap = np.roll(gap, -k)
    ring = ring[~gap]
    return [[[round(float(x), 2), round(float(-y), 2)] for x, y in ring]]


def density(X, Y):
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    t = into_lake(X, Y)
    d = 0.7 + 0.2 * fbm(X / 30.0, Y / 30.0, 2, 721)
    clearing = 1 - smoothstep(6.0, 11.0, np.hypot(X - 2.0, Y + 16.0))  # the meadow by the jetty
    return np.clip(d * smoothstep(-0.3, -1.6, t) * (1 - clearing) * smoothstep(1.2, 2.6, path_dist(X, Y)), 0, 1)


def tree_kind(X, Y, roll):
    t = into_lake(X, Y)
    shore = t > -9.0
    near = np.where(roll < 0.35, BIRCH, np.where(roll < 0.6, ALDER, np.where(roll < 0.72, ASPEN, np.where(roll < 0.85, SPRUCE, PINE))))
    back = np.where(roll < 0.3, BIRCH, np.where(roll < 0.38, ASPEN, np.where(roll < 0.68, SPRUCE, PINE)))
    return np.where(shore, near, back)


def ground_masks(X, Y):
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    h = height(X, Y)
    pathw = np.clip(1 - path_dist(X, Y) / 4.0, 0, 1)
    off_path = 1 - smoothstep(0.0, 0.5, pathw)
    bed = smoothstep(0.02, -0.2, h - LEVEL)  # under the water
    shore = (1 - smoothstep(0.25, 0.5 + 0.25 * fbm(X / 6.0, Y / 6.0, 2, 731), h - LEVEL)) * (1 - bed)  # grass by the water
    meadow = 1 - smoothstep(7.0, 12.0, np.hypot(X - 2.0, Y + 16.0) + 3.0 * fbm(X / 8.0, Y / 8.0, 2, 732))
    moss = 0.6 * smoothstep(-0.1, 0.4, fbm(X / 14.0, Y / 14.0, 2, 733)) * (1 - meadow) * (1 - shore) * (1 - bed)
    return dict(pathw=pathw, meadow=meadow * (1 - bed) * (1 - shore), bed=bed, shore=shore * off_path, moss=moss * off_path)


def populate(L):
    rng = L.rng
    L.clear += [(START[0], 3.5)] + [(p, 2.0 * s + 1.0) for p, s in ERRATICS]
    L.extras["walls"] = walls()
    # the island's pines, and a birch
    for k, (dx, dy) in enumerate([(-1.5, 0.5), (1.6, 1.4), (0.3, -1.8)]):
        x, y = ISLAND[0][0] + dx, ISLAND[0][1] + dy
        L.add_tree("SilverBirch" if k == 2 else "ScotsPine", x, y, rng.uniform(0.85, 1.05), rng.uniform(0, math.tau), "near")
        L.clear.append(((x, y), 1.5))
    L.forest(cell=3.6, saplings=False)
    L.far_forest()
    L.rocks_and_logs(cell=8.0, rates=(0.1, 0.13, 0.17, 0.21, 0.22))
    L.erratics_and_landmarks()
    # boulders along the shore, some in the shallows
    X, Y = np.meshgrid(np.arange(-40.0, 44.0, 3.0), np.arange(-14.0, 44.0, 3.0))
    X, Y = (X + rng.uniform(0, 3.0, X.shape)).ravel(), (Y + rng.uniform(0, 3.0, Y.shape)).ravel()
    t = into_lake(X, Y)
    for x, y, t_ in zip(X, Y, t):
        if -2.0 < t_ < 2.5 and rng.uniform() < 0.12 and path_dist(np.array([x]), np.array([y]))[0] > 1.6 \
                and not L.blocked(x, y, 1.0) and abs(x - JETTY[0][0]) > 3.0:
            m = f"{'Moss' if rng.uniform() < 0.4 else ''}Boulder{int(rng.integers(4))}"
            L.add_prop(m, x, y, rng.uniform(0, math.tau), rng.uniform(0.5, 1.1), sink=0.2)

    def cover(i, x, y, r, pick, G, patch, lingon):
        t_ = float(into_lake(np.array([x]), np.array([y]))[0])
        if t_ > -0.6:  # in the water: reeds along the shore, water lilies further out, most of them in the bay
            if abs(x - JETTY[0][0]) < 2.5 and y < 2.0:
                return None
            reeds = fbm(np.array([x / 12.0]), np.array([y / 12.0]), 2, 741)[0] > 0.05
            if t_ < 1.8 and reeds:
                return f"Reed{pick % 3}" if r < 0.55 else None
            bay = math.hypot(x - BAY[0][0], y - BAY[0][1]) < BAY[1]
            if 1.5 < t_ and (bay and r < 0.4 or r < 0.025):
                return f"LilyPad{pick % 3}"
            return None
        if t_ > -2.5:
            return f"Sedge{pick % 3}" if r < 0.2 else (f"TallGrass{pick % 3}" if r < 0.3 else None)
        if G["meadow"][i] > 0.5:
            return f"Grass{pick % 4}" if r < 0.15 else (f"TallGrass{pick % 3}" if r < 0.2 else None)
        if patch[i] > 0.25:
            return (f"Blueberry{pick % 3}" if r < 0.14 else f"Fern{pick % 3}") if r < 0.38 else None
        if lingon[i] and r < 0.22:
            return f"Lingonberry{pick % 3}"
        return [f"Shrub{pick % 3}", f"MossMound{pick % 3}", f"Grass{pick % 4}"][pick % 3] if r < 0.1 else None

    def place(i, x, y, m):
        if m.startswith("LilyPad"):
            L.add_prop(m, x, y, rng.uniform(0, math.tau), rng.uniform(0.8, 1.3), sink=0.0, z=LEVEL + 0.012)
            return True
        return False

    L.ground_cover(pick_model=cover, place=place)
    L.trail_edges()


def build_extras(E):
    E.water("Lake", (-42.0, 42.0, -16.0, 44.0), water_level, step=1.0)
    E.jetty("Jetty", JETTY[0], JETTY[1], width=1.6, deck=0.4, level=LEVEL)
