"""Paint a placeholder ARPG HUD over the Blender renders."""
import json, math, os, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SRC = sys.argv[1]
DST = sys.argv[2]
os.makedirs(DST, exist_ok=True)

NARROW_B = "/usr/share/fonts/truetype/liberation/LiberationSansNarrow-Bold.ttf"
NARROW = "/usr/share/fonts/truetype/liberation/LiberationSansNarrow-Regular.ttf"
SANS_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def font(path, size):
    return ImageFont.truetype(path, size)


GOLD = (226, 176, 79)
RED = (184, 58, 50)
INK = (232, 234, 238)
MUTED = (160, 168, 178)
PANEL = (16, 19, 24, 175)
LINE = (88, 96, 108, 255)
FOGBLUE = (176, 218, 242)


def panel(d, box, r=8, fill=PANEL, outline=LINE):
    d.rounded_rectangle(box, r, fill=fill, outline=outline, width=2)


def bar(d, x, y, w, h, frac, color, label):
    d.rounded_rectangle((x, y, x + w, y + h), 4, fill=(10, 12, 15, 220), outline=LINE, width=2)
    inner = int((w - 6) * frac)
    d.rounded_rectangle((x + 3, y + 3, x + 3 + inner, y + h - 3), 3, fill=color + (255,))
    hi = tuple(min(255, int(c * 1.25)) for c in color)
    d.rectangle((x + 4, y + 4, x + 2 + inner, y + 4 + (h - 8) // 3), fill=hi + (120,))
    f = font(SANS_B, 13)
    d.text((x + w / 2, y + h / 2), label, font=f, fill=INK + (255,), anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0, 200))


def crosshair(d, x, y, color=GOLD):
    d.ellipse((x - 14, y - 14, x + 14, y + 14), outline=(0, 0, 0, 150), width=5)
    d.ellipse((x - 14, y - 14, x + 14, y + 14), outline=color + (255,), width=3)
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        d.line((x + dx * 8, y + dy * 8, x + dx * 22, y + dy * 22), fill=(0, 0, 0, 150), width=5)
        d.line((x + dx * 8, y + dy * 8, x + dx * 22, y + dy * 22), fill=color + (255,), width=3)
    d.ellipse((x - 2.5, y - 2.5, x + 2.5, y + 2.5), fill=color + (255,))


def glyph(d, kind, cx, cy, s, col):
    c = col + (255,)
    if kind == "slash":
        d.line((cx - s * .45, cy + s * .45, cx + s * .4, cy - s * .4), fill=c, width=4)
        d.line((cx - s * .25, cy + s * .05, cx + s * .05, cy + s * .35), fill=c, width=4)
    elif kind == "shield":
        d.ellipse((cx - s * .42, cy - s * .42, cx + s * .42, cy + s * .42), outline=c, width=4)
        d.ellipse((cx - s * .1, cy - s * .1, cx + s * .1, cy + s * .1), fill=c)
    elif kind == "whirl":
        d.arc((cx - s * .42, cy - s * .42, cx + s * .42, cy + s * .42), 200, 520, fill=c, width=4)
        d.polygon([(cx + s * .42, cy - s * .05), (cx + s * .25, cy - s * .3), (cx + s * .55, cy - s * .3)], fill=c)
    elif kind == "dash":
        for k in range(3):
            o = k * s * .22 - s * .25
            d.line((cx - s * .3 + o, cy - s * .3, cx + o, cy, cx - s * .3 + o, cy + s * .3), fill=c, width=4)
    elif kind == "rune":
        d.line((cx, cy - s * .42, cx, cy + s * .42), fill=c, width=4)
        d.line((cx, cy - s * .1, cx - s * .3, cy - s * .38), fill=c, width=4)
        d.line((cx, cy - s * .1, cx + s * .3, cy - s * .38), fill=c, width=4)
    elif kind == "locked":
        d.rounded_rectangle((cx - s * .22, cy - s * .05, cx + s * .22, cy + s * .3), 3, outline=c, width=3)
        d.arc((cx - s * .15, cy - s * .32, cx + s * .15, cy + s * .05), 180, 360, fill=c, width=3)


def skillbar(d, W, H, active=None, cooldown=None):
    slots = [("LMB", "slash"), ("RMB", "shield"), ("1", "whirl"), ("2", "dash"), ("3", "rune"), ("4", "locked")]
    size, gap = 58, 10
    total = len(slots) * size + (len(slots) - 1) * gap
    x0 = W / 2 - total / 2
    y0 = H - size - 40
    panel(d, (x0 - 12, y0 - 10, x0 + total + 12, y0 + size + 30), r=10)
    fk = font(NARROW_B, 14)
    for i, (key, kind) in enumerate(slots):
        x = x0 + i * (size + gap)
        border = GOLD + (255,) if key == active else LINE
        d.rounded_rectangle((x, y0, x + size, y0 + size), 6, fill=(28, 33, 41, 235), outline=border, width=3 if key == active else 2)
        col = MUTED if kind == "locked" else (INK if key != active else GOLD)
        glyph(d, kind, x + size / 2, y0 + size / 2, size * 0.62, col)
        if key == cooldown:
            d.pieslice((x + 3, y0 + 3, x + size - 3, y0 + size - 3), -90, 150, fill=(0, 0, 0, 150))
            d.text((x + size / 2, y0 + size / 2), "3", font=font(SANS_B, 20), fill=INK + (255,), anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0, 220))
        d.text((x + size / 2, y0 + size + 13), key, font=fk, fill=MUTED + (255,), anchor="mm")


def vitals(d, W, H, hp, en):
    x, y = 36, H - 118
    panel(d, (x - 12, y - 12, x + 330, y + 70), r=10)
    bar(d, x, y, 318, 24, hp / 200, RED, "%d / 200" % hp)
    bar(d, x, y + 34, 318, 20, en / 100, (214, 160, 58), "%d / 100" % en)


def minimap(img, info, W):
    R = 92
    cx, cy = W - 30 - R, 30 + R
    scale = 3.0
    mm = Image.new("RGBA", (2 * R, 2 * R), (0, 0, 0, 0))
    d = ImageDraw.Draw(mm)
    d.rectangle((0, 0, 2 * R, 2 * R), fill=(38, 48, 34, 210) if info["mode"] == "day" else (40, 46, 52, 215))
    px, py = info["player_world"]

    def to_mm(x, y):
        dx, dy = x - px, y - py
        u = (dx - dy) / math.sqrt(2)
        v = (dx + dy) / math.sqrt(2)
        return (R + u * scale, R - v * scale)

    bx, by, br = info["bog"]
    bc = to_mm(bx, by)
    d.ellipse((bc[0] - br * scale, bc[1] - br * scale, bc[0] + br * scale, bc[1] + br * scale), fill=(64, 62, 44, 230))
    d.polygon([to_mm(x, y) for x, y in info["tarn"]], fill=(58, 104, 128, 255))
    for pts in info["paths"]:
        d.line([to_mm(x, y) for x, y in pts], fill=(150, 116, 78, 255), width=5, joint="curve")
    # player arrow
    f = info["facing"] + math.pi / 2
    fx, fy = math.cos(f), math.sin(f)
    u = (fx - fy) / math.sqrt(2)
    v = (fx + fy) / math.sqrt(2)
    ang = math.atan2(-v, u)
    pts = []
    for a, rr in ((0, 9), (2.5, 7), (math.pi, 3), (-2.5, 7)):
        pts.append((R + math.cos(ang + a) * rr, R + math.sin(ang + a) * rr))
    d.polygon(pts, fill=GOLD + (255,), outline=(0, 0, 0, 255))
    if info["mode"] == "fog":
        fog = Image.new("RGBA", mm.size, (200, 212, 222, 70))
        mm = Image.alpha_composite(mm, fog)
    mask = Image.new("L", mm.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 2 * R - 1, 2 * R - 1), fill=255)
    img.paste(mm, (cx - R, cy - R), mask)
    d2 = ImageDraw.Draw(img)
    d2.ellipse((cx - R, cy - R, cx + R, cy + R), outline=LINE, width=3)
    d2.text((cx, cy - R + 14), "N", font=font(NARROW_B, 13), fill=MUTED + (255,), anchor="mm")
    # area label
    y = cy + R + 22
    d2.text((cx, y), "ACT I", font=font(NARROW_B, 15), fill=MUTED + (255,), anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0, 170))
    d2.text((cx, y + 22), "Pine forest", font=font(NARROW_B, 21), fill=INK + (255,), anchor="mm", stroke_width=3, stroke_fill=(0, 0, 0, 170))
    if info["mode"] == "fog":
        d2.text((cx, y + 46), "The fog has rolled in", font=font(NARROW, 17), fill=FOGBLUE + (255,), anchor="mm", stroke_width=3, stroke_fill=(0, 0, 0, 170))


def target_frame(d, W, name, frac):
    w = 340
    x0 = W / 2 - w / 2
    y0 = 26
    panel(d, (x0, y0, x0 + w, y0 + 52), r=8)
    d.text((W / 2, y0 + 15), name, font=font(NARROW_B, 18), fill=FOGBLUE + (255,), anchor="mm")
    d.rounded_rectangle((x0 + 14, y0 + 30, x0 + w - 14, y0 + 42), 3, fill=(10, 12, 15, 230))
    d.rounded_rectangle((x0 + 16, y0 + 32, x0 + 16 + (w - 32) * frac, y0 + 40), 2, fill=RED + (255,))


def compose(name):
    info = json.load(open(os.path.join(SRC, name + ".json")))
    img = Image.open(os.path.join(SRC, name + ".png")).convert("RGBA")
    W, H = img.size
    # soft vignette so the HUD sits on the frame
    vig = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vig)
    vd.rectangle((0, 0, W, H), fill=90)
    vd.ellipse((-W * 0.1, -H * 0.15, W * 1.1, H * 1.15), fill=0)
    vig = vig.filter(ImageFilter.GaussianBlur(120))
    img = Image.composite(Image.new("RGBA", (W, H), (0, 0, 0, 255)), img, vig)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    attacking = name == "fog_path"
    vitals(d, W, H, hp=138 if attacking else 186, en=41 if attacking else 88)
    skillbar(d, W, H, active="LMB" if attacking else None, cooldown="2" if attacking else None)
    if attacking:
        target_frame(d, W, "Antlered wraith", 0.62)
        dx, dy = info["damage"]
        d.text((dx, dy), "27", font=font(SANS_B, 30), fill=(255, 236, 190, 255), anchor="mm", stroke_width=3, stroke_fill=(40, 20, 10, 230))
        d.text((dx + 34, dy - 30), "19", font=font(SANS_B, 22), fill=(255, 236, 190, 200), anchor="mm", stroke_width=3, stroke_fill=(40, 20, 10, 200))
    cx, cy = info["cursor"]
    crosshair(d, cx, cy)
    d.text((W - 24, H - 18), "wfarpg mockup  ·  Blender render, not final art  ·  placeholder HUD",
           font=font(NARROW, 15), fill=(230, 232, 236, 150), anchor="rs")
    img = Image.alpha_composite(img, ov)
    minimap(img, info, W)
    out = os.path.join(DST, name + ".png")
    img.convert("RGB").save(out, optimize=True)
    print("wrote", out)


for n in ["day_path", "day_tarn", "fog_path", "fog_bog"]:
    compose(n)
