"""HUD v2: sharper, more detailed Norse ARPG HUD (hard edges, hammered iron, brass hairlines, engraved details).

python3 hud_sharp.py <src_dir> <dst_dir> <shot> [<shot> ...]
python3 hud_sharp.py --icons <dst_png>
"""
import json, math, os, random, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1600, 900
rng = random.Random(4)

STYLE = """
@font-face { font-family: Cinzel; src: url(fonts/Cinzel.ttf); font-weight: 400 900; }
@font-face { font-family: CinzelDeco; src: url(fonts/CinzelDecorative-Bold.ttf); font-weight: 700; }
html, body { margin: 0; background: transparent; }
svg { display: block; text-rendering: geometricPrecision; }
"""

IRON = "#2c2825"
IRON_L = "#4a4440"
BRASS = "#8a6a3c"
BRASS_L = "#d9b77a"
TEXT = "#e4d2a6"

DEFS = """
<defs>
  <filter id="metal" x="-5%" y="-5%" width="110%" height="110%" color-interpolation-filters="sRGB">
    <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" seed="4" result="n"/>
    <feDiffuseLighting in="n" surfaceScale="1.4" diffuseConstant="1.05" lighting-color="#ffffff" result="d">
      <feDistantLight azimuth="225" elevation="58"/></feDiffuseLighting>
    <feComposite in="d" in2="SourceAlpha" operator="in" result="dm"/>
    <feBlend in="SourceGraphic" in2="dm" mode="multiply" result="tex"/>
    <feGaussianBlur in="SourceAlpha" stdDeviation="0.7" result="ab"/>
    <feSpecularLighting in="ab" surfaceScale="2.2" specularConstant="0.75" specularExponent="22" lighting-color="#fff0d0" result="s">
      <feDistantLight azimuth="225" elevation="32"/></feSpecularLighting>
    <feComposite in="s" in2="SourceAlpha" operator="in" result="sm"/>
    <feComposite in="tex" in2="sm" operator="arithmetic" k1="0" k2="1" k3="0.6" k4="0"/>
  </filter>
  <filter id="paint" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">
    <feTurbulence type="fractalNoise" baseFrequency="0.32 0.95" numOctaves="3" seed="9" result="n"/>
    <feDiffuseLighting in="n" surfaceScale="1.8" lighting-color="#ffffff" result="d"><feDistantLight azimuth="200" elevation="62"/></feDiffuseLighting>
    <feComposite in="d" in2="SourceAlpha" operator="in" result="dm"/>
    <feBlend in="SourceGraphic" in2="dm" mode="multiply"/>
  </filter>
  <filter id="stone" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">
    <feTurbulence type="fractalNoise" baseFrequency="0.14" numOctaves="5" seed="5" result="n"/>
    <feDiffuseLighting in="n" surfaceScale="3" lighting-color="#ffffff" result="d"><feDistantLight azimuth="220" elevation="50"/></feDiffuseLighting>
    <feComposite in="d" in2="SourceAlpha" operator="in" result="dm"/>
    <feBlend in="SourceGraphic" in2="dm" mode="multiply"/>
  </filter>
  <filter id="wood" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">
    <feTurbulence type="fractalNoise" baseFrequency="0.04 0.7" numOctaves="3" seed="8" result="n"/>
    <feDiffuseLighting in="n" surfaceScale="2" lighting-color="#ffffff" result="d"><feDistantLight azimuth="180" elevation="55"/></feDiffuseLighting>
    <feComposite in="d" in2="SourceAlpha" operator="in" result="dm"/>
    <feBlend in="SourceGraphic" in2="dm" mode="multiply"/>
  </filter>
  <filter id="liquid" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">
    <feTurbulence type="turbulence" baseFrequency="0.05" numOctaves="4" seed="11" result="t"/>
    <feColorMatrix in="t" type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.11 0" result="tw"/>
    <feComposite in="tw" in2="SourceAlpha" operator="in" result="twm"/>
    <feBlend in="SourceGraphic" in2="twm" mode="screen" result="a"/>
    <feTurbulence type="fractalNoise" baseFrequency="0.7" numOctaves="2" seed="2" result="g"/>
    <feColorMatrix in="g" type="saturate" values="0" result="gg"/>
    <feComposite in="gg" in2="SourceAlpha" operator="in" result="ggm"/>
    <feComposite in="a" in2="ggm" operator="arithmetic" k1="0.35" k2="0.75" k3="0" k4="0" result="b"/>
    <feTurbulence type="turbulence" baseFrequency="0.028 0.06" numOctaves="3" seed="23" result="v"/>
    <feColorMatrix in="v" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -0.9 0.62" result="veins"/>
    <feComposite in="veins" in2="SourceAlpha" operator="in" result="vm"/>
    <feComposite in="vm" in2="b" operator="over"/>
  </filter>
  <filter id="tight" x="-40%" y="-40%" width="180%" height="180%">
    <feGaussianBlur stdDeviation="1.1" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="halo" x="-60%" y="-60%" width="220%" height="220%">
    <feGaussianBlur stdDeviation="2.4" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="drop" x="-10%" y="-10%" width="125%" height="130%">
    <feDropShadow dx="1.5" dy="2.5" stdDeviation="1.2" flood-color="#000" flood-opacity="0.85"/>
  </filter>
  <filter id="txt" x="-10%" y="-30%" width="120%" height="160%">
    <feDropShadow dx="1" dy="1.4" stdDeviation="0.5" flood-color="#000" flood-opacity="0.95"/>
  </filter>
  <linearGradient id="lifeFill" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#d23a22"/><stop offset="0.3" stop-color="#94130b"/><stop offset="1" stop-color="#2a0202"/>
  </linearGradient>
  <linearGradient id="manaFill" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#3f8de0"/><stop offset="0.3" stop-color="#14449c"/><stop offset="1" stop-color="#020a28"/>
  </linearGradient>
  <radialGradient id="orbShade" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0.62" stop-color="#000" stop-opacity="0"/><stop offset="0.92" stop-color="#000" stop-opacity="0.55"/><stop offset="1" stop-color="#000" stop-opacity="0.9"/>
  </radialGradient>
  <radialGradient id="vign" cx="0.5" cy="0.5" r="0.72">
    <stop offset="0.55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="0.75"/>
  </radialGradient>
  <linearGradient id="slash" x1="0" y1="1" x2="1" y2="0">
    <stop offset="0" stop-color="#a8360c" stop-opacity="0"/><stop offset="0.45" stop-color="#ff8a2a"/><stop offset="1" stop-color="#fff2cf"/>
  </linearGradient>
  <linearGradient id="frost" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#3fd0e6"/>
  </linearGradient>
  <linearGradient id="dmg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#fff4d2"/><stop offset="0.6" stop-color="#f2b24e"/><stop offset="1" stop-color="#c8561a"/>
  </linearGradient>
</defs>
"""


# ------------------------------------------------------------------ geometry helpers
def chamfer(x, y, w, h, c):
    return f"{x + c},{y} {x + w - c},{y} {x + w},{y + c} {x + w},{y + h - c} {x + w - c},{y + h} {x + c},{y + h} {x},{y + h - c} {x},{y + c}"


def pts(lst):
    return " ".join(f"{a:.1f},{b:.1f}" for a, b in lst)


def scratches(x0, y0, w, h, n, seed):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        x, y = r.uniform(x0, x0 + w), r.uniform(y0, y0 + h)
        a = r.uniform(-0.5, 0.5) + (math.pi if r.random() < 0.5 else 0)
        L = r.uniform(4, 16)
        out.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + math.cos(a) * L:.1f}" y2="{y + math.sin(a) * L:.1f}" '
                   f'stroke="#d8cbb4" stroke-opacity="{r.uniform(0.06, 0.16):.2f}" stroke-width="0.6"/>')
    return "".join(out)


def bolt(x, y, s=3.4):
    hexp = pts([(x + math.cos(k * math.pi / 3 + 0.3) * s, y + math.sin(k * math.pi / 3 + 0.3) * s) for k in range(6)])
    return (f'<polygon points="{hexp}" fill="#5a524b" stroke="#0d0b0a" stroke-width="0.8"/>'
            f'<polygon points="{pts([(x - s * 0.6, y - s * 0.2), (x - s * 0.1, y - s * 0.75), (x + s * 0.2, y - s * 0.45), (x - s * 0.35, y + s * 0.1)])}" fill="#c8bba8" opacity="0.75"/>')


def engraved(d, w=1.4):
    """A groove: dark cut plus a light lip below-right."""
    return (f'<path d="{d}" fill="none" stroke="#0a0807" stroke-width="{w + 0.6}" stroke-linejoin="miter" transform="translate(-0.4 -0.4)"/>'
            f'<path d="{d}" fill="none" stroke="#9a8a72" stroke-opacity="0.55" stroke-width="{w * 0.55}" transform="translate(0.7 0.7)"/>')


def triquetra(cx, cy, r):
    parts = []
    for k in range(3):
        a = math.radians(-90 + k * 120)
        b = math.radians(-90 + (k + 1) * 120)
        p0 = (cx + math.cos(a) * r, cy + math.sin(a) * r)
        p1 = (cx + math.cos(b) * r, cy + math.sin(b) * r)
        parts.append(f"M{p0[0]:.1f},{p0[1]:.1f} A{r * 0.95:.1f},{r * 0.95:.1f} 0 0,1 {p1[0]:.1f},{p1[1]:.1f}")
        parts.append(f"M{p0[0]:.1f},{p0[1]:.1f} A{r * 0.95:.1f},{r * 0.95:.1f} 0 0,0 {p1[0]:.1f},{p1[1]:.1f}")
    return engraved(" ".join(parts), 1.2) + engraved(f"M{cx + r * 0.62:.1f},{cy} A{r * 0.62:.1f},{r * 0.62:.1f} 0 1,1 {cx - r * 0.62:.1f},{cy} A{r * 0.62:.1f},{r * 0.62:.1f} 0 1,1 {cx + r * 0.62:.1f},{cy}", 1.0)


def crescent(cx, cy, R, a0, a1, thick, n=28):
    outer, inner = [], []
    for i in range(n + 1):
        s = i / n
        a = a0 + (a1 - a0) * s
        t = thick * math.sin(math.pi * s) ** 0.8
        outer.append((cx + math.cos(a) * R, cy + math.sin(a) * R))
        inner.append((cx + math.cos(a) * (R - t), cy + math.sin(a) * (R - t)))
    return pts(outer + inner[::-1])


# ------------------------------------------------------------------ ability icons (64x64)
def bg(inner, outer, flt="paint"):
    gid = "g" + inner[1:] + outer[1:]
    return (f'<radialGradient id="{gid}" cx="0.45" cy="0.4" r="0.75"><stop offset="0" stop-color="{inner}"/>'
            f'<stop offset="1" stop-color="{outer}"/></radialGradient><rect width="64" height="64" fill="url(#{gid})" filter="url(#{flt})"/>')


def icon_cleave():
    sparks = "".join(f'<polygon points="{pts([(x, y - 1.6), (x + 0.7, y), (x, y + 1.6), (x - 0.7, y)])}" fill="#fff0c4" transform="rotate({a} {x} {y})"/>'
                     for x, y, a in ((51, 11, 30), (56, 19, -20), (45, 7, 60), (59, 9, 10)))
    return bg("#3d160a", "#080302") + f"""
    <polygon points="{crescent(64, 64, 52, math.radians(185), math.radians(268), 13)}" fill="url(#slash)" filter="url(#tight)"/>
    <polyline points="{pts([(64 + math.cos(math.radians(a)) * 44, 64 + math.sin(math.radians(a)) * 44) for a in range(195, 262, 4)])}" fill="none" stroke="#ffe3a8" stroke-width="0.8" opacity="0.8"/>
    <polyline points="{pts([(64 + math.cos(math.radians(a)) * 56, 64 + math.sin(math.radians(a)) * 56) for a in range(205, 258, 4)])}" fill="none" stroke="#ff9a40" stroke-width="0.7" opacity="0.6"/>
    <g transform="rotate(-45 30 34)">
      <polygon points="30,2 33.6,9 33.6,40 30,40" fill="#dfe6ea"/>
      <polygon points="30,2 26.4,9 26.4,40 30,40" fill="#87939c"/>
      <polygon points="30,2 33.6,9 33.6,40 26.4,40 26.4,9" fill="none" stroke="#11161a" stroke-width="0.9" stroke-linejoin="miter"/>
      <line x1="30" y1="10" x2="30" y2="37" stroke="#4d5860" stroke-width="1.1"/>
      <polygon points="33.6,20 32.6,21.2 33.6,22.2" fill="#2a3036"/><polygon points="26.4,27 27.4,28 26.4,29.2" fill="#2a3036"/>
      <polygon points="19,40 41,40 43,43 39,45 21,45 17,43" fill="{BRASS}" stroke="#1a1006" stroke-width="0.9" filter="url(#metal)"/>
      <line x1="19.5" y1="41" x2="40.5" y2="41" stroke="{BRASS_L}" stroke-width="0.6" opacity="0.8"/>
      <rect x="27.8" y="45" width="4.4" height="11" fill="#3b2414" stroke="#120904" stroke-width="0.7"/>
      <g stroke="#7a5233" stroke-width="0.7">{''.join(f'<line x1="27.8" y1="{46 + k * 2}" x2="32.2" y2="{47.4 + k * 2}"/>' for k in range(5))}</g>
      <polygon points="30,55.5 33,57.5 33,60.5 30,62.5 27,60.5 27,57.5" fill="{BRASS}" stroke="#1a1006" stroke-width="0.8"/>
    </g>
    {sparks}"""


def icon_whirl():
    c = (32, 33)
    arcs = (f'<polygon points="{crescent(c[0], c[1], 25, math.radians(-150), math.radians(40), 6)}" fill="url(#frost)" opacity="0.95" filter="url(#tight)"/>'
            f'<polygon points="{crescent(c[0], c[1], 19, math.radians(60), math.radians(230), 5)}" fill="url(#frost)" opacity="0.8" filter="url(#tight)"/>'
            f'<polygon points="{crescent(c[0], c[1], 29, math.radians(80), math.radians(170), 3)}" fill="#c8fbff" opacity="0.55"/>')
    bits = "".join(f'<polygon points="{pts([(x, y), (x + 2.2, y + 0.8), (x + 0.6, y + 2.2)])}" fill="#9fe6d0" opacity="0.7" transform="rotate({a} {x} {y})"/>'
                   for x, y, a in ((10, 18, 20), (52, 50, 70), (48, 12, -30), (14, 48, 50)))
    return bg("#0c3138", "#020809") + arcs + f"""
    <g transform="rotate(35 32 33)">
      <rect x="30.4" y="16" width="3.4" height="32" fill="#5a3a20" stroke="#140a04" stroke-width="0.7"/>
      <line x1="31.4" y1="18" x2="31.4" y2="46" stroke="#8a6040" stroke-width="0.5"/>
      <polygon points="33.8,17 43,15.5 47,21 44.5,30 38,27.5 33.8,26" fill="#c9d2d8" stroke="#11161a" stroke-width="0.9"/>
      <polygon points="43,15.5 47,21 44.5,30 43.2,29.2 45.2,21.5 42,16.6" fill="#f2f7fa"/>
      <polygon points="33.8,17 38,16.6 38,26.6 33.8,26" fill="#7d8890"/>
      <rect x="29.6" y="45" width="5" height="3" fill="{BRASS}" stroke="#1a1006" stroke-width="0.6"/>
    </g>{bits}"""


def icon_charge():
    chev = ""
    for i, (x, op) in enumerate(((14, 0.38), (26, 0.65), (38, 1.0))):
        p = [(x, 13), (x + 9, 13), (x + 22, 32), (x + 9, 51), (x, 51), (x + 13, 32)]
        chev += (f'<polygon points="{pts(p)}" fill="#b8832a" opacity="{op}" stroke="#2a1704" stroke-width="1" stroke-linejoin="miter" filter="url(#metal)"/>'
                 f'<polyline points="{pts([(x + 1.5, 14), (x + 8.5, 14), (x + 20.6, 31.6)])}" fill="none" stroke="#ffe3a0" stroke-width="0.9" opacity="{op}"/>')
    streaks = "".join(f'<polygon points="{pts([(2, y), (16, y - 0.9), (16, y + 0.9)])}" fill="#ffdc8c" opacity="0.6"/>' for y in (20, 27, 37, 44))
    dust = "".join(f'<polygon points="{pts([(x, y), (x + 2.6, y - 1.2), (x + 3.4, y + 1.4), (x + 0.6, y + 2.2)])}" fill="#7a5a32" opacity="0.6"/>'
                   for x, y in ((5, 54), (10, 57), (3, 49), (15, 58)))
    return bg("#3f2808", "#0a0602") + streaks + dust + f'<g filter="url(#tight)">{chev}</g>'


def icon_ward():
    cracks = "".join(f'<polyline points="{pts(p)}" fill="none" stroke="#0a0c0e" stroke-width="0.8" opacity="0.8"/>' for p in (
        [(2, 40), (9, 42), (13, 47), (20, 49)], [(60, 8), (55, 14), (56, 20), (52, 25)], [(44, 62), (46, 55), (52, 52)]))
    rune = "M32,9 L32,56 M32,30 L17,12 M32,30 L47,12"
    ring = "".join(f'<text x="{32 + math.cos(a) * 27:.1f}" y="{33 + math.sin(a) * 27 + 2:.1f}" font-family="Noto Sans Runic" font-size="5.5" fill="#8fe8f5" opacity="0.45" text-anchor="middle">{ch}</text>'
                   for a, ch in zip([k * math.tau / 14 - math.pi / 2 for k in range(14)], "ᚠᚢᚦᚨᚱᚲᚷᚹᚺᚾᛁᛃᛇᛈ"))
    return bg("#575c62", "#121518", "stone") + cracks + ring + f"""
    <path d="{rune}" fill="none" stroke="#06080a" stroke-width="7.5" stroke-linecap="square" stroke-linejoin="miter" transform="translate(0.8 0.8)"/>
    <path d="{rune}" fill="none" stroke="#a7b0b6" stroke-width="7" stroke-linecap="square" stroke-linejoin="miter" opacity="0.35" transform="translate(-0.9 -0.9)"/>
    <path d="{rune}" fill="none" stroke="#5fd8ea" stroke-width="4.2" stroke-linecap="square" stroke-linejoin="miter" filter="url(#halo)"/>
    <path d="{rune}" fill="none" stroke="#e9feff" stroke-width="1.3" stroke-linecap="square" stroke-linejoin="miter"/>"""


def icon_shield():
    nails = "".join(f'<circle cx="{math.cos(k * math.tau / 14) * 21.6:.1f}" cy="{math.sin(k * math.tau / 14) * 21.6:.1f}" r="1.05" fill="#b5ab9e" stroke="#0f0d0b" stroke-width="0.5"/>' for k in range(14))
    planks = "".join(f'<line x1="{x}" y1="-25" x2="{x}" y2="25" stroke="#1d1007" stroke-width="0.9"/><line x1="{x + 0.9}" y1="-25" x2="{x + 0.9}" y2="25" stroke="#a07448" stroke-width="0.4" opacity="0.6"/>' for x in (-15, -8, 0, 8, 15))
    chips = "".join(f'<polygon points="{pts([(x, y), (x + rng.uniform(1.5, 3.5), y + rng.uniform(-1, 1)), (x + rng.uniform(0.5, 2.5), y + rng.uniform(1.2, 3))])}" fill="#5a3a20"/>'
                    for x, y in ((-12, -14), (6, -18), (14, 6), (-16, 9), (-3, 15), (9, -6), (-8, 2)))
    impact = "".join(f'<polygon points="{pts([(54, y), (63, y - 3 + k), (63, y - 1 + k)])}" fill="#fff0c4" opacity="0.85"/>' for k, y in enumerate((20, 32, 44)))
    return bg("#2e2016", "#090604") + f"""
    <g transform="translate(29 33)">
      <clipPath id="shieldclip"><circle r="23.5"/></clipPath>
      <g clip-path="url(#shieldclip)">
        <rect x="-25" y="-25" width="50" height="50" fill="#5f3e22" filter="url(#wood)"/>
        <path d="M0,0 L0,-25 L25,-25 L25,0 Z" fill="#8a1f16" opacity="0.92"/>
        <path d="M0,0 L0,25 L-25,25 L-25,0 Z" fill="#8a1f16" opacity="0.92"/>
        <path d="M0,0 L25,0 L25,25 L0,25 Z" fill="#c8b083" opacity="0.88"/>
        <path d="M0,0 L-25,0 L-25,-25 L0,-25 Z" fill="#c8b083" opacity="0.88"/>
        {chips}{planks}
      </g>
      <circle r="23.5" fill="none" stroke="#3b3734" stroke-width="3.6"/>
      <circle r="25.2" fill="none" stroke="#0c0a09" stroke-width="0.9"/>
      <path d="M-16.6,-16.6 A23.5,23.5 0 0,1 16.6,-16.6" fill="none" stroke="#a69c90" stroke-width="0.8"/>
      {nails}
      <circle r="7.2" fill="#6e767c" stroke="#0e1113" stroke-width="1"/>
      <path d="M-4.6,-3.8 A6,6 0 0,1 3.6,-5" fill="none" stroke="#f2f6f8" stroke-width="1.4"/>
      <circle cx="2.4" cy="2.6" r="1.6" fill="#2a3034" opacity="0.6"/>
    </g>{impact}"""


def icon_locked():
    links = ""
    for x, y in ((12, 12), (21, 21), (43, 43), (52, 52)):
        links += (f'<ellipse cx="{x}" cy="{y}" rx="6.6" ry="3.8" transform="rotate(45 {x} {y})" fill="none" stroke="#0c0c0c" stroke-width="3.6"/>'
                  f'<ellipse cx="{x}" cy="{y}" rx="6.6" ry="3.8" transform="rotate(45 {x} {y})" fill="none" stroke="#6b6660" stroke-width="2.2"/>'
                  f'<ellipse cx="{x - 0.6}" cy="{y - 0.6}" rx="6.6" ry="3.8" transform="rotate(45 {x} {y})" fill="none" stroke="#b9b2a8" stroke-width="0.5" stroke-dasharray="6 8"/>')
    return bg("#232221", "#070707") + links + f"""
    <path d="M24.5,30 L24.5,23 A7.5,7.5 0 0,1 39.5,23 L39.5,30" fill="none" stroke="#0c0c0c" stroke-width="5"/>
    <path d="M24.5,30 L24.5,23 A7.5,7.5 0 0,1 39.5,23 L39.5,30" fill="none" stroke="#8d877f" stroke-width="3.2"/>
    <polygon points="{chamfer(20, 29, 24, 19, 2)}" fill="#7a5c2e" stroke="#120b04" stroke-width="1" filter="url(#metal)"/>
    <line x1="21.5" y1="30.5" x2="42.5" y2="30.5" stroke="{BRASS_L}" stroke-width="0.6" opacity="0.7"/>
    <circle cx="23" cy="45" r="0.9" fill="#d9c08a"/><circle cx="41" cy="45" r="0.9" fill="#d9c08a"/>
    <circle cx="32" cy="36.5" r="2.4" fill="#0e0905"/><polygon points="31,37.5 33,37.5 33.6,43 30.4,43" fill="#0e0905"/>"""


ICONS = {"cleave": icon_cleave, "whirl": icon_whirl, "charge": icon_charge, "ward": icon_ward, "shield": icon_shield, "locked": icon_locked}
SLOTS = [("LMB", "cleave", "Cleave"), ("1", "whirl", "Whirlwind"), ("2", "charge", "Charge"),
         ("3", "ward", "Ward Rune"), ("4", "shield", "Shield Bash"), ("5", "locked", "Locked")]


def icon_svg(kind, x, y, size, uid):
    s = size / 64.0
    return (f'<g transform="translate({x} {y}) scale({s})"><clipPath id="c_{uid}"><polygon points="{chamfer(0, 0, 64, 64, 3)}"/></clipPath>'
            f'<g clip-path="url(#c_{uid})">{ICONS[kind]()}<rect width="64" height="64" fill="url(#vign)"/></g></g>')


def slot_frame(x, y, size, active=False):
    o = 5
    out = (f'<polygon points="{chamfer(x - o, y - o, size + 2 * o, size + 2 * o, 6)}" fill="{IRON}" stroke="#090807" stroke-width="1" filter="url(#metal)"/>'
           f'<polygon points="{chamfer(x - o + 1.5, y - o + 1.5, size + 2 * o - 3, size + 2 * o - 3, 5)}" fill="none" stroke="{BRASS}" stroke-width="1"/>'
           f'<polygon points="{chamfer(x - 1, y - 1, size + 2, size + 2, 3.5)}" fill="#050404"/>')
    return out


def slot_overlay(x, y, size, active=False):
    out = f'<polygon points="{chamfer(x, y, size, size, 3)}" fill="none" stroke="#000" stroke-opacity="0.8" stroke-width="1"/>'
    out += f'<polyline points="{x + 3},{y + size - 1} {x + 1},{y + size - 3} {x + 1},{y + 3} {x + 3},{y + 1} {x + size - 3},{y + 1}" fill="none" stroke="#fff" stroke-opacity="0.18" stroke-width="1"/>'
    if active:
        out += (f'<polygon points="{chamfer(x - 2.5, y - 2.5, size + 5, size + 5, 4.5)}" fill="none" stroke="#f3cf82" stroke-width="1.6" filter="url(#halo)"/>')
    return out


# ------------------------------------------------------------------ HUD pieces
def orb(cx, cy, r, frac, kind, label):
    fill = "lifeFill" if kind == "life" else "manaFill"
    dark = "#0a0201" if kind == "life" else "#01040f"
    gem = ("#e0321f", "#4a0704") if kind == "life" else ("#3d9bf0", "#06204e")
    level = cy + r - 2 * r * frac
    wave = [(cx - r + i * (2 * r / 24), level + math.sin(i * 0.75 + (0 if kind == "life" else 2)) * 1.6 + math.sin(i * 2.1) * 0.6) for i in range(25)]
    uid = kind
    clasps = ""
    for a in (-135, -45, 45, 135):
        t = math.radians(a)
        px, py = cx + math.cos(t) * (r + 5), cy + math.sin(t) * (r + 5)
        clasps += (f'<g transform="translate({px:.1f} {py:.1f}) rotate({a + 90})">'
                   f'<polygon points="-7,-5 7,-5 9,0 7,5 -7,5 -9,0" fill="{IRON_L}" stroke="#0a0908" stroke-width="0.9" filter="url(#metal)"/>'
                   f'<line x1="-6" y1="-3.6" x2="6" y2="-3.6" stroke="{BRASS_L}" stroke-width="0.6" opacity="0.6"/>{bolt(0, 0, 2.2)}</g>')
    return f"""
    <circle cx="{cx}" cy="{cy}" r="{r + 9}" fill="#0b0a09" filter="url(#drop)"/>
    <circle cx="{cx}" cy="{cy}" r="{r + 5}" fill="none" stroke="{IRON}" stroke-width="7" filter="url(#metal)"/>
    <circle cx="{cx}" cy="{cy}" r="{r + 8.6}" fill="none" stroke="{BRASS}" stroke-width="1.1"/>
    <circle cx="{cx}" cy="{cy}" r="{r + 1.4}" fill="none" stroke="{BRASS}" stroke-width="0.9"/>
    <clipPath id="oc_{uid}"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath>
    <g clip-path="url(#oc_{uid})">
      <rect x="{cx - r}" y="{cy - r}" width="{2 * r}" height="{2 * r}" fill="{dark}"/>
      <polygon points="{pts(wave)} {cx + r},{cy + r} {cx - r},{cy + r}" fill="url(#{fill})" filter="url(#liquid)"/>
      <polyline points="{pts(wave)}" fill="none" stroke="#ffffff" stroke-opacity="0.35" stroke-width="1"/>
      <rect x="{cx - r}" y="{cy - r}" width="{2 * r}" height="{2 * r}" fill="url(#orbShade)"/>
      <path d="M{cx - r * 0.72:.1f},{cy - r * 0.32:.1f} A{r * 0.8:.1f},{r * 0.8:.1f} 0 0,1 {cx + r * 0.1:.1f},{cy - r * 0.78:.1f} A{r * 0.9:.1f},{r * 0.9:.1f} 0 0,0 {cx - r * 0.72:.1f},{cy - r * 0.32:.1f} Z" fill="#ffffff" opacity="0.16"/>
      <circle cx="{cx - r * 0.42:.1f}" cy="{cy - r * 0.5:.1f}" r="{r * 0.045:.1f}" fill="#fff" opacity="0.6"/>
    </g>
    {clasps}
    <g transform="translate({cx} {cy - r - 9})">
      <polygon points="0,-10 9,0 0,10 -9,0" fill="{IRON_L}" stroke="#0a0908" stroke-width="1" filter="url(#metal)"/>
      <polygon points="0,-10 9,0 0,10 -9,0" fill="none" stroke="{BRASS}" stroke-width="0.8" transform="scale(0.78)"/>
      <polygon points="0,-4.6 4.2,0 0,4.6 -4.2,0" fill="{gem[0]}" stroke="{gem[1]}" stroke-width="0.8"/>
      <polygon points="0,-4.6 2.4,-1.8 -1.2,-1" fill="#fff" opacity="0.55"/>
    </g>
    <text x="{cx}" y="{cy - r - 26}" text-anchor="middle" font-family="Cinzel" font-weight="700" font-size="16" letter-spacing="0.5"
          fill="{TEXT}" filter="url(#txt)">{label}</text>
    """


def action_bar(active=None, cooldown=None, xp=0.63):
    size, gap = 64, 12
    n = len(SLOTS)
    total = n * size + (n - 1) * gap
    x0 = W / 2 - total / 2
    y0 = H - size - 22
    L, R = x0 - 30, x0 + total + 30
    T = y0 - 26
    plate = [(L - 74, H + 2), (L - 30, T + 16), (L - 18, T + 4), (L, T), (R, T), (R + 18, T + 4), (R + 30, T + 16), (R + 74, H + 2)]
    out = [f'<polygon points="{pts(plate)}" fill="{IRON}" stroke="#070606" stroke-width="1.2" filter="url(#drop)"/>',
           f'<polygon points="{pts(plate)}" fill="{IRON}" filter="url(#metal)"/>',
           f'<polyline points="{pts(plate[1:-1])}" fill="none" stroke="{BRASS}" stroke-width="1.3"/>',
           f'<polyline points="{pts([(p[0], p[1] + 3.5) for p in plate[2:-2]])}" fill="none" stroke="#000" stroke-opacity="0.6" stroke-width="1"/>',
           scratches(L - 40, T + 6, R - L + 80, H - T - 6, 70, 17)]
    # experience bar: segmented, sharp
    bx0, bx1, by = L + 6, R - 6, T + 7
    out.append(f'<rect x="{bx0}" y="{by}" width="{bx1 - bx0}" height="6" fill="#070605" stroke="#000" stroke-width="0.8"/>')
    out.append(f'<rect x="{bx0 + 1}" y="{by + 1}" width="{(bx1 - bx0 - 2) * xp:.1f}" height="4" fill="#c08a2c"/>')
    out.append(f'<rect x="{bx0 + 1}" y="{by + 1}" width="{(bx1 - bx0 - 2) * xp:.1f}" height="1.2" fill="#ffe2a0" opacity="0.8"/>')
    for k in range(1, 10):
        tx = bx0 + (bx1 - bx0) * k / 10
        out.append(f'<line x1="{tx:.1f}" y1="{by}" x2="{tx:.1f}" y2="{by + 6}" stroke="#000" stroke-width="1"/>')
    # engraved knots on the shoulders, bolts at the corners
    out.append(triquetra(L - 26, H - 30, 11))
    out.append(triquetra(R + 26, H - 30, 11))
    out.append(engraved(f"M{L + 4},{H - 8} L{R - 4},{H - 8}", 1.0))
    for bx, byy in ((L + 8, T + 20), (R - 8, T + 20), (L - 40, H - 12), (R + 40, H - 12)):
        out.append(bolt(bx, byy))
    for i, (key, kind, _) in enumerate(SLOTS):
        x = x0 + i * (size + gap)
        out.append(slot_frame(x, y0, size))
        out.append(icon_svg(kind, x, y0, size, "s" + str(i)))
        if kind == "locked":
            out.append(f'<polygon points="{chamfer(x, y0, size, size, 3)}" fill="#000" opacity="0.42"/>')
        if key == cooldown:
            cx_, cy_, rr = x + size / 2, y0 + size / 2, size * 0.75
            a = math.radians(-90 + 360 * 0.62)
            out.append(f'<clipPath id="cd{i}"><polygon points="{chamfer(x, y0, size, size, 3)}"/></clipPath>'
                       f'<path clip-path="url(#cd{i})" d="M{cx_},{cy_} L{cx_},{cy_ - rr} A{rr},{rr} 0 1,1 {cx_ + math.cos(a) * rr:.1f},{cy_ + math.sin(a) * rr:.1f} Z" fill="#000" opacity="0.66"/>'
                       f'<line x1="{cx_}" y1="{cy_}" x2="{cx_ + math.cos(a) * rr:.1f}" y2="{cy_ + math.sin(a) * rr:.1f}" stroke="#f3cf82" stroke-width="1" clip-path="url(#cd{i})" opacity="0.8"/>'
                       f'<text x="{cx_}" y="{cy_ + 9}" text-anchor="middle" font-family="Cinzel" font-weight="900" font-size="25" fill="#f3e3bd" filter="url(#txt)">3</text>')
        out.append(slot_overlay(x, y0, size, key == active))
        kw = 28 if len(key) > 1 else 16
        kx, ky = x + 2, y0 + size - 12
        out.append(f'<polygon points="{chamfer(kx, ky, kw, 14, 2)}" fill="#0e0b08" stroke="{BRASS}" stroke-width="0.9"/>'
                   f'<text x="{kx + kw / 2}" y="{ky + 10.5}" text-anchor="middle" font-family="Cinzel" font-weight="700" font-size="10" fill="{TEXT}">{key}</text>')
        if i < n - 1:
            sx = x + size + gap / 2
            out.append(f'<polygon points="{sx},{y0 + size / 2 - 5} {sx + 3},{y0 + size / 2} {sx},{y0 + size / 2 + 5} {sx - 3},{y0 + size / 2}" fill="{BRASS}" stroke="#0a0705" stroke-width="0.6"/>')
    return "".join(out), x0, total, L, R


def minimap(info):
    R = 86
    cx, cy = W - 40 - R, 38 + R
    px, py = info["player_world"]
    yaw = math.radians(info.get("yaw", 225.0))
    fwd = (-math.cos(yaw), -math.sin(yaw))
    right = (fwd[1], -fwd[0])
    scale = info.get("mm_scale", 3.0)

    def mm(x, y):
        dx, dy = x - px, y - py
        return (cx + (dx * right[0] + dy * right[1]) * scale, cy - (dx * fwd[0] + dy * fwd[1]) * scale)

    paths = "".join('<polyline points="%s" fill="none" stroke="#b8935c" stroke-width="3.6" stroke-linecap="butt" stroke-linejoin="miter" opacity="0.95"/>'
                    % pts([mm(x, y) for x, y in p]) for p in info["paths"])
    waters = info.get("waters") or ([info["tarn"]] if info.get("tarn") else [])
    water_svg = "".join('<polygon points="%s" fill="#28546d" stroke="#6f9cb6" stroke-width="1"/>' % pts([mm(x, y) for x, y in w]) for w in waters)
    bog = info.get("bog")
    bog_svg = ""
    if bog:
        bcx, bcy = mm(bog[0], bog[1])
        bog_svg = '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="#3a3622" opacity="0.9"/>' % (bcx, bcy, bog[2] * scale)
    f = info["facing"] + math.pi / 2
    fx, fy = math.cos(f), math.sin(f)
    ang = math.degrees(math.atan2(-(fx * fwd[0] + fy * fwd[1]), fx * right[0] + fy * right[1]))
    nx, ny = right[1], fwd[1]
    nang = math.degrees(math.atan2(-ny, nx)) + 90
    fog = info["mode"] in ("fog", "dusk")
    studs = ""
    for a in (45, 135, 225, 315):
        t = math.radians(a)
        studs += (f'<g transform="translate({cx + math.cos(t) * (R + 5):.1f} {cy + math.sin(t) * (R + 5):.1f}) rotate({a + 90})">'
                  f'<polygon points="-6,-4 6,-4 8,0 6,4 -6,4 -8,0" fill="{IRON_L}" stroke="#0a0908" stroke-width="0.8" filter="url(#metal)"/>{bolt(0, 0, 1.9)}</g>')
    return f"""
    <circle cx="{cx}" cy="{cy}" r="{R + 9}" fill="#0b0a09" filter="url(#drop)"/>
    <clipPath id="mmclip"><circle cx="{cx}" cy="{cy}" r="{R}"/></clipPath>
    <g clip-path="url(#mmclip)">
      <rect x="{cx - R}" y="{cy - R}" width="{2 * R}" height="{2 * R}" fill="{'#2a3033' if fog else '#232b1c'}" filter="url(#paint)"/>
      {bog_svg}
      {water_svg}
      {paths}
      {'<rect x="%d" y="%d" width="%d" height="%d" fill="#c9d3dc" opacity="0.2"/>' % (cx - R, cy - R, 2 * R, 2 * R) if fog else ''}
      <circle cx="{cx}" cy="{cy}" r="{R}" fill="url(#orbShade)"/>
    </g>
    <g transform="translate({cx} {cy}) rotate({ang:.1f})">
      <polygon points="10,0 -7,-6.5 -3.5,0 -7,6.5" fill="#f0c674" stroke="#1a1004" stroke-width="1.2" stroke-linejoin="miter"/>
    </g>
    <circle cx="{cx}" cy="{cy}" r="{R + 4.5}" fill="none" stroke="{IRON}" stroke-width="7" filter="url(#metal)"/>
    <circle cx="{cx}" cy="{cy}" r="{R + 8.3}" fill="none" stroke="{BRASS}" stroke-width="1"/>
    <circle cx="{cx}" cy="{cy}" r="{R + 0.8}" fill="none" stroke="{BRASS}" stroke-width="0.9"/>
    {studs}
    <g transform="translate({cx + nx * (R + 5):.1f} {cy - ny * (R + 5):.1f}) rotate({nang:.1f})">
      <polygon points="0,-13 9,-4 6,9 -6,9 -9,-4" fill="{IRON_L}" stroke="#0a0908" stroke-width="1" filter="url(#metal)"/>
      <polygon points="0,-13 9,-4 6,9 -6,9 -9,-4" fill="none" stroke="{BRASS}" stroke-width="0.8" transform="scale(0.8)"/>
    </g>
    <text x="{cx + nx * (R + 5):.1f}" y="{cy - ny * (R + 5) + 5:.1f}" text-anchor="middle" font-family="Cinzel" font-weight="900" font-size="12" fill="{TEXT}">N</text>
    <text x="{cx}" y="{cy + R + 36}" text-anchor="middle" font-family="Cinzel" font-weight="700" font-size="12" letter-spacing="4.5" fill="#b8a273" filter="url(#txt)">ACT I</text>
    <line x1="{cx - 70}" y1="{cy + R + 43}" x2="{cx - 22}" y2="{cy + R + 43}" stroke="{BRASS}" stroke-width="0.8"/>
    <line x1="{cx + 22}" y1="{cy + R + 43}" x2="{cx + 70}" y2="{cy + R + 43}" stroke="{BRASS}" stroke-width="0.8"/>
    <polygon points="{cx},{cy + R + 39.5} {cx + 4},{cy + R + 43} {cx},{cy + R + 46.5} {cx - 4},{cy + R + 43}" fill="{BRASS}"/>
    <text x="{cx}" y="{cy + R + 66}" text-anchor="middle" font-family="CinzelDeco" font-size="21" fill="{TEXT}" filter="url(#txt)">{info.get("zone_name", "Pine Forest")}</text>
    {'<text x="%d" y="%d" text-anchor="middle" font-family="Cinzel" font-weight="700" font-size="12.5" fill="#b9dcf2" filter="url(#txt)">&#10052; The fog has rolled in</text>' % (cx, cy + R + 86) if fog else ''}
    """


def target_frame(name, frac):
    w, h = 420, 56
    x0, y0 = W / 2 - w / 2, 22
    shape = [(x0 + 24, y0), (x0 + w - 24, y0), (x0 + w, y0 + h / 2), (x0 + w - 24, y0 + h), (x0 + 24, y0 + h), (x0, y0 + h / 2)]
    inner = [(x0 + 27, y0 + 3), (x0 + w - 27, y0 + 3), (x0 + w - 4, y0 + h / 2), (x0 + w - 27, y0 + h - 3), (x0 + 27, y0 + h - 3), (x0 + 4, y0 + h / 2)]
    bw = w - 92
    bar = (f'<rect x="{x0 + 46}" y="{y0 + 32}" width="{bw}" height="11" fill="#090404" stroke="#000" stroke-width="1"/>'
           f'<rect x="{x0 + 47}" y="{y0 + 33}" width="{(bw - 2) * frac:.1f}" height="9" fill="#8e140c"/>'
           f'<rect x="{x0 + 47}" y="{y0 + 33}" width="{(bw - 2) * frac:.1f}" height="2.2" fill="#e0533a" opacity="0.85"/>'
           + "".join(f'<line x1="{x0 + 46 + bw * k / 8:.1f}" y1="{y0 + 32}" x2="{x0 + 46 + bw * k / 8:.1f}" y2="{y0 + 43}" stroke="#000" stroke-width="1" opacity="0.7"/>' for k in range(1, 8)))
    return (f'<polygon points="{pts(shape)}" fill="{IRON}" stroke="#070606" stroke-width="1.2" filter="url(#drop)"/>'
            f'<polygon points="{pts(shape)}" fill="{IRON}" filter="url(#metal)"/>'
            f'<polygon points="{pts(inner)}" fill="none" stroke="{BRASS}" stroke-width="1"/>'
            + scratches(x0 + 20, y0 + 4, w - 40, h - 8, 25, 5)
            + f'<text x="{W / 2}" y="{y0 + 23}" text-anchor="middle" font-family="Cinzel" font-weight="700" font-size="16.5" letter-spacing="1.2" fill="#d4ecfb" filter="url(#txt)">{name}</text>'
            + bar + bolt(x0 + 16, y0 + h / 2, 3) + bolt(x0 + w - 16, y0 + h / 2, 3))


def cursor(x, y):
    spikes = "".join(f'<polygon points="0,-22 2.6,-12.5 -2.6,-12.5" transform="rotate({a})" fill="{BRASS_L}" stroke="#140c04" stroke-width="0.9"/>' for a in (0, 90, 180, 270))
    return (f'<g transform="translate({x:.1f} {y:.1f})" filter="url(#txt)"><circle r="11.5" fill="none" stroke="#140c04" stroke-width="3.2"/>'
            f'<circle r="11.5" fill="none" stroke="{BRASS_L}" stroke-width="1.4"/>{spikes}<circle r="1.8" fill="#ffe6a6"/></g>')


def damage(x, y, txt, size, op=1.0):
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" font-family="Cinzel" font-weight="900" font-size="{size}" opacity="{op}" '
            f'fill="url(#dmg)" stroke="#1d0a03" stroke-width="2.6" paint-order="stroke" filter="url(#txt)">{txt}</text>')


def build_svg(info, name):
    attacking = info.get("attacking", name in ("fog_path", "cam_fogbehind"))
    hp = (138, 200) if attacking else (186, 200)
    mp = (61, 120) if attacking else (104, 120)
    bar, x0, total, L, R = action_bar(active="LMB" if attacking else None, cooldown="2" if attacking else None)
    r = 72
    parts = [DEFS,
             orb(L - 74 - r + 4, H - r - 26, r, hp[0] / hp[1], "life", f"{hp[0]} / {hp[1]}"),
             orb(R + 74 + r - 4, H - r - 26, r, mp[0] / mp[1], "mana", f"{mp[0]} / {mp[1]}"),
             bar, minimap(info)]
    if attacking:
        parts.append(target_frame(info.get("target_name", "Antlered Wraith"), 0.62))
        dx, dy = info["damage"]
        parts.append(damage(dx, dy, "27", 36))
        parts.append(damage(dx + 38, dy - 32, "19", 24, 0.85))
    cx, cy = info["cursor"]
    if 0 < cx < W and 0 < cy < H:
        parts.append(cursor(cx, cy))
    parts.append(f'<text x="18" y="24" font-family="Cinzel" font-size="12" fill="#e8e0d0" opacity="0.55" filter="url(#txt)">'
                 'wfarpg mockup · Blender render, not final art · placeholder HUD</text>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{"".join(parts)}</svg>'


def render_html(svg, out_png, w=W, h=H):
    html = f"<html><head><meta charset='utf-8'><style>{STYLE}</style></head><body>{svg}</body></html>"
    hp = os.path.join(HERE, "_hud2.html")
    with open(hp, "w") as fh:
        fh.write(html)
    subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                    "--default-background-color=00000000", f"--window-size={w},{h}", "--virtual-time-budget=2000",
                    f"--screenshot={out_png}", "file://" + hp], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)


def compose(src, dst, name):
    info = json.load(open(os.path.join(src, name + ".json")))
    img = Image.open(os.path.join(src, name + ".png")).convert("RGBA")
    if img.size != (W, H):  # preview renders are smaller: scale them and their screen positions up to the HUD size
        k = W / img.size[0]
        img = img.resize((W, H), Image.BICUBIC)
        for key in ("cursor", "damage", "target_head", "player_head", "player_feet"):
            if info.get(key):
                info[key] = [v * k for v in info[key]]
    vig = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vig)
    vd.rectangle((0, 0, W, H), fill=95)
    vd.ellipse((-W * 0.1, -H * 0.15, W * 1.1, H * 1.15), fill=0)
    vig = vig.filter(ImageFilter.GaussianBlur(120))
    img = Image.composite(Image.new("RGBA", (W, H), (0, 0, 0, 255)), img, vig)
    layer = os.path.join(HERE, "_hud2_layer.png")
    render_html(build_svg(info, name), layer)
    out = Image.alpha_composite(img, Image.open(layer).convert("RGBA"))
    os.makedirs(dst, exist_ok=True)
    out.convert("RGB").save(os.path.join(dst, name + ".png"), optimize=True)
    print("wrote", os.path.join(dst, name + ".png"))


def icon_sheet(out_png):
    cell, pad = 150, 34
    w = len(SLOTS) * (cell + pad) + pad
    h = cell + 112
    parts = [DEFS, f'<rect width="{w}" height="{h}" fill="#14110e"/>']
    for i, (key, kind, label) in enumerate(SLOTS):
        x = pad + i * (cell + pad)
        parts.append(f'<polygon points="{chamfer(x - 9, pad - 9, cell + 18, cell + 18, 10)}" fill="{IRON}" stroke="#070606" stroke-width="1.2" filter="url(#metal)"/>')
        parts.append(f'<polygon points="{chamfer(x - 6.5, pad - 6.5, cell + 13, cell + 13, 8.5)}" fill="none" stroke="{BRASS}" stroke-width="1.3"/>')
        parts.append(icon_svg(kind, x, pad, cell, "big" + str(i)))
        parts.append(f'<polygon points="{chamfer(x, pad, cell, cell, 7)}" fill="none" stroke="#000" stroke-width="1.5"/>')
        parts.append(f'<text x="{x + cell / 2}" y="{pad + cell + 42}" text-anchor="middle" font-family="Cinzel" font-weight="700" font-size="19" fill="{TEXT}">{label}</text>')
        parts.append(f'<text x="{x + cell / 2}" y="{pad + cell + 63}" text-anchor="middle" font-family="Cinzel" font-size="13" fill="#a8946a">{key}</text>')
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(parts)}</svg>'
    render_html(svg, out_png, w, h)
    print("wrote", out_png)


if __name__ == "__main__":
    if sys.argv[1] == "--icons":
        icon_sheet(sys.argv[2])
    else:
        for n in sys.argv[3:]:
            compose(sys.argv[1], sys.argv[2], n)
