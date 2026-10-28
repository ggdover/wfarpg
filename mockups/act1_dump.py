import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv[:-1] else os.path.join(HERE, "build", "act1")
os.makedirs(OUT, exist_ok=True)
import act1_world as A
f = lambda pts: [[round(float(x), 2), round(float(y), 2)] for x, y in pts]
out = dict(
    zones={k: dict(name=z["name"], orig=z["orig"], mood=z["mood"], poly=f(z["smooth"])) for k, z in A.ZONES.items()},
    paths={k: dict(pts=f(p), w=w, kind=kind) for k, (p, w, kind) in A.PATHS.items()},
    quests=[dict(id=q[0], kind=q[1], zone=q[2], sv=q[3], en=q[4], pos=list(q[5]), min=q[6]) for q in A.QUESTS],
    waystones={k: list(v) for k, v in A.WAYSTONES.items()},
    areas=[dict(sv=a, en=b, pos=list(p)) for a, b, p in A.AREAS],
    shots=[dict(id=s[0], zone=s[1], label=s[2], pos=list(s[3]), yaw=s[4], pitch=s[5], dist=s[6]) for s in A.SHOTS],
    hill=A.HILL, hollow=A.HOLLOW, lake=A.LAKE, esker=f(A.ESKER), farm=A.FARMSTEAD, courtyard=A.COURTYARD, arena=A.ARENA,
    houses=A.TOWN_HOUSES)
json.dump(out, open(os.path.join(OUT, "world.json"), "w", encoding="utf-8", newline="\n"))
print("dumped")
