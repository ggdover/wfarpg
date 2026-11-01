"""The play demo's checks, the same on Linux and Windows: Godot imports the project without changing any file in the
repository, the selftest tries the controls (scripts/dev/selftest.gd), and each scene's scenetest walks it
(scripts/dev/scenetest.gd). The demo's window opens for each, a few minutes in all, on the monitor the Claude app is
on, as for play.py (found on Windows; elsewhere, or with no Claude window, on the primary screen), saying first which
screen it chose and why.

    python3 game/tools/checks.py                      all of them
    python3 game/tools/checks.py import selftest bog  only these (scenes by their ids in scripts/scenes.gd)
    python3 game/tools/checks.py --screen=primary ... the window on the primary screen instead
    python3 game/tools/checks.py --screen=1 ...       on screen 1 (Godot counts from 0; 0 needn't be the primary)

GODOT=... to use another Godot 4.7. Exits with 1 if a check fails. A check with a window that's still running after
10 minutes (they take about one) has hung: it's stopped and fails, rather than staying on the screen.
"""
import collections
import os
import re
import subprocess
import sys
import threading
import time

import godot

GAME = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT = os.path.dirname(GAME)
LIMIT = 10 * 60  # seconds a check with a window may run


def scenes():
    with open(os.path.join(GAME, "scripts", "scenes.gd"), encoding="utf-8") as fh:
        return re.findall(r'"id": "(\w+)"', fh.read())


def changed_files():
    """What git sees changed in the repository, or None without git."""
    r = subprocess.run(["git", "-C", ROOT, "status", "--porcelain"], capture_output=True, encoding="utf-8")
    return set(r.stdout.splitlines()) if r.returncode == 0 else None


def stop(p):
    """Stops Godot: on Windows with whatever runs it (godot.cmd, Godot's console build), which killing p would leave."""
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/f", "/t", "/pid", str(p.pid)], capture_output=True)
    else:
        p.kill()


def run(name, *args, limit=None):
    """Runs Godot on the game with args, printing its failures, errors and tallies as they come, and if it fails, its
    exit code and last lines; it's stopped if it's still running after limit seconds. True if it passed."""
    start = time.time()
    last = collections.deque(maxlen=12)
    with subprocess.Popen([godot.exe(), "--path", GAME, *args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          encoding="utf-8", errors="replace") as p:
        timer = threading.Timer(limit or 0, stop, [p])
        timer.daemon = True
        if limit:
            timer.start()
        for line in p.stdout:
            last.append(line.rstrip())
            if line.startswith(("FAIL", "ERROR", "SCRIPT ERROR")) or re.match(r"(self|scene)test.*passed", line):
                print("    " + line.rstrip())
        timer.cancel()
    if limit and time.time() - start >= limit:
        print(f"    stopped: still running after {limit // 60} minutes, so it hung")
    if p.returncode != 0:
        print(f"    Godot exited with {p.returncode}, after:", *last, sep="\n      ")
    print(f"{'ok  ' if p.returncode == 0 else 'FAIL'}  {name}  ({time.time() - start:.0f} s)", flush=True)
    return p.returncode == 0


def check_import():
    before = changed_files()
    ok = run("import", "--headless", "--import")
    after = changed_files()
    if before is not None and after is not None and after - before:
        print("FAIL  the import changed files in the repository:", *sorted(after - before), sep="\n    ")
        ok = False
    return ok


if __name__ == "__main__":
    ids = scenes()
    window, wanted = godot.take_screen(sys.argv[1:])  # where the demo's window opens, and the checks asked for
    wanted = wanted or ["import", "selftest", *ids]
    unknown = [w for w in wanted if w not in ("import", "selftest", *ids)]
    if unknown:
        sys.exit(f"no such check: {' '.join(unknown)} (import, selftest, or a scene: {' '.join(ids)})")
    results = []
    for w in wanted:
        if w == "import":
            results.append(check_import())
        elif w == "selftest":
            results.append(run("selftest", *window, "res://scenes/demo.tscn", "--", "--selftest", limit=LIMIT))
        else:
            results.append(run(f"scenetest {w}", *window, "res://scenes/demo.tscn", "--", f"--scene={w}",
                               "--scenetest", limit=LIMIT))
    print(f"{results.count(True)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)
