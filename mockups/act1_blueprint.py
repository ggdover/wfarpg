"""Compose the Act 1 blueprints: baked terrain + trees + paths (PIL), annotations (SVG via headless Chrome)."""
import json, math, os
from pathlib import Path
from PIL import Image, ImageDraw
import chrome

HERE = os.path.dirname(os.path.abspath(__file__))
A1 = os.path.join(HERE, "build", "act1")
D = json.load(open(os.path.join(A1, "world.json"), encoding="utf-8"))
ST = json.load(open(os.path.join(A1, "stats.json"), encoding="utf-8"))
PR = json.load(open(os.path.join(A1, "profile.json"), encoding="utf-8"))

TREE_COL = {0: ((47, 74, 41), (78, 108, 58)), 1: ((33, 56, 33), (56, 84, 50)), 2: ((111, 138, 64), (150, 172, 92)), 3: ((92, 83, 72), (128, 118, 104))}
LETTERS = "ABCDEFGHIJ"
MOOD = {"day": "Daylight", "fog": "Fog", "golden": "Sunset", "dusk": "Dusk and fog"}


def paint_map(name, scale):
    info = json.load(open(os.path.join(A1, name + ".json"), encoding="utf-8"))
    base = Image.open(os.path.join(A1, name + ".png")).convert("RGB")
    W = int(round((info["x1"] - info["x0"]) * scale))
    H = int(round((info["y1"] - info["y0"]) * scale))
    img = base.resize((W, H), Image.BICUBIC).convert("RGBA")
    x0, y1 = info["x0"], info["y1"]
    tf = lambda x, y: ((x - x0) * scale, (y1 - y) * scale)
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    crowns = Image.new("RGBA", img.size, (0, 0, 0, 0))
    cd = ImageDraw.Draw(crowns)
    rmul = {0: 2.6, 1: 2.9, 2: 2.3, 3: 1.6}
    for x, y, k in info["wall"]:
        px, py = tf(x, y)
        r = 3.2 * scale
        cd.ellipse((px - r, py - r, px + r, py + r), fill=(22, 34, 22, 255))
    for x, y, k in info["trees"]:
        px, py = tf(x, y)
        r = rmul[k] * scale * (0.85 + 0.3 * ((x * 7.3 + y * 3.1) % 1))
        sd.ellipse((px - r + 1.2 * scale, py - r + 1.4 * scale, px + r + 1.2 * scale, py + r + 1.4 * scale), fill=(0, 0, 0, 90))
        c0, c1 = TREE_COL[k]
        cd.ellipse((px - r, py - r, px + r, py + r), fill=c0 + (255,))
        cd.ellipse((px - r * 0.75, py - r * 0.8, px + r * 0.2, py + r * 0.15), fill=c1 + (255,))
    img = Image.alpha_composite(img, shadow)
    # paths under the crowns would hide them; draw paths, then crowns that are off-path
    pd = ImageDraw.Draw(img)
    for p in D["paths"].values():
        pts = [tf(x, y) for x, y in p["pts"]]
        if p["kind"] == "road":
            pd.line(pts, fill=(52, 38, 24, 255), width=int(7.5 * scale + 2), joint="curve")
            pd.line(pts, fill=(186, 150, 100, 255), width=int(5.0 * scale + 1), joint="curve")
        elif p["kind"] == "trail":
            pd.line(pts, fill=(52, 40, 26, 230), width=int(4.6 * scale + 2), joint="curve")
            pd.line(pts, fill=(204, 178, 132, 255), width=int(2.8 * scale + 1), joint="curve")
        else:
            pd.line(pts, fill=(40, 28, 16, 255), width=int(5.2 * scale + 2), joint="curve")
            pd.line(pts, fill=(160, 120, 74, 255), width=int(3.4 * scale + 1), joint="curve")
            for (ax, ay), (bx, by) in zip(pts[:-1], pts[1:]):
                L = math.hypot(bx - ax, by - ay)
                if L < 1:
                    continue
                nx, ny = -(by - ay) / L, (bx - ax) / L
                for k in range(int(L // (3 * scale)) + 1):
                    t = k * 3 * scale / L
                    cx, cy = ax + (bx - ax) * t, ay + (by - ay) * t
                    pd.line((cx - nx * 2.6 * scale, cy - ny * 2.6 * scale, cx + nx * 2.6 * scale, cy + ny * 2.6 * scale), fill=(60, 42, 24, 255), width=1)
    img = Image.alpha_composite(img, crowns)
    pd = ImageDraw.Draw(img)
    for p in D["paths"].values():  # repaint the path surface over crowns that overhang it
        pts = [tf(x, y) for x, y in p["pts"]]
        if p["kind"] == "road":
            pd.line(pts, fill=(186, 150, 100, 200), width=int(4.0 * scale + 1), joint="curve")
    out = os.path.join(A1, name + "_painted.png")
    img.convert("RGB").save(out)
    return out, info, tf, W, H


SIZES = {"longhouse": (20, 7.5), "barn": (12, 7), "cottage": (8, 5)}


def structures():
    out = [(x, y, r, SIZES[k][0], SIZES[k][1], "#7a2a1e" if k != "longhouse" else "#4f6a32") for x, y, r, k in D["houses"]]
    fx, fy = D["farm"]["c"]
    cx, cy = D["courtyard"]["c"]
    out += [(fx + 6, fy - 4, 20, 10, 6, "#2a2420"), (fx - 12, fy + 10, 15, 12, 7, "#7a2a1e"), (cx + 18, cy + 10, 0, 16, 9, "#77736a"),
            (152, 452, 20, 4, 4, "#4a3322"), (166, 448, 0, 3.5, 3.5, "#d9772a")]
    return out


def footprint_svg(T, scale):
    parts = []
    for x, y, rot, w, d, col in structures():
        px, py = T(x, y)
        parts.append(f'<rect x="{px - w * scale / 2:.1f}" y="{py - d * scale / 2:.1f}" width="{w * scale:.1f}" height="{d * scale:.1f}" '
                     f'fill="{col}" stroke="#f1e2bd" stroke-width="{0.6 if scale < 1.2 else 1.0}" transform="rotate({-rot} {px:.1f} {py:.1f})"/>')
    return "".join(parts)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;")


DEFS = """<defs>
<filter id="halo" x="-20%" y="-50%" width="140%" height="200%"><feMorphology operator="dilate" radius="2.2" in="SourceAlpha" result="d"/>
<feGaussianBlur in="d" stdDeviation="1.6" result="b"/><feFlood flood-color="#0b0906" flood-opacity="0.92"/><feComposite in2="b" operator="in" result="s"/>
<feMerge><feMergeNode in="s"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="drop" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="1.2" dy="2" stdDeviation="1.4" flood-color="#000" flood-opacity="0.8"/></filter>
<filter id="glow" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="2.4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>"""

GOLD, SILVER, TXT, MUTED, BRASS = "#d9a441", "#b9c6d3", "#ead9ae", "#a8977a", "#8a6a3c"


def pin(x, y, n, kind, r=13):
    fill = GOLD if kind == "main" else SILVER
    return (f'<g filter="url(#drop)"><path d="M{x},{y + r * 1.9} L{x - r * 0.62},{y + r * 0.6} A{r},{r} 0 1,1 {x + r * 0.62},{y + r * 0.6} Z" fill="{fill}" stroke="#1b130a" stroke-width="1.6"/>'
            f'<text x="{x}" y="{y + r * 0.42}" text-anchor="middle" font-family="Cinzel" font-weight="900" font-size="{r * 1.15:.0f}" fill="#1b130a">{n}</text></g>')


def waystone(x, y, s=8):
    return (f'<g filter="url(#glow)"><polygon points="{x},{y - s * 1.5} {x + s},{y} {x},{y + s * 1.5} {x - s},{y}" fill="#1c3a44" stroke="#7fe3f2" stroke-width="1.6"/>'
            f'<line x1="{x}" y1="{y - s * 0.8}" x2="{x}" y2="{y + s * 0.8}" stroke="#bff6ff" stroke-width="1.4"/></g>')


def camera(x, y, yaw, letter, L=70):
    view = math.radians(yaw + 180)
    fov = math.radians(27)
    # map y grows downwards, world y grows north
    p1 = (x + math.cos(view - fov) * L, y - math.sin(view - fov) * L)
    p2 = (x + math.cos(view + fov) * L, y - math.sin(view + fov) * L)
    cx, cy = x - math.cos(view) * 16, y + math.sin(view) * 16
    return (f'<polygon points="{x:.1f},{y:.1f} {p1[0]:.1f},{p1[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}" fill="#ffffff" fill-opacity="0.16" stroke="#ffffff" stroke-opacity="0.7" stroke-width="1.2" stroke-dasharray="4 3"/>'
            f'<g filter="url(#drop)"><rect x="{cx - 11:.1f}" y="{cy - 11:.1f}" width="22" height="22" fill="#11161a" stroke="#e8f4fa" stroke-width="1.6" transform="rotate(45 {cx:.1f} {cy:.1f})"/>'
            f'<text x="{cx:.1f}" y="{cy + 5:.1f}" text-anchor="middle" font-family="Cinzel" font-weight="900" font-size="14" fill="#e8f4fa">{letter}</text></g>')


def label(x, y, text, size, fill=TXT, family="Cinzel", weight=700, anchor="middle", spacing=0):
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-family="{family}" font-weight="{weight}" font-size="{size}" '
            f'letter-spacing="{spacing}" fill="{fill}" filter="url(#halo)">{esc(text)}</text>')


def render(svg, w, h, out):
    html = ("<html><head><meta charset='utf-8'><style>@font-face{font-family:Cinzel;src:url(fonts/Cinzel.ttf);font-weight:400 900}"
            "@font-face{font-family:CinzelDeco;src:url(fonts/CinzelDecorative-Bold.ttf)}html,body{margin:0;background:#15120f}</style></head>"
            f"<body>{svg}</body></html>")
    hp = os.path.join(HERE, "_bp.html")
    with open(hp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)
    chrome.screenshot(hp, out, w, h, "--virtual-time-budget=4000", timeout=180)
    print("wrote", out)


def panel(x, y, w, h, title):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#1d1813" stroke="{BRASS}" stroke-width="1.5"/>'
            f'<rect x="{x + 5}" y="{y + 5}" width="{w - 10}" height="{h - 10}" fill="none" stroke="#3a2f22" stroke-width="1"/>'
            f'<text x="{x + 22}" y="{y + 38}" font-family="Cinzel" font-weight="700" font-size="21" fill="{TXT}" letter-spacing="1.5">{esc(title)}</text>'
            f'<line x1="{x + 22}" y1="{y + 50}" x2="{x + w - 22}" y2="{y + 50}" stroke="{BRASS}" stroke-width="1"/>')


def legend_items(x, y, items, gap=34):
    out = []
    for i, (sym, text) in enumerate(items):
        yy = y + i * gap
        out.append(f'<g transform="translate({x} {yy})">{sym}</g>')
        out.append(f'<text x="{x + 40}" y="{yy + 6}" font-family="Cinzel" font-size="15" fill="{TXT}">{esc(text)}</text>')
    return "".join(out)


def legend_symbols():
    sw = lambda c: f'<rect x="-14" y="-9" width="28" height="18" fill="{c}" stroke="#000" stroke-width="0.8"/>'
    return [
        (pin(0, -8, 1, "main", 10), "Main quest"),
        (pin(0, -8, 2, "side", 10), "Side quest"),
        (waystone(0, 0, 6), "Waystone (fast travel)"),
        ('<polygon points="-12,-12 14,-4 14,8 -12,0" fill="#fff" fill-opacity="0.2" stroke="#fff" stroke-opacity="0.7" stroke-dasharray="3 2"/>', "Screenshot camera"),
        ('<line x1="-15" y1="0" x2="15" y2="0" stroke="#342618" stroke-width="7"/><line x1="-15" y1="0" x2="15" y2="0" stroke="#ba9664" stroke-width="4.5"/>', "Road"),
        ('<line x1="-15" y1="0" x2="15" y2="0" stroke="#342818" stroke-width="5"/><line x1="-15" y1="0" x2="15" y2="0" stroke="#ccb284" stroke-width="2.6"/>', "Trail / boardwalk"),
        (sw("#a7ae62"), "Open meadow, fields"),
        ('<circle cx="-6" cy="0" r="5" fill="#2f4a29"/><circle cx="5" cy="-2" r="5" fill="#213821"/><circle cx="1" cy="5" r="4" fill="#6f8a40"/>', "Pine, spruce, birch"),
        (sw("#3d6c86"), "Water"),
        (sw("#7d8790"), "Fog zone"),
        (sw("#22241f"), "Impassable: dense forest wall"),
        ('<path d="M-14,4 C-6,-8 6,-8 14,4" fill="none" stroke="#2b2a20" stroke-width="1.2"/><path d="M-14,9 C-6,-3 6,-3 14,9" fill="none" stroke="#2b2a20" stroke-width="2"/>', "Contours: 2 m, bold every 10 m"),
    ]


ZONE_LABEL = {"town": (150, -62), "storskogen": (150, 590), "harddalen": (560, 940), "gamlagarden": (740, 190),
              "dimskogen": (-440, 800), "dimmyren": (-480, 60), "odeskogen": (-1160, 395)}


def overview():
    mpath, info, tf, MW, MH = paint_map("overview", 1.0)
    ox, oy = 24, 116
    PW = 640
    CW, CH = ox + MW + 24 + PW + 24, oy + MH + 30
    T = lambda x, y: (tf(x, y)[0] + ox, tf(x, y)[1] + oy)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{CW}" height="{CH}" viewBox="0 0 {CW} {CH}">', DEFS,
         f'<rect width="{CW}" height="{CH}" fill="#15120f"/>',
         f'<text x="{ox}" y="58" font-family="Cinzel" font-weight="900" font-size="42" fill="{TXT}" letter-spacing="1">Act I — The Pine Forest</text>',
         f'<text x="{ox + 2}" y="92" font-family="Cinzel" font-weight="700" font-size="17" fill="{MUTED}" letter-spacing="1">Layout blueprint · zones traced from act1_layout.png · grid squares are 100 m · north is up</text>',
         f'<rect x="{ox - 3}" y="{oy - 3}" width="{MW + 6}" height="{MH + 6}" fill="none" stroke="{BRASS}" stroke-width="2"/>',
         f'<image href="{Path(mpath).as_uri()}" x="{ox}" y="{oy}" width="{MW}" height="{MH}"/>']
    # 100 m grid
    for gx in range(-1400, 1000, 100):
        x, _ = T(gx, 0)
        s.append(f'<line x1="{x:.1f}" y1="{oy}" x2="{x:.1f}" y2="{oy + MH}" stroke="#ffffff" stroke-opacity="0.07" stroke-width="1"/>')
    for gy in range(-100, 1100, 100):
        _, y = T(0, gy)
        if oy <= y <= oy + MH:
            s.append(f'<line x1="{ox}" y1="{y:.1f}" x2="{ox + MW}" y2="{y:.1f}" stroke="#ffffff" stroke-opacity="0.07" stroke-width="1"/>')
    s.append(footprint_svg(T, 1.0))
    # sub-areas, zones
    for a in D["areas"]:
        x, y = T(*a["pos"])
        s.append(label(x, y, a["sv"], 14, "#f3e9cf", weight=700, spacing=0.5))
    for k, z in D["zones"].items():
        x, y = T(*ZONE_LABEL[k])
        sz = 38 if k == "storskogen" else (24 if k == "town" else 30)
        s.append(label(x, y, z["name"], sz, TXT, family="CinzelDeco", weight=700))
        s.append(label(x, y + 22, f'{z["orig"]} · {MOOD[z["mood"]]}', 13.5, "#cbbd98", weight=700, spacing=0.6))
    for ws in D["waystones"].values():
        s.append(waystone(*T(*ws)))
    for i, sh in enumerate(D["shots"]):
        s.append(camera(*T(*sh["pos"]), sh["yaw"], LETTERS[i]))
    for q in D["quests"]:
        x, y = T(*q["pos"])
        s.append(pin(x, y - 26, q["id"], q["kind"]))
    # scale bar + north arrow
    sx, sy = ox + 40, oy + MH - 40
    s.append(f'<rect x="{sx - 14}" y="{sy - 34}" width="{300 + 28}" height="58" fill="#15120f" fill-opacity="0.75" stroke="{BRASS}" stroke-width="1"/>')
    for k in range(3):
        s.append(f'<rect x="{sx + k * 100}" y="{sy}" width="100" height="8" fill="{"#ead9ae" if k % 2 == 0 else "#2a241c"}" stroke="#000" stroke-width="0.8"/>')
    for k in range(4):
        s.append(f'<text x="{sx + k * 100}" y="{sy - 8}" text-anchor="middle" font-family="Cinzel" font-weight="700" font-size="13" fill="{TXT}">{k * 100} m</text>')
    nx_, ny_ = ox + MW - 60, oy + 70
    s.append(f'<g filter="url(#drop)"><polygon points="{nx_},{ny_ - 38} {nx_ + 13},{ny_ + 4} {nx_},{ny_ - 6} {nx_ - 13},{ny_ + 4}" fill="{TXT}" stroke="#000"/>'
             f'<text x="{nx_}" y="{ny_ + 28}" text-anchor="middle" font-family="Cinzel" font-weight="900" font-size="20" fill="{TXT}">N</text></g>')
    # right panel: quests and time budget
    px = ox + MW + 24
    s.append(panel(px, oy, PW, 700, "Quests and time budget"))
    zone_name = {k: z["name"] for k, z in D["zones"].items()}
    y = oy + 84
    for q in D["quests"]:
        s.append(pin(px + 34, y - 18, q["id"], q["kind"], 11))
        s.append(f'<text x="{px + 62}" y="{y - 4}" font-family="Cinzel" font-weight="700" font-size="16" fill="{TXT}">{esc(q["sv"])}</text>')
        s.append(f'<text x="{px + 62}" y="{y + 15}" font-family="Cinzel" font-size="13" fill="{MUTED}">{esc(q["en"])} · {esc(zone_name[q["zone"]])}</text>')
        s.append(f'<text x="{px + PW - 26}" y="{y + 4}" text-anchor="end" font-family="Cinzel" font-weight="700" font-size="15" fill="{TXT}">{q["min"]} min</text>')
        y += 44
    main_m = sum(q["min"] for q in D["quests"] if q["kind"] == "main")
    all_m = sum(q["min"] for q in D["quests"])
    travel = 12
    s.append(f'<line x1="{px + 22}" y1="{y - 18}" x2="{px + PW - 22}" y2="{y - 18}" stroke="{BRASS}" stroke-width="1"/>')
    s.append(f'<text x="{px + 26}" y="{y + 8}" font-family="Cinzel" font-weight="700" font-size="16" fill="{TXT}">Main story only: about {main_m + travel} min</text>')
    s.append(f'<text x="{px + 26}" y="{y + 32}" font-family="Cinzel" font-weight="700" font-size="16" fill="{TXT}">Everything: about {(all_m + travel) // 60} h {(all_m + travel) % 60} min</text>')
    s.append(f'<text x="{px + 26}" y="{y + 54}" font-family="Cinzel" font-size="13" fill="{MUTED}">Includes about {travel} min of travel and town visits</text>')
    ly = oy + 718
    s.append(panel(px, ly, PW, MH - 718, "Legend"))
    sy_ = legend_symbols()
    s.append(legend_items(px + 40, ly + 86, sy_[:6], 40))
    s.append(legend_items(px + 40 + PW / 2 - 34, ly + 86, sy_[6:], 40))
    s.append(f'<text x="{px + 26}" y="{ly + MH - 718 - 28}" font-family="Cinzel" font-size="13" fill="{MUTED}">Walkable everywhere: steepest slope {ST["max_slope"]:.0f}°, 95% of the ground under {ST["p95"]:.0f}°</text>')
    s.append("</svg>")
    render("".join(s), CW, CH, os.path.join(A1, "blueprint_act1.png"))


def storskogen():
    sc = 1.6
    mpath, info, tf, MW, MH = paint_map("storskogen", sc)
    ox, oy = 24, 112
    PW = 620
    CW, CH = ox + MW + 24 + PW + 24, oy + MH + 30
    T = lambda x, y: (tf(x, y)[0] + ox, tf(x, y)[1] + oy)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{CW}" height="{CH}" viewBox="0 0 {CW} {CH}">', DEFS,
         f'<rect width="{CW}" height="{CH}" fill="#15120f"/>',
         f'<text x="{ox}" y="56" font-family="CinzelDeco" font-size="40" fill="{TXT}">Storskogen</text>',
         f'<text x="{ox + 2}" y="88" font-family="Cinzel" font-weight="700" font-size="16" fill="{MUTED}" letter-spacing="1">The first zone · about 720 × 650 m · grid squares are 50 m · contours every 2 m</text>',
         f'<rect x="{ox - 3}" y="{oy - 3}" width="{MW + 6}" height="{MH + 6}" fill="none" stroke="{BRASS}" stroke-width="2"/>',
         f'<image href="{Path(mpath).as_uri()}" x="{ox}" y="{oy}" width="{MW}" height="{MH}"/>']
    for gx in range(-300, 480, 50):
        x, _ = T(gx, 0)
        s.append(f'<line x1="{x:.1f}" y1="{oy}" x2="{x:.1f}" y2="{oy + MH}" stroke="#ffffff" stroke-opacity="0.06" stroke-width="1"/>')
    for gy in range(-100, 650, 50):
        _, y = T(0, gy)
        if oy <= y <= oy + MH:
            s.append(f'<line x1="{ox}" y1="{y:.1f}" x2="{ox + MW}" y2="{y:.1f}" stroke="#ffffff" stroke-opacity="0.06" stroke-width="1"/>')
    s.append(footprint_svg(T, sc))
    # profile line
    a, b = PR["a"], PR["b"]
    (ax, ay), (bx, by) = T(*a), T(*b)
    s.append(f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}" stroke="#f6e7c0" stroke-width="2" stroke-dasharray="8 6" opacity="0.85"/>')
    for (x, y), t in (((ax, ay), "P1"), ((bx, by), "P2")):
        s.append(f'<g filter="url(#drop)"><circle cx="{x:.1f}" cy="{y:.1f}" r="13" fill="#f6e7c0" stroke="#000"/><text x="{x:.1f}" y="{y + 5:.1f}" text-anchor="middle" font-family="Cinzel" font-weight="900" font-size="12" fill="#1b130a">{t}</text></g>')
    for txt, pos in (("+18 m", (182, 452)), ("−10 m", (-205, 372)), ("+11 m", (-112, 262))):
        x, y = T(*pos)
        s.append(label(x, y, txt, 14, "#fff4d6", weight=900))
    nudge = {"Utsiktsberget": (0, 62), "Vägskälet": (52, 34)}
    for a_ in D["areas"]:
        dx_, dy_ = nudge.get(a_["sv"], (0, 0))
        x, y = T(a_["pos"][0] + dx_, a_["pos"][1] + dy_)
        s.append(label(x, y, a_["sv"], 20, TXT, weight=700))
        s.append(label(x, y + 18, a_["en"], 13, "#d9caa4", weight=700))
    for k in ("town", "harddalen", "gamlagarden", "dimskogen"):
        pos = {"town": (60, -80), "harddalen": (420, 625), "gamlagarden": (395, 12), "dimskogen": (-255, 625)}[k]
        x, y = T(*pos)
        s.append(label(x, y, "→ " + D["zones"][k]["name"], 16, "#f3e9cf", weight=900))
    for ws in D["waystones"].values():
        x, y = T(*ws)
        if ox < x < ox + MW and oy < y < oy + MH:
            s.append(waystone(x, y, 9))
    for i, sh in enumerate(D["shots"]):
        x, y = T(*sh["pos"])
        if ox < x < ox + MW and oy < y < oy + MH:
            s.append(camera(x, y, sh["yaw"], LETTERS[i], 90))
    for q in D["quests"]:
        x, y = T(*q["pos"])
        if ox < x < ox + MW and oy < y < oy + MH:
            s.append(pin(x, y - 30, q["id"], q["kind"], 15))
    sx, sy = ox + 36, oy + MH - 36
    s.append(f'<rect x="{sx - 14}" y="{sy - 34}" width="{100 * sc + 28:.0f}" height="58" fill="#15120f" fill-opacity="0.75" stroke="{BRASS}" stroke-width="1"/>')
    for k in range(2):
        s.append(f'<rect x="{sx + k * 50 * sc:.1f}" y="{sy}" width="{50 * sc:.1f}" height="8" fill="{"#ead9ae" if k == 0 else "#2a241c"}" stroke="#000" stroke-width="0.8"/>')
    for k in range(3):
        s.append(f'<text x="{sx + k * 50 * sc:.1f}" y="{sy - 8}" text-anchor="middle" font-family="Cinzel" font-weight="700" font-size="13" fill="{TXT}">{k * 50} m</text>')
    # right panel: what is where + profile
    px = ox + MW + 24
    s.append(panel(px, oy, PW, 600, "Landforms"))
    notes = [("Stora ängen, Hagen", "Wide open meadows, no trees: long sight lines and room to fight packs"),
             ("Tätskogen", "The thick of the pines, like the earlier screenshots: tight paths, ambushes"),
             ("Åsen", "A long glacial ridge (esker), 11 m high, with a trail along its crest"),
             ("Utsiktsberget", "Lookout hill, 18 m up, with the beacon tower and a view over the zone"),
             ("Trollgrytan", "A kettle hole 10 m down, with a grove, a small tarn and a stone circle"),
             ("Tjärnen", "A small lake at the edge of the great meadow"),
             ("Vägskälet", "The crossroads: roads to Härddalen, Gamla gården and Dimskogen")]
    y = oy + 88
    for t, d in notes:
        s.append(f'<text x="{px + 26}" y="{y}" font-family="Cinzel" font-weight="700" font-size="16.5" fill="{TXT}">{esc(t)}</text>')
        words, line, lines = d.split(), "", []
        for w_ in words:
            if len(line) + len(w_) > 58:
                lines.append(line)
                line = w_
            else:
                line = (line + " " + w_).strip()
        lines.append(line)
        for j, l in enumerate(lines):
            s.append(f'<text x="{px + 26}" y="{y + 21 + j * 18}" font-family="Cinzel" font-size="13.5" fill="{MUTED}">{esc(l)}</text>')
        y += 30 + 18 * len(lines) + 8
    # profile chart
    cy0 = oy + 620
    ch = MH - 620
    s.append(panel(px, cy0, PW, ch, "Height profile P1 → P2"))
    gx0, gx1 = px + 60, px + PW - 30
    gy0, gy1 = cy0 + 80, cy0 + ch - 110
    dmax = max(PR["d"])
    hmin, hmax = -12, 20
    X = lambda d: gx0 + (gx1 - gx0) * d / dmax
    Y = lambda h: gy1 - (gy1 - gy0) * (h - hmin) / (hmax - hmin)
    for hv in range(-10, 21, 10):
        s.append(f'<line x1="{gx0}" y1="{Y(hv):.1f}" x2="{gx1}" y2="{Y(hv):.1f}" stroke="#ffffff" stroke-opacity="0.12"/>'
                 f'<text x="{gx0 - 8}" y="{Y(hv) + 4:.1f}" text-anchor="end" font-family="Cinzel" font-size="12" fill="{MUTED}">{hv:+d} m</text>')
    for dv in range(0, int(dmax) + 1, 100):
        s.append(f'<text x="{X(dv):.1f}" y="{gy1 + 20}" text-anchor="middle" font-family="Cinzel" font-size="12" fill="{MUTED}">{dv} m</text>')
    pts = " ".join(f"{X(d):.1f},{Y(h):.1f}" for d, h in zip(PR["d"], PR["h"]))
    s.append(f'<polygon points="{X(0):.1f},{gy1} {pts} {X(dmax):.1f},{gy1}" fill="#5d7838" fill-opacity="0.55"/>')
    s.append(f'<polyline points="{pts}" fill="none" stroke="#ead9ae" stroke-width="2"/>')
    for name_, dd in (("Trollgrytan", 96), ("Åsen", 228), ("Utsiktsberget", 448)):
        idx = min(range(len(PR["d"])), key=lambda i: abs(PR["d"][i] - dd))
        s.append(f'<text x="{X(PR["d"][idx]):.1f}" y="{Y(PR["h"][idx]) - 12:.1f}" text-anchor="middle" font-family="Cinzel" font-weight="700" font-size="13" fill="{TXT}" filter="url(#halo)">{name_}</text>')
    pmax = max(PR["slope"])
    exag = ((gy1 - gy0) / (hmax - hmin)) / ((gx1 - gx0) / dmax)
    s.append(f'<text x="{px + 26}" y="{gy1 + 52}" font-family="Cinzel" font-weight="700" font-size="14.5" fill="{TXT}">Height drawn {exag:.0f}× exaggerated. Steepest on this line: {pmax:.0f}°.</text>')
    s.append(f'<text x="{px + 26}" y="{gy1 + 74}" font-family="Cinzel" font-size="13.5" fill="{MUTED}">Across all of Act 1 the steepest walkable slope is {ST["max_slope"]:.0f}°,</text>')
    s.append(f'<text x="{px + 26}" y="{gy1 + 92}" font-family="Cinzel" font-size="13.5" fill="{MUTED}">so every slope can be walked: no ropes or ladders.</text>')
    s.append("</svg>")
    render("".join(s), CW, CH, os.path.join(A1, "blueprint_storskogen.png"))


if __name__ == "__main__":
    overview()
    storskogen()
