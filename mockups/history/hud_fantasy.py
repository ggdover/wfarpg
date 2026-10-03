"""Rustic Norse-flavoured ARPG HUD, drawn as SVG, rendered by headless Chrome, composited over the renders.

python3 hud_fantasy.py <src_dir> <dst_dir> <shot> [<shot> ...]
python3 hud_fantasy.py --icons <dst_png>      (large icon sheet for review)
"""
import json, math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1600, 900

STYLE = """
@font-face { font-family: Cinzel; src: url(../fonts/Cinzel.ttf); font-weight: 400 900; }
@font-face { font-family: CinzelDeco; src: url(../fonts/CinzelDecorative-Bold.ttf); font-weight: 700; }
html, body { margin: 0; background: transparent; }
svg { display: block; }
"""

# ------------------------------------------------------------------ shared defs
DEFS = """
<defs>
  <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur stdDeviation="2.2" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="softglow" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur stdDeviation="5" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="shadow" x="-20%" y="-20%" width="140%" height="160%">
    <feDropShadow dx="0" dy="3" stdDeviation="3" flood-color="#000" flood-opacity="0.75"/>
  </filter>
  <filter id="grain" x="0" y="0" width="100%" height="100%">
    <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="3" result="n"/>
    <feColorMatrix in="n" type="saturate" values="0" result="g"/>
    <feComposite in="g" in2="SourceAlpha" operator="in" result="gm"/>
    <feBlend in="SourceGraphic" in2="gm" mode="multiply"/>
  </filter>
  <filter id="woodgrain" x="0" y="0" width="100%" height="100%">
    <feTurbulence type="fractalNoise" baseFrequency="0.012 0.32" numOctaves="3" seed="8" result="n"/>
    <feColorMatrix in="n" type="matrix" values="0 0 0 0 0.16  0 0 0 0 0.09  0 0 0 0 0.04  0 0 0 0.85 0" result="w"/>
    <feComposite in="w" in2="SourceAlpha" operator="in" result="wm"/>
    <feBlend in="SourceGraphic" in2="wm" mode="multiply"/>
  </filter>
  <filter id="stone" x="0" y="0" width="100%" height="100%">
    <feTurbulence type="fractalNoise" baseFrequency="0.08" numOctaves="4" seed="5" result="n"/>
    <feColorMatrix in="n" type="saturate" values="0" result="g"/>
    <feComposite in="g" in2="SourceAlpha" operator="in" result="gm"/>
    <feBlend in="SourceGraphic" in2="gm" mode="multiply"/>
  </filter>
  <filter id="swirl" x="0" y="0" width="100%" height="100%">
    <feTurbulence type="turbulence" baseFrequency="0.035" numOctaves="3" seed="11" result="t"/>
    <feColorMatrix in="t" type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.16 0" result="tw"/>
    <feComposite in="tw" in2="SourceAlpha" operator="in" result="twm"/>
    <feBlend in="SourceGraphic" in2="twm" mode="screen"/>
  </filter>
  <linearGradient id="bronze" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#f0c879"/><stop offset="0.35" stop-color="#b3832f"/>
    <stop offset="0.7" stop-color="#6e4a1b"/><stop offset="1" stop-color="#3b2710"/>
  </linearGradient>
  <linearGradient id="bronzeH" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#5a3c16"/><stop offset="0.5" stop-color="#d6a650"/><stop offset="1" stop-color="#5a3c16"/>
  </linearGradient>
  <linearGradient id="iron" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#77706a"/><stop offset="0.45" stop-color="#3d3936"/><stop offset="1" stop-color="#181615"/>
  </linearGradient>
  <linearGradient id="wood" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#6e4728"/><stop offset="0.5" stop-color="#4a2e19"/><stop offset="1" stop-color="#2a190d"/>
  </linearGradient>
  <radialGradient id="rivet" cx="0.35" cy="0.3" r="0.8">
    <stop offset="0" stop-color="#ffe2a0"/><stop offset="0.45" stop-color="#a87a30"/><stop offset="1" stop-color="#2e1e0a"/>
  </radialGradient>
  <radialGradient id="ironRivet" cx="0.35" cy="0.3" r="0.8">
    <stop offset="0" stop-color="#c9c3bb"/><stop offset="0.5" stop-color="#5a544e"/><stop offset="1" stop-color="#151312"/>
  </radialGradient>
  <linearGradient id="lifeFill" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ff5a3c"/><stop offset="0.35" stop-color="#c41f14"/><stop offset="1" stop-color="#3d0303"/>
  </linearGradient>
  <linearGradient id="manaFill" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#6cc0ff"/><stop offset="0.35" stop-color="#1f5fd0"/><stop offset="1" stop-color="#03113d"/>
  </linearGradient>
  <radialGradient id="orbShade" cx="0.5" cy="0.45" r="0.55">
    <stop offset="0.55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="0.75"/>
  </radialGradient>
  <radialGradient id="orbGloss" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#fff" stop-opacity="0.55"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="hpBar" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ff6a4a"/><stop offset="0.5" stop-color="#b3180f"/><stop offset="1" stop-color="#5a0705"/>
  </linearGradient>
  <linearGradient id="xpBar" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ffe39a"/><stop offset="0.5" stop-color="#d79a2c"/><stop offset="1" stop-color="#6e4610"/>
  </linearGradient>
  <linearGradient id="dmg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#fff6d8"/><stop offset="0.55" stop-color="#ffc35a"/><stop offset="1" stop-color="#e2641c"/>
  </linearGradient>
  <linearGradient id="steel" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#f4f8fb"/><stop offset="0.5" stop-color="#a9b4bd"/><stop offset="1" stop-color="#5d6770"/>
  </linearGradient>
  <linearGradient id="slashGrad" x1="0" y1="1" x2="1" y2="0">
    <stop offset="0" stop-color="#ff7b1f" stop-opacity="0"/><stop offset="0.5" stop-color="#ffb347"/><stop offset="1" stop-color="#fff6dc"/>
  </linearGradient>
  <linearGradient id="whirlGrad" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#4fe0f0" stop-opacity="0.2"/>
  </linearGradient>
  <linearGradient id="goldChev" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#8a5412"/><stop offset="1" stop-color="#ffe9a6"/>
  </linearGradient>
  <radialGradient id="boss" cx="0.35" cy="0.3" r="0.8">
    <stop offset="0" stop-color="#ffffff"/><stop offset="0.4" stop-color="#9aa3aa"/><stop offset="1" stop-color="#2b3035"/>
  </radialGradient>
  <radialGradient id="vign" cx="0.5" cy="0.5" r="0.7">
    <stop offset="0.6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="0.7"/>
  </radialGradient>
</defs>
"""


# ------------------------------------------------------------------ ability icons (64x64 local space)
def icon_bg(inner, outer, texture="grain"):
    return (f'<radialGradient id="bg_{inner[1:]}" cx="0.5" cy="0.42" r="0.7"><stop offset="0" stop-color="{inner}"/>'
            f'<stop offset="1" stop-color="{outer}"/></radialGradient>'
            f'<rect width="64" height="64" fill="url(#bg_{inner[1:]})" filter="url(#{texture})"/>')


ICONS = {
    "cleave": lambda: icon_bg("#6a2614", "#140604") + """
      <path d="M8,54 C14,26 34,10 58,8 C40,16 24,30 16,56 Z" fill="url(#slashGrad)" filter="url(#glow)"/>
      <g transform="rotate(-45 32 32)">
        <polygon points="29,6 35,6 35.5,40 32,46 28.5,40" fill="url(#steel)" stroke="#2a3036" stroke-width="0.8"/>
        <line x1="32" y1="9" x2="32" y2="38" stroke="#6d7880" stroke-width="1.2"/>
        <rect x="22" y="40" width="20" height="4.5" rx="1.5" fill="url(#bronze)" stroke="#2a1a08" stroke-width="0.7"/>
        <rect x="30" y="44.5" width="4" height="10" fill="#4a2a14" stroke="#1d0f05" stroke-width="0.6"/>
        <circle cx="32" cy="57" r="3.2" fill="url(#rivet)"/>
      </g>
      <circle cx="50" cy="13" r="2" fill="#fff3d0" filter="url(#glow)"/>""",
    "whirl": lambda: icon_bg("#14505c", "#031214") + """
      <g fill="none" stroke-linecap="round" filter="url(#glow)">
        <path d="M32,14 A18,18 0 1,1 14.5,36" stroke="url(#whirlGrad)" stroke-width="5"/>
        <path d="M32,21 A11,11 0 1,0 43,32" stroke="url(#whirlGrad)" stroke-width="4"/>
        <path d="M12,22 A24,24 0 0,1 40,9" stroke="#bff8ff" stroke-width="2.5" opacity="0.8"/>
      </g>
      <g transform="rotate(30 32 32)">
        <polygon points="30,22 34,22 34,42 30,42" fill="#6b4527"/>
        <path d="M34,22 C42,22 44,28 42,33 L34,31 Z" fill="url(#steel)" stroke="#25303a" stroke-width="0.6"/>
      </g>
      <circle cx="47" cy="47" r="1.6" fill="#dffcff" filter="url(#glow)"/><circle cx="16" cy="18" r="1.2" fill="#dffcff"/>""",
    "charge": lambda: icon_bg("#6a440c", "#140c02") + """
      <g stroke="#ffd98a" stroke-width="1.6" stroke-linecap="round" opacity="0.7">
        <line x1="6" y1="22" x2="22" y2="22"/><line x1="4" y1="32" x2="18" y2="32"/><line x1="8" y1="42" x2="22" y2="42"/>
      </g>
      <g filter="url(#glow)">
        <path d="M18,14 L32,32 L18,50 L24,50 L38,32 L24,14 Z" fill="url(#goldChev)" opacity="0.45"/>
        <path d="M28,14 L42,32 L28,50 L35,50 L49,32 L35,14 Z" fill="url(#goldChev)" opacity="0.75"/>
        <path d="M38,12 L54,32 L38,52 L46,52 L60,32 L46,12 Z" fill="url(#goldChev)"/>
      </g>
      <circle cx="12" cy="52" r="3" fill="#8a6a3a" opacity="0.5"/><circle cx="7" cy="48" r="2" fill="#8a6a3a" opacity="0.4"/>""",
    "ward": lambda: icon_bg("#5a6068", "#14171a", "stone") + """
      <g stroke-linecap="round" fill="none">
        <path d="M32,10 L32,55 M32,30 L17,13 M32,30 L47,13" stroke="#0b0f12" stroke-width="7" opacity="0.7"/>
        <path d="M32,10 L32,55 M32,30 L17,13 M32,30 L47,13" stroke="#8ff2ff" stroke-width="4" filter="url(#glow)"/>
        <path d="M32,10 L32,55 M32,30 L17,13 M32,30 L47,13" stroke="#e8feff" stroke-width="1.4"/>
      </g>
      <circle cx="32" cy="32" r="27" fill="none" stroke="#8ff2ff" stroke-width="1" opacity="0.35" filter="url(#glow)"/>""",
    "shield": lambda: icon_bg("#46301c", "#0e0905") + """
      <g transform="translate(30 33)">
        <circle r="24" fill="url(#wood)" filter="url(#woodgrain)"/>
        <path d="M0,0 L0,-24 A24,24 0 0,1 24,0 Z" fill="#a3291d" opacity="0.9"/>
        <path d="M0,0 L0,24 A24,24 0 0,1 -24,0 Z" fill="#a3291d" opacity="0.9"/>
        <path d="M0,0 L24,0 A24,24 0 0,1 0,24 Z" fill="#dcc79c" opacity="0.85"/>
        <path d="M0,0 L-24,0 A24,24 0 0,1 0,-24 Z" fill="#dcc79c" opacity="0.85"/>
        <g stroke="#2a180b" stroke-width="0.8" opacity="0.6"><line x1="-8" y1="-23" x2="-8" y2="23"/><line x1="8" y1="-23" x2="8" y2="23"/><line x1="-16" y1="-18" x2="-16" y2="18"/><line x1="16" y1="-18" x2="16" y2="18"/></g>
        <circle r="24" fill="none" stroke="url(#iron)" stroke-width="3.5"/>
        <circle r="7.5" fill="url(#boss)" stroke="#1b1e21" stroke-width="0.8"/>
      </g>
      <g stroke="#fff1c4" stroke-width="2" stroke-linecap="round" filter="url(#glow)">
        <line x1="55" y1="20" x2="61" y2="16"/><line x1="57" y1="32" x2="63" y2="32"/><line x1="55" y1="44" x2="61" y2="48"/>
      </g>""",
    "locked": lambda: icon_bg("#2c2c2c", "#0b0b0b") + """
      <g fill="none" stroke="#6f6a64" stroke-width="3.2" opacity="0.8">
        <ellipse cx="14" cy="14" rx="7" ry="4.5" transform="rotate(45 14 14)"/><ellipse cx="24" cy="24" rx="7" ry="4.5" transform="rotate(45 24 24)"/>
        <ellipse cx="40" cy="40" rx="7" ry="4.5" transform="rotate(45 40 40)"/><ellipse cx="50" cy="50" rx="7" ry="4.5" transform="rotate(45 50 50)"/>
      </g>
      <path d="M25,30 L25,24 A7,7 0 0,1 39,24 L39,30" fill="none" stroke="#8a8279" stroke-width="3.5"/>
      <rect x="21" y="29" width="22" height="18" rx="2.5" fill="url(#bronze)" stroke="#2a1a08" stroke-width="1"/>
      <circle cx="32" cy="36" r="2.4" fill="#1a1006"/><rect x="31" y="37" width="2" height="5" fill="#1a1006"/>""",
}

SLOTS = [("LMB", "cleave", "Cleave"), ("1", "whirl", "Whirlwind"), ("2", "charge", "Charge"),
         ("3", "ward", "Ward Rune"), ("4", "shield", "Shield Bash"), ("5", "locked", "Locked")]


def icon_svg(kind, x, y, size, uid):
    s = size / 64.0
    return (f'<g transform="translate({x} {y}) scale({s})"><clipPath id="clip_{uid}"><rect width="64" height="64" rx="5"/></clipPath>'
            f'<g clip-path="url(#clip_{uid})">{ICONS[kind]()}<rect width="64" height="64" fill="url(#vign)"/></g></g>')


# ------------------------------------------------------------------ HUD pieces
def rivets(cx, cy, r, n, size=3.2, grad="rivet", start=0.0):
    out = []
    for k in range(n):
        a = start + k * math.tau / n
        out.append(f'<circle cx="{cx + math.cos(a) * r:.1f}" cy="{cy + math.sin(a) * r:.1f}" r="{size}" fill="url(#{grad})" stroke="#120c06" stroke-width="0.6"/>')
    return "".join(out)


def orb(cx, cy, r, frac, kind, label):
    fill = "lifeFill" if kind == "life" else "manaFill"
    dark = "#0d0302" if kind == "life" else "#020619"
    gem = ("#ff3b2a", "#5a0a05") if kind == "life" else ("#58b6ff", "#082660")
    level = cy + r - 2 * r * frac
    uid = kind
    wave = " ".join(f"{cx - r + i * (2 * r / 16):.1f},{level + math.sin(i * 0.9 + (0 if kind == 'life' else 2)) * 2.4:.1f}" for i in range(17))
    runes = "ᚠᚢᚦᚨᚱᚲ ᚷᚹᚺᚾᛁᛃ ᛇᛈᛉᛊᛏᛒ ᛖᛗᛚᛜᛞᛟ " if kind == "life" else "ᛗᚨᚾᚨ ᛊᛏᚱᛖᚾᚷᚦ ᚹᛁᛊᛞᛟᛗ ᚱᚢᚾᚨ "
    rr = r + 13
    return f"""
    <g filter="url(#shadow)">
      <circle cx="{cx}" cy="{cy}" r="{r + 24}" fill="url(#iron)"/>
      <circle cx="{cx}" cy="{cy}" r="{r + 21}" fill="none" stroke="#0e0c0b" stroke-width="2"/>
    </g>
    <circle cx="{cx}" cy="{cy}" r="{rr}" fill="none" stroke="url(#bronze)" stroke-width="17"/>
    <path id="ring_{uid}" d="M {cx - rr},{cy} A {rr},{rr} 0 1,1 {cx + rr},{cy} A {rr},{rr} 0 1,1 {cx - rr},{cy}" fill="none"/>
    <text font-family="Noto Sans Runic" font-size="12.5" letter-spacing="3" fill="#3a2508" dy="4.5">
      <textPath href="#ring_{uid}">{runes * 2}</textPath></text>
    <text font-family="Noto Sans Runic" font-size="12.5" letter-spacing="3" fill="#f6d78f" opacity="0.35" dy="3.6">
      <textPath href="#ring_{uid}">{runes * 2}</textPath></text>
    <circle cx="{cx}" cy="{cy}" r="{r + 5}" fill="none" stroke="#1a120a" stroke-width="3"/>
    {rivets(cx, cy, r + 21, 12, 3.0, "ironRivet", 0.26)}
    <clipPath id="orbclip_{uid}"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath>
    <g clip-path="url(#orbclip_{uid})">
      <rect x="{cx - r}" y="{cy - r}" width="{2 * r}" height="{2 * r}" fill="{dark}"/>
      <ellipse cx="{cx}" cy="{cy - r * 0.2}" rx="{r * 0.8}" ry="{r * 0.6}" fill="{'#3a120c' if kind == 'life' else '#0c1d4a'}" opacity="0.6"/>
      <polygon points="{wave} {cx + r},{cy + r} {cx - r},{cy + r}" fill="url(#{fill})" filter="url(#swirl)"/>
      <polyline points="{wave}" fill="none" stroke="#ffffff" stroke-opacity="0.45" stroke-width="2"/>
      <rect x="{cx - r}" y="{cy - r}" width="{2 * r}" height="{2 * r}" fill="url(#orbShade)"/>
      <ellipse cx="{cx - r * 0.28}" cy="{cy - r * 0.45}" rx="{r * 0.42}" ry="{r * 0.26}" fill="url(#orbGloss)"/>
      <circle cx="{cx + r * 0.38}" cy="{cy + r * 0.42}" r="{r * 0.06}" fill="#fff" opacity="0.25"/>
    </g>
    <g transform="translate({cx} {cy - r - 24})" filter="url(#shadow)">
      <path d="M0,-15 L13,0 L0,15 L-13,0 Z" fill="url(#bronze)" stroke="#2a1a08" stroke-width="1"/>
      <path d="M0,-8 L7,0 L0,8 L-7,0 Z" fill="{gem[0]}" stroke="{gem[1]}" stroke-width="1" filter="url(#glow)"/>
    </g>
    <text x="{cx}" y="{cy - r - 50}" text-anchor="middle" font-family="Cinzel" font-weight="700" font-size="17"
          fill="#f1dfb3" stroke="#000" stroke-width="3.5" paint-order="stroke" letter-spacing="1">{label}</text>
    """


def action_bar(active=None, cooldown=None, xp=0.63):
    size, gap = 66, 9
    n = len(SLOTS)
    total = n * size + (n - 1) * gap
    x0 = W / 2 - total / 2
    y0 = H - size - 22
    px0, px1 = x0 - 26, x0 + total + 26
    py0, py1 = y0 - 22, H + 2
    out = [f"""
    <g filter="url(#shadow)">
      <path d="M{px0 - 60},{py1} L{px0 - 18},{py0 + 6} Q{px0 - 12},{py0} {px0},{py0} L{px1},{py0} Q{px1 + 12},{py0} {px1 + 18},{py0 + 6} L{px1 + 60},{py1} Z"
            fill="url(#wood)" filter="url(#woodgrain)"/>
    </g>
    <path d="M{px0 - 60},{py1} L{px0 - 18},{py0 + 6} Q{px0 - 12},{py0} {px0},{py0} L{px1},{py0} Q{px1 + 12},{py0} {px1 + 18},{py0 + 6} L{px1 + 60},{py1}"
          fill="none" stroke="url(#bronze)" stroke-width="4"/>
    <rect x="{px0}" y="{py0 + 7}" width="{px1 - px0}" height="7" fill="url(#iron)"/>
    <rect x="{px0 + 4}" y="{py0 + 8.5}" width="{(px1 - px0 - 8) * xp:.1f}" height="4" rx="2" fill="url(#xpBar)" filter="url(#glow)"/>
    """]
    for k in range(9):
        rx = px0 + 14 + k * (px1 - px0 - 28) / 8
        out.append(f'<circle cx="{rx:.1f}" cy="{py0 + 2.5}" r="2.6" fill="url(#rivet)"/>')
    for i, (key, kind, _) in enumerate(SLOTS):
        x = x0 + i * (size + gap)
        is_active = key == active
        out.append(f"""
        <rect x="{x - 4}" y="{y0 - 4}" width="{size + 8}" height="{size + 8}" rx="7" fill="#120c07"/>
        {icon_svg(kind, x, y0, size, "s" + str(i))}
        <rect x="{x - 2}" y="{y0 - 2}" width="{size + 4}" height="{size + 4}" rx="6" fill="none"
              stroke="{'#ffd77a' if is_active else 'url(#bronze)'}" stroke-width="{4 if is_active else 3}"
              {'filter="url(#softglow)"' if is_active else ''}/>
        <rect x="{x}" y="{y0}" width="{size}" height="{size}" rx="5" fill="none" stroke="#000" stroke-opacity="0.6" stroke-width="1"/>""")
        if kind == "locked":
            out.append(f'<rect x="{x}" y="{y0}" width="{size}" height="{size}" rx="5" fill="#000" opacity="0.35"/>')
        if key == cooldown:
            cx_, cy_, rr = x + size / 2, y0 + size / 2, size * 0.75
            a = math.radians(-90 + 360 * 0.62)
            out.append(f'<clipPath id="cd{i}"><rect x="{x}" y="{y0}" width="{size}" height="{size}" rx="5"/></clipPath>'
                       f'<path clip-path="url(#cd{i})" d="M{cx_},{cy_} L{cx_},{cy_ - rr} A{rr},{rr} 0 1,1 {cx_ + math.cos(a) * rr:.1f},{cy_ + math.sin(a) * rr:.1f} Z" fill="#000" opacity="0.62"/>'
                       f'<text x="{cx_}" y="{cy_ + 9}" text-anchor="middle" font-family="Cinzel" font-weight="900" font-size="26" fill="#f6e7c2" stroke="#000" stroke-width="3" paint-order="stroke">3</text>')
        kw = 30 if len(key) > 1 else 18
        out.append(f'<rect x="{x - 3}" y="{y0 + size - 13}" width="{kw}" height="16" rx="3" fill="#1a110a" stroke="url(#bronze)" stroke-width="1.2"/>'
                   f'<text x="{x - 3 + kw / 2}" y="{y0 + size - 1}" text-anchor="middle" font-family="Cinzel" font-weight="700" font-size="11" fill="#f1dfb3">{key}</text>')
    return "".join(out), x0, total


def minimap(info):
    R = 88
    cx, cy = W - 38 - R, 36 + R
    px, py = info["player_world"]
    yaw = math.radians(info.get("yaw", 225.0))
    fwd = (-math.cos(yaw), -math.sin(yaw))
    right = (fwd[1], -fwd[0])
    scale = 3.0

    def mm(x, y):
        dx, dy = x - px, y - py
        return (cx + (dx * right[0] + dy * right[1]) * scale, cy - (dx * fwd[0] + dy * fwd[1]) * scale)

    paths = "".join('<polyline points="%s" fill="none" stroke="#c9a46a" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.9"/>'
                    % " ".join("%.1f,%.1f" % mm(x, y) for x, y in pts) for pts in info["paths"])
    tarn = " ".join("%.1f,%.1f" % mm(x, y) for x, y in info["tarn"])
    bx, by, br = info["bog"]
    bcx, bcy = mm(bx, by)
    f = info["facing"] + math.pi / 2
    fx, fy = math.cos(f), math.sin(f)
    ang = math.degrees(math.atan2(-(fx * fwd[0] + fy * fwd[1]), fx * right[0] + fy * right[1]))
    nx, ny = right[1], fwd[1]
    fog = info["mode"] == "fog"
    return f"""
    <clipPath id="mmclip"><circle cx="{cx}" cy="{cy}" r="{R}"/></clipPath>
    <g filter="url(#shadow)"><circle cx="{cx}" cy="{cy}" r="{R + 14}" fill="url(#iron)"/></g>
    <g clip-path="url(#mmclip)">
      <rect x="{cx - R}" y="{cy - R}" width="{2 * R}" height="{2 * R}" fill="{'#2b3134' if fog else '#25301d'}" opacity="0.92" filter="url(#grain)"/>
      <circle cx="{bcx:.1f}" cy="{bcy:.1f}" r="{br * scale:.1f}" fill="#3e3a24" opacity="0.85"/>
      <polygon points="{tarn}" fill="#2f6584" stroke="#7fb2cf" stroke-width="1.5"/>
      {paths}
      {'<rect x="%d" y="%d" width="%d" height="%d" fill="#c9d3dc" opacity="0.22"/>' % (cx - R, cy - R, 2 * R, 2 * R) if fog else ''}
      <circle cx="{cx}" cy="{cy}" r="{R}" fill="url(#orbShade)"/>
    </g>
    <g transform="translate({cx} {cy}) rotate({ang:.1f})" filter="url(#glow)">
      <path d="M11,0 L-7,-7 L-3,0 L-7,7 Z" fill="#ffd77a" stroke="#3a2508" stroke-width="1.2"/>
    </g>
    <circle cx="{cx}" cy="{cy}" r="{R + 6}" fill="none" stroke="url(#bronze)" stroke-width="7"/>
    {rivets(cx, cy, R + 6, 10, 2.6, "rivet", 0.3)}
    <g transform="translate({cx + nx * (R + 6):.1f} {cy - ny * (R + 6):.1f})" filter="url(#shadow)">
      <circle r="12" fill="url(#iron)" stroke="url(#bronze)" stroke-width="2.5"/>
      <text y="5" text-anchor="middle" font-family="Cinzel" font-weight="900" font-size="14" fill="#f1dfb3">N</text>
    </g>
    <text x="{cx}" y="{cy + R + 38}" text-anchor="middle" font-family="Cinzel" font-weight="700" font-size="13" letter-spacing="4"
          fill="#c9b07a" stroke="#000" stroke-width="3" paint-order="stroke">ACT I</text>
    <text x="{cx}" y="{cy + R + 64}" text-anchor="middle" font-family="CinzelDeco" font-size="23"
          fill="#f1dfb3" stroke="#000" stroke-width="4" paint-order="stroke">Pine Forest</text>
    {'<text x="%d" y="%d" text-anchor="middle" font-family="Cinzel" font-weight="700" font-size="13.5" fill="#bfe6ff" stroke="#000" stroke-width="3" paint-order="stroke">&#10052; The fog has rolled in</text>' % (cx, cy + R + 86) if fog else ''}
    """


def target_frame(name, frac):
    w = 400
    x0, y0 = W / 2 - w / 2, 22
    return f"""
    <g filter="url(#shadow)">
      <path d="M{x0 + 18},{y0} L{x0 + w - 18},{y0} L{x0 + w},{y0 + 30} L{x0 + w - 18},{y0 + 60} L{x0 + 18},{y0 + 60} L{x0},{y0 + 30} Z" fill="url(#iron)"/>
    </g>
    <path d="M{x0 + 18},{y0} L{x0 + w - 18},{y0} L{x0 + w},{y0 + 30} L{x0 + w - 18},{y0 + 60} L{x0 + 18},{y0 + 60} L{x0},{y0 + 30} Z"
          fill="none" stroke="url(#bronze)" stroke-width="3"/>
    <text x="{W / 2}" y="{y0 + 24}" text-anchor="middle" font-family="Cinzel" font-weight="700" font-size="18" letter-spacing="1"
          fill="#d9f0ff" stroke="#000" stroke-width="3" paint-order="stroke">{name}</text>
    <rect x="{x0 + 34}" y="{y0 + 34}" width="{w - 68}" height="14" rx="3" fill="#120808" stroke="#000" stroke-width="1"/>
    <rect x="{x0 + 36}" y="{y0 + 36}" width="{(w - 72) * frac:.1f}" height="10" rx="2" fill="url(#hpBar)"/>
    <rect x="{x0 + 36}" y="{y0 + 36}" width="{(w - 72) * frac:.1f}" height="3" rx="1" fill="#fff" opacity="0.25"/>
    {rivets(x0 + 18, y0 + 30, 0, 1, 3.2)}{rivets(x0 + w - 18, y0 + 30, 0, 1, 3.2)}
    """


def cursor(x, y):
    spikes = "".join(f'<path d="M0,-{24} L4,-13 L-4,-13 Z" transform="rotate({a})" fill="url(#bronze)" stroke="#1d1206" stroke-width="0.8"/>' for a in (0, 90, 180, 270))
    return f"""<g transform="translate({x:.1f} {y:.1f})" filter="url(#shadow)">
      <circle r="13" fill="none" stroke="#1d1206" stroke-width="5"/>
      <circle r="13" fill="none" stroke="url(#bronze)" stroke-width="3"/>
      {spikes}<circle r="2.6" fill="#ffd77a" filter="url(#glow)"/></g>"""


def damage(x, y, txt, size, op=1.0):
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" font-family="Cinzel" font-weight="900" font-size="{size}" opacity="{op}" '
            f'fill="url(#dmg)" stroke="#2a0e04" stroke-width="4" paint-order="stroke" filter="url(#shadow)">{txt}</text>')


def build_svg(info, name):
    attacking = name in ("fog_path", "cam_fogbehind")
    hp = (138, 200) if attacking else (186, 200)
    mp = (61, 120) if attacking else (104, 120)
    bar, x0, total = action_bar(active="LMB" if attacking else None, cooldown="2" if attacking else None)
    r = 74
    parts = [DEFS, bar,
             orb(x0 - 26 - 60 - r + 8, H - r - 30, r, hp[0] / hp[1], "life", f"{hp[0]} / {hp[1]}"),
             orb(x0 + total + 26 + 60 + r - 8, H - r - 30, r, mp[0] / mp[1], "mana", f"{mp[0]} / {mp[1]}"),
             minimap(info)]
    if attacking:
        parts.append(target_frame("Antlered Wraith", 0.62))
        dx, dy = info["damage"]
        parts.append(damage(dx, dy, "27", 38))
        parts.append(damage(dx + 40, dy - 34, "19", 26, 0.85))
    cx, cy = info["cursor"]
    if 0 < cx < W and 0 < cy < H:
        parts.append(cursor(cx, cy))
    parts.append(f'<text x="18" y="24" font-family="Cinzel" font-size="12" fill="#e8e0d0" opacity="0.55" stroke="#000" stroke-width="2" stroke-opacity="0.4" paint-order="stroke">'
                 'wfarpg mockup · Blender render, not final art · placeholder HUD</text>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{"".join(parts)}</svg>'


def render_html(svg, out_png, w=W, h=H):
    html = f"<html><head><meta charset='utf-8'><style>{STYLE}</style></head><body>{svg}</body></html>"
    hp = os.path.join(HERE, "_hud.html")
    with open(hp, "w") as fh:
        fh.write(html)
    subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                    "--default-background-color=00000000", f"--window-size={w},{h}", "--virtual-time-budget=2000",
                    f"--screenshot={out_png}", "file://" + hp], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)


def compose(src, dst, name):
    info = json.load(open(os.path.join(src, name + ".json")))
    img = Image.open(os.path.join(src, name + ".png")).convert("RGBA")
    vig = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vig)
    vd.rectangle((0, 0, W, H), fill=95)
    vd.ellipse((-W * 0.1, -H * 0.15, W * 1.1, H * 1.15), fill=0)
    vig = vig.filter(ImageFilter.GaussianBlur(120))
    img = Image.composite(Image.new("RGBA", (W, H), (0, 0, 0, 255)), img, vig)
    layer = os.path.join(HERE, "_hud_layer.png")
    render_html(build_svg(info, name), layer)
    hud = Image.open(layer).convert("RGBA")
    out = Image.alpha_composite(img, hud)
    os.makedirs(dst, exist_ok=True)
    out.convert("RGB").save(os.path.join(dst, name + ".png"), optimize=True)
    print("wrote", os.path.join(dst, name + ".png"))


def icon_sheet(out_png):
    cell, pad = 150, 30
    w = len(SLOTS) * (cell + pad) + pad
    h = cell + 90
    parts = [DEFS, f'<rect width="{w}" height="{h}" fill="#17120d"/>']
    for i, (key, kind, label) in enumerate(SLOTS):
        x = pad + i * (cell + pad)
        parts.append(f'<rect x="{x - 6}" y="{pad - 6}" width="{cell + 12}" height="{cell + 12}" rx="10" fill="#0c0805"/>')
        parts.append(icon_svg(kind, x, pad, cell, "big" + str(i)))
        parts.append(f'<rect x="{x - 3}" y="{pad - 3}" width="{cell + 6}" height="{cell + 6}" rx="9" fill="none" stroke="url(#bronze)" stroke-width="5"/>')
        parts.append(f'<text x="{x + cell / 2}" y="{pad + cell + 38}" text-anchor="middle" font-family="Cinzel" font-weight="700" font-size="19" fill="#f1dfb3">{label}</text>')
        parts.append(f'<text x="{x + cell / 2}" y="{pad + cell + 60}" text-anchor="middle" font-family="Cinzel" font-size="13" fill="#b9a47c">{key}</text>')
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(parts)}</svg>'
    render_html(svg, out_png, w, h)
    print("wrote", out_png)


if __name__ == "__main__":
    if sys.argv[1] == "--icons":
        icon_sheet(sys.argv[2])
    else:
        for n in sys.argv[3:]:
            compose(sys.argv[1], sys.argv[2], n)
