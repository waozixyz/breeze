"""First-run Apps, saved preferences and Quit on a private display/profile."""
import contextlib
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
    # Both root artifacts open the ready-to-use Apps library and migrate old
    # navigation settings without rewriting an owner's saved app preferences.
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
                      "tutorial_seen": 1, "habits_guide_seen": 1, "launcher_guide_seen": 1,
                      "ui_scale": 10,
                      "navigation_placement": 1, "navigation_collapsed": 0,
                      "bottom_nav_route_count": 2, "bottom_nav_route_0": 0,
                      "bottom_nav_route_1": 4}
            for key, value in values.items():
                db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                           "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user, key, str(value)))
        with application(profile, profile.name + "-all", *args) as (app, window, log):
            command("import", "-window", window, str(OUTPUT / (profile.name + "-checked.png")))
            with Image.open(OUTPUT / (profile.name + "-checked.png")) as image:
                text = read_text(image, profile.name + "-startup")
            for label in ("apps", "lumi", "habits", "practice", "lists", "diary", "profile", "settings"):
                assert label in text, f"{profile.name}: Apps omitted {label}"
            # Opening the first app completes setup; the library itself does
            # not require a separate Next button or overwrite preferences.
            click(window, 44, 218)  # Practice, the third favorite.
            deadline = time.monotonic() + 2
            while settings(profile).get("apps_setup_done") != "1":
                assert time.monotonic() < deadline, "Apps setup did not complete\n" + log.read_text()
                time.sleep(.05)
            saved = settings(profile)
            assert saved["enabled_apps"] == "22", "Startup changed saved app preferences"
            order = [int(saved[f"launcher_favorite_{i}"]) for i in range(int(saved["launcher_favorite_count"]))]
            assert order == [12, 1, 2, 3, 11], "Desktop defaults omitted an installed app: " + str(order)
            deadline = time.monotonic() + 2
            while "->0" not in log.read_text():
                assert time.monotonic() < deadline, "Practices click was ignored\n" + log.read_text()
                time.sleep(.05)
            command("import", "-window", window, str(OUTPUT / "practices-open.png"))
            # Diary is pinned but not installed, so the dock leaves it out;
            # its card in the Apps library installs and opens it.
            click(window, 44, 310)  # Apps, after the three installed favorites.
            time.sleep(.4)
            click(window, 297, 427)  # Diary, the fifth pinned card.
            deadline = time.monotonic() + 2
            while "screen=0->22" not in log.read_text():
                assert time.monotonic() < deadline, "Diary click was ignored\n" + log.read_text()
                time.sleep(.05)
            command("import", "-window", window, str(OUTPUT / "diary-open.png"))
            selected = settings(profile)
            assert selected["enabled_apps"] == "30", "Opening Diary changed unrelated app choices"
            receipts[profile.name] = dict(selection=int(selected["enabled_apps"]), order=order)
        with application(profile, profile.name + "-restart", *args):
            saved = settings(profile)
            assert saved["enabled_apps"] == "30", "Restart lost the explicit Diary choice"
            restored = [int(saved[f"launcher_favorite_{i}"]) for i in range(int(saved["launcher_favorite_count"]))]
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
