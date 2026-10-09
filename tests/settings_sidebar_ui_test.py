"""Verify Settings scale gestures and removal of the former favorites panel."""
import ast
import contextlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/settings-sidebar-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
KEYS = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS")
assert all(not os.environ.get(key) for key in KEYS), "Inherited desktop environment"
BINARY = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "build/bin/linux/inbe-linux-x86_64")


def stop(process):
    if process.poll() is None:
        process.terminate()
    process.wait(timeout=5)


with tempfile.TemporaryDirectory(prefix="inbe-settings-") as temporary, contextlib.ExitStack() as stack:
    profile = Path(temporary)
    env = {key: value for key, value in os.environ.items() if key not in KEYS}
    env.update(YUE_DESKTOP_RECOVERY="0", APP_NO_TRAY="1", SDL_AUDIODRIVER="dummy",
               APP_DATA_ROOT=str(profile), INBE_DEBUG_ROUTE="1")
    display_log = stack.enter_context((OUTPUT / "display.log").open("w"))
    display = subprocess.Popen(["Xvfb", "-displayfd", "1", "-screen", "0", "1280x900x24",
                                "-nolisten", "tcp"], env=env, stdout=subprocess.PIPE, stderr=display_log)
    stack.callback(stop, display)
    number = display.stdout.readline().decode().strip()
    display.stdout.close()
    assert number.isdecimal()
    env["DISPLAY"] = ":" + number

    def command(*args):
        return subprocess.run(args, env=env, check=True, capture_output=True, text=True, timeout=5).stdout.strip()

    def capture(window, name):
        path = OUTPUT / (name + ".png")
        command("import", "-window", window, str(path))
        with Image.open(path) as image:
            return image.convert("RGB").copy()

    def settings():
        with sqlite3.connect(profile / "inbe.db", timeout=3) as db:
            return dict(db.execute("SELECT key,value FROM settings"))

    def settled_sidebar(window):
        # Keep the exact pixel assertion, but let the selected/pressed
        # transition finish before using it as the drag reference.
        deadline = time.monotonic() + 3
        previous = capture(window, "drag-started")
        stable_frames = 0
        while time.monotonic() < deadline:
            time.sleep(.15)
            current = capture(window, "drag-started")
            difference = ImageChops.difference(previous.crop((0, 0, 344, 720)),
                                              current.crop((0, 0, 344, 720)))
            stable_frames = stable_frames + 1 if difference.getbbox() is None else 0
            if stable_frames == 3:
                return current
            previous = current
        raise AssertionError("Settings sidebars never settled before the slider drag")

    def wait_setting(key, expected):
        deadline = time.monotonic() + 5
        while settings().get(key) != str(expected):
            assert time.monotonic() < deadline, (key, expected, settings().get(key))
            time.sleep(.05)

    def order():
        saved = settings()
        return [int(saved[f"launcher_favorite_{i}"]) for i in range(int(saved["launcher_favorite_count"]))]

    def click(window, x, y, hold=.12):
        command("xdotool", "mousemove", "--window", window, str(x), str(y))
        time.sleep(.15)
        command("xdotool", "mousedown", "1")
        time.sleep(hold)
        command("xdotool", "mouseup", "1")
        time.sleep(.5)

    @contextlib.contextmanager
    def application(name):
        log_path = OUTPUT / (name + ".log")
        with log_path.open("w") as log:
            app = subprocess.Popen([str(BINARY)], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 15
                window = ""
                while time.monotonic() < deadline:
                    assert app.poll() is None, log_path.read_text()
                    found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                                           env=env, capture_output=True, text=True, timeout=2)
                    if found.returncode == 0 and (profile / "inbe.db").exists():
                        window = found.stdout.splitlines()[0]
                        break
                    time.sleep(.05)
                assert window, log_path.read_text()
                command("xdotool", "windowsize", window, "900", "720")
                command("xdotool", "windowmove", window, "0", "0")
                command("xdotool", "windowfocus", window)
                time.sleep(.6)
                yield window, log_path
                assert app.poll() is None, log_path.read_text()
                assert "frame rejected" not in log_path.read_text(), log_path.read_text()
            finally:
                stop(app)

    # Create the real storage schema, then seed only this disposable profile.
    with application("prepare"):
        pass
    with sqlite3.connect(profile / "inbe.db") as db:
        user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
        values = {"language": "en", "language_system": 0, "language_setup_done": 1,
                  "apps_setup_done": 1, "launcher_guide_seen": 1,
                  "enabled_apps": 22, "lumi_introduced": 1,
                  "main_tab": 1, "tutorial_seen": 1, "habits_guide_seen": 1, "ui_scale": 10, "navigation_placement": 1,
                  "navigation_collapsed": 0, "cells_auto_update": 0,
                  "apps_last_update_check": 1900000000,
                  "launcher_favorite_count": 2, "launcher_favorite_0": 12, "launcher_favorite_1": 1,
                  "bottom_nav_route_count": 4, "bottom_nav_route_0": 12,
                  "bottom_nav_route_1": 1, "bottom_nav_route_2": 2, "bottom_nav_route_3": 4}
        for key, value in values.items():
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                       "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user, key, str(value)))
        db.execute("INSERT INTO elist_lists(id,user_id,title,sort_order,deleted_at,updated_at) "
                   "VALUES('settings-preserved-list',?,'Keep this saved list',0,0,1)", (user,))
        db.execute("INSERT INTO habits(id,user_id,name,color_r,color_g,color_b,sync_mode,sync_activity,sort_order,updated_at) "
                   "VALUES('settings-preserved-habit',?,'Keep this habit',1,2,3,0,0,0,1)", (user,))

    with application("gestures") as (window, log):
        capture(window, "initial")
        click(window, 44, 228)  # Apps follows the two saved favorites.
        click(window, 690, 684)  # Settings is the right footer card beside Profile.
        hub = capture(window, "settings-hub")
        hub.crop((88, 0, 900, 60)).save(OUTPUT / "settings-title.png")
        text = command("tesseract", str(OUTPUT / "settings-title.png"), "stdout", "--psm", "7")
        assert "Settings" in text, "The Settings fixture opened a different app"
        click(window, 200, 325)  # Appearance.
        before = capture(window, "appearance")
        text = command("tesseract", str(OUTPUT / "appearance.png"), "stdout")
        assert "Scale factor" in text, "Appearance did not open before the slider gesture"
        # Coordinates come from the 900x720 rendered Appearance panel.
        command("xdotool", "mousemove", "--window", window, "650", "388")
        time.sleep(.15)
        command("xdotool", "mousedown", "1")
        time.sleep(.3)
        before = settled_sidebar(window)
        for x, y in ((550, 398), (860, 400), (580, 380), (845, 393)):
            command("xdotool", "mousemove", "--window", window, str(x), str(y))
            time.sleep(.12)
            assert settings()["ui_scale"] == "10", "Scale changed while the slider was held"
            held = capture(window, f"held-{x}")
            difference = ImageChops.difference(before.crop((0, 0, 344, 720)),
                                              held.crop((0, 0, 344, 720))).getbbox()
            assert difference is None, f"Sidebars moved during drag: {difference}"
        command("xdotool", "mouseup", "1")
        time.sleep(.5)
        assert settings()["ui_scale"] != "10", "Release did not commit the scale"
        capture(window, "scaled-after-release")
        command("xdotool", "keydown", "ctrl")
        time.sleep(.15)
        command("xdotool", "keydown", "0")
        time.sleep(.15)
        command("xdotool", "keyup", "0", "ctrl")
        wait_setting("ui_scale", 10)
        time.sleep(.5)
        image = capture(window, "settings-without-apps-panel")
        image.save(OUTPUT / "settings-without-apps-panel.png")
        text = command("tesseract", str(OUTPUT / "settings-without-apps-panel.png"), "stdout")
        assert "Apps and favorites" not in text, "Removed panel remains in Settings"
        assert order() == [12, 1], "Settings changed the favorite order"
        assert settings()["enabled_apps"] == "22"

    with application("restart") as (window, log):
        assert order() == [12, 1], "Settings changes altered saved favorites"
        assert settings()["enabled_apps"] == "22"
        with sqlite3.connect(profile / "inbe.db") as db:
            assert db.execute("SELECT title FROM elist_lists WHERE id='settings-preserved-list'").fetchone() == ("Keep this saved list",)
            assert db.execute("SELECT name FROM habits WHERE id='settings-preserved-habit'").fetchone() == ("Keep this habit",)

print("Settings: scale commits on release; Apps and Favorites removed; saved data preserved")
