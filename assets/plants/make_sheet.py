"""Lays out the plant portraits from make_plants.py as one captioned sheet: previews/portfolio.png.

    python3 make_sheet.py      (make_plants.py runs it after rendering the portraits)
"""
import json
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
TILES = os.path.join(HERE, "previews", "tiles")
FONT = os.path.join(HERE, "..", "..", "mockups", "fonts", "Cinzel.ttf")
BG, INK, SOFT = (236, 232, 222), (52, 46, 38), (120, 108, 90)
KINDS = {"bush": "bush", "fern": "fern", "grass": "grass", "patch": "a patch of it"}


def font(size):
    try:
        return ImageFont.truetype(FONT, size)
    except OSError:
        return ImageFont.load_default()


def main():
    info = json.load(open(os.path.join(TILES, "info.json"), encoding="utf-8"))
    tw, th, cap, pad, cols = 700, 560, 124, 28, 4
    keys = list(info)
    rows = (len(keys) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (tw + pad) + pad, 150 + rows * (th + cap + pad)), BG)
    d = ImageDraw.Draw(sheet)
    d.text((pad, 40), "Bushes and grasses of the Swedish forest", fill=INK, font=font(52))
    d.text((pad, 104), "Leaves, sprigs, fronds and blades as crossed cards; low-poly stems. Both variants of each",
           fill=SOFT, font=font(26))
    for i, key in enumerate(keys):
        x = pad + (i % cols) * (tw + pad)
        y = 150 + (i // cols) * (th + cap + pad)
        sheet.paste(Image.open(os.path.join(TILES, key + ".png")).convert("RGB").resize((tw, th), Image.LANCZOS), (x, y))
        t = info[key]
        d.text((x, y + th + 14), t["name"], fill=INK, font=font(34))
        d.text((x, y + th + 60), f"{t['swedish']} · {t['latin']}", fill=SOFT, font=font(22))
        size = f"{t['height']:.1f} m tall" if t["height"] >= 1 else f"{round(t['height'] * 100)} cm tall"
        d.text((x, y + th + 90), f"{KINDS[t['kind']]} · {size} · {t['cards']} cards · {t['faces']} faces", fill=SOFT, font=font(20))
    out = os.path.join(HERE, "previews", "portfolio.png")
    sheet.save(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
