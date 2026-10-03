"""Leaf cards for the tree portfolio: one texture per species, with a transparent background.

    python3 make_leaf_cards.py      writes textures/<card>.png (512 x 512) and previews/leaf_cards.png

Each card is a cluster of leaves or needles. make_trees.py crosses three copies of a card at their centre to make a
leaf clump. Leaves are drawn as two flat halves, one lighter and one darker, to match the faceted low-poly props.
The transparent pixels carry the cards' average leaf colour, so filtered edges don't get dark or white fringes.
"""
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

    def berry(self, c, r, col, hi):
        x, y = self.px(c)
        rr = r * N
        self.d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=rgb(col) + (255,))
        h = rr * 0.38
        self.d.ellipse([x - rr * 0.45 - h, y - rr * 0.45 - h, x - rr * 0.45 + h, y - rr * 0.45 + h], fill=rgb(hi) + (255,))

    def save(self, name):
        os.makedirs(OUT, exist_ok=True)
        img = self.img.resize((SIZE, SIZE), Image.LANCZOS)
        img.save(os.path.join(OUT, name + ".png"))
        return img


def curve_pts(p0, ang, length, bend, n=8, droop=0.0):
    """Points along a gently curving twig: bend turns it sideways, droop pulls it down."""
    pts = []
    for i in range(n + 1):
        t = i / n
        a = ang + bend * t
        if i == 0:
            pts.append(p0)
            continue
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


def pine():
    c = Card(["#3B5A35", "#48683E", "#557548", "#5F7F4E", "#6B8A55"], 11)
    r = c.rng
    tufts = [(0.5, 0.5, 0.21)]  # x, y, needle length: a full round cluster of tufts
    for ring, (rad, n, length) in enumerate(((0.16, 6, 0.19), (0.3, 9, 0.15))):
        for k in range(n):
            a = k * TAU / n + ring * 0.35 + r.uniform(-0.2, 0.2)
            tufts.append((0.5 + rad * math.cos(a), 0.5 + rad * math.sin(a), length))
    for tx, ty, _ in tufts[1:]:
        c.twig([(0.5, 0.5), (tx, ty)], 0.01, "#7A4E2E")
    for i, (tx, ty, length) in enumerate(tufts):
        base = math.atan2(ty - 0.5, tx - 0.5)
        for _ in range(80):
            a = r.uniform(0, TAU) if i == 0 else base + r.gauss(0, 0.85)
            st = r.uniform(0.0, 0.03)
            c.needle((tx + math.cos(a) * st, ty + math.sin(a) * st), a, length * r.uniform(0.7, 1.0), 0.0055)
    return c


def spruce():
    c = Card(["#1E3A25", "#25442C", "#2D5033", "#355A3A", "#3F6644"], 12)
    r = c.rng
    main = curve_pts((0.06, 0.76), -0.04, 0.88, -0.1, 12)
    twigs = [main]
    for k in range(9):  # a curtain of branchlets hanging from the twig, as on a Norway spruce
        f = 0.08 + 0.84 * k / 8
        twigs.append(curve_pts(at(main, f), -math.pi / 2 + r.uniform(-0.35, 0.35), r.uniform(0.38, 0.58) * (1.1 - 0.5 * abs(f - 0.5)), r.uniform(-0.3, 0.3), 8))
    for f in (0.15, 0.3, 0.45, 0.6, 0.75, 0.88):  # and a few reaching up and out
        twigs.append(curve_pts(at(main, f), heading(main, f) + r.uniform(0.6, 0.9), r.uniform(0.12, 0.2), -0.3, 5))
    for tw in twigs:
        c.twig(tw, 0.007, "#5A4030")
    for tw in twigs:
        length = sum(math.dist(tw[i], tw[i + 1]) for i in range(len(tw) - 1))
        for j in range(int(length / 0.0055)):
            f = j * 0.0055 / length
            p, h = at(tw, f), heading(tw, f)
            for side in (1, -1):
                c.needle(p, h + side * r.uniform(0.9, 1.35), r.uniform(0.03, 0.045) * (1.05 - 0.4 * f), 0.0045)
    return c


def birch():
    c = Card(["#7DA03A", "#8BAE43", "#99BA4C", "#A9C659", "#B8CF66"], 13)
    r = c.rng
    for k in range(11):
        x0 = 0.16 + 0.68 * k / 10 + r.uniform(-0.03, 0.03)
        tw = curve_pts((x0, r.uniform(0.82, 0.94)), -math.pi / 2 + r.uniform(-0.35, 0.35), r.uniform(0.6, 0.78), r.uniform(-0.4, 0.4), 10)
        c.twig(tw, 0.0045, "#4A3B30")
        n = r.randint(8, 11)
        for j in range(n):
            f = 0.08 + 0.9 * j / n
            side = 1 if j % 2 else -1
            c.leaf(at(tw, f), heading(tw, f) + side * r.uniform(0.45, 1.0), r.uniform(0.06, 0.085), r.uniform(0.042, 0.052), DELTOID, serr=0.12)
    return c


def aspen():
    c = Card(["#7C9C43", "#8AAA4C", "#98B656", "#A7C062", "#BCC66C"], 14)
    r = c.rng
    for k in range(8):
        tw = curve_pts((0.5, 0.3), math.radians(30 + 120 * k / 7) + r.uniform(-0.12, 0.12), r.uniform(0.27, 0.36), r.uniform(-0.3, 0.3), 8)
        c.twig(tw, 0.006, "#5E5A4A")
        for j in range(r.randint(6, 8)):
            f = 0.2 + 0.8 * j / 7
            side = 1 if j % 2 else -1
            p = at(tw, f)
            a = heading(tw, f) + side * r.uniform(0.6, 1.2)
            stalk = r.uniform(0.03, 0.045)
            q = (p[0] + math.cos(a) * stalk, p[1] + math.sin(a) * stalk)
            c.twig([p, q], 0.003, "#6E7A40")
            col = c.colour(["#C9C86E", "#B9B85E"]) if r.random() < 0.15 else None
            c.leaf(q, a + r.uniform(-0.4, 0.4), r.uniform(0.09, 0.12), r.uniform(0.085, 0.105), ROUND, col)
    return c


def rowan(berries=False):
    c = Card(["#4C7A2C", "#588634", "#64923C", "#71A045", "#7FAA4E"], 16 if berries else 15)
    r = c.rng
    for k in range(9):
        a = k * TAU / 9 + r.uniform(-0.15, 0.15)
        rach = curve_pts((0.5, 0.48), a, r.uniform(0.3, 0.38), r.uniform(-0.25, 0.25), 8)
        c.twig(rach, 0.004, "#4E6B2E")
        for s in (0.2, 0.34, 0.48, 0.62, 0.76):
            h = heading(rach, s)
            for side in (1, -1):
                c.leaf(at(rach, s), h + side * r.uniform(0.95, 1.15), r.uniform(0.065, 0.085), r.uniform(0.019, 0.023), LANCE, serr=0.15)
        c.leaf(rach[-1], heading(rach, 1.0), r.uniform(0.07, 0.085), 0.021, LANCE, serr=0.15)
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


def alder():
    c = Card(["#33592A", "#3C6530", "#467238", "#517E40", "#5C884A"], 17)
    r = c.rng
    tws = []
    for k in range(8):
        tw = curve_pts((0.5, 0.32), math.radians(25 + 130 * k / 7) + r.uniform(-0.12, 0.12), r.uniform(0.25, 0.33), r.uniform(-0.3, 0.3), 8)
        c.twig(tw, 0.006, "#4A3E34")
        tws.append(tw)
        for j in range(r.randint(5, 7)):
            f = 0.2 + 0.8 * j / 6
            side = 1 if j % 2 else -1
            p = at(tw, f)
            a = heading(tw, f) + side * r.uniform(0.6, 1.1)
            q = (p[0] + math.cos(a) * 0.02, p[1] + math.sin(a) * 0.02)
            c.twig([p, q], 0.003, "#4A5A34")
            c.leaf(q, a + r.uniform(-0.3, 0.3), r.uniform(0.11, 0.145), r.uniform(0.095, 0.115), OVAL, serr=0.08, notch=True)
    for tw in r.sample(tws, 2):  # small cones near the twig tips
        p = at(tw, 0.85)
        for k in range(3):
            a = r.uniform(0, TAU)
            q = (p[0] + math.cos(a) * 0.035, p[1] + math.sin(a) * 0.035)
            c.twig([p, q], 0.003, "#3E2C20")
            x, y = c.px(q)
            c.d.ellipse([x - 0.012 * N, y - 0.017 * N, x + 0.012 * N, y + 0.017 * N], fill=rgb(r.choice(["#3E2C20", "#4E3828"])) + (255,))
    return c


def juniper():
    c = Card(["#3E5C4C", "#4A6A58", "#577664", "#668470", "#78927E", "#8AA090"], 18)
    r = c.rng
    tws = []
    for k in range(9):
        tw = curve_pts((0.5, 0.06), math.radians(52 + 76 * k / 8) + r.uniform(-0.08, 0.08), r.uniform(0.55, 0.82), r.uniform(-0.25, 0.25), 10)
        tws.append(tw)
        c.twig(tw, 0.006, "#6A4A3A")
    for tw in tws:
        for j in range(70):
            f = 0.1 + 0.9 * j / 70
            p, h = at(tw, f), heading(tw, f)
            for side in (-1, 0, 1):  # whorls of three short, sharp needles
                c.needle(p, h + side * r.uniform(0.45, 0.75) + (0 if side else r.uniform(-0.2, 0.2)), r.uniform(0.03, 0.048), 0.005)
    for _ in range(7):
        tw = r.choice(tws)
        c.berry(at(tw, r.uniform(0.35, 0.9)), 0.016, r.choice(["#2E3A5E", "#3A4A72"]), "#7D8DB8")
    return c


CARDS = {"pine": pine, "spruce": spruce, "birch": birch, "aspen": aspen, "rowan": rowan,
         "rowan_berries": lambda: rowan(True), "alder": alder, "juniper": juniper}

if __name__ == "__main__":
    made = [(name, fn().save(name)) for name, fn in CARDS.items()]
    # a contact sheet for the board
    tile, pad = 300, 24
    sheet = Image.new("RGB", (4 * (tile + pad) + pad, 2 * (tile + pad + 34) + pad), (236, 232, 222))
    dr = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype(os.path.join(HERE, "..", "..", "mockups", "fonts", "Cinzel.ttf"), 22)
    except OSError:
        font = ImageFont.load_default()
    for i, (name, img) in enumerate(made):
        x = pad + (i % 4) * (tile + pad)
        y = pad + (i // 4) * (tile + pad + 34)
        sheet.paste(img.resize((tile, tile), Image.LANCZOS), (x, y), img.resize((tile, tile), Image.LANCZOS))
        dr.text((x + tile / 2, y + tile + 6), name.replace("_", " + "), fill=(60, 52, 40), font=font, anchor="mt")
    os.makedirs(os.path.join(HERE, "previews"), exist_ok=True)
    sheet.save(os.path.join(HERE, "previews", "leaf_cards.png"))
    print("wrote", len(made), "cards to", OUT)
