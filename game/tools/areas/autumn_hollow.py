"""Autumn hollow: a grove of birch, aspen, rowan and alder in a hollow that sinks a few metres into the ground, its
trees 1-4 m apart and turning yellow, orange and red, the ground in it deep in their fallen leaves (the leaves on the
ground references). The forest round it is still mostly green, spruce and pine, its birches only starting to turn.
About 125 x 100 m to walk. No paths: the user wants it just leaf-filled ground and trees (14 October); in the game the
leaves lie thick in drifts and piles here and there, which stir as the hero walks through them (scripts/leaf_litter.gd).

Coordinates are metres, +X east, +Y north, Z up (Blender's axes), as in storskogen.py.
"""
import numpy as np

from areas.common import (ALDER, ASPEN, BIRCH, PINE, ROWAN, SPECIES, SPRUCE, catmull_closed, catmull_open, fbm,  # noqa: F401
                          paths_and_outline, smoothstep)

TITLE = "Autumn hollow"
SEED = 51
BOUNDARY = catmull_closed([(-60, -42), (-30, -52), (10, -50), (48, -46), (62, -20), (58, 18), (50, 46), (12, 52),
                           (-28, 48), (-58, 36), (-64, 0)], 5)
BAKE = (-80.0, 80.0, -68.0, 68.0)
FAR_R = 230.0
START = ((-18.0, -1.5), 15.0)  # in the grove, on the slope down into the hollow
PATHS = {}  # none (the user, 14 October)
HOLLOW = (4.0, 2.0)  # the hollow's middle
HOLLOW_R = 36.0
HOLLOW_DEPTH = 2.8
LONE_TREES = []
ERRATICS = [((-10, 16), 1.2), ((22, -14), 1.0)]
LANDMARKS = []
path_dist, inside, boundary_dist = paths_and_outline(PATHS, BOUNDARY)
_tints = np.random.default_rng(5101)  # the trees' autumn colours, each its own


def hollow(X, Y):
    """How far the hollow sinks the ground (m, below 0), its outline uneven and lopsided."""
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    d = np.hypot((X - HOLLOW[0]) / 1.15, (Y - HOLLOW[1]) / 0.9) / HOLLOW_R
    d = d + 0.2 * fbm(X / 24.0, Y / 24.0, 2, 511)
    return -HOLLOW_DEPTH * (1 - smoothstep(0.25, 1.0, d))


def grove(X, Y):
    """1 down in the hollow, where the autumn grove stands, 0 up round it."""
    return 1 - smoothstep(-0.6, -0.15, hollow(X, Y))


def height(X, Y):
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    h = 1.2 * fbm(X / 60.0, Y / 60.0, 3, 521) + 0.3 * fbm(X / 14.0, Y / 14.0, 2, 522)
    return h + hollow(X, Y) - 0.05 * (1 - smoothstep(0.6, 1.4, path_dist(X, Y)))


def density(X, Y):
    """The forest round the hollow; the grove's own is grove_density."""
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    d = 0.85 + 0.15 * fbm(X / 40.0, Y / 40.0, 2, 525)
    return np.clip(d * (1 - grove(X, Y)) * smoothstep(1.2, 2.6, path_dist(X, Y)), 0, 1)


def grove_density(X, Y):
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    d = 0.8 + 0.15 * fbm(X / 18.0, Y / 18.0, 2, 526)
    return np.clip(d * grove(X, Y) * smoothstep(1.2, 2.6, path_dist(X, Y)), 0, 1)


def tree_kind(X, Y, roll):
    """Round the hollow: spruce and pine, some birch and aspen."""
    return np.where(roll < 0.14, BIRCH, np.where(roll < 0.19, ASPEN, np.where(roll < 0.6, SPRUCE, PINE)))


def grove_kind(X, Y, roll):
    """In the hollow: birch and aspen, rowan and alder, and now and then a pine."""
    return np.where(roll < 0.36, BIRCH, np.where(roll < 0.66, ASPEN, np.where(roll < 0.8, ROWAN,
                    np.where(roll < 0.93, ALDER, PINE))))


def tint(x, y, kind):
    """Autumn, as (how far turned, which way: 0 yellow, 0.5 orange, 1 red): far on in the hollow, starting round it.
    Birches turn yellow, aspens anything from yellow to red, rowans orange and red; alders hardly turn."""
    u, v = _tints.uniform(0, 1, 2)
    g = float(grove(np.array([x]), np.array([y]))[0])
    if kind == "SilverBirch":
        return (0.35 + 0.5 * u + 0.15 * g if g < 0.5 else 1.0, 0.18 * v)
    if kind == "Aspen":
        return (0.4 + 0.4 * u if g < 0.5 else 1.0, 0.1 + 0.85 * v)
    if kind == "Rowan":
        return (0.85 if g < 0.5 else 1.0, 0.6 + 0.4 * v)
    if kind == "Alder":
        return (0.25 + 0.35 * u * g, 0.15 * v)
    return None


def ground_masks(X, Y):
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    pathw = np.clip(1 - path_dist(X, Y) / 4.0, 0, 1)
    g = grove(X, Y)
    patches = smoothstep(0.0, 0.35, fbm(X / 9.0, Y / 9.0, 2, 531))
    litter = np.maximum(smoothstep(0.1, 0.6, g + 0.25 * fbm(X / 6.0, Y / 6.0, 2, 532)), 0.45 * patches)
    moss = 0.7 * smoothstep(-0.1, 0.4, fbm(X / 14.0, Y / 14.0, 2, 533)) * (1 - litter)
    return dict(pathw=pathw, meadow=np.zeros_like(X), moss=moss * (1 - smoothstep(0.0, 0.5, pathw)), litter=litter)


def populate(L):
    L.clear += [(START[0], 3.5)] + [(p, 2.0 * s + 1.0) for p, s in ERRATICS]
    L.forest(cell=2.7, saplings=False, size=(0.8, 1.1), tint=tint, density=grove_density, kind=grove_kind)
    L.forest(cell=3.5, tint=tint)
    L.far_forest(tint=lambda x, y, kind: (0.4, 0.1) if kind == "SilverBirch" else None)
    L.rocks_and_logs(cell=7.0, rates=(0.07, 0.09, 0.12, 0.17, 0.185))
    L.erratics_and_landmarks()

    def cover(i, x, y, r, pick, G, patch, lingon):
        if G["litter"][i] > 0.6:  # in the hollow: only the leaves (the user: leaf-filled ground and trees, 14 October),
            return None  # which the game heaps up in piles of its own (scripts/leaf_litter.gd)
        if patch[i] > 0.25:
            return (f"Blueberry{pick % 3}" if r < 0.14 else f"Shrub{pick % 3}") if r < 0.4 else None
        if fbm(np.array([x / 8.0]), np.array([y / 8.0]), 2, 77)[0] > 0.3:
            return f"Fern{pick % 3}" if r < 0.25 else None
        if lingon[i] and r < 0.25:
            return f"Lingonberry{pick % 3}"
        return [f"Shrub{pick % 3}", f"Lichen{pick % 3}", f"MossMound{pick % 3}"][pick % 3] if r < 0.1 else None

    L.ground_cover(pick_model=cover)
    L.trail_edges()
