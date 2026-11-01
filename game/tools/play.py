"""Starts the play demo as `godot --path game` does, on Linux or Windows, but on the monitor the Claude app is on
(found on Windows; elsewhere, or with no Claude window, on the primary screen), saying first which screen it chose and
why. --screen=primary (or --screen primary) opens it on the primary instead, --screen=N on screen N as Godot counts
them (from 0; 0 needn't be the primary). Everything else goes to Godot:

    python3 game/tools/play.py
    python3 game/tools/play.py res://scenes/demo.tscn -- --scene=bog --trees=old
    python3 game/tools/play.py --screen=primary

GODOT=... to use another Godot 4.7. Exits with Godot's exit code.
"""
import os
import subprocess
import sys

import godot

GAME = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

if __name__ == "__main__":
    args = sys.argv[1:]
    ours = args.index("--") if "--" in args else len(args)  # what follows -- is the demo's own
    window, rest = godot.take_screen(args[:ours])
    sys.exit(subprocess.run([godot.exe(), "--path", GAME, *window, *rest, *args[ours:]]).returncode)
