"""Act 1 screenshots: build each zone around a camera spot from act1_world, then render.
blender -b --factory-startup -P act1_shots.py -- <outdir> <preview|final> <shot> [...]
Reuses the low-poly kit (materials, builders, lighting helpers) from forest_cam.py.
"""
import os, sys, math, json, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_src = open(os.path.join(HERE, "forest_cam.py")).read()
exec(_src[:_src.index("# ---------------------------------------------------------------- shots")])

import numpy as np
import act1_world as A
from mathutils import Vector, Matrix

MAT_EMBER = mat_emit("Ember", "#ff7a2a", 9.0)
MAT_FIRE = mat_emit("Fire", "#ff8a2a", 5.0)
MAT_GLASS = mat_dark("Glass", "#2a3540")
MAT_WARMWIN = mat_emit("WarmWindow", "#ffb860", 3.0)
P.update({k: lin(v) for k, v in {
    "falu": "#8a2a1c", "falu2": "#7a2418", "white": "#e6e0d2", "shingle": "#4a3d33", "shingle2": "#3d322a", "turf": "#5f7a36",
    "timber": "#4a3322", "timber2": "#5a3e28", "thatch": "#6b5a3a", "charred": "#231e1a", "charred2": "#332a24", "cloth": "#9a2a20",
    "cloth2": "#d8c7a0", "hay": "#c2a45a", "hay2": "#d4b86a", "wool": "#e6e0d2", "wool2": "#d6cfbf", "sheephead": "#2a2522",
    "wolf": "#6e6e6a", "wolf2": "#55554f", "wolfdark": "#3a3a37", "stonewall": "#7c786e", "stonewall2": "#6a675e", "stonewall3": "#8c887e",
    "birch": "#dcd8cc", "birchmark": "#2a2826", "birchleaf": "#7f9a3f", "birchleaf2": "#93ad4a", "birchleaf3": "#6e8a36",
    "sprucedk": "#1f3824", "sprucedk2": "#27432c", "sprucedk3": "#2d4a30", "deadwood": "#4a4440", "deadwood2": "#5a534d", "blackwood": "#2e2a29",
    "crop": "#c2ab5e", "crop2": "#b39a50", "soil": "#6f5a3a", "tunic_b": "#4f6a8a", "tunic_g": "#4f6b3d", "tunic_y": "#a08a4a", "dress": "#6a3d5a",
}.items()})


# ------------------------------------------------------------------ extra ground layers on the textured ground shader
def extend_ground():
    nt = MAT_GROUND.node_tree
    N, L = nt.nodes, nt.links
    path_in, path_out, grade = N["PathIn"], N["PathOut"], N["Grade"]
    pos = N.new("ShaderNodeNewGeometry").outputs["Position"]

    def link(v, sock):
        if hasattr(v, "links") or hasattr(v, "is_output"):
            L.new(v, sock)
        else:
            sock.default_value = v

    def offs(v):
        vm = N.new("ShaderNodeVectorMath")
        vm.operation = "ADD"
        L.new(pos, vm.inputs[0])
        vm.inputs[1].default_value = v
        return vm.outputs[0]

    def noise(scale, detail=2.0, rough=0.5, off=(0, 0, 0)):
        n = N.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rough
        L.new(offs(off), n.inputs["Vector"])
        return n.outputs["Fac"]

    def ramp(fac, stops):
        r = N.new("ShaderNodeValToRGB")
        el = r.color_ramp.elements
        el[0].position, el[0].color = stops[0][0], lin(stops[0][1])
        el[1].position, el[1].color = stops[-1][0], lin(stops[-1][1])
        for p_, c_ in stops[1:-1]:
            el.new(p_).color = lin(c_)
        L.new(fac, r.inputs["Fac"])
        return r.outputs["Color"]

    def mix(fac, a, b):
        mx = N.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        link(fac, [x for x in mx.inputs if x.name == "Factor" and x.type == "VALUE"][0])
        link(lin(a) if isinstance(a, str) else a, [x for x in mx.inputs if x.name == "A" and x.type == "RGBA"][0])
        link(lin(b) if isinstance(b, str) else b, [x for x in mx.inputs if x.name == "B" and x.type == "RGBA"][0])
        return [x for x in mx.outputs if x.name == "Result" and x.type == "RGBA"][0]

    def math_(op, a, b=0.0):
        mt = N.new("ShaderNodeMath")
        mt.operation = op
        link(a, mt.inputs[0])
        link(b, mt.inputs[1])
        return mt.outputs[0]

    def sstep(v, lo, hi, a=0.0, b=1.0):
        mr = N.new("ShaderNodeMapRange")
        mr.interpolation_type = "SMOOTHSTEP"
        link(v, mr.inputs["Value"])
        mr.inputs["From Min"].default_value = lo
        mr.inputs["From Max"].default_value = hi
        mr.inputs["To Min"].default_value = a
        mr.inputs["To Max"].default_value = b
        return mr.outputs["Result"]

    def attr(name):
        a = N.new("ShaderNodeAttribute")
        a.attribute_name = name
        a.attribute_type = "GEOMETRY"
        return a.outputs["Fac"]

    def broken(mask, scale, amt, off):
        return sstep(math_("ADD", mask, math_("MULTIPLY", math_("SUBTRACT", noise(scale, 2.0, 0.5, off), 0.5), amt)), 0.42, 0.58)

    # meadow grass, under the path so roads and trails show as worn tracks through it
    col = path_in.inputs["Color"].links[0].from_socket
    mead = ramp(noise(0.3, 3.0, 0.55, (11, 5, 0)), [(0.3, "#7f9a44"), (0.5, "#96a650"), (0.68, "#adb062"), (0.82, "#bdb46c")])
    mead = mix(math_("MULTIPLY", sstep(noise(1.6, 2.0, 0.6, (5, 1, 0)), 0.45, 0.75), 0.35), mead, "#c6bd76")
    col = mix(broken(attr("meadow"), 0.5, 0.5, (2, 9, 0)), col, mead)
    L.new(col, path_in.inputs["Color"])
    # the rest sits on top of the path: dark, damp floor in the misty and forsaken forests
    col = path_out.outputs["Color"]
    dark = ramp(noise(0.6, 3.0, 0.55, (3, 3, 0)), [(0.3, "#2c3a22"), (0.55, "#3a4a2a"), (0.75, "#4a4a32")])
    col = mix(math_("MULTIPLY", attr("darkfloor"), 0.75), col, dark)
    # fields: soil with crop rows
    soil = ramp(noise(2.0, 2.0, 0.6, (7, 7, 0)), [(0.3, "#5e4b30"), (0.7, "#7a6340")])
    col = mix(attr("fieldbase"), col, soil)
    crop = ramp(noise(3.0, 2.0, 0.6, (1, 4, 0)), [(0.3, "#b39a50"), (0.7, "#cdb565")])
    col = mix(math_("MULTIPLY", attr("field"), 0.95), col, crop)
    # packed yard dirt
    yard = ramp(noise(1.2, 3.0, 0.6, (9, 2, 0)), [(0.3, "#6e5a40"), (0.6, "#86704f"), (0.8, "#9a8460")])
    col = mix(broken(attr("yard"), 0.7, 0.4, (4, 4, 0)), col, yard)
    # cobbles in the old courtyard
    vor = N.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 1.6
    L.new(pos, vor.inputs["Vector"])
    edge = N.new("ShaderNodeTexVoronoi")
    edge.feature = "DISTANCE_TO_EDGE"
    edge.inputs["Scale"].default_value = 1.6
    L.new(pos, edge.inputs["Vector"])
    bw = N.new("ShaderNodeRGBToBW")
    L.new(vor.outputs["Color"], bw.inputs[0])
    cob = ramp(bw.outputs[0], [(0.2, "#77736a"), (0.5, "#8d8980"), (0.8, "#a19c92")])
    gap = sstep(edge.outputs["Distance"], 0.02, 0.07, 1.0, 0.0)
    cob = mix(gap, cob, "#4e5a32")
    col = mix(math_("MULTIPLY", broken(attr("paving"), 0.6, 0.5, (8, 8, 0)), 0.92), col, cob)
    # ash around the burned farm
    ash = ramp(noise(2.5, 3.0, 0.6, (6, 1, 0)), [(0.3, "#1f1b18"), (0.6, "#3a332d"), (0.85, "#5a524a")])
    col = mix(broken(attr("ash"), 1.0, 0.5, (2, 2, 0)), col, ash)
    L.new(col, grade.inputs["Color"])


extend_ground()


# ------------------------------------------------------------------ terrain from the world data
def grid_mesh(name, cx, cy, half, step, hole=None, drop=0.0, attrs=True):
    xs = np.arange(cx - half, cx + half + 1e-6, step)
    ys = np.arange(cy - half, cy + half + 1e-6, step)
    X, Y = np.meshgrid(xs, ys)
    masks = A.zone_masks(X, Y)
    Z = A.height(X, Y, masks) - drop
    nx, ny = len(xs), len(ys)
    verts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    I, J = np.meshgrid(np.arange(nx - 1), np.arange(ny - 1))
    a = (J * nx + I).ravel()
    quads = np.stack([a, a + 1, a + nx + 1, a + nx], -1)
    if hole is not None:
        qx = (X[:-1, :-1] + step / 2).ravel()
        qy = (Y[:-1, :-1] + step / 2).ravel()
        keep = ~((np.abs(qx - cx) < hole) & (np.abs(qy - cy) < hole))
        quads = quads[keep]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts.tolist(), [], quads.tolist())
    me.update()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    if attrs:
        G = A.ground_masks(X, Y, masks)
        G["bog"] = G["bog"] * 0.9
        G["pathw"] = np.clip(1 - A.path_dist(X, Y) / 4.0, 0, 1)  # see the path layer in forest_cam.mat_ground
        for k in ("pathw", "litter", "bog", "shore", "meadow", "field", "fieldbase", "yard", "paving", "ash", "darkfloor"):
            at = me.attributes.new(k, "FLOAT", "POINT")
            at.data.foreach_set("value", G[k].ravel().astype(np.float32))
    me.materials.append(MAT_GROUND)
    return place(me, (0, 0, 0), name=name)


def gz(x, y):
    return float(A.height(np.array([x]), np.array([y]))[0])


def water_plane(poly, z, name="Water"):
    b = Builder()
    vs = [b.bm.verts.new((x, y, z)) for x, y in poly]
    f = b.bm.faces.new(vs)
    b.paint([f], lambda f: (1, 1, 1, 1))
    return place(b.mesh(name, mats=[MAT_WATER]), (0, 0, 0))


def add_waters(cx, cy, R):
    out = []
    lk = A.LAKE
    if math.hypot(cx - lk["c"][0], cy - lk["c"][1]) < R + 80:
        ang = np.linspace(0, math.tau, 48, endpoint=False)
        rim = [gz(lk["c"][0] + math.cos(a) * lk["rx"] * 1.02, lk["c"][1] + math.sin(a) * lk["ry"] * 1.02) for a in ang]
        z = float(np.percentile(rim, 15)) - 0.05
        poly = [(lk["c"][0] + math.cos(a) * lk["rx"] * 1.25, lk["c"][1] + math.sin(a) * lk["ry"] * 1.25) for a in ang]
        water_plane(poly, z)
        out.append([[round(x, 1), round(y, 1)] for x, y in poly[::2]])
    ho = A.HOLLOW
    if math.hypot(cx - ho["c"][0], cy - ho["c"][1]) < R + 40:
        ang = np.linspace(0, math.tau, 32, endpoint=False)
        rim = [gz(ho["c"][0] + math.cos(a) * 12, ho["c"][1] + math.sin(a) * 12) for a in ang]
        z = float(np.mean(rim)) - 0.15
        poly = [(ho["c"][0] + math.cos(a) * 16, ho["c"][1] + math.sin(a) * 16) for a in ang]
        water_plane(poly, z)
        out.append([[round(x, 1), round(y, 1)] for x, y in poly[::2]])
    bg = A.BOG
    if math.hypot(cx - bg["c"][0], cy - bg["c"][1]) < R + max(bg["rx"], bg["ry"]):
        ang = np.linspace(0, math.tau, 48, endpoint=False)
        poly = [(bg["c"][0] + math.cos(a) * bg["rx"] * 0.98, bg["c"][1] + math.sin(a) * bg["ry"] * 0.98) for a in ang]
        water_plane(poly, A.BOG_WATER)
    st = A.STREAM
    if min(math.hypot(cx - x, cy - y) for x, y in st) < R + 40:
        b = Builder()
        left, right = [], []
        for i, (x, y) in enumerate(st):
            x2, y2 = st[min(i + 1, len(st) - 1)]
            x1, y1 = st[max(i - 1, 0)]
            dx, dy = x2 - x1, y2 - y1
            L_ = math.hypot(dx, dy) or 1
            nx, ny = -dy / L_, dx / L_
            z = gz(x, y) + 0.5
            left.append(b.bm.verts.new((x + nx * 2.4, y + ny * 2.4, z)))
            right.append(b.bm.verts.new((x - nx * 2.4, y - ny * 2.4, z)))
        fs = [b.bm.faces.new((left[i], left[i + 1], right[i + 1], right[i])) for i in range(len(st) - 1)]
        b.paint(fs, lambda f: (1, 1, 1, 1))
        place(b.mesh("Stream", mats=[MAT_WATER]), (0, 0, 0))
    return out


# ------------------------------------------------------------------ new plants
def tall_spruce_mesh(seed):
    r = random.Random(seed)
    b = Builder()
    H = r.uniform(9.0, 14.0)
    b.limb((0, 0, -0.3), (0, 0, H * 0.3), 0.26, 0.18, pick("barklow", "barklow2"), segs=6)
    tiers = r.randint(7, 9)
    for k in range(tiers):
        t = k / tiers
        z0 = H * (0.12 + t * 0.82)
        rad = H * 0.2 * (1 - t * 0.85) + 0.22
        b.limb((0, 0, z0), (0, 0, z0 + H * 0.2), rad, 0.0, pick("sprucedk", "sprucedk2", "sprucedk3"), segs=7)
    return b.mesh("TallSpruce%d" % seed)


def birch_mesh(seed):
    r = random.Random(seed)
    b = Builder()
    H = r.uniform(7.0, 10.0)
    lean = Vector((r.uniform(-0.4, 0.4), r.uniform(-0.4, 0.4), 0))

    def bark(f):
        return jitter(P["birchmark"]) if r.random() < 0.22 else jitter(P["birch"], 0.03)
    b.limb((0, 0, -0.2), Vector((0, 0, H * 0.75)) + lean, 0.17, 0.08, bark, segs=6)
    for k in range(r.randint(4, 6)):
        t = r.uniform(0.5, 0.95)
        a = r.uniform(0, math.tau)
        c = Vector((math.cos(a) * r.uniform(0.6, 1.5), math.sin(a) * r.uniform(0.6, 1.5), H * t)) + lean * t
        b.ico(c, r.uniform(0.9, 1.4), pick("birchleaf", "birchleaf2", "birchleaf3"), sub=1, scale=(1, 1, 1.2), displace=0.1)
    return b.mesh("Birch%d" % seed)


def dead_tree_mesh(seed, dark=False):
    r = random.Random(seed)
    b = Builder()
    H = r.uniform(7.0, 11.0)
    key = ("blackwood", "deadwood") if dark else ("deadwood", "deadwood2", "snag")
    top = Vector((r.uniform(-0.5, 0.5), r.uniform(-0.5, 0.5), H))
    b.limb((0, 0, -0.3), top, 0.3, 0.06, pick(*key), segs=6)
    for k in range(r.randint(5, 8)):
        t = r.uniform(0.3, 0.9)
        p0 = top * t
        a = r.uniform(0, math.tau)
        L_ = (1 - t) * r.uniform(2.0, 4.0) + 0.8
        p1 = p0 + Vector((math.cos(a) * L_, math.sin(a) * L_, r.uniform(0.6, 2.0)))
        b.limb(p0, p1, 0.08 * (1 - t) + 0.03, 0.01, pick(*key), segs=4)
        if r.random() < 0.6:
            p2 = p1 + Vector((math.cos(a + 0.6) * L_ * 0.4, math.sin(a + 0.6) * L_ * 0.4, r.uniform(0.3, 1.0)))
            b.limb(p1, p2, 0.03, 0.005, pick(*key), segs=3)
    return b.mesh("Dead%d" % seed)


# ------------------------------------------------------------------ buildings and props
def gable_house(x, y, rot, w, d, h, wall, roof, pitch=40, door=True, windows=2, trim="white", chimney=True, warm=False, name="House"):
    b = Builder()
    a = math.radians(pitch)
    b.box((w, d, h), (0, 0, h / 2), pick(wall, wall))
    rh = (d / 2) * math.tan(a)
    for s in (-1, 1):  # gable triangles
        v = [b.bm.verts.new((s * w / 2, -d / 2, h)), b.bm.verts.new((s * w / 2, d / 2, h)), b.bm.verts.new((s * w / 2, 0, h + rh))]
        f = b.bm.faces.new(v if s > 0 else v[::-1])
        b.paint([f], pick(wall))
    ov = 0.45
    half = d / 2 + ov
    slant = half / math.cos(a)
    for s in (-1, 1):
        c = (0, s * (half / 2 - ov / 2 + 0.05), h + (half / 2 - ov) * math.tan(a) + 0.12)
        cy_ = s * (d / 4)
        cz = h + rh / 2 + 0.1
        b.box((w + 2 * ov, slant, 0.24), (0, cy_ + s * 0.05, cz), pick(roof, roof + "2" if roof + "2" in P else roof),
              rot=Matrix.Rotation(-s * a, 4, "X"))
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.box((0.18, 0.18, h + 0.02), (sx * (w / 2 - 0.05), sy * (d / 2 - 0.05), h / 2), pick(trim))
    for k in range(windows):
        wx = -w / 2 + w * (k + 1) / (windows + 1)
        if door and windows % 2 == 1 and k == windows // 2:
            continue
        for sy in (-1, 1):
            b.box((1.0, 0.1, 1.0), (wx, sy * (d / 2 + 0.03), h * 0.58), pick(trim))
            b.box((0.78, 0.12, 0.78), (wx, sy * (d / 2 + 0.05), h * 0.58), lambda f: (1, 1, 1, 1), mat_index=2 if warm else 1)
    if door:
        b.box((1.25, 0.12, 2.1), (0, -d / 2 - 0.04, 1.05), pick(trim))
        b.box((1.0, 0.16, 1.95), (0, -d / 2 - 0.06, 0.98), pick("timber"))
    if chimney:
        b.box((0.7, 0.7, 2.2), (w * 0.25, 0.4, h + rh * 0.6), pick("stone", "stone2"))
    ob = place(b.mesh(name, mats=[MAT, MAT_GLASS, MAT_WARMWIN]), (x, y, gz(x, y) - 0.1), math.radians(rot))
    return ob


def longhouse(x, y, rot):
    b = Builder()
    w, d, h = 20, 7.5, 2.2
    b.box((w, d, h), (0, 0, h / 2), pick("timber", "timber2"))
    a = math.radians(52)
    rh = (d / 2) * math.tan(a)
    half = d / 2 + 0.7
    slant = half / math.cos(a)
    for s in (-1, 1):
        b.box((w + 1.0, slant, 0.35), (0, s * (d / 4), h + rh / 2 + 0.1), pick("turf", "moss3", "turf"), rot=Matrix.Rotation(-s * a, 4, "X"))
        v = [b.bm.verts.new((s * w / 2, -d / 2, h)), b.bm.verts.new((s * w / 2, d / 2, h)), b.bm.verts.new((s * w / 2, 0, h + rh))]
        f = b.bm.faces.new(v if s > 0 else v[::-1])
        b.paint([f], pick("timber2"))
        # crossed carved gable boards
        for t in (-1, 1):
            p0 = Vector((s * (w / 2 + 0.55), t * 1.2, h + rh - 1.0))
            p1 = Vector((s * (w / 2 + 0.55), -t * 0.9, h + rh + 1.4))
            b.limb(p0, p1, 0.12, 0.08, pick("timber"), segs=4)
            b.ico(p1 + Vector((0, -t * 0.25, 0.15)), 0.22, pick("timber2"), sub=1, scale=(0.6, 1.4, 0.8))
    for k in range(7):
        b.box((0.3, 0.3, h + 0.3), (-w / 2 + k * w / 6, -d / 2 - 0.1, h / 2), pick("timber2"))
    b.box((1.8, 0.2, 2.0), (0, -d / 2 - 0.1, 1.0), pick("timber"))
    cnt = [0]
    for k in (-3.5, -1.8, 1.8, 3.5):
        res = bmesh.ops.create_cone(b.bm, cap_ends=True, cap_tris=False, segments=10, radius1=0.45, radius2=0.45, depth=0.06,
                                    matrix=Matrix.Translation((k, -d / 2 - 0.22, 1.5)) @ Matrix.Rotation(math.radians(90), 4, "X"))
        fs = b._faces(res["verts"])
        cnt[0] += 1
        ccol = P["shieldpaint"] if cnt[0] % 2 else P["cloth"]
        b.paint(fs, lambda f, c=ccol: jitter(c))
    return place(b.mesh("Longhouse"), (x, y, gz(x, y) - 0.1), math.radians(rot))


def well_sweep(x, y, rot):
    b = Builder()
    b.box((1.5, 1.5, 0.9), (0, 0, 0.45), pick("timber2"))
    b.box((1.2, 1.2, 0.05), (0, 0, 0.92), lambda f: lin("#141414"))
    b.limb((2.2, 0, 0), (2.2, 0, 4.2), 0.16, 0.13, pick("timber"), segs=6)
    b.limb((2.2, 0, 4.0), (2.4, 0, 4.6), 0.07, 0.05, pick("timber"), segs=4)
    b.limb((2.0, 0, 4.0), (1.9, 0, 4.6), 0.07, 0.05, pick("timber"), segs=4)
    p_pivot = Vector((2.2, 0, 4.3))
    p_long = Vector((-0.2, 0, 7.6))
    p_short = Vector((4.6, 0, 2.6))
    b.limb(p_short, p_long, 0.09, 0.05, pick("timber2"), segs=5)
    b.ico(p_short + Vector((0.2, 0, -0.2)), 0.45, pick("stone", "stone2"), sub=1)
    b.limb(p_long, Vector((0.0, 0, 1.6)), 0.015, 0.015, pick("belt"), segs=3)
    b.limb((0, 0, 1.2), (0, 0, 1.6), 0.18, 0.2, pick("timber"), segs=7)
    return place(b.mesh("WellSweep"), (x, y, gz(x, y)), math.radians(rot))


def fence(points, step=1.7):
    b = Builder()
    pts = [Vector((x, y, 0)) for x, y in points]
    for i in range(len(pts) - 1):
        p0, p1 = pts[i], pts[i + 1]
        L_ = (p1 - p0).length
        n = max(1, int(L_ // step))
        d = (p1 - p0).normalized()
        side = Vector((-d.y, d.x, 0))
        for k in range(n):
            p = p0 + d * (k * L_ / n)
            z = gz(p.x, p.y)
            for s in (-0.12, 0.12):
                q = p + side * s
                b.limb((q.x, q.y, z - 0.2), (q.x, q.y, z + 1.25), 0.04, 0.035, pick("snag", "snag2"), segs=4)
            a0 = p - d * 1.0 + Vector((0, 0, z + 0.15))
            a1 = p + d * 1.4 + Vector((0, 0, z + 1.15))
            b.limb(a0, a1, 0.05, 0.04, pick("snag", "snag2", "log"), segs=4)
    return place(b.mesh("Fence"), (0, 0, 0))


def stall(x, y, rot):
    b = Builder()
    for sx in (-1.4, 1.4):
        for sy in (-0.9, 0.9):
            b.limb((sx, sy, 0), (sx, sy, 2.3 if sy < 0 else 2.0), 0.06, 0.05, pick("timber"), segs=4)
    b.box((3.0, 1.6, 0.12), (0, 0, 0.9), pick("timber2"))
    cnt = [0]

    def stripes(f):
        cnt[0] += 1
        return jitter(P["cloth"] if (int(f.calc_center_median().x * 1.4 + 10) % 2) else P["cloth2"])
    b.box((3.4, 2.2, 0.06), (0, 0, 2.2), pick("cloth"), rot=Matrix.Rotation(math.radians(8), 4, "X"))
    b.box((3.45, 0.08, 0.3), (0, -1.1, 2.05), pick("cloth2"))
    for k in range(4):
        b.box((0.45, 0.4, 0.3), (-1.0 + k * 0.62, 0.1, 1.11), pick("hay", "crop2", "berryred", "steeldark"))
    for k in range(2):
        b.limb((1.9 + k * 0.7, 0.8, 0), (1.9 + k * 0.7, 0.8, 0.85), 0.32, 0.3, pick("timber2"), segs=8)
    b.box((0.7, 0.7, 0.6), (-2.1, 0.6, 0.3), pick("timber2"))
    return place(b.mesh("Stall"), (x, y, gz(x, y)), math.radians(rot))


def campfire(x, y):
    b = Builder()
    for k in range(9):
        a = k * math.tau / 9
        b.ico((math.cos(a) * 0.75, math.sin(a) * 0.75, 0.1), 0.2, pick("stone", "stone2"), sub=1, scale=(1, 1, 0.7))
    for k in range(3):
        a = k * math.tau / 3
        b.limb((math.cos(a) * 0.6, math.sin(a) * 0.6, 0.05), (0, 0, 0.5), 0.07, 0.05, pick("log", "charred"), segs=5)
    for k in range(3):
        a = k * math.tau / 3 + 0.5
        b.limb((math.cos(a) * 0.15, math.sin(a) * 0.15, 0.1), (math.cos(a) * 0.05, math.sin(a) * 0.05, 0.9 - k * 0.15), 0.22, 0.0, lambda f: P["gold"], segs=5, mat_index=1)
    ob = place(b.mesh("Campfire", mats=[MAT, MAT_FLAME]), (x, y, gz(x, y)))
    add_point(None, None, 0, parent=ob, local=(0, 0, 1.0), color="#ff9a3c", power=420, radius=0.3)
    return ob


def woodpile(x, y, rot, n=24):
    b = Builder()
    for k in range(n):
        row, col = divmod(k, 8)
        b.limb((-0.6, col * 0.24 - 0.85 + (row % 2) * 0.12, 0.12 + row * 0.22), (0.6, col * 0.24 - 0.85 + (row % 2) * 0.12, 0.12 + row * 0.22),
               0.11, 0.11, pick("log", "log2", "wood"), segs=6)
    b.box((1.4, 2.2, 0.08), (0, 0, 0.12 + (n // 8) * 0.22 + 0.15), pick("shingle"))
    return place(b.mesh("Woodpile"), (x, y, gz(x, y)), math.radians(rot))


def haystack(x, y, s=1.0):
    b = Builder()
    b.ico((0, 0, 0.9), 1.3, pick("hay", "hay2"), sub=1, scale=(1, 1, 0.95), displace=0.08)
    b.ico((0, 0, 1.95), 0.55, pick("hay2"), sub=1)
    b.limb((0, 0, 0), (0, 0, 2.7), 0.04, 0.03, pick("timber"), segs=4)
    return place(b.mesh("Haystack"), (x, y, gz(x, y)), random.uniform(0, 6), scale=s)


def hay_rack(x, y, rot, length=16):
    b = Builder()
    n = int(length // 2.2)
    for k in range(n + 1):
        px = -length / 2 + k * length / n
        b.limb((px, 0, -0.2), (px, 0, 2.0), 0.05, 0.04, pick("timber"), segs=4)
    for zz in (0.5, 1.0, 1.5):
        b.limb((-length / 2, 0, zz), (length / 2, 0, zz), 0.03, 0.03, pick("timber"), segs=4)
    for k in range(n):
        px = -length / 2 + (k + 0.5) * length / n
        b.box((length / n + 0.1, 0.55, 1.6), (px, 0, 1.0), pick("hay", "hay2"), top_scale=0.35)
    return place(b.mesh("HayRack"), (x, y, gz(x, y)), math.radians(rot))


def villager(x, y, facing, tunic, hood=None, dress=False, s=1.0):
    root = bpy.data.objects.new("Villager", None)
    root.location = (x, y, gz(x, y))
    root.rotation_euler = (0, 0, facing)
    root.scale = (s, s, s)
    COLL.objects.link(root)
    b = Builder()
    if dress:
        b.box((0.5, 0.36, 0.95), (0, 0, 0.5), pick(tunic), top_scale=0.7)
    else:
        for sx in (-0.1, 0.1):
            b.box((0.16, 0.18, 0.9), (sx, 0, 0.45), pick("trouser"))
    b.box((0.44, 0.26, 0.6), (0, 0, 1.25), pick(tunic), top_scale=1.08)
    b.box((0.46, 0.28, 0.07), (0, 0, 0.97), pick("belt"))
    for sx in (-0.29, 0.29):
        b.box((0.13, 0.13, 0.58), (sx, 0.04, 1.2), pick(tunic), rot=Matrix.Rotation(math.radians(8 if sx < 0 else -8), 4, "X"))
        b.box((0.1, 0.1, 0.1), (sx, 0.1, 0.88), pick("skin"))
    b.ico((0, 0, 1.72), 0.15, pick("skin"), sub=1, scale=(0.95, 1, 1.1))
    if hood:
        b.ico((0, -0.03, 1.77), 0.18, pick(hood), sub=1, scale=(1, 1.05, 1.0))
    else:
        b.ico((0, -0.035, 1.77), 0.155, pick("hair", "beard"), sub=1, scale=(1, 1, 0.85))
    ob = place(b.mesh("VillagerBody"), (0, 0, 0), parent=root)
    return root


def sheep(x, y, facing, s=1.0):
    b = Builder()
    b.ico((0, 0, 0.62), 1.0, pick("wool", "wool2"), sub=1, scale=(0.42, 0.7, 0.38), displace=0.04)
    for k in range(3):
        b.ico((random.uniform(-0.15, 0.15), random.uniform(-0.4, 0.4), 0.88), 0.2, pick("wool", "wool2"), sub=1)
    b.box((0.2, 0.32, 0.24), (0, 0.72, 0.78), pick("sheephead"), top_scale=0.8)
    for sx in (-0.18, 0.18):
        for sy in (-0.42, 0.42):
            b.limb((sx, sy, 0.35), (sx, sy, 0.0), 0.05, 0.04, pick("sheephead"), segs=4)
    return place(b.mesh("Sheep"), (x, y, gz(x, y)), facing, scale=s)


def wolf(x, y, facing, s=1.0):
    b = Builder()
    b.box((0.42, 1.2, 0.5), (0, 0, 0.8), pick("wolf", "wolf2"), top_scale=0.85)
    b.box((0.36, 0.5, 0.4), (0, 0.72, 1.0), pick("wolf"))
    b.box((0.18, 0.4, 0.2), (0, 1.1, 0.92), pick("wolf2"), top_scale=0.7)
    for sx in (-0.11, 0.11):
        b.limb((sx, 0.85, 1.18), (sx, 0.82, 1.42), 0.07, 0.0, pick("wolfdark"), segs=4)
    for sx in (-0.15, 0.15):
        for sy in (-0.45, 0.45):
            b.limb((sx, sy, 0.6), (sx, sy + 0.05, 0.0), 0.07, 0.05, pick("wolf2"), segs=4)
    b.limb((0, -0.6, 0.95), (0, -1.2, 0.65), 0.1, 0.03, pick("wolf2"), segs=4)
    return place(b.mesh("Wolf"), (x, y, gz(x, y)), facing, scale=s)


def watchtower(x, y, rot):
    b = Builder()
    H = 9.0
    for sx in (-1.6, 1.6):
        for sy in (-1.6, 1.6):
            b.limb((sx * 1.15, sy * 1.15, -0.3), (sx, sy, H + 1.2), 0.17, 0.13, pick("timber", "timber2"), segs=6)
    for zz in (2.5, 5.5):
        for (ax, ay), (bx_, by_) in (((-1.6, -1.6), (1.6, -1.6)), ((1.6, -1.6), (1.6, 1.6)), ((1.6, 1.6), (-1.6, 1.6)), ((-1.6, 1.6), (-1.6, -1.6))):
            b.limb((ax * 1.08, ay * 1.08, zz), (bx_ * 1.04, by_ * 1.04, zz + 2.6), 0.07, 0.07, pick("timber2"), segs=4)
    b.box((4.0, 4.0, 0.25), (0, 0, H), pick("wood", "wood2"))
    for s in (-1, 1):
        b.box((4.0, 0.12, 0.12), (0, s * 1.95, H + 1.0), pick("timber"))
        b.box((0.12, 4.0, 0.12), (s * 1.95, 0, H + 1.0), pick("timber"))
    b.limb((0, 0, H + 1.2), (0, 0, H + 3.4), 2.8, 0.0, pick("shingle", "shingle2"), segs=4)
    for s in (-0.35, 0.35):
        b.limb((s, -2.6, 0), (s, -1.7, H), 0.05, 0.05, pick("timber2"), segs=4)
    for k in range(14):
        t = (k + 0.5) / 14
        b.limb((-0.35, -2.6 + 0.9 * t, H * t), (0.35, -2.6 + 0.9 * t, H * t), 0.03, 0.03, pick("timber2"), segs=3)
    return place(b.mesh("Watchtower"), (x, y, gz(x, y)), math.radians(rot))


def beacon(x, y, lit=True):
    b = Builder()
    for k in range(26):
        a = k * math.tau / 26 + random.uniform(-0.05, 0.05)
        r0 = random.uniform(1.5, 1.9)
        b.limb((math.cos(a) * r0, math.sin(a) * r0, -0.1), (math.cos(a) * 0.25, math.sin(a) * 0.25, random.uniform(3.4, 4.2)), 0.1, 0.08, pick("log", "log2", "timber"), segs=5)
    if lit:
        for k in range(6):
            a = k * math.tau / 6
            b.limb((math.cos(a) * 0.5, math.sin(a) * 0.5, 2.6), (math.cos(a) * 0.15, math.sin(a) * 0.15, 5.0 + random.uniform(-0.4, 0.6)), 0.45, 0.0, lambda f: P["gold"], segs=5, mat_index=1)
    ob = place(b.mesh("Beacon", mats=[MAT, MAT_FIRE]), (x, y, gz(x, y)))
    if lit:
        add_point(None, None, 0, parent=ob, local=(0, 0, 4.0), color="#ff8a30", power=2500, radius=1.0)
    return ob


def stone_circle(cx, cy, r=8.0, n=9, glow_index=0):
    for k in range(n):
        a = k * math.tau / n
        x, y = cx + math.cos(a) * r, cy + math.sin(a) * r
        b = Builder()
        hgt = random.uniform(1.4, 2.2)
        b.box((0.9, 0.6, hgt), (0, 0, hgt / 2 - 0.2), pick("granite1", "granite2", "granite3"), top_scale=0.7)
        b.box((0.95, 0.65, 0.2), (0, 0, hgt - 0.25), pick("rmoss1", "lichen"))
        mats = [MAT]
        if k == glow_index:
            b.box((0.06, 0.66, 0.9), (0, 0, hgt * 0.5), lambda f: (1, 1, 1, 1), mat_index=1)
            mats = [MAT, MAT_RUNE_FOG]
        ob = place(b.mesh("Standing", mats=mats), (x, y, gz(x, y)), a + math.pi / 2 + random.uniform(-0.2, 0.2))
        ob.rotation_euler.x = random.uniform(-0.08, 0.08)
    add_point((cx + math.cos(0) * r, cy, gz(cx + r, cy) + 1.4), None, 0, color="#8fd8ff", power=140, radius=0.3)


def burned_house(x, y, rot):
    b = Builder()
    w, d, h = 10, 6, 2.6
    rr = random.Random(3)
    for s in (-1, 1):
        for k in range(10):
            if rr.random() < 0.3:
                continue
            seg = w / 10
            hh = h * rr.uniform(0.3, 1.0)
            b.box((seg + 0.05, 0.35, hh), (-w / 2 + (k + 0.5) * seg, s * d / 2, hh / 2), pick("charred", "charred2"))
        for k in range(6):
            if rr.random() < 0.35:
                continue
            seg = d / 6
            hh = h * rr.uniform(0.3, 1.0)
            b.box((0.35, seg + 0.05, hh), (s * w / 2, -d / 2 + (k + 0.5) * seg, hh / 2), pick("charred", "charred2"))
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.limb((sx * w / 2, sy * d / 2, 0), (sx * w / 2, sy * d / 2, h + rr.uniform(0, 1.2)), 0.18, 0.12, pick("charred"), segs=5)
    for k in range(5):
        p0 = Vector((rr.uniform(-w / 2, w / 2), rr.uniform(-d / 2, d / 2), 0.1))
        p1 = p0 + Vector((rr.uniform(-3, 3), rr.uniform(-2, 2), rr.uniform(1.5, 3.0)))
        b.limb(p0, p1, 0.12, 0.1, pick("charred", "charred2"), segs=5)
    b.box((1.0, 1.0, 5.0), (w * 0.3, 0.6, 2.5), pick("stone", "stone2"))
    for k in range(14):
        b.ico((rr.uniform(-w / 2, w / 2), rr.uniform(-d / 2, d / 2), 0.05), rr.uniform(0.08, 0.16), lambda f: (1, 1, 1, 1), sub=1, mat_index=1)
    ob = place(b.mesh("BurnedHouse", mats=[MAT, MAT_EMBER]), (x, y, gz(x, y)), math.radians(rot))
    for k in range(3):
        add_point(None, None, 0, parent=ob, local=(rr.uniform(-3, 3), rr.uniform(-2, 2), 0.6), color="#ff6a20", power=160, radius=0.5)
    return ob


def smoke(x, y, z, hgt=26, r=4.0):
    me = bpy.data.meshes.new("Smoke")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bm.to_mesh(me)
    bm.free()
    m = bpy.data.materials.new("SmokeVol")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = lin("#5a5550")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    # a column that widens upwards and fades
    rad = nt.nodes.new("ShaderNodeVectorMath")
    rad.operation = "LENGTH"
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(sep.outputs["X"], comb.inputs["X"])
    nt.links.new(sep.outputs["Y"], comb.inputs["Y"])
    nt.links.new(comb.outputs[0], rad.inputs[0])
    widen = nt.nodes.new("ShaderNodeMapRange")
    widen.inputs["From Min"].default_value = -1
    widen.inputs["From Max"].default_value = 1
    widen.inputs["To Min"].default_value = 0.25
    widen.inputs["To Max"].default_value = 0.95
    nt.links.new(sep.outputs["Z"], widen.inputs["Value"])
    dv = nt.nodes.new("ShaderNodeMath")
    dv.operation = "DIVIDE"
    nt.links.new(rad.outputs["Value"], dv.inputs[0])
    nt.links.new(widen.outputs[0], dv.inputs[1])
    col_ = nt.nodes.new("ShaderNodeMapRange")
    col_.inputs["From Min"].default_value = 1.0
    col_.inputs["From Max"].default_value = 0.2
    nt.links.new(dv.outputs[0], col_.inputs["Value"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 3.0
    nz.inputs["Detail"].default_value = 3.0
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    fade = nt.nodes.new("ShaderNodeMapRange")
    fade.inputs["From Min"].default_value = -1
    fade.inputs["From Max"].default_value = 1
    fade.inputs["To Min"].default_value = 1.0
    fade.inputs["To Max"].default_value = 0.1
    nt.links.new(sep.outputs["Z"], fade.inputs["Value"])
    m1 = nt.nodes.new("ShaderNodeMath")
    m1.operation = "MULTIPLY"
    nt.links.new(col_.outputs[0], m1.inputs[0])
    nt.links.new(nz.outputs["Fac"], m1.inputs[1])
    m2 = nt.nodes.new("ShaderNodeMath")
    m2.operation = "MULTIPLY"
    nt.links.new(m1.outputs[0], m2.inputs[0])
    nt.links.new(fade.outputs[0], m2.inputs[1])
    m3 = nt.nodes.new("ShaderNodeMath")
    m3.operation = "MULTIPLY"
    m3.inputs[1].default_value = 4.5
    nt.links.new(m2.outputs[0], m3.inputs[0])
    nt.links.new(m3.outputs[0], vol.inputs["Density"])
    nt.links.new(vol.outputs[0], out.inputs["Volume"])
    me.materials.append(m)
    ob = bpy.data.objects.new("SmokeCol", me)
    ob.location = (x, y, z + hgt / 2)
    ob.scale = (r * 2.2, r * 2.2, hgt / 2)
    ob.rotation_euler = (0.12, 0.08, 0)
    COLL.objects.link(ob)


def stone_wall(points, height=1.0, gaps=()):
    b = Builder()
    rr = random.Random(9)
    for i in range(len(points) - 1):
        p0, p1 = Vector(points[i] + (0,)), Vector(points[i + 1] + (0,))
        L_ = (p1 - p0).length
        d = (p1 - p0).normalized()
        n = int(L_ // 1.1)
        for k in range(n):
            t = (k + 0.5) / n
            p = p0 + (p1 - p0) * t
            if any((p - Vector(g + (0,))).length < r for g, r in gaps):
                continue
            z = gz(p.x, p.y)
            hh = height * rr.uniform(0.55, 1.1)
            rot = Matrix.Rotation(math.atan2(d.y, d.x) + rr.uniform(-0.1, 0.1), 4, "Z")
            b.box((1.15, 0.75, hh), (p.x, p.y, z + hh / 2 - 0.15), pick("stonewall", "stonewall2", "stonewall3"), top_scale=0.85, rot=rot)
            if rr.random() < 0.4:
                b.box((0.6, 0.5, 0.35), (p.x + rr.uniform(-0.3, 0.3), p.y + rr.uniform(-0.2, 0.2), z + hh + 0.05), pick("stonewall3", "rmoss1"), rot=rot)
    return place(b.mesh("StoneWall"), (0, 0, 0))


def manor_ruin(x, y, rot):
    b = Builder()
    w, d, h = 16, 9, 3.4
    rr = random.Random(5)

    def wall_run(x0, y0, x1, y1, holes):
        L_ = math.hypot(x1 - x0, y1 - y0)
        n = int(L_ // 2.0)
        ang = math.atan2(y1 - y0, x1 - x0)
        rot = Matrix.Rotation(ang, 4, "Z")
        for k in range(n):
            t = (k + 0.5) / n
            px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            seg = L_ / n + 0.05
            if any(abs(t - c) < hw for c, hw in holes):
                b.box((seg, 0.9, 0.95), (px, py, 0.47), pick("stonewall", "stonewall2"), rot=rot)
                b.box((seg, 0.9, 0.7), (px, py, h - 0.35), pick("stonewall2"), rot=rot)
                continue
            hh = h * rr.uniform(0.92, 1.0)
            if rr.random() < 0.15:
                hh *= rr.uniform(0.35, 0.6)
            b.box((seg, 0.9, hh), (px, py, hh / 2), pick("stonewall", "stonewall2", "stonewall3"), rot=rot)
            for j in range(2):
                b.box((rr.uniform(0.5, 0.9), 0.96, rr.uniform(0.3, 0.45)), (px + rr.uniform(-0.5, 0.5) * math.cos(ang), py + rr.uniform(-0.5, 0.5) * math.sin(ang),
                      rr.uniform(0.3, hh - 0.3)), pick("stonewall3", "stonewall2", "granite4"), rot=rot)
    wall_run(-w / 2, -d / 2, w / 2, -d / 2, [(0.2, 0.05), (0.5, 0.06), (0.8, 0.05)])
    wall_run(-w / 2, d / 2, w / 2, d / 2, [(0.3, 0.05), (0.7, 0.05)])
    wall_run(-w / 2, -d / 2, -w / 2, d / 2, [(0.5, 0.08)])
    wall_run(w / 2, -d / 2, w / 2, d / 2, [])
    for k in range(5):
        p0 = Vector((rr.uniform(-w / 2, w / 2), rr.uniform(-d / 2, d / 2), h))
        p1 = p0 + Vector((rr.uniform(-4, 4), rr.uniform(-2, 2), rr.uniform(-2.5, -0.5)))
        b.limb(p0, p1, 0.14, 0.12, pick("timber", "charred2"), segs=5)
    for k in range(4):
        b.limb((-w / 2 + 2 + k * 4, -d / 2, h), (-w / 2 + 2 + k * 4, 0, h + 3.5), 0.13, 0.11, pick("timber"), segs=5)
    b.box((1.2, 1.2, 8.0), (w / 2 - 1.2, d / 2 - 1.2, 4.0), pick("stonewall2", "stonewall"))
    b.box((2.4, 0.7, 0.4), (0, -d / 2 - 0.1, 2.6), pick("stonewall3"))
    return place(b.mesh("Manor"), (x, y, gz(x, y) - 0.05), math.radians(rot))


def stone_well(x, y):
    b = Builder()
    for k in range(12):
        a = k * math.tau / 12
        b.box((0.62, 0.42, 0.85), (math.cos(a) * 0.95, math.sin(a) * 0.95, 0.42), pick("stonewall", "stonewall3"),
              rot=Matrix.Rotation(a + math.pi / 2, 4, "Z"))
    b.box((1.5, 1.5, 0.05), (0, 0, 0.6), lambda f: lin("#101010"))
    for s in (-1, 1):
        b.limb((s * 1.1, 0, 0.6), (s * 1.0, 0, 2.6), 0.08, 0.07, pick("timber"), segs=4)
    b.limb((-1.2, 0, 2.5), (1.2, 0, 2.5), 0.06, 0.06, pick("timber"), segs=4)
    return place(b.mesh("Well"), (x, y, gz(x, y)))


def cart(x, y, rot):
    b = Builder()
    b.box((2.6, 1.4, 0.5), (0, 0, 0.75), pick("wood", "wood2"))
    b.box((2.6, 0.08, 0.5), (0, 0.7, 1.15), pick("wood2"))
    b.limb((1.3, 0.3, 0.6), (3.3, 0.2, 0.1), 0.06, 0.05, pick("timber"), segs=4)
    for sy, tilt in ((-0.85, 0.0), (0.85, 1.2)):
        res = bmesh.ops.create_cone(b.bm, cap_ends=True, cap_tris=False, segments=12, radius1=0.6, radius2=0.6, depth=0.1,
                                    matrix=Matrix.Translation((-0.3 + tilt * 0.6, sy * (1 + tilt * 0.4), 0.6 - tilt * 0.45)) @ Matrix.Rotation(math.radians(90) - tilt, 4, "X"))
        b.paint(b._faces(res["verts"]), pick("timber"))
    return place(b.mesh("Cart"), (x, y, gz(x, y)), math.radians(rot))


def lantern_post(x, y, rot):
    b = Builder()
    b.limb((0, 0, -0.2), (0, 0, 2.5), 0.07, 0.06, pick("timber"), segs=5)
    b.limb((0, 0, 2.35), (0.7, 0, 2.45), 0.04, 0.04, pick("timber"), segs=4)
    b.limb((0.7, 0, 2.45), (0.7, 0, 2.2), 0.008, 0.008, pick("belt"), segs=3)
    b.box((0.2, 0.2, 0.05), (0.7, 0, 2.18), pick("belt"))
    b.box((0.16, 0.16, 0.24), (0.7, 0, 2.03), lambda f: P["gold"], mat_index=1)
    b.box((0.2, 0.2, 0.05), (0.7, 0, 1.89), pick("belt"))
    ob = place(b.mesh("LanternPost", mats=[MAT, MAT_FLAME]), (x, y, gz(x, y)), math.radians(rot))
    add_point(None, None, 0, parent=ob, local=(0.7, 0, 2.0), color="#ffa040", power=130, radius=0.1)
    return ob


def boardwalk(pts, z_water):
    b = Builder()
    for i in range(len(pts) - 1):
        p0, p1 = Vector(pts[i] + (0,)), Vector(pts[i + 1] + (0,))
        L_ = (p1 - p0).length
        d = (p1 - p0).normalized()
        side = Vector((-d.y, d.x, 0))
        n = max(1, int(L_ // 3.6))
        for k in range(n):
            a = p0 + (p1 - p0) * (k / n)
            c = p0 + (p1 - p0) * ((k + 1) / n)
            for s in (-0.22, 0.22):
                za = max(gz(a.x, a.y), z_water) + 0.22
                zc = max(gz(c.x, c.y), z_water) + 0.22
                q0 = a + side * s + Vector((0, 0, za))
                q1 = c + side * s + Vector((0, 0, zc))
                mid = (q0 + q1) / 2
                ang = math.atan2(d.y, d.x)
                pitch = math.atan2(zc - za, (q1 - q0).xy.length)
                b.box(((q1 - q0).length + 0.15, 0.36, 0.08), mid, pick("wood", "wood2", "log"),
                      rot=Matrix.Rotation(ang, 4, "Z") @ Matrix.Rotation(-pitch, 4, "Y"))
            zc = max(gz(a.x, a.y), z_water)
            b.limb(a - side * 0.6 + Vector((0, 0, zc + 0.12)), a + side * 0.6 + Vector((0, 0, zc + 0.12)), 0.08, 0.08, pick("log2", "timber"), segs=5)
    return place(b.mesh("Boardwalk"), (0, 0, 0))


def giant_tree(x, y):
    b = Builder()
    rr = random.Random(12)
    base = Vector((0, 0, -0.5))
    top = Vector((0.6, -0.4, 16.0))
    b.limb(base, top * 0.5, 2.6, 1.6, pick("blackwood", "deadwood"), segs=9)
    b.limb(top * 0.5, top, 1.6, 0.5, pick("blackwood", "deadwood"), segs=8)
    for k in range(8):
        a = k * math.tau / 8 + rr.uniform(-0.2, 0.2)
        p0 = Vector((math.cos(a) * 1.5, math.sin(a) * 1.5, 0.6))
        p1 = Vector((math.cos(a) * rr.uniform(4.5, 6.5), math.sin(a) * rr.uniform(4.5, 6.5), -0.3))
        b.limb(p0, p1, 0.9, 0.2, pick("blackwood"), segs=6)

    def branch(p, d, L_, r, depth):
        q = p + d * L_
        b.limb(p, q, r, r * 0.65, pick("blackwood", "deadwood"), segs=6 if depth < 2 else 4)
        if depth >= 3:
            return
        for s in (-1, 1):
            ax = d.cross(Vector((0, 0, 1))).normalized() if abs(d.z) < 0.99 else Vector((1, 0, 0))
            nd = (Matrix.Rotation(s * rr.uniform(0.35, 0.6), 3, ax) @ Matrix.Rotation(rr.uniform(-0.6, 0.6), 3, "Z") @ d).normalized()
            nd.z += 0.25
            branch(q, nd.normalized(), L_ * 0.68, r * 0.62, depth + 1)
    for k in range(5):
        a = k * math.tau / 5 + 0.3
        p = top * rr.uniform(0.55, 0.95)
        d = Vector((math.cos(a), math.sin(a), rr.uniform(0.4, 0.9))).normalized()
        branch(p, d, rr.uniform(4.5, 6.0), 0.55, 0)
    return place(b.mesh("GiantTree"), (x, y, gz(x, y)))


# ------------------------------------------------------------------ zone dressing
TOWN_LAYOUT = A.TOWN_LAYOUT


def dress_town():
    clear = []
    for x, y, rot, kind in TOWN_LAYOUT:
        if kind == "longhouse":
            longhouse(x, y, rot)
            clear.append(((x, y), 13))
        elif kind == "barn":
            gable_house(x, y, rot, 12, 7, 3.6, "falu", "shingle", pitch=42, windows=0, chimney=False, name="Barn")
            clear.append(((x, y), 9))
        else:
            gable_house(x, y, rot, 8, 5, 2.8, "falu", "shingle" if (x + y) % 2 else "turf", pitch=38, windows=3, name="Cottage")
            clear.append(((x, y), 7))
    well_sweep(37, -60, 20)
    stall(19, -60, 12)
    stall(28, -63, -8)
    campfire(33, -51)
    woodpile(40, -66, 10)
    woodpile(-2, -55, 90)
    haystack(52, -82)
    haystack(58, -80, 0.8)
    for k, (x, y, f, tunic, hood, dress) in enumerate([
            (17, -57, 1.2, "tunic_b", None, False), (21, -62, 2.8, "dress", "cloth2", True), (29, -60, 0.2, "tunic_y", None, False),
            (35, -58, 3.6, "tunic_g", "cloak", False), (31, -49, 4.5, "tunic_b", None, False), (35, -53, 1.5, "dress", "cloth", True),
            (25, -48, 3.1, "tunic_y", None, False), (40, -62, 2.0, "tunic_g", None, False)]):
        villager(x, y, f, tunic, hood, dress)
    rs = place(runestone_mesh(True), (A.WAYSTONES["Tallmo"][0], A.WAYSTONES["Tallmo"][1], gz(*A.WAYSTONES["Tallmo"]) - 0.1), math.radians(-30))
    add_point((A.WAYSTONES["Tallmo"][0] + 0.8, A.WAYSTONES["Tallmo"][1] - 0.8, gz(*A.WAYSTONES["Tallmo"]) + 1.0), None, 0, color="#8fd8ff", power=90, radius=0.3)
    # fence around the town edge, open at the gate and the square
    poly = A.ZONES["town"]["smooth"]
    ring = [(x * 0.94 + 26 * 0.06, y * 0.94 - 55 * 0.06) for x, y in poly]
    ring = ring + ring[:1]
    run_ = []
    for p in ring:
        if abs(p[0]) < 10 and p[1] > -40:
            if len(run_) > 1:
                fence(run_)
            run_ = []
        else:
            run_.append(p)
    if len(run_) > 1:
        fence(run_)
    for s in (-1, 1):
        b = Builder()
        b.limb((s * 3.2, 0, -0.3), (s * 3.2, 0, 4.4), 0.22, 0.18, pick("timber"), segs=6)
        b.ico((s * 3.2, 0, 4.6), 0.3, pick("timber2"), sub=1, scale=(0.7, 1.6, 0.8))
        place(b.mesh("GatePost"), (0, -27, gz(0, -27)))
    b = Builder()
    b.limb((-3.6, 0, 4.0), (3.6, 0, 4.0), 0.16, 0.16, pick("timber2"), segs=6)
    place(b.mesh("GateBeam"), (0, -27, gz(0, -27)))
    signpost((5.0, -22.0), gz(5.0, -22.0), math.radians(80), [(1.85, math.radians(10), "STORSKOGEN"), (1.55, math.radians(190), "TALLMO")])
    return clear


def dress_storskogen(shot):
    clear = [(A.HILL["c"], 9), ((A.HOLLOW["c"][0], A.HOLLOW["c"][1]), 10)]
    watchtower(152, 452, 20)
    beacon(166, 448, lit=True)
    clear += [((152, 452), 5), ((166, 448), 3.5)]
    stone_circle(A.HOLLOW["c"][0] + 19, A.HOLLOW["c"][1] + 2, r=4.6)
    clear.append(((A.HOLLOW["c"][0] + 19, A.HOLLOW["c"][1] + 2), 6))
    signpost((52.0, 228.0), gz(52.0, 228.0), math.radians(0), [(1.85, math.radians(45), "HÄRDDALEN"), (1.55, math.radians(150), "DIMSKOGEN")])
    clear.append(((52, 228), 3))
    if shot == "angen":
        for k in range(11):
            sheep(176 + random.uniform(-7, 7), 211 + random.uniform(-5, 5), random.uniform(0, math.tau), random.uniform(0.9, 1.1))
        for k, (x, y) in enumerate([(158, 222), (153, 217), (163, 227)]):
            wolf(x, y, math.radians(-30), 1.0)
        villager(184, 206, 2.0, "tunic_y", "cloth2")
        for x, y in [(190, 250), (138, 238), (226, 192), (205, 262)]:
            TREES.append(place(pine_mesh(int(x) % 6)[0], (x, y, gz(x, y) - 0.15), random.uniform(0, 6), 1.1))
    if shot == "tatskogen":
        wolf(-128, 462, math.radians(200))
        wolf(-123, 466, math.radians(210), 0.95)
    return clear


def bridge(x, y, rot):
    b = Builder()
    for k in range(9):
        b.box((0.5, 3.2, 0.12), (-2.0 + k * 0.5, 0, 0.75), pick("wood", "wood2", "log"))
    for s in (-1.5, 1.5):
        b.box((4.6, 0.14, 0.14), (0, s, 1.55), pick("timber"))
        for k in (-2.1, 0, 2.1):
            b.limb((k, s, -0.4), (k, s, 1.6), 0.07, 0.06, pick("timber"), segs=4)
    return place(b.mesh("Bridge"), (x, y, gz(x, y)), math.radians(rot))


def dress_harddalen():
    fx, fy = A.FARMSTEAD["c"]
    burned_house(fx + 6, fy - 4, 20)
    gable_house(fx - 12, fy + 10, 15, 12, 7, 3.6, "falu", "shingle", pitch=42, windows=0, chimney=False, name="Barn")
    smoke(fx + 6, fy - 4, gz(fx + 6, fy - 4), 30, 3.5)
    for k, (x, y, rot) in enumerate([(560, 790, 7), (585, 800, 7), (660, 770, -3), (640, 850, 11)]):
        hay_rack(x, y, rot, 14)
    for x, y in [(548, 812), (552, 818), (672, 786)]:
        haystack(x, y, random.uniform(0.8, 1.1))
    fence([(fx - 28, fy + 24), (fx, fy + 30), (fx + 26, fy + 26), (fx + 34, fy + 8)])
    bridge(574, 789, 62)
    for x, y, f, t in [(fx - 2, fy - 16, 2.2, "tunic_g"), (fx + 1, fy - 18, 2.6, "dress"), (fx - 6, fy - 14, 1.0, "tunic_y")]:
        villager(x, y, f, t, "cloth2" if t == "dress" else None, t == "dress")
    cart(fx - 16, fy - 10, 60)
    return [((fx + 6, fy - 4), 9), ((fx - 12, fy + 10), 9)]


def dress_gamlagarden():
    cx, cy = A.COURTYARD["c"]
    w, h = A.COURTYARD["w"], A.COURTYARD["h"]
    corners = [(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2), (cx - w / 2, cy - h / 2)]
    stone_wall(corners, 1.1, gaps=[((cx - w / 2, cy - 4), 4.5), ((cx + 8, cy - h / 2), 3.0), ((cx + w / 2, cy + 14), 5.0)])
    manor_ruin(cx + 18, cy + 10, 0)
    stone_well(cx - 6, cy + 2)
    cart(cx - 14, cy - 12, 25)
    for x, y in [(cx + 4, cy + 18), (cx - 22, cy + 16), (cx + 30, cy - 18)]:
        place(birch_mesh(int(x * 3) % 7 + 1), (x, y, gz(x, y) - 0.1), random.uniform(0, math.tau), 0.9)
    wraith((cx + 10, cy - 4), gz(cx + 10, cy - 4), math.radians(200), scale=0.95)
    return [((cx + 18, cy + 10), 11), ((cx - 6, cy + 2), 2.5)]


def along(pts, start, dist):
    """Point and direction `dist` metres along a polyline from the vertex nearest `start`."""
    i0 = min(range(len(pts)), key=lambda i: math.hypot(pts[i][0] - start[0], pts[i][1] - start[1]))
    acc = 0.0
    for i in range(i0, len(pts) - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        seg = math.hypot(x1 - x0, y1 - y0)
        if acc + seg >= dist:
            t = (dist - acc) / seg
            return (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t), ((x1 - x0) / seg, (y1 - y0) / seg)
        acc += seg
    (x0, y0), (x1, y1) = pts[-2], pts[-1]
    seg = math.hypot(x1 - x0, y1 - y0)
    return (x1, y1), ((x1 - x0) / seg, (y1 - y0) / seg)


def dress_dimskogen():
    pts = A.PATHS["ds_path"][0]
    hero = [s for s in A.SHOTS if s[0] == "dimskogen"][0][3]
    out = []
    for k, d in enumerate((-8, 6, 18, 30, 42, 54)):
        if d < 0:
            continue
        (x, y), (dx, dy) = along(pts, hero, d)
        side = 1 if k % 2 else -1
        lx, ly = x - dy * 2.8 * side, y + dx * 2.8 * side
        lantern_post(lx, ly, math.degrees(math.atan2(dy, dx)) + (90 if side > 0 else -90))
        out.append(((lx, ly), 1.6))
    for d, lat, ant in ((15, 2.5, True), (24, -3.0, False), (33, 3.5, False)):
        (x, y), (dx, dy) = along(pts, hero, d)
        wx, wy = x - dy * lat, y + dx * lat
        wraith((wx, wy), gz(wx, wy), math.atan2(-dy, -dx) - math.pi / 2, antlers=ant)
        out.append(((wx, wy), 2.5))
    for d, lat, z in ((8, 1.5, 1.6), (12, -2, 2.2), (20, 0.5, 1.4), (28, -1.5, 2.6), (36, 2.0, 1.8)):
        (x, y), (dx, dy) = along(pts, hero, d)
        wisp((x - dy * lat, y + dx * lat, gz(x, y) + z))
    return out


def dress_dimmyren():
    boardwalk(A.PATHS["dm_boardwalk"][0], A.BOG_WATER)
    sx, sy = -481, 330
    stag((sx, sy), max(gz(sx, sy), A.BOG_WATER), math.radians(160))
    rs = place(runestone_mesh(True), (-500, 322, max(gz(-500, 322), A.BOG_WATER) - 0.5), math.radians(30))
    rs.rotation_euler.x = math.radians(16)
    add_point((-499, 321, A.BOG_WATER + 1.2), None, 0, color="#8fd8ff", power=120, radius=0.3)
    for (x, y, z) in [(-475, 305, 1.4), (-462, 318, 2.0), (-488, 296, 1.7), (-452, 290, 2.4), (-470, 285, 1.2), (-495, 332, 2.1)]:
        wisp((x, y, max(gz(x, y), A.BOG_WATER) + z))
    wraith((-515, 296), max(gz(-515, 296), A.BOG_WATER), math.radians(-40), scale=0.95)
    return [((sx, sy), 5), ((-500, 322), 2)]


def dress_odeskogen():
    cx, cy = A.ARENA["c"]
    giant_tree(cx, cy)
    for k in range(8):
        a = k * math.tau / 8
        x, y = cx + math.cos(a) * 24, cy + math.sin(a) * 24
        place(runestone_mesh(True), (x, y, gz(x, y) - 0.1), a + math.pi / 2)
        add_point((x, y, gz(x, y) + 1.4), None, 0, color="#8fd8ff", power=60, radius=0.3)
    boss = wraith((cx + 8, cy + 8), gz(cx + 8, cy + 8), math.radians(-45), antlers=True, scale=3.0)
    for k in range(3):
        a = k * 2.1 + 0.4
        wraith((cx + math.cos(a) * 16, cy + math.sin(a) * 16), gz(cx + math.cos(a) * 16, cy + math.sin(a) * 16), a + math.pi, scale=0.9)
    for k in range(10):
        a = k * 0.63
        wisp((cx + math.cos(a) * 10, cy + math.sin(a) * 12, gz(cx, cy) + 2 + (k % 3)))
    return [((cx, cy), 9)]


# ------------------------------------------------------------------ world, lighting
def setup_world_act(mode, cx, cy):
    w = bpy.data.worlds.new("World")
    scene.world = w
    safe(w, "use_nodes", True)
    nt = w.node_tree
    bg = nt.nodes.get("Background") or nt.nodes.new("ShaderNodeBackground")
    out = nt.nodes.get("World Output") or nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    sun_d = bpy.data.lights.new("Sun", "SUN")
    sun = bpy.data.objects.new("Sun", sun_d)
    COLL.objects.link(sun)
    if mode == "day":
        bg.inputs["Color"].default_value = lin("#A9C6E6")
        bg.inputs["Strength"].default_value = 1.1
        sun_d.energy, sun_d.color, sun_d.angle = 4.2, lin("#FFE4BC")[:3], math.radians(2.5)
        sun.rotation_euler = (math.radians(52), 0, math.radians(-120))
        sky_for_camera(nt, bg, out, [(0.0, "#DCE5EC"), (0.08, "#C4D7EA"), (0.35, "#93B7E0"), (0.8, "#6C9AD3")], clouds=True)
        haze_box(0.0028, "#DDE8F2")
    elif mode == "golden":
        bg.inputs["Color"].default_value = lin("#C9AE92")
        bg.inputs["Strength"].default_value = 0.85
        bg.inputs["Color"].default_value = lin("#BCB9B2")
        sun_d.energy, sun_d.color, sun_d.angle = 3.4, lin("#FFD9AE")[:3], math.radians(1.5)
        sun.rotation_euler = (math.radians(70), 0, math.radians(-70))
        sky_for_camera(nt, bg, out, [(0.0, "#F2D2AE"), (0.12, "#E3C4A2"), (0.45, "#A3B3CB"), (0.9, "#6886BA")], clouds=True)
        haze_box(0.004, "#EED8BE", 0.4)
    elif mode == "fog":
        bg.inputs["Color"].default_value = lin("#98A5B2")
        bg.inputs["Strength"].default_value = 0.9
        sun_d.energy, sun_d.color, sun_d.angle = 1.1, lin("#C4D2E0")[:3], math.radians(8)
        sun.rotation_euler = (math.radians(40), 0, math.radians(-120))
        sky_for_camera(nt, bg, out, [(0.0, "#A9B4BE"), (0.25, "#9AA6B2"), (0.8, "#7F8B98")], clouds=False)
        haze_box(0.028, "#C3CDD6", 0.3)
        ground_fog()
    else:  # dusk
        bg.inputs["Color"].default_value = lin("#8A86A2")
        sun_d.energy, sun_d.color, sun_d.angle = 1.6, lin("#E8A894")[:3], math.radians(6)
        sun.rotation_euler = (math.radians(80), 0, math.radians(-100))
        sky_for_camera(nt, bg, out, [(0.0, "#C79CA0"), (0.15, "#8A7394"), (0.5, "#4C4A6E"), (0.9, "#262842")], clouds=False)
        haze_box(0.024, "#A3A0BA", 0.3)
        ground_fog()
        gf = bpy.data.objects.get("GroundFog")
        if gf:
            gf.active_material.node_tree.nodes["Principled Volume"].inputs["Color"].default_value = lin("#A6A2BC")
    for nm in ("Haze", "GroundFog"):
        ob = bpy.data.objects.get(nm)
        if ob:
            ob.location.x, ob.location.y = cx, cy
            ob.location.z += gz(cx, cy)


# ------------------------------------------------------------------ population
def populate_act(cx, cy, shot, mode, low, clear):
    rng_np = np.random.default_rng(11)
    pines = [pine_mesh(s) for s in range(6)]
    spruces = [tall_spruce_mesh(150 + s) for s in range(5)]
    birches = [birch_mesh(170 + s) for s in range(4)]
    deads = [dead_tree_mesh(190 + s, dark=(mode == "dusk")) for s in range(4)]
    saplings = [spruce_mesh(100 + s) for s in range(4)]
    boulders = [boulder_mesh(200 + s) for s in range(8)]
    bigs = [boulder_mesh(300 + s, big=True) for s in range(4)]
    shrubs_b = [shrub_mesh(410 + s, "berryblue") for s in range(3)]
    shrubs = [shrub_mesh(420 + s, None) for s in range(3)]
    lichens = [lichen_mesh(600 + s) for s in range(3)]
    grasses = [grass_mesh(700 + s) for s in range(4)]
    tall = [grass_mesh(720 + s, tall=True) for s in range(3)]
    logs = [log_mesh(800 + s, 6) for s in range(2)]

    def pick_tree(k, x, y):
        if k == 1:
            return random.choice(spruces), 1.0
        if k == 2:
            return random.choice(birches), 1.0
        if k == 3:
            return random.choice(deads), 1.0
        return random.choice(pines)[0], 1.0

    def blocked(x, y, pad=0.0):
        return any(math.hypot(x - c[0], y - c[1]) < r + pad for c, r in clear)

    R = 140.0
    cell = 3.8
    gxs = np.arange(cx - R, cx + R, cell)
    GX, GY = np.meshgrid(gxs, np.arange(cy - R, cy + R, cell))
    GX = GX + rng_np.uniform(0, cell, GX.shape)
    GY = GY + rng_np.uniform(0, cell, GY.shape)
    m = A.zone_masks(GX, GY)
    wk = A.walkable(GX, GY, m)
    dn = A.density(GX, GY, m)
    kd = A.tree_kind(GX, GY, m)
    lk, tn, bw = A.water(GX, GY)
    rnd = rng_np.uniform(0, 1, GX.shape)
    pdist = A.path_dist(GX, GY)
    near = 0
    for x, y, w_, d_, k, r_, l_, t_, b_, pd in zip(GX.ravel(), GY.ravel(), wk.ravel(), dn.ravel(), kd.ravel(), rnd.ravel(), lk.ravel(), tn.ravel(), bw.ravel(), pdist.ravel()):
        if l_ or t_ or b_ or blocked(x, y, 2.0) or pd < 1.6:
            continue
        if w_ and d_ > 0.62 and d_ * 0.92 <= r_ < d_ * 1.35 and k != 3:
            TREES.append(place(random.choice(saplings), (x + 1.3, y - 0.8, gz(x, y) - 0.05), random.uniform(0, math.tau), random.uniform(2.2, 3.6)))
            continue
        if w_ and r_ < d_ * 0.92:
            me, s_ = pick_tree(k, x, y)
        elif (not w_) and r_ < 0.8:
            me, s_ = (random.choice(spruces), 1.0) if (k == 1 or random.random() < 0.35) else pick_tree(k, x, y)
            if random.random() < 0.12:
                place(random.choice(bigs), (x, y, gz(x, y) - 0.6), random.uniform(0, math.tau), random.uniform(1.2, 2.0))
        else:
            continue
        TREES.append(place(me, (x, y, gz(x, y) - 0.15), random.uniform(0, math.tau), s_ * random.uniform(0.85, 1.15)))
        near += 1
    # distant forest for low cameras
    far = 0
    if low:
        R2 = 470.0
        c2 = 9.0
        FX, FY = np.meshgrid(np.arange(cx - R2, cx + R2, c2), np.arange(cy - R2, cy + R2, c2))
        FX = FX + rng_np.uniform(0, c2, FX.shape)
        FY = FY + rng_np.uniform(0, c2, FY.shape)
        ring = (np.abs(FX - cx) > R) | (np.abs(FY - cy) > R)
        FX, FY = FX[ring], FY[ring]
        fm = A.zone_masks(FX, FY)
        fw = A.walkable(FX, FY, fm)
        fd = A.density(FX, FY, fm)
        fk = A.tree_kind(FX, FY, fm)
        flk, ftn, fbw = A.water(FX, FY)
        fr = rng_np.uniform(0, 1, FX.shape)
        for x, y, w_, d_, k, r_, a_, b_, c_ in zip(FX, FY, fw, fd, fk, fr, flk, ftn, fbw):
            if a_ or b_ or c_:
                continue
            if (w_ and r_ < d_ * 1.6) or ((not w_) and r_ < 0.9):
                me, s_ = pick_tree(k if w_ else (1 if random.random() < 0.4 else k), x, y)
                place(me, (x, y, gz(x, y) - 0.15), random.uniform(0, math.tau), random.uniform(0.95, 1.25))
                far += 1
    # boulders, logs, saplings
    BX, BY = np.meshgrid(np.arange(cx - 110, cx + 110, 7.0), np.arange(cy - 110, cy + 110, 7.0))
    BX = BX + rng_np.uniform(0, 7, BX.shape)
    BY = BY + rng_np.uniform(0, 7, BY.shape)
    bm_ = A.zone_masks(BX, BY)
    bwk = A.walkable(BX, BY, bm_)
    bgm = A.ground_masks(BX, BY, bm_)
    blk, btn, bbw = A.water(BX, BY)
    br = rng_np.uniform(0, 1, BX.shape)
    for x, y, w_, pth, mead, yard, pav, fld, r_, a_, b_, c_ in zip(BX.ravel(), BY.ravel(), bwk.ravel(), bgm["path"].ravel(), bgm["meadow"].ravel(),
                                                                    bgm["yard"].ravel(), bgm["paving"].ravel(), bgm["fieldbase"].ravel(), br.ravel(), blk.ravel(), btn.ravel(), bbw.ravel()):
        if (not w_) or pth > 0.05 or yard > 0.3 or pav > 0.3 or fld > 0.3 or a_ or b_ or c_ or blocked(x, y, 2.5) or A.in_poly(np.array([x]), np.array([y]), A.ZONES["town"]["smooth"])[0]:
            continue
        if r_ < 0.11:
            place(random.choice(boulders), (x, y, gz(x, y) - 0.25), random.uniform(0, math.tau), random.uniform(0.6, 1.4))
        elif r_ < 0.14 and mead < 0.5:
            place(random.choice(bigs), (x, y, gz(x, y) - 0.5), random.uniform(0, math.tau), random.uniform(0.9, 1.5))
        elif r_ < 0.2 and mead < 0.5 and mode != "golden":
            TREES.append(place(random.choice(saplings), (x, y, gz(x, y) - 0.05), random.uniform(0, math.tau), random.uniform(0.8, 1.3)))
        elif r_ < 0.215:
            place(random.choice(logs), (x, y, gz(x, y) - 0.1), random.uniform(0, math.tau))
    # ground cover close to the camera target
    GR = 62.0
    QX, QY = np.meshgrid(np.arange(cx - GR, cx + GR, 0.95), np.arange(cy - GR, cy + GR, 0.95))
    QX = QX + rng_np.uniform(0, 0.95, QX.shape)
    QY = QY + rng_np.uniform(0, 0.95, QY.shape)
    qm = A.zone_masks(QX, QY)
    qw = A.walkable(QX, QY, qm)
    G = A.ground_masks(QX, QY, qm)
    qlk, qtn, qbw = A.water(QX, QY)
    qr = rng_np.uniform(0, 1, QX.shape)
    qn = A.fbm(QX / 9.0, QY / 9.0, 2, 33)
    cover = 0
    for i, (x, y) in enumerate(zip(QX.ravel(), QY.ravel())):
        if not qw.flat[i] or qlk.flat[i] or qtn.flat[i] or qbw.flat[i] or G["path"].flat[i] > 0.2 or G["paving"].flat[i] > 0.5 or blocked(x, y, 0.5):
            continue
        r_ = qr.flat[i]
        if G["yard"].flat[i] > 0.5:
            me = random.choice(grasses) if r_ < 0.03 else None
        elif G["field"].flat[i] > 0.5:
            me = random.choice(tall) if r_ < 0.25 else None
        elif G["fieldbase"].flat[i] > 0.5:
            me = None
        elif G["meadow"].flat[i] > 0.5:
            me = random.choice(grasses) if r_ < 0.12 else (random.choice(tall) if r_ < 0.14 else (random.choice(shrubs) if r_ < 0.16 else None))
        elif G["bog"].flat[i] > 0.5:
            me = random.choice(tall + grasses) if r_ < 0.32 else None
        else:
            if qn.flat[i] > 0.25 and mode != "dusk":
                me = random.choice(shrubs_b if r_ < 0.12 else shrubs) if r_ < 0.42 else None
            elif r_ < 0.18:
                me = random.choice(shrubs + grasses + lichens)
            else:
                me = None
        if me is None:
            continue
        place(me, (x, y, gz(x, y) - 0.03), random.uniform(0, math.tau), random.uniform(0.9, 1.3))
        cover += 1
    # low grass tufts in the worn edges of roads and trails, and pebbles on and beside them. Own random numbers,
    # so everything above keeps its layout.
    er = np.random.default_rng(4242)
    n = int((2 * GR) ** 2 * 3.0)
    EX, EY = cx + er.uniform(-GR, GR, n), cy + er.uniform(-GR, GR, n)
    ed = A.path_dist(EX, EY)  # half-widths from the centre line, 1 at the nominal edge
    keep = ed < 1.8
    EX, EY, ed = EX[keep], EY[keep], ed[keep]
    eg = A.ground_masks(EX, EY)
    elk, etn, ebw = A.water(EX, EY)
    er_r, er_rot, er_s, er_k = (er.uniform(0, 1, len(EX)) for _ in range(4))
    pebbles = boulders[:3]
    edge = 0
    for i, (x, y, d) in enumerate(zip(EX, EY, ed)):
        if elk[i] or etn[i] or ebw[i] or eg["yard"][i] > 0.5 or eg["paving"][i] > 0.5 or eg["fieldbase"][i] > 0.3 or blocked(x, y, 0.4):
            continue
        r_ = er_r[i]
        if 0.75 < d < 1.7 and r_ < A.smoothstep(0.75, 1.3, d) * 0.65:
            place(grasses[int(er_k[i] * len(grasses))], (x, y, gz(x, y) - 0.03), er_rot[i] * math.tau, 0.45 + 0.4 * er_s[i])
        elif d < 1.35 and r_ > 0.85:
            place(pebbles[int(er_k[i] * len(pebbles))], (x, y, gz(x, y) - 0.02), er_rot[i] * math.tau, 0.04 + 0.05 * er_s[i])
        else:
            continue
        edge += 1
    print("populate near", near, "far", far, "cover", cover, "path edges", edge)


def cull_act(cam, subjects, wide=True):
    bpy.context.view_layer.update()
    cpos = cam.matrix_world.translation.copy()
    hidden = 0
    for t in TREES:
        if t.hide_render:
            continue
        base = t.matrix_world.translation
        hgt, rad = t.dimensions.z, max(t.dimensions.x, t.dimensions.y) / 2
        hide = (Vector((base.x - cpos.x, base.y - cpos.y))).length < (15.0 if not wide else 10.0)
        for s in subjects:
            a2, b2 = Vector((cpos.x, cpos.y)), Vector((s.x, s.y))
            ab = b2 - a2
            tt = max(0.0, min(1.0, (Vector((base.x, base.y)) - a2).dot(ab) / max(ab.length_squared, 1e-6)))
            dd = (Vector((base.x, base.y)) - (a2 + ab * tt)).length
            line_z = cpos.z + (s.z - cpos.z) * tt
            if 0.02 < tt < 0.98 and dd < rad + 2.5 and base.z + hgt > line_z - 1.0:
                hide = True
        if hide:
            t.hide_render = True
            if t.name in ROOTS:
                ROOTS[t.name].hide_render = True
            hidden += 1
    for ob in scene.objects:
        if ob.name.startswith("Wisp") and (ob.matrix_world.translation - cpos).length < 7.0:
            ob.hide_render = True
            for c in ob.children:
                c.hide_render = True
    if wide:
        cull_occluders(cam, subjects)
    print("cull_act hid", hidden)


# ------------------------------------------------------------------ shots
def run_act(shot_id):
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    TREES.clear()
    ROOTS.clear()
    global rng
    rng = random.Random(7)
    random.seed(21)
    sh = [s for s in A.SHOTS if s[0] == shot_id][0]
    _, zone, label_, (cx, cy), yaw, pitch, dist = sh
    mode = A.ZONES[zone]["mood"]
    setup_render()
    setup_world_act(mode, cx, cy)
    for mat in (MAT, MAT_GROUND):
        gnode = mat.node_tree.nodes["Grade"]
        gnode.inputs["Saturation"].default_value = {"day": 1.0, "golden": 1.0, "fog": 0.62, "dusk": 0.55}[mode]
        gnode.inputs["Value"].default_value = {"day": 1.0, "golden": 1.0, "fog": 0.92, "dusk": 0.9}[mode]
    low = pitch < 30
    grid_mesh("Terrain", cx, cy, 100, 0.7)
    grid_mesh("MidGround", cx, cy, 160, 2.0, hole=99, drop=0.04)
    grid_mesh("OuterGround", cx, cy, 650, 8.0, hole=158, drop=0.08)
    waters = add_waters(cx, cy, 160)
    clear = []
    if zone == "town":
        clear += dress_town()
    elif zone == "storskogen":
        clear += dress_storskogen(shot_id)
    elif zone == "harddalen":
        clear += dress_harddalen()
    elif zone == "gamlagarden":
        clear += dress_gamlagarden()
    elif zone == "dimskogen":
        clear += dress_dimskogen()
    elif zone == "dimmyren":
        clear += dress_dimmyren()
    elif zone == "odeskogen":
        clear += dress_odeskogen()
    # the hero
    px, py = cx, cy
    attacking = shot_id == "odeskogen"
    hero_dir = {"tallmo": (-22, 26), "angen": (1, 0.3), "tatskogen": (-0.6, 0.8), "utsikten": (-0.6, -0.8), "trollgrytan": (-1, -0.2),
                "harddalen": (0.7, 0.6), "gamlagarden": (0.9, 0.4), "dimskogen": (-0.9, -0.2), "dimmyren": (0.2, -1), "odeskogen": (-0.6, -0.5)}[shot_id]
    face = math.atan2(hero_dir[1], hero_dir[0]) - math.pi / 2
    clear.append(((px, py), 3.0))
    hz = gz(px, py)
    if zone == "dimmyren":
        hz = max(hz, A.BOG_WATER) + 0.3
    player((px, py), hz, face, "attack" if attacking else "walk")
    if attacking:
        swing_arc((px, py), gz(px, py), face)
    if mode in ("fog", "dusk"):
        add_point((px, py, gz(px, py) + 3.2), None, 0, color="#FFE2B8", power=320, radius=1.0)
    populate_act(cx, cy, shot_id, mode, low, clear)
    shift = {"trollgrytan": (-14, -2, -3.0), "harddalen": (8, 5, 0), "gamlagarden": (6, 5, 0), "odeskogen": (-2.5, -2.5, 1.2),
             "dimmyren": (0, 1, 0.3), "utsikten": (0, 0, 0.6)}.get(shot_id, (0, 0, 0))
    cam = orbit_camera((px + shift[0], py + shift[1], hz + 1.4 + shift[2]), yaw, pitch, dist)
    f = face + math.pi / 2
    hud = {"shot": shot_id, "res": RES, "mode": mode, "yaw": yaw, "pitch": pitch, "facing": face, "player_world": [px, py],
           "zone_name": A.ZONES[zone]["name"], "attacking": attacking, "mm_scale": 1.6}
    aim = (px + math.cos(f) * 5.0, py + math.sin(f) * 5.0)
    hud["cursor"] = screen(cam, (aim[0], aim[1], gz(*aim) + 0.3))
    subjects = [Vector((px, py, gz(px, py) + 1.0))]
    if attacking:
        bx, by = A.ARENA["c"][0] + 8, A.ARENA["c"][1] + 8
        hud["cursor"] = screen(cam, (bx, by, gz(bx, by) + 4.0))
        hud["damage"] = screen(cam, (bx + 2.0, by - 1.0, gz(bx, by) + 6.5))
        hud["target_name"] = "Den hornkrönte"
        subjects.append(Vector((bx, by, gz(bx, by) + 4.0)))
    cull_act(cam, subjects, wide=shot_id not in ("tatskogen", "dimskogen"))
    near_paths = []
    for name, (pts, w, kind) in A.PATHS.items():
        sub = [[round(x, 1), round(y, 1)] for x, y in pts if math.hypot(x - px, y - py) < 170]
        if len(sub) > 1:
            near_paths.append(sub)
    hud["paths"] = near_paths
    hud["waters"] = waters
    hud["bog"] = [A.BOG["c"][0], A.BOG["c"][1], 150] if zone == "dimmyren" else None
    scene.render.filepath = os.path.join(OUT, shot_id + ".png")
    if QUALITY != "json":
        bpy.ops.render.render(write_still=True)
    with open(os.path.join(OUT, shot_id + ".json"), "w") as fh:
        json.dump(hud, fh)
    print("RENDERED", shot_id)


for s_ in SHOTS:
    run_act(s_)
