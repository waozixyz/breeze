"""First-run cell choices and Quit on an owned private display/profile."""
import contextlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/startup-quit-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
BINARY = Path(sys.argv[1]).resolve()
KEYS = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS")
assert all(not os.environ.get(key) for key in KEYS), "Inherited desktop environment"


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


with tempfile.TemporaryDirectory(prefix="inbe-startup-quit-") as temporary, contextlib.ExitStack() as stack:
    env = {key: value for key, value in os.environ.items() if key not in KEYS}
    env.pop("INBE_DIARY_IMPORT", None)
    env.update(YUE_DESKTOP_RECOVERY="0", APP_NO_TRAY="1", SDL_AUDIODRIVER="dummy",
               INBE_DEBUG_ROUTE="1")
    display_log = stack.enter_context((OUTPUT / "display.log").open("w"))
    server = subprocess.Popen(["Xvfb", "-displayfd", "1", "-screen", "0", "1280x900x24",
                               "-nolisten", "tcp"], env=env, stdout=subprocess.PIPE, stderr=display_log)
    stack.callback(stop, server)
    number = server.stdout.readline().decode().strip()
    server.stdout.close()
    assert number.isdecimal()
    env["DISPLAY"] = ":" + number

    def command(*args):
        return subprocess.run(args, env=env, check=True, capture_output=True,
                              text=True, timeout=5).stdout.strip()

    def click(window, x, y):
        command("xdotool", "mousemove", "--window", window, str(x), str(y))
        time.sleep(.1)
        command("xdotool", "mousedown", "1")
        time.sleep(.1)
        command("xdotool", "mouseup", "1")

    def settings(profile):
        with sqlite3.connect(profile / "inbe.db", timeout=3) as db:
            return dict(db.execute("SELECT key,value FROM settings"))

    @contextlib.contextmanager
    def application(profile, name, *args, preview=False):
        log_path = OUTPUT / (name + ".log")
        with log_path.open("w") as log:
            environment = env | {"APP_DATA_ROOT": str(profile)}
            if preview:
                environment["APP_SHOT_WINDOW"] = "1"
            app = subprocess.Popen([str(BINARY), *args], cwd=ROOT, env=environment,
                                   stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 15
                window = ""
                while time.monotonic() < deadline:
                    assert app.poll() is None, log_path.read_text()
                    found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                                           env=env, capture_output=True, text=True, timeout=2)
                    if found.returncode == 0 and found.stdout.strip():
                        window = found.stdout.splitlines()[0]
                        break
                    time.sleep(.05)
                assert window, log_path.read_text()
                command("xdotool", "windowsize", window, "900", "720")
                command("xdotool", "windowfocus", window)
                time.sleep(.7)
                yield app, window, log_path
                assert "frame rejected" not in log_path.read_text(), log_path.read_text()
            finally:
                stop(app)

    receipts = {}
    # The shipped picker completes immediately with all five offline cells.
    # Both root artifacts keep every shortcut and Settings fixed last.
    for full in (False, True):
        profile = Path(temporary) / ("full" if full else "base")
        args = ["--bundle", str(ROOT / "build/inbe-full.zib")] if full else []
        with application(profile, profile.name + "-prepare", *args):
            pass
        with sqlite3.connect(profile / "inbe.db") as db:
            user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
            values = {"language": "en", "language_system": 0, "language_setup_done": 1,
                      "apps_setup_done": 0, "enabled_apps": 22, "lumi_introduced": 1,
                      "cells_auto_update": 0, "apps_last_update_check": 1900000000,
                      "tutorial_seen": 1, "habits_guide_seen": 1, "ui_scale": 10,
                      "navigation_placement": 1, "navigation_collapsed": 0,
                      "bottom_nav_route_count": 2, "bottom_nav_route_0": 0,
                      "bottom_nav_route_1": 4}
            for key, value in values.items():
                db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                           "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user, key, str(value)))
        with application(profile, profile.name + "-all", *args) as (app, window, log):
            click(window, 260, 474)  # Lists.
            time.sleep(.2)
            click(window, 260, 546)  # Diary.
            time.sleep(.2)
            command("import", "-window", window, str(OUTPUT / (profile.name + "-checked.png")))
            click(window, 450, 676)  # Next.
            deadline = time.monotonic() + 2
            while settings(profile).get("apps_setup_done") != "1":
                assert time.monotonic() < deadline, "All checked: Next was ignored\n" + log.read_text()
                time.sleep(.05)
            saved = settings(profile)
            assert saved["enabled_apps"] == "31", saved
            order = [int(saved[f"bottom_nav_route_{i}"]) for i in range(int(saved["bottom_nav_route_count"]))]
            assert order[-1] == 4, "Settings must stay last: " + str(order)
            assert set(order) == {0, 1, 2, 3, 4, 11, 12}, "A selected cell was omitted: " + str(order)
            time.sleep(.4)
            assert "screen=21->23" in log.read_text(), log.read_text()
            # All five cells fit alongside a previously saved Profile
            # shortcut; Practices and Diary both remain usable.
            rail = [route for route in order if route not in (0, 4)]
            click(window, 110, 146 + rail.index(2) * 64)
            deadline = time.monotonic() + 2
            while "screen=23->0" not in log.read_text():
                assert time.monotonic() < deadline, "Practices click was ignored\n" + log.read_text()
                time.sleep(.05)
            command("import", "-window", window, str(OUTPUT / "practices-open.png"))
            diary_index = rail.index(11)
            click(window, 110, 146 + diary_index * 64)
            deadline = time.monotonic() + 2
            while "screen=0->22" not in log.read_text():
                assert time.monotonic() < deadline, "Diary click was ignored\n" + log.read_text()
                time.sleep(.05)
            command("import", "-window", window, str(OUTPUT / "diary-open.png"))
            receipts[profile.name] = dict(selection=int(saved["enabled_apps"]), order=order)
        with application(profile, profile.name + "-restart", *args):
            saved = settings(profile)
            restored = [int(saved[f"bottom_nav_route_{i}"]) for i in range(int(saved["bottom_nav_route_count"]))]
            assert restored == order, "Restart lost a selected cell: " + str(restored)

    # Preview windows used to discard the close dialog result forever.
    with application(Path(temporary) / "quit", "quit-modal", "--screenshot", str(OUTPUT / "prompt.png"),
                     "--screenshot-scene", "close_prompt", "--screenshot-width", "900",
                     "--screenshot-height", "720", preview=True) as (app, window, log):
        command("import", "-window", window, str(OUTPUT / "quit-before.png"))
        started = time.monotonic()
        click(window, 526, 414)
        try:
            status = app.wait(timeout=1)
        except subprocess.TimeoutExpired:
            raise AssertionError("A single Quit click did not exit promptly\n" + log.read_text())
        assert status == 0, log.read_text()
        receipts["quit_seconds"] = round(time.monotonic() - started, 3)
    (OUTPUT / "receipt.json").write_text(json.dumps(receipts, indent=2) + "\n")
    print(json.dumps(receipts))
