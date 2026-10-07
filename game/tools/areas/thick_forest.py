"""Thick forest: dense spruce and pine all round, with one winding path cleared through it, as where the first demo
starts (Tätskogen). About 125 x 100 m to walk; young spruces fill the gaps, and moss, blueberries and ferns the floor.

Coordinates are metres, +X east, +Y north, Z up (Blender's axes), as in storskogen.py.
"""
import numpy as np

from areas.common import (BIRCH, PINE, ROWAN, SPECIES, SPRUCE, catmull_closed, catmull_open, fbm,  # noqa: F401
                          paths_and_outline, smoothstep)

TITLE = "Thick forest"
SEED = 21
BOUNDARY = catmull_closed([(-60, -42), (-30, -52), (10, -50), (48, -46), (62, -20), (58, 18), (50, 46), (12, 52),
                           (-28, 48), (-58, 36), (-64, 0)], 5)
BAKE = (-80.0, 80.0, -68.0, 68.0)
FAR_R = 230.0
START = ((-52.0, -5.5), 15.0)
PATHS = {
    "path": (catmull_open([(-80, -10), (-60, -6), (-46, 2), (-34, 0), (-22, -8), (-8, -6), (4, 4), (18, 8), (30, 0),
                           (42, -6), (56, 0), (80, 6)]), 2.2, "trail"),
}
LONE_TREES = []
ERRATICS = [((-14, 18), 1.3), ((26, -24), 1.5), ((40, 22), 1.2)]
LANDMARKS = []
path_dist, inside, boundary_dist = paths_and_outline(PATHS, BOUNDARY)


def height(X, Y):
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    h = 1.8 * fbm(X / 70.0, Y / 70.0, 3, 161) + 0.5 * fbm(X / 22.0, Y / 22.0, 2, 162)
    return h - 0.05 * (1 - smoothstep(0.6, 1.4, path_dist(X, Y)))


def density(X, Y):
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    d = 0.9 + 0.15 * fbm(X / 40.0, Y / 40.0, 2, 165)
    return np.clip(d * smoothstep(1.2, 2.6, path_dist(X, Y)), 0, 1)


def tree_kind(X, Y, roll):
    """Mostly spruce, thicker in patches, with pine; a birch or a rowan here and there."""
    n = fbm(np.asarray(X, dtype=float) / 26.0, np.asarray(Y, dtype=float) / 26.0, 2, 131)
    p_birch = np.where(n < -0.3, 0.12, 0.05)
    p_spruce = np.where(n > 0.2, 0.75, 0.55)
    return np.where(roll < p_birch, BIRCH, np.where(roll < p_birch + 0.02, ROWAN,
                    np.where(roll < p_birch + 0.02 + p_spruce * (1 - p_birch), SPRUCE, PINE)))


def ground_masks(X, Y):
    pathw = np.clip(1 - path_dist(X, Y) / 4.0, 0, 1)
    moss = 0.75 * smoothstep(-0.1, 0.4, fbm(np.asarray(X, dtype=float) / 14.0, np.asarray(Y, dtype=float) / 14.0, 2, 171))
    return dict(pathw=pathw, meadow=np.zeros_like(pathw), moss=moss * (1 - smoothstep(0.0, 0.5, pathw)))


def populate(L):
    L.clear += [(START[0], 3.5)] + [(p, 2.0 * s + 1.0) for p, s in ERRATICS]
    L.forest(cell=3.4)
    L.far_forest()
    L.rocks_and_logs(rates=(0.1, 0.13, 0.21, 0.24, 0.255))
    L.erratics_and_landmarks()

    def cover(i, x, y, r, pick, G, patch, lingon):  # blueberries, ferns where it's damp, moss cushions
        if patch[i] > 0.25:
            return (f"Blueberry{pick % 3}" if r < 0.14 else f"Shrub{pick % 3}") if r < 0.4 else None
        if fbm(np.array([x / 8.0]), np.array([y / 8.0]), 2, 77)[0] > 0.3:
            return f"Fern{pick % 3}" if r < 0.3 else None
        if lingon[i] and r < 0.25:
            return f"Lingonberry{pick % 3}"
        if G["moss"][i] > 0.5 and r < 0.05:
            return f"MossMound{pick % 3}"
        return [f"Shrub{pick % 3}", f"Lichen{pick % 3}", f"Grass{pick % 4}"][pick % 3] if r < 0.1 else None

    L.ground_cover(pick_model=cover)
    L.trail_edges()
