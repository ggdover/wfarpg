"""How each rig of the run portfolio deforms the mesh over some runs, for README.md's table: the volume the mesh keeps
(against the figure as made, standing), the edges' stretch and squash (the worst in a thousand), and the worst
triangle's area, at the worst moment of each run, for each model and rig, and then for each rig over the models.

    blender -b run_portfolio.blend -P measure_rigs.py [-- athletic,snappy]

It reads the figures and actions in run_portfolio.blend (make_runs.py), so build that first.
"""
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_runs  # noqa: E402
import rigs  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
styles = args[0].split(",") if args else ["athletic", "snappy"]
scene = bpy.context.scene
dg = bpy.context.evaluated_depsgraph_get()


def volume(co, polys):
    """The volume a closed mesh holds (by its faces' signed tetrahedra from the origin)."""
    v = 0.0
    for p in polys:
        a = co[p[0]]
        for i in range(1, len(p) - 1):
            v += a.dot(co[p[i]].cross(co[p[i + 1]])) / 6.0
    return v


def areas(co, tris):
    return [((co[b] - co[a]).cross(co[c] - co[a])).length / 2 for a, b, c in tris]


results = {}
for style in styles:
    for m, _label in make_runs.MODELS:
        for v, _vlabel, _text in rigs.VARIANTS:
            rig, mesh = bpy.data.objects[f"{m}_{v}_rig"], bpy.data.objects[f"{m}_{v}"]
            act = bpy.data.actions[style + ("_" + v if v in ("helpers", "cloth") else "")]
            make_runs.use(rig, act)
            if v == "corrective":  # its shapes, as the run turns them
                make_runs.use(mesh.data.shape_keys, bpy.data.actions[style + "_shapes"])
            me = mesh.data
            rest = [x.co.copy() for x in me.vertices]
            polys = [list(p.vertices) for p in me.polygons]
            edges = [tuple(e.vertices) for e in me.edges]
            me.calc_loop_triangles()
            tris = [tuple(t.vertices) for t in me.loop_triangles]
            rest_len = [(rest[a] - rest[b]).length for a, b in edges]
            rest_area = areas(rest, tris)
            v0 = volume(rest, polys)
            vol_lo, vol_hi, stretch, squash, area_lo = 9.0, 0.0, 0.0, 9.0, 9.0
            for f in range(0, int(act.frame_range[1]), 2):
                scene.frame_set(f)
                ev = mesh.evaluated_get(dg)
                em = ev.to_mesh()
                co = [x.co.copy() for x in em.vertices]
                ev.to_mesh_clear()
                r = volume(co, polys) / v0
                vol_lo, vol_hi = min(vol_lo, r), max(vol_hi, r)
                ratios = sorted((co[a] - co[b]).length / n for (a, b), n in zip(edges, rest_len) if n > 1e-5)
                stretch = max(stretch, ratios[int(len(ratios) * 0.999)])
                squash = min(squash, ratios[int(len(ratios) * 0.001)])
                ratio = sorted(a / ra for a, ra in zip(areas(co, tris), rest_area) if ra > 1e-7)
                area_lo = min(area_lo, ratio[int(len(ratio) * 0.001)])
            results[(style, m, v)] = (vol_lo, vol_hi, stretch, squash, area_lo)
            print(f"{style:9s} {m:12s} {v:10s} volume {vol_lo:.3f}..{vol_hi:.3f}  edges x{squash:.2f}..x{stretch:.2f}  "
                  f"worst triangle x{area_lo:.2f}")
print()
for v, label, _text in rigs.VARIANTS:  # each rig over the models and runs, as README.md's table has it
    rows = [results[(s, m, v)] for s in styles for m, _ in make_runs.MODELS]
    per_model = [max(results[(s, m, v)][2] for s in styles) for m, _ in make_runs.MODELS]
    kept = [min(results[(s, m, v)][0] for s in styles) for m, _ in make_runs.MODELS]
    print(f"{label:18s} edges stretch to {min(per_model):.1f}-{max(per_model):.1f}x, volume kept at least "
          f"{min(kept) * 100:.0f}-{max(kept) * 100:.0f}%, worst triangle x{min(r[4] for r in rows):.2f}")
