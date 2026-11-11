"""Records each run in the play demo itself (game/scripts/dev/runs.gd --tour, with Godot's --write-movie): one model on
one rig running about the open field, starting, turning and stopping, in the game's own light, from the game's camera
zoomed in to ZOOM m, as the player can with the mouse wheel (or, with --views=near, from nearer and lower: runs.gd
--close). Each becomes build/runs/game/<run>.mp4 (<run>_near.mp4) by movie_to_mp4.py in Blender, which the rating page
shows beside the run's side clip. The runs are the build's (build/runs/runs.json, from make_runs.py), on Faceted 1500
with bone heat's rig unless asked otherwise.

    python3 record_runs.py [--model=2] [--rig=heat] [--runs=athletic,heroic] [--views=far,near] [--screen=1]

The same on Linux and Windows: it runs game/tools/play.py and blender from PATH. --screen goes to play.py: the screen
the demo's window opens on (the Claude app's by default).
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BUILD = os.path.join(HERE, "build", "runs")
OUT = os.path.join(BUILD, "game")
ZOOM = 10.0  # m from the hero, the game's camera (it starts at 20 and zooms in to 7): near enough to see the run


def main():
    opts = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    model, rig = opts.get("model", "2"), opts.get("rig", "heat")
    if "runs" in opts:
        todo = opts["runs"].split(",")
    else:
        with open(os.path.join(BUILD, "runs.json"), encoding="utf-8") as f:
            todo = [r["key"] for r in json.load(f)]
    views = opts.get("views", "far").split(",")
    os.makedirs(OUT, exist_ok=True)
    blender = shutil.which("blender") or "blender"
    for run in todo:
        for view in views:
            name = run + ("_near" if view == "near" else "")
            avi = os.path.join(OUT, name + ".avi")
            mp4 = os.path.join(OUT, name + ".mp4")
            subprocess.run([sys.executable, os.path.join(ROOT, "game", "tools", "play.py"), "--write-movie", avi]
                           + ([f"--screen={opts['screen']}"] if "screen" in opts else [])
                           + ["--fixed-fps", "30", "--script", "res://scripts/dev/runs.gd", "--", "--scene=open_field",
                            f"--model={model}", f"--rig={rig}", f"--run={run}", "--tour", "--nohud"]
                           + (["--close"] if view == "near" else [f"--zoom={ZOOM:g}"]), check=True)
            subprocess.run([blender, "-b", "--factory-startup", "-P", os.path.join(HERE, "movie_to_mp4.py"), "--",
                            avi, mp4, "3.4", "1280"], check=True, stdout=subprocess.DEVNULL)
            os.remove(avi)
            print("recorded", mp4)


if __name__ == "__main__":
    main()
