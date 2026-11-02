"""Checks the runs (runs.py) over a cycle each, on the hero portfolio's skeleton, and says what's wrong if anything is:

- a foot on the ground stays where it landed, as the ground moves back under it (to within a millimetre);
- no foot goes into the ground, and none hangs over it while it should be on it;
- no leg is asked to stretch past its length (99.9% of it), on the ground or in the air;
- nothing turns jerkily: no bone's turning speed jumps between one moment and the next, but the foot and leg as the
  foot lands, which is meant to (it plants);
- every foot lands heel first, its toes up (HEEL_FIRST), and is planted flat, heel and ball on the ground, for a good
  share of its time down (FLAT): the first runs seemed to run on their toes, and the user asked for the heel to plant
  first, the forefoot coming down just after;
- the hands don't cross the body's middle, nor rise much above the shoulders, nor go through the hips or thighs (or
  the tunic's skirt over them) as they swing past, nor the forearms into the chest, on Faceted 1500's mesh;
- no two runs look nearly the same: over a cycle (from the left foot landing) the knees, feet, elbows, hands, hips,
  chest and head of every two lie on average at least ALIKE apart, or their rhythms differ by a tenth or more;
- every run's numbers lie within the run editor's sliders (run_editor.py), so it shows each as made.

    blender -b --factory-startup -P check_runs.py [-- style,style]

It needs hero_portfolio.blend (make_heroes.py). Exits 1 if a run fails a check.
"""
import math
import os
import sys

import bpy
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_runs  # noqa: E402
import runs  # noqa: E402

SAMPLES = 480  # moments a cycle
HEEL_FIRST = -5.0  # degrees: a foot's pitch as it lands, at most (below 0, the toes up)
FLAT = 0.3  # the least share of its time on the ground a foot is flat on it
WATCH = ["pelvis", "spine_03", "head", "upperarm_l", "lowerarm_l", "hand_l", "thigh_l", "calf_l", "foot_l"]


def quat_rate(a, b):
    """The turn from a to b as a rotation vector, in double precision (a single-precision acos loses small angles)."""
    aw, ax, ay, az = a.w, -a.x, -a.y, -a.z
    dw = b.w * aw - b.x * ax - b.y * ay - b.z * az
    dx = b.w * ax + b.x * aw + b.y * az - b.z * ay
    dy = b.w * ay - b.x * az + b.y * aw + b.z * ax
    dz = b.w * az + b.x * ay - b.y * ax + b.z * aw
    if dw < 0:
        dw, dx, dy, dz = -dw, -dx, -dy, -dz
    n = math.sqrt(dx * dx + dy * dy + dz * dz)
    k = 2 * math.atan2(n, dw) / n if n > 1e-12 else 0.0
    return (dx * k, dy * k, dz * k)


def check(name, run, rest, still=False):
    """still: standing, the feet on the ground all along and not moving."""
    legs = rest.legs
    speed = 0.0 if still else runs.SPEED
    problems = []
    planted = {}
    reach = 0.0
    low = 9.0
    hover = 0.0
    turns = {b: [] for b in WATCH}
    hand_in, hand_top = 9.0, 0.0
    down = flat = 0
    shoulder = rest.head["upperarm_l"].z
    for i in range(SAMPLES):
        ph = i / SAMPLES
        P, off, stretch = run.pose(ph)
        M = runs.posed(rest, P, off)
        for b in WATCH:
            turns[b].append(M[b].to_quaternion())
        for s in "lr":
            reach = max(reach, stretch[s])
            p = (ph - (0.0 if s == "l" else 0.5)) % 1.0
            heel = M[f"foot_{s}"] @ (rest.inv[f"foot_{s}"] @ legs[s]["heel"])
            ball = M[f"foot_{s}"] @ (rest.inv[f"foot_{s}"] @ legs[s]["ball"])
            toe = M[f"ball_{s}"] @ (rest.inv[f"ball_{s}"] @ legs[s]["toe"])
            low = min(low, heel.z, toe.z)
            if still or p < run.D:
                theta = 0.0 if still else run.planted(s, p)[3]
                down += 1
                flat += abs(theta) < 1e-6
                point, base = (ball, 0.032) if theta >= 0 else (heel, 0.0)
                planted.setdefault((s, theta >= 0), []).append(point.y - speed * ph * run.T)
                hover = max(hover, abs(point.z - base - (legs[s]["ball"].z - 0.032 if theta >= 0 else 0.0)))
        for s, sign in (("l", 1), ("r", -1)):
            h = M[f"middle_01_{s}"].translation
            hand_in = min(hand_in, sign * (h.x - rest.hip_mid.x))
            hand_top = max(hand_top, h.z - shoulder)
    drift = max(max(v) - min(v) for v in planted.values())
    if drift > 0.001:
        problems.append(f"a planted foot slides {drift * 1000:.1f} mm")
    if low < -0.005:
        problems.append(f"a foot goes {-low * 1000:.0f} mm into the ground")
    if hover > 0.002:
        problems.append(f"a planted foot hangs {hover * 1000:.1f} mm off the ground")
    if reach > 0.999:
        problems.append(f"a leg is asked to stretch to {reach * 100:.1f}% of its length")
    land = {round((0.0 + k / 2) * SAMPLES) % SAMPLES for k in range(2)}
    jerk_worst = (0.0, "", 0.0)
    for b, qs in turns.items():
        w = [quat_rate(qs[i], qs[(i + 1) % SAMPLES]) for i in range(SAMPLES)]
        top = max(math.sqrt(sum(c * c for c in v)) for v in w) + 1e-9
        for i in range(SAMPLES):
            j = (i + 1) % SAMPLES
            near_landing = b in ("calf_l", "thigh_l", "foot_l") and any(abs(j - L) <= 2 or abs(j - L) >= SAMPLES - 2
                                                                        for L in land)
            jump = math.sqrt(sum((w[j][k] - w[i][k]) ** 2 for k in range(3))) / top
            if not near_landing and jump > jerk_worst[0]:
                jerk_worst = (jump, b, i / SAMPLES)
    if jerk_worst[0] > 0.25:
        problems.append(f"{jerk_worst[1]} turns jerkily at {jerk_worst[2]:.3f} of the cycle ({jerk_worst[0]:.2f})")
    if hand_in < 0.06:
        problems.append(f"a hand comes within {hand_in * 100:.0f} cm of the body's middle")
    if hand_top > 0.05:
        problems.append(f"a hand rises {hand_top * 100:.0f} cm above the shoulders")
    strike = 0.0 if still else run.planted("l", 0.0)[3]
    if not still and strike > HEEL_FIRST:
        problems.append(f"a foot lands {'flat' if abs(strike) < 1 else 'on its forefoot'}, not heel first "
                        f"(pitched {strike:+.0f}°)")
    if not still and flat < FLAT * down:
        problems.append(f"a foot is flat on the ground for only {flat / down:.0%} of its time down")
    print(f"{name:9s} {'ok' if not problems else 'FAILED'}: feet slide {drift * 1000:.2f} mm, "
          f"lowest {low * 1000:+.1f} mm, legs to {reach * 100:.1f}%, worst jerk {jerk_worst[0]:.2f}, "
          f"hands {hand_in * 100:.0f} cm from the middle"
          + ("" if still else f", heel first {-strike:.0f}°, flat {flat / down:.0%}")
          + "".join("\n    " + p for p in problems))
    return not problems


ALIKE = 0.04  # m: runs whose joints lie nearer than this on average, at the same moments, look alike


def alike(rest, styles, n=24):
    """Every two runs (styles: {name: Run}) with how far apart (m) their joints lie on average over a cycle, phase for
    phase, nearest first: [(distance, a, b)]."""
    joints = ["calf_l", "calf_r", "foot_l", "foot_r", "ball_l", "ball_r", "lowerarm_l", "lowerarm_r", "hand_l",
              "hand_r", "pelvis", "spine_03", "head"]
    at = {}
    for name, run in styles.items():
        at[name] = []
        for i in range(n):
            P, off, _ = run.pose(i / n)
            M = runs.posed(rest, P, off)
            at[name].append([M[j].translation.copy() for j in joints])
    pairs = []
    names = list(styles)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            d = math.sqrt(sum((p - q).length_squared for fa, fb in zip(at[a], at[b]) for p, q in zip(fa, fb))
                          / (n * len(joints)))
            pairs.append((d, a, b))
    return sorted(pairs)


def same_rhythm(a, b):
    """Whether two runs' steps a minute lie within a tenth of each other (further apart tells them apart too)."""
    fa, fb = (runs.STYLES[x].get("frames", runs.DEFAULTS["frames"]) for x in (a, b))
    return abs(fa - fb) < 0.1 * max(fa, fb)


def hands_through(rig, mesh, rest, styles, n=48):
    """The runs (styles: {name: Run}) whose hands go through the hips or thighs, the tunic's skirt over them too, or
    whose forearms or hands go into the chest or belly: the figure's mesh posed at n moments of a cycle, its faces on
    the hand and finger bones crossing those on the pelvis, the lowest spine bone and the thighs, or those on the
    forearms and hands crossing those on the upper spine. {name: how many of the n moments}."""
    names = {g.index: g.name for g in mesh.vertex_groups}
    part = {}
    for v in mesh.data.vertices:
        g = max(v.groups, key=lambda g: g.weight, default=None)
        bone = names.get(g.group, "") if g else ""
        if bone.startswith(("hand_", "index", "middle", "ring", "pinky", "thumb")):
            part[v.index] = "hand"
        elif bone.startswith("lowerarm"):
            part[v.index] = "forearm"
        elif bone.startswith(("pelvis", "spine_01", "thigh_")):
            part[v.index] = "hips"
        elif bone.startswith(("spine_02", "spine_03")):
            part[v.index] = "chest"
    faces = [list(p.vertices) for p in mesh.data.polygons]

    def of(*parts):
        return [f for f in faces if all(part.get(i) in parts for i in f)]
    hands, arms, body, chest = of("hand"), of("hand", "forearm"), of("hips"), of("chest")
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
    out = {}
    for name, run in styles.items():
        hits = 0
        for i in range(n):
            P, off, _ = run.pose(i / n)
            for b, (loc, q) in runs.bases(rest, runs.posed(rest, P, off)).items():
                pb = rig.pose.bones[b]
                pb.rotation_quaternion = q
                pb.location = loc if b == "pelvis" else (0.0, 0.0, 0.0)
            bpy.context.view_layer.update()
            co = [v.co.copy() for v in mesh.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]
            hits += bool(BVHTree.FromPolygons(co, hands).overlap(BVHTree.FromPolygons(co, body))
                         or BVHTree.FromPolygons(co, arms).overlap(BVHTree.FromPolygons(co, chest)))
        if hits:
            out[name] = hits
    return out


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    styles = args[0].split(",") if args else list(runs.STYLES)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    figs = make_runs.load_figures([make_runs.MODELS[1][0]])
    rig, mesh = figs[make_runs.MODELS[1][0]]
    make_runs.free_pelvis(rig)
    rest = make_runs.rest_of(rig, figs["Tripo20k"])
    good = [check(n, runs.Run(rest, runs.STYLES[n]), rest) for n in styles]
    good.append(check("stand", runs.Stand(rest), rest, still=True) if not args else True)
    through = hands_through(rig, mesh, rest, {n: runs.Run(rest, runs.STYLES[n]) for n in styles})
    print("arms     " + ("ok: no hand goes through the hips or thighs, no forearm into the chest" if not through else
                         "FAILED: a hand goes through the hips or thighs, or a forearm into the chest, in "
                         + ", ".join(f"{n} ({k} of 48)" for n, k in through.items())))
    good.append(not through)
    if not args:  # the runs against each other
        pairs = alike(rest, {n: runs.Run(rest, runs.STYLES[n]) for n in styles})
        bad = [(d, a, b) for d, a, b in pairs if d < ALIKE and same_rhythm(a, b)]
        d, a, b = bad[0] if bad else pairs[0]
        fine = not bad
        print(f"alike    {'ok' if fine else 'FAILED'}: the closest two" + (" at one rhythm" if bad else "")
              + f", {a} and {b}, {d * 100:.1f} cm apart on average"
              + ("" if d >= ALIKE or bad else ", but at another rhythm")
              + (f" ({len(bad)} pairs under {ALIKE * 100:.0f} cm)" if len(bad) > 1 else ""))
        good.append(fine)
        from run_editor import SETTING  # noqa: E402  (it imports this file, so not at the top)
        out = [f"{n} {name} {spec[name]:g} (the editor's {lo:g}-{hi:g})" for n in styles for spec in [runs.STYLES[n]]
               for name, (_label, lo, hi, _text) in SETTING.items() if not lo - 1e-9 <= spec[name] <= hi + 1e-9]
        print("ranges   " + ("ok: every run's numbers within the run editor's sliders" if not out else
                             "FAILED: outside the run editor's sliders: " + ", ".join(out)))
        good.append(not out)
    print(f"{sum(good)} of {len(good)} fine" if not args else f"{sum(good[:-2])} of {len(styles)} fine"
          + ("" if good[-1] else ", but an arm goes through the body"))
    sys.exit(0 if all(good) else 1)


if __name__ == "__main__":
    main()
