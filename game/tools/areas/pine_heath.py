"""Pine heath: tall pines standing apart over a thick, lumpy carpet of moss, heather and blueberries, and low rocky
knolls of bare granite slabs (hällmark) with lichen (the mid-density references). About 125 x 100 m to walk; the
sunbeams scene shows it in a low morning sun through mist.

Coordinates are metres, +X east, +Y north, Z up (Blender's axes), as in storskogen.py.
"""
import numpy as np

from areas.common import (BIRCH, PINE, ROWAN, SPECIES, SPRUCE, catmull_closed, catmull_open, fbm,  # noqa: F401
                          paths_and_outline, smoothstep)

TITLE = "Pine heath"
SEED = 41
BOUNDARY = catmull_closed([(-62, -40), (-28, -52), (14, -50), (50, -44), (64, -12), (60, 24), (44, 48), (6, 52),
                           (-34, 48), (-60, 30), (-66, -6)], 5)
BAKE = (-80.0, 80.0, -68.0, 68.0)
FAR_R = 230.0
START = ((-46.0, -24.0), 35.0)
PATHS = {
    "path": (catmull_open([(-80, -36), (-56, -28), (-38, -18), (-20, -16), (-4, -6), (10, 2), (24, 0), (40, 10), (54, 22),
                           (80, 30)]), 2.0, "trail"),
}
KNOLLS = [((-18, 22), 13.0, 2.6), ((28, -26), 11.0, 2.0), ((40, 30), 9.0, 1.8), ((-46, 8), 8.0, 1.5)]  # centre, radius, height
LONE_TREES = []
ERRATICS = [((4, 30), 1.4), ((-30, -36), 1.3)]
LANDMARKS = []
path_dist, inside, boundary_dist = paths_and_outline(PATHS, BOUNDARY)


def knoll(X, Y):
    """How high the rocky knolls lift the ground (m), and 0..1 for how near their bare tops a point is."""
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    h = np.zeros_like(X)
    top = np.zeros_like(X)
    for (cx, cy), r, kh in KNOLLS:
        d = np.hypot(X - cx, Y - cy) / r + 0.25 * fbm(X / 9.0, Y / 9.0, 2, 401)
        h = np.maximum(h, kh * (1 - smoothstep(0.2, 1.0, d)))
        top = np.maximum(top, 1 - smoothstep(0.35, 0.75, d))
    return h, top


def height(X, Y):
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    h = 1.4 * fbm(X / 60.0, Y / 60.0, 3, 461) + 0.35 * fbm(X / 8.0, Y / 8.0, 2, 462)  # the moss's lumps, a little
    return h + knoll(X, Y)[0] - 0.05 * (1 - smoothstep(0.6, 1.4, path_dist(X, Y)))


def density(X, Y):
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    d = 0.42 + 0.2 * fbm(X / 35.0, Y / 35.0, 2, 465)
    d *= 1 - 0.7 * knoll(X, Y)[1]  # few trees on the bare rock
    return np.clip(d * smoothstep(1.2, 2.6, path_dist(X, Y)), 0, 1)


def tree_kind(X, Y, roll):
    return np.where(roll < 0.12, BIRCH, np.where(roll < 0.15, ROWAN, np.where(roll < 0.21, SPRUCE, PINE)))


def ground_masks(X, Y):
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    pathw = np.clip(1 - path_dist(X, Y) / 4.0, 0, 1)
    rock = knoll(X, Y)[1]
    heath = smoothstep(0.15, 0.45, fbm(X / 18.0, Y / 18.0, 2, 471)) * (1 - rock)
    moss = (1 - heath) * (1 - rock)
    off_path = 1 - smoothstep(0.0, 0.5, pathw)
    return dict(pathw=pathw, meadow=np.zeros_like(X), moss=0.9 * moss * off_path, heath=heath * off_path,
                rock=rock * off_path)


def populate(L):
    L.clear += [(START[0], 3.5)] + [(p, 2.0 * s + 1.0) for p, s in ERRATICS]
    L.forest(cell=6.0, saplings=False, size=(0.95, 1.2))
    L.far_forest()
    rng = L.rng
    # the knolls' bare slabs, and boulders about them
    for (cx, cy), r, _h in KNOLLS:
        for _ in range(int(r / 2.5)):
            a, d = rng.uniform(0, 2 * np.pi), rng.uniform(0, 0.55 * r)
            x, y = cx + np.cos(a) * d, cy + np.sin(a) * d
            if L.blocked(x, y, 1.0) or path_dist(np.array([x]), np.array([y]))[0] < 2.0:
                continue
            m = f"Slab{int(rng.integers(4))}"
            L.add_prop(m, x, y, rng.uniform(0, 2 * np.pi), rng.uniform(0.6, 1.0), sink=0.0, solid=1.6)
    L.rocks_and_logs(cell=8.0, rates=(0.1, 0.14, 0.14, 0.17, 0.18))
    L.erratics_and_landmarks()

    def cover(i, x, y, r, pick, G, patch, lingon):  # moss cushions, heather, blueberries, lichen on the rock
        if G["rock"][i] > 0.5:
            return f"Lichen{pick % 3}" if r < 0.2 else None
        if G["heath"][i] > 0.5:
            return f"Heather{pick % 3}" if r < 0.45 else (f"Lingonberry{pick % 3}" if r < 0.55 else None)
        if patch[i] > 0.3:
            return f"Blueberry{pick % 3}" if r < 0.3 else None
        return f"MossMound{pick % 3}" if r < 0.12 else (f"Lichen{pick % 3}" if r < 0.15 else None)

    L.ground_cover(pick_model=cover)
    L.trail_edges()
