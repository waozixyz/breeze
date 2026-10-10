#!/usr/bin/env python3
"""Every practice shows its picture, and a running Sun Salutation its figure."""
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

from PIL import Image, ImageStat

assert int(os.environ.get("DISPLAY", ":0").split(":")[-1].split(".")[0]) >= 300
root = Path(__file__).resolve().parents[1]
binary = Path(sys.argv[1]).resolve()
output = root / "build/practice-images-ui-test"
output.mkdir(parents=True, exist_ok=True)
WIDTH, HEIGHT = 390, 844
PRACTICES = ("wim-hof", "patterns", "meditation", "sun-salutation")


def command(*args):
    return subprocess.check_output(args, text=True, timeout=5).strip()


def click(window, x, y):
    command("xdotool", "mousemove", "--window", window, str(x), str(y))
    time.sleep(0.12)
    command("xdotool", "mousedown", "1")
    time.sleep(0.15)
    command("xdotool", "mouseup", "1")
    time.sleep(1.2)


def capture(window, name):
    path = output / (name + ".png")
    command("import", "-window", window, str(path))
    with Image.open(path) as image:
        return image.convert("RGB").copy()


def pictured(image, box):
    """A loaded picture varies; a missing one leaves the flat page colour."""
    return max(ImageStat.Stat(image.crop(box)).stddev) > 12


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def launch(profile, name):
    log = (output / (name + ".log")).open("w")
    app = subprocess.Popen([str(binary)], cwd=root, env=os.environ | {"APP_DATA_ROOT": str(profile)},
                           stdout=log, stderr=subprocess.STDOUT)
    for _ in range(200):
        assert app.poll() is None, (output / (name + ".log")).read_text()
        found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                               capture_output=True, text=True)
        if found.returncode == 0 and (profile / "inbe.db").exists():
            window = found.stdout.splitlines()[0]
            command("xdotool", "windowsize", window, str(WIDTH), str(HEIGHT))
            command("xdotool", "windowmove", window, "0", "0")
            time.sleep(1.5)
            return app, window
        time.sleep(0.1)
    stop(app)
    raise AssertionError("Inbe did not map its window")


with tempfile.TemporaryDirectory(prefix="inbe-practice-images-") as directory:
    profile = Path(directory)
    app, _ = launch(profile, "first-start")
    stop(app)
    with sqlite3.connect(profile / "inbe.db") as db:
        user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
        settings = {"language": "en", "language_system": 0, "language_setup_done": 1,
                    "apps_setup_done": 1, "main_tab": 1, "tutorial_seen": 1,
                    "habits_guide_seen": 1, "launcher_guide_seen": 1, "cells_auto_update": 0,
                    "apps_last_update_check": 1900000000}
        for key, value in settings.items():
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                       "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value",
                       (user, key, str(value)))
    app, window = launch(profile, "practice")
    try:
        missing = []
        for index, practice in enumerate(PRACTICES):
            if index > 0:
                click(window, 324, 620)  # The next practice.
            if not pictured(capture(window, practice), (0, 40, WIDTH, 420)):
                missing.append(practice)
        click(window, 195, 678)  # Start Sun Salutation.
        if not pictured(capture(window, "sun-salutation-running"), (100, 250, 290, 650)):
            missing.append("sun-salutation figure")
        assert not missing, "Practice pictures are missing: " + ", ".join(missing)
        assert app.poll() is None, (output / "practice.log").read_text()
    finally:
        stop(app)
print("Practice pictures: Wim Hof, patterns, meditation and Sun Salutation, and the running figure passed")
