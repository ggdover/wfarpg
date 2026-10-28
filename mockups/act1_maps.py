"""Bake Act 1 map layers in Blender (numpy): shaded terrain + contours, tree points and a height profile.
blender -b --factory-startup --python act1_maps.py -- <outdir>
"""
import sys, os, json, math, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import bpy
import act1_world as A

OUT = os.path.abspath(sys.argv[sys.argv.index("--") + 1]) if "--" in sys.argv[:-1] else os.path.join(os.path.dirname(os.path.abspath(__file__)), "build", "act1")  # Blender on Windows saves a relative path under C:\
os.makedirs(OUT, exist_ok=True)


def hexc(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], dtype=np.float32)


C = {k: hexc(v) for k, v in dict(
    outside="#1f211d", outside2="#2a2c26", floor="#5d7838", floor2="#6c8740", meadow="#a7ae62", meadow2="#b9b46a",
    field1="#c0aa5c", field2="#8f8f48", yard="#8a7452", paving="#8e8b82", bog="#4c5233", ash="#3b3631",
    water="#3d6c86", water_deep="#2b546c", shore="#9aa356", dark="#40523a", square="#ba9664").items()}


def save_png(rgb, path):
    h, w, _ = rgb.shape
    img = bpy.data.images.new(os.path.basename(path), width=w, height=h, alpha=False)
    px = np.ones((h, w, 4), dtype=np.float32)
    px[..., :3] = np.clip(rgb, 0, 1)
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def mix(a, b, t):
    return a * (1 - t[..., None]) + b * t[..., None]


def bake(x0, x1, y0, y1, res, name, contours=True):
    t = time.time()
    xs = np.arange(x0, x1, res) + res / 2
    ys = np.arange(y0, y1, res) + res / 2
    X, Y = np.meshgrid(xs, ys)
    masks = A.zone_masks(X, Y)
    walk = A.walkable(X, Y, masks)
    H = A.height(X, Y, masks)
    G = A.ground_masks(X, Y, masks)
    lake, tarn, bogw = A.water(X, Y)
    dens = A.density(X, Y, masks)
    n = A.fbm(X / 9.0, Y / 9.0, 2, 3)
    col = mix(np.broadcast_to(C["floor"], X.shape + (3,)), np.broadcast_to(C["floor2"], X.shape + (3,)), (n * 0.5 + 0.5))
    col = mix(col, np.broadcast_to(C["dark"], col.shape), G["darkfloor"] * 0.6)
    col = mix(col, mix(np.broadcast_to(C["meadow"], col.shape), np.broadcast_to(C["meadow2"], col.shape), (n * 0.5 + 0.5)), G["meadow"])
    col = mix(col, np.broadcast_to(C["field2"], col.shape), G["fieldbase"])
    col = mix(col, np.broadcast_to(C["field1"], col.shape), G["field"])
    col = mix(col, np.broadcast_to(C["yard"], col.shape), G["yard"])
    # Tallmo's square is worn ground like the roads, in the colour act1_blueprint draws them
    col = mix(col, np.broadcast_to(C["square"], col.shape), 1 - A.smoothstep(0.85, 1.15, A.square_dist(X, Y)))
    col = mix(col, np.broadcast_to(C["paving"], col.shape), G["paving"])
    col = mix(col, np.broadcast_to(C["bog"], col.shape), G["bog"])
    col = mix(col, np.broadcast_to(C["ash"], col.shape), G["ash"] * 0.85)
    col = mix(col, np.broadcast_to(C["shore"], col.shape), G["shore"] * 0.6)
    # hillshade (light from the north-west)
    gy, gx = np.gradient(H, res)
    nx_, ny_, nz_ = -gx, -gy, np.ones_like(H)
    ln = np.sqrt(nx_ ** 2 + ny_ ** 2 + nz_ ** 2)
    L = np.array([-0.5, 0.5, 0.7])
    L = L / np.linalg.norm(L)
    shade = (nx_ * L[0] + ny_ * L[1] + nz_ * L[2]) / ln
    col = col * (0.62 + 0.55 * shade)[..., None]
    # water
    wat = lake | tarn | (bogw & (G["bog"] > 0.5))
    col = np.where(wat[..., None], mix(np.broadcast_to(C["water"], col.shape), np.broadcast_to(C["water_deep"], col.shape), np.clip(-(H - H.max()) * 0, 0, 1)), col)
    # contours
    if contours:
        lv = np.floor(H / 2.0)
        edge = (np.abs(np.diff(lv, axis=0, prepend=lv[:1])) + np.abs(np.diff(lv, axis=1, prepend=lv[:, :1]))) > 0
        lv10 = np.floor(H / 10.0)
        edge10 = (np.abs(np.diff(lv10, axis=0, prepend=lv10[:1])) + np.abs(np.diff(lv10, axis=1, prepend=lv10[:, :1]))) > 0
        col = np.where((edge & walk & ~wat)[..., None], col * 0.78, col)
        col = np.where((edge10 & walk & ~wat)[..., None], col * 0.6, col)
    # outside the playable area
    tex = (A.fbm(X / 14.0, Y / 14.0, 3, 41) * 0.5 + 0.5)
    outside = mix(np.broadcast_to(C["outside"], col.shape), np.broadcast_to(C["outside2"], col.shape), tex)
    col = np.where(walk[..., None], col, outside)
    # fog zones get a pale wash
    fogz = (masks["dimskogen"] | masks["dimmyren"] | masks["odeskogen"]) & walk
    col = np.where(fogz[..., None], col * 0.82 + np.array([0.70, 0.75, 0.80]) * 0.18, col)
    save_png(col, os.path.join(OUT, name + ".png"))
    # tree points (jittered grid)
    cell = 5.0
    gxs = np.arange(x0, x1, cell)
    gys = np.arange(y0, y1, cell)
    TX, TY = np.meshgrid(gxs, gys)
    rngx = A._hash(np.floor(TX), np.floor(TY), 77)
    rngy = A._hash(np.floor(TX), np.floor(TY), 78)
    rnga = A._hash(np.floor(TX), np.floor(TY), 79)
    TX = TX + rngx * cell
    TY = TY + rngy * cell
    tm = A.zone_masks(TX, TY)
    tw = A.walkable(TX, TY, tm)
    td = A.density(TX, TY, tm)
    lk, tn, bw = A.water(TX, TY)
    keep = tw & (rnga < td) & ~lk & ~tn & ~bw
    kind = A.tree_kind(TX, TY, tm)
    trees = [[round(float(a), 1), round(float(b), 1), int(k)] for a, b, k in zip(TX[keep], TY[keep], kind[keep])]
    # forest wall just outside the playable area
    border = (~tw) & (A.walkable(TX + 9, TY, tm) | A.walkable(TX - 9, TY, tm) | A.walkable(TX, TY + 9, tm) | A.walkable(TX, TY - 9, tm)) & (rnga < 0.85)
    wall = [[round(float(a), 1), round(float(b), 1), int(k)] for a, b, k in zip(TX[border], TY[border], kind[border])]
    info = dict(x0=x0, x1=x1, y0=y0, y1=y1, res=res, w=int(len(xs)), h=int(len(ys)), trees=trees, wall=wall,
                hmin=float(H[walk].min()), hmax=float(H[walk].max()))
    with open(os.path.join(OUT, name + ".json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(info, fh)
    print(name, X.shape, "trees", len(trees), "wall", len(wall), "%.1fs" % (time.time() - t))
    return H, walk


bake(-1400, 990, -105, 1015, 1.5, "overview")
bake(-300, 470, -100, 640, 1.0, "storskogen")

# height profile across Storskogen: hollow -> esker -> hill
a, b = (-300.0, 372.0), (262.0, 474.0)
ts = np.linspace(0, 1, 600)
PX = a[0] + (b[0] - a[0]) * ts
PY = a[1] + (b[1] - a[1]) * ts
PH = A.height(PX, PY)
dist = np.hypot(PX - a[0], PY - a[1])
sl = np.degrees(np.arctan(np.abs(np.gradient(PH, dist))))
with open(os.path.join(OUT, "profile.json"), "w", encoding="utf-8", newline="\n") as fh:
    json.dump(dict(a=a, b=b, d=dist.round(2).tolist(), h=PH.round(2).tolist(), slope=sl.round(1).tolist()), fh)
# global slope stat for the legend
x = np.arange(-1400, 990, 2.0)
y = np.arange(-100, 1010, 2.0)
X, Y = np.meshgrid(x, y)
m = A.zone_masks(X, Y)
wk = A.walkable(X, Y, m)
HH = A.height(X, Y, m)
gy, gx = np.gradient(HH, 2.0)
slope = np.degrees(np.arctan(np.hypot(gx, gy)))
with open(os.path.join(OUT, "stats.json"), "w", encoding="utf-8", newline="\n") as fh:
    json.dump(dict(max_slope=float(slope[wk].max()), p95=float(np.percentile(slope[wk], 95)),
                   walk_km2=float(wk.sum() * 4 / 1e6), zones={k: float(v.sum() * 4 / 1e6) for k, v in m.items()}), fh)
print("done")
