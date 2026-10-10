"""The plant generator: low-poly bushes and grasses of the Swedish forest, of crossed-plane cards like the trees' leaves.

Used by make_plants.py (builds the portfolio .blend) and plant_editor.py (the editor panel in Blender). It builds on the
tree generator (../trees/treegen.py): its faceted tubes for stems and its crossed clumps for leaves. Every plant is one
mesh with up to three materials: its stems, coloured per face; its card (make_plant_cards.py); and the card's extra
version, with berries, flowers or nuts for a bush, or a card of flowering stalks for a grass. A plant is rebuilt in
place from its kind, variant and settings (see DEFAULTS), so the plants in the .blend, and their linked copies on the
forest floor, follow the settings.

Four kinds of plant:
- Dwarf shrubs (blueberry, lingonberry, heather): a low mound of crossed clumps over a patch of ground, a few stems
  under them. The cards face out from the mound's foot, so it shades as one rounded mound.
- Bushes (raspberry, alder buckthorn, hazel): stems from the ground, branching, with crossed clumps along and at the
  ends of their branches, as a small tree's crown.
- The fern: a ring of fronds, each a card from the middle of the ring, rising and arching over, bent in three.
- Grasses: tufts of crossed cards standing on the ground, each bent once so it arches; a share of the tufts carry a
  card of flowering stalks, taller, crossed among them. Their normals point mostly up, so a tuft is lit as the ground
  under it is.
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
    "Blueberry": dict(BASE, card=2, size=1.25, planes=3, density=2.0, spread=0.8),
    "Lingonberry": dict(BASE, planes=3, density=2.2, spread=0.7, size=1.4),
    "Heather": dict(BASE, planes=3, size=1.15, density=1.6, upright=1.1, extra=0.35),
    "Raspberry": dict(BASE, stems=7, extra=0.25),
    "AlderBuckthorn": dict(BASE, stems=4, extra=0.3),
    "Hazel": dict(BASE, stems=8, extra=0.15),
    "WoodFern": dict(BASE, planes=9, rise=60.0, bend=0.45),
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

    def _facing(self, p, cen, crown):
        """A low mound's cards face out from its foot, not its middle, so its top faces up."""
        if crown == "dome":
            return Vector((cen.x, cen.y, -0.1))
        return super()._facing(p, cen, crown)

    def emit(self, crown, cfg, kind):
        if kind == "grass":
            self._emit_tufts(cfg)
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
        for i in range(n):
            a, b = rows[i], rows[i + 1]
            corners = [a - right * width / 2, a + right * width / 2, b + right * width / 2, b - right * width / 2]
            uv = [(us[0], i / n), (us[1], i / n), (us[1], (i + 1) / n), (us[0], (i + 1) / n)]
            self.face([self.vert(p) for p in corners], mat, uv=uv, nrm=[nrm_for(p) for p in corners])

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


# ------------------------------------------------------------------ the dwarf shrubs
def mound(T, cfg, height, width, clump, stem_cols, squash=0.9, stem_share=0.5):
    """A low mound of crossed clumps over a patch: the clumps' centres under a dome height high and width across,
    their feet at the ground toward its edge; under some, a thin stem from the ground."""
    r = T.r
    H, R = height * cfg["height"], 0.5 * width * cfg["width"]
    n = max(3, round(16 * (R / 0.5) ** 2))
    for p in spots(r, n, R, 0.06):
        d = min(1.0, p.length / max(R, 1e-6))
        top = H * (1 - d * d) ** 0.6 * r.uniform(0.75, 1.0)
        s = clump * r.uniform(0.85, 1.15) * (1 - 0.25 * d)
        c = p + UP * max(s * 0.38, top - s * 0.3)
        T.clump(c, s, "extra" if r.random() < cfg["extra"] else "leaves", squash=squash, flat=1.0)
        if r.random() < stem_share:
            T.tube([p - UP * 0.02, c.lerp(p, 0.5) + Vector((r.uniform(-1, 1), r.uniform(-1, 1), 0)) * 0.02, c - UP * s * 0.1],
                   [0.008, 0.006, 0.003], 3, lambda i, k: pick(r, *stem_cols))
    return T, "dome"


def blueberry(seed, cfg):
    """A patch of bright green, upright sprigs, knee-high at most; the berries single, dark blue."""
    return mound(Plant(seed), cfg, 0.36, 1.0, 0.3, ("#4E7E2A", "#5A8A30"))


def lingonberry(seed, cfg):
    """A low, dense mat of dark, glossy leaves; the berries bright red, in clusters at the tips."""
    return mound(Plant(seed), cfg, 0.2, 0.85, 0.22, ("#5A4632", "#6A5238"), squash=0.8, stem_share=0.3)


def heather(seed, cfg):
    """A low, wiry, bushy mound, dark olive; in flower, small pink-mauve bells along its upper sprigs."""
    return mound(Plant(seed), cfg, 0.42, 0.95, 0.34, ("#5A4A3A", "#4A3E30"), squash=1.0, stem_share=0.6)


# ------------------------------------------------------------------ the bushes
def raspberry(seed, cfg):
    """Canes from the ground, rising and arching over, leafy along their upper part; the berries hanging below."""
    T = Plant(seed)
    r = T.r
    H, W = 1.75 * cfg["height"], cfg["width"]
    az0 = r.uniform(0, TAU)
    for k in range(max(1, int(cfg["stems"]))):
        az = az0 + k * 2.39996 + r.uniform(-0.3, 0.3)
        foot = Vector((math.cos(az), math.sin(az), 0)) * r.uniform(0.05, 0.3) * W - UP * 0.05
        L = H * r.uniform(0.8, 1.15)
        cane = limb(r, foot, direction(az, r.uniform(1.1, 1.35)), L, 6, droop=0.42, wiggle=0.04)
        cane = [foot + Vector(((p.x - foot.x) * W, (p.y - foot.y) * W, p.z - foot.z)) for p in cane]  # width: how far they reach out
        T.tube(cane, taper(0.014, 0.005, 7), 4, lambda i, k: pick(r, "#7A4A3A", "#6A4A34", "#7A6A3E"))
        for f in (0.4, 0.55, 0.7, 0.85, 1.0):
            p = along(cane, f)
            T.clump(p + Vector((0, 0, 0.04)), r.uniform(0.36, 0.46), "extra" if (f > 0.5 and r.random() < cfg["extra"]) else "leaves",
                    squash=0.85)
    return T, "sphere"


def alder_buckthorn(seed, cfg):
    """A few slender, dark stems, side branches held out level, an open, airy crown of glossy oval leaves; the berries
    in small groups along the twigs, green, red and black at once."""
    T = Plant(seed)
    r = T.r
    H, W = 2.4 * cfg["height"], cfg["width"]
    az0 = r.uniform(0, TAU)
    for k in range(max(1, int(cfg["stems"]))):
        az = az0 + k * TAU / max(1, int(cfg["stems"])) + r.uniform(-0.4, 0.4)
        foot = Vector((math.cos(az), math.sin(az), 0)) * r.uniform(0.05, 0.18)
        h = H * r.uniform(0.75, 1.0)
        stem = limb(r, foot - UP * 0.05, direction(az, r.uniform(1.25, 1.42)), h, 6, wiggle=0.08)
        T.tube(stem, taper(0.035, 0.008, 7), 5, lambda i, k: pick(r, "#3E3A36", "#4A4440", "#56504A"))
        for j in range(r.randint(4, 6)):
            t = 0.35 + 0.55 * j / 5 + r.uniform(-0.04, 0.04)
            p = along(stem, t)
            baz = az + r.uniform(-1.8, 1.8)
            L = r.uniform(0.5, 0.95) * W * (1.15 - t * 0.6)
            b = limb(r, p, direction(baz, r.uniform(0.1, 0.5)), L, 3, droop=0.08)
            T.tube(b, taper(0.014, 0.005, 4), 4, lambda i, k: pick(r, "#4A4440", "#56504A"))
            for f in (0.55, 1.0):
                T.clump(along(b, f) + Vector((0, 0, 0.05)), r.uniform(0.5, 0.65), "extra" if r.random() < cfg["extra"] else "leaves",
                        squash=0.8)
        T.clump(stem[-1], r.uniform(0.55, 0.7), squash=0.9)
    return T, "sphere"


def hazel(seed, cfg):
    """Many stems from one foot, fanning out like a vase, smooth and grey-brown; a full, rounded crown of broad leaves;
    the nuts in their husks, two or three together."""
    T = Plant(seed)
    r = T.r
    H, W = 3.0 * cfg["height"], cfg["width"]
    az0 = r.uniform(0, TAU)
    n = max(1, int(cfg["stems"]))
    for k in range(n):
        az = az0 + k * TAU / n + r.uniform(-0.3, 0.3)
        foot = Vector((math.cos(az), math.sin(az), 0)) * r.uniform(0.1, 0.3)
        h = H * r.uniform(0.7, 1.0)
        out = r.uniform(0.25, 0.45) * W
        stem = [foot - UP * 0.05 + Vector((math.cos(az), math.sin(az), 0)) * (out * h * (i / 6) ** 1.6) + UP * (h * i / 6)
                for i in range(7)]
        T.tube(stem, taper(0.045, 0.012, 7), 5, lambda i, k: pick(r, "#7A6A58", "#8A7A66", "#6E604E"))
        for j in range(r.randint(3, 5)):
            t = 0.45 + 0.5 * j / 4 + r.uniform(-0.04, 0.04)
            p = along(stem, t)
            L = r.uniform(0.6, 1.1) * W * (1.2 - t * 0.5)
            b = limb(r, p, direction(az + r.uniform(-1.2, 1.2), r.uniform(0.3, 0.7)), L, 3, droop=0.15)
            T.tube(b, taper(0.016, 0.005, 4), 4, lambda i, k: pick(r, "#7A6A58", "#6E604E"))
            for f in (0.5, 1.0):
                T.clump(along(b, f) + Vector((0, 0, 0.06)), r.uniform(0.75, 0.95), "extra" if r.random() < cfg["extra"] else "leaves",
                        squash=0.85)
        T.clump(stem[-1], r.uniform(0.8, 1.0), squash=0.9)
    return T, "sphere"


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


def cottongrass(seed, cfg):
    """A round tussock of wiry leaves in the bog, white tufts of cotton above it."""
    return grass(Plant(seed), cfg, 0.32, 1.0, 4, 0.14)


SPECIES = [  # key, builder, English name, Swedish name, Latin name, width in the lineup (m), card set, kind
    ("Blueberry", blueberry, "Blueberry", "Blåbär", "Vaccinium myrtillus", 1.3, "blueberry", "dwarf"),
    ("Lingonberry", lingonberry, "Lingonberry", "Lingon", "Vaccinium vitis-idaea", 1.1, "lingonberry", "dwarf"),
    ("Heather", heather, "Heather", "Ljung", "Calluna vulgaris", 1.2, "heather", "dwarf"),
    ("Raspberry", raspberry, "Raspberry", "Hallon", "Rubus idaeus", 2.2, "raspberry", "bush"),
    ("AlderBuckthorn", alder_buckthorn, "Alder buckthorn", "Brakved", "Frangula alnus", 2.6, "buckthorn", "bush"),
    ("Hazel", hazel, "Hazel", "Hassel", "Corylus avellana", 3.6, "hazel", "bush"),
    ("WoodFern", wood_fern, "Wood fern", "Skogsbräken", "Dryopteris carthusiana", 1.5, "fern", "fern"),
    ("WavyHairGrass", wavy_hair_grass, "Wavy hair-grass", "Kruståtel", "Avenella flexuosa", 0.9, "hairgrass", "grass"),
    ("CommonBent", common_bent, "Common bent", "Rödven", "Agrostis capillaris", 0.9, "bent", "grass"),
    ("WoodSmallReed", wood_small_reed, "Wood small-reed", "Piprör", "Calamagrostis arundinacea", 1.2, "smallreed", "grass"),
    ("PurpleMoorGrass", purple_moor_grass, "Purple moor-grass", "Blåtåtel", "Molinia caerulea", 0.9, "moorgrass", "grass"),
    ("CommonSedge", common_sedge, "Common sedge", "Hundstarr", "Carex nigra", 0.9, "sedge", "grass"),
    ("Cottongrass", cottongrass, "Hare's-tail cottongrass", "Tuvull", "Eriophorum vaginatum", 0.8, "cottongrass", "grass"),
]
BY_KEY = {s[0]: s for s in SPECIES}
GROUPS = {"BUSHES": ("dwarf", "bush", "fern"), "GRASSES": ("grass",)}


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


def seed_for(key, variant, cfg):
    i = [s[0] for s in SPECIES].index(key)
    return 5000 + 97 * i + 13 * "AB".index(variant) + 7919 * int(cfg["seed"])


def build_into(key, variant, cfg, me):
    """(Re)build one plant into the mesh me. Returns (cards, faces)."""
    builder = BY_KEY[key][1]
    plant, crown = builder(seed_for(key, variant, cfg), cfg)
    plant.emit(crown, cfg, kind(key))
    plant.to_mesh(me, materials_for(key, cfg))
    return sum(1 for m in plant.mat if m > 0), len(plant.f)
