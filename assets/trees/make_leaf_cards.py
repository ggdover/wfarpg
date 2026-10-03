"""Leaf cards for the tree portfolio: five designs per species, each a texture with a transparent background.

    python3 make_leaf_cards.py      writes textures/<species>_<1-5>.png (512 x 512) and previews/leaf_cards.png

Each card is a cluster of leaves or needles. The trees cross several copies of a card at their centre to make a leaf
clump; the tree editor (tree_editor.py) picks the card and how the copies are crossed. Rowan cards also come with
berries, as textures/rowan_<n>_berries.png. Leaves are drawn as two flat halves, one lighter and one darker, to match
the faceted low-poly props. The transparent pixels carry the card's average leaf colour, so filtered edges don't get
dark or white fringes.
"""
import json
import math
import os
import random

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "textures")
SIZE = 512
SS = 4  # drawn at 4x and scaled down, for clean edges
N = SIZE * SS
TAU = math.tau


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def shade(c, f):
    return tuple(max(0, min(255, int(round(v * f)))) for v in c)


class Card:
    """Drawing in unit coordinates: x to the right, y up, (0.5, 0.5) is the clump's centre."""

    def __init__(self, palette, seed):
        self.rng = random.Random(seed)
        self.pal = [rgb(p) for p in palette]
        bg = tuple(sum(c[i] for c in self.pal) // len(self.pal) for i in range(3))
        self.img = Image.new("RGBA", (N, N), bg + (0,))
        self.d = ImageDraw.Draw(self.img)

    def px(self, p):
        return (p[0] * N, (1 - p[1]) * N)

    def colour(self, pal=None, jitter=0.07):
        c = self.rng.choice([rgb(p) for p in pal] if pal else self.pal)
        return shade(c, 1 + self.rng.uniform(-jitter, jitter))

    def twig(self, pts, width, col):
        col = rgb(col) if isinstance(col, str) else col
        w = max(1, int(width * N))
        self.d.line([self.px(p) for p in pts], fill=col + (255,), width=w, joint="curve")
        for p in pts[:1] + pts[-1:]:
            x, y = self.px(p)
            self.d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=col + (255,))

    def leaf(self, base, ang, length, width, profile, col=None, serr=0.0, curve=0.0, notch=False, samples=14):
        """A leaf from its stalk end along ang, as two halves split by the midrib: light on one side, dark on the other."""
        col = col or self.colour()
        dx, dy = math.cos(ang), math.sin(ang)
        px_, py_ = -dy, dx
        prof = [profile(i / samples) for i in range(samples + 1)]
        peak = max(prof) or 1.0
        left, right, mid = [], [], []
        for i in range(samples + 1):
            t = i / samples
            bend = curve * length * t * t
            mx = base[0] + dx * length * t + px_ * bend
            my = base[1] + dy * length * t + py_ * bend
            w = width * prof[i] / peak
            if serr and 0 < i < samples:
                w *= 1 + serr * (1 if i % 2 else -1)
            if notch and i == samples:  # a notched tip: pull the end of the midrib back
                mx -= dx * length * 0.06
                my -= dy * length * 0.06
            mid.append((mx, my))
            left.append((mx + px_ * w, my + py_ * w))
            right.append((mx - px_ * w, my - py_ * w))
        light, dark = (shade(col, 1.1), shade(col, 0.82)) if self.rng.random() < 0.5 else (shade(col, 0.82), shade(col, 1.1))
        self.d.polygon([self.px(p) for p in left + mid[::-1]], fill=light + (255,))
        self.d.polygon([self.px(p) for p in right + mid[::-1]], fill=dark + (255,))

    def needle(self, start, ang, length, width, col=None):
        col = col or self.colour()
        dx, dy = math.cos(ang), math.sin(ang)
        tip = (start[0] + dx * length, start[1] + dy * length)
        a = (start[0] - dy * width, start[1] + dx * width)
        b = (start[0] + dy * width, start[1] - dx * width)
        self.d.polygon([self.px(a), self.px(tip), self.px(b)], fill=col + (255,))

    def tuft(self, c, n, length, spread=None, direction=0.0, width=0.0055, pal=None):
        """Needles fanning out from one point: all round, or spread radians either side of direction."""
        for _ in range(n):
            a = self.rng.uniform(0, TAU) if spread is None else direction + self.rng.gauss(0, spread)
            s = self.rng.uniform(0.0, 0.02)
            self.needle((c[0] + math.cos(a) * s, c[1] + math.sin(a) * s), a, length * self.rng.uniform(0.65, 1.0), width,
                        self.colour(pal) if pal else None)

    def berry(self, c, r, col, hi):
        x, y = self.px(c)
        rr = r * N
        self.d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=rgb(col) + (255,))
        h = rr * 0.38
        self.d.ellipse([x - rr * 0.45 - h, y - rr * 0.45 - h, x - rr * 0.45 + h, y - rr * 0.45 + h], fill=rgb(hi) + (255,))

    def needles_along(self, tw, step=0.0055, length=(0.03, 0.045), angle=(0.9, 1.35), width=0.0045):
        total = sum(math.dist(tw[i], tw[i + 1]) for i in range(len(tw) - 1))
        for j in range(int(total / step)):
            f = j * step / total
            p, h = at(tw, f), heading(tw, f)
            for side in (1, -1):
                self.needle(p, h + side * self.rng.uniform(*angle), self.rng.uniform(*length) * (1.05 - 0.4 * f), width)

    def save(self, name):
        os.makedirs(OUT, exist_ok=True)
        img = self.img.resize((SIZE, SIZE), Image.LANCZOS)
        img.save(os.path.join(OUT, name + ".png"))
        return img


def curve_pts(p0, ang, length, bend, n=8, droop=0.0):
    """Points along a gently curving twig: bend turns it sideways, droop pulls it down."""
    pts = [p0]
    for i in range(1, n + 1):
        t = i / n
        a = ang + bend * t
        x, y = pts[-1]
        step = length / n
        pts.append((x + math.cos(a) * step, y + math.sin(a) * step - droop * step * t))
    return pts


def at(pts, f):
    f = max(0.0, min(1.0, f)) * (len(pts) - 1)
    i = min(int(f), len(pts) - 2)
    t = f - i
    return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t)


def heading(pts, f):
    a, b = at(pts, max(0.0, f - 0.03)), at(pts, min(1.0, f + 0.03))
    return math.atan2(b[1] - a[1], b[0] - a[0])


# leaf outlines along the leaf, 0 at the stalk and 1 at the tip
DELTOID = lambda t: min(t / 0.22, 1.0) ** 0.8 * (1 - t) ** 0.85    # birch: broad base, straight sides to a point
ROUND = lambda t: math.sin(math.pi * t) ** 0.55                       # aspen
OVAL = lambda t: math.sin(math.pi * min(t, 0.97)) ** 0.5               # alder, with a notched tip
LANCE = lambda t: math.sin(math.pi * t) ** 0.9                        # rowan leaflets

PINE_GREEN = ["#3B5A35", "#48683E", "#557548", "#5F7F4E", "#6B8A55"]
SPRUCE_GREEN = ["#1E3A25", "#25442C", "#2D5033", "#355A3A", "#3F6644"]
BIRCH_GREEN = ["#7DA03A", "#8BAE43", "#99BA4C", "#A9C659", "#B8CF66"]
ASPEN_GREEN = ["#7C9C43", "#8AAA4C", "#98B656", "#A7C062", "#BCC66C"]
ROWAN_GREEN = ["#4C7A2C", "#588634", "#64923C", "#71A045", "#7FAA4E"]
ALDER_GREEN = ["#33592A", "#3C6530", "#467238", "#517E40", "#5C884A"]


# ------------------------------------------------------------------ Scots pine
def pine(v):
    if v == 1:  # a round cluster of tufts on twigs
        c = Card(PINE_GREEN, 11)
        r = c.rng
        tufts = [(0.5, 0.5, 0.21)]
        for ring, (rad, n, length) in enumerate(((0.16, 6, 0.19), (0.3, 9, 0.15))):
            for k in range(n):
                a = k * TAU / n + ring * 0.35 + r.uniform(-0.2, 0.2)
                tufts.append((0.5 + rad * math.cos(a), 0.5 + rad * math.sin(a), length))
        for tx, ty, _ in tufts[1:]:
            c.twig([(0.5, 0.5), (tx, ty)], 0.01, "#7A4E2E")
        for i, (tx, ty, length) in enumerate(tufts):
            c.tuft((tx, ty), 80, length, None if i == 0 else 0.85, math.atan2(ty - 0.5, tx - 0.5))
    elif v == 2:  # one dense tuft filling the card: small round clumps for packing into patches
        c = Card(PINE_GREEN, 21)
        c.tuft((0.5, 0.5), 260, 0.44, width=0.007)
        c.tuft((0.5, 0.5), 90, 0.3, width=0.007, pal=["#6B8A55", "#7A9860"])
    elif v == 3:  # a twig with tufts along it
        c = Card(PINE_GREEN, 31)
        r = c.rng
        tw = curve_pts((0.12, 0.36), 0.35, 0.68, -0.3, 10)
        c.twig(tw, 0.012, "#7A4E2E")
        for f in (0.25, 0.42, 0.58, 0.74, 0.9, 1.0):
            p = at(tw, f)
            c.tuft(p, 70, r.uniform(0.15, 0.2), 0.9, heading(tw, f) + r.uniform(-0.4, 0.4))
    elif v == 4:  # sparse, long needles: an airy, light clump
        c = Card(["#55753F", "#62824A", "#6F8E54", "#7C9A5E"], 41)
        r = c.rng
        for k in range(4):
            a = k * TAU / 4 + 0.6
            p = (0.5 + 0.12 * math.cos(a), 0.5 + 0.12 * math.sin(a))
            c.twig([(0.5, 0.5), p], 0.009, "#7A4E2E")
            c.tuft(p, 45, r.uniform(0.27, 0.33), 0.9, a, width=0.0045)
    else:  # a packed pad of short tufts, darker inside: a painted look
        c = Card(PINE_GREEN, 51)
        r = c.rng
        pts = []
        while len(pts) < 26:
            p = (r.uniform(0.18, 0.82), r.uniform(0.25, 0.75))
            if ((p[0] - 0.5) / 0.34) ** 2 + ((p[1] - 0.5) / 0.26) ** 2 < 1:
                pts.append(p)
        for p in sorted(pts, key=lambda p: -abs(p[1] - 0.5)):
            inner = 1 - min(1.0, math.dist(p, (0.5, 0.5)) / 0.34)
            pal = ["#34522F", "#3F5E37"] if inner > 0.6 else None
            c.tuft(p, 60, r.uniform(0.09, 0.13), width=0.006, pal=pal)
    return c


# ------------------------------------------------------------------ Norway spruce
def spruce(v):
    c = Card(SPRUCE_GREEN, 12 + 10 * v)
    r = c.rng
    twigs = []
    if v == 1:  # a curtain of branchlets hanging from a twig
        main = curve_pts((0.06, 0.76), -0.04, 0.88, -0.1, 12)
        twigs.append(main)
        for k in range(9):
            f = 0.08 + 0.84 * k / 8
            twigs.append(curve_pts(at(main, f), -math.pi / 2 + r.uniform(-0.35, 0.35), r.uniform(0.38, 0.58) * (1.1 - 0.5 * abs(f - 0.5)), r.uniform(-0.3, 0.3), 8))
        for f in (0.15, 0.3, 0.45, 0.6, 0.75, 0.88):
            twigs.append(curve_pts(at(main, f), heading(main, f) + r.uniform(0.6, 0.9), r.uniform(0.12, 0.2), -0.3, 5))
    elif v == 2:  # a flat comb: side twigs both ways along a twig
        main = curve_pts((0.06, 0.5), 0.0, 0.88, -0.1, 12)
        twigs.append(main)
        for k, f in enumerate([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]):
            side = 1 if k % 2 else -1
            twigs.append(curve_pts(at(main, f), heading(main, f) + side * r.uniform(0.7, 0.95), r.uniform(0.2, 0.32) * (1.15 - f * 0.5), side * -0.3, 6))
    elif v == 3:  # a branch tip with shoots turning up
        main = curve_pts((0.06, 0.3), 0.15, 0.8, 0.5, 12)
        twigs.append(main)
        for f in (0.3, 0.45, 0.6, 0.75, 0.88):
            for side in (1, -1):
                twigs.append(curve_pts(at(main, f), heading(main, f) + side * 0.8, r.uniform(0.14, 0.22), side * 0.6, 6))
    elif v == 4:  # a dense mass seen from above
        for k in range(12):
            a = k * TAU / 12 + r.uniform(-0.15, 0.15)
            twigs.append(curve_pts((0.5, 0.5), a, r.uniform(0.3, 0.42), r.uniform(-0.4, 0.4), 8))
    else:  # a short, compact spray for small clumps
        main = curve_pts((0.2, 0.42), 0.25, 0.6, -0.2, 10)
        twigs.append(main)
        for f in (0.2, 0.35, 0.5, 0.65, 0.8):
            for side in (1, -1):
                twigs.append(curve_pts(at(main, f), heading(main, f) + side * 0.9, r.uniform(0.12, 0.18), side * -0.2, 5))
    for tw in twigs:
        c.twig(tw, 0.007, "#5A4030")
    for tw in twigs:
        c.needles_along(tw)
    return c


# ------------------------------------------------------------------ silver birch
def birch(v):
    pal = BIRCH_GREEN + (["#C9C25A", "#D4C467"] if v == 5 else [])
    c = Card(pal, 13 + 10 * v)
    r = c.rng
    if v == 3:  # a round cluster, no hanging strands
        for k in range(9):
            tw = curve_pts((0.5, 0.5), k * TAU / 9 + r.uniform(-0.15, 0.15), r.uniform(0.26, 0.34), r.uniform(-0.4, 0.4), 6)
            c.twig(tw, 0.0045, "#4A3B30")
            for j in range(6):
                f = 0.15 + 0.85 * j / 5
                c.leaf(at(tw, f), heading(tw, f) + (1 if j % 2 else -1) * r.uniform(0.45, 1.0), r.uniform(0.07, 0.095), r.uniform(0.048, 0.058), DELTOID, serr=0.12)
        return c
    strands = {1: 11, 2: 6, 4: 10, 5: 11}[v]
    for k in range(strands):
        x0 = 0.16 + 0.68 * k / (strands - 1) + r.uniform(-0.03, 0.03)
        tw = curve_pts((x0, r.uniform(0.82, 0.94)), -math.pi / 2 + r.uniform(-0.35, 0.35), r.uniform(0.6, 0.8), r.uniform(-0.4, 0.4), 10)
        c.twig(tw, 0.0045, "#4A3B30")
        n = r.randint(8, 11) if v != 2 else r.randint(10, 13)
        for j in range(n):
            f = 0.08 + 0.9 * j / n
            c.leaf(at(tw, f), heading(tw, f) + (1 if j % 2 else -1) * r.uniform(0.45, 1.0), r.uniform(0.06, 0.085), r.uniform(0.042, 0.052), DELTOID, serr=0.12)
        if v == 4 and k % 3 == 0:  # catkins hanging at the strand's end
            p = tw[-1]
            c.twig([p, (p[0] + r.uniform(-0.02, 0.02), p[1] - 0.09)], 0.016, r.choice(["#8E7A4A", "#A08A52"]))
    return c


# ------------------------------------------------------------------ aspen
def aspen(v):
    pal = {4: ["#C9B44E", "#D9C25A", "#B8A040", "#9EAA48", "#E0A84A"], 5: ASPEN_GREEN + ["#C8CDB8", "#B8BEA6"]}.get(v, ASPEN_GREEN)
    c = Card(pal, 14 + 10 * v)
    r = c.rng
    size = 0.7 if v == 3 else 1.0
    if v == 2 or v == 3:  # round clusters around the centre
        twigs = [curve_pts((0.5, 0.5), k * TAU / 7 + r.uniform(-0.2, 0.2), r.uniform(0.18, 0.28), r.uniform(-0.4, 0.4), 6) for k in range(7)]
        per = (5, 7) if v == 2 else (8, 10)
    else:
        twigs = [curve_pts((0.5, 0.3), math.radians(30 + 120 * k / 7) + r.uniform(-0.12, 0.12), r.uniform(0.27, 0.36), r.uniform(-0.3, 0.3), 8) for k in range(8)]
        per = (6, 8)
    for tw in twigs:
        c.twig(tw, 0.006, "#5E5A4A")
        n = r.randint(*per)
        for j in range(n):
            f = 0.2 + 0.8 * j / max(1, n - 1)
            p = at(tw, f)
            a = heading(tw, f) + (1 if j % 2 else -1) * r.uniform(0.6, 1.2)
            stalk = r.uniform(0.03, 0.045) * size
            q = (p[0] + math.cos(a) * stalk, p[1] + math.sin(a) * stalk)
            c.twig([p, q], 0.003, "#6E7A40")
            col = c.colour(["#C9C86E", "#B9B85E"]) if (v == 1 and r.random() < 0.15) else None
            c.leaf(q, a + r.uniform(-0.4, 0.4), r.uniform(0.09, 0.12) * size, r.uniform(0.085, 0.105) * size, ROUND, col)
    return c


# ------------------------------------------------------------------ rowan
def rowan(v, berries=False):
    pal = {4: ["#B8461E", "#C85A24", "#9A5A2A", "#7A8A34", "#D06A2A"], 5: ["#6E9A3C", "#7EAA46", "#8EB852", "#9CC25E"]}.get(v, ROWAN_GREEN)
    c = Card(pal, 15 + 10 * v)
    r = c.rng
    leaves, rach, leaflet = {1: (9, (0.3, 0.38), 1.0), 2: (5, (0.34, 0.42), 1.25), 3: (13, (0.26, 0.36), 0.95), 4: (9, (0.3, 0.38), 1.0), 5: (9, (0.24, 0.3), 0.8)}[v]
    for k in range(leaves):
        a = k * TAU / leaves + r.uniform(-0.15, 0.15)
        rc = curve_pts((0.5, 0.48), a, r.uniform(*rach), r.uniform(-0.25, 0.25), 8)
        c.twig(rc, 0.004, "#4E6B2E")
        for s in (0.2, 0.34, 0.48, 0.62, 0.76):
            h = heading(rc, s)
            for side in (1, -1):
                c.leaf(at(rc, s), h + side * r.uniform(0.95, 1.15), r.uniform(0.065, 0.085) * leaflet, r.uniform(0.019, 0.023) * leaflet, LANCE, serr=0.15)
        c.leaf(rc[-1], heading(rc, 1.0), r.uniform(0.07, 0.085) * leaflet, 0.021 * leaflet, LANCE, serr=0.15)
    if berries:
        for k in range(3):
            a = k * TAU / 3 + r.uniform(-0.4, 0.4)
            cx, cy = 0.5 + math.cos(a) * 0.12, 0.48 + math.sin(a) * 0.12
            pts = []
            for _ in range(r.randint(18, 26)):
                rr = 0.065 * math.sqrt(r.random())
                b = r.uniform(0, TAU)
                pts.append((cx + math.cos(b) * rr, cy + math.sin(b) * rr * 0.8))
            for p in pts[::3]:
                c.twig([(cx, cy - 0.05), p], 0.003, "#5A4A30")
            for p in sorted(pts, key=lambda p: p[1]):
                c.berry(p, r.uniform(0.016, 0.02), r.choice(["#B9281A", "#CC3520", "#DA4428", "#E05530"]), "#F08A60")
    return c


# ------------------------------------------------------------------ alder
def alder(v):
    pal = {5: ["#24461E", "#2C5226", "#355E2C", "#3F6A34"]}.get(v, ALDER_GREEN)
    c = Card(pal, 17 + 10 * v)
    r = c.rng
    size = 0.72 if v == 4 else 1.0
    if v == 2:
        twigs = [curve_pts((0.5, 0.5), k * TAU / 7 + r.uniform(-0.2, 0.2), r.uniform(0.2, 0.28), r.uniform(-0.3, 0.3), 6) for k in range(7)]
    else:
        twigs = [curve_pts((0.5, 0.32), math.radians(25 + 130 * k / 7) + r.uniform(-0.12, 0.12), r.uniform(0.25, 0.33), r.uniform(-0.3, 0.3), 8) for k in range(8)]
    for tw in twigs:
        c.twig(tw, 0.006, "#4A3E34")
        n = r.randint(5, 7) if v != 4 else r.randint(7, 9)
        for j in range(n):
            f = 0.2 + 0.8 * j / max(1, n - 1)
            p = at(tw, f)
            a = heading(tw, f) + (1 if j % 2 else -1) * r.uniform(0.6, 1.1)
            q = (p[0] + math.cos(a) * 0.02, p[1] + math.sin(a) * 0.02)
            c.twig([p, q], 0.003, "#4A5A34")
            c.leaf(q, a + r.uniform(-0.3, 0.3), r.uniform(0.11, 0.145) * size, r.uniform(0.095, 0.115) * size, OVAL, serr=0.08, notch=True)
    for tw in r.sample(twigs, 5 if v == 3 else 2):  # small cones near the twig tips; catkins too on design 3
        p = at(tw, 0.85)
        for k in range(3):
            a = r.uniform(0, TAU)
            q = (p[0] + math.cos(a) * 0.035, p[1] + math.sin(a) * 0.035)
            c.twig([p, q], 0.003, "#3E2C20")
            x, y = c.px(q)
            c.d.ellipse([x - 0.012 * N, y - 0.017 * N, x + 0.012 * N, y + 0.017 * N], fill=rgb(r.choice(["#3E2C20", "#4E3828"])) + (255,))
        if v == 3:
            c.twig([p, (p[0] + r.uniform(-0.03, 0.03), p[1] - 0.1)], 0.014, r.choice(["#7A5A3A", "#8A6A42"]))
    return c


# ------------------------------------------------------------------ truer aspen and alder leaves (designs 6-10)
def aspen_outline(t):
    """Nearly round with a short point, the edge gently wavy."""
    w = math.sin(math.pi * t) ** 0.62 * (1 - 0.3 * max(0.0, t - 0.78) / 0.22)
    return w * (1 + 0.045 * math.sin(t * 27)) if 0.08 < t < 0.95 else w


def alder_outline(t):
    """Broadest near the tip, which is notched; the teeth come in from the edge index in real_leaf."""
    return t ** 0.7 * (1 - min(t, 0.985)) ** 0.38


def inside(poly, p):
    """Whether point p lies inside the polygon (even-odd rule)."""
    x, y = p
    hit = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            hit = not hit
    return hit


def real_leaf(c, base, ang, length, width, kind, col, veins=True, stalk=0.0, samples=26):
    """A leaf with a true outline (kind "aspen" or "alder"), a stalk, light and dark halves split by the midrib, and
    veins. width is the half-width at the widest point. col is the leaf's colour at its depth: draw back leaves
    first, darker."""
    dx, dy = math.cos(ang), math.sin(ang)
    if stalk:
        tip = (base[0] + dx * stalk, base[1] + dy * stalk)
        c.twig([base, tip], 0.0032, shade(col, 0.7))
        base = tip
    px_, py_ = -dy, dx
    outline = aspen_outline if kind == "aspen" else alder_outline
    prof = [outline(i / samples) for i in range(samples + 1)]
    peak = max(prof)
    left, right, mid = [], [], []
    for i in range(samples + 1):
        t = i / samples
        mx, my = base[0] + dx * length * t, base[1] + dy * length * t
        w = width * prof[i] / peak
        if kind == "alder" and 0 < i < samples:  # double teeth: big and small ones in turn
            w *= 1 + 0.05 * (1 if i % 2 else -1) + 0.025 * (1 if (i // 2) % 2 else -1)
        if kind == "alder" and i == samples:
            mx, my = mx - dx * length * 0.07, my - dy * length * 0.07
        mid.append((mx, my))
        left.append((mx + px_ * w, my + py_ * w))
        right.append((mx - px_ * w, my - py_ * w))
    flip = c.rng.random() < 0.5
    c.d.polygon([c.px(p) for p in left + mid[::-1]], fill=shade(col, 1.06 if flip else 0.9) + (255,))
    c.d.polygon([c.px(p) for p in right + mid[::-1]], fill=shade(col, 0.9 if flip else 1.06) + (255,))
    if not veins:
        return
    vein = shade(col, 0.74)
    c.twig([mid[0], mid[int(samples * 0.93)]], 0.0026, vein)
    pairs, angle = (4, 0.95) if kind == "aspen" else (7, 0.78)
    for j in range(pairs):
        t = 0.16 + 0.7 * j / (pairs - 1)
        i = int(t * samples)
        for side, half in ((1, left + mid[::-1]), (-1, right + mid[::-1])):
            a = ang + side * angle
            step = length / 60
            n = 1
            while n < 60 and inside(half, (mid[i][0] + math.cos(a) * step * n, mid[i][1] + math.sin(a) * step * n)):
                n += 1
            reach = step * n * 0.82  # stop short of the edge
            c.twig([mid[i], (mid[i][0] + math.cos(a) * reach, mid[i][1] + math.sin(a) * reach)], 0.0017, vein)


def leafy_twig(c, kind, base_col, sizes, stalks, spacing=0.085, start=(0.08, 0.3), heading_=0.42, length=0.84, depth=(0.8, 1.08)):
    """One twig across the card with leaves on alternate sides, drawn back to front."""
    r = c.rng
    tw = curve_pts(start, heading_, length, r.uniform(-0.25, 0.25), 10)
    c.twig(tw, 0.007, "#5A4A3A")
    leaves = []
    n = int(length / spacing)
    for j in range(n):
        f = 0.08 + 0.9 * j / max(1, n - 1)
        side = 1 if j % 2 else -1
        leaves.append((r.uniform(*depth), at(tw, f), heading(tw, f) + side * r.uniform(0.7, 1.15)))
    for k in range(3):  # short side shoots with a couple of leaves each
        f = r.uniform(0.25, 0.8)
        sh = curve_pts(at(tw, f), heading(tw, f) + r.choice((-1, 1)) * 0.7, r.uniform(0.12, 0.18), 0.2, 4)
        c.twig(sh, 0.005, "#5A4A3A")
        for g in (0.6, 1.0):
            leaves.append((r.uniform(*depth), at(sh, g), heading(sh, g) + r.uniform(-0.8, 0.8)))
    for d, p, a in sorted(leaves):
        L = r.uniform(*sizes)
        real_leaf(c, p, a, L, L * (0.48 if kind == "aspen" else 0.4), kind, shade(base_col, d * r.uniform(0.97, 1.03)), stalk=r.uniform(*stalks))


def fan_cluster(c, kind, base_col, sizes, stalks, twigs=6, per=(3, 4)):
    r = c.rng
    leaves = []
    for k in range(twigs):
        tw = curve_pts((0.5, 0.26), math.radians(28 + 124 * k / (twigs - 1)) + r.uniform(-0.1, 0.1), r.uniform(0.22, 0.3), r.uniform(-0.3, 0.3), 6)
        c.twig(tw, 0.006, "#5A4A3A")
        n = r.randint(*per)
        for j in range(n):
            f = 0.35 + 0.65 * j / max(1, n - 1)
            leaves.append((r.uniform(0.78, 1.1), at(tw, f), heading(tw, f) + (1 if j % 2 else -1) * r.uniform(0.4, 0.9)))
    for d, p, a in sorted(leaves):
        L = r.uniform(*sizes)
        real_leaf(c, p, a, L, L * (0.48 if kind == "aspen" else 0.4), kind, shade(base_col, d), stalk=r.uniform(*stalks))


def painted_mass(c, kind, dark, mid, light):
    """A solid mass of foliage: a silhouette of leaves in the shadow colour, lit leaves over its upper side, and a few
    highlights along the top. Reads as one clump rather than as separate leaves."""
    r = c.rng
    pts = []
    while len(pts) < 46:
        p = (r.uniform(0.14, 0.86), r.uniform(0.16, 0.84))
        if ((p[0] - 0.5) / 0.34) ** 2 + ((p[1] - 0.5) / 0.3) ** 2 < 1:
            pts.append(p)
    ratio = 0.48 if kind == "aspen" else 0.4
    for p in pts:
        L = r.uniform(0.11, 0.14)
        real_leaf(c, p, r.uniform(0, TAU), L, L * ratio, kind, rgb(dark), veins=False)
    for p in sorted(pts, key=lambda p: p[1])[len(pts) // 3:]:  # the upper two-thirds catch the light
        L = r.uniform(0.09, 0.12)
        real_leaf(c, (p[0] + r.uniform(-0.01, 0.01), p[1] + 0.01), r.uniform(0, TAU), L, L * ratio, kind,
                  shade(rgb(mid), r.uniform(0.95, 1.08)))
    for p in sorted(pts, key=lambda p: -p[1])[:6]:
        L = r.uniform(0.08, 0.1)
        real_leaf(c, p, r.uniform(0.6, 2.5), L, L * ratio, kind, rgb(light))


def hanging_leaves(c, base_col, under):
    """Aspen leaves trembling on long, flat stalks below a twig; some turn their pale undersides out."""
    r = c.rng
    tw = curve_pts((0.06, 0.82), -0.1, 0.88, r.uniform(-0.2, 0.2), 10)
    c.twig(tw, 0.007, "#5A4A3A")
    leaves = []
    for j in range(14):
        f = 0.05 + 0.9 * j / 13
        p = at(tw, f)
        a = -math.pi / 2 + r.uniform(-0.7, 0.7)
        leaves.append((r.uniform(0.8, 1.08), p, a, r.uniform(0.05, 0.11)))
    for d, p, a, stalk in sorted(leaves):
        L = r.uniform(0.14, 0.18)
        col = shade(rgb(under), d) if r.random() < 0.25 else shade(base_col, d)
        real_leaf(c, p, a + r.uniform(-0.5, 0.5), L, L * 0.48, "aspen", col, stalk=stalk)


def aspen_more(v):
    c = Card(ASPEN_GREEN, 100 + v)
    green = rgb("#7FA046")
    if v == 6:
        leafy_twig(c, "aspen", green, (0.13, 0.17), (0.04, 0.06))
    elif v == 7:
        fan_cluster(c, "aspen", green, (0.13, 0.16), (0.03, 0.05))
    elif v == 8:
        painted_mass(c, "aspen", "#4E6E32", "#7FA046", "#A9C266")
    elif v == 9:  # lit from behind: yellow-green, with the veins showing dark
        leafy_twig(c, "aspen", rgb("#A3BE5C"), (0.13, 0.17), (0.04, 0.06), depth=(0.88, 1.1))
    else:
        hanging_leaves(c, green, "#B9C2A4")
    return c


def alder_more(v):
    c = Card(ALDER_GREEN, 200 + v)
    green = rgb("#41702F")
    if v == 6:
        leafy_twig(c, "alder", green, (0.15, 0.19), (0.015, 0.03))
    elif v == 7:
        fan_cluster(c, "alder", green, (0.15, 0.18), (0.015, 0.025))
    elif v == 8:
        painted_mass(c, "alder", "#264520", "#3E6B2E", "#5E8A44")
    elif v == 9:  # a leafy twig with cones and catkins
        leafy_twig(c, "alder", green, (0.14, 0.17), (0.015, 0.03), spacing=0.1)
        r = c.rng
        for cx, cy in ((0.62, 0.3), (0.32, 0.68)):
            for k in range(3):
                q = (cx + r.uniform(-0.03, 0.03), cy + r.uniform(-0.03, 0.03))
                x, y = c.px(q)
                c.d.ellipse([x - 0.014 * N, y - 0.02 * N, x + 0.014 * N, y + 0.02 * N], fill=rgb(r.choice(["#3E2C20", "#4E3828"])) + (255,))
            c.twig([(cx, cy), (cx + r.uniform(-0.03, 0.03), cy - 0.12)], 0.014, "#7A5A3A")
    else:  # big, dark leaves in the shade of the crown
        leafy_twig(c, "alder", rgb("#355F28"), (0.19, 0.23), (0.015, 0.03), spacing=0.12, depth=(0.75, 1.0))
    return c


SPECIES = {"pine": pine, "spruce": spruce, "birch": birch, "aspen": aspen, "rowan": rowan, "alder": alder}
MORE = {"aspen": aspen_more, "alder": alder_more}  # designs 6 to 10
NAMES = {  # what each design is called in the editor
    "pine": ["Tuft cluster", "Single tuft", "Twig with tufts", "Long, sparse needles", "Packed pad"],
    "spruce": ["Hanging curtain", "Flat comb", "Upturned tip", "Dense mass", "Short spray"],
    "birch": ["Hanging twigs", "Sparse strands", "Round cluster", "With catkins", "Late summer"],
    "aspen": ["Twig fan", "Round cluster", "Small leaves", "Autumn", "Pale undersides",
              "Leafy twig", "Toothed cluster", "Painted mass", "Sunlit", "Trembling"],
    "rowan": ["Radial", "Few, large leaves", "Dense", "Autumn", "Young, light"],
    "alder": ["Twig fan", "Round cluster", "Cones and catkins", "Small leaves", "Deep green",
              "Leafy twig", "Veined cluster", "Painted mass", "Twig with cones", "Shade leaves"],
}
# where each spray card's twig starts on the card, and which way it runs (degrees), for sprays set along a branch
ANCHORS = {"spruce_1": [0.06, 0.76, -2], "spruce_2": [0.06, 0.5, 0], "spruce_3": [0.06, 0.3, 9], "spruce_4": [0.5, 0.5, 0],
           "spruce_5": [0.2, 0.42, 14]}

if __name__ == "__main__":
    made = {}
    for sp, names in NAMES.items():
        for v in range(1, len(names) + 1):
            fn = SPECIES[sp] if v <= 5 else MORE[sp]
            made[(sp, v)] = fn(v).save(f"{sp}_{v}")
            if sp == "rowan":
                rowan(v, berries=True).save(f"rowan_{v}_berries")
    # a contact sheet: one row per species
    tile, pad, label_w = 170, 14, 150
    cols = max(len(n) for n in NAMES.values())
    sheet = Image.new("RGB", (label_w + cols * (tile + pad) + pad, len(NAMES) * (tile + pad + 26) + pad), (236, 232, 222))
    dr = ImageDraw.Draw(sheet)
    try:
        big, small = (ImageFont.truetype(os.path.join(HERE, "..", "..", "mockups", "fonts", "Cinzel.ttf"), s) for s in (24, 13))
    except OSError:
        big = small = ImageFont.load_default()
    for row, sp in enumerate(NAMES):
        y = pad + row * (tile + pad + 26)
        dr.text((pad, y + tile / 2), sp.capitalize(), fill=(60, 52, 40), font=big, anchor="lm")
        for v in range(1, len(NAMES[sp]) + 1):
            x = label_w + pad + (v - 1) * (tile + pad)
            img = made[(sp, v)].resize((tile, tile), Image.LANCZOS)
            sheet.paste(img, (x, y), img)
            dr.text((x + tile / 2, y + tile + 4), f"{v}  {NAMES[sp][v - 1]}", fill=(90, 80, 64), font=small, anchor="mt")
    os.makedirs(os.path.join(HERE, "previews"), exist_ok=True)
    sheet.save(os.path.join(HERE, "previews", "leaf_cards.png"))
    with open(os.path.join(OUT, "cards.json"), "w") as fh:  # the design names and spray anchors, for the tree editor
        json.dump({"names": NAMES, "anchors": ANCHORS}, fh, indent=1)
    print("wrote", len(made), "cards (and 5 rowan berry versions) to", OUT)
