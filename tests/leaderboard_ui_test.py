#!/usr/bin/env python3
"""Leaderboard opens as its own unpinned app and ranks saved friend results."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

from PIL import Image
from native_visual_test import read_text

assert int(os.environ.get("DISPLAY", ":0").split(":")[-1].split(".")[0]) >= 300
root = Path(__file__).resolve().parents[1]
binary = Path(sys.argv[1]).resolve()
output = root / "build/leaderboard-ui-test"
output.mkdir(parents=True, exist_ok=True)
WIDTH, HEIGHT = 390, 844
LEADERBOARD_ROUTE = 9


def command(*args):
    return subprocess.check_output(args, text=True, timeout=5).strip()


def click(window, x, y):
    command("xdotool", "mousemove", "--window", window, str(x), str(y))
    time.sleep(0.12)
    command("xdotool", "mousedown", "1")
    time.sleep(0.15)
    command("xdotool", "mouseup", "1")
    # Move off the control so its hover state does not cover the selection.
    time.sleep(0.3)
    command("xdotool", "mousemove", "--window", window, "200", "600")
    time.sleep(0.6)


def rows(window, name):
    """The ranked names, in order, read from the board's rows."""
    path = output / (name + ".png")
    command("import", "-window", window, str(path))
    with Image.open(path) as image:
        text = read_text(image.crop((16, 112, 374, 400)), name)
    return [word for word in text.split() if word in ("maple", "river", "cedar")], text


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


with tempfile.TemporaryDirectory(prefix="inbe-leaderboard-") as directory:
    profile = Path(directory)
    app, _ = launch(profile, "first-start")
    stop(app)
    with sqlite3.connect(profile / "inbe.db") as db:
        user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
        saved = dict(db.execute("SELECT key,value FROM settings WHERE user_id=?", (user,)))
        favorites = [int(saved[f"launcher_favorite_{i}"])
                     for i in range(int(saved.get("launcher_favorite_count", 0)))]
        assert int(saved["enabled_apps"]) & 32, "Leaderboard is not installed for a new profile"
        assert LEADERBOARD_ROUTE not in favorites, "Leaderboard was pinned by default"
        settings = {"language": "en", "language_system": 0, "language_setup_done": 1,
                    "apps_setup_done": 1, "main_tab": 5, "tutorial_seen": 1,
                    "habits_guide_seen": 1, "launcher_guide_seen": 1, "cells_auto_update": 0,
                    "apps_last_update_check": 1900000000}
        for key, value in settings.items():
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                       "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value",
                       (user, key, str(value)))
        river, maple, cedar = "a" * 64, "b" * 64, "d" * 64
        snapshots = {
            "leaderboard.breathing.whm.streak": {"rows": [
                {"user_id_hash": river, "alias": "river", "value": 12, "label": "12"},
                {"user_id_hash": maple, "alias": "maple", "value": 30, "label": "30"}]},
            "leaderboard.breathing.whm.avg_hold": {"rows": [
                {"user_id_hash": river, "value": 95, "label": "95"},
                {"user_id_hash": maple, "value": 61, "label": "61"}]},
            "leaderboard.breathing.meditation.streak": {"rows": [
                {"user_id_hash": river, "alias": "river", "value": 2, "label": "2"}]},
            "leaderboard.breathing.meditation.avg_time": {"rows": [
                {"user_id_hash": river, "value": 900, "label": "0:15"}]},
            # A friend without results yet still appears, at zero.
            "friends.list": {"friends": [{"user_id_hash": river, "alias": "river"},
                                         {"user_id_hash": cedar, "alias": "cedar"}]},
        }
        for kind, value in snapshots.items():
            db.execute("INSERT OR REPLACE INTO social_snapshots(user_id,kind,json,updated_at) "
                       "VALUES(?,?,?,1)", (user, kind, json.dumps(value)))
    app, window = launch(profile, "board")
    try:
        names, text = rows(window, "streak")
        assert names == ["maple", "river", "cedar"], f"streak order: {text}"
        click(window, 329, 86)
        names, text = rows(window, "average")
        assert names == ["river", "maple", "cedar"], f"average hold order: {text}"
        # Meditation is the third practice tab; its average time is shown.
        click(window, 352, 34)
        names, text = rows(window, "meditation")
        assert names == ["river", "cedar"] and "0" in text and "15" in text, f"meditation: {text}"
        click(window, 235, 34)
        names, text = rows(window, "patterns")
        assert sorted(names) == ["cedar", "river"], f"breathing patterns: {text}"
        log = (output / "board.log").read_text()
        assert "frame rejected" not in log, log
        assert app.poll() is None, log
    finally:
        stop(app)
print("Leaderboard: unpinned install, saved ranks, average hold, meditation time and patterns passed")
