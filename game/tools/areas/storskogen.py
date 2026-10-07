"""The play demo's area as data: a small slice of Storskogen, about 155 x 110 m that the hero can walk.

Dense pine and spruce forest in the west, like Tätskogen, with a winding trail that comes out onto an open meadow in
the east, like Stora ängen, with a low rise at its far side. Beyond the walls round the walkable area, a rim of forest
hides the edge, and a sparse distant forest fills the view from low camera angles.

Coordinates are metres, +X east, +Y north, Z up (Blender's axes; build_demo.py turns them into Godot's). Everything
is vectorised with numpy, like mockups/act1_world.py, whose noise and geometry helpers it uses.
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "mockups"))
import act1_world as A  # noqa: E402

smoothstep, fbm, seg_dist, in_poly = A.smoothstep, A.fbm, A.seg_dist, A.in_poly

# ------------------------------------------------------------------ outline
# the walkable area: invisible walls follow this line, and the forest rim fills everything beyond it
BOUNDARY = A.catmull_closed([(-78, -40), (-66, -54), (-30, -57), (8, -52), (44, -56), (70, -46), (78, -12), (76, 22),
                             (66, 48), (34, 56), (-6, 52), (-46, 56), (-74, 42), (-80, 2)], 5)
BAKE = (-112.0, 112.0, -88.0, 88.0)  # x0, x1, y0, y1: the detailed ground, the walkable area and its forest rim
FAR_R = 250.0  # the distant forest reaches this far from the centre
START = ((-71.0, -4.6), 0.0)  # where the hero starts, and which way it faces (degrees from east, anticlockwise)

# ------------------------------------------------------------------ paths: polyline, width (m), kind
P = A.catmull_open
PATHS = {
    "trail": (P([(-90, -8), (-72, -4.5), (-60, 2), (-48, 1), (-37, -6), (-25, -5), (-14, 3), (-2, 5), (10, 1),
                 (23, -5), (36, -3), (48, 5), (62, 1), (90, -7)]), 2.4, "trail"),
    "north_fork": (P([(-37, -6), (-41, 8), (-50, 22), (-55, 36), (-64, 62)]), 2.0, "trail"),
    "rise_trail": (P([(48, 5), (51, 15), (54, 25), (55, 31)]), 2.0, "trail"),
}

# ------------------------------------------------------------------ landforms and areas
RISE = dict(c=(55.0, 33.0), r0=7.0, r1=32.0, h=7.0)  # a low rise with a flat top, at the meadow's far side
MEADOW = dict(c=(40.0, 2.0), rx=40.0, ry=42.0)  # Stora ängen, the open meadow
DENSE = dict(c=(-45.0, 0.0), r0=30.0, r1=75.0)  # the thicket's core, like Tätskogen
# trees standing on their own in the meadow (species, position)
LONE_TREES = [("ScotsPine", (30, 18)), ("ScotsPine", (63, -27)), ("ScotsPine", (56.5, 35.5)), ("SilverBirch", (20, -13)),
              ("SilverBirch", (46, -31)), ("SilverBirch", (69, 13)), ("Rowan", (36, 30)), ("Rowan", (9, 23)),
              ("Aspen", (14, -36)), ("Aspen", (18.5, -39)), ("Aspen", (11, -41)), ("Aspen", (16.5, -33)),
              ("Alder", (3, -44)), ("Alder", (-1, -40))]
# boulders the glacier left in the meadow and on the rise (position, scale)
ERRATICS = [((26, 8), 1.6), ((44, -15), 1.9), ((61, 21), 1.4), ((58.5, 36), 1.2), ((13, 31), 1.5), ((33, -40), 1.3)]
LANDMARKS = [("RuneStone", (4.0, 9.0), -60.0), ("Cairn", (53.5, 32.0), 0.0)]  # name, position, rotation (deg)


# ------------------------------------------------------------------ fields
def path_dist(X, Y):
    """Distance from the nearest path's centre line, in that path's half-widths: 1 at its nominal edge."""
    best = np.full(np.shape(X), 1e9)
    for pts, w, _kind in PATHS.values():
        best = np.minimum(best, seg_dist(X, Y, pts) / (w / 2))
    return best


def inside(X, Y):
    return in_poly(X, Y, BOUNDARY)


def boundary_dist(X, Y):
    """Distance from the walkable outline in metres: positive inside, negative outside."""
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    d = seg_dist(X, Y, BOUNDARY + BOUNDARY[:1])
    return np.where(inside(X, Y), d, -d)


def meadow_e(X, Y):
    """The meadow's elliptic distance, ragged with noise: under 1 inside."""
    m = MEADOW
    return A.ell(X, Y, m["c"], m["rx"], m["ry"]) + 0.18 * fbm(X / 25.0, Y / 25.0, 2, 71)


def rise_dist(X, Y):
    return np.hypot(X - RISE["c"][0], Y - RISE["c"][1])


def height(X, Y):
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    h = 1.6 * fbm(X / 90.0, Y / 90.0, 3, 61) + 0.45 * fbm(X / 28.0, Y / 28.0, 2, 62)
    h += RISE["h"] * (1 - smoothstep(RISE["r0"], RISE["r0"] + RISE["r1"], rise_dist(X, Y)))
    h -= 0.05 * (1 - smoothstep(0.6, 1.4, path_dist(X, Y)))  # feet have pressed the trails down a little
    return h


def density(X, Y):
    """How thick the forest grows, 0 to 1."""
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    d = 0.55 + 0.4 * fbm(X / 60.0, Y / 60.0, 3, 65)
    d += 0.42 * (1 - smoothstep(DENSE["r0"], DENSE["r1"], np.hypot(X - DENSE["c"][0], Y - DENSE["c"][1])))
    d *= smoothstep(0.85, 1.3, meadow_e(X, Y))
    d *= 0.06 + 0.94 * smoothstep(RISE["r0"] + 10, RISE["r0"] + 30, rise_dist(X, Y))  # an open top on the rise
    rim = smoothstep(2.0, 8.0, -boundary_dist(X, Y))  # beyond the walls the forest closes in
    d = d * (1 - rim) + np.maximum(d, 0.88) * rim
    d *= smoothstep(1.2, 2.6, path_dist(X, Y))
    return np.clip(d, 0, 1)


SPECIES = ["ScotsPine", "NorwaySpruce", "SilverBirch", "Aspen", "Rowan", "Alder"]


def tree_kind(X, Y, roll):
    """Which species grows here, as an index into SPECIES; roll is a uniform random number per tree. Spruce
    thickens in the core, and the birch, aspen, rowan and alder keep to the forest's edge."""
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    n = fbm(X / 30.0, Y / 30.0, 2, 31)
    core = 1 - smoothstep(DENSE["r0"] - 10, DENSE["r1"] - 10, np.hypot(X - DENSE["c"][0], Y - DENSE["c"][1]))
    e = meadow_e(X, Y)
    edge = smoothstep(0.8, 1.05, e) * (1 - smoothstep(1.3, 1.9, e))
    p_leaf = 0.1 + 0.45 * edge
    p_spruce = (0.22 + 0.45 * core + np.where(n > 0.3, 0.25, 0.0)) * (1 - p_leaf)
    leafy = fbm(X / 14.0, Y / 14.0, 2, 37)  # the deciduous trees grow in clumps of one kind
    kind = np.where(roll < p_leaf, np.where(leafy > 0.35, 3, np.where(leafy < -0.4, 5, np.where(leafy < -0.1, 4, 2))),
                    np.where(roll < p_leaf + p_spruce, 1, 0))
    return kind


def ground_masks(X, Y):
    """The ground layers the shader paints (see mockups/forest_cam.py, mat_ground, and act1_shots.extend_ground)."""
    e = meadow_e(X, Y)
    return dict(pathw=np.clip(1 - path_dist(X, Y) / 4.0, 0, 1), meadow=1 - smoothstep(0.8, 1.2, e))


def steepest(step=0.5):
    """The steepest slope in degrees, for checking that the whole area is walkable."""
    xs = np.arange(BAKE[0], BAKE[1], step)
    ys = np.arange(BAKE[2], BAKE[3], step)
    X, Y = np.meshgrid(xs, ys)
    Z = height(X, Y)
    gy, gx = np.gradient(Z, step)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    return float(slope[inside(X, Y)].max())


if __name__ == "__main__":
    print("steepest walkable slope: %.1f degrees" % steepest())
    print("walkable area: %.0f m2" % (sum(inside(*np.meshgrid(np.arange(-90, 90, 1.0), np.arange(-70, 70, 1.0))).ravel())))
