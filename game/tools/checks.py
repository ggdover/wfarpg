"""The play demo's checks, the same on Linux and Windows: Godot imports the project without changing any file in the
repository, the selftest tries the controls (scripts/dev/selftest.gd), and each scene's scenetest walks it
(scripts/dev/scenetest.gd). The demo's window opens for each, a few minutes in all.

    python3 game/tools/checks.py                      all of them
    python3 game/tools/checks.py import selftest bog  only these (scenes by their ids in scripts/scenes.gd)

GODOT=... to use another Godot 4.7. Exits with 1 if a check fails.
"""
import os
import re
import shutil
import subprocess
import sys
import time

GAME = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT = os.path.dirname(GAME)


def godot():
    """Godot 4.7: $GODOT, else godot on PATH (on Windows, its console build or a godot.cmd that runs it)."""
    exe = os.environ.get("GODOT") or shutil.which("godot")
    if not exe:
        sys.exit("Godot 4.7 not found: put godot on PATH, or set GODOT to it (README.md)")
    return exe


def scenes():
    with open(os.path.join(GAME, "scripts", "scenes.gd"), encoding="utf-8") as fh:
        return re.findall(r'"id": "(\w+)"', fh.read())


def changed_files():
    """What git sees changed in the repository, or None without git."""
    r = subprocess.run(["git", "-C", ROOT, "status", "--porcelain"], capture_output=True, encoding="utf-8")
    return set(r.stdout.splitlines()) if r.returncode == 0 else None


def run(name, *args):
    """Runs Godot on the game with args, printing its failures, errors and tallies as they come. True if it passed."""
    start = time.time()
    with subprocess.Popen([godot(), "--path", GAME, *args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          encoding="utf-8", errors="replace") as p:
        for line in p.stdout:
            if line.startswith(("FAIL", "ERROR", "SCRIPT ERROR")) or re.match(r"(self|scene)test.*passed", line):
                print("    " + line.rstrip())
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
    wanted = sys.argv[1:] or ["import", "selftest", *ids]
    unknown = [w for w in wanted if w not in ("import", "selftest", *ids)]
    if unknown:
        sys.exit(f"no such check: {' '.join(unknown)} (import, selftest, or a scene: {' '.join(ids)})")
    results = []
    for w in wanted:
        if w == "import":
            results.append(check_import())
        elif w == "selftest":
            results.append(run("selftest", "res://scenes/demo.tscn", "--", "--selftest"))
        else:
            results.append(run(f"scenetest {w}", "res://scenes/demo.tscn", "--", f"--scene={w}", "--scenetest"))
    print(f"{results.count(True)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)
