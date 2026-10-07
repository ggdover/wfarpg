"""River and cliffs: down in a forest valley, by a little river, under a band of low cliffs, 3-4 m of mossy granite
(the hike trail references: mossy boulders, a stony path, wooden steps). A trail runs along the valley floor and
crosses the river on a footbridge; a path climbs to the top of the cliffs where they peter out to the west, wooden
steps climb them in the middle, and a path along the top looks down over them. A spur leads down to a gravel bank,
with stepping stones across. The river runs east, over a rapid. About 125 x 95 m to walk.

Coordinates are metres, +X east, +Y north, Z up (Blender's axes), as in storskogen.py.
"""
import math

import numpy as np

from areas.common import (ALDER, ASPEN, BIRCH, PINE, ROWAN, SPECIES, SPRUCE, catmull_closed, catmull_open, fbm,  # noqa: F401
                          paths_and_outline, point_at, signed_dist, smoothstep)

TITLE = "River and cliffs"
SEED = 61
BOUNDARY = catmull_closed([(-60, -46), (-30, -52), (10, -50), (48, -46), (62, -20), (58, 18), (50, 40), (12, 46),
                           (-28, 44), (-58, 34), (-64, 0)], 5)
BAKE = (-80.0, 80.0, -68.0, 68.0)
FAR_R = 230.0
RIVER = catmull_open([(-100, -31), (-80, -30), (-60, -27), (-40, -31), (-22, -27), (-4, -29), (12, -25), (28, -26),
                      (44, -22), (60, -21), (80, -17), (100, -15)])
CLIFF = catmull_open([(-100, 4), (-80, 2), (-60, 0), (-42, -4), (-24, -2), (-6, 2), (12, -2), (30, -6), (46, -12),
                      (62, -12.5), (80, -9), (100, -7)])
NOTCH_W = 7.8  # the cliff's face where the steps climb it: a ramp this wide, from its foot to its top
_c, _t, _n = point_at(CLIFF, float(signed_dist(np.array([-6.0]), np.array([2.0]), CLIFF)[1][0]))
NOTCH = float(signed_dist(np.array([_c[0]]), np.array([_c[1]]), CLIFF)[1][0])  # where along the cliff the steps are
STAIRS = ((_c[0] - _n[0] * NOTCH_W / 2, _c[1] - _n[1] * NOTCH_W / 2), (_c[0] + _n[0] * NOTCH_W / 2, _c[1] + _n[1] * NOTCH_W / 2))
BRIDGE = ((24.0, -20.6), (24.0, -31.4))
START = ((-31.5, -20.5), 45.0)  # on the way down to the gravel bank: the river behind, the cliffs ahead
PATHS = {
    "valley": (catmull_open([(-80, -19), (-64, -17), (-48, -19), (-32, -16), (-16, -17), (-4, -15), (10, -15), (20, -18),
                             BRIDGE[0]]), 2.0, "trail"),
    "south": (catmull_open([BRIDGE[1], (28, -35), (44, -36), (60, -33), (80, -29)]), 2.0, "trail"),
    "ramp": (catmull_open([(-50, -18), (-57, -12), (-62, -4), (-63, 4), (-56, 10)]), 1.6, "trail"),
    "top": (catmull_open([(-56, 10), (-40, 8), (-24, 9), (-8, 10), (8, 7), (24, 4), (40, -1), (56, -4), (80, -1)]),
            1.6, "trail"),
    "steps": (catmull_open([(-5.0, -15.5), (STAIRS[0][0], STAIRS[0][1] - 3.0), STAIRS[0], STAIRS[1],
                            (STAIRS[1][0], STAIRS[1][1] + 2.5), (-8.5, 10.0)], 4), 1.4, "trail"),
    "beach": (catmull_open([(-32, -16), (-31.5, -21), (-31, -26)]), 1.4, "trail"),
}
STEPPING = [(-31.0 + 0.15 * k, -27.2 - 1.05 * k) for k in range(5)]  # stepping stones across, from the gravel bank
LONE_TREES = []
ERRATICS = [((-20, -9), 1.3), ((40, -40), 1.4), ((-44, 20), 1.2)]
LANDMARKS = []
path_dist, inside, boundary_dist = paths_and_outline(PATHS, BOUNDARY)


def half_width(X):
    """The river's half-width (m), wider and narrower as it goes."""
    X = np.asarray(X, dtype=float)
    return 2.0 + 0.45 * np.sin(X / 13.0) + 0.7 * fbm(X / 9.0, np.full_like(X, 3.7), 2, 605)


def base(X):
    """The valley's fall eastwards, with the rapid: the river's level, give or take."""
    X = np.asarray(X, dtype=float)
    return -0.010 * (X + 80.0) - 0.6 * smoothstep(26.0, 34.0, X)


def cliff_height(X):
    X = np.asarray(X, dtype=float)
    return 3.7 * smoothstep(-68.0, -46.0, X) + 0.3 * fbm(X / 20.0, np.zeros_like(X), 2, 601)


def notch(along):
    """1 where the steps climb the cliff, where its face is a ramp rather than a wall."""
    return 1 - smoothstep(1.2, 3.2, np.abs(np.asarray(along, dtype=float) - NOTCH))


def face_width(X, along):
    """How wide the cliff's face is (m), from its foot to its top: narrow where it's a wall; a ramp at the steps,
    and to the west, where the cliffs peter out."""
    X = np.asarray(X, dtype=float)
    return 1.4 + (NOTCH_W - 1.4) * notch(along) + 8.0 * (1 - smoothstep(-58.0, -48.0, X))


def cliff_step(X, u, along):
    """How far the cliffs lift the ground at signed distance u from their line (+ on top)."""
    w = face_width(X, along)
    t = np.clip((u + w / 2) / w, 0.0, 1.0)
    wide = np.maximum(notch(along), 1 - smoothstep(-58.0, -48.0, np.asarray(X, dtype=float)))
    return cliff_height(X) * ((1 - wide) * t * t * (3 - 2 * t) + wide * t)


def height(X, Y):
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    sr, _ = signed_dist(X, Y, RIVER)
    dr = np.abs(sr)
    hw = half_width(X)
    u, along = signed_dist(X, Y, CLIFF)
    edge = 0.25 * fbm(X / 2.5, Y / 2.5, 2, 607)  # the banks wobble, so the water's edge isn't a line
    bank = np.where(dr < hw, -0.1 - 0.5 * (1 - (dr / hw) ** 2), -0.1 + 0.7 * smoothstep(hw, hw + 2.5, dr))
    bank = bank + edge * (1 - smoothstep(hw + 2.0, hw + 4.0, dr)) * smoothstep(hw * 0.5, hw * 0.9, dr)
    out = np.maximum(dr - hw - 2.5, 0.0)
    valley = np.where(sr > 0, 0.03 * out, 0.1 * out)  # up gently to the cliffs' foot, more steeply to the south
    pd = path_dist(X, Y)
    away = smoothstep(hw + 1.0, hw + 4.0, dr)
    rough = 0.35 * fbm(X / 25.0, Y / 25.0, 2, 612) * away + 0.2 * fbm(X / 7.0, Y / 7.0, 2, 611) * away * smoothstep(1.0, 3.0, pd)
    return base(X) + bank + valley + cliff_step(X, u, along) + rough - 0.05 * (1 - smoothstep(0.6, 1.4, pd))


def water_level(X, Y):
    X = np.asarray(X, dtype=float)
    sr, _ = signed_dist(X, np.asarray(Y, dtype=float), RIVER)
    return np.where(np.abs(sr) < half_width(X) + 1.2, base(X) - 0.15, -100.0)


def flow(X, Y):
    """The river's flow (m/s): along it, faster over the rapid."""
    X = np.asarray(X, dtype=float)
    _, along = signed_dist(X, np.asarray(Y, dtype=float), RIVER)
    _p, (tx, ty), _n = point_at(RIVER, along)
    t = np.clip((X - 26.0) / 8.0, 0.0, 1.0)
    speed = 0.6 + 12.0 * (0.010 + 0.6 * 6.0 * t * (1 - t) / 8.0)
    return tx * speed, ty * speed


def zones(X, Y):
    """Where a point is: by the river (0..1), on the cliffs' face (0..1), up on top (0..1)."""
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    sr, _ = signed_dist(X, Y, RIVER)
    u, along = signed_dist(X, Y, CLIFF)
    w = face_width(X, along)
    river = 1 - smoothstep(half_width(X) + 1.0, half_width(X) + 7.0, np.abs(sr))
    face = (1 - smoothstep(w / 2 + 0.6, w / 2 + 1.4, np.abs(u))) * smoothstep(0.8, 1.5, cliff_height(X))
    top = smoothstep(w / 2, w / 2 + 1.0, u)
    return river, face, top, sr, u, along


def density(X, Y):
    """Thick on the slope south of the river and on top of the cliffs; open on the valley floor between them,
    where the cliffs' face shows, with alders and birches along the water."""
    river, face, top, sr, u, along = zones(X, Y)
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    valley = (sr > 0) * (1 - top)
    d = np.where(sr < 0, 0.85, np.where(top > 0.5, 0.6, 0.3)) + 0.2 * fbm(X / 30.0, Y / 30.0, 2, 621)
    d = d * (1 - 0.75 * valley * smoothstep(-face_width(X, along) / 2 - 7.0, -face_width(X, along) / 2 - 2.0, u))
    d = d + 0.25 * river * valley
    d = d * smoothstep(half_width(X) + 0.3, half_width(X) + 1.5, np.abs(sr))  # none in the water
    d = d * (1 - face) * (1 - 0.3 * top)
    return np.clip(d * smoothstep(1.2, 2.6, path_dist(X, Y)), 0, 1)


def tree_kind(X, Y, roll):
    river, face, top, sr, u, along = zones(X, Y)
    by_river = np.where(roll < 0.35, ALDER, np.where(roll < 0.6, BIRCH, np.where(roll < 0.85, SPRUCE, np.where(roll < 0.9, ROWAN, PINE))))
    valley = np.where(roll < 0.5, SPRUCE, np.where(roll < 0.7, BIRCH, np.where(roll < 0.85, PINE, np.where(roll < 0.95, ASPEN, ROWAN))))
    on_top = np.where(roll < 0.55, PINE, np.where(roll < 0.85, SPRUCE, BIRCH))
    return np.where(top > 0.5, on_top, np.where(river > 0.5, by_river, valley))


def ground_masks(X, Y):
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    river, face, top, sr, u, along = zones(X, Y)
    hw = half_width(X)
    dr = np.abs(sr)
    pathw = np.clip(1 - path_dist(X, Y) / 4.0, 0, 1)
    off_path = 1 - smoothstep(0.0, 0.5, pathw)
    bed = 1 - smoothstep(hw * 0.7, hw * 1.0, dr)
    beach = 1 - smoothstep(2.5, 5.0, np.hypot(X + 31.0, Y + 26.5))
    gravel = np.maximum((1 - smoothstep(hw + 0.4, hw + 2.0 + 0.8 * fbm(X / 5.0, Y / 5.0, 2, 631), dr)) * (1 - bed), beach)
    w = face_width(X, along)
    rock = smoothstep(0.3, 0.6, (1 - smoothstep(w / 2 + 0.5, w / 2 + 3.5, u)) * top + 0.3 * fbm(X / 4.0, Y / 4.0, 2, 632)) * top
    moss = (0.55 + 0.4 * smoothstep(-0.1, 0.3, fbm(X / 12.0, Y / 12.0, 2, 633))) * (1 - rock) * (1 - gravel)
    return dict(pathw=pathw, meadow=np.zeros_like(X), bed=bed, gravel=gravel * (1 - bed), rock=rock * off_path,
                moss=moss * off_path * (1 - bed))


def populate(L):
    rng = L.rng
    L.clear += [(START[0], 3.5)] + [(p, 2.0 * s + 1.0) for p, s in ERRATICS]
    L.clear += [(p, 2.2) for p in STEPPING] + [(((STAIRS[0][0] + STAIRS[1][0]) / 2, (STAIRS[0][1] + STAIRS[1][1]) / 2), 4.5)]
    L.clear += [(((BRIDGE[0][0] + BRIDGE[1][0]) / 2, (BRIDGE[0][1] + BRIDGE[1][1]) / 2), 6.0)]
    # the cliffs' face: rocks side by side along their foot, each reaching back into the slope
    s0 = float(signed_dist(np.array([-52.0]), np.array([0.0]), CLIFF)[1][0])
    s1 = float(signed_dist(np.array([80.0]), np.array([-9.0]), CLIFF)[1][0])
    a = s0
    while a < s1:
        (cx, cy), _t, (nx, ny) = point_at(CLIFF, a)
        H = float(cliff_height(np.array([cx]))[0])
        w = float(face_width(np.array([cx]), np.array([a]))[0])
        if abs(a - NOTCH) > 2.4 and H > 1.4 and w < 3.5:
            out = w / 2 + rng.uniform(0.1, 0.45)
            fx, fy = cx - nx * out, cy - ny * out
            s = (H + 0.75) / 4.6 * rng.uniform(0.96, 1.08)
            foot = L.ground(fx, fy)
            L.add_prop(f"CliffRock{int(rng.integers(6))}", fx, fy, math.atan2(-nx, ny) + rng.uniform(-0.12, 0.12), s,
                       sink=0.0, z=foot - 0.45)
            L.add_solid(fx + nx * 0.9, fy + ny * 0.9, 1.25, 4.6 * s, z=foot - 0.45)
            L.clear.append(((fx + nx * 0.6, fy + ny * 0.6), 1.6))
            if rng.uniform() < 0.55:  # rocks fallen from it, grown over with moss
                d = rng.uniform(1.6, 5.0)
                bx, by = fx - nx * d + rng.uniform(-1, 1), fy - ny * d + rng.uniform(-1, 1)
                if path_dist(np.array([bx]), np.array([by]))[0] > 1.6 and not L.blocked(bx, by, 0.8):
                    m = f"MossBoulder{int(rng.integers(4))}"
                    bs = rng.uniform(0.45, 1.1)
                    L.add_prop(m, bx, by, rng.uniform(0, math.tau), bs, solid=L.info[m]["foot"] * 0.85)
                    L.clear.append(((bx, by), 1.2 * bs))
        a += rng.uniform(2.2, 2.7)
    # the river: stepping stones, and boulders in the rapid
    for x, y in STEPPING:
        lv = float(water_level(np.array([x]), np.array([y]))[0])
        L.add_prop(f"SteppingStone{int(rng.integers(3))}", x, y, rng.uniform(0, math.tau), rng.uniform(0.9, 1.1), sink=0.0, z=lv + 0.1)
    for _ in range(9):
        x = rng.uniform(26.0, 36.0)
        _sr, al = signed_dist(np.array([x]), np.array([-25.0]), RIVER)
        (px, py), _t, (nx, ny) = point_at(RIVER, float(al[0]))
        off = rng.uniform(-1.6, 1.6)
        L.add_prop(f"Boulder{int(rng.integers(8))}", px + nx * off, py + ny * off, rng.uniform(0, math.tau), rng.uniform(0.4, 0.75), sink=0.15)
    L.forest(cell=3.4, saplings=True)
    L.far_forest()
    # boulders and logs about the valley, most of them mossy
    X, Y = np.meshgrid(np.arange(BAKE[0], BAKE[1], 7.0), np.arange(BAKE[2], BAKE[3], 7.0))
    X, Y = (X + rng.uniform(0, 7.0, X.shape)).ravel(), (Y + rng.uniform(0, 7.0, Y.shape)).ravel()
    river, face, top, sr, u, along = zones(X, Y)
    pd = path_dist(X, Y)
    r = rng.uniform(0, 1, len(X))
    for x, y, rv, fc, p, r_, s_ in zip(X, Y, river, face, pd, r, sr):
        if p < 1.6 or fc > 0.2 or abs(s_) < float(half_width(np.array([x]))[0]) + 0.5 or L.blocked(x, y, 2.0):
            continue
        rot = rng.uniform(0, math.tau)
        if r_ < 0.16:
            m = f"MossBoulder{int(rng.integers(4))}"
            L.add_prop(m, x, y, rot, rng.uniform(0.5, 1.3), solid=L.info[m]["foot"] * 0.85)
        elif r_ < 0.2:
            m = f"Boulder{int(rng.integers(8))}"
            L.add_prop(m, x, y, rot, rng.uniform(0.6, 1.2), solid=L.info[m]["foot"] * 0.85)
        elif r_ < 0.25:
            L.log(f"Log{int(rng.integers(2))}", x, y, rot)
        elif r_ < 0.27:
            m = f"Snag{int(rng.integers(3))}"
            L.add_prop(m, x, y, rot, 1.0, solid=0.3)
    L.erratics_and_landmarks()

    def cover(i, x, y, r, pick, G, patch, lingon):
        if G["bed"][i] > 0.3:
            return None
        if G["gravel"][i] > 0.5:  # cobbles, and a tuft of grass
            return f"Boulder{pick % 8}" if r < 0.1 else (f"Grass{pick % 4}" if r < 0.18 else None)
        if G["rock"][i] > 0.5:
            return f"Lichen{pick % 3}" if r < 0.2 else (f"Heather{pick % 3}" if r < 0.26 else None)
        if G["gravel"][i] > 0.15:
            return f"TallGrass{pick % 3}" if r < 0.25 else (f"Sedge{pick % 3}" if r < 0.35 else None)
        if patch[i] > 0.2:
            return f"Fern{pick % 3}" if r < 0.4 else (f"Blueberry{pick % 3}" if r < 0.5 else None)
        if lingon[i] and r < 0.2:
            return f"Lingonberry{pick % 3}"
        return f"MossMound{pick % 3}" if r < 0.07 else (f"Fern{pick % 3}" if r < 0.13 else None)

    def place(i, x, y, m):
        if m.startswith("Boulder"):  # the banks' cobbles: small, sunk in the gravel
            L.add_prop(m, x, y, rng.uniform(0, math.tau), rng.uniform(0.1, 0.24), sink=0.3)
            return True
        return False

    L.ground_cover(pick_model=cover, place=place)
    L.trail_edges()


def build_extras(E):
    E.water("River", (-80.0, 80.0, -42.0, -8.0), water_level, flow, step=0.5)
    E.stairs("Steps", STAIRS[0], STAIRS[1], width=1.3)
    E.bridge("Bridge", BRIDGE[0], BRIDGE[1], width=1.5, arch=0.4)
