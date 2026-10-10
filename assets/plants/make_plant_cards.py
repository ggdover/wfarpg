"""Cards for the plant portfolio: four designs per plant, each a texture with a transparent background, drawn in the
tree cards' style (../trees/make_leaf_cards.py): leaves as two flat halves, one lighter and one darker, crisp edges.

    python3 make_plant_cards.py     writes textures/<plant>_<1-4>.png (512 x 512), their berry, flower or nut versions
                                    (<plant>_<n>_<extra>.png), textures/cards.json and previews/cards.png

The bushes' cards are a sprig or a cluster of leaves round the card's centre: plantgen.py crosses several copies at a
clump's centre, as the trees do. The grasses' and the fern's grow from the middle of the card's foot, (0.5, 0.02),
as a tuft or a frond stands on the ground; the long grass's thin strands stand in a row all along it, a strip of
grass, so crossed copies make a patch. A bush's extra version is the same card with its berries, flowers or nuts
drawn on, and the bush mixes the two (the editor's share of them); a grass's is a card of flowering stalks alone, which
stands taller among its tufts. The transparent pixels
carry the card's average colour, so filtered edges don't get dark fringes.
"""
import json
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "trees"))
from make_leaf_cards import Card, at, curve_pts, heading, inside, rgb, shade  # noqa: E402

OUT = os.path.join(HERE, "textures")
SIZE = 512
TAU = math.tau
FOOT = (0.5, 0.02)  # where a tuft or frond grows from on its card


# ------------------------------------------------------------------ shapes
OVATE = lambda t: min(t / 0.3, 1.0) ** 0.7 * (1 - t) ** 0.75             # raspberry leaflets: broad base, pointed
BLADE = lambda t: min(1.0, 0.55 + t / 0.12 * 0.45) * (1 - t) ** 0.85     # a grass blade: narrow foot, long taper
PINNULE = lambda t: math.sin(math.pi * t) ** 0.7


def veined_leaf(c, base, ang, length, width, outline, col, pairs=6, vein_angle=0.75, teeth=0.0, stalk=0.0,
                samples=24, veins=True):
    """A leaf with its outline, a stalk, light and dark halves split by the midrib, and veins; teeth > 0 toothes the
    edge, big and small teeth in turn. width is the half-width at the widest point."""
    dx, dy = math.cos(ang), math.sin(ang)
    if stalk:
        tip = (base[0] + dx * stalk, base[1] + dy * stalk)
        c.twig([base, tip], 0.0032, shade(col, 0.7))
        base = tip
    px_, py_ = -dy, dx
    prof = [outline(i / samples) for i in range(samples + 1)]
    peak = max(prof) or 1.0
    left, right, mid = [], [], []
    for i in range(samples + 1):
        t = i / samples
        mx, my = base[0] + dx * length * t, base[1] + dy * length * t
        w = width * prof[i] / peak
        if teeth and 0 < i < samples:
            w *= 1 + teeth * (1 if i % 2 else -1) + teeth * 0.5 * (1 if (i // 2) % 2 else -1)
        mid.append((mx, my))
        left.append((mx + px_ * w, my + py_ * w))
        right.append((mx - px_ * w, my - py_ * w))
    flip = c.rng.random() < 0.5
    c.d.polygon([c.px(p) for p in left + mid[::-1]], fill=shade(col, 1.07 if flip else 0.88) + (255,))
    c.d.polygon([c.px(p) for p in right + mid[::-1]], fill=shade(col, 0.88 if flip else 1.07) + (255,))
    if not veins:
        return
    vein = shade(col, 0.74)
    c.twig([mid[0], mid[int(samples * 0.93)]], 0.0024, vein)
    for j in range(pairs):
        t = 0.14 + 0.72 * j / max(1, pairs - 1)
        i = int(t * samples)
        for side, half in ((1, left + mid[::-1]), (-1, right + mid[::-1])):
            a = ang + side * vein_angle
            step = length / 60
            n = 1
            while n < 60 and inside(half, (mid[i][0] + math.cos(a) * step * n, mid[i][1] + math.sin(a) * step * n)):
                n += 1
            reach = step * n * 0.8
            c.twig([mid[i], (mid[i][0] + math.cos(a) * reach, mid[i][1] + math.sin(a) * reach)], 0.0016, vein)


def wavy(p0, ang, length, bend, wave, n=14, phase=0.0, droop=0.0):
    """Points along a hair-thin blade: bending as curve_pts, with a wave across it."""
    pts = curve_pts(p0, ang, length, bend, n, droop)
    out = []
    for i, (x, y) in enumerate(pts):
        t = i / n
        h = ang + bend * t
        s = wave * length * math.sin(t * 9.0 + phase) * t
        out.append((x - math.sin(h) * s, y + math.cos(h) * s))
    return out


def blade(c, base, ang, length, width, curve, col, droop=0.0):
    """A grass blade from base: tapering to a point, curving sideways (curve) and hanging (droop), folded along its
    midrib, one half lighter. Drawn as a leaf with the blade's outline."""
    dx, dy = math.cos(ang), math.sin(ang)
    px_, py_ = -dy, dx
    n = 18
    left, right, mid = [], [], []
    for i in range(n + 1):
        t = i / n
        bend = curve * length * t * t
        mx = base[0] + dx * length * t + px_ * bend
        my = base[1] + dy * length * t + py_ * bend - droop * length * t ** 2.2
        w = width * BLADE(t)
        mid.append((mx, my))
        left.append((mx + px_ * w, my + py_ * w))
        right.append((mx - px_ * w, my - py_ * w))
    light, dark = (shade(col, 1.08), shade(col, 0.84)) if c.rng.random() < 0.5 else (shade(col, 0.84), shade(col, 1.08))
    c.d.polygon([c.px(p) for p in left + mid[::-1]], fill=light + (255,))
    c.d.polygon([c.px(p) for p in right + mid[::-1]], fill=dark + (255,))
    return mid


def lens(c, p, ang, length, width, col):
    """A lens in one colour, with a lighter half: a seed head or a flower bud."""
    dx, dy = math.cos(ang), math.sin(ang)
    px_, py_ = -dy, dx
    n = 8
    left, right = [], []
    for i in range(n + 1):
        t = i / n
        w = width * math.sin(math.pi * t) ** 0.8
        mx, my = p[0] + dx * length * t, p[1] + dy * length * t
        left.append((mx + px_ * w, my + py_ * w))
        right.append((mx - px_ * w, my - py_ * w))
    c.d.polygon([c.px(q) for q in left + right[::-1]], fill=col + (255,))
    c.d.polygon([c.px(q) for q in left], fill=shade(col, 1.15) + (255,)) if len(left) > 2 else None


def dot(c, p, r, col, hi=None):
    x, y = c.px(p)
    rr = r * c.img.width
    c.d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=col + (255,))
    if hi:
        h = rr * 0.4
        c.d.ellipse([x - rr * 0.4 - h, y - rr * 0.4 - h, x - rr * 0.4 + h, y - rr * 0.4 + h], fill=hi + (255,))


def spread_points(r, n, cx, cy, rx, ry, gap):
    """n points in an ellipse, kept gap apart where there's room."""
    pts = []
    tries = 0
    while len(pts) < n and tries < n * 60:
        tries += 1
        p = (cx + r.uniform(-rx, rx), cy + r.uniform(-ry, ry))
        if ((p[0] - cx) / rx) ** 2 + ((p[1] - cy) / ry) ** 2 > 1:
            continue
        if all(math.dist(p, q) > gap for q in pts) or tries > n * 40:
            pts.append(p)
    return pts


class Plant(Card):
    """A card, and the spots its extra version draws its berries, flowers or nuts on, with their own random numbers so
    the card itself stays the same."""

    def __init__(self, palette, seed):
        super().__init__(palette, seed)
        self.spots = []  # (point, heading) where the extras go
        self.xr = random.Random(seed * 31 + 7)
        self.fit = None  # "top" or "box": crop the card to what's drawn on it (save)


# ------------------------------------------------------------------ raspberry
RASPBERRY = ["#4F7E30", "#5B8A38", "#679642", "#74A04C"]
UNDERSIDE = ["#B9C6A8", "#C6D0B8", "#AEBC9C"]


def raspberry(v, extra=False):
    """Compound leaves of three or five toothed, pointed leaflets, some turned to show their pale undersides; the berries
    red, of many small rounded drupelets, hanging."""
    pal = {4: ["#6E9A3C", "#7CA646", "#8AB250", "#97BC5C"]}.get(v, RASPBERRY)
    c = Plant(pal, 600 + v)
    r = c.rng
    pale = {3: 0.3}.get(v, 0.1)
    if v == 2:  # an arching cane tip with leaves along it
        cane = curve_pts((0.08, 0.3), 0.75, 0.95, -1.3, 14)
        c.twig(cane, 0.012, "#7A4A3A")
        stalks = [(at(cane, f), heading(cane, f) + (1 if k % 2 else -1) * r.uniform(0.6, 1.0), r.uniform(0.85, 1.0))
                  for k, f in enumerate((0.2, 0.32, 0.44, 0.56, 0.68, 0.8, 0.92))]
        for k in range(3):
            c.spots.append((at(cane, 0.3 + 0.25 * k), -math.pi / 2))
    else:  # leaves on long stalks from a stem across the card's middle
        stem = curve_pts((0.3, 0.2), 1.1, 0.6, r.uniform(-0.3, 0.3), 8)
        c.twig(stem, 0.01, "#7A4A3A")
        stalks = [(at(stem, f), heading(stem, f) + (1 if k % 2 else -1) * r.uniform(0.7, 1.2), r.uniform(1.25, 1.5))
                  for k, f in enumerate((0.15, 0.4, 0.62, 0.85))] + [(stem[-1], heading(stem, 1.0), 1.4)]
    for p, a, s in stalks:
        L = 0.13 * s
        tip = (p[0] + math.cos(a) * L, p[1] + math.sin(a) * L)
        c.twig([p, tip], 0.005, "#6A7A40")
        c.spots.append((at([p, tip], 0.4), a))
        five = r.random() < 0.35
        leaflets = [(tip, a, 1.0)] + [(tip, a + side * 1.25, 0.8) for side in (1, -1)]
        if five:
            back = (p[0] + math.cos(a) * L * 0.6, p[1] + math.sin(a) * L * 0.6)
            leaflets += [(back, a + side * 1.55, 0.65) for side in (1, -1)]
        for q, b, f in sorted(leaflets, key=lambda x: x[2]):
            col = c.colour(UNDERSIDE) if r.random() < pale else c.colour()
            veined_leaf(c, q, b + r.uniform(-0.15, 0.15), 0.15 * f * s, 0.06 * f * s, OVATE, col, pairs=6, vein_angle=0.7,
                        teeth=0.07, stalk=0.006)
    if extra:
        xr = c.xr
        for p, a in xr.sample(c.spots, min(len(c.spots), 4)):
            q = (p[0] + xr.uniform(-0.03, 0.03), p[1] - xr.uniform(0.04, 0.07))
            c.twig([p, q], 0.003, "#6A7A40")
            for i in range(16):  # drupelets, back to front
                b = xr.uniform(0, TAU)
                rr = 0.022 * math.sqrt(xr.random())
                dot(c, (q[0] + math.cos(b) * rr, q[1] - 0.008 + math.sin(b) * rr * 1.25), 0.009,
                    xr.choice([rgb("#B8283C"), rgb("#CC3448"), rgb("#A82034")]), rgb("#F08898"))
    return c


# ------------------------------------------------------------------ alder buckthorn
BUCKTHORN = ["#2E5A26", "#36662C", "#3F7234", "#487C3C"]


def buckthorn_outline(t):
    """Broad oval with a short point, the edge smooth."""
    return math.sin(math.pi * min(t, 0.98)) ** 0.6 * (1 - 0.35 * max(0.0, t - 0.8) / 0.2)


def leafy_twigs(c, kind, start, heading_, length, sizes, depth=(0.8, 1.08), spacing=0.085):
    """A twig across the card with leaves on alternate sides and short side shoots, drawn back to front."""
    r = c.rng
    tw = curve_pts(start, heading_, length, r.uniform(-0.25, 0.25), 10)
    c.twig(tw, 0.007, "#5A4A3A")
    leaves = []
    n = int(length / spacing)
    for j in range(n):
        f = 0.08 + 0.9 * j / max(1, n - 1)
        side = 1 if j % 2 else -1
        leaves.append((r.uniform(*depth), at(tw, f), heading(tw, f) + side * r.uniform(0.7, 1.15)))
        c.spots.append((at(tw, f), heading(tw, f)))
    for k in range(3):
        f = r.uniform(0.25, 0.8)
        sh = curve_pts(at(tw, f), heading(tw, f) + r.choice((-1, 1)) * 0.7, r.uniform(0.12, 0.18), 0.2, 4)
        c.twig(sh, 0.005, "#5A4A3A")
        for g in (0.6, 1.0):
            leaves.append((r.uniform(*depth), at(sh, g), heading(sh, g) + r.uniform(-0.8, 0.8)))
    for d, p, a in sorted(leaves):
        draw_leaf(c, kind, p, a, r.uniform(*sizes), d)


def fan(c, kind, sizes, twigs=7, per=(3, 4), centre=(0.5, 0.26)):
    r = c.rng
    leaves = []
    for k in range(twigs):
        tw = curve_pts(centre, math.radians(25 + 130 * k / (twigs - 1)) + r.uniform(-0.1, 0.1), r.uniform(0.22, 0.3), r.uniform(-0.3, 0.3), 6)
        c.twig(tw, 0.006, "#5A4A3A")
        n = r.randint(*per)
        for j in range(n):
            f = 0.35 + 0.65 * j / max(1, n - 1)
            leaves.append((r.uniform(0.78, 1.1), at(tw, f), heading(tw, f) + (1 if j % 2 else -1) * r.uniform(0.4, 0.9)))
            c.spots.append((at(tw, f), heading(tw, f)))
    for d, p, a in sorted(leaves):
        draw_leaf(c, kind, p, a, r.uniform(*sizes), d)


def mass(c, kind, dark, mid, light):
    """A solid mass of foliage: leaves in the shadow colour, lit ones over its upper side, a few highlights on top."""
    r = c.rng
    pts = spread_points(r, 44, 0.5, 0.5, 0.34, 0.3, 0.05)
    for p in pts:
        draw_leaf(c, kind, p, r.uniform(0, TAU), r.uniform(0.11, 0.14), 1.0, rgb(dark), veins=False)
        c.spots.append((p, r.uniform(0, TAU)))
    for p in sorted(pts, key=lambda p: p[1])[len(pts) // 3:]:
        draw_leaf(c, kind, (p[0] + r.uniform(-0.01, 0.01), p[1] + 0.01), r.uniform(0, TAU), r.uniform(0.09, 0.12), r.uniform(0.95, 1.08), rgb(mid))
    for p in sorted(pts, key=lambda p: -p[1])[:6]:
        draw_leaf(c, kind, p, r.uniform(0.6, 2.5), r.uniform(0.08, 0.1), 1.0, rgb(light))


def draw_leaf(c, kind, p, a, L, depth, col=None, veins=True):
    col = shade(col or c.colour(), depth)
    if kind == "buckthorn":  # smooth edge, veins curving up toward the tip
        veined_leaf(c, p, a, L, L * 0.34, buckthorn_outline, col, pairs=7, vein_angle=0.55, stalk=0.012, veins=veins)
    else:  # hazel: round, short-pointed, double-toothed
        veined_leaf(c, p, a, L, L * 0.44, hazel_outline, col, pairs=6, vein_angle=0.7, teeth=0.06, stalk=0.01, veins=veins)


def buckthorn(v, extra=False):
    """Oval, glossy leaves with smooth edges and curving veins; the berries in small groups by the leaves, green, red
    and black at once."""
    pal = {4: ["#D8A030", "#C87828", "#B85A24", "#E0B848", "#9A8A2E"]}.get(v, BUCKTHORN)
    c = Plant(pal, 700 + v)
    if v == 1:
        leafy_twigs(c, "buckthorn", (0.08, 0.3), 0.42, 0.84, (0.13, 0.16))
    elif v == 2:
        fan(c, "buckthorn", (0.12, 0.15))
    elif v == 3:
        mass(c, "buckthorn", "#22441C", "#36662C", "#5A8A44")
    else:
        leafy_twigs(c, "buckthorn", (0.08, 0.3), 0.42, 0.84, (0.13, 0.16))
    if extra:
        xr = c.xr
        for p, h in xr.sample(c.spots, min(len(c.spots), 6)):
            for _ in range(xr.randint(2, 4)):
                q = (p[0] + xr.uniform(-0.025, 0.025), p[1] - xr.uniform(0.01, 0.035))
                c.twig([p, q], 0.0025, "#4A5A34")
                dot(c, q, xr.uniform(0.012, 0.015), rgb(xr.choice(["#1E1A1E", "#1E1A1E", "#C8282A", "#B82424", "#7A9A3A"])), rgb("#E8A090"))
    return c


# ------------------------------------------------------------------ hazel
HAZEL = ["#4F7A30", "#5A8638", "#659240", "#719C48"]


def hazel_outline(t):
    """Nearly round, broadest past the middle, a heart-shaped foot and a short, sudden point."""
    w = math.sin(math.pi * min(t, 0.9) / 0.9) ** 0.5 if t < 0.9 else 0.0
    return max(w, 0.0) * (1 - 0.6 * max(0.0, t - 0.82) / 0.18) + (0.05 if 0.88 < t < 0.98 else 0.0)


def hazel(v, extra=False):
    """Broad, round, double-toothed leaves with a short point; the nuts in twos and threes in frilled green husks."""
    pal = {4: ["#C8B040", "#D4BE50", "#B89A38", "#A8A040", "#C89A38"]}.get(v, HAZEL)
    c = Plant(pal, 800 + v)
    if v == 1:
        leafy_twigs(c, "hazel", (0.08, 0.3), 0.42, 0.84, (0.15, 0.19), spacing=0.1)
    elif v == 2:
        fan(c, "hazel", (0.14, 0.17), twigs=6)
    elif v == 3:
        mass(c, "hazel", "#3A5E24", "#5A8638", "#86AE58")
    else:
        leafy_twigs(c, "hazel", (0.08, 0.3), 0.42, 0.84, (0.15, 0.19), spacing=0.1)
    if extra:
        xr = c.xr
        for p, h in xr.sample(c.spots, min(len(c.spots), 3)):
            for k in range(xr.randint(2, 3)):
                b = h + (k - 1) * 0.7 + xr.uniform(-0.2, 0.2)
                q = (p[0] + math.cos(b) * 0.03, p[1] + math.sin(b) * 0.03)
                for j in range(7):  # the husk: a frill of ragged lobes
                    lens(c, q, b + (j - 3) * 0.35, 0.05, 0.012, rgb(xr.choice(["#7A9A44", "#8AA84E", "#6A8A3C"])))
                dot(c, (q[0] + math.cos(b) * 0.012, q[1] + math.sin(b) * 0.012), 0.016, rgb(xr.choice(["#9A7A48", "#8A6A3A", "#A88A52"])), rgb("#C8AA78"))
    return c


# ------------------------------------------------------------------ fern
FERN = ["#4C7E2E", "#588A36", "#64963E", "#72A248"]


def fern(v, extra=False):
    """A frond from the card's foot to its top: pinnae in pairs along the stalk, longest a third of the way up, each
    with small rounded pinnules; the fronds of a fern stand in a ring."""
    pal = {3: ["#7AAE44", "#88B850", "#96C25C"], 4: ["#A8743A", "#B88446", "#986432", "#8A7A3A"]}.get(v, FERN)
    c = Plant(pal, 900 + v)
    r = c.rng
    broad = 1.3 if v == 2 else 1.0
    rach = curve_pts(FOOT, math.pi / 2, 0.95, r.uniform(-0.15, 0.15), 16)
    c.twig(rach, 0.008, "#5E7A34" if v != 4 else "#7A5A30")
    n = 15
    for j in range(n):
        f = 0.12 + 0.86 * j / n
        p, h = at(rach, f), heading(rach, f)
        reach = 0.3 * broad * (min(1.0, (f - 0.05) / 0.3) ** 0.7) * (1 - f) ** 0.6 + 0.02
        for side in (1, -1):
            a = h + side * r.uniform(1.05, 1.25)
            pin = curve_pts(p, a, reach, side * -0.35, 8)
            c.twig(pin, 0.004, "#5E7A34" if v != 4 else "#7A5A30")
            m = max(2, int(reach / 0.022))
            for k in range(m):
                g = 0.1 + 0.9 * k / m
                q, hh = at(pin, g), heading(pin, g)
                for s2 in (1, -1):
                    c.leaf(q, hh + s2 * 1.0, 0.03 * (1.15 - g * 0.6) * broad, 0.011 * broad, PINNULE, c.colour())
            c.leaf(pin[-1], heading(pin, 1.0), 0.026, 0.009, PINNULE, c.colour())
    return c


# ------------------------------------------------------------------ the grasses
def tuft(c, blades, length, width, spread, curve, droop, wide=0.12):
    """Blades fanning up from the card's foot, back to front; returns their tips."""
    r = c.rng
    tips = []
    order = sorted(range(blades), key=lambda i: r.random())
    for i in order:
        a = math.pi / 2 + r.gauss(0, spread)
        base = (FOOT[0] + r.uniform(-wide, wide) * 0.5, FOOT[1] + r.uniform(0, 0.02))
        L = length * r.uniform(0.6, 1.0)
        side = 1 if a < math.pi / 2 else -1
        mid = blade(c, base, a, L, width * r.uniform(0.8, 1.1), side * -abs(r.gauss(curve, curve * 0.5)), c.colour(),
                    droop * r.uniform(0.5, 1.2))
        tips.append(mid[-1])
    return tips


def hairs(c, n, length, spread, wave, width=0.009, wide=0.1):
    """Hair-thin blades, curling: wavy hair-grass, cottongrass."""
    r = c.rng
    for _ in range(n):
        a = math.pi / 2 + r.gauss(0, spread)
        base = (FOOT[0] + r.uniform(-wide, wide) * 0.5, FOOT[1])
        pts = wavy(base, a, length * r.uniform(0.55, 1.0), (math.pi / 2 - a) * -0.8, wave * r.uniform(0.5, 1.3), 14,
                   r.uniform(0, TAU), droop=0.3)
        c.twig(pts, width * r.uniform(0.8, 1.2), c.colour())


def stalk(c, r, height, lean, col, width=0.006):
    """A flowering stalk from the foot, nearly straight."""
    base = (FOOT[0] + r.uniform(-0.05, 0.05), FOOT[1])
    pts = curve_pts(base, math.pi / 2 + lean, height, r.uniform(-0.15, 0.15), 10)
    c.twig(pts, width, col)
    return pts


def panicle(c, r, pts, start, cols, branches=7, reach=0.12, airy=True, size=1.0):
    """An open panicle over the stalk's top part: thin branches, spikelets along and at their ends."""
    for k in range(branches):
        f = start + (1 - start) * k / branches
        p, h = at(pts, f), heading(pts, f)
        side = 1 if k % 2 else -1
        L = reach * (1.15 - (f - start) / (1 - start)) * r.uniform(0.7, 1.0)
        br = curve_pts(p, h + side * r.uniform(0.3, 0.6 if airy else 0.25), L, -side * 0.25, 5)
        c.twig(br, 0.004, shade(rgb(cols[0]), 0.8))
        for g in (0.35, 0.6, 0.8, 1.0) if airy else (0.3, 0.5, 0.7, 0.85, 1.0):
            q = at(br, g)
            lens(c, q, heading(br, g) + r.uniform(-0.3, 0.3), 0.026 * size, 0.008 * size, rgb(r.choice(cols)))
    lens(c, pts[-1], heading(pts, 1.0), 0.026 * size, 0.006 * size, rgb(r.choice(cols)))


def spike(c, r, pts, start, cols, width=0.008, size=1.0):
    """A narrow, dense flower head along the stalk's top part."""
    n = int((1 - start) * 60)
    for k in range(n):
        f = start + (1 - start) * k / n
        p, h = at(pts, f), heading(pts, f)
        side = 1 if k % 2 else -1
        lens(c, (p[0] + math.cos(h + side * 1.57) * width * 0.4, p[1] + math.sin(h + side * 1.57) * width * 0.4),
             h + side * 0.35, 0.03 * size, width * 0.6 * size, rgb(r.choice(cols)))


def flowers(c, n, height, lean, stem, head, **kw):
    """A grass's flower card: n stalks from the foot, up to height, each carrying head(c, r, pts, **kw)."""
    for k in range(n):
        pts = stalk(c, c.rng, height * c.rng.uniform(0.82, 1.0), c.rng.gauss(0, lean), stem, kw.pop("width", 0.006) if k == 0 else 0.006)
        head(c, c.rng, pts, **kw)


HAIRGRASS = ["#6E9640", "#7AA248", "#87AE52", "#95B85C"]


def hairgrass(v, extra=False):
    """Wavy hair-grass (kruståtel), the pine forest's grass: a tuft of hair-thin, curling blades; its flowers airy,
    purple-silver panicles on thin stalks."""
    pal = {3: ["#B8A660", "#C8B670", "#A89850", "#9AA055"], 4: ["#5E8A38", "#6A9440", "#78A048"]}.get(v, HAIRGRASS)
    c = Plant(pal, 1000 + v)
    if extra:
        flowers(c, 5, 0.95, 0.16, "#8A7A6A", lambda c, r, pts: panicle(c, r, pts, 0.55, ["#A08AA0", "#B8A8B8", "#8C7890", "#C8C0B0"], 6, 0.13))
        return c
    n = {1: 70, 2: 110, 3: 75, 4: 45}[v]
    hairs(c, n, 0.92, 0.5, 0.05, wide=0.14)
    return c


BENT = ["#6E9A44", "#7CA64E", "#8AB258", "#97BC64"]


def bent(v, extra=False):
    """Common bent (rödven), the meadow grass: narrow, flat blades; its flowers airy, reddish-purple panicles."""
    pal = {3: ["#A8A060", "#B8AE6A", "#9A9A58", "#8C9A50"], 4: ["#5A8E38", "#669A40", "#72A64A", "#80B054"]}.get(v, BENT)
    c = Plant(pal, 1100 + v)
    if extra:
        flowers(c, 6, 0.95, 0.18, "#8A7A5A", lambda c, r, pts: panicle(c, r, pts, 0.5, ["#9A5A5A", "#A86A64", "#8A4E58", "#B88078"], 7, 0.15))
        return c
    blades = {1: 30, 2: 20, 3: 28, 4: 42}[v]
    tuft(c, blades, 0.95, 0.018, 0.42, 0.25, 0.25)
    return c


SMALLREED = ["#4E7E34", "#5A8A3C", "#66964A", "#72A052"]


def smallreed(v, extra=False):
    """Wood small-reed (piprör), tall at forest edges: broad blades arching over; its flowers narrow, pale brownish
    panicles on tall stalks."""
    pal = {3: ["#8A9A48", "#9AA452", "#7A8E42", "#A8A860"]}.get(v, SMALLREED)
    c = Plant(pal, 1200 + v)
    if extra:
        flowers(c, 4, 0.97, 0.1, "#7A8A4A", lambda c, r, pts: panicle(c, r, pts, 0.55, ["#B8A88A", "#A89678", "#9A8070", "#C8B898"], 14, 0.045, airy=False, size=1.3))
        return c
    blades, droop = {1: (13, 0.3), 2: (14, 0.15), 3: (13, 0.35), 4: (18, 0.28)}[v]
    tuft(c, blades, 0.98, 0.034, 0.5, 0.4, droop)
    return c


MOORGRASS = ["#6A8A64", "#78966E", "#86A07A", "#6E8E5E"]


def moorgrass(v, extra=False):
    """Purple moor-grass (blåtåtel), in tussocks on wet ground: stiff, grey-green blades that turn bright gold in
    autumn; its flowers narrow, dark purple panicles."""
    pal = {2: ["#D0A048", "#C88A38", "#E0B860", "#B87A30"], 3: ["#A89A62", "#B8A46A", "#98905A", "#8A9A62"]}.get(v, MOORGRASS)
    c = Plant(pal, 1300 + v)
    if extra:
        flowers(c, 5, 0.96, 0.14, "#8A8A6A" if v == 1 else "#B89A50", lambda c, r, pts: panicle(c, r, pts, 0.5, ["#5A3A5A", "#6A4A6A", "#7A5A70"], 16, 0.04, airy=False, size=1.3))
        return c
    blades = {1: 36, 2: 36, 3: 32, 4: 46}[v]
    tuft(c, blades, 0.95, 0.017, 0.32, 0.18, 0.22, wide=0.22)
    return c


SEDGE = ["#3E5E46", "#4A6A50", "#56765A", "#466652"]


def sedge_spikes(c, r, pts):
    for j, f in enumerate((0.74, 0.84, 0.95)):  # female spikes below, the slim male one on top
        p, h = at(pts, f), heading(pts, f)
        lens(c, (p[0] - math.cos(h) * 0.04, p[1] - math.sin(h) * 0.04), h, 0.08 if j < 2 else 0.09, 0.015 if j < 2 else 0.008,
             rgb(r.choice(["#4A3420", "#5A4028", "#3E2A1A"])))


def sedge(v, extra=False):
    """Sedge (starr), by water and in bogs: stiff, keeled, dark blue-green blades; its flowers dark brown spikes on
    three-sided stems."""
    pal = {3: ["#5A7A74", "#668680", "#4E6E68"], 4: ["#4A6A50", "#56765A", "#8A7A4A", "#9A8452"]}.get(v, SEDGE)
    c = Plant(pal, 1400 + v)
    if extra:
        flowers(c, 5, 0.96, 0.12, "#4E6A4A", sedge_spikes, width=0.006)
        return c
    blades, droop = {1: (30, 0.1), 2: (28, 0.45), 3: (30, 0.15), 4: (30, 0.25)}[v]
    tuft(c, blades, 0.97, 0.013, 0.3, 0.12, droop, wide=0.14)
    return c


COTTONGRASS = ["#6A7A58", "#788866", "#869474", "#5E6E50"]


def cotton(c, r, pts):
    """A head of cotton: a dense, round tuft of white strands at the stalk's top."""
    top = pts[-1]
    for j in range(70):
        a = math.pi / 2 + r.gauss(0, 1.1)
        L = r.uniform(0.03, 0.07)
        start = (top[0] + r.uniform(-0.004, 0.004), top[1] - 0.01)
        lens(c, start, a, L, 0.009, rgb(r.choice(["#F4F2EA", "#E8E6DC", "#FFFFFF", "#DCDAD0", "#ECEAE0"])))


def cottongrass(v, extra=False):
    """Hare's-tail cottongrass (tuvull), the bog's tussocks: dense, wiry, grey-green leaves; in seed, a round white tuft
    of cotton on each stalk."""
    pal = {3: ["#B07A40", "#A86E3A", "#C08A4C", "#8A7A50"]}.get(v, COTTONGRASS)
    c = Plant(pal, 1500 + v)
    if extra:
        flowers(c, 6, 0.9, 0.18, "#6A7A58", cotton)
        return c
    n = {1: 80, 2: 120, 3: 80, 4: 55}[v]
    hairs(c, n, 0.92, 0.42, 0.02, width=0.01, wide=0.22)
    return c


# ------------------------------------------------------------------ long grass
LONGGRASS = ["#4E7A2E", "#5A8636", "#66923E", "#72A048"]
LONGGRASS_TIPS = ["#8EAE58", "#9AB862", "#A6BE6A"]
STRAW = ["#B8A868", "#C8B878", "#A89858", "#BCAE70"]


def strand(c, base, ang, length, width, curve, droop, col, tip):
    """A thin strand of grass from base: tapering to a point, curving sideways (curve) and hanging (droop), its colour
    running from col at its foot to tip at its end, so a card of them reads darker low down, as grass does."""
    n = 16
    pts = []
    for i in range(n + 1):
        t = i / n
        bend = curve * length * t * t
        pts.append((base[0] + math.cos(ang) * length * t - math.sin(ang) * bend,
                    base[1] + math.sin(ang) * length * t + math.cos(ang) * bend - droop * length * t ** 2.2))
    for i in range(n):
        h = heading(pts, (i + 0.5) / n)
        nx, ny = -math.sin(h), math.cos(h)
        w0, w1 = width * (1 - i / n) ** 0.6, width * (1 - (i + 1) / n) ** 0.6
        a, b = pts[i], pts[i + 1]
        f = ((i + 0.5) / n) ** 1.3
        colour = tuple(round(col[k] + (tip[k] - col[k]) * f) for k in range(3))
        quad = [(a[0] + nx * w0, a[1] + ny * w0), (b[0] + nx * w1, b[1] + ny * w1),
                (b[0] - nx * w1, b[1] - ny * w1), (a[0] - nx * w0, a[1] - ny * w0)]
        c.d.polygon([c.px(q) for q in quad], fill=colour + (255,))


def strands(c, n, length, spread, curve, droop, width, dry=0.0, tips=LONGGRASS_TIPS):
    """A row of thin strands across the card, their feet spread along its foot: a strip of grass, not one tuft, so
    crossed copies make a patch. The back ones darker and the front ones lighter, drawn back to front; those at the
    card's sides lean out a little."""
    r = c.rng
    for k in range(n):
        depth = k / max(1, n - 1)  # 0 at the back
        x = r.uniform(0.05, 0.95)
        a = math.pi / 2 + (0.5 - x) * 0.5 + r.gauss(0, spread)
        L = length * r.uniform(0.55, 1.0)
        if r.random() < dry:
            col, tip = rgb(r.choice(STRAW)), shade(rgb(r.choice(STRAW)), 1.1)
        else:
            col = shade(c.colour(), 0.62 + 0.3 * depth)
            tip = shade(rgb(r.choice(tips)), 0.85 + 0.2 * depth)
        side = 1 if r.random() < 0.5 else -1
        strand(c, (x, FOOT[1] + r.uniform(-0.01, 0.02)), a, L, width * r.uniform(0.8, 1.15),
               side * abs(r.gauss(curve, curve * 0.5)), droop * (L / length) ** 2 * r.uniform(0.4, 1.3), col, tip)


def longgrass(v, extra=False):
    """Long grass, thick and semi-long, the grass the game's green ground grows: thin strands standing in a row along
    the card's foot, so crossed copies make a patch. Its flowers: seed heads on thin stalks, the meadow's bent and
    timothy."""
    pal = {4: ["#3E6E26", "#4A7A2C", "#568634", "#62903C"]}.get(v, LONGGRASS)
    c = Plant(pal, 1600 + v)
    c.fit = "box" if extra else "top"
    if extra:
        r = c.rng
        for k in range({1: 6, 2: 5, 3: 6, 4: 5}[v]):
            stem = rgb(r.choice(["#7A8A4A", "#8A9452", "#9A9A5A"] if v != 3 else ["#A89858", "#B8A868"]))
            pts = stalk(c, r, 0.95 * r.uniform(0.8, 1.0), r.gauss(0, 0.16), stem, 0.007)
            if (v == 2 or v == 4) and k % 2 == 0:  # timothy: a dense cylinder of a head
                spike(c, r, pts, 0.72, ["#A8B080", "#98A070", "#B4B88A"], width=0.013, size=0.8)
            else:  # bent: an airy panicle, reddish-purple, or straw when dry
                panicle(c, r, pts, 0.55, ["#9A6A5A", "#A87A68", "#8A5E58"] if v != 3 else ["#C0AE72", "#B09E62", "#D0C080"], 6, 0.12)
        return c
    n, length, spread, curve, droop, width, dry = {
        1: (130, 0.95, 0.2, 0.15, 0.15, 0.010, 0.0),
        2: (100, 0.98, 0.26, 0.3, 0.38, 0.010, 0.0),
        3: (120, 0.95, 0.22, 0.18, 0.2, 0.010, 0.18),
        4: (75, 0.92, 0.22, 0.25, 0.25, 0.016, 0.0),
    }[v]
    strands(c, n, length, spread, curve, droop, width, dry)
    return c


# ------------------------------------------------------------------ the game's grass: four styles and their ground
# The user found the long grass didn't blend into the ground (10 October): its cards showed as crossed planes, its
# colour wasn't the ground's, and the ground under it was too smooth. So the game's grass comes in styles of fewer
# strands a card than the long grass, more of each card clear so the ground shows through, each with a ground texture
# to match: the same strands lying flat, as seen from above, which the game paints over its green ground. Cards and
# ground are painted round one base colour, the strands' feet in it and their tips a little lighter and yellower:
# the game colours both by the ground's own colour where they lie, so they only need to agree with each other.
GRASS_BASE = "#5E8A38"  # a strand's foot, and the ground's background
GRASS_TIP = "#76A440"   # its tip: about 1.5 times as light as its foot, once the game has it in linear colour
GRASS_DRY = "#98A44C"   # a dry strand's tip
STYLES = {  # set: its card's strands (half-width and length as shares of the card), and its ground's (in metres)
    "wisps": dict(n=20, width=0.016, length=0.95, spread=0.26, curve=0.28, droop=0.32, tuft=False,
                  ground=dict(kind="loose", count=2600, length=(0.1, 0.24), width=0.008)),
    "tufts": dict(n=16, width=0.022, length=0.95, spread=0.42, curve=0.3, droop=0.22, tuft=True,
                  ground=dict(kind="tufts", count=380, blades=(8, 14), length=(0.08, 0.18), width=0.009)),
    "clumps": dict(n=30, width=0.014, length=0.95, spread=0.22, curve=0.22, droop=0.24, tuft=False,
                   ground=dict(kind="clumps", count=240, blades=(20, 34), length=(0.12, 0.24), width=0.007)),
    "shortgrass": dict(n=26, width=0.024, length=0.92, spread=0.3, curve=0.2, droop=0.12, tuft=False,
                       ground=dict(kind="loose", count=5200, length=(0.04, 0.09), width=0.008)),
}
GROUND_METRES = 4.0  # how far a ground texture reaches before it repeats
GROUND_SIZE = 2048   # its pixels across


def grass_style(name, v):
    """A card of one of the game's grass styles (STYLES): fewer strands than the long grass's, in a row along the
    card's foot, or fanning out from its middle as a tuft; design 2 has some dry blades, 3 more strands."""
    s = STYLES[name]
    c = Plant([GRASS_BASE], 1700 + 10 * list(STYLES).index(name) + v)
    c.fit = "box" if s["tuft"] else "top"
    r = c.rng
    n = round(s["n"] * (1.4 if v == 3 else 1.0))
    base, tip, dry = rgb(GRASS_BASE), rgb(GRASS_TIP), rgb(GRASS_DRY)
    for k in range(n):
        x = 0.5 + r.gauss(0, 0.06) if s["tuft"] else r.uniform(0.06, 0.94)
        a = math.pi / 2 + (0.5 - x) * (0.5 if not s["tuft"] else 0.0) + r.gauss(0, s["spread"])
        L = s["length"] * r.uniform(0.55, 1.0)
        foot = shade(base, r.uniform(0.94, 1.04))
        end = shade(dry if (v == 2 and r.random() < 0.2) else tip, r.uniform(0.95, 1.05))
        side = 1 if r.random() < 0.5 else -1
        strand(c, (x, FOOT[1] + r.uniform(-0.01, 0.015)), a, L, s["width"] * r.uniform(0.8, 1.15),
               side * abs(r.gauss(s["curve"], s["curve"] * 0.5)), s["droop"] * (L / s["length"]) ** 2 * r.uniform(0.4, 1.3),
               foot, end)
    return c


def ground_tile(name):
    """The ground under a grass style: its strands lying flat in the same colours, as seen from above, on the base
    colour, GROUND_METRES across and seamless (a strand over an edge comes back in at the other). Loose strands lie
    every which way; tufts lie as stars from their middles; clumps lie combed one way, a clump at a time. Under them,
    lighter and darker blotches a clump of grass across."""
    g = STYLES[name]["ground"]
    r = random.Random(1800 + list(STYLES).index(name))
    big = GROUND_SIZE * 2  # drawn at twice the size, for clean edges
    img = Image.new("RGB", (big, big), rgb(GRASS_BASE))
    # under the strands, lighter and darker blotches a clump of grass across (10 to 40 cm), so the ground has
    # texture at the size the game's camera sees, not only in strands too fine for it: drawn small, wrapped round and
    # blurred, then laid over the base colour
    low = 256
    blot = Image.new("L", (low * 3, low * 3), 128)
    bd = ImageDraw.Draw(blot)
    for _ in range(int(140 * GROUND_METRES ** 2 / 16)):
        x, y, rad = r.uniform(0, low), r.uniform(0, low), r.uniform(0.05, 0.2) * low / GROUND_METRES
        tone = 128 + round(r.choice((-1, 1)) * r.uniform(14, 34))
        for ox in (0, low, 2 * low):
            for oy in (0, low, 2 * low):
                bd.ellipse([x + ox - rad, y + oy - rad * r.uniform(0.6, 1.0), x + ox + rad, y + oy + rad], fill=tone)
    blot = blot.filter(ImageFilter.GaussianBlur(low / GROUND_METRES * 0.05)).crop((low, low, 2 * low, 2 * low))
    blot = blot.resize((big, big), Image.BILINEAR)
    img = Image.composite(Image.new("RGB", (big, big), shade(rgb(GRASS_BASE), 1.12)), img, blot.point(lambda v: max(0, v - 128) * 2))
    img = Image.composite(Image.new("RGB", (big, big), shade(rgb(GRASS_BASE), 0.88)), img, blot.point(lambda v: max(0, 128 - v) * 2))
    d = ImageDraw.Draw(img)
    m = big / GROUND_METRES  # pixels a metre
    base, tip, dry = rgb(GRASS_BASE), rgb(GRASS_TIP), rgb(GRASS_DRY)

    def lie(x, y, ang, length, width, foot, end):
        """One strand lying from (x, y), metres, along ang: tapering, its colour running from foot to end."""
        n = 6
        pts = [(x + math.cos(ang) * length * i / n + math.sin(ang) * r.uniform(-0.1, 0.1) * length * (i / n) ** 2,
                y + math.sin(ang) * length * i / n) for i in range(n + 1)]
        for ox in (-GROUND_METRES, 0.0, GROUND_METRES):  # and its copies over the edges, so the tile repeats seamlessly
            for oy in (-GROUND_METRES, 0.0, GROUND_METRES):
                if not (-0.3 < x + ox < GROUND_METRES + 0.3 and -0.3 < y + oy < GROUND_METRES + 0.3):
                    continue
                for i in range(n):
                    (ax, ay), (bx, by) = pts[i], pts[i + 1]
                    h = math.atan2(by - ay, bx - ax)
                    nx, ny = -math.sin(h), math.cos(h)
                    w0, w1 = width * (1 - i / n) ** 0.6, width * (1 - (i + 1) / n) ** 0.6
                    f = (i + 0.5) / n
                    col = tuple(round(foot[k] + (end[k] - foot[k]) * f) for k in range(3))
                    quad = [(ax + nx * w0, ay + ny * w0), (bx + nx * w1, by + ny * w1), (bx - nx * w1, by - ny * w1), (ax - nx * w0, ay - ny * w0)]
                    d.polygon([((qx + ox) * m, (qy + oy) * m) for qx, qy in quad], fill=col)

    def colours():
        foot = shade(base, r.uniform(0.86, 1.0))
        end = shade(dry if r.random() < 0.08 else tip, r.uniform(0.94, 1.06))
        return foot, end

    W = GROUND_METRES
    if g["kind"] == "loose":
        for _ in range(g["count"]):
            lie(r.uniform(0, W), r.uniform(0, W), r.uniform(0, math.tau), r.uniform(*g["length"]), g["width"] * r.uniform(0.8, 1.2), *colours())
    elif g["kind"] == "tufts":
        for _ in range(g["count"]):
            x, y = r.uniform(0, W), r.uniform(0, W)
            for k in range(r.randint(*g["blades"])):
                lie(x, y, r.uniform(0, math.tau), r.uniform(*g["length"]), g["width"] * r.uniform(0.8, 1.2), *colours())
    else:  # clumps, combed one way each
        for _ in range(g["count"]):
            cx, cy, way = r.uniform(0, W), r.uniform(0, W), r.uniform(0, math.tau)
            for k in range(r.randint(*g["blades"])):
                x, y = cx + r.gauss(0, 0.12), cy + r.gauss(0, 0.12)
                lie(x, y, way + r.gauss(0, 0.45), r.uniform(*g["length"]), g["width"] * r.uniform(0.8, 1.2), *colours())
    return img.resize((GROUND_SIZE, GROUND_SIZE), Image.LANCZOS)


# ------------------------------------------------------------------ the list
PLANTS = {  # card set: (draw, extra kind, the designs' names)
    "raspberry": (raspberry, "berries", ["Leaf cluster", "Arching cane", "Pale undersides", "Young, light"]),
    "buckthorn": (buckthorn, "berries", ["Leafy twig", "Fan cluster", "Painted mass", "Autumn"]),
    "hazel": (hazel, "nuts", ["Leafy twig", "Fan cluster", "Painted mass", "Autumn"]),
    "fern": (fern, None, ["Frond", "Broad frond", "Young, light", "Autumn, rusty"]),
    "longgrass": (longgrass, "flowers", ["Thick, semi-long", "Long, arching", "With dry blades", "Lush, broad"]),
    "wisps": (lambda v, extra=False: grass_style("wisps", v), None, ["Even", "Dry blades", "Fuller"]),
    "tufts": (lambda v, extra=False: grass_style("tufts", v), None, ["Even", "Dry blades", "Fuller"]),
    "clumps": (lambda v, extra=False: grass_style("clumps", v), None, ["Even", "Dry blades", "Fuller"]),
    "shortgrass": (lambda v, extra=False: grass_style("shortgrass", v), None, ["Even", "Dry blades", "Fuller"]),
    "hairgrass": (hairgrass, "flowers", ["Fine tuft", "Dense tuft", "Golden, late summer", "Sparse"]),
    "bent": (bent, "flowers", ["Meadow tuft", "Tall, loose", "Dry", "Lush"]),
    "smallreed": (smallreed, "flowers", ["Arching blades", "Upright", "Late summer", "Full"]),
    "moorgrass": (moorgrass, "flowers", ["Summer tussock", "Autumn gold", "Fading", "Wet meadow"]),
    "sedge": (sedge, "flowers", ["Stiff tuft", "Arching", "Bluish", "Brown tips"]),
    "cottongrass": (cottongrass, "flowers", ["Wiry tuft", "Dense", "Autumn", "Sparse"]),
}


GRASSES = (longgrass, hairgrass, bent, smallreed, moorgrass, sedge, cottongrass)  # their extra is a card of flowering stalks


FITS = {}  # card -> (width, height): the share of the drawing a card cropped to its strands keeps (Plant.fit)


def save(c, name):
    """Scaled down without premultiplying, so the edges keep the leaves' colours (not black). A card that fits (the
    long grass's) is first cropped to what's drawn on it, its foot kept: its empty top, and with "box" its empty sides
    too, evenly round its middle, so the game doesn't draw pixels that are all thrown away; FITS keeps how much of
    the drawing it kept, for plantgen.py to size the card by (cards.json)."""
    os.makedirs(OUT, exist_ok=True)
    src = c.img
    if c.fit:
        n = src.width
        k = n / SIZE  # what survives the cut at 0.5 once scaled down: the thin tips don't
        small = src.getchannel("A").resize((SIZE, SIZE), Image.LANCZOS).point(lambda v: 255 if v >= 128 else 0).getbbox()
        box = [v * k for v in small]
        half = max(n / 2 - box[0], box[2] - n / 2) + n * 0.01 if c.fit == "box" else n / 2
        top = max(0, box[1] - n * 0.01)
        src = src.crop((round(n / 2 - half), round(top), round(n / 2 + half), n))
        FITS[name] = (round(src.width / n, 4), round(src.height / n, 4))
    col = src.convert("RGB").resize((SIZE, SIZE), Image.LANCZOS)
    alpha = src.getchannel("A").resize((SIZE, SIZE), Image.LANCZOS)
    img = Image.merge("RGBA", (*col.split(), alpha))
    img.save(os.path.join(OUT, name + ".png"))
    return img


def font(size):
    try:
        return ImageFont.truetype(os.path.join(HERE, "..", "..", "mockups", "fonts", "Cinzel.ttf"), size)
    except OSError:
        return ImageFont.load_default()


if __name__ == "__main__":
    made = {}
    for name, (draw, extra, names) in PLANTS.items():
        for v in range(1, len(names) + 1):
            made[(name, v)] = save(draw(v), f"{name}_{v}")
            if extra:
                made[(name, v, extra)] = save(draw(v, extra=True), f"{name}_{v}_{extra}")
    # a contact sheet: one row per plant, each design with its extra version beside it
    tile, pad, label_w = 150, 12, 170
    cols = max(len(p[2]) for p in PLANTS.values()) * 2
    sheet = Image.new("RGB", (label_w + cols * (tile + pad) + pad, len(PLANTS) * (tile + pad + 24) + pad), (236, 232, 222))
    dr = ImageDraw.Draw(sheet)
    big, small = font(20), font(12)
    for row, (name, (draw, extra, names)) in enumerate(PLANTS.items()):
        y = pad + row * (tile + pad + 24)
        dr.text((pad, y + tile / 2), name.capitalize(), fill=(60, 52, 40), font=big, anchor="lm")
        for v in range(1, len(names) + 1):
            for k, key in enumerate([(name, v)] + ([(name, v, extra)] if extra else [])):
                x = label_w + pad + ((v - 1) * 2 + k) * (tile + pad)
                img = made[key].resize((tile, tile), Image.LANCZOS)
                sheet.paste(img, (x, y), img)
                below = f"{v}  {names[v - 1]}" if k == 0 else (f"{v} with {extra}" if draw not in GRASSES else f"{v}  its flowers")
                dr.text((x + tile / 2, y + tile + 3), below,
                        fill=(90, 80, 64), font=small, anchor="mt")
    os.makedirs(os.path.join(HERE, "previews"), exist_ok=True)
    sheet.save(os.path.join(HERE, "previews", "cards.png"))
    # the grass styles' grounds (ground_tile), and a sheet of them, each with a card of its strands on it
    tiles = []
    for name in STYLES:
        tile = ground_tile(name)
        tile.save(os.path.join(OUT, f"{name}_ground.jpg"), quality=92)
        tiles.append((name, tile))
    side = 700
    sheet = Image.new("RGB", (pad + len(tiles) * (side + pad), side + 2 * pad + 40), (236, 232, 222))
    dr = ImageDraw.Draw(sheet)
    for i, (name, tile) in enumerate(tiles):
        x = pad + i * (side + pad)
        part = tile.crop((0, 0, GROUND_SIZE // 2, GROUND_SIZE // 2)).resize((side, side), Image.LANCZOS)  # 2 m of it
        card = made[(name, 1)].resize((side // 2, side // 2), Image.LANCZOS)
        part.paste(card, (side // 4, side // 2 - 20), card)
        sheet.paste(part, (x, pad))
        dr.text((x + side / 2, pad + side + 8), f"{name}: 2 m of its ground, a card on it", fill=(90, 80, 64), font=big, anchor="mt")
    sheet.save(os.path.join(HERE, "previews", "grounds.png"))
    with open(os.path.join(OUT, "cards.json"), "w") as fh:  # the designs' names and extras, for the plant editor
        json.dump({"names": {k: p[2] for k, p in PLANTS.items()}, "extras": {k: p[1] for k, p in PLANTS.items()}, "fits": FITS,
                   "grounds": {k: {"file": f"{k}_ground.jpg", "metres": GROUND_METRES} for k in STYLES}}, fh, indent=1)
    print("wrote", len(made), "cards to", OUT)
