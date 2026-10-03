"""Lays out the tree portraits from make_trees.py as one captioned sheet: previews/portfolio.png.

    python3 make_sheet.py      (make_trees.py runs it after rendering the portraits)
"""
import json
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
TILES = os.path.join(HERE, "previews", "tiles")
FONT = os.path.join(HERE, "..", "..", "mockups", "fonts", "Cinzel.ttf")
BG, INK, SOFT = (236, 232, 222), (52, 46, 38), (120, 108, 90)


def font(size):
    try:
        return ImageFont.truetype(FONT, size)
    except OSError:
        return ImageFont.load_default()


def main():
    info = json.load(open(os.path.join(TILES, "info.json")))
    tw, th, cap, pad, cols = 600, 750, 120, 28, 4
    keys = list(info)
    rows = (len(keys) + 1 + cols - 1) // cols  # one more slot for the leaf cards
    sheet = Image.new("RGB", (cols * (tw + pad) + pad, 150 + rows * (th + cap + pad)), BG)
    d = ImageDraw.Draw(sheet)
    d.text((pad, 40), "Trees of the Swedish forest", fill=INK, font=font(52))
    d.text((pad, 104), "Low-poly trunks and branches; leaves as crossed cards, or sprays set along the branches", fill=SOFT, font=font(26))
    slots = [(k, os.path.join(TILES, k + ".png")) for k in keys] + [("cards", os.path.join(HERE, "previews", "leaf_cards.png"))]
    for i, (key, path) in enumerate(slots):
        x = pad + (i % cols) * (tw + pad)
        y = 150 + (i // cols) * (th + cap + pad)
        img = Image.open(path).convert("RGB")
        if key == "cards":
            img.thumbnail((tw, th))
            sheet.paste(img, (x, y + (th - img.height) // 2))
            d.text((x, y + th + 14), "Leaf cards", fill=INK, font=font(34))
            d.text((x, y + th + 60), "five to ten designs per tree, 512 x 512 with alpha", fill=SOFT, font=font(22))
            continue
        sheet.paste(img.resize((tw, th), Image.LANCZOS), (x, y))
        t = info[key]
        d.text((x, y + th + 14), t["name"], fill=INK, font=font(34))
        d.text((x, y + th + 60), f"{t['swedish']} · {t['latin']}", fill=SOFT, font=font(22))
        d.text((x, y + th + 90), f"about {t['height']:.0f} m · {t['cards']} leaf cards · {t['faces']} faces", fill=SOFT, font=font(20))
    out = os.path.join(HERE, "previews", "portfolio.png")
    sheet.save(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
