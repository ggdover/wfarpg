"""Act 1 world definition, shared by the blueprint maps and the 3D shots.

Coordinates are metres. Origin = the town gate. +X east, +Y north.
Zone outlines are traced from ref_imgs/act1_layout.png (displayed at 2000 px wide), 1 sketch unit = 1.2 m.
Everything is vectorised with numpy so it runs both in Blender and for the maps.
"""
import math
import numpy as np

S = 1.2
OX, OY = 1162.0, 855.0


def W(pts):
    return [((x - OX) * S, (OY - y) * S) for x, y in pts]


def catmull_closed(pts, n=6):
    out = []
    m = len(pts)
    for i in range(m):
        p0, p1, p2, p3 = [np.array(pts[(i + k) % m]) for k in (-1, 0, 1, 2)]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)))
    return out


def catmull_open(pts, n=8):
    out = []
    pts = [np.array(p, dtype=float) for p in pts]
    for i in range(len(pts) - 1):
        p0 = pts[max(0, i - 1)]; p1 = pts[i]; p2 = pts[i + 1]; p3 = pts[min(len(pts) - 1, i + 2)]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)))
    out.append(tuple(pts[-1]))
    return out


# ------------------------------------------------------------------ zones (from the sketch)
ZONES = {
    "town": dict(name="Tallmo", orig="Town", mood="day", poly=W([
        (1138, 880), (1180, 876), (1225, 886), (1238, 900), (1228, 920), (1180, 927), (1140, 920), (1131, 900)])),
    "storskogen": dict(name="Storskogen", orig="The Fairmeadow", mood="day", poly=W([
        (945, 378), (1000, 345), (1200, 349), (1450, 343), (1520, 373), (1531, 450), (1516, 560), (1497, 680), (1488, 800),
        (1470, 848), (1430, 882), (1300, 881), (1180, 863), (1150, 853), (1000, 848), (966, 822), (941, 740), (932, 560), (937, 450)])),
    "harddalen": dict(name="Härddalen", orig="Hearthvale", mood="day", poly=W([
        (1362, 62), (1430, 46), (1600, 44), (1730, 48), (1790, 80), (1815, 180), (1830, 260), (1795, 318), (1700, 332),
        (1640, 345), (1525, 372), (1458, 345), (1532, 300), (1528, 282), (1470, 256), (1366, 236), (1360, 140)])),
    "gamlagarden": dict(name="Gamla gården", orig="The Old Courtyard", mood="golden", poly=W([
        (1582, 672), (1720, 685), (1945, 708), (1955, 800), (1945, 910), (1800, 896), (1576, 893), (1574, 845), (1582, 760)])),
    "dimskogen": dict(name="Dimskogen", orig="Misty Woods", mood="fog", poly=W([
        (662, 168), (760, 163), (860, 180), (896, 215), (896, 300), (905, 320), (1000, 343), (945, 378), (902, 376),
        (890, 430), (880, 488), (830, 492), (800, 488), (750, 482), (700, 470), (665, 440), (660, 300)])),
    "dimmyren": dict(name="Dimmyren", orig="Misty Swamp", mood="fog", poly=W([
        (688, 537), (745, 540), (800, 545), (860, 555), (880, 580), (882, 700), (880, 840), (800, 846), (700, 826),
        (645, 810), (630, 760), (650, 690), (655, 580)])),
    "odeskogen": dict(name="Ödeskogen", orig="The Forsaken Forest", mood="dusk", poly=W([
        (22, 512), (200, 508), (352, 512), (346, 632), (360, 680), (370, 760), (356, 900), (250, 922), (150, 925),
        (45, 920), (15, 880), (40, 700), (25, 560)])),
}
for z in ZONES.values():
    z["smooth"] = catmull_closed(z["poly"], 5)

# passages between zones (polyline, width in metres)
CORRIDORS = [
    (W([(1162, 885), (1162, 845)]), 28),                                   # town gate
    (W([(1470, 822), (1530, 824), (1590, 822)]), 54),                      # to Gamla gården
    (W([(1470, 360), (1500, 330), (1520, 300)]), 60),                      # to Härddalen
    (W([(975, 362), (930, 352), (890, 340)]), 60),                         # to Dimskogen
    (W([(775, 470), (774, 515), (772, 560)]), 40),                         # Dimskogen -> Dimmyren pass
    (W([(652, 670), (560, 668), (528, 640), (515, 565), (470, 543), (430, 550), (420, 620), (395, 660), (330, 662)]), 40),  # winding way west
]


# ------------------------------------------------------------------ paths (main roads and trails)
def P(pts, n=8):
    return catmull_open(pts, n)


PATHS = {
    "town_square": (P([(-24, -57), (4, -54), (26, -57), (40, -59)]), 4.0, "road"),
    "town_road": (P([(2, -52), (0, -28), (0, -5), (4, 20), (18, 60), (26, 110), (32, 170), (45, 245)]), 4.0, "road"),
    "road_nw": (P([(45, 245), (8, 290), (-50, 340), (-112, 410), (-160, 470), (-205, 532), (-240, 585), (-280, 615), (-330, 630)]), 3.6, "road"),
    "road_ne": (P([(45, 245), (105, 292), (185, 352), (255, 425), (318, 505), (368, 572), (405, 615), (450, 660)]), 3.6, "road"),
    "road_e": (P([(45, 245), (118, 214), (200, 168), (278, 118), (338, 66), (392, 41), (460, 36), (520, 38)]), 3.6, "road"),
    "esker_trail": (P([(-238, 82), (-196, 128), (-150, 178), (-112, 246), (-92, 318), (-66, 396), (-30, 462)]), 2.2, "trail"),
    "hill_trail": (P([(232, 400), (214, 430), (194, 452), (182, 466)]), 2.2, "trail"),
    "hollow_trail": (P([(-112, 410), (-140, 400), (-170, 392), (-196, 384)]), 2.0, "trail"),
    # Härddalen
    "hv_road": (P([(450, 660), (500, 720), (560, 770), (620, 800), (700, 830)]), 3.4, "road"),
    # Gamla gården
    "gg_road": (P([(520, 38), (600, 60), (680, 80), (735, 88)]), 3.4, "road"),
    # Dimskogen: lantern path west, then south to the pass
    "ds_path": (P([(-330, 630), (-400, 660), (-470, 690), (-530, 650), (-540, 560), (-492, 480), (-466, 420)]), 2.8, "trail"),
    # Dimmyren boardwalks
    "dm_boardwalk": (P([(-466, 420), (-470, 360), (-500, 300), (-470, 230), (-520, 160), (-560, 120), (-590, 222)]), 2.0, "boardwalk"),
    # winding way west and Ödeskogen
    "west_trail": (P([(-590, 222), (-720, 224), (-760, 260), (-776, 350), (-830, 375), (-878, 366), (-890, 284), (-920, 236), (-1000, 233)]), 2.6, "trail"),
    "od_path": (P([(-1000, 233), (-1060, 220), (-1110, 190), (-1150, 170)]), 2.6, "trail"),
}

# ------------------------------------------------------------------ terrain features
ESKER = P([(-262, 60), (-205, 118), (-152, 170), (-114, 240), (-94, 318), (-68, 396), (-32, 465), (6, 520)], 6)
HILL = dict(c=(182, 468), r0=30, r1=85, h=18.0)                # Utsiktsberget
HOLLOW = dict(c=(-205, 382), r0=26, r1=52, h=-10.0)            # Trollgrytan (kettle hole)
LAKE = dict(c=(312, 292), rx=48, ry=30, depth=2.8)            # Tjärnen
PLAINS = [((186, 228), 175, 118), ((60, 70), 85, 62), ((620, 760), 150, 70)]   # Stora ängen, Hagen (pasture), Härddalen fields
BOG_WATER = -2.95
DENSE = [((-150, 420), 170), ((-40, 560), 150), ((-470, 600), 260), ((-1160, 160), 320)]
VALLEY = P([(260, 760), (420, 800), (560, 790), (700, 800), (820, 850)], 6)   # Härddalen valley floor
STREAM = P([(280, 900), (380, 840), (480, 812), (580, 790), (690, 795), (790, 830)], 6)
COURTYARD = dict(c=(750, 92), w=74, h=54)
FARMSTEAD = dict(c=(625, 812), r=19)
FIELDS = [((560, 760), 70, 26, 0.12), ((660, 742), 60, 22, -0.05), ((600, 870), 66, 22, 0.2), ((520, 868), 44, 18, -0.1)]
BOG = dict(c=(-500, 230), rx=140, ry=170)
ARENA = dict(c=(-1160, 160), r=36)

# points of interest
WAYSTONES = {"Tallmo": (22, -49), "Vägskälet": (52, 236), "Härddalen": (606, 808), "Gamla gården": (705, 70),
             "Dimskogen": (-360, 640), "Dimmyren": (-480, 380), "Ödeskogen": (-1000, 240)}

QUESTS = [
    # id, kind, zone, title (Swedish), title (English), location, minutes
    (1, "main", "storskogen", "Vägen ut", "The Road Out", (48, 236), 6),
    (2, "side", "storskogen", "Fårherdens flock", "The Shepherd's Flock", (200, 210), 7),
    (3, "side", "storskogen", "Trollgrytan", "The Troll's Cauldron", (-205, 382), 8),
    (4, "main", "storskogen", "Vårdkasen", "The Beacon", (182, 468), 7),
    (5, "main", "harddalen", "Den kalla härden", "The Cold Hearth", (625, 812), 10),
    (6, "side", "harddalen", "Björnen i kornet", "The Bear in the Barley", (520, 868), 6),
    (7, "side", "gamlagarden", "Sista skörden", "The Last Harvest", (790, 60), 7),
    (8, "main", "gamlagarden", "Förvaltarens brev", "The Steward's Letter", (750, 100), 7),
    (9, "main", "dimskogen", "När dimman kommer", "When the Fog Rolls In", (-500, 640), 10),
    (10, "side", "dimskogen", "Lyktbäraren", "The Lantern Bearer", (-420, 690), 6),
    (11, "main", "dimmyren", "De sjunkna stenarna", "The Sunken Stones", (-520, 200), 12),
    (12, "main", "odeskogen", "Den hornkrönte", "The Antlered One", (-1160, 160), 15),
]

AREAS = [  # sub-area labels inside zones (name, translation, position)
    ("Stora ängen", "the great meadow", (205, 205)), ("Hagen", "the pasture", (60, 60)), ("Åsen", "the esker", (-150, 200)),
    ("Utsiktsberget", "lookout hill", (182, 505)), ("Trollgrytan", "the troll's cauldron", (-205, 330)), ("Tjärnen", "the tarn", (312, 262)),
    ("Tätskogen", "the thicket", (-160, 520)), ("Vägskälet", "the crossroads", (60, 270)),
]

# screenshot cameras: id, zone, label, target (x, y), yaw, pitch, dist, extras
SHOTS = [
    ("tallmo", "town", "Tallmo, the town square", (24, -57), 212.0, 46.0, 34.0),
    ("angen", "storskogen", "Stora ängen, the great meadow", (150, 196), 222.0, 12.0, 11.0),
    ("tatskogen", "storskogen", "Tätskogen, the thicket", (-140, 445), 225.0, 55.0, 21.0),
    ("utsikten", "storskogen", "On top of Utsiktsberget", (176, 462), 62.0, 13.0, 9.5),
    ("trollgrytan", "storskogen", "Down into Trollgrytan", (-147, 392), 8.0, 22.0, 14.0),
    ("harddalen", "harddalen", "Härddalen, the burned farm", (612, 800), 250.0, 30.0, 26.0),
    ("gamlagarden", "gamlagarden", "Gamla gården at sunset", (756, 94), 205.0, 48.0, 30.0),
    ("dimskogen", "dimskogen", "The lantern path in Dimskogen", (-450, 676), 337.0, 38.0, 16.0),
    ("dimmyren", "dimmyren", "Boardwalks over Dimmyren", (-490, 310), 250.0, 28.0, 17.0),
    ("odeskogen", "odeskogen", "The heart of Ödeskogen", (-1140, 180), 40.0, 20.0, 20.0),
]

TOWN_SQUARE = dict(c=(26, -57), rx=12, ry=8)
TOWN_LAYOUT = [  # x, y, rot (deg), kind
    (26, -42, 0, "longhouse"), (8, -48, 25, "cottage"), (6, -62, 90, "cottage"), (14, -72, 160, "cottage"),
    (34, -73, 180, "barn"), (48, -68, -135, "cottage"), (47, -55, -90, "cottage"), (44, -44, -25, "cottage"), (-16, -74, 160, "cottage")]
TOWN_HOUSES = TOWN_LAYOUT


# ------------------------------------------------------------------ math helpers (numpy)
def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _hash(ix, iy, seed):
    h = (ix.astype(np.int64) * 374761393 + iy.astype(np.int64) * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h = h ^ (h >> 16)
    return (h & 0xFFFFFF) / float(0xFFFFFF)


def vnoise(x, y, seed=0):
    ix, iy = np.floor(x), np.floor(y)
    fx, fy = x - ix, y - iy
    ux, uy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = _hash(ix, iy, seed), _hash(ix + 1, iy, seed)
    c, d = _hash(ix, iy + 1, seed), _hash(ix + 1, iy + 1, seed)
    return (a + (b - a) * ux + (c - a) * uy + (a - b - c + d) * ux * uy) * 2 - 1


def fbm(x, y, octaves=3, seed=0):
    tot, amp, f, norm = 0.0, 1.0, 1.0, 0.0
    for o in range(octaves):
        tot = tot + amp * vnoise(x * f, y * f, seed + o * 17)
        norm += amp
        amp *= 0.5
        f *= 2.0
    return tot / norm


def seg_dist(X, Y, pts):
    pts = np.asarray(pts, dtype=float)
    best = np.full(np.shape(X), 1e9)
    for (ax, ay), (bx, by) in zip(pts[:-1], pts[1:]):
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy + 1e-9
        t = np.clip(((X - ax) * dx + (Y - ay) * dy) / L2, 0, 1)
        best = np.minimum(best, np.hypot(X - (ax + t * dx), Y - (ay + t * dy)))
    return best


def in_poly(X, Y, poly):
    poly = np.asarray(poly, dtype=float)
    inside = np.zeros(np.shape(X), dtype=bool)
    x0, y0 = poly[-1]
    for x1, y1 in poly:
        cond = ((y1 > Y) != (y0 > Y))
        with np.errstate(divide="ignore", invalid="ignore"):
            xi = (x0 - x1) * (Y - y1) / (y0 - y1 + 1e-12) + x1
        inside ^= cond & (X < xi)
        x0, y0 = x1, y1
    return inside


def zone_masks(X, Y):
    return {k: in_poly(X, Y, z["smooth"]) for k, z in ZONES.items()}


def walkable(X, Y, masks=None):
    masks = masks or zone_masks(X, Y)
    m = np.zeros(np.shape(X), dtype=bool)
    for v in masks.values():
        m |= v
    for pts, w in CORRIDORS:
        m |= seg_dist(X, Y, P(pts, 6)) < w / 2
    return m


def ell(X, Y, c, rx, ry):
    return np.hypot((X - c[0]) / rx, (Y - c[1]) / ry)


def path_dist(X, Y, kinds=None):
    best = np.full(np.shape(X), 1e9)
    for name, (pts, w, kind) in PATHS.items():
        if kinds and kind not in kinds:
            continue
        best = np.minimum(best, seg_dist(X, Y, pts) / (w / 2))
    return best


# ------------------------------------------------------------------ height, density, masks
def height(X, Y, masks=None):
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    masks = masks or zone_masks(X, Y)
    h = 2.0 * fbm(X / 170.0, Y / 170.0, 3, 1) + 0.5 * fbm(X / 45.0, Y / 45.0, 2, 2)
    # Storskogen landforms
    d_esk = seg_dist(X, Y, ESKER)
    h += 11.0 * (1 - smoothstep(4.0, 54.0, d_esk))
    d_hill = np.hypot(X - HILL["c"][0], Y - HILL["c"][1])
    h += HILL["h"] * (1 - smoothstep(HILL["r0"], HILL["r0"] + HILL["r1"], d_hill))
    d_hol = np.hypot(X - HOLLOW["c"][0], Y - HOLLOW["c"][1])
    h += HOLLOW["h"] * (1 - smoothstep(HOLLOW["r0"], HOLLOW["r0"] + HOLLOW["r1"], d_hol))
    h -= 1.4 * (1 - smoothstep(5.0, 15.0, d_hol))
    e_lake = ell(X, Y, LAKE["c"], LAKE["rx"], LAKE["ry"])
    h -= LAKE["depth"] * (1 - smoothstep(0.7, 1.5, e_lake))
    # Härddalen: a broad valley with a stream
    d_val = seg_dist(X, Y, VALLEY)
    h -= 6.0 * (1 - smoothstep(30, 170, d_val))
    d_str = seg_dist(X, Y, STREAM)
    h -= 1.3 * (1 - smoothstep(1.5, 9.0, d_str))
    # Gamla gården: flat courtyard
    cx, cy = COURTYARD["c"]
    yard = (1 - smoothstep(0, 18, np.maximum(np.abs(X - cx) - COURTYARD["w"] / 2, np.abs(Y - cy) - COURTYARD["h"] / 2)))
    h = h * (1 - yard) + 0.6 * yard
    # Dimskogen: rolling hills
    h += 3.5 * fbm(X / 95.0, Y / 95.0, 2, 7) * (1 - smoothstep(150, 260, np.hypot(X + 450, Y - 640)))
    # Dimmyren: low and flat
    bog = 1 - smoothstep(0.75, 1.15, ell(X, Y, BOG["c"], BOG["rx"], BOG["ry"]))
    pool = 1 - smoothstep(-0.36, -0.2, fbm(X / 22.0, Y / 22.0, 2, 21))
    h = h * (1 - bog) + (-2.5 + 0.3 * fbm(X / 18.0, Y / 18.0, 2, 9) - 0.85 * pool) * bog
    # Ödeskogen: rolling, with a flat arena bowl
    h += 2.5 * fbm(X / 80.0, Y / 80.0, 2, 13) * (1 - smoothstep(200, 300, np.hypot(X + 1160, Y - 170)))
    d_ar = np.hypot(X - ARENA["c"][0], Y - ARENA["c"][1])
    ar = 1 - smoothstep(ARENA["r"], ARENA["r"] + 30, d_ar)
    h = h * (1 - ar) - 1.0 * ar
    # Town: flatten
    tw = 1 - smoothstep(0.9, 1.6, ell(X, Y, (26, -55), 70, 38))
    h = h * (1 - tw * 0.7) + 0.4 * tw
    # roads ease the terrain a little
    pd = path_dist(X, Y, ("road",))
    h -= 0.06 * (1 - smoothstep(0.6, 1.4, pd))
    return h


def water(X, Y):
    """Returns (is_water, water_level) for lakes and pools."""
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    lake = ell(X, Y, LAKE["c"], LAKE["rx"], LAKE["ry"]) < 1.0
    tarn = np.hypot(X - HOLLOW["c"][0], Y - HOLLOW["c"][1]) < 13.0
    bogw = (ell(X, Y, BOG["c"], BOG["rx"], BOG["ry"]) < 0.9) & (fbm(X / 22.0, Y / 22.0, 2, 21) < -0.27)
    return lake, tarn, bogw


def density(X, Y, masks=None):
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    masks = masks or zone_masks(X, Y)
    d = 0.55 + 0.4 * fbm(X / 70.0, Y / 70.0, 3, 5)
    for c, r in DENSE:
        d += 0.4 * (1 - smoothstep(r * 0.5, r, np.hypot(X - c[0], Y - c[1])))
    for c, rx, ry in PLAINS:
        d *= smoothstep(0.85, 1.25, ell(X, Y, c, rx, ry))
    d *= smoothstep(0.9, 1.6, ell(X, Y, LAKE["c"], LAKE["rx"], LAKE["ry"]))
    d_hill = np.hypot(X - HILL["c"][0], Y - HILL["c"][1])
    d *= 0.05 + 0.95 * smoothstep(HILL["r0"] + 38, HILL["r0"] + 95, d_hill)
    d_hol = np.hypot(X - HOLLOW["c"][0], Y - HOLLOW["c"][1])
    d = np.where(d_hol < HOLLOW["r0"] + 4, np.minimum(d, 0.32), d)
    slope_ring = (d_hol >= HOLLOW["r0"] + 4) & (d_hol < HOLLOW["r0"] + HOLLOW["r1"] + 6)
    d = np.where(slope_ring, d * 0.18, d)
    d *= smoothstep(14, 22, d_hol)
    d_esk = seg_dist(X, Y, ESKER)
    d = np.where(d_esk < 12, d * 0.7, d)
    cx, cy = COURTYARD["c"]
    d *= smoothstep(10, 40, np.maximum(np.abs(X - cx) - COURTYARD["w"] / 2, np.abs(Y - cy) - COURTYARD["h"] / 2))
    d *= smoothstep(FARMSTEAD["r"], FARMSTEAD["r"] + 25, np.hypot(X - FARMSTEAD["c"][0], Y - FARMSTEAD["c"][1]))
    d = np.where(masks["harddalen"], d * smoothstep(40, 150, seg_dist(X, Y, VALLEY)), d)
    d = np.where(masks["dimskogen"], np.maximum(d, 0.75), d)
    bog = ell(X, Y, BOG["c"], BOG["rx"], BOG["ry"])
    d = np.where(bog < 1.0, d * 0.18, d)
    d *= smoothstep(ARENA["r"] + 4, ARENA["r"] + 24, np.hypot(X - ARENA["c"][0], Y - ARENA["c"][1]))
    d = np.where(masks["town"], 0.0, d)
    pd = path_dist(X, Y)
    d *= smoothstep(1.2, 2.6, pd)
    return np.clip(d, 0, 1)


def tree_kind(X, Y, masks=None):
    """0 pine, 1 spruce, 2 birch, 3 dead."""
    masks = masks or zone_masks(X, Y)
    n = fbm(X / 30.0, Y / 30.0, 2, 31)
    k = np.where(n > 0.35, 1, 0)
    k = np.where((np.hypot(X + 150, Y - 420) < 150) & (n > -0.25), 1, k)
    k = np.where(masks["dimskogen"], np.where(n > -0.4, 1, 0), k)
    k = np.where(masks["harddalen"] | masks["gamlagarden"], np.where(n > 0.1, 2, k), k)
    k = np.where(masks["dimmyren"], 3, k)
    k = np.where(masks["odeskogen"], np.where(n > 0.0, 3, 1), k)
    return k


def ground_masks(X, Y, masks=None):
    masks = masks or zone_masks(X, Y)
    pd = path_dist(X, Y)
    path = 1 - smoothstep(0.55, 1.2, pd)
    meadow = np.zeros(np.shape(X))
    for c, rx, ry in PLAINS:
        meadow = np.maximum(meadow, 1 - smoothstep(0.8, 1.2, ell(X, Y, c, rx, ry)))
    dens = density(X, Y, masks)
    litter = smoothstep(0.55, 0.85, dens)
    field = np.zeros(np.shape(X))
    stripe = np.zeros(np.shape(X))
    for c, hw, hh, rot in FIELDS:
        ca, sa = math.cos(rot), math.sin(rot)
        lx = (X - c[0]) * ca + (Y - c[1]) * sa
        ly = -(X - c[0]) * sa + (Y - c[1]) * ca
        f = (1 - smoothstep(-1, 2, np.maximum(np.abs(lx) - hw, np.abs(ly) - hh)))
        field = np.maximum(field, f)
        stripe = np.where(f > 0, (np.sin(ly * 2.2) > 0).astype(float), stripe)
    bog = 1 - smoothstep(0.8, 1.05, ell(X, Y, BOG["c"], BOG["rx"], BOG["ry"]))
    cx, cy = COURTYARD["c"]
    paving = (1 - smoothstep(-2, 2, np.maximum(np.abs(X - cx + 4) - 15, np.abs(Y - cy + 2) - 10))) * smoothstep(-0.5, -0.1, fbm(X / 6.0, Y / 6.0, 2, 51))
    sq = 1 - smoothstep(0.85, 1.15, ell(X, Y, TOWN_SQUARE["c"], TOWN_SQUARE["rx"], TOWN_SQUARE["ry"]))
    yard = np.maximum(sq, 1 - smoothstep(FARMSTEAD["r"] - 8, FARMSTEAD["r"] + 4, np.hypot(X - FARMSTEAD["c"][0], Y - FARMSTEAD["c"][1])))
    meadow = np.maximum(meadow, masks["town"].astype(float) * (1 - sq))
    ash = 1 - smoothstep(6, 18, np.hypot(X - FARMSTEAD["c"][0] - 6, Y - FARMSTEAD["c"][1] + 4))
    lake, tarn, bogw = water(X, Y)
    shore = np.maximum(1 - smoothstep(0.95, 1.35, ell(X, Y, LAKE["c"], LAKE["rx"], LAKE["ry"])),
                       1 - smoothstep(13, 20, np.hypot(X - HOLLOW["c"][0], Y - HOLLOW["c"][1])))
    darkfloor = (masks["dimskogen"] | masks["odeskogen"]).astype(float)
    return dict(path=path, meadow=meadow, litter=litter, field=field * stripe, fieldbase=field, bog=bog, paving=paving,
                yard=yard, ash=ash, shore=shore, darkfloor=darkfloor)
