"""Bog: an open wetland in the forest, golden tussocks of last year's sedge between dark pools, stunted pines and
birches, grey snags, birches all round its edge (the wetland reference, vatmark). A boardwalk of split logs (a
spang) crosses it; the pools are shallow enough to wade. About 125 x 100 m to walk.

Coordinates are metres, +X east, +Y north, Z up (Blender's axes), as in storskogen.py.
"""
import math

import numpy as np

from areas.common import (ALDER, ASPEN, BIRCH, PINE, ROWAN, SPECIES, SPRUCE, catmull_closed, catmull_open, fbm,  # noqa: F401
                          in_poly, paths_and_outline, seg_dist, smoothstep)

TITLE = "Bog"
SEED = 81
BOUNDARY = catmull_closed([(-60, -42), (-30, -50), (10, -48), (48, -44), (62, -20), (60, 18), (52, 44), (14, 50),
                           (-28, 48), (-58, 36), (-64, 0)], 5)
BAKE = (-80.0, 80.0, -68.0, 68.0)
FAR_R = 230.0
LEVEL = -0.12  # the pools' surface
BOG = catmull_closed([(-44, -8), (-30, -22), (-8, -26), (14, -20), (34, -24), (46, -10), (44, 10), (30, 24), (6, 28),
                      (-16, 22), (-36, 18), (-48, 6)], 6)
WALK = catmull_open([(-50, -2), (-40, -3), (-30, -1), (-20, -4), (-10, -2), (0, 1), (10, -2), (20, 0), (30, -3), (40, -1),
                     (50, 0)], 3)  # the boardwalk, from firm ground to firm ground
START = ((-22.0, -6.5), 30.0)  # out on the bog by the boardwalk, on a dry hummock, pools ahead
PATHS = {
    "west": (catmull_open([(-80, -8), (-68, -6), (-58, -4), (-50, -2)]), 1.8, "trail"),
    "east": (catmull_open([(50, 0), (58, 4), (66, 2), (80, 6)]), 1.8, "trail"),
    "edge": (catmull_open([(-58, -4), (-54, -16), (-44, -28), (-28, -34), (-8, -36), (14, -32), (34, -34), (50, -24),
                           (56, -10), (52, 0)]), 1.6, "trail"),
}
LONE_TREES = []
ERRATICS = [((-52, 20), 1.3), ((54, 24), 1.2), ((10, -40), 1.4)]
LANDMARKS = []
path_dist, inside, boundary_dist = paths_and_outline(PATHS, BOUNDARY)


def into_bog(X, Y):
    """Metres in from the bog's edge (below 0 on firm ground)."""
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    X2 = X + 3.0 * fbm(X / 15.0, Y / 15.0, 2, 801)  # its edge wanders
    d = seg_dist(X2, Y, BOG + BOG[:1])
    return np.where(in_poly(X2, Y, BOG), d, -d)


def pools(X, Y):
    """0..1: the pools, irregular and many, more towards the bog's middle."""
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    n = fbm(X / 10.0, Y / 10.0, 3, 811) + 0.35 * fbm(X / 4.0, Y / 4.0, 2, 812)
    wet = smoothstep(1.0, 9.0, into_bog(X, Y))
    return smoothstep(0.08, 0.2, n * wet + 0.12 * wet - 0.12)


def height(X, Y):
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    t = into_bog(X, Y)
    rise = np.maximum(1.4 * fbm(X / 50.0, Y / 50.0, 3, 821) + 0.9, 0.2) * smoothstep(0.0, -16.0, t)  # firm ground round it
    lumps = 0.12 * fbm(X / 2.5, Y / 2.5, 2, 822) * smoothstep(-2.0, 2.0, t)  # the bog's hummocks
    g = rise + lumps - 0.38 * pools(X, Y)
    return g - 0.04 * (1 - smoothstep(0.6, 1.4, path_dist(X, Y)))


def water_level(X, Y):
    return np.where(into_bog(X, Y) > 0.0, LEVEL, -100.0)


def density(X, Y):
    """Thick birch and pine round the bog; out on it, only a stunted tree here and there (bog_trees)."""
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    t = into_bog(X, Y)
    d = 0.78 + 0.2 * fbm(X / 30.0, Y / 30.0, 2, 831)
    return np.clip(d * smoothstep(1.0, -3.0, t) * smoothstep(1.2, 2.6, path_dist(X, Y)), 0, 1)


def tree_kind(X, Y, roll):
    t = into_bog(X, Y)
    edge = t > -14.0
    near = np.where(roll < 0.55, BIRCH, np.where(roll < 0.85, PINE, np.where(roll < 0.93, SPRUCE, ALDER)))
    back = np.where(roll < 0.3, BIRCH, np.where(roll < 0.65, PINE, SPRUCE))
    return np.where(edge, near, back)


def ground_masks(X, Y):
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    t = into_bog(X, Y)
    pathw = np.clip(1 - path_dist(X, Y) / 4.0, 0, 1)
    off_path = 1 - smoothstep(0.0, 0.5, pathw)
    on_bog = smoothstep(-2.5 - 2.0 * fbm(X / 7.0, Y / 7.0, 2, 841), 1.5, t)
    pool = pools(X, Y)
    bog = np.clip(0.55 * on_bog * smoothstep(0.0, 0.4, fbm(X / 5.0, Y / 5.0, 2, 842)) + pool, 0, 1)
    sedge = on_bog * (1 - pool)
    moss = 0.65 * smoothstep(-0.2, 0.3, fbm(X / 12.0, Y / 12.0, 2, 843)) * (1 - on_bog)
    return dict(pathw=pathw, meadow=np.zeros_like(X), bog=bog * off_path, sedge=sedge * off_path, moss=moss * off_path,
                bed=smoothstep(0.4, 0.8, pool))


def populate(L):
    rng = L.rng
    L.clear += [(START[0], 3.5)] + [(p, 2.0 * s + 1.0) for p, s in ERRATICS]
    walk = np.asarray(WALK)
    for a, b in zip(walk, walk[1:]):  # nothing on the boardwalk
        for f in np.linspace(0, 1, 6):
            L.clear.append(((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f), 1.1))
    L.forest(cell=3.4, saplings=True)
    L.far_forest()
    # out on the bog: stunted pines and birches, and grey snags, here and there
    X, Y = np.meshgrid(np.arange(-50.0, 50.0, 6.0), np.arange(-30.0, 30.0, 6.0))
    X, Y = (X + rng.uniform(0, 6.0, X.shape)).ravel(), (Y + rng.uniform(0, 6.0, Y.shape)).ravel()
    t, pool = into_bog(X, Y), pools(X, Y)
    for x, y, t_, p in zip(X, Y, t, pool):
        if t_ < 1.0 or p > 0.2 or L.blocked(x, y, 1.5):
            continue
        r = rng.uniform()
        if r < 0.2:
            kind = "ScotsPine" if rng.uniform() < 0.65 else "SilverBirch"
            L.add_tree(kind, x, y, rng.uniform(0.38, 0.62), rng.uniform(0, math.tau), "near")
            L.clear.append(((x, y), 1.2))
        elif r < 0.26:
            m = f"Snag{int(rng.integers(3))}"
            L.add_prop(m, x, y, rng.uniform(0, math.tau), rng.uniform(0.6, 0.9), solid=0.3)
    L.rocks_and_logs(cell=9.0, rates=(0.08, 0.1, 0.16, 0.2, 0.22))
    L.erratics_and_landmarks()

    def cover(i, x, y, r, pick, G, patch, lingon):
        if G["bed"][i] > 0.5:  # in a pool: now and then a tuft of sedge standing in the water
            return f"Sedge{pick % 3}" if r < 0.05 else None
        if G["sedge"][i] > 0.5:
            return f"Tussock{pick % 3}" if r < 0.38 else (f"Sedge{pick % 3}" if r < 0.62 else None)
        if G["sedge"][i] > 0.15:
            return f"Sedge{pick % 3}" if r < 0.3 else (f"Heather{pick % 3}" if r < 0.4 else None)
        if patch[i] > 0.25:
            return (f"Blueberry{pick % 3}" if r < 0.14 else f"Shrub{pick % 3}") if r < 0.4 else None
        if lingon[i] and r < 0.25:
            return f"Lingonberry{pick % 3}"
        return [f"Shrub{pick % 3}", f"MossMound{pick % 3}", f"Grass{pick % 4}"][pick % 3] if r < 0.1 else None

    L.ground_cover(pick_model=cover)
    L.trail_edges()


def build_extras(E):
    E.water("Pool", (-56.0, 54.0, -34.0, 34.0), water_level, step=0.5)
    E.boardwalk("Spang", WALK, width=0.9, lift=0.14, level=lambda x, y: LEVEL)
