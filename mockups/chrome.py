"""Headless Chrome, which draws the mockups' SVG (the HUD, the blueprints' labels) into PNGs, on Linux or Windows.

Chrome is $CHROME if that's set, else Google Chrome or Chromium on PATH, else Chrome where Windows installs it.
"""
import os, shutil, subprocess
from pathlib import Path

NAMES = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome")


def find():
    if os.environ.get("CHROME"):
        return os.environ["CHROME"]
    for name in NAMES:
        if shutil.which(name):
            return shutil.which(name)
    for root in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):  # Windows: Chrome isn't on PATH
        exe = os.path.join(os.environ.get(root, ""), "Google", "Chrome", "Application", "chrome.exe")
        if os.environ.get(root) and os.path.isfile(exe):
            return exe
    raise SystemExit("Chrome not found: install Google Chrome or Chromium, or set CHROME to its path")


def screenshot(html, png, w, h, *options, timeout=120):
    """Draws the page in the file html, w x h pixels, into png."""
    png = os.path.abspath(png)  # Chrome on Windows doesn't save to a relative path, and still says it did
    if os.path.exists(png):
        os.remove(png)
    subprocess.run([find(), "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars", f"--window-size={w},{h}",
                    *options, f"--screenshot={png}", Path(html).resolve().as_uri()],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout)
    if not os.path.exists(png):
        raise SystemExit(f"Chrome didn't draw {png}")
