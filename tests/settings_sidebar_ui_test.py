"""Exercise scale dragging, cell choices and saved sidebar order on owned Xvfb."""
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
        return [int(saved[f"bottom_nav_route_{i}"]) for i in range(int(saved["bottom_nav_route_count"]))]

    def click(window, x, y):
        command("xdotool", "mousemove", "--window", window, str(x), str(y))
        time.sleep(.15)
        command("xdotool", "mousedown", "1")
        time.sleep(.12)
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
        click(window, 110, 670)  # Settings in the app rail.
        capture(window, "settings-hub")
        click(window, 320, 325)  # Appearance.
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
            assert ImageChops.difference(before.crop((0, 0, 430, 720)),
                                         held.crop((0, 0, 430, 720))).getbbox() is None, "Sidebars moved during drag"
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
        click(window, 320, 381)  # Direct Cells & sidebar entry.
        capture(window, "cells-sidebar")
        command("xdotool", "mousemove", "--window", window, "478", "122")
        time.sleep(.15)
        command("xdotool", "mousedown", "1")
        time.sleep(.2)
        command("xdotool", "mousemove", "--window", window, "478", "254")
        time.sleep(.3)
        capture(window, "sidebar-reordering")
        command("xdotool", "mouseup", "1")
        time.sleep(.4)
        assert order() == [1, 2, 12, 4], order()  # Lumi moves with the other cells.
        click(window, 826, 122)  # Remove Habits from the first compact row.
        assert order() == [2, 12, 4], order()
        wait_setting("enabled_apps", 20)
        assert order() == [2, 12, 4], order()
        capture(window, "cell-removed")

    with application("restart") as (window, log):
        assert order() == [2, 12, 4], "Restart restored removed or reordered shortcuts"
        click(window, 110, 670)
        click(window, 320, 381)
        # All five cells appear once, with hidden cells after active rows.
        # Adding Habits uses bundled bytes without a network request.
        capture(window, "available-cells")
        started = time.monotonic()
        click(window, 826, 290)  # Add Habits from the hidden rows.
        wait_setting("enabled_apps", 22)
        assert time.monotonic() - started < 2, "Cached reinstall waited for a download"
        assert order() == [2, 12, 1, 4], order()
        capture(window, "cell-reinstalled")
        click(window, 620, 122)  # The Practices cell name is also a destination.
        deadline = time.monotonic() + 3
        while "screen=6->0" not in log.read_text():
            assert time.monotonic() < deadline, "Clicking the installed cell did not open it"
            time.sleep(.05)
        with sqlite3.connect(profile / "inbe.db") as db:
            assert db.execute("SELECT title FROM elist_lists WHERE id='settings-preserved-list'").fetchone() == ("Keep this saved list",)
            assert db.execute("SELECT name FROM habits WHERE id='settings-preserved-habit'").fetchone() == ("Keep this habit",)

    with application("hidden-lumi") as (window, log):
        click(window, 110, 670)
        click(window, 320, 381)
        click(window, 826, 178)  # Hide Lumi in the same list.
        wait_setting("enabled_apps", 6)
        assert order() == [2, 1, 4], order()

        def host_state():
            value = command("xprop", "-id", window, "_HARMONY_APP_STATE")
            return json.loads(ast.literal_eval(value.split(" = ", 1)[1]))

        for control, arguments in (("mcp.set_theme", {"theme": "forest"}),
                                   ("mcp.open_view", {"view": "lumi"})):
            request = "hidden-" + control.replace(".", "-")
            command("xprop", "-id", window, "-f", "_HARMONY_APP_ACTION", "8s", "-set",
                    "_HARMONY_APP_ACTION", json.dumps(dict(control=control,
                    request_id=request, arguments=arguments)))
            deadline = time.monotonic() + 3
            while host_state()["last_request_id"] != request:
                assert time.monotonic() < deadline, "Hidden Lumi stopped accepting app tools"
                time.sleep(.05)
            assert host_state()["last_request_ok"]
        assert host_state()["screen"] == 23
        assert host_state()["settings"]["theme"] == "forest"
        assert settings()["enabled_apps"] == "6"
        assert order() == [2, 1, 4], "Opening Lumi restored its hidden shortcut"
        capture(window, "hidden-lumi-tools")

        request = "hidden-open-settings"
        command("xprop", "-id", window, "-f", "_HARMONY_APP_ACTION", "8s", "-set",
                "_HARMONY_APP_ACTION", json.dumps(dict(control="mcp.open_view",
                request_id=request, arguments={"view": "settings"})))
        deadline = time.monotonic() + 3
        while host_state()["last_request_id"] != request:
            assert time.monotonic() < deadline
            time.sleep(.05)
        for y, mask in ((234, 7), (290, 15), (346, 31)):
            started = time.monotonic()
            click(window, 826, y)
            wait_setting("enabled_apps", mask)
            assert time.monotonic() - started < 2, "Adding a bundled cell waited for a download"
        assert order() == [2, 1, 3, 11, 12, 4], order()
        capture(window, "all-cells-unified")

print("Settings: held scale keeps both sidebars fixed; release commits; order and removals survive restart")
