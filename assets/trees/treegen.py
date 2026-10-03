"""The tree generator: low-poly trees of the Swedish forest with crossed-plane leaf clumps.

Used by make_trees.py (builds the portfolio .blend) and tree_editor.py (the editor panel in Blender). Every tree is
one mesh with up to three materials: faceted bark coloured per face, the species' leaf card, and for rowan a card with
berries. A tree is rebuilt in place from its species, variant and settings (see DEFAULTS), so the trees in the .blend,
and their linked copies in the grove, follow the settings.

Leaf clumps are crossed planes: copies of a leaf card crossing at the clump's centre, one lying nearly flat for the
view from above and the rest standing upright, spread evenly around. Their normals point out from the crown, so a
crown shades as one rounded volume instead of as many flat cards.
"""
import json
import math
import os
import random

import bpy
from mathutils import Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
TEXTURES = os.path.join(HERE, "textures")
SETTINGS = os.path.join(HERE, "tree_settings.json")
TAU = math.tau
UP = Vector((0, 0, 1))

# what each setting does is described in tree_editor.py, next to its slider
BASE = dict(card=1, size=1.0, planes=3, density=1.0, spread=1.0, upright=1.0, flat=True, tilt=1.0,
            brightness=1.0, hue=0.5, saturation=1.0, height=1.0, width=1.0, seed=0, berries=0.3)
DEFAULTS = {
    "ScotsPine": dict(BASE, card=1, size=0.55, planes=5, density=4.5, spread=0.9),  # small tufts packed into pads
    "SilverBirch": dict(BASE),
    "NorwaySpruce": dict(BASE),
    "Aspen": dict(BASE),
    "Rowan": dict(BASE),
    "Alder": dict(BASE),
    "Juniper": dict(BASE),
}


def lin(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c) + (1.0,)


def jit(c, r, amt=0.07):
    f = 1 + r.uniform(-amt, amt)
    return (c[0] * f, c[1] * f, c[2] * f, 1.0)


def pick(r, *hexes):
    return jit(lin(r.choice(hexes)), r)


def direction(az, el):
    return Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))


def along(pts, f):
    f = max(0.0, min(1.0, f)) * (len(pts) - 1)
    i = min(int(f), len(pts) - 2)
    return pts[i].lerp(pts[i + 1], f - i)


def newell(pts):
    n = Vector((0, 0, 0))
    for i, a in enumerate(pts):
        b = pts[(i + 1) % len(pts)]
        n.x += (a.y - b.y) * (a.z + b.z)
        n.y += (a.z - b.z) * (a.x + b.x)
        n.z += (a.x - b.x) * (a.y + b.y)
    return n.normalized() if n.length > 1e-12 else UP.copy()


# ------------------------------------------------------------------ building a tree
class Tree:
    def __init__(self, seed):
        self.seed = seed
        self.r = random.Random(seed)
        self.v, self.f, self.mat, self.col, self.uv, self.nrm = [], [], [], [], [], []
        self.clumps = []
        self.slots = ["bark"]

    def slot(self, name):
        if name not in self.slots:
            self.slots.append(name)
        return self.slots.index(name)

    def vert(self, p):
        self.v.append(Vector(p))
        return len(self.v) - 1

    def face(self, idx, mat=0, col=(1, 1, 1, 1), uv=None, nrm=None):
        self.f.append(tuple(idx))
        self.mat.append(mat)
        self.col.append(col)
        self.uv.append(uv)
        self.nrm.append(nrm)

    def tube(self, pts, radii, sides, colour):
        """A tapered tube along pts, faceted; colour(i, k) gives segment i, side k. A zero end radius makes a point."""
        n = len(pts)
        tang = [(pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized() for i in range(n)]
        ref = UP if abs(tang[0].z) < 0.9 else Vector((1, 0, 0))
        nrm = tang[0].cross(ref).normalized()
        rot0 = self.r.uniform(0, TAU)
        rings = []
        for i in range(n):
            if i:
                nrm = tang[i - 1].rotation_difference(tang[i]) @ nrm
            t = tang[i]
            nrm = (nrm - t * nrm.dot(t)).normalized()
            b = t.cross(nrm)
            if radii[i] <= 1e-4:
                rings.append([self.vert(pts[i])])
                continue
            rings.append([self.vert(pts[i] + (nrm * math.cos(rot0 + k * TAU / sides) + b * math.sin(rot0 + k * TAU / sides)) * radii[i])
                          for k in range(sides)])
        for i in range(n - 1):
            a, b = rings[i], rings[i + 1]
            for k in range(sides):
                if len(b) == 1:
                    self.face((a[k], a[(k + 1) % sides], b[0]), col=colour(i, k))
                else:
                    self.face((a[k], a[(k + 1) % sides], b[(k + 1) % sides], b[k]), col=colour(i, k))
        if len(rings[-1]) > 1:
            self.face(rings[-1], col=colour(n - 2, 0))

    def clump(self, c, size, card="leaves", squash=1.0, flat=1.0, hang=False):
        """Queue a leaf clump at c. squash scales the upright cards' height and flat the lying card; hang keeps the
        texture's top up on the upright cards (for twigs that hang, like birch)."""
        self.clumps.append((Vector(c), size, self.slot(card), squash, flat, hang))

    def emit_leaves(self, crown, cfg):
        """Turn the queued clumps into crossed cards, by the settings. Uses its own random numbers, so the leaf
        settings never change the trunk and branches."""
        if not self.clumps:
            return
        r = random.Random(self.seed * 7 + 3)
        cen = sum((c[0] for c in self.clumps), Vector()) / len(self.clumps)
        density, spread, tilt = cfg["density"], cfg["spread"], cfg["tilt"]
        for c, size, mat, squash, flat, hang in self.clumps:
            # a patch: the extra clumps fill the flattened volume the full-size clump would take up, scaled by spread
            n = int(density) + (1 if r.random() < density - int(density) else 0)
            rx, rz = size * flat * 0.5 * spread, size * squash * 0.5 * spread
            for k in range(n):
                p = c
                if k:
                    u = Vector((1, 1, 1))
                    while u.length > 1:
                        u = Vector((r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(-1, 1)))
                    p = c + Vector((u.x * rx, u.y * rx, u.z * rz))
                s = size * cfg["size"] * (1.0 if k == 0 else r.uniform(0.8, 1.0))
                self._clump_cards(r, p, s, mat, squash * cfg["upright"], flat, hang, cfg["planes"], cfg["flat"], tilt, cen, crown)

    def _clump_cards(self, r, c, size, mat, squash, flat, hang, planes, with_flat, tilt, cen, crown):
        az = r.uniform(0, TAU)
        upright = planes - 1 if with_flat else planes
        if with_flat:
            q = Quaternion(Vector((math.cos(az + 1.3), math.sin(az + 1.3), 0)), r.uniform(-0.45, 0.45) * tilt)
            self._card(c, q @ UP, Vector((math.cos(az), math.sin(az), 0)), size * flat, size * flat, mat, r.uniform(0, TAU), cen, crown, r.random() < 0.5)
        for i in range(upright):  # upright cards spread evenly around the clump's axis
            a = az + i * math.pi / upright + r.uniform(-0.15, 0.15) * tilt
            n = Quaternion(UP, a) @ (Quaternion(Vector((0, 1, 0)), r.uniform(-0.3, 0.3) * tilt) @ Vector((1, 0, 0)))
            turn = r.uniform(-0.25, 0.25) if hang else r.uniform(0, TAU)
            self._card(c, n, UP, size, size * squash, mat, turn, cen, crown, r.random() < 0.5)

    def _card(self, c, n, hint, w, h, mat, turn, cen, crown, mirror):
        n = n.normalized()
        up = hint - n * hint.dot(n)
        up = up.normalized() if up.length > 1e-4 else n.orthogonal().normalized()
        up = (Quaternion(n, turn) @ up).normalized()
        right = up.cross(n).normalized()
        corners = [c - right * w / 2 - up * h / 2, c + right * w / 2 - up * h / 2, c + right * w / 2 + up * h / 2, c - right * w / 2 + up * h / 2]
        uv = [(0, 0), (1, 0), (1, 1), (0, 1)]
        if mirror:
            uv = [(1 - u, v) for u, v in uv]
        nrm = []
        for p in corners:
            if crown == "axis":  # tall, narrow crowns: out from the trunk, a little upward
                out = Vector((p.x - cen.x, p.y - cen.y, 0))
                out = (out.normalized() if out.length > 1e-4 else UP) + Vector((0, 0, 0.5))
            else:
                out = p - cen
            nrm.append((out.normalized() * 0.65 + (p - c).normalized() * 0.35).normalized())
        self.face([self.vert(p) for p in corners], mat, uv=uv, nrm=nrm)

    def to_mesh(self, me, materials):
        """Write the tree into an existing mesh, replacing what was there (objects sharing the mesh follow)."""
        me.clear_geometry()
        for a in list(me.color_attributes):
            me.color_attributes.remove(a)
        for uv in list(me.uv_layers):
            me.uv_layers.remove(uv)
        me.materials.clear()
        me.from_pydata([tuple(v) for v in self.v], [], self.f)
        me.update()
        me.polygons.foreach_set("material_index", self.mat)
        me.polygons.foreach_set("use_smooth", [True] * len(self.f))  # the custom normals decide the shading
        col = me.color_attributes.new("Col", "FLOAT_COLOR", "CORNER")
        col.data.foreach_set("color", [x for i, f in enumerate(self.f) for _ in f for x in self.col[i]])
        me.color_attributes.active_color = col
        uv = me.uv_layers.new(name="UVMap")
        uv.data.foreach_set("uv", [x for i, f in enumerate(self.f) for p in (self.uv[i] or [(0.5, 0.5)] * len(f)) for x in p])
        normals = []
        for i, f in enumerate(self.f):
            normals.extend(self.nrm[i] or [newell([self.v[j] for j in f])] * len(f))  # bark: one normal per face
        me.normals_split_custom_set([tuple(n) for n in normals])
        for s in self.slots:
            me.materials.append(materials[s])


def trunk_line(r, height, segs, lean, wobble, base=Vector()):
    az = r.uniform(0, TAU)
    p1, p2 = r.uniform(0, TAU), r.uniform(0, TAU)
    pts = []
    for i in range(segs + 1):
        t = i / segs
        x = math.cos(az) * lean * t * t + wobble * math.sin(t * 4.7 + p1) * t
        y = math.sin(az) * lean * t * t + wobble * math.sin(t * 4.1 + p2) * t
        pts.append(base + Vector((x, y, -0.3 + t * (height + 0.3))))
    return pts


def limb(r, start, d, length, segs, droop=0.0, upturn=0.0, wiggle=0.06):
    d = d.normalized()
    pts = []
    for i in range(segs + 1):
        s = i / segs
        p = start + d * (length * s)
        p.z += -droop * length * s * s + upturn * length * max(0.0, s - 0.55) ** 2 * 2.5
        if 0 < i < segs:
            p += Vector((r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(-1, 1))) * wiggle * length / segs
        pts.append(p)
    return pts


def taper(r0, r1, n):
    return [r0 + (r1 - r0) * i / (n - 1) for i in range(n)]


# ------------------------------------------------------------------ the species
# each builder takes a seed and the settings; height scales the tree and width its branches
def scots_pine(seed, cfg):
    """Tall and bare, grey low on the trunk and orange higher up, with flat clouds of needles in an open crown."""
    T = Tree(seed)
    r = T.r
    H = r.uniform(13.0, 16.0) * cfg["height"]
    W = cfg["width"]
    pts = trunk_line(r, H, 12, r.uniform(0.3, 0.9), 0.25)
    radii = [0.36 * (1 - i / 12) ** 1.1 + 0.06 + (0.1 if i == 0 else 0) for i in range(13)]
    split = r.uniform(0.33, 0.42)

    def bark(i, k):
        t = i / 12
        if t < split - 0.05:
            return pick(r, "#5E5248", "#6B5D50", "#544A40")
        if t < split + 0.05:
            return pick(r, "#8E5A3A", "#7A5440")
        return pick(r, "#B5653A", "#C27A45", "#A85A32")

    T.tube(pts, radii, 7, bark)
    for _ in range(r.randint(3, 6)):  # dead branch stubs down the trunk
        p = along(pts, r.uniform(0.25, 0.6))
        b = limb(r, p, direction(r.uniform(0, TAU), r.uniform(-0.2, 0.3)), r.uniform(0.4, 1.0), 2)
        T.tube(b, [0.045, 0.02, 0.004], 4, lambda i, k: pick(r, "#7A7166", "#8A8276"))
    nb = r.randint(10, 13)
    az0 = r.uniform(0, TAU)
    for j in range(nb):
        t = 0.55 + 0.4 * j / (nb - 1) + r.uniform(-0.02, 0.02)
        p = along(pts, t)
        az = az0 + j * 2.39996 + r.uniform(-0.3, 0.3)
        L = r.uniform(2.8, 4.4) * (1.25 - (t - 0.55) * 1.6) * W
        b = limb(r, p, direction(az, r.uniform(0.0, 0.25) + (t - 0.55) * 0.9), L, 4, droop=0.12, upturn=0.3)
        T.tube(b, taper(0.08, 0.015, 5), 5, lambda i, k: pick(r, "#A85A32", "#8E5A3A"))
        T.clump(b[-1] + Vector((0, 0, 0.25)), r.uniform(2.3, 3.0), squash=0.45, flat=1.25)
        if r.random() < 0.4:
            T.clump(along(b, 0.6) + Vector((0, 0, 0.3)), r.uniform(1.8, 2.3), squash=0.45, flat=1.2)
        for side in (-1, 1):
            if r.random() < 0.75:
                s = limb(r, along(b, r.uniform(0.4, 0.6)), direction(az + side * r.uniform(0.6, 1.0), 0.2), L * r.uniform(0.4, 0.6), 3, droop=0.1)
                T.tube(s, taper(0.04, 0.01, 4), 4, lambda i, k: pick(r, "#A85A32", "#8E5A3A"))
                T.clump(s[-1] + Vector((0, 0, 0.2)), r.uniform(1.9, 2.5), squash=0.45, flat=1.2)
    top = pts[-1]
    for k in range(3):
        a = az0 + k * TAU / 3
        T.clump(top + Vector((math.cos(a) * 0.8 * W, math.sin(a) * 0.8 * W, 0.1 + k * 0.2)), r.uniform(1.9, 2.5), squash=0.45, flat=1.2)
    return T, "sphere"


def silver_birch(seed, cfg):
    """Slender and white with black marks, dark at the foot; ascending branches whose twigs weep."""
    T = Tree(seed)
    r = T.r
    H = r.uniform(11.0, 14.0) * cfg["height"]
    pts = trunk_line(r, H, 12, r.uniform(0.2, 0.6), 0.2)
    radii = [0.2 * (1 - i / 12) ** 1.2 + 0.03 + (0.06 if i == 0 else 0) for i in range(13)]

    def bark(i, k):
        t = i / 12
        if t < 0.1 and r.random() < 0.75:
            return pick(r, "#3A3632", "#4A4540", "#2E2A27")
        if r.random() < 0.17:
            return pick(r, "#2A2826", "#3A3632")
        return pick(r, "#E6E2D8", "#DCD8CC", "#EFEBE2")

    T.tube(pts, radii, 6, bark)
    nb = r.randint(15, 20)
    az0 = r.uniform(0, TAU)
    for j in range(nb):
        t = 0.3 + 0.65 * j / (nb - 1)
        p = along(pts, t)
        az = az0 + j * 2.39996 + r.uniform(-0.3, 0.3)
        L = r.uniform(2.4, 3.8) * (1 - abs(t - 0.55) * 1.1) * cfg["width"]
        b = limb(r, p, direction(az, r.uniform(0.6, 0.95)), L, 5, droop=0.5)
        T.tube(b, taper(0.05, 0.008, 6), 4, lambda i, k: pick(r, "#3A3430", "#4A423A"))
        for f in (0.3, 0.5, 0.7, 0.95):  # weeping twigs: clumps hang below the branch
            q = along(b, f)
            if f < 0.9:
                tw = limb(r, q, direction(az + r.uniform(-0.6, 0.6), -1.1), r.uniform(0.8, 1.6), 2)
                T.tube(tw, [0.012, 0.006, 0.0], 3, lambda i, k: pick(r, "#3A3430"))
                q = along(tw, 0.7)
            T.clump(q - Vector((0, 0, 0.2)), r.uniform(0.95, 1.35), squash=1.3, flat=0.8, hang=True)
    for k in range(2):
        T.clump(pts[-1] + Vector((r.uniform(-0.3, 0.3), r.uniform(-0.3, 0.3), -0.3 * k)), 1.0, squash=1.3, flat=0.8, hang=True)
    return T, "sphere"


def norway_spruce(seed, cfg):
    """Straight and dark, with whorls of drooping, upturned branches all the way down: a dense cone."""
    T = Tree(seed)
    r = T.r
    H = r.uniform(14.0, 17.0) * cfg["height"]
    pts = trunk_line(r, H, 14, r.uniform(0.05, 0.2), 0.05)
    radii = [0.32 * (1 - i / 14) ** 1.05 + (0.08 if i == 0 else 0) for i in range(15)]
    T.tube(pts, radii, 7, lambda i, k: pick(r, "#4A3F36", "#55493E", "#3F362F"))
    z = 0.08 * H
    gap = r.uniform(0.5, 0.62)
    lmax = r.uniform(3.2, 3.8) * cfg["width"]
    while z < H - 0.7:
        t = z / H
        p = along(pts, (z + 0.3) / (H + 0.3))
        nbr = r.randint(4, 6)
        az0 = r.uniform(0, TAU)
        L = lmax * (1 - t) ** 0.95 + 0.3
        for j in range(nbr):
            az = az0 + j * TAU / nbr + r.uniform(-0.25, 0.25)
            b = limb(r, p, direction(az, -0.12 - 0.25 * (1 - t) + r.uniform(-0.08, 0.08)), L * r.uniform(0.85, 1.1), 4, droop=0.12, upturn=0.35)
            T.tube(b, taper(0.05 * (1 - t) + 0.015, 0.006, 5), 4, lambda i, k: pick(r, "#4A3F36", "#3F362F"))
            n = max(2, int(L / 0.55))
            for s in range(n):
                f = 1.0 - s * 0.8 / n
                T.clump(along(b, f), (0.95 + 0.6 * min(L, 3.5) / 3.5) * r.uniform(0.9, 1.1), squash=0.75, flat=1.1)
            if j % 2 == 0:
                T.clump(along(b, 0.15), 1.0, squash=0.8)
        z += gap * (1 - 0.35 * t)
    top = pts[-1]
    T.clump(top - Vector((0, 0, 0.35)), 0.9, squash=1.2)
    T.clump(top - Vector((0, 0, 0.9)), 1.1, squash=1.0)
    for _ in range(r.randint(6, 10)):  # cones hanging near the top
        p = along(pts, r.uniform(0.8, 0.95)) + direction(r.uniform(0, TAU), 0) * r.uniform(0.3, 0.9)
        T.tube([p, p - Vector((0, 0, 0.08)), p - Vector((0, 0, 0.2)), p - Vector((0, 0, 0.26))], [0.025, 0.045, 0.035, 0.0], 5,
               lambda i, k: pick(r, "#7A4E2E", "#6A4428", "#8A5A34"))
    return T, "axis"


def aspen(seed, cfg):
    """Straight and slender with smooth, pale grey-green bark; a narrow, light crown of round leaves."""
    T = Tree(seed)
    r = T.r
    H = r.uniform(12.0, 15.0) * cfg["height"]
    pts = trunk_line(r, H, 12, r.uniform(0.15, 0.4), 0.08)
    radii = [0.22 * (1 - i / 12) ** 1.15 + 0.04 + (0.06 if i == 0 else 0) for i in range(13)]

    def bark(i, k):
        t = i / 12
        if t < 0.1 and r.random() < 0.7:
            return pick(r, "#6E6A60", "#5E5A52")
        if t > 0.15 and r.random() < 0.06:
            return pick(r, "#4A4A42", "#3E3E38")
        return pick(r, "#B9BCA8", "#A9AE98", "#C3C5B4")

    T.tube(pts, radii, 6, bark)
    nb = r.randint(13, 16)
    az0 = r.uniform(0, TAU)
    for j in range(nb):
        t = 0.42 + 0.53 * j / (nb - 1)
        p = along(pts, t)
        az = az0 + j * 2.39996 + r.uniform(-0.3, 0.3)
        L = r.uniform(2.4, 3.6) * (1.15 - (t - 0.42)) * cfg["width"]
        b = limb(r, p, direction(az, r.uniform(0.65, 0.95)), L, 4, droop=0.1)
        T.tube(b, taper(0.05, 0.01, 5), 4, lambda i, k: pick(r, "#8A8C7A", "#7A7C6A"))
        for f in (0.35, 0.55, 0.75, 1.0):
            T.clump(along(b, f) + Vector((0, 0, 0.1)), r.uniform(1.25, 1.7), squash=0.95)
        if r.random() < 0.6:
            s = limb(r, along(b, 0.45), direction(az + r.choice((-1, 1)) * 0.8, 0.6), L * 0.5, 3)
            T.tube(s, taper(0.025, 0.006, 4), 3, lambda i, k: pick(r, "#8A8C7A"))
            T.clump(s[-1], r.uniform(1.0, 1.3), squash=0.95)
    T.clump(pts[-1] + Vector((0, 0, 0.2)), 1.3)
    T.clump(pts[-1] - Vector((0, 0, 0.6)), 1.4)
    return T, "sphere"


def rowan(seed, cfg):
    """A small tree with mottled grey bark, a rounded crown of feathery leaves and clusters of red berries."""
    T = Tree(seed)
    r = T.r
    H = r.uniform(6.5, 8.5) * cfg["height"]
    berries = cfg["berries"]
    pts = trunk_line(r, H, 10, r.uniform(0.3, 0.7), 0.15)
    radii = [0.14 * (1 - i / 10) ** 1.1 + 0.03 + (0.05 if i == 0 else 0) for i in range(11)]
    T.tube(pts, radii, 6, lambda i, k: pick(r, "#7A7568", "#8C8778", "#6A665B", "#7A806A"))
    nb = r.randint(9, 12)
    az0 = r.uniform(0, TAU)
    for j in range(nb):
        t = 0.3 + 0.62 * j / (nb - 1)
        p = along(pts, t)
        az = az0 + j * 2.39996 + r.uniform(-0.3, 0.3)
        L = r.uniform(1.9, 3.0) * (1.1 - abs(t - 0.55) * 0.8) * cfg["width"]
        b = limb(r, p, direction(az, r.uniform(0.45, 0.9)), L, 4, droop=0.12)
        T.tube(b, taper(0.04, 0.008, 5), 4, lambda i, k: pick(r, "#6A665B", "#7A7568"))
        for f in (0.35, 0.6, 0.8, 1.0):
            T.clump(along(b, f) + Vector((0, 0, 0.1)), r.uniform(1.15, 1.55), "berries" if r.random() < berries else "leaves")
        if r.random() < 0.6:
            s = limb(r, along(b, 0.5), direction(az + r.choice((-1, 1)) * 0.8, 0.5), L * 0.5, 3)
            T.tube(s, taper(0.02, 0.005, 4), 3, lambda i, k: pick(r, "#6A665B"))
            T.clump(s[-1], r.uniform(0.9, 1.2), "berries" if r.random() < berries else "leaves")
    T.clump(pts[-1] + Vector((0, 0, 0.2)), 1.2)
    return T, "sphere"


def alder(seed, cfg):
    """Often several dark, fissured stems from one foot; an oval crown of dark, rounded leaves."""
    T = Tree(seed)
    r = T.r
    H = r.uniform(10.0, 13.0) * cfg["height"]
    stems = r.randint(2, 3)
    az0 = r.uniform(0, TAU)
    for s in range(stems):
        a = az0 + s * TAU / stems + r.uniform(-0.3, 0.3)
        base = Vector((math.cos(a), math.sin(a), 0)) * r.uniform(0.12, 0.25)
        h = H * r.uniform(0.85, 1.0)
        pts = [p + Vector((math.cos(a), math.sin(a), 0)) * (r.uniform(0.5, 1.1) * max(0.0, (p.z + 0.3) / (h + 0.3)) ** 1.5)
               for p in trunk_line(r, h, 10, 0.2, 0.12, base)]
        radii = [0.17 * (1 - i / 10) ** 1.1 + 0.035 + (0.04 if i == 0 else 0) for i in range(11)]

        def bark(i, k):
            return pick(r, "#2F2A26", "#26221F") if r.random() < 0.25 else pick(r, "#3E3832", "#4A433B", "#453E37")

        T.tube(pts, radii, 6, bark)
        nb = r.randint(8, 11)
        for j in range(nb):
            t = 0.36 + 0.59 * j / (nb - 1)
            p = along(pts, t)
            baz = a + r.uniform(-1.6, 1.6)
            L = r.uniform(1.9, 3.1) * (1.15 - (t - 0.36) * 0.9) * cfg["width"]
            b = limb(r, p, direction(baz, r.uniform(0.4, 0.8)), L, 4, droop=0.1)
            T.tube(b, taper(0.04, 0.008, 5), 4, lambda i, k: pick(r, "#3E3832", "#4A433B"))
            for f in (0.35, 0.55, 0.75, 1.0):
                T.clump(along(b, f) + Vector((0, 0, 0.1)), r.uniform(1.35, 1.9), squash=0.9)
        T.clump(pts[-1] + Vector((0, 0, 0.2)), 1.4)
    return T, "sphere"


def juniper(seed, cfg):
    """A small, narrow column of prickly grey-green with blue berries, on a few reddish stems."""
    T = Tree(seed)
    r = T.r
    H = r.uniform(3.0, 4.5) * cfg["height"]
    R0 = r.uniform(0.85, 1.1) * cfg["width"]
    for s in range(r.randint(3, 4)):
        a = r.uniform(0, TAU)
        h = H * (1.0 if s == 0 else r.uniform(0.55, 0.85))
        base = Vector((math.cos(a), math.sin(a), 0)) * (0.0 if s == 0 else r.uniform(0.08, 0.2))
        pts = trunk_line(r, h, 8, 0.15 if s == 0 else 0.35, 0.06, base)
        T.tube(pts, [(0.09 if s == 0 else 0.06) * (1 - i / 8) + 0.012 for i in range(9)], 5, lambda i, k: pick(r, "#6A4A3A", "#7A5644", "#5A3E30"))
        for j in range(r.randint(13, 16)):
            t = 0.08 + 0.87 * j / 15
            p = along(pts, t)
            b = limb(r, p, direction(r.uniform(0, TAU), r.uniform(1.0, 1.3)), r.uniform(0.3, 0.7) * (1 - t * 0.6) * cfg["width"], 2)
            T.tube(b, [0.02, 0.01, 0.0], 3, lambda i, k: pick(r, "#6A4A3A"))
            for q in (along(b, 0.5), b[-1]):
                rad = R0 * (1 - q.z / H) ** 0.7 + 0.15
                horiz = Vector((q.x, q.y, 0))
                if horiz.length > rad:  # keep the crown a narrow column
                    q = Vector((q.x * rad / horiz.length, q.y * rad / horiz.length, q.z))
                T.clump(q, r.uniform(0.55, 0.85), squash=1.3, flat=0.8)
    return T, "axis"


SPECIES = [  # key, builder, English name, Swedish name, Latin name, width in the lineup (m), leaf-card name
    ("ScotsPine", scots_pine, "Scots pine", "Tall", "Pinus sylvestris", 10, "pine"),
    ("SilverBirch", silver_birch, "Silver birch", "Björk", "Betula pendula", 9, "birch"),
    ("NorwaySpruce", norway_spruce, "Norway spruce", "Gran", "Picea abies", 9, "spruce"),
    ("Aspen", aspen, "Aspen", "Asp", "Populus tremula", 8, "aspen"),
    ("Rowan", rowan, "Rowan", "Rönn", "Sorbus aucuparia", 7, "rowan"),
    ("Alder", alder, "Alder", "Klibbal", "Alnus glutinosa", 9, "alder"),
    ("Juniper", juniper, "Juniper", "En", "Juniperus communis", 5, "juniper"),
]
BY_KEY = {s[0]: s for s in SPECIES}


def load_settings():
    """The saved settings (tree_settings.json) over the defaults, per species."""
    saved = {}
    if os.path.exists(SETTINGS):
        with open(SETTINGS) as fh:
            saved = json.load(fh)
    return {k: dict(DEFAULTS[k], **{n: v for n, v in saved.get(k, {}).items() if n in BASE}) for k in DEFAULTS}


def card_names():
    path = os.path.join(TEXTURES, "cards.json")
    return json.load(open(path)) if os.path.exists(path) else {}


# ------------------------------------------------------------------ materials
def bark_material():
    m = bpy.data.materials.get("Bark")
    if m:
        return m
    m = bpy.data.materials.new("Bark")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    a = nt.nodes.new("ShaderNodeAttribute")
    a.attribute_name = "Col"
    nt.links.new(a.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.9
    return m


def card_image(card, n, berries=False):
    name = f"{card}_{n}" + ("_berries" if berries else "")
    path = os.path.join(TEXTURES, name + ".png")
    img = bpy.data.images.get(name + ".png")
    if img is None:
        img = bpy.data.images.load(path, check_existing=True)
    return img


def leaf_material(name):
    """A leaf-card material: the card's colour through a hue/saturation/value node (the editor's tint sliders), cut
    out at alpha 0.5 like alpha clip in a game engine, drawn on both sides."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.name = "Card"
    tint = nt.nodes.new("ShaderNodeHueSaturation")
    tint.name = "Tint"
    cut = nt.nodes.new("ShaderNodeMath")
    cut.operation = "GREATER_THAN"
    cut.inputs[1].default_value = 0.5
    nt.links.new(tex.outputs["Color"], tint.inputs["Color"])
    nt.links.new(tint.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tex.outputs["Alpha"], cut.inputs[0])
    nt.links.new(cut.outputs[0], bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = 0.75
    try:
        bsdf.inputs["Specular IOR Level"].default_value = 0.25
    except KeyError:
        pass
    m.surface_render_method = "DITHERED"
    m.use_backface_culling = False
    m.use_transparent_shadow = True
    return m


def materials_for(key, cfg):
    """The species' materials, with its chosen card and tint applied."""
    card = BY_KEY[key][6]
    mats = {"bark": bark_material(), "leaves": leaf_material(f"Leaves {key}")}
    if key == "Rowan":
        mats["berries"] = leaf_material(f"Berries {key}")
    for slot, m in mats.items():
        if slot == "bark":
            continue
        nodes = m.node_tree.nodes
        nodes["Card"].image = card_image(card, int(cfg["card"]), berries=(slot == "berries"))
        nodes["Tint"].inputs["Hue"].default_value = cfg["hue"]
        nodes["Tint"].inputs["Saturation"].default_value = cfg["saturation"]
        nodes["Tint"].inputs["Value"].default_value = cfg["brightness"]
    return mats


def seed_for(key, variant, cfg):
    i = [s[0] for s in SPECIES].index(key)
    return 1000 + 97 * i + 13 * "AB".index(variant) + 7919 * int(cfg["seed"])


def build_into(key, variant, cfg, me):
    """(Re)build one tree into the mesh me. Returns (leaf cards, faces)."""
    builder = BY_KEY[key][1]
    tree, crown = builder(seed_for(key, variant, cfg), cfg)
    tree.emit_leaves(crown, cfg)
    tree.to_mesh(me, materials_for(key, cfg))
    return sum(1 for m in tree.mat if m > 0), len(tree.f)
