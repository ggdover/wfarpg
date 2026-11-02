"""Our own hero, built by script (Blender): a low-poly man in the Tripo3D model's clothes, after it but made from
scratch, the way a modeller would block out a low-poly character. A ragged linen tunic with short sleeves, belted with
a rope; trousers; wrapped shins; leather boots; chunky hair. With gear, light leather on top: a shoulder guard, a
strap across the chest, bracers and a belt pouch (the user asked for an ARPG's starting hero without much gear or
armour, 1 November).

Every part is a few rings of faces lofted along the skeleton, so the figure stands where the Tripo model's skeleton
stands and can share it, its weights carried over from the Tripo model (lowpoly.transfer_weights); rings at the
shoulders, elbows, hips and knees let it bend there. Each face is one flat colour from PALETTE, a little lighter or
darker at random, as the trees' faces are.
"""
import math
import random

import bpy
from mathutils import Vector

# the Tripo model's colours, as its texture has them (sRGB)
PALETTE = {
    "tunic": "#8D8574", "tunic_dark": "#6F6859", "trousers": "#4A3B2D", "wraps": "#A79C88", "boots": "#3A2B20",
    "rope": "#7A6248", "skin": "#C4977C", "stubble": "#9E7B66", "eyes": "#2B231D", "hair": "#3A2A1F",
    "leather": "#5C4231", "leather_dark": "#3F2D21",
}


def lin(h):
    h = h.lstrip("#")
    return tuple((v / 12.92) if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
                 for v in (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)))


def frame(d, hint=Vector((1.0, 0.0, 0.0))):
    """Two axes across direction d: x as near hint as can be, y = d × x."""
    d = d.normalized()
    x = hint - d * hint.dot(d)
    if x.length < 1e-4:
        x = Vector((0.0, 1.0, 0.0)) - d * d.y
    x.normalize()
    return x, d.cross(x)


class Builder:
    """Faces with one colour each, written into a mesh at the end."""

    def __init__(self, seed=7):
        self.v, self.f, self.c = [], [], []
        self.rng = random.Random(seed)

    def ring(self, c, d, rx, ry, sides, hint=Vector((1.0, 0.0, 0.0)), turn=0.0, drop=None):
        """A ring of sides points round c, across direction d: an ellipse rx across (toward hint) and ry deep.
        drop(k) lowers point k along -d, for ragged hems."""
        x, y = frame(d, hint)
        out = []
        for k in range(sides):
            a = turn + math.tau * k / sides
            p = c + x * (math.cos(a) * rx) + y * (math.sin(a) * ry)
            if drop:
                p = p - d.normalized() * drop(k)
            self.v.append(p)
            out.append(len(self.v) - 1)
        return out

    def face(self, idx, colour):
        self.f.append(list(idx))
        self.c.append(colour)

    def loft(self, rings, colours, cap_start=True, cap_end=True):
        """Quads between each ring and the next (colours: one per band, or one for all), capped at the ends."""
        for i in range(len(rings) - 1):
            a, b = rings[i], rings[i + 1]
            col = colours[i] if isinstance(colours, list) else colours
            for k in range(len(a)):
                k1 = (k + 1) % len(a)
                self.face([a[k], a[k1], b[k1], b[k]], col)
        first = colours[0] if isinstance(colours, list) else colours
        last = colours[-1] if isinstance(colours, list) else colours
        if cap_start:
            self.face(list(reversed(rings[0])), first)
        if cap_end:
            self.face(rings[-1], last)

    def tube(self, pts, radii, sides, colours, hint=Vector((1.0, 0.0, 0.0)), caps=(True, True), turn=0.0):
        """A tube through pts, radii (r or (rx, ry)) at each, its rings across the way it runs there."""
        rings = []
        for i, p in enumerate(pts):
            d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)])
            r = radii[i]
            rx, ry = (r, r) if isinstance(r, (int, float)) else r
            rings.append(self.ring(p, d, rx, ry, sides, hint, turn))
        self.loft(rings, colours, *caps)
        return rings

    def ellipsoid(self, c, r, segments, rings, colour, keep=None, axis=None):
        """An ellipsoid round c with radii r (x, y, z), faceted; keep(face_centre) drops faces it says no to.
        axis: a direction to stand it along instead of up (its z)."""
        z = axis.normalized() if axis else Vector((0.0, 0.0, 1.0))
        x, y = frame(z)
        top = len(self.v)
        self.v.append(c + z * r[2])
        bottom = len(self.v)
        self.v.append(c - z * r[2])
        rows = []
        for j in range(1, rings):
            phi = math.pi * j / rings
            row = []
            for k in range(segments):
                th = math.tau * k / segments
                p = c + x * (math.sin(phi) * math.cos(th) * r[0]) + y * (math.sin(phi) * math.sin(th) * r[1]) \
                    + z * (math.cos(phi) * r[2])
                self.v.append(p)
                row.append(len(self.v) - 1)
            rows.append(row)
        faces = []
        for k in range(segments):
            k1 = (k + 1) % segments
            faces.append([top, rows[0][k], rows[0][k1]])
            for j in range(len(rows) - 1):
                faces.append([rows[j][k], rows[j + 1][k], rows[j + 1][k1], rows[j][k1]])
            faces.append([rows[-1][k], bottom, rows[-1][k1]])
        for f in faces:
            centre = sum((self.v[i] for i in f), Vector()) / len(f)
            if keep is None or keep(centre):
                self.face(f, colour)

    def to_object(self, name, collection, material, jitter=0.07):
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(p) for p in self.v], [], self.f)
        me.update()
        col = me.color_attributes.new("Col", "FLOAT_COLOR", "CORNER")
        data = []
        for f, c in zip(self.f, self.c):
            k = 1.0 + self.rng.uniform(-jitter, jitter)
            rgb = [min(1.0, v * k) for v in lin(PALETTE[c])]
            data.extend((rgb + [1.0]) * len(f))
        col.data.foreach_set("color", data)
        me.color_attributes.active_color = col
        me.polygons.foreach_set("use_smooth", [False] * len(me.polygons))
        me.materials.append(material)
        ob = bpy.data.objects.new(name, me)
        collection.objects.link(ob)
        bpy.context.view_layer.update()
        return ob


def joints(arm):
    """Where the skeleton's joints are, in the world: each bone's head, and the fingers' and toes' tips."""
    j = {b.name: arm.matrix_world @ b.head_local for b in arm.data.bones}
    j.update({b.name + ".tip": arm.matrix_world @ b.tail_local for b in arm.data.bones})
    return j


def build(arm, name, collection, material, gear=False, seed=7):
    """The hero, standing where arm's skeleton stands (the Tripo model's, UE names: pelvis, thigh_l, upperarm_r...)."""
    J = joints(arm)
    b = Builder(seed)
    up = Vector((0.0, 0.0, 1.0))
    mid = J["pelvis"]
    cx, cy = mid.x, J["spine_02"].y

    def at(z, dy=0.0):
        return Vector((cx, cy + dy, z))

    # the tunic over the torso, its hem torn (every other point lower, some more), short ragged sleeves
    rng = random.Random(seed)
    hem = [rng.uniform(0.0, 0.045) * (k % 2) for k in range(12)]
    torso = [
        b.ring(at(0.80), up, 0.205, 0.145, 12, drop=lambda k: hem[k]),
        b.ring(at(0.90), up, 0.195, 0.138, 12),
        b.ring(at(0.99), up, 0.172, 0.118, 12),
        b.ring(at(1.05), up, 0.158, 0.112, 12),
        b.ring(at(1.18, -0.005), up, 0.172, 0.12, 12),
        b.ring(at(1.31, -0.008), up, 0.186, 0.124, 12),
        b.ring(at(1.395, 0.002), up, 0.182, 0.112, 12),
        b.ring(at(1.44, 0.008), up, 0.14, 0.092, 12),  # the shoulders sloping to the neck
        b.ring(at(1.47, 0.01), up, 0.085, 0.07, 12),
    ]
    b.loft(torso, ["tunic_dark", "tunic", "tunic", "tunic", "tunic", "tunic", "tunic", "tunic"], cap_start=True, cap_end=False)
    # the V of the neckline: the skin under it, a wedge on the chest
    i0 = len(b.v)
    b.v.extend([Vector((cx - 0.045, cy - 0.112, 1.455)), Vector((cx + 0.045, cy - 0.112, 1.455)), at(1.355, -0.14)])
    b.face([i0 + 1, i0, i0 + 2], "skin")
    # the neck and the head, the face forward (-y): a jaw with stubble, a nose, eyes and brows, ears
    neck_top = Vector((cx, J["head"].y + 0.005, J["head"].z - 0.02))
    b.tube([Vector((cx, cy + 0.01, 1.43)), neck_top], [0.058, 0.054], 8, "skin", caps=(False, False))
    head_c = Vector((cx, J["head"].y - 0.004, J["head"].z + 0.078))
    b.ellipsoid(head_c, (0.09, 0.104, 0.118), 10, 7, "skin")
    b.ellipsoid(head_c + Vector((0, -0.032, -0.07)), (0.07, 0.07, 0.052), 8, 4, "stubble")
    n = len(b.v)
    b.v.extend([head_c + Vector((0, -0.124, -0.014)), head_c + Vector((-0.018, -0.1, 0.022)),
                head_c + Vector((0.018, -0.1, 0.022)), head_c + Vector((0, -0.1, -0.034))])
    b.face([n + 1, n + 0, n + 2], "skin")
    b.face([n + 0, n + 3, n + 2], "skin")
    b.face([n + 0, n + 1, n + 3], "skin")
    for sx in (-1, 1):
        b.tube([head_c + Vector((sx * 0.034, -0.096, 0.004)), head_c + Vector((sx * 0.034, -0.106, 0.004))],
               [(0.014, 0.007), (0.012, 0.006)], 4, "eyes", hint=Vector((1, 0, 0)))
        b.tube([head_c + Vector((sx * 0.036, -0.094, 0.026)), head_c + Vector((sx * 0.036, -0.108, 0.03))],
               [(0.02, 0.006), (0.018, 0.005)], 4, "hair", hint=Vector((1, 0, 0)))
        b.ellipsoid(head_c + Vector((sx * 0.09, 0.004, -0.006)), (0.012, 0.024, 0.032), 6, 3, "skin")
    # hair: a full head of it, to the brow in front, over the ears' tops and down to the nape behind, and locks lying
    # along it, swept to the side over the brow and down behind
    hair_c = head_c + Vector((0, 0.014, 0.024))
    hr = (0.1, 0.116, 0.118)

    def scalp(p):
        rel = p - hair_c
        front, back = max(0.0, -rel.y / hr[1]), max(0.0, rel.y / hr[1])
        return rel.z > -0.025 + 0.06 * front - 0.065 * back

    b.ellipsoid(hair_c, hr, 10, 7, "hair", keep=scalp)
    rng_h = random.Random(seed + 1)
    # (around the head from the front, toward its left; how high; how long): the fringe, swept sideways, and down the
    # nape behind
    locks = [(-0.6 + 0.35 * i, 0.6, 0.055) for i in range(4)]
    locks += [(math.pi - 0.75 + 0.5 * i, -0.15 + 0.08 * (i % 2), 0.07) for i in range(4)]
    for around, height, length in locks:
        out = Vector((math.sin(around), -math.cos(around), height)).normalized()
        s = hair_c + Vector((out.x * hr[0], out.y * hr[1], out.z * hr[2]))
        side = Vector((0.0, 0.0, 1.0)).cross(out).normalized()
        down = out.cross(side).normalized() * -1.0  # along the head, downward
        sweep = side * (0.4 if abs(height - 0.6) < 0.01 else 0.0)
        e = s + (down + sweep).normalized() * length * rng_h.uniform(0.85, 1.15) + out * 0.012
        b.tube([s, s.lerp(e, 0.5) + out * 0.012, e], [(0.022, 0.009), (0.018, 0.008), (0.005, 0.003)], 4, "hair", hint=side)
    # the rope belt, knotted at the front, its ends hanging
    belt = [b.ring(at(1.005), up, 0.165, 0.118, 12), b.ring(at(1.04), up, 0.165, 0.118, 12)]
    b.loft(belt, "rope", False, False)
    knot = at(1.02, -0.125) + Vector((0.035, 0, 0))
    b.ellipsoid(knot, (0.022, 0.016, 0.02), 6, 3, "rope")
    for dx, dz in ((0.0, 0.16), (0.03, 0.12)):
        b.tube([knot + Vector((dx - 0.01, -0.004, -0.01)), knot + Vector((dx + 0.005, -0.012, -dz))], [0.008, 0.007], 4,
               "rope")
    # legs: trousers to the shins, wrapped below, boots
    for s in ("l", "r"):
        hip, knee, ankle, ball = J[f"thigh_{s}"], J[f"calf_{s}"], J[f"foot_{s}"], J[f"ball_{s}"]
        thigh = [hip + Vector((0, 0, 0.02)), hip.lerp(knee, 0.5), knee + (hip - knee).normalized() * 0.05, knee,
                 knee.lerp(ankle, 0.42)]
        b.tube(thigh, [0.086, 0.076, 0.062, 0.058, 0.062], 8, "trousers", caps=(True, False))
        shin = [knee.lerp(ankle, 0.42), knee.lerp(ankle, 0.6), knee.lerp(ankle, 0.78), knee.lerp(ankle, 0.92)]
        b.tube(shin, [0.068, 0.062, 0.058, 0.054], 8, ["wraps", "wraps", "wraps"], caps=(False, False))
        b.tube([knee.lerp(ankle, 0.5), knee.lerp(ankle, 0.52)], [0.071, 0.071], 8, "wraps", caps=(False, False))
        heel = Vector((ankle.x, ankle.y + 0.05, 0.0))
        toe = Vector((ball.x + (ball.x - ankle.x) * 0.3, ball.y - 0.06, 0.0))
        shaft = [knee.lerp(ankle, 0.88), ankle + Vector((0, 0.005, 0)), Vector((ankle.x, ankle.y + 0.01, 0.05))]
        b.tube(shaft, [0.06, 0.058, 0.06], 8, "boots", caps=(False, True))
        foot = [heel + Vector((0, 0, 0.045)), heel.lerp(toe, 0.45) + Vector((0, 0, 0.05)), toe + Vector((0, 0.02, 0.035)),
                toe + Vector((0, 0, 0.022))]
        b.tube(foot, [(0.048, 0.045), (0.05, 0.05), (0.045, 0.035), (0.03, 0.022)], 6, "boots", hint=up)
    # arms: a short sleeve, skin to the wrist, the hand a mitten with a thumb
    for s in ("l", "r"):
        sh, el, wr = J[f"upperarm_{s}"], J[f"lowerarm_{s}"], J[f"hand_{s}"]
        tip = J[f"middle_03_{s}"] + (J[f"middle_03_{s}"] - J[f"middle_02_{s}"]) * 0.8
        out = Vector((1.0 if s == "l" else -1.0, 0.0, 0.0))
        sleeve_hem = [rng.uniform(0.0, 0.03) * (k % 2) for k in range(8)]
        sleeve = [sh + (sh - el).normalized() * 0.03 + Vector((0, 0, 0.01)), sh.lerp(el, 0.3), sh.lerp(el, 0.62)]
        rings = [b.ring(sleeve[0], el - sh, 0.07, 0.066, 8, out), b.ring(sleeve[1], el - sh, 0.067, 0.063, 8, out),
                 b.ring(sleeve[2], el - sh, 0.063, 0.06, 8, out, drop=lambda k: sleeve_hem[k])]
        b.loft(rings, "tunic", cap_start=True, cap_end=False)
        b.tube([sh.lerp(el, 0.55), el, el.lerp(wr, 0.5), wr], [0.053, 0.047, 0.044, 0.036], 7, "skin", out, caps=(False, False))
        b.tube([wr, wr.lerp(tip, 0.45), tip], [(0.042, 0.023), (0.05, 0.022), (0.04, 0.017)], 6, "skin",
               hint=Vector((0.0, 1.0, 0.0)))  # wide front to back, the palm toward the thigh
        th0, th1 = J[f"thumb_01_{s}"], J[f"thumb_03_{s}"]
        b.tube([th0, th1 + (th1 - th0) * 0.3], [0.018, 0.014], 4, "skin")
    if gear:
        _gear(b, J, at, up)
    return b.to_object(name, collection, material)


def _gear(b, J, at, up):
    """Light leather: a guard on the left shoulder and a strap across the chest holding it, bracers, a belt pouch."""
    sh, el = J["upperarm_l"], J["lowerarm_l"]
    axis = ((sh - el).normalized() + Vector((0.2, 0, 0.9))).normalized()
    c = sh + axis * 0.015 + Vector((0.012, 0, 0))
    b.ellipsoid(c, (0.095, 0.1, 0.07), 7, 4, "leather", axis=axis, keep=lambda p: (p - c).dot(axis) > -0.005)
    b.tube([c - axis * 0.012, c + axis * 0.008], [0.1, 0.104], 7, "leather_dark", hint=Vector((0, 1, 0)), caps=(False, False))
    for side in (-1, 1):  # the strap, over the chest and the back, from the left shoulder to the right hip
        pts = []
        for t in (0.0, 0.33, 0.66, 1.0):
            z = 1.40 - 0.38 * t
            x = J["pelvis"].x + 0.12 - 0.27 * t
            depth = 0.112 + 0.012 * math.sin(math.pi * t)
            pts.append(Vector((x, J["spine_02"].y + side * (depth + 0.006), z)))
        first = len(b.v)
        for p in pts:
            b.v.extend([p + Vector((0.0, 0.0, 0.022)), p - Vector((0.0, 0.0, 0.022))])
        for i in range(len(pts) - 1):
            q = first + 2 * i
            b.face([q + 2, q + 3, q + 1, q] if side < 0 else [q, q + 1, q + 3, q + 2], "leather")  # facing out
    for s in ("l", "r"):
        el, wr = J[f"lowerarm_{s}"], J[f"hand_{s}"]
        out = Vector((1.0 if s == "l" else -1.0, 0.0, 0.0))
        b.tube([el.lerp(wr, 0.38), el.lerp(wr, 0.7), el.lerp(wr, 0.96)], [0.05, 0.048, 0.042], 7, "leather", out)
    pouch = at(0.96, -0.02) + Vector((-0.165, 0, 0))
    b.tube([pouch + Vector((0, 0, 0.045)), pouch - Vector((0, 0, 0.05))], [(0.035, 0.05), (0.03, 0.045)], 6, "leather_dark",
           hint=Vector((0, 1, 0)))
