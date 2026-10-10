"""The plant generator: low-poly bushes and grasses of the Swedish forest, of crossed-plane cards like the trees' leaves.

Used by make_plants.py (builds the portfolio .blend) and plant_editor.py (the editor panel in Blender). It builds on the
tree generator (../trees/treegen.py): its faceted tubes for stems and its crossed clumps for leaves. Every plant is one
mesh with up to three materials: its stems, coloured per face; its card (make_plant_cards.py); and the card's extra
version, with berries, flowers or nuts for a bush, or a card of flowering stalks for a grass. A plant is rebuilt in
place from its kind, variant and settings (see DEFAULTS), so the plants in the .blend, and their linked copies on the
forest floor, follow the settings.

Four kinds of plant:
- Bushes (raspberry, alder buckthorn, hazel): stems from the ground, branching, with crossed clumps along and at the
  ends of their branches, filling a dome widest at the foot (the user found them thin there): the lowest branches
  reach furthest, down to the ground. Their cards face out from the bush's foot, so it shades as one rounded mass.
- The fern: a ring of fronds, each a card from the middle of the ring, rising and arching over, bent in three.
- Grasses: tufts of crossed cards standing on the ground, each bent once so it arches; a share of the tufts carry a
  card of flowering stalks, taller, crossed among them. Their normals point mostly up, so a tuft is lit as the ground
  under it is.
- Long grass: a patch of it, cards of thin strands crossing at its middle, each a strip of grass rather than a tuft,
  bent once; variant B has a card of seed heads crossed among them. Copies of it cover the ground, as in the game,
  where they fold as the hero walks through.
"""
import json
import math
import os
import random
import sys

import bpy
from mathutils import Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.join(HERE, "..", "trees") not in sys.path:
    sys.path.insert(0, os.path.join(HERE, "..", "trees"))
import treegen  # noqa: E402
from treegen import TAU, UP, Tree, along, direction, limb, lin, pick, taper  # noqa: E402

TEXTURES = os.path.join(HERE, "textures")
SETTINGS = os.path.join(HERE, "plant_settings.json")

# what each setting does is described in plant_editor.py, next to its slider
BASE = dict(card=1, size=1.0, planes=3, density=1.0, spread=1.0, upright=1.0, flat=True, tilt=1.0,
            brightness=1.0, hue=0.5, saturation=1.0, height=1.0, width=1.0, seed=0, extra=0.3,
            stems=5, lean=0.3, bend=0.35, rise=55.0, flower_height=1.6)
DEFAULTS = {
    "Raspberry": dict(BASE, stems=16, extra=0.25),
    "AlderBuckthorn": dict(BASE, stems=7, extra=0.3),
    "Hazel": dict(BASE, stems=11, extra=0.15),
    "WoodFern": dict(BASE, planes=9, rise=60.0, bend=0.45),
    "LongGrass": dict(BASE, planes=3, lean=0.35, bend=0.55, extra=0.15, flower_height=1.25),
    "WavyHairGrass": dict(BASE, planes=3, density=1.0, lean=0.35, bend=0.4, extra=0.35),
    "CommonBent": dict(BASE, planes=3, density=1.0, lean=0.3, bend=0.35, extra=0.4),
    "WoodSmallReed": dict(BASE, planes=3, density=1.0, lean=0.25, bend=0.45, extra=0.4, flower_height=1.7),
    "PurpleMoorGrass": dict(BASE, planes=4, density=1.0, lean=0.2, bend=0.25, extra=0.4, flower_height=1.7),
    "CommonSedge": dict(BASE, planes=3, density=1.0, lean=0.2, bend=0.25, extra=0.35, flower_height=1.3),
    "Cottongrass": dict(BASE, planes=4, density=1.0, lean=0.2, bend=0.2, extra=0.5, flower_height=1.5),
}


# ------------------------------------------------------------------ building a plant
class Plant(Tree):
    """A tree's tubes and crossed clumps (treegen.Tree), and a grass's tufts and a fern's fronds."""

    def __init__(self, seed):
        super().__init__(seed)
        self.slots = ["stems"]
        self.tufts = []   # (foot, height, width): a grass's tufts
        self.fronds = []  # (foot, azimuth, length): a fern's fronds
        self.flowering = False  # a patch of long grass: with its card of seed heads (variant B)
        self.fits = ((1.0, 1.0), (1.0, 1.0))  # its cards' crops, width and height: the strands' and the seed heads' (fit_of)

    def _facing(self, p, cen, crown):
        """A low mound's cards face out from its foot, not its middle, so its top faces up."""
        if crown == "dome":
            return Vector((cen.x, cen.y, -0.1))
        return super()._facing(p, cen, crown)

    def emit(self, crown, cfg, kind):
        if kind == "grass":
            self._emit_tufts(cfg)
        elif kind == "patch":
            self._emit_patch(cfg)
        elif kind == "fern":
            self._emit_fronds(cfg)
        else:
            self.emit_leaves(crown, cfg)

    def _strip(self, foot, right, ups, width, mat, nrm_for, mirror):
        """A card bent along its length: from foot, one segment per direction in ups (each a vector as long as the
        segment), width wide across right; the texture runs up it, v from 0 to 1."""
        rows = [foot]
        for u in ups:
            rows.append(rows[-1] + u)
        n = len(ups)
        us = (1.0, 0.0) if mirror else (0.0, 1.0)
        edges = [(row - right * width / 2, row + right * width / 2) for row in rows]
        ids = [(self.vert(l), self.vert(r)) for l, r in edges]  # each row's corners shared by the segments either side
        for i in range(n):
            (a0, a1), (b0, b1) = edges[i], edges[i + 1]
            uv = [(us[0], i / n), (us[1], i / n), (us[1], (i + 1) / n), (us[0], (i + 1) / n)]
            self.face([ids[i][0], ids[i][1], ids[i + 1][1], ids[i + 1][0]], mat, uv=uv, nrm=[nrm_for(p) for p in (a0, a1, b1, b0)])

    def _emit_tufts(self, cfg):
        """Each tuft: planes cards crossing at its foot, spread evenly round, each leaning a little to one side and bent
        once halfway up, so it arches; a share carry a card of flowering stalks, taller and less bent."""
        r = random.Random(self.seed * 7 + 3)
        leaves, flowers = self.slot("leaves"), self.slot("extra")
        planes, tilt = max(1, int(cfg["planes"])), cfg["tilt"]
        for foot, h, w in self.tufts:
            az = r.uniform(0, TAU)

            def nrm(p, foot=foot):  # mostly up, a little out from the tuft's middle
                out = Vector((p.x - foot.x, p.y - foot.y, 0))
                return (UP * 0.8 + (out.normalized() * 0.2 if out.length > 1e-4 else Vector())).normalized()

            for i in range(planes):
                a = az + i * math.pi / planes + r.uniform(-0.25, 0.25) * tilt
                self._bent_card(r, foot, a, h * r.uniform(0.85, 1.1), w, cfg["lean"] * r.uniform(0.5, 1.2), cfg["bend"],
                                tilt, leaves, nrm)
            if r.random() < cfg["extra"]:
                fa = az + r.uniform(0, math.pi)
                for i in range(2):  # the flowering stalks: two cards across each other
                    self._bent_card(r, foot, fa + i * math.pi / 2, h * cfg["flower_height"] * r.uniform(0.9, 1.05), w * 0.8,
                                    cfg["lean"] * 0.4, cfg["bend"] * 0.3, tilt, flowers, nrm)

    def _emit_patch(self, cfg):
        """A patch of long grass: planes cards of strands crossing near its middle, spread evenly round, each leaning a
        little and bent once halfway up; with flowers (variant B), two cards of seed heads across each other among
        them, taller and less bent."""
        r = random.Random(self.seed * 7 + 3)
        planes, tilt = max(1, int(cfg["planes"])), cfg["tilt"]
        H, W = 0.5 * cfg["size"], 0.65 * cfg["width"]
        az = r.uniform(0, TAU)
        (sw, sh), (fw, fh) = self.fits  # the cards are cropped to what's on them: sized by what they kept

        def nrm(p):  # mostly up, a little out from the patch's middle
            out = Vector((p.x, p.y, 0))
            return (UP * 0.8 + (out.normalized() * 0.2 if out.length > 1e-4 else Vector())).normalized()

        for i in range(planes):
            foot = Vector((r.uniform(-1, 1), r.uniform(-1, 1), 0)) * 0.1  # not quite at one point: no star from above
            self._bent_card(r, foot, az + i * math.pi / planes + r.uniform(-0.2, 0.2) * tilt, H * sh * r.uniform(0.85, 1.1), W * sw,
                            cfg["lean"] * r.uniform(0.5, 1.2), cfg["bend"], tilt, self.slot("leaves"), nrm)
        if self.flowering and cfg["extra"] > 0:
            fa = az + r.uniform(0, math.pi)
            for i in range(2):
                self._bent_card(r, Vector(), fa + i * math.pi / 2, H * cfg["flower_height"] * fh * r.uniform(0.9, 1.05), W * 0.6 * fw,
                                cfg["lean"] * 0.4, cfg["bend"] * 0.3, tilt, self.slot("extra"), nrm)

    def _bent_card(self, r, foot, az, h, w, lean, bend, tilt, mat, nrm):
        right = Vector((math.cos(az), math.sin(az), 0))
        side = Vector((-math.sin(az), math.cos(az), 0)) * (1 if r.random() < 0.5 else -1)  # the way it leans
        lean = lean + r.uniform(-0.1, 0.1) * tilt
        up0 = (UP * math.cos(lean) + side * math.sin(lean)).normalized()
        up1 = (UP * math.cos(lean + bend) + side * math.sin(lean + bend)).normalized()
        self._strip(foot - UP * 0.02, right, [up0 * h * 0.5, up1 * h * 0.5], w, mat, nrm, r.random() < 0.5)

    def _emit_fronds(self, cfg):
        """Each frond a card in three segments from the middle of the ring: rising at the frond angle, arching over by
        the arch, rolled a little; its face looks up."""
        r = random.Random(self.seed * 7 + 3)
        mat = self.slot("leaves")
        rise, bend, tilt = math.radians(cfg["rise"]), cfg["bend"], cfg["tilt"]
        for foot, az, length in self.fronds:
            el = rise + r.uniform(-0.12, 0.12) * tilt
            right = Vector((-math.sin(az), math.cos(az), 0))
            roll = Quaternion(direction(az, 0), r.uniform(-0.25, 0.25) * tilt)
            right = roll @ right
            ups = []
            for k in range(3):
                e = el - bend * k * 1.1
                ups.append(direction(az, e) * length / 3)
            face_up = right.cross(ups[0]).normalized()
            if face_up.z < 0:
                face_up = -face_up

            def nrm(p, face_up=face_up):
                return (face_up + UP * 0.6).normalized()

            self._strip(foot, right, ups, length * 0.75, mat, nrm, r.random() < 0.5)


def spots(r, n, radius, gap=0.0):
    """n spots in a disc, spread like seeds in a sunflower, a little jittered."""
    out = []
    for i in range(n):
        d = radius * math.sqrt((i + 0.5) / n)
        a = i * 2.39996 + r.uniform(-0.3, 0.3)
        d = min(radius, max(0.0, d + r.uniform(-1, 1) * gap))
        out.append(Vector((math.cos(a) * d, math.sin(a) * d, 0)))
    return out


# ------------------------------------------------------------------ the bushes
def envelope(z, H, R):
    """How far a bush reaches out from its middle at height z: furthest at its foot, rounding over to its top."""
    t = max(0.0, min(1.0, z / H))
    return R * (1 - t ** 1.5) ** 0.65


def dome_bush(T, cfg, H, R, stem_cols, twig_cols, clump, stem_r, per_stem, clumps_at=(0.35, 0.65, 1.0)):
    """A full bush, widest at its foot: stems from a wide foot, leaning out, with branches all the way down, the lowest
    longest and nearly level, drooping to the ground, the higher ones shorter and rising, so their clumps fill a dome
    H high and R out from the middle (envelope). Clumps along and at the end of every branch, and at the stems' tops."""
    r = T.r
    H, R = H * cfg["height"], R * cfg["width"]
    n = max(1, int(cfg["stems"]))
    az0 = r.uniform(0, TAU)
    for k in range(n):
        az = az0 + k * TAU / n + r.uniform(-0.35, 0.35)
        out = Vector((math.cos(az), math.sin(az), 0))
        foot = out * r.uniform(0.05, 0.3) * min(1.0, R / 1.4)
        h = H * r.uniform(0.7, 0.95)
        lean = R * r.uniform(0.08, 0.22)  # how far out the stem's top stands
        stem = [foot - UP * 0.05 + out * (lean * (i / 6) ** 1.4) + UP * (h * i / 6) for i in range(7)]
        T.tube(stem, taper(stem_r, stem_r * 0.25, 7), 5, lambda i, k: pick(r, *stem_cols))
        m = r.randint(*per_stem)
        for j in range(m):
            t = 0.06 + 0.8 * (j + r.uniform(0.0, 0.8)) / m
            p = along(stem, t)
            el = -0.05 + 0.8 * t + r.uniform(-0.12, 0.12)  # the low ones level, the high ones rising
            d = direction(az + r.uniform(-1.4, 1.4), el)
            out_d = Vector((d.x, d.y, 0)).normalized()
            L = 0.5
            for _ in range(3):  # long enough for its tip to reach the dome's outline at the tip's own height
                reach = envelope(p.z + L * math.sin(el), H, R) - Vector((p.x, p.y, 0)).dot(out_d)
                L = max(0.25, reach / max(0.4, math.cos(el)))
            L *= r.uniform(0.75, 1.0)
            b = limb(r, p, d, L, 3, droop=0.1 + 0.25 * (1 - t))
            T.tube(b, taper(stem_r * 0.4, stem_r * 0.12, 4), 4, lambda i, k: pick(r, *twig_cols))
            for f in clumps_at if L > 0.6 else clumps_at[-1:]:
                s_ = clump * r.uniform(0.85, 1.15) * (1.0 - 0.25 * t)
                c = along(b, f) + Vector((0, 0, 0.05))
                c.z = max(c.z, s_ * 0.3)  # the skirt's clumps sit on the ground rather than in it
                T.clump(c, s_, "extra" if r.random() < cfg["extra"] else "leaves", squash=0.85)
        T.clump(stem[-1], clump * r.uniform(0.9, 1.1), squash=0.9)
    return T, "dome"


def raspberry(seed, cfg):
    """A thicket of canes from a wide patch, rising and arching over and out, leafy along their upper part, the berries
    hanging below; short new shoots round its edge fill it down to the ground, so it's widest at its foot."""
    T = Plant(seed)
    r = T.r
    H, W = 2.3 * cfg["height"], cfg["width"]
    az0 = r.uniform(0, TAU)
    n = max(1, int(cfg["stems"]))
    for k in range(n):
        az = az0 + k * 2.39996 + r.uniform(-0.3, 0.3)
        foot = Vector((math.cos(az), math.sin(az), 0)) * r.uniform(0.05, 0.45) * W - UP * 0.05
        L = H * r.uniform(0.85, 1.15)
        cane = limb(r, foot, direction(az, r.uniform(1.05, 1.32)), L, 6, droop=0.48, wiggle=0.04)
        cane = [foot + Vector(((p.x - foot.x) * W, (p.y - foot.y) * W, p.z - foot.z)) for p in cane]  # width: how far they reach out
        T.tube(cane, taper(0.016, 0.005, 7), 4, lambda i, k: pick(r, "#7A4A3A", "#6A4A34", "#7A6A3E"))
        for f in (0.3, 0.48, 0.64, 0.8, 0.94):
            p = along(cane, f)
            T.clump(p + Vector((0, 0, 0.04)), r.uniform(0.42, 0.55), "extra" if (f > 0.45 and r.random() < cfg["extra"]) else "leaves",
                    squash=0.85)
    for k in range(max(1, n // 2)):  # new shoots round the edge, low and leaning out
        az = az0 + (k + 0.5) * TAU / max(1, n // 2) + r.uniform(-0.3, 0.3)
        foot = Vector((math.cos(az), math.sin(az), 0)) * r.uniform(0.45, 0.7) * W - UP * 0.05
        shoot = limb(r, foot, direction(az, r.uniform(0.7, 1.0)), r.uniform(0.6, 0.95) * W, 4, droop=0.25, wiggle=0.04)
        T.tube(shoot, taper(0.011, 0.004, 5), 4, lambda i, k: pick(r, "#6A8A3A", "#7A6A3E"))
        for f in (0.45, 0.75, 1.0):
            c = along(shoot, f) + Vector((0, 0, 0.04))
            c.z = max(c.z, 0.14)
            T.clump(c, r.uniform(0.4, 0.5), squash=0.85)
    return T, "dome"


def alder_buckthorn(seed, cfg):
    """Slender, dark stems from a wide foot, side branches held out level, the lowest longest, down to the ground, a
    full crown of glossy oval leaves widest at its foot; the berries in small groups along the twigs, green, red and
    black at once."""
    return dome_bush(Plant(seed), cfg, 2.3, 1.3, ("#3E3A36", "#4A4440", "#56504A"), ("#4A4440", "#56504A"),
                     0.6, 0.032, (5, 7))


def hazel(seed, cfg):
    """Many smooth, grey-brown stems from one wide foot, leaning out, a full, rounded mass of broad leaves from the
    ground up, widest at its foot; the nuts in their husks, two or three together."""
    return dome_bush(Plant(seed), cfg, 2.75, 1.75, ("#7A6A58", "#8A7A66", "#6E604E"), ("#7A6A58", "#6E604E"),
                     0.82, 0.042, (5, 7))


# ------------------------------------------------------------------ the fern
def wood_fern(seed, cfg):
    """A ring of fronds from one crown, rising and arching over: a shuttlecock."""
    T = Plant(seed)
    r = T.r
    n = max(3, int(cfg["planes"]))
    az0 = r.uniform(0, TAU)
    for k in range(n):
        az = az0 + k * TAU / n + r.uniform(-0.2, 0.2)
        L = 0.75 * cfg["size"] * r.uniform(0.8, 1.1)
        T.fronds.append((Vector((math.cos(az), math.sin(az), 0)) * 0.03, az, L))
    return T, "sphere"


# ------------------------------------------------------------------ the grasses
def grass(T, cfg, height, width, tufts, radius):
    """A clump of grass: tufts tufts (times the setting) in a patch radius across (times its spread), each height tall
    and its cards width wide for each metre of height."""
    r = T.r
    n = max(1, round(tufts * cfg["density"]))
    for p in spots(r, n, radius * cfg["spread"] * math.sqrt(n / tufts), 0.05):
        h = height * cfg["size"] * r.uniform(0.8, 1.1) * (1 - 0.25 * p.length / max(radius * 1.5, 1e-6))
        T.tufts.append((p, h, h * width * cfg["width"]))
    return T, "tufts"


def wavy_hair_grass(seed, cfg):
    """Fine, hair-thin, curling tufts, the pine forest's grass, its airy flowers purple-silver."""
    return grass(Plant(seed), cfg, 0.32, 1.1, 5, 0.25)


def common_bent(seed, cfg):
    """The meadow grass: narrow, flat blades, its airy flowers reddish-purple."""
    return grass(Plant(seed), cfg, 0.38, 0.95, 5, 0.25)


def wood_small_reed(seed, cfg):
    """Tall grass at the forest's edges: broad blades arching over, narrow pale panicles on tall stalks."""
    return grass(Plant(seed), cfg, 0.62, 1.0, 4, 0.3)


def purple_moor_grass(seed, cfg):
    """A dense tussock on wet ground, stiff grey-green blades, narrow dark purple flowers."""
    return grass(Plant(seed), cfg, 0.5, 0.85, 4, 0.16)


def common_sedge(seed, cfg):
    """Stiff, dark blue-green blades by water and in bogs, dark brown spikes on their stems."""
    return grass(Plant(seed), cfg, 0.42, 0.8, 4, 0.2)


def long_grass(seed, cfg):
    """A patch of long grass, thick and semi-long: cards of thin strands crossing near its middle (Plant._emit_patch)."""
    return Plant(seed), "patch"


def cottongrass(seed, cfg):
    """A round tussock of wiry leaves in the bog, white tufts of cotton above it."""
    return grass(Plant(seed), cfg, 0.32, 1.0, 4, 0.14)


SPECIES = [  # key, builder, English name, Swedish name, Latin name, width in the lineup (m), card set, kind
    ("Raspberry", raspberry, "Raspberry", "Hallon", "Rubus idaeus", 2.8, "raspberry", "bush"),
    ("AlderBuckthorn", alder_buckthorn, "Alder buckthorn", "Brakved", "Frangula alnus", 3.2, "buckthorn", "bush"),
    ("Hazel", hazel, "Hazel", "Hassel", "Corylus avellana", 4.4, "hazel", "bush"),
    ("WoodFern", wood_fern, "Wood fern", "Skogsbräken", "Dryopteris carthusiana", 1.5, "fern", "fern"),
    ("LongGrass", long_grass, "Long grass", "Långt gräs", "Poa, Festuca, Agrostis", 0.9, "longgrass", "patch"),
    ("WavyHairGrass", wavy_hair_grass, "Wavy hair-grass", "Kruståtel", "Avenella flexuosa", 0.9, "hairgrass", "grass"),
    ("CommonBent", common_bent, "Common bent", "Rödven", "Agrostis capillaris", 0.9, "bent", "grass"),
    ("WoodSmallReed", wood_small_reed, "Wood small-reed", "Piprör", "Calamagrostis arundinacea", 1.2, "smallreed", "grass"),
    ("PurpleMoorGrass", purple_moor_grass, "Purple moor-grass", "Blåtåtel", "Molinia caerulea", 0.9, "moorgrass", "grass"),
    ("CommonSedge", common_sedge, "Common sedge", "Hundstarr", "Carex nigra", 0.9, "sedge", "grass"),
    ("Cottongrass", cottongrass, "Hare's-tail cottongrass", "Tuvull", "Eriophorum vaginatum", 0.8, "cottongrass", "grass"),
]
BY_KEY = {s[0]: s for s in SPECIES}
GROUPS = {"BUSHES": ("bush", "fern"), "GRASSES": ("patch", "grass")}


def kind(key):
    return BY_KEY[key][7]


def load_settings():
    """The saved settings (plant_settings.json) over the defaults, per plant."""
    saved = {}
    if os.path.exists(SETTINGS):
        with open(SETTINGS) as fh:
            saved = json.load(fh)
    return {k: dict(DEFAULTS[k], **{n: v for n, v in saved.get(k, {}).items() if n in BASE}) for k in DEFAULTS}


def _cards():
    path = os.path.join(TEXTURES, "cards.json")
    return json.load(open(path)) if os.path.exists(path) else {}


def card_names():
    """card set -> the names of its designs, in order (written by make_plant_cards.py)."""
    return _cards().get("names", {})


def fit_of(card, n, extra=None):
    """How much of a card's drawing it kept, width and height, if it was cropped to what's on it (the long grass's)."""
    name = f"{card}_{n}" + (f"_{extra}" if extra else "")
    return tuple(_cards().get("fits", {}).get(name, (1.0, 1.0)))


def extra_of(key):
    """What the plant's extra card carries: berries, flowers or nuts (None for the fern)."""
    return _cards().get("extras", {}).get(BY_KEY[key][6])


# ------------------------------------------------------------------ materials
def stem_material(key):
    """The stems' material ("Stems <plant>"): the colour attribute, per face."""
    name = f"Stems {key}"
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    col = nt.nodes.new("ShaderNodeAttribute")
    col.attribute_name = "Col"
    bsdf = nt.nodes["Principled BSDF"]
    nt.links.new(col.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.9
    return m


def card_image(card, n, extra=None):
    name = f"{card}_{n}" + (f"_{extra}" if extra else "")
    img = bpy.data.images.get(name + ".png")
    if img is None:
        img = bpy.data.images.load(os.path.join(TEXTURES, name + ".png"), check_existing=True)
    return img


def materials_for(key, cfg):
    """The plant's materials, with its chosen card and tint applied (the extra card tinted alike)."""
    card, extra = BY_KEY[key][6], extra_of(key)
    mats = {"stems": stem_material(key), "leaves": treegen.leaf_material(f"Leaves {key}")}
    if extra:
        mats["extra"] = treegen.leaf_material(f"{extra.capitalize()} {key}")
    for slot, m in mats.items():
        if slot == "stems":
            continue
        nodes = m.node_tree.nodes
        nodes["Card"].image = card_image(card, int(cfg["card"]), extra if slot == "extra" else None)
        nodes["Tint"].inputs["Hue"].default_value = cfg["hue"]
        nodes["Tint"].inputs["Saturation"].default_value = cfg["saturation"]
        nodes["Tint"].inputs["Value"].default_value = cfg["brightness"]
    return mats


# each plant's seed number, kept as it was when the portfolio had the dwarf shrubs first, so the plants still there
# grow as they did
SEED_INDEX = {"Raspberry": 3, "AlderBuckthorn": 4, "Hazel": 5, "WoodFern": 6, "WavyHairGrass": 7, "CommonBent": 8,
              "WoodSmallReed": 9, "PurpleMoorGrass": 10, "CommonSedge": 11, "Cottongrass": 12, "LongGrass": 13}


def seed_for(key, variant, cfg):
    i = SEED_INDEX[key]
    return 5000 + 97 * i + 13 * "AB".index(variant) + 7919 * int(cfg["seed"])


def build_into(key, variant, cfg, me):
    """(Re)build one plant into the mesh me. Returns (cards, faces)."""
    builder = BY_KEY[key][1]
    plant, crown = builder(seed_for(key, variant, cfg), cfg)
    plant.flowering = variant == "B"
    card, extra = BY_KEY[key][6], extra_of(key)
    plant.fits = (fit_of(card, int(cfg["card"])), fit_of(card, int(cfg["card"]), extra))
    plant.emit(crown, cfg, kind(key))
    plant.to_mesh(me, materials_for(key, cfg))
    return sum(1 for m in plant.mat if m > 0), len(plant.f)
