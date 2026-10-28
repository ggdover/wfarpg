"""The play demo for Windows, as one file: dist/wfarpg.exe, with everything packed into it. Runs on Linux or Windows:

    python3 game/tools/export_windows.py        (from anywhere; GODOT=... to use another Godot 4.7)

The first time, it fetches Godot's export templates for this version (1.3 GB, checked against the release's SHA-512)
and keeps only the Windows ones, where Godot looks for them: ~/.local/share/godot/export_templates on Linux,
%APPDATA%\\Godot\\export_templates on Windows.
"""
import fnmatch
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "dist", "wfarpg.exe")
KEEP = ("templates/version.txt", "templates/windows_*_x86_64*.exe")  # the Windows templates, from the .tpz


def godot():
    """Godot 4.7: $GODOT, else godot on PATH (on Windows, its console build or a godot.cmd that runs it)."""
    exe = os.environ.get("GODOT") or shutil.which("godot")
    if not exe:
        sys.exit("Godot 4.7 not found: put godot on PATH, or set GODOT to it (README.md)")
    return exe


def templates_dir(version):
    if sys.platform == "win32":
        data = os.path.join(os.environ["APPDATA"], "Godot")
    else:
        data = os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"), "godot")
    return os.path.join(data, "export_templates", version)


def fetch_templates(version, dest):
    tag = version.removesuffix(".stable") + "-stable"  # 4.7.2.stable -> 4.7.2-stable
    url = f"https://github.com/godotengine/godot/releases/download/{tag}"
    tpz = f"Godot_v{tag}_export_templates.tpz"
    sums = urllib.request.urlopen(f"{url}/SHA512-SUMS.txt").read().decode()
    want = next((line.split()[0] for line in sums.splitlines() if line.endswith(" " + tpz)), None)
    if not want:
        sys.exit(f"{tpz} isn't in the release's SHA512-SUMS.txt")
    print(f"Fetching Godot's export templates for {version}...")
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, tpz)
        digest = hashlib.sha512()
        with urllib.request.urlopen(f"{url}/{tpz}") as r, open(path, "wb") as fh:
            size, got = int(r.headers.get("Content-Length", 0)), 0
            while chunk := r.read(1 << 20):
                fh.write(chunk)
                digest.update(chunk)
                got += len(chunk)
                print(f"\r  {got >> 20} of {size >> 20} MB", end="", flush=True)
        print()
        if digest.hexdigest() != want:
            sys.exit(f"{tpz}: its SHA-512 isn't the release's")
        os.makedirs(dest, exist_ok=True)
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if any(fnmatch.fnmatch(name, keep) for keep in KEEP):
                    with z.open(name) as src, open(os.path.join(dest, os.path.basename(name)), "wb") as dst:
                        shutil.copyfileobj(src, dst)


if __name__ == "__main__":
    exe = godot()
    out = subprocess.run([exe, "--version"], capture_output=True, encoding="utf-8", check=True).stdout
    version = ".".join(out.strip().split(".")[:4])  # 4.7.2.stable.official.ed1daf0bf -> 4.7.2.stable
    templates = templates_dir(version)
    if not os.path.isfile(os.path.join(templates, "windows_release_x86_64.exe")):
        fetch_templates(version, templates)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    subprocess.run([exe, "--headless", "--path", os.path.join(ROOT, "game"), "--export-release", "Windows", OUT], check=True)
    print(f"{OUT}: {os.path.getsize(OUT) >> 20} MB")
