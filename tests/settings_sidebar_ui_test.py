"""Exercise scale dragging and saved favorites on owned private windows."""
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
                  "apps_setup_done": 1, "enabled_apps": 22, "lumi_introduced": 1,
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
        click(window, 44, 316)  # Apps in the compact dock.
        click(window, 220, 684)  # Settings in the drawer.
        capture(window, "settings-hub")
        click(window, 200, 325)  # Appearance.
        before = capture(window, "appearance")
        # Coordinates come from the 900x720 rendered Appearance panel.
        command("xdotool", "mousemove", "--window", window, "650", "420")
        time.sleep(.15)
        command("xdotool", "mousedown", "1")
        time.sleep(.3)
        before = capture(window, "drag-started")
        for x, y in ((550, 430), (860, 440), (580, 410), (845, 425)):
            command("xdotool", "mousemove", "--window", window, str(x), str(y))
            time.sleep(.12)
            assert settings()["ui_scale"] == "10", "Scale changed while the slider was held"
            held = capture(window, f"held-{x}")
            assert ImageChops.difference(before.crop((0, 0, 344, 720)),
                                         held.crop((0, 0, 344, 720))).getbbox() is None, "Sidebars moved during drag"
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
        click(window, 200, 381)  # Apps and favorites.
        capture(window, "apps-favorites")
        assert order() == [12, 1]
        command("xdotool", "mousemove", "--window", window, "396", "148")
        time.sleep(.15)
        command("xdotool", "mousedown", "1")
        time.sleep(.2)
        command("xdotool", "mousemove", "--window", window, "396", "224")
        time.sleep(.3)
        capture(window, "favorites-reordering")
        command("xdotool", "mouseup", "1")
        time.sleep(.4)
        assert order() == [1, 12], order()
        click(window, 826, 148)  # Unpin Habits.
        assert order() == [12], order()
        wait_setting("enabled_apps", 22)
        capture(window, "favorite-unpinned")

    with application("restart") as (window, log):
        assert order() == [12], "Restart restored an unpinned shortcut"
        click(window, 44, 232)  # Apps follows the one favorite.
        click(window, 220, 684)
        click(window, 200, 381, hold=.35)
        assert order() == [12], "Opening settings with a held click changed favorites"
        assert settings()["enabled_apps"] == "22"
        click(window, 826, 260)  # Pin Habits from the available rows.
        assert order() == [12, 1], order()
        click(window, 826, 148)  # Unpin Lumi.
        assert order() == [1], order()
        assert settings()["enabled_apps"] == "22", "Unpinning disabled an app"
        capture(window, "lumi-unpinned")

        def host_state():
            value = command("xprop", "-id", window, "_HARMONY_APP_STATE")
            return json.loads(ast.literal_eval(value.split(" = ", 1)[1]))

        for control, arguments in (("mcp.set_theme", {"theme": "forest"}),
                                   ("mcp.open_view", {"view": "lumi"})):
            request = "unpinned-" + control.replace(".", "-")
            command("xprop", "-id", window, "-f", "_HARMONY_APP_ACTION", "8s", "-set",
                    "_HARMONY_APP_ACTION", json.dumps(dict(control=control,
                    request_id=request, arguments=arguments)))
            deadline = time.monotonic() + 3
            while host_state()["last_request_id"] != request:
                assert time.monotonic() < deadline, "Unpinned Lumi stopped accepting app tools"
                time.sleep(.05)
            assert host_state()["last_request_ok"]
        assert host_state()["screen"] == 23
        assert host_state()["settings"]["theme"] == "forest"
        assert settings()["enabled_apps"] == "22"
        assert order() == [1], "Opening Lumi added an unwanted shortcut"
        capture(window, "unpinned-lumi-tools")

        request = "unpinned-open-settings"
        command("xprop", "-id", window, "-f", "_HARMONY_APP_ACTION", "8s", "-set",
                "_HARMONY_APP_ACTION", json.dumps(dict(control="mcp.open_view",
                request_id=request, arguments={"view": "settings"})))
        deadline = time.monotonic() + 3
        while host_state()["last_request_id"] != request:
            assert time.monotonic() < deadline
            time.sleep(.05)
        click(window, 826, 316)  # Pin Diary without changing app choices.
        assert order() == [1, 11], order()
        assert settings()["enabled_apps"] == "22"
        click(window, 826, 372)  # Pin Lumi as the third favorite.
        assert order() == [1, 11, 12], order()
        click(window, 826, 316)  # Pin Lists from the remaining available rows.
        assert order() == [1, 11, 12, 3], order()
        click(window, 826, 372)  # Pin Practice: every app may be a favorite.
        assert order() == [1, 11, 12, 3, 2], order()
        assert settings()["enabled_apps"] == "22", "Extra pins changed app choices"
        click(window, 620, 204)  # Opening Diary also enables it.
        wait_setting("enabled_apps", 30)
        assert host_state()["screen"] == 22
        with sqlite3.connect(profile / "inbe.db") as db:
            assert db.execute("SELECT title FROM elist_lists WHERE id='settings-preserved-list'").fetchone() == ("Keep this saved list",)
            assert db.execute("SELECT name FROM habits WHERE id='settings-preserved-habit'").fetchone() == ("Keep this habit",)

    with application("saved-order"):
        assert order() == [1, 11, 12, 3, 2], "All favorite positions did not persist"
        assert settings()["enabled_apps"] == "30"

print("Settings: scale commits on release; favorite reordering, every app pinned and app tools preserve data")
