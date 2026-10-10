"""Bark textures for the tree portfolio's trunks, painted after the bark swatches on ref_imgs/Trees of the Swedish
Forest.png, in the low-poly style: flat plates and marks with crisp edges and a few tones each, no photographic noise.

    python3 make_bark.py        writes textures/bark_<species>.png and bark_<species>_base.png, and previews/bark.png

Each texture covers 1 m round by 2 m up the trunk (512 x 1024 pixels) and tiles both ways. bark_<species>.png is the
bark of most of the trunk; bark_<species>_base.png the rougher bark at its foot (birch and aspen dark and furrowed, the
pine's thick grey plates under its orange upper bark), its alpha a noise the game blends the two by, so the edge
between them is ragged (shaders/lowpoly.gdshaderinc, BARK). treegen.py maps them onto the trunks: each facet shows its
own window of the texture, at its real size.

- Scots pine: thin, flaky orange plates above; thick grey-brown plates below, orange inner bark in the fissures
- Silver birch: white, with dark lenticels in bands, grey streaks and black, brown-hearted scars; at the foot, black
  furrowed plates with white between
- Norway spruce: small grey-brown scales, dark between, orange-brown here and there
- Aspen: smooth, pale grey-green, with dark diamond "eyes" and fine lines; a dark, furrowed foot
- Rowan: smooth, mottled grey, with lichen and orange-brown patches and short pale lenticels
- Alder: dark grey-brown plates in long vertical fissures, lighter grey on some
"""
import math
import os
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "textures")
PREVIEW = os.path.join(HERE, "previews", "bark.png")
W, H = 512, 1024  # pixels: 1 m round, 2 m up
M = W  # pixels per metre
SS = 2  # drawn at twice the size and scaled down, for clean edges


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def shade(c, f):
    return tuple(max(0, min(255, int(round(v * f)))) for v in c)


class Bark:
    """A tileable canvas in metres: x round the trunk (0..1), y up it (0..2), drawn wrapped at the edges."""

    def __init__(self, bg, seed):
        self.r = random.Random(seed)
        self.img = Image.new("RGB", (W * SS, H * SS), rgb(bg))
        self.d = ImageDraw.Draw(self.img)

    def _offsets(self):
        for ox in (-W * SS, 0, W * SS):
            for oy in (-H * SS, 0, H * SS):
                yield ox, oy

    def px(self, x, y):
        return x * M * SS, (2.0 - y) * M * SS

    def poly(self, pts, col):
        col = rgb(col) if isinstance(col, str) else col
        q = [self.px(x, y) for x, y in pts]
        for ox, oy in self._offsets():
            self.d.polygon([(a + ox, b + oy) for a, b in q], fill=col)

    def line(self, pts, col, width):
        col = rgb(col) if isinstance(col, str) else col
        q = [self.px(x, y) for x, y in pts]
        w = max(1, int(round(width * M * SS)))
        for ox, oy in self._offsets():
            self.d.line([(a + ox, b + oy) for a, b in q], fill=col, width=w, joint="curve")

    def blob(self, cx, cy, rx, ry, col, n=9, rough=0.25, angle=0.0):
        """An irregular, faceted blob: a polygon round an ellipse, its radius jittered."""
        pts = []
        a0 = self.r.uniform(0, math.tau)
        for i in range(n):
            a = a0 + i * math.tau / n
            f = 1 + self.r.uniform(-rough, rough)
            x, y = math.cos(a) * rx * f, math.sin(a) * ry * f
            pts.append((cx + x * math.cos(angle) - y * math.sin(angle), cy + x * math.sin(angle) + y * math.cos(angle)))
        self.poly(pts, col)
        return pts

    def lens(self, cx, cy, w, h, col, n=10):
        """A lens (almond) shape, w wide and h tall: a lenticel, an aspen's eye."""
        pts = [(cx + w / 2 * math.cos(math.pi * i / n), cy + h / 2 * math.sin(math.pi * i / n) ** 0.8) for i in range(n + 1)]
        pts += [(cx + w / 2 * math.cos(math.pi * i / n), cy - h / 2 * math.sin(math.pi * i / n) ** 0.8) for i in range(n, -1, -1)]
        self.poly(pts, col)

    def tone(self, cells, col, strength, seed_off=0, hard=None):
        """Wash a colour over the canvas through a tileable noise, cells across and up (a few for broad patches,
        many up for horizontal bands); hard (0..1) makes its edges crisp, as flat patches."""
        mask = noise(cells[0], cells[1], self.r.randrange(1 << 30) + seed_off)
        if hard is not None:
            mask = mask.point(lambda v: 255 if v > hard * 255 else 0).filter(ImageFilter.GaussianBlur(SS * 0.7))
        mask = mask.point(lambda v: int(v * strength))
        over = Image.new("RGB", self.img.size, rgb(col) if isinstance(col, str) else col)
        self.img = Image.composite(over, self.img, mask)
        self.d = ImageDraw.Draw(self.img)

    def plates(self, cols, rows, size, colours, gap_colour=None, inner=None, light=1.08, stagger=0.5, rough=0.22, n=8):
        """Bark plates on a staggered grid, cols across the metre and rows up the 2 m, each an irregular polygon of
        size (width, height) in metres, in one of colours; inner, if given, a slightly bigger polygon of another colour
        behind each (the inner bark showing in the fissures); its left part a facet a little lighter, its right a
        little darker, as a faceted plate catches the light."""
        cw, rh = 1.0 / cols, 2.0 / rows
        for j in range(rows):
            for i in range(cols):
                cx = (i + (stagger if j % 2 else 0.0) + self.r.uniform(-0.2, 0.2)) * cw
                cy = (j + self.r.uniform(-0.15, 0.15)) * rh
                w = size[0] * self.r.uniform(0.85, 1.15) / 2
                h = size[1] * self.r.uniform(0.8, 1.2) / 2
                if inner:
                    self.blob(cx, cy, w * 1.18, h * 1.08, shade(rgb(self.r.choice(inner)), self.r.uniform(0.9, 1.1)), n, rough)
                c = shade(rgb(self.r.choice(colours)), self.r.uniform(0.92, 1.08))
                pts = self.blob(cx, cy, w, h, c, n, rough)
                # the facets: the plate's left part lighter, a sliver on the right darker
                left = [(x, y) for x, y in pts if x <= cx + w * 0.1]
                if len(left) >= 3:
                    self.poly(left + [(cx + w * 0.1, cy)], shade(c, light))
                right = [(x, y) for x, y in pts if x >= cx + w * 0.55]
                if len(right) >= 3:
                    self.poly(right + [(cx + w * 0.55, cy)], shade(c, 2.0 - light))

    def dashes(self, count, length, height, colours, bands=None, spread=0.02):
        """Short horizontal marks (lenticels), in bands up the trunk if bands is a count."""
        ys = [self.r.uniform(0, 2) for _ in range(bands)] if bands else None
        for _ in range(count):
            x = self.r.uniform(0, 1)
            y = (self.r.choice(ys) + self.r.gauss(0, spread)) if ys else self.r.uniform(0, 2)
            self.lens(x, y, self.r.uniform(*length), self.r.uniform(*height), self.r.choice(colours))

    def streaks(self, count, length, width, colours):
        """Thin horizontal lines, slightly wavy."""
        for _ in range(count):
            x, y = self.r.uniform(0, 1), self.r.uniform(0, 2)
            L = self.r.uniform(*length)
            pts = [(x + L * t / 4, y + self.r.uniform(-0.002, 0.002)) for t in range(5)]
            self.line(pts, self.r.choice(colours), self.r.uniform(*width))

    def done(self, alpha=None):
        img = self.img.resize((W, H), Image.LANCZOS)
        if alpha is not None:
            img = img.convert("RGBA")
            img.putalpha(alpha)
        return img


def noise(cx, cy, seed, size=None):
    """Smooth value noise that tiles: cx cells across, cy up, as a greyscale image the canvas's size."""
    r = random.Random(seed)
    small = Image.new("L", (cx, cy))
    small.putdata([r.randrange(256) for _ in range(cx * cy)])
    big = Image.new("L", (cx * 3, cy * 3))
    for i in range(3):
        for j in range(3):
            big.paste(small, (i * cx, j * cy))
    size = size or (W * SS, H * SS)
    big = big.resize((size[0] * 3, size[1] * 3), Image.BICUBIC)
    out = big.crop((size[0], size[1], size[0] * 2, size[1] * 2))
    lo, hi = out.getextrema()
    return out.point(lambda v: int((v - lo) * 255 / max(hi - lo, 1)))


def edge(seed):
    """The base texture's alpha: a tileable noise, broad and fine, for the ragged edge where the foot's bark ends."""
    a = noise(6, 6, seed, (W, H))
    b = noise(24, 18, seed + 1, (W, H))
    return ImageChops.add(a.point(lambda v: int(v * 0.7)), b.point(lambda v: int(v * 0.3)))


# ------------------------------------------------------------------ the species
# The marks are drawn bigger than life where they'd vanish otherwise: from the game's camera, 20 m off, a trunk's facet
# is a few pixels across, so a birch's lenticels are 6-15 mm tall here, an aspen's eyes up to 16 cm wide.
def silver_birch(seed):
    b = Bark("#EAE6DC", seed)
    b.tone((2, 26), "#D3D0C6", 0.6)  # faint horizontal bands
    b.tone((5, 9), "#F4F0E7", 0.45)  # creamy patches
    b.streaks(150, (0.05, 0.3), (0.002, 0.004), ["#C6C3BA", "#BAB7AE", "#CFCCC3"])
    b.dashes(170, (0.03, 0.12), (0.006, 0.015), ["#2E2A27", "#3E3935", "#4A443E"], bands=16, spread=0.014)
    for _ in range(8):  # branch scars: black, horizontally drawn-out diamonds with a brown heart, a dark brow above
        cx, cy = b.r.uniform(0, 1), b.r.uniform(0, 2)
        w, h = b.r.uniform(0.12, 0.26), b.r.uniform(0.05, 0.12)
        pts = [(cx - w / 2, cy), (cx - w * 0.15, cy + h * b.r.uniform(0.35, 0.6)), (cx, cy + h / 2),
               (cx + w * 0.2, cy + h * b.r.uniform(0.3, 0.55)), (cx + w / 2, cy), (cx + w * 0.15, cy - h * 0.25),
               (cx, cy - h / 2), (cx - w * 0.2, cy - h * 0.3)]
        b.poly(pts, "#262220")
        b.blob(cx, cy, w * 0.18, h * 0.22, "#6B4C36", 7, 0.3)
        b.line([(cx - w * 0.35, cy + h * 0.65), (cx, cy + h * 0.85), (cx + w * 0.35, cy + h * 0.65)], "#3A3430", 0.006)
    upper = b.done()
    f = Bark("#1C1A18", seed + 7)  # the foot: black, furrowed plates, white bark left between them
    f.plates(8, 10, (0.13, 0.22), ["#3A3632", "#48433E", "#2F2C29", "#55504A"], rough=0.3, n=6)
    for _ in range(30):
        f.blob(f.r.uniform(0, 1), f.r.uniform(0, 2), f.r.uniform(0.012, 0.035), f.r.uniform(0.01, 0.03), "#C9C4BA", 6, 0.35)
    return upper, f.done(edge(seed + 9))


def aspen(seed):
    b = Bark("#B4BA9F", seed)
    b.tone((2, 22), "#A3A98E", 0.6)
    b.tone((4, 8), "#C2C6B0", 0.4)
    b.streaks(110, (0.05, 0.3), (0.002, 0.004), ["#D3D5C8", "#9A9D8A", "#8E917E"])
    b.dashes(70, (0.015, 0.05), (0.004, 0.008), ["#3A3A33", "#4A4A42"])
    for _ in range(8):  # the eyes: dark almonds, paler inside, a dark pupil, a pale lid above
        cx, cy = b.r.uniform(0, 1), b.r.uniform(0, 2)
        w, h = b.r.uniform(0.07, 0.16), b.r.uniform(0.03, 0.06)
        b.line([(cx - w * 0.6, cy + h * 0.55), (cx, cy + h * 1.0), (cx + w * 0.6, cy + h * 0.55)], "#D8DACC", 0.006)
        b.lens(cx, cy, w, h, "#2E2D27")
        b.lens(cx, cy, w * 0.6, h * 0.55, "#77735F")
        b.blob(cx, cy, h * 0.22, h * 0.22, "#1E1D19", 6, 0.1)
    upper = b.done()
    f = Bark("#2A2925", seed + 7)
    f.plates(8, 10, (0.13, 0.22), ["#5E5B52", "#6A665C", "#4F4C45", "#75715F"], rough=0.3, n=6)
    return upper, f.done(edge(seed + 9))


def scots_pine(seed):
    b = Bark("#8A4A2A", seed)  # above: thin orange plates, flaking
    b.plates(9, 14, (0.125, 0.16), ["#C27A45", "#B86C3C", "#CC8450", "#B5653A"], rough=0.3, light=1.07, n=7)
    for _ in range(30):  # paper-thin flakes peeling, paler
        b.blob(b.r.uniform(0, 1), b.r.uniform(0, 2), b.r.uniform(0.015, 0.04), b.r.uniform(0.008, 0.02), "#E0A272", 6, 0.3)
    upper = b.done()
    f = Bark("#2E241E", seed + 7)  # below: thick grey plates, orange inner bark in the fissures
    f.plates(7, 7, (0.16, 0.33), ["#6B5D50", "#5E5248", "#7A6C5E", "#8A7C6C", "#574B42"], inner=["#A85A32", "#8E4A2A", "#B5653A"],
             rough=0.28, light=1.1, n=7)
    return upper, f.done(edge(seed + 9))


def norway_spruce(seed):
    b = Bark("#2E2620", seed)
    b.plates(12, 16, (0.095, 0.145), ["#5A4E44", "#4F443B", "#66594D", "#6E6052"], inner=["#3A3029", "#7A4E2E"], rough=0.3, n=7)
    upper = b.done()
    f = Bark("#241D18", seed + 7)
    f.plates(9, 11, (0.13, 0.2), ["#4F443B", "#5A4E44", "#463C34"], inner=["#3A3029", "#6A4428"], rough=0.3, n=7)
    return upper, f.done(edge(seed + 9))


def rowan(seed):
    b = Bark("#8A8372", seed)
    b.tone((5, 10), "#9C957F", 0.5)
    b.tone((6, 12), "#756E5F", 0.45)
    for _ in range(18):  # lichen
        b.blob(b.r.uniform(0, 1), b.r.uniform(0, 2), b.r.uniform(0.025, 0.07), b.r.uniform(0.02, 0.06),
               b.r.choice(["#A9AE9A", "#BCC1AE", "#C2C09A"]), 9, 0.35)
    for _ in range(10):  # orange-brown patches
        b.blob(b.r.uniform(0, 1), b.r.uniform(0, 2), b.r.uniform(0.025, 0.07), b.r.uniform(0.015, 0.04), "#8E5E3A", 8, 0.35)
    b.dashes(80, (0.02, 0.06), (0.005, 0.009), ["#A8A290", "#B2AC9A"], bands=10, spread=0.02)
    upper = b.done()
    f = Bark("#3A362F", seed + 7)
    f.plates(8, 10, (0.13, 0.22), ["#6E695E", "#7A7568", "#5E5A50"], rough=0.3, n=6)
    return upper, f.done(edge(seed + 9))


def alder(seed):
    b = Bark("#1E1A17", seed)
    b.plates(10, 8, (0.105, 0.27), ["#3E3832", "#4A433B", "#453E37", "#57504A", "#5E5850"], inner=["#5A3E2C", "#2E2622"],
             rough=0.3, n=7)
    upper = b.done()
    f = Bark("#1A1714", seed + 7)
    f.plates(8, 7, (0.13, 0.31), ["#3A342E", "#453E37", "#332E29"], inner=["#4A3426"], rough=0.3, n=7)
    return upper, f.done(edge(seed + 9))


SPECIES = {"ScotsPine": scots_pine, "SilverBirch": silver_birch, "NorwaySpruce": norway_spruce, "Aspen": aspen,
           "Rowan": rowan, "Alder": alder}


def main():
    os.makedirs(OUT, exist_ok=True)
    tiles = []
    for i, (key, paint) in enumerate(SPECIES.items()):
        upper, base = paint(4100 + 37 * i)
        upper.save(os.path.join(OUT, f"bark_{key}.png"))
        base.save(os.path.join(OUT, f"bark_{key}_base.png"))
        tiles.append((key, upper, base))
        print("bark", key)
    # the preview: each species' bark and its foot, a metre square of each, side by side
    cell = 256
    sheet = Image.new("RGB", (len(tiles) * (2 * cell + 16) + 16, cell * 2 + 32), (240, 238, 232))
    for i, (key, upper, base) in enumerate(tiles):
        x = 16 + i * (2 * cell + 16)
        sheet.paste(upper.crop((0, 0, W, H)).resize((cell, cell * 2)), (x, 16))
        sheet.paste(base.convert("RGB").crop((0, 0, W, H)).resize((cell, cell * 2)), (x + cell, 16))
    sheet.save(PREVIEW)
    print("preview", PREVIEW)


if __name__ == "__main__":
    main()
