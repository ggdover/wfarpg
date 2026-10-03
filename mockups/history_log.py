"""The design history log: every step of the look & feel board, from the first sketch to the newest mockups.

    python3 history_log.py                          writes HISTORY.html next to this script (images from renders/)
    python3 history_log.py --web build/history_web  writes a web copy with resized JPEGs, ready to publish
    python3 history_log.py --record <step-id>       appends a step to board/history.json with every board item
                                                    added or changed since the last step (from board/items.json)

The history lives in board/history.json. Each step holds what was asked, what changed, the board items it added or
changed (notes word for word, as they read at the end of that step), any in-between renders kept in renders/wip/,
and optionally a "cover" image for the newest-screenshot spot at the top of the page.
"""
import datetime
import html
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HISTORY = os.path.join(HERE, "board", "history.json")
CONTENT = ("type", "text", "title", "caption", "url", "hex", "name", "assetId", "stance")

# the same subject across versions, oldest first
COMPARE = [
    ("Daylight path", [("renders/forest_v1/day_path.png", "Version 1"), ("renders/forest_v2/day_path.png", "Version 2"),
                       ("renders/forest_v3/day_path.png", "Version 3, paths redrawn"),
                       ("renders/hud_v1/day_path.png", "HUD version 1"), ("renders/hud_v2/day_path.png", "HUD version 2"),
                       ("renders/worn_paths/day_path.png", "Worn paths"), ("renders/worn_paths_v2/day_path.png", "Worn paths 2")]),
    ("Fog path", [("renders/forest_v1/fog_path.png", "Version 1"), ("renders/forest_v2/fog_path.png", "Version 2"),
                  ("renders/forest_v3/fog_path.png", "Version 3, paths redrawn"),
                  ("renders/hud_v1/fog_path.png", "HUD version 1"), ("renders/hud_v2/fog_path.png", "HUD version 2"),
                  ("renders/worn_paths/fog_path.png", "Worn paths"), ("renders/worn_paths_v2/fog_path.png", "Worn paths 2")]),
    ("Daylight pond", [("renders/forest_v1/day_tarn.png", "Version 1"), ("renders/forest_v2/day_tarn.png", "Version 2"),
                       ("renders/forest_v3/day_tarn.png", "Version 3")]),
    ("Fog bog", [("renders/forest_v1/fog_bog.png", "Version 1"), ("renders/forest_v2/fog_bog.png", "Version 2"),
                 ("renders/forest_v3/fog_bog.png", "Version 3")]),
    ("Low behind the hero", [("renders/camera/cam_behind.png", "Camera shots"), ("renders/hud_v1/cam_behind.png", "HUD version 1"),
                             ("renders/hud_v2/cam_behind.png", "HUD version 2"), ("renders/worn_paths/cam_behind.png", "Worn paths"),
                             ("renders/worn_paths_v2/cam_behind.png", "Worn paths 2")]),
    ("Low toward the pond", [("renders/camera/cam_tarn.png", "Camera shots"), ("renders/hud_v1/cam_tarn.png", "HUD version 1"),
                             ("renders/hud_v2/cam_tarn.png", "HUD version 2")]),
    ("Low behind the hero in the fog", [("renders/camera/cam_fogbehind.png", "Camera shots"),
                                        ("renders/hud_v1/cam_fogbehind.png", "HUD version 1"),
                                        ("renders/hud_v2/cam_fogbehind.png", "HUD version 2")]),
    ("The fork from the side", [("renders/camera/cam_side.png", "Camera shots"), ("renders/worn_paths/cam_side.png", "Worn paths"),
                                ("renders/worn_paths_v2/cam_side.png", "Worn paths 2")]),
    ("Act 1 · Tallmo", [("renders/act1/tallmo.png", "Act 1"), ("renders/worn_paths/tallmo.png", "Worn paths"), ("renders/worn_paths_v2/tallmo.png", "Worn paths 2"),
                        ("renders/town_square/tallmo.png", "New square")]),
    ("Act 1 · Tätskogen", [("renders/act1/tatskogen.png", "Act 1"), ("renders/worn_paths/tatskogen.png", "Worn paths"), ("renders/worn_paths_v2/tatskogen.png", "Worn paths 2")]),
    ("Act 1 · Trollgrytan", [("renders/act1/trollgrytan.png", "Act 1"), ("renders/worn_paths/trollgrytan.png", "Worn paths"), ("renders/worn_paths_v2/trollgrytan.png", "Worn paths 2")]),
    ("Ability icons", [("renders/hud_v1/icons.png", "HUD version 1"), ("renders/hud_v2/icons.png", "HUD version 2")]),
    ("Movement diagram", [("renders/diagrams/move-aim.svg", "First"), ("renders/diagrams/facing-states.svg", "With the facing rule")]),
    ("Act 1 blueprint", [("renders/act1/blueprint_act1_first.jpg", "First published"), ("renders/act1/blueprint_act1.png", "Updated")]),
    ("Storskogen blueprint", [("renders/act1/blueprint_storskogen_first.jpg", "First published"),
                              ("renders/act1/blueprint_storskogen.png", "Updated")]),
]

STANCE = {"want": "Want", "maybe": "Maybe", "avoid": "Avoid"}


def load():
    with open(HISTORY, encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------------------------------------------ --record
def record(step_id):
    """Append a step with every board item added, changed or removed since the last recorded step."""
    data = load()
    if any(s["id"] == step_id for s in data["steps"]):
        sys.exit(f"step {step_id!r} already exists in {HISTORY}")
    state = {}
    for s in data["steps"]:
        for it in s["items"]:
            if it["status"] == "removed":
                state.pop(it["id"], None)
            else:
                state[it["id"]] = it
    with open(os.path.join(HERE, "board", "items.json"), encoding="utf-8") as fh:
        board = json.load(fh)
    with open(os.path.join(HERE, "board", "assets.json"), encoding="utf-8") as fh:
        assets = json.load(fh)
    items = []
    # oldest first; items made together follow their places on the board, in reading order
    for did, d in sorted(board.items(), key=lambda kv: (kv[1].get("createdAt") or 0, kv[1].get("y", 0), kv[1].get("x", 0), kv[0])):
        before = state.get(did)
        changed = [k for k in CONTENT if (before or {}).get(k) != d.get(k)]
        if not changed:
            continue
        if before is None:
            status = "new"
        elif "assetId" in changed:
            status = "replaced"
        elif changed == ["caption"]:
            status = "relabelled"
        else:
            status = "updated"
        item = {"id": did, "type": d.get("type"), "status": status}
        if status != "new":
            item["changed"] = [k for k in changed if k != "type"]
        for k in ("title", "text", "caption", "url", "hex", "name", "stance", "assetId"):
            if d.get(k) is not None:
                item[k] = d[k]
        if d.get("assetId"):
            item["file"] = assets.get(d["assetId"])
            if not item["file"]:
                print(f"warning: {did} shows asset {d['assetId']}, which board/assets.json doesn't map to a file")
        if d.get("author"):
            item["author"] = d["author"]
        items.append(item)
    for did, it in state.items():
        if did not in board:
            label = it.get("title") or it.get("caption") or (it.get("text") or "").split("\n")[0].lstrip("# ") or did
            items.append({"id": did, "type": it.get("type"), "status": "removed", "label": label})
    now = datetime.datetime.now()
    data["steps"].append({"id": step_id, "date": now.strftime("%Y-%m-%d"), "asked_at": "", "posted_at": now.strftime("%H:%M"),
                          "title": "", "section": "", "asked": "", "changed": [], "items": items, "wip": []})
    with open(HISTORY, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    counts = {}
    for it in items:
        counts[f'{it["type"]} {it["status"]}'] = counts.get(f'{it["type"]} {it["status"]}', 0) + 1
    print(f"recorded step {step_id!r}:", ", ".join(f"{n} {k}" for k, n in counts.items()) or "no board changes")
    print("now fill in its asked_at, title, section, asked and changed in board/history.json, and list any renders/wip/ images")


# ------------------------------------------------------------------ page parts
def esc(s):
    return html.escape(s or "", quote=True)


def inline(s):
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", esc(s))


def note_html(it):
    out, items, title = [], [], ""

    def flush():
        if items:
            out.append("<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>")
            items.clear()
    for line in (it.get("text") or "").split("\n"):
        if line.startswith("# "):
            flush()
            if title:
                out.append(f"<h5>{inline(line[2:])}</h5>")
            else:
                title = inline(line[2:])
        elif line.startswith("- "):
            items.append(inline(line[2:]))
        elif line.strip():
            flush()
            out.append(f"<p>{inline(line)}</p>")
        else:
            flush()
    flush()
    if it["status"] == "new":
        tag = "New"
    elif "text" in it.get("changed", []):
        tag = "Reworded"
    else:
        tag = "Marked"
    by = "" if it.get("author") == "claude" else '<span class="tag">Added by you</span>'
    chip = f'<span class="chip chip-{it["stance"]}">{STANCE[it["stance"]]}</span>' if it.get("stance") in STANCE else ""
    return (f'<article class="note"><div class="in"><header><h4>{title}</h4>{chip}</header>'
            f'<p class="meta"><span class="tag">{tag}</span>{by}</p>{"".join(out)}</div></article>')


def link_html(it):
    url = it.get("url") or ""
    shown = re.sub(r"^https?://(www\.)?", "", url)
    text = "".join(f"<p>{inline(line)}</p>" for line in (it.get("text") or "").split("\n") if line.strip())
    tag = "New" if it["status"] == "new" else "Changed"
    return (f'<article class="note"><div class="in"><header><h4>{esc(it.get("title") or shown)}</h4></header>'
            f'<p class="meta"><span class="tag">{tag} link</span></p>{text}'
            f'<p><a href="{esc(url)}" target="_blank" rel="noopener">{esc(shown)}</a></p></div></article>')


def is_wide(path):
    return any(k in os.path.basename(path) for k in ("blueprint", "row_a", "row_b", "portfolio"))


class Images:
    """Gives the src for a repo image: the file itself, or resized web copies when building for the web."""

    def __init__(self, web_dir=None):
        self.web_dir = web_dir
        self.done = set()

    def src(self, path, thumb=False):
        if not self.web_dir:
            return path
        os.makedirs(os.path.join(self.web_dir, "img"), exist_ok=True)
        base = path.replace("../", "").replace("renders/", "").replace("/", "_").rsplit(".", 1)[0]
        if path.endswith(".svg"):
            dst = f"img/{base}.svg"
            if dst not in self.done:
                shutil.copy2(os.path.join(HERE, path), os.path.join(self.web_dir, dst))
                self.done.add(dst)
            return dst
        from PIL import Image
        dst = f"img/{base}_{'t' if thumb else 'f'}.jpg"
        if dst not in self.done:
            im = Image.open(os.path.join(HERE, path)).convert("RGB")
            maxw = (1100 if is_wide(path) else 720) if thumb else (2600 if is_wide(path) else 1600)
            if im.width > maxw:
                im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
            im.save(os.path.join(self.web_dir, dst), quality=80 if thumb else 87, optimize=True)
            self.done.add(dst)
        return dst


def figure(img, path, caption, group, tag=""):
    wide = " wide" if is_wide(path) else ""
    tag = f'<span class="tag">{esc(tag)}</span>' if tag else ""
    return (f'<figure class="shot{wide}"><button type="button" class="frame" data-full="{esc(img.src(path))}" '
            f'data-group="{esc(group)}" data-caption="{esc(caption)}" aria-label="Enlarge: {esc(caption)}">'
            f'<img src="{esc(img.src(path, thumb=True))}" alt="{esc(caption)}" loading="lazy" decoding="async"></button>'
            f'<figcaption>{tag}{esc(caption)}</figcaption></figure>')


def nice_date(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%b')} {d.year}"


def step_images(step):
    """Images the step added or replaced, blueprints first, lettered shots A–J in order."""
    imgs = [it for it in step["items"] if it["type"] == "image" and it["status"] in ("new", "replaced") and it.get("file")]

    def key(it):
        m = re.match(r"^([A-Z]) · ", it.get("caption") or "")
        return (0 if is_wide(it["file"]) else 1, m.group(1) if m else "")
    return sorted(imgs, key=key)


def is_ref(path):
    return path.startswith("renders/reference_copies/")


STYLE = r"""
/* A chronicle down the page: a rail with each step's number and times, the step beside it.
   Images sit in chamfered iron frames, like the HUD. One column on phones. */
:root {
  color-scheme: dark;
  --soot: #121110;
  --iron: #1c1a18;
  --iron-2: #262320;
  --rule: #3d362c;
  --brass: #b48d4e;
  --brass-hi: #e2c68e;
  --parchment: #ece0c6;
  --muted: #a99b7e;
  --want: #7dba89;
  --maybe: #9aa6e6;
  --avoid: #dc7462;
  --f-display: "Cinzel", "Trajan Pro", Georgia, serif;
  --f-body: "Spectral", Georgia, "Times New Roman", serif;
  --f-mono: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace;
  --cut: 9px;
}
@font-face { font-family: "Cinzel"; src: url("fonts/Cinzel.ttf") format("truetype"); font-weight: 400 900; font-display: swap; }
html { background: var(--soot); }
body { margin: 0; background: var(--soot); color: var(--parchment); font: 17px/1.6 var(--f-body); }
.wrap { max-width: 1240px; margin: 0 auto; padding: 44px clamp(16px, 4vw, 32px) 80px; }
a { color: var(--brass-hi); }
:focus-visible { outline: 2px solid var(--brass-hi); outline-offset: 3px; }
h1, h2, h3, h4, h5 { font-family: var(--f-display); font-weight: 700; text-wrap: balance; margin: 0; }
code { font: 500 .88em var(--f-mono); }

.masthead { display: grid; gap: 14px; padding-bottom: 32px; border-bottom: 1px solid var(--rule); }
.eyebrow { margin: 0; font: 600 12px/1 var(--f-mono); letter-spacing: .16em; text-transform: uppercase; color: var(--brass); }
h1 { font-size: clamp(36px, 6.4vw, 64px); font-weight: 900; letter-spacing: .04em; line-height: 1.02; }
.lede { max-width: 64ch; color: var(--muted); margin: 0; }
.facts { display: flex; flex-wrap: wrap; gap: 8px 22px; font: 500 13px/1.4 var(--f-mono); color: var(--muted); font-variant-numeric: tabular-nums; }
.facts b { color: var(--parchment); font-weight: 600; }
.diptych { display: grid; grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr); align-items: center; gap: 18px; margin-top: 26px; }
.diptych .arrow { font: 900 30px/1 var(--f-display); color: var(--brass); }
.diptych figcaption { font-family: var(--f-mono); font-size: 12.5px; letter-spacing: .04em; }

.contents { margin-top: 34px; display: grid; gap: 10px; }
.contents h2 { font-size: 14px; letter-spacing: .16em; text-transform: uppercase; color: var(--brass); }
.contents ol { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 260px), 1fr)); gap: 0 28px; }
.contents a { display: grid; grid-template-columns: 2.2em minmax(0, 1fr) auto; gap: 8px; align-items: baseline; padding: 8px 0; border-bottom: 1px solid var(--rule); color: var(--parchment); text-decoration: none; }
.contents a:hover .t { color: var(--brass-hi); }
.contents .n { font: 700 15px/1 var(--f-display); color: var(--brass); }
.contents .t { font-size: 15.5px; line-height: 1.35; }
.contents .w { font: 500 12px/1 var(--f-mono); color: var(--muted); font-variant-numeric: tabular-nums; }

.step { display: grid; grid-template-columns: 148px minmax(0, 1fr); gap: 34px; padding-block: 54px; border-bottom: 1px solid var(--rule); scroll-margin-top: 8px; }
.rail { display: flex; flex-direction: column; gap: 7px; position: sticky; top: 18px; align-self: start; }
.rail .num { font: 900 56px/0.9 var(--f-display); color: var(--brass); font-variant-numeric: lining-nums tabular-nums; }
.rail .when { font: 500 12.5px/1.5 var(--f-mono); color: var(--muted); font-variant-numeric: tabular-nums; }
.rail .where { font: 600 11.5px/1.4 var(--f-mono); letter-spacing: .08em; text-transform: uppercase; color: var(--brass-hi); }
.body { display: grid; gap: 28px; min-width: 0; }
.body > h2 { font-size: clamp(26px, 3.4vw, 36px); letter-spacing: .02em; line-height: 1.12; }
.pair { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 30px; }
.label { font: 600 11.5px/1.2 var(--f-mono); letter-spacing: .14em; text-transform: uppercase; color: var(--brass); margin: 0 0 10px; }
.asked p:not(.label) { margin: 0; max-width: 64ch; }
.list { margin: 0; padding-left: 1.15em; display: grid; gap: 6px; }
.list li::marker { color: var(--brass); }
.sections { margin: 0; color: var(--muted); font-size: 15px; }
.sections b { color: var(--parchment); font-weight: 600; }

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 300px), 1fr)); gap: 20px 18px; }
.grid.refs { grid-template-columns: repeat(auto-fill, minmax(min(100%, 180px), 1fr)); }
.grid.pairs { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.shot { margin: 0; display: grid; gap: 8px; align-content: start; min-width: 0; }
.shot.wide { grid-column: 1 / -1; }
.frame { display: block; width: 100%; padding: 1px; border: 0; background: var(--rule); cursor: zoom-in;
  clip-path: polygon(var(--cut) 0, calc(100% - var(--cut)) 0, 100% var(--cut), 100% calc(100% - var(--cut)), calc(100% - var(--cut)) 100%, var(--cut) 100%, 0 calc(100% - var(--cut)), 0 var(--cut)); }
.frame:hover { background: var(--brass); }
.frame img { display: block; width: 100%; height: auto; background: var(--iron);
  clip-path: polygon(var(--cut) 0, calc(100% - var(--cut)) 0, 100% var(--cut), 100% calc(100% - var(--cut)), calc(100% - var(--cut)) 100%, var(--cut) 100%, 0 calc(100% - var(--cut)), 0 var(--cut)); }
.shot figcaption { font-size: 14px; line-height: 1.45; color: var(--muted); }
.tag { display: inline-block; margin-right: 8px; font: 600 10.5px/1 var(--f-mono); letter-spacing: .1em; text-transform: uppercase; color: var(--brass-hi); vertical-align: 1px; }

.notes { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 330px), 1fr)); gap: 14px; align-items: start; }
.note { padding: 1px; background: var(--rule); clip-path: polygon(11px 0, 100% 0, 100% calc(100% - 11px), calc(100% - 11px) 100%, 0 100%, 0 11px); }
.note .in { background: var(--iron); padding: 15px 18px 15px; display: grid; gap: 8px; font-size: 15px; line-height: 1.5;
  clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px); }
.note header { display: flex; justify-content: space-between; align-items: start; gap: 10px; }
.note h4 { font-size: 15.5px; letter-spacing: .04em; color: var(--parchment); line-height: 1.3; }
.note h5 { font-size: 14px; letter-spacing: .04em; color: var(--brass-hi); }
.note p { margin: 0; }
.note .meta { margin-top: -4px; }
.note ul { margin: 0; padding-left: 1.05em; display: grid; gap: 3px; }
.note li::marker { color: var(--brass); }
.chip { flex: none; font: 600 10.5px/1 var(--f-mono); letter-spacing: .1em; text-transform: uppercase; padding: 4px 7px; border: 1px solid currentColor; }
.chip-want { color: var(--want); } .chip-maybe { color: var(--maybe); } .chip-avoid { color: var(--avoid); }

details.wip { background: var(--iron); box-shadow: inset 0 0 0 1px var(--rule); }
details.wip summary { cursor: pointer; padding: 12px 16px; font: 600 12px/1.3 var(--f-mono); letter-spacing: .1em; text-transform: uppercase; color: var(--brass-hi); }
details.wip .grid { padding: 4px 16px 18px; }

.compare { padding-block: 54px 10px; display: grid; gap: 36px; }
.compare > h2 { font-size: clamp(26px, 3.4vw, 36px); }
.compare > .lede { margin-top: -22px; }
.row { display: grid; gap: 12px; min-width: 0; }
.row h3 { font-size: 17px; letter-spacing: .06em; color: var(--brass-hi); }
.strip { display: grid; grid-auto-flow: column; grid-auto-columns: minmax(230px, 1fr); gap: 14px; overflow-x: auto; padding-bottom: 6px; }
.strip.two { grid-auto-columns: minmax(300px, 1fr); }
.strip .shot.wide { grid-column: auto; }
.strip figcaption { font-family: var(--f-mono); font-size: 12.5px; letter-spacing: .03em; }

.lightbox { position: fixed; inset: 0; z-index: 50; background: rgb(8 7 6 / .95); display: grid; grid-template-rows: minmax(0, 1fr) auto; gap: 12px; padding: 16px; }
.lightbox img { max-width: 100%; max-height: 100%; object-fit: contain; margin: auto; display: block; }
.lightbox .bar { display: flex; align-items: center; gap: 14px; justify-content: space-between; font-size: 15px; }
.lightbox .bar p { margin: 0; min-width: 0; }
.lightbox .btns { display: flex; gap: 8px; flex: none; }
.lightbox button { font: 600 13px/1 var(--f-mono); color: var(--parchment); background: var(--iron-2); border: 1px solid var(--rule); padding: 10px 12px; cursor: pointer; }
.lightbox button:hover { border-color: var(--brass); }

footer.end { padding-top: 36px; color: var(--muted); font-size: 14px; display: grid; gap: 6px; }

@media (max-width: 860px) {
  .step { grid-template-columns: minmax(0, 1fr); gap: 16px; padding-block: 40px; }
  .rail { position: static; flex-direction: row; flex-wrap: wrap; align-items: baseline; gap: 4px 16px; }
  .rail .num { font-size: 40px; }
  .pair { grid-template-columns: minmax(0, 1fr); gap: 22px; }
  .diptych { grid-template-columns: minmax(0, 1fr); gap: 10px; }
  .diptych .arrow { transform: rotate(90deg); justify-self: center; }
  .lightbox .bar { flex-direction: column; align-items: stretch; }
}
@media (max-width: 480px) { .grid.pairs { grid-template-columns: minmax(0, 1fr); } }
@media (prefers-reduced-motion: no-preference) { .frame { transition: background .15s ease; } }
"""

SCRIPT = r"""
(() => {
  const frames = [...document.querySelectorAll('.frame')];
  let box = null, group = [], idx = 0, opener = null;
  function show() {
    const f = group[idx], img = box.querySelector('img');
    img.src = f.dataset.full;
    img.alt = f.dataset.caption;
    box.querySelector('p').textContent = f.dataset.caption + (group.length > 1 ? '  (' + (idx + 1) + ' of ' + group.length + ')' : '');
    box.querySelectorAll('[data-a="prev"], [data-a="next"]').forEach(b => { b.hidden = group.length < 2; });
  }
  function step(d) { idx = (idx + d + group.length) % group.length; show(); }
  function close() {
    if (!box) return;
    box.remove(); box = null;
    document.documentElement.style.overflow = '';
    if (opener) opener.focus();
  }
  function open(f) {
    opener = f;
    group = frames.filter(x => x.dataset.group === f.dataset.group);
    idx = group.indexOf(f);
    box = document.createElement('div');
    box.className = 'lightbox';
    box.setAttribute('role', 'dialog');
    box.setAttribute('aria-modal', 'true');
    box.setAttribute('aria-label', 'Image viewer');
    box.innerHTML = '<img alt=""><div class="bar"><p></p><div class="btns">' +
      '<button type="button" data-a="prev">Previous</button><button type="button" data-a="next">Next</button>' +
      '<button type="button" data-a="close">Close</button></div></div>';
    box.addEventListener('click', e => {
      const b = e.target.closest('button');
      const a = b && b.dataset.a;
      if (a === 'close' || e.target === box) close();
      else if (a === 'prev') step(-1);
      else if (a === 'next') step(1);
    });
    document.body.appendChild(box);
    document.documentElement.style.overflow = 'hidden';
    show();
    box.querySelector('[data-a="close"]').focus();
  }
  frames.forEach(f => f.addEventListener('click', () => open(f)));
  document.addEventListener('keydown', e => {
    if (!box) return;
    if (e.key === 'Escape') close();
    else if (e.key === 'ArrowRight') step(1);
    else if (e.key === 'ArrowLeft') step(-1);
  });
})();
"""


def build(web_dir=None):
    data = load()
    steps = data["steps"]
    img = Images(web_dir)
    n_imgs = sum(1 for s in steps for it in step_images(s) if not is_ref(it["file"]))
    n_refs = sum(1 for s in steps for it in step_images(s) if is_ref(it["file"]))
    n_wip = sum(len(s["wip"]) for s in steps)
    notes = [it for s in steps for it in s["items"] if it["type"] == "note" and it["status"] != "relabelled"]
    n_new = sum(1 for it in notes if it["status"] == "new")
    rasters = [(s, it) for s in steps for it in step_images(s)
               if not is_ref(it["file"]) and not is_wide(it["file"]) and not it["file"].endswith(".svg")]
    (s0, first), (s1, newest) = rasters[0], rasters[-1]
    covered = [s for s in steps if s.get("cover")]  # a step can name the image that best shows it
    if covered and steps.index(covered[-1]) >= steps.index(s1):
        s1, newest = covered[-1], {"file": covered[-1]["cover"]}
    span = f'{nice_date(steps[0]["date"])}, {steps[0]["posted_at"]} to {steps[-1]["posted_at"]}' \
        if steps[0]["date"] == steps[-1]["date"] else f'{nice_date(steps[0]["date"])} to {nice_date(steps[-1]["date"])}'

    parts = []
    if not web_dir:
        parts.append('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                     '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">')
    parts += ["<title>wfarpg Design History</title>",
              '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
              '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;600&family=Spectral:ital,wght@0,400;0,600;1,400&display=swap">',
              f"<style>{STYLE}</style>"]
    if not web_dir:
        parts.append("</head><body>")
    parts.append(f"""<div class="wrap">
<header class="masthead">
  <p class="eyebrow">wfarpg · look &amp; feel</p>
  <h1>Design History</h1>
  <p class="lede">Every step of working out how the game should look and feel, from the first sketch of the controls to the whole
  of Act 1. Each step shows what you asked for, what changed, the images, and the board's notes word for word as they read
  at the end of that step. Earlier wordings stay with the step that wrote them.</p>
  <div class="facts"><span><b>{len(steps)}</b> steps</span><span><b>{n_imgs}</b> images</span><span><b>{n_wip}</b> earlier attempts</span>
    <span><b>{n_new}</b> notes, <b>{len(notes) - n_new}</b> rewordings</span><span>{esc(span)}</span>
    <span><a href="{esc(data["board"])}" target="_blank" rel="noopener">Open the board</a></span></div>
  <div class="diptych">
    {figure(img, first["file"], f'First screenshot · {s0["posted_at"]}', "hero")}
    <span class="arrow" aria-hidden="true">→</span>
    {figure(img, newest["file"], f'Newest screenshot · {s1["posted_at"]}', "hero")}
  </div>
</header>
<nav class="contents" aria-label="Steps"><h2>Steps</h2><ol>""")
    for i, s in enumerate(steps, 1):
        parts.append(f'<li><a href="#{esc(s["id"])}"><span class="n">{i}</span><span class="t">{esc(s["title"])}</span>'
                     f'<span class="w">{esc(s["posted_at"])}</span></a></li>')
    parts.append('<li><a href="#compare"><span class="n">↔</span><span class="t">Side by side</span><span class="w"></span></a></li></ol></nav>')

    for i, s in enumerate(steps, 1):
        g = s["id"]
        asked = f'<span>Asked {esc(s["asked_at"])}</span>' if s.get("asked_at") else ""
        parts.append(f'<section class="step" id="{esc(g)}"><aside class="rail"><span class="num">{i}</span>'
                     f'<span class="when">{esc(nice_date(s["date"]))}<br>{asked}{"<br>" if asked else ""}Done {esc(s["posted_at"])}</span>'
                     f'<span class="where">{esc(s["section"])}</span></aside><div class="body">')
        parts.append(f'<h2>{esc(s["title"])}</h2>')
        parts.append('<div class="pair">'
                     f'<div class="asked"><p class="label">Your request</p><p>{esc(s["asked"])}</p></div>'
                     f'<div><p class="label">What changed</p><ul class="list">{"".join(f"<li>{esc(c)}</li>" for c in s["changed"])}</ul></div></div>')
        if s.get("found"):
            parts.append('<div><p class="label">Found along the way</p><ul class="list">'
                         + "".join(f"<li>{esc(c)}</li>" for c in s["found"]) + "</ul></div>")
        frames = [it for it in s["items"] if it["type"] == "frame" and it["status"] == "new"]
        if frames:
            names = ", ".join(f'<b>{esc(it.get("title"))}</b>' for it in frames)
            parts.append(f'<p class="sections">New board section{"s" if len(frames) > 1 else ""}: {names}</p>')
        imgs = step_images(s)
        shots = [it for it in imgs if not is_ref(it["file"])]
        refs = [it for it in imgs if is_ref(it["file"])]
        if refs:
            parts.append('<div><p class="label">Your reference images</p><div class="grid refs">'
                         + "".join(figure(img, it["file"], it.get("caption", ""), g + "-refs") for it in refs) + "</div></div>")
        if shots:
            pairs = " pairs" if any((it.get("caption") or "").startswith("Before") for it in shots) else ""  # before/after side by side
            parts.append(f'<div><p class="label">Images on the board, with their captions</p><div class="grid{pairs}">'
                         + "".join(figure(img, it["file"], it.get("caption", ""), g,
                                          "Replaced the earlier image" if it["status"] == "replaced" else "") for it in shots)
                         + "</div></div>")
        step_notes = [it for it in s["items"] if it["type"] == "note" and it["status"] != "removed"]
        if step_notes:
            parts.append('<div><p class="label">Notes written in this step</p><div class="notes">'
                         + "".join(note_html(it) for it in step_notes) + "</div></div>")
        links = [it for it in s["items"] if it["type"] == "link" and it["status"] != "removed"]
        if links:
            parts.append('<div><p class="label">Links on the board</p><div class="notes">'
                         + "".join(link_html(it) for it in links) + "</div></div>")
        gone = [it for it in s["items"] if it["status"] == "removed"]
        if gone:
            parts.append('<p class="sections">Removed from the board: '
                         + "; ".join(f'<b>{esc(it.get("label") or it["id"])}</b>' for it in gone) + "</p>")
        if s["wip"]:
            parts.append(f'<details class="wip" open><summary>Earlier attempts in this step ({len(s["wip"])})</summary><div class="grid">'
                         + "".join(figure(img, w["file"], w["caption"], g + "-wip") for w in s["wip"]) + "</div></details>")
        parts.append("</div></section>")

    parts.append('<section class="compare" id="compare"><h2>Side by side</h2>'
                 '<p class="lede">The same subject across versions, oldest on the left.</p>')
    for k, (title, row) in enumerate(COMPARE):
        two = " two" if len(row) <= 2 else ""
        parts.append(f'<div class="row"><h3>{esc(title)}</h3><div class="strip{two}">'
                     + "".join(figure(img, p, c, f"cmp{k}") for p, c in row) + "</div></div>")
    parts.append("</section>")
    parts.append('<footer class="end"><span>Generated by <code>mockups/history_log.py</code> from <code>mockups/board/history.json</code>. '
                 'The images are in <code>mockups/renders/</code>.</span>'
                 '<span>Everything shown is a mockup: the models, colors, effects, HUD and names are placeholders.</span></footer>')
    parts.append(f"</div><script>{SCRIPT}</script>")
    if not web_dir:
        parts.append("</body></html>")

    if web_dir:
        os.makedirs(os.path.join(web_dir, "fonts"), exist_ok=True)
        shutil.copy2(os.path.join(HERE, "fonts", "Cinzel.ttf"), os.path.join(web_dir, "fonts", "Cinzel.ttf"))
        out = os.path.join(web_dir, "index.html")
    else:
        out = os.path.join(HERE, "HISTORY.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(parts))
    print(f"wrote {out}: {len(steps)} steps, {n_imgs} images, {n_refs} references, {n_wip} earlier attempts, {len(notes)} notes")


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 2 and args[0] == "--web":
        build(os.path.abspath(args[1]))
    elif len(args) == 2 and args[0] == "--record":
        record(args[1])
    elif not args:
        build()
    else:
        sys.exit(__doc__)
