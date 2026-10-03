"""Tree portfolio: low-poly trees of the Swedish forest, after ref_imgs/Trees of the Swedish Forest.png.

    python3 make_leaf_cards.py                                  leaf textures (once, or after changing them)
    blender -b --factory-startup -P make_trees.py               builds tree_portfolio.blend and renders previews/
    blender -b --factory-startup -P make_trees.py -- --no-render   only the .blend

Each tree is one mesh with a bark material and one or two leaf-card materials, standing on its own origin:
  - Trunk and branches are low-poly tubes, flat shaded, coloured per face (a "Col" colour attribute).
  - Leaf clumps are crossed planes: three copies of the species' leaf card crossing at the clump's centre, one lying
    nearly flat (for the view from above) and two upright. The cards' normals point out from the crown, so the crown
    shades as one rounded volume instead of as separate flat cards.
The .blend has two variants of every species in a row each, with labels and a person for scale, plus a small mixed
grove seen from the game camera. The grove uses linked copies, so editing a tree updates it there too.
"""
import json
import math
import os
import random
import subprocess
import sys

import bpy
from mathutils import Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
TEXTURES = os.path.join(HERE, "textures")
PREVIEWS = os.path.join(HERE, "previews")
BLEND = os.path.join(HERE, "tree_portfolio.blend")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TAU = math.tau
UP = Vector((0, 0, 1))


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

    def clump(self, c, size, card, squash=1.0, flat=1.0, hang=False):
        """Queue a leaf clump: three crossed copies of a card. squash scales the upright cards' height and flat the
        lying card; hang keeps the texture's top up on the upright cards (for twigs that hang, like birch)."""
        self.clumps.append((Vector(c), size, self.slot(card), squash, flat, hang))

    def finish(self, name, crown="sphere"):
        """Emit the leaf cards, with normals pointing out from the crown, and build the Blender object."""
        if self.clumps:
            cen = sum((c[0] for c in self.clumps), Vector()) / len(self.clumps)
            for c, size, mat, squash, flat, hang in self.clumps:
                r = self.r
                az = r.uniform(0, TAU)
                tilt = Quaternion(Vector((math.cos(az + 1.3), math.sin(az + 1.3), 0)), r.uniform(-0.45, 0.45))
                cards = [(tilt @ UP, size * flat, size * flat, False)]
                for a in (az, az + math.pi / 2):
                    n = Quaternion(UP, a) @ (Quaternion(Vector((0, 1, 0)), r.uniform(-0.3, 0.3)) @ Vector((1, 0, 0)))
                    cards.append((n, size, size * squash, True))
                for n, w, h, upright in cards:
                    hint = UP if upright else Vector((math.cos(az), math.sin(az), 0))
                    turn = r.uniform(-0.25, 0.25) if (upright and hang) else r.uniform(0, TAU)
                    self._card(c, n, hint, w, h, mat, turn, cen, crown, r.random() < 0.5)
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(v) for v in self.v], [], self.f)
        me.update()
        me.polygons.foreach_set("material_index", self.mat)
        me.polygons.foreach_set("use_smooth", [True] * len(self.f))  # the custom normals below decide the shading
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
            me.materials.append(MATS[s])
        return bpy.data.objects.new(name, me)

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
def scots_pine(seed):
    """Tall and bare, grey low on the trunk and orange higher up, with flat clouds of needles in an open crown."""
    T = Tree(seed)
    r = T.r
    H = r.uniform(13.0, 16.0)
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
        L = r.uniform(2.8, 4.4) * (1.25 - (t - 0.55) * 1.6)
        b = limb(r, p, direction(az, r.uniform(0.0, 0.25) + (t - 0.55) * 0.9), L, 4, droop=0.12, upturn=0.3)
        T.tube(b, taper(0.08, 0.015, 5), 5, lambda i, k: pick(r, "#A85A32", "#8E5A3A"))
        T.clump(b[-1] + Vector((0, 0, 0.25)), r.uniform(2.3, 3.0), "pine", squash=0.45, flat=1.25)
        if r.random() < 0.4:
            T.clump(along(b, 0.6) + Vector((0, 0, 0.3)), r.uniform(1.8, 2.3), "pine", squash=0.45, flat=1.2)
        for side in (-1, 1):
            if r.random() < 0.75:
                s = limb(r, along(b, r.uniform(0.4, 0.6)), direction(az + side * r.uniform(0.6, 1.0), 0.2), L * r.uniform(0.4, 0.6), 3, droop=0.1)
                T.tube(s, taper(0.04, 0.01, 4), 4, lambda i, k: pick(r, "#A85A32", "#8E5A3A"))
                T.clump(s[-1] + Vector((0, 0, 0.2)), r.uniform(1.9, 2.5), "pine", squash=0.45, flat=1.2)
    top = pts[-1]
    for k in range(3):
        a = az0 + k * TAU / 3
        T.clump(top + Vector((math.cos(a) * 0.8, math.sin(a) * 0.8, 0.1 + k * 0.2)), r.uniform(1.9, 2.5), "pine", squash=0.45, flat=1.2)
    return T, "sphere"


def silver_birch(seed):
    """Slender and white with black marks, dark at the foot; ascending branches whose twigs weep."""
    T = Tree(seed)
    r = T.r
    H = r.uniform(11.0, 14.0)
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
        L = r.uniform(2.4, 3.8) * (1 - abs(t - 0.55) * 1.1)
        b = limb(r, p, direction(az, r.uniform(0.6, 0.95)), L, 5, droop=0.5)
        T.tube(b, taper(0.05, 0.008, 6), 4, lambda i, k: pick(r, "#3A3430", "#4A423A"))
        for f in (0.3, 0.5, 0.7, 0.95):  # weeping twigs: clumps hang below the branch
            q = along(b, f)
            if f < 0.9:
                tw = limb(r, q, direction(az + r.uniform(-0.6, 0.6), -1.1), r.uniform(0.8, 1.6), 2)
                T.tube(tw, [0.012, 0.006, 0.0], 3, lambda i, k: pick(r, "#3A3430"))
                q = along(tw, 0.7)
            T.clump(q - Vector((0, 0, 0.2)), r.uniform(0.95, 1.35), "birch", squash=1.3, flat=0.8, hang=True)
    for k in range(2):
        T.clump(pts[-1] + Vector((r.uniform(-0.3, 0.3), r.uniform(-0.3, 0.3), -0.3 * k)), 1.0, "birch", squash=1.3, flat=0.8, hang=True)
    return T, "sphere"


def norway_spruce(seed):
    """Straight and dark, with whorls of drooping, upturned branches all the way down: a dense cone."""
    T = Tree(seed)
    r = T.r
    H = r.uniform(14.0, 17.0)
    pts = trunk_line(r, H, 14, r.uniform(0.05, 0.2), 0.05)
    radii = [0.32 * (1 - i / 14) ** 1.05 + (0.08 if i == 0 else 0) for i in range(15)]
    T.tube(pts, radii, 7, lambda i, k: pick(r, "#4A3F36", "#55493E", "#3F362F"))
    z = 0.08 * H
    gap = r.uniform(0.5, 0.62)
    lmax = r.uniform(3.2, 3.8)
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
                T.clump(along(b, f), (0.95 + 0.6 * min(L, 3.5) / 3.5) * r.uniform(0.9, 1.1), "spruce", squash=0.75, flat=1.1)
            if j % 2 == 0:
                T.clump(along(b, 0.15), 1.0, "spruce", squash=0.8)
        z += gap * (1 - 0.35 * t)
    top = pts[-1]
    T.clump(top - Vector((0, 0, 0.35)), 0.9, "spruce", squash=1.2)
    T.clump(top - Vector((0, 0, 0.9)), 1.1, "spruce", squash=1.0)
    for _ in range(r.randint(6, 10)):  # cones hanging near the top
        p = along(pts, r.uniform(0.8, 0.95)) + direction(r.uniform(0, TAU), 0) * r.uniform(0.3, 0.9)
        T.tube([p, p - Vector((0, 0, 0.08)), p - Vector((0, 0, 0.2)), p - Vector((0, 0, 0.26))], [0.025, 0.045, 0.035, 0.0], 5,
               lambda i, k: pick(r, "#7A4E2E", "#6A4428", "#8A5A34"))
    return T, "axis"


def aspen(seed):
    """Straight and slender with smooth, pale grey-green bark; a narrow, light crown of round leaves."""
    T = Tree(seed)
    r = T.r
    H = r.uniform(12.0, 15.0)
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
        L = r.uniform(2.4, 3.6) * (1.15 - (t - 0.42))
        b = limb(r, p, direction(az, r.uniform(0.65, 0.95)), L, 4, droop=0.1)
        T.tube(b, taper(0.05, 0.01, 5), 4, lambda i, k: pick(r, "#8A8C7A", "#7A7C6A"))
        for f in (0.35, 0.55, 0.75, 1.0):
            T.clump(along(b, f) + Vector((0, 0, 0.1)), r.uniform(1.25, 1.7), "aspen", squash=0.95)
        if r.random() < 0.6:
            s = limb(r, along(b, 0.45), direction(az + r.choice((-1, 1)) * 0.8, 0.6), L * 0.5, 3)
            T.tube(s, taper(0.025, 0.006, 4), 3, lambda i, k: pick(r, "#8A8C7A"))
            T.clump(s[-1], r.uniform(1.0, 1.3), "aspen", squash=0.95)
    T.clump(pts[-1] + Vector((0, 0, 0.2)), 1.3, "aspen")
    T.clump(pts[-1] - Vector((0, 0, 0.6)), 1.4, "aspen")
    return T, "sphere"


def rowan(seed):
    """A small tree with mottled grey bark, a rounded crown of feathery leaves and clusters of red berries."""
    T = Tree(seed)
    r = T.r
    H = r.uniform(6.5, 8.5)
    pts = trunk_line(r, H, 10, r.uniform(0.3, 0.7), 0.15)
    radii = [0.14 * (1 - i / 10) ** 1.1 + 0.03 + (0.05 if i == 0 else 0) for i in range(11)]
    T.tube(pts, radii, 6, lambda i, k: pick(r, "#7A7568", "#8C8778", "#6A665B", "#7A806A"))
    nb = r.randint(9, 12)
    az0 = r.uniform(0, TAU)
    for j in range(nb):
        t = 0.3 + 0.62 * j / (nb - 1)
        p = along(pts, t)
        az = az0 + j * 2.39996 + r.uniform(-0.3, 0.3)
        L = r.uniform(1.9, 3.0) * (1.1 - abs(t - 0.55) * 0.8)
        b = limb(r, p, direction(az, r.uniform(0.45, 0.9)), L, 4, droop=0.12)
        T.tube(b, taper(0.04, 0.008, 5), 4, lambda i, k: pick(r, "#6A665B", "#7A7568"))
        for f in (0.35, 0.6, 0.8, 1.0):
            T.clump(along(b, f) + Vector((0, 0, 0.1)), r.uniform(1.15, 1.55), "rowan_berries" if r.random() < 0.3 else "rowan")
        if r.random() < 0.6:
            s = limb(r, along(b, 0.5), direction(az + r.choice((-1, 1)) * 0.8, 0.5), L * 0.5, 3)
            T.tube(s, taper(0.02, 0.005, 4), 3, lambda i, k: pick(r, "#6A665B"))
            T.clump(s[-1], r.uniform(0.9, 1.2), "rowan_berries" if r.random() < 0.3 else "rowan")
    T.clump(pts[-1] + Vector((0, 0, 0.2)), 1.2, "rowan")
    return T, "sphere"


def alder(seed):
    """Often several dark, fissured stems from one foot; an oval crown of dark, rounded leaves."""
    T = Tree(seed)
    r = T.r
    H = r.uniform(10.0, 13.0)
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
            L = r.uniform(1.9, 3.1) * (1.15 - (t - 0.36) * 0.9)
            b = limb(r, p, direction(baz, r.uniform(0.4, 0.8)), L, 4, droop=0.1)
            T.tube(b, taper(0.04, 0.008, 5), 4, lambda i, k: pick(r, "#3E3832", "#4A433B"))
            for f in (0.35, 0.55, 0.75, 1.0):
                T.clump(along(b, f) + Vector((0, 0, 0.1)), r.uniform(1.35, 1.9), "alder", squash=0.9)
        T.clump(pts[-1] + Vector((0, 0, 0.2)), 1.4, "alder")
    return T, "sphere"


def juniper(seed):
    """A small, narrow column of prickly grey-green with blue berries, on a few reddish stems."""
    T = Tree(seed)
    r = T.r
    H = r.uniform(3.0, 4.5)
    R0 = r.uniform(0.85, 1.1)
    for s in range(r.randint(3, 4)):
        a = r.uniform(0, TAU)
        h = H * (1.0 if s == 0 else r.uniform(0.55, 0.85))
        base = Vector((math.cos(a), math.sin(a), 0)) * (0.0 if s == 0 else r.uniform(0.08, 0.2))
        pts = trunk_line(r, h, 8, 0.15 if s == 0 else 0.35, 0.06, base)
        T.tube(pts, [(0.09 if s == 0 else 0.06) * (1 - i / 8) + 0.012 for i in range(9)], 5, lambda i, k: pick(r, "#6A4A3A", "#7A5644", "#5A3E30"))
        for j in range(r.randint(13, 16)):
            t = 0.08 + 0.87 * j / 15
            p = along(pts, t)
            b = limb(r, p, direction(r.uniform(0, TAU), r.uniform(1.0, 1.3)), r.uniform(0.3, 0.7) * (1 - t * 0.6), 2)
            T.tube(b, [0.02, 0.01, 0.0], 3, lambda i, k: pick(r, "#6A4A3A"))
            for q in (along(b, 0.5), b[-1]):
                rad = R0 * (1 - q.z / H) ** 0.7 + 0.15
                horiz = Vector((q.x, q.y, 0))
                if horiz.length > rad:  # keep the crown a narrow column
                    q = Vector((q.x * rad / horiz.length, q.y * rad / horiz.length, q.z))
                T.clump(q, r.uniform(0.55, 0.85), "juniper", squash=1.3, flat=0.8)
    return T, "axis"


SPECIES = [  # key, builder, English name, Swedish name, Latin name, width in the lineup (m)
    ("ScotsPine", scots_pine, "Scots pine", "Tall", "Pinus sylvestris", 10),
    ("SilverBirch", silver_birch, "Silver birch", "Björk", "Betula pendula", 9),
    ("NorwaySpruce", norway_spruce, "Norway spruce", "Gran", "Picea abies", 9),
    ("Aspen", aspen, "Aspen", "Asp", "Populus tremula", 8),
    ("Rowan", rowan, "Rowan", "Rönn", "Sorbus aucuparia", 7),
    ("Alder", alder, "Alder", "Klibbal", "Alnus glutinosa", 9),
    ("Juniper", juniper, "Juniper", "En", "Juniperus communis", 5),
]


# ------------------------------------------------------------------ materials
def bark_material():
    m = bpy.data.materials.new("Bark")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    a = nt.nodes.new("ShaderNodeAttribute")
    a.attribute_name = "Col"
    nt.links.new(a.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.9
    return m


def leaf_material(name):
    m = bpy.data.materials.new("Leaves_" + name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(os.path.join(TEXTURES, name + ".png"), check_existing=True)
    cut = nt.nodes.new("ShaderNodeMath")  # a hard cut-out, like alpha clip in a game engine
    cut.operation = "GREATER_THAN"
    cut.inputs[1].default_value = 0.5
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
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


def flat_material(name, hexcol, rough=0.9):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = lin(hexcol)
    b.inputs["Roughness"].default_value = rough
    return m


# ------------------------------------------------------------------ the portfolio scene
def collection(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c)
    return c


def text(body, size, loc, coll, mat):
    cu = bpy.data.curves.new("Label", "FONT")
    cu.body = body
    cu.size = size
    cu.align_x = "CENTER"
    cu.materials.append(mat)
    ob = bpy.data.objects.new("Label " + body.split("\n")[0], cu)
    ob.location = loc
    ob.rotation_euler = (math.pi / 2, 0, 0)
    coll.objects.link(ob)
    return ob


def person(loc, coll, mat):
    """A 1.8 m figure for scale."""
    me = bpy.data.meshes.new("Person")
    verts, faces = [], []

    def box(cx, cy, z0, sx, sy, sz):
        o = len(verts)
        for dz in (0, sz):
            for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                verts.append((cx + dx * sx / 2, cy + dy * sy / 2, z0 + dz))
        faces.extend([(o, o + 3, o + 2, o + 1), (o + 4, o + 5, o + 6, o + 7), (o, o + 1, o + 5, o + 4),
                      (o + 1, o + 2, o + 6, o + 5), (o + 2, o + 3, o + 7, o + 6), (o + 3, o, o + 4, o + 7)])

    box(-0.1, 0, 0, 0.16, 0.2, 0.86)
    box(0.1, 0, 0, 0.16, 0.2, 0.86)
    box(0, 0, 0.86, 0.44, 0.24, 0.64)
    box(-0.29, 0, 0.82, 0.12, 0.14, 0.66)
    box(0.29, 0, 0.82, 0.12, 0.14, 0.66)
    box(0, 0, 1.54, 0.22, 0.24, 0.26)
    me.from_pydata(verts, [], faces)
    me.materials.append(mat)
    ob = bpy.data.objects.new("Person for scale", me)
    ob.location = loc
    coll.objects.link(ob)
    return ob


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    global MATS
    MATS = {"bark": bark_material()}
    for name in ("pine", "spruce", "birch", "aspen", "rowan", "rowan_berries", "alder", "juniper"):
        MATS[name] = leaf_material(name)
    label_mat = flat_material("Label", "#2A2824", 0.6)
    person_mat = flat_material("Person", "#5A6070", 0.8)
    ground_mat = flat_material("Ground", "#7D8C52", 1.0)

    trees_coll = collection("Trees")
    stage = collection("Portfolio")
    trees, extras, rows = {}, {}, {}
    row_len = sum(sp[5] for sp in SPECIES) + 3.0 * (len(SPECIES) - 1)
    for row, variant in enumerate("AB"):  # the two rows side by side, so neither stands behind the other
        x0 = row * (row_len + 60.0)
        x = x0
        for i, (key, fn, eng, swe, latin, width) in enumerate(SPECIES):
            sub = bpy.data.collections.get(eng) or collection(eng, trees_coll)
            tree, crown = fn(1000 + 97 * i + 13 * row)
            ob = tree.finish(f"{key}_{variant}", crown)
            x += width / 2
            ob.location = (x, 0, 0)
            sub.objects.link(ob)
            trees[(key, variant)] = ob
            extras[(key, variant)] = [text(eng, 0.9, (x, -6.0, 0.9), stage, label_mat),
                                      text(f"{swe} · {latin}", 0.45, (x, -6.0, 0.25), stage, label_mat),
                                      person((x + (width / 2 + 0.6 if width >= 7 else 2.0), 0, 0), stage, person_mat)]  # beside the tree
            x += width / 2 + 3.0
        rows[variant] = x0 + row_len / 2

    # a small mixed grove, as it might stand in Act 1, off to the side of the rows
    grove = collection("Grove")
    gr = random.Random(7)
    mix = (["ScotsPine"] * 9 + ["NorwaySpruce"] * 7 + ["SilverBirch"] * 4 + ["Aspen"] * 2 + ["Rowan"] * 2 + ["Alder"] * 2 + ["Juniper"] * 4)
    gx0 = -150.0
    placed = []
    for key in mix:
        for _ in range(60):
            p = Vector((gx0 + gr.uniform(-22, 22), gr.uniform(-16, 16), 0))
            if all((p - q).length > (2.5 if key == "Juniper" else 4.2) for q in placed):
                break
        placed.append(p)
        src = trees[(key, gr.choice("AB"))]
        ob = bpy.data.objects.new(src.name + " (grove)", src.data)
        ob.location = p
        ob.rotation_euler = (0, 0, gr.uniform(0, TAU))
        sc = gr.uniform(0.85, 1.1)
        ob.scale = (sc, sc, sc)
        grove.objects.link(ob)

    gme = bpy.data.meshes.new("Ground")
    gme.from_pydata([(-350, -250, 0), (350, -250, 0), (350, 250, 0), (-350, 250, 0)], [], [(0, 1, 2, 3)])
    gme.materials.append(ground_mat)
    ground = bpy.data.objects.new("Ground", gme)
    ground.location = (40, 0, 0)
    stage.objects.link(ground)

    sun_data = bpy.data.lights.new("Sun", "SUN")
    sun_data.energy = 3.6
    sun_data.angle = math.radians(2.5)
    sun = bpy.data.objects.new("Sun", sun_data)
    sun.rotation_euler = (math.radians(48), 0, math.radians(-35))
    stage.objects.link(sun)
    world = bpy.data.worlds.new("Sky")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = lin("#B8C8D6")
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
    scene.world = world

    cams = {}
    for variant, cx in rows.items():  # orthographic and tipped down a little, like a sheet of tree portraits
        cams["Row " + variant] = camera(f"Camera row {variant}", (cx, -60, 21.0), (cx, 0, 8.0), stage, ortho=row_len + 10)
    cams["Grove"] = camera("Camera grove, game view", (gx0 + 6, -30, 32), (gx0, 1, 2), stage, lens=35)
    scene.camera = cams["Row A"]
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 64
    scene.view_settings.view_transform = "AgX"

    # open the file looking at row A, with materials shown
    for scr in bpy.data.screens:
        for area in scr.areas:
            if area.type == "VIEW_3D":
                sp = area.spaces[0]
                sp.shading.type = "MATERIAL"
                sp.clip_end = 2000
                r3d = sp.region_3d
                r3d.view_location = (rows["A"], 0, 7)
                r3d.view_distance = 75
                r3d.view_rotation = Quaternion((0.82, 0.57, 0.0, 0.0)).normalized()
    return scene, cams, trees, extras, stage


def camera(name, loc, target, coll, lens=50, ortho=None):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_end = 2000
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    ob = bpy.data.objects.new(name, cd)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    coll.objects.link(ob)
    return ob


def render(scene, cams, trees, extras, stage):
    os.makedirs(PREVIEWS, exist_ok=True)
    shots = [("Row A", "row_a.png", (2400, 1000)), ("Row B", "row_b.png", (2400, 1000)), ("Grove", "grove_game_view.png", (1600, 900))]
    for key, file, res in shots:
        scene.camera = cams[key]
        scene.render.resolution_x, scene.render.resolution_y = res
        scene.render.filepath = os.path.join(PREVIEWS, file)
        bpy.ops.render.render(write_still=True)
        print("RENDERED", file)
    # one portrait per species, everything else hidden, then a sheet of them
    tiles, info = [], {}
    tw, th = 600, 750
    scene.render.resolution_x, scene.render.resolution_y = tw, th
    keep = set()
    for key, fn, eng, swe, latin, width in SPECIES:
        ob = trees[(key, "A")]
        keep = {ob.name, "Ground", "Sun"} | {e.name for e in extras[(key, "A")] if e.type == "MESH"}
        hidden = [o for o in scene.objects if o.type in ("MESH", "FONT") and o.name not in keep and not o.hide_render]
        for o in hidden:
            o.hide_render = True
        h = ob.dimensions.z
        x, y = ob.location.x, ob.location.y
        cam = camera("Camera " + key, (x, y - (h / 2 + 1.3) / math.tan(math.radians(19.8)), h * 0.55), (x, y, h * 0.47), stage)
        scene.camera = cam
        path = os.path.join(PREVIEWS, "tiles", key + ".png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        tiles.append(path)
        me = ob.data
        info[key] = dict(name=eng, swedish=swe, latin=latin, height=round(h, 1), faces=len(me.polygons),
                         cards=sum(1 for q in me.polygons if q.material_index > 0))
        for o in hidden:
            o.hide_render = False
        bpy.data.objects.remove(cam, do_unlink=True)
    with open(os.path.join(PREVIEWS, "tiles", "info.json"), "w") as fh:
        json.dump(info, fh, indent=1)
    # the sheet with captions is drawn by make_sheet.py, which needs Pillow, so it runs in the system Python
    done = subprocess.run(["python3", os.path.join(HERE, "make_sheet.py")])
    print("RENDERED portfolio.png" if done.returncode == 0 else "make_sheet.py failed; run it with python3")
    scene.camera = cams["Row A"]
    scene.render.resolution_x, scene.render.resolution_y = 2400, 1000


scene, cams, trees, extras, stage = build()
for (key, variant), ob in sorted(trees.items()):
    me = ob.data
    print(f"TREE {ob.name}: {len(me.polygons)} faces, {sum(1 for p in me.polygons if p.material_index > 0)} leaf cards, "
          f"height {ob.dimensions.z:.1f} m")
bpy.ops.wm.save_as_mainfile(filepath=BLEND, relative_remap=True)
print("SAVED", BLEND)
if "--no-render" not in ARGS:
    render(scene, cams, trees, extras, stage)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, relative_remap=True)
