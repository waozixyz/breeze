"""Exercise the app launcher with disposable data on a private Xvfb display."""

import contextlib
import argparse
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile
import time

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/launcher-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
parser = argparse.ArgumentParser()
parser.add_argument("binary")
parser.add_argument("--layout", choices=("all", "desktop", "mobile"), default="all")
parser.add_argument("--drag-only", action="store_true")
arguments = parser.parse_args()
BINARY = Path(arguments.binary).resolve()
DESKTOP_ENV = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS")
assert all(not os.environ.get(key) for key in DESKTOP_ENV), "Inherited desktop environment"


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


with contextlib.ExitStack() as stack:
    env = {key: value for key, value in os.environ.items() if key not in DESKTOP_ENV}
    env.update(YUE_DESKTOP_RECOVERY="0", APP_NO_TRAY="1", SDL_AUDIODRIVER="dummy",
               INBE_DEBUG_ROUTE="1")
    display_log = stack.enter_context((OUTPUT / "display.log").open("w"))
    display = subprocess.Popen(["Xvfb", "-displayfd", "1", "-screen", "0", "1280x1000x24",
                                "-nolisten", "tcp"], env=env, stdout=subprocess.PIPE, stderr=display_log)
    stack.callback(stop, display)
    number = display.stdout.readline().decode().strip()
    display.stdout.close()
    assert number.isdecimal(), "Private display did not start"
    env["DISPLAY"] = ":" + number

    def command(*args):
        return subprocess.run(args, env=env, check=True, capture_output=True,
                              text=True, timeout=5).stdout.strip()

    def capture(window, name):
        path = OUTPUT / (name + ".png")
        command("import", "-window", window, str(path))
        with Image.open(path) as image:
            return image.convert("RGB").copy()

    def click(window, x, y, hold=.12):
        command("xdotool", "mousemove", "--window", window, str(x), str(y))
        time.sleep(.12)
        command("xdotool", "mousedown", "1")
        time.sleep(hold)
        command("xdotool", "mouseup", "1")
        time.sleep(.4)

    def key(window, name):
        command("xdotool", "windowfocus", window)
        command("xdotool", "keydown", "--clearmodifiers", name)
        time.sleep(.12)
        command("xdotool", "keyup", name)
        time.sleep(.4)

    def drag(window, start, end, name):
        command("xdotool", "mousemove", "--window", window, *map(str, start))
        time.sleep(.12)
        command("xdotool", "mousedown", "1")
        time.sleep(.12)
        for step in range(1, 13):
            point = [round(a + (b - a) * step / 12) for a, b in zip(start, end)]
            command("xdotool", "mousemove", "--window", window, *map(str, point))
            time.sleep(.035)
        capture(window, name + "-dragging")
        command("xdotool", "mouseup", "1")
        time.sleep(.4)

    def settings(profile):
        with sqlite3.connect(profile / "inbe.db", timeout=3) as db:
            return dict(db.execute("SELECT key,value FROM settings WHERE user_id=?", (user,)))

    def favorites(profile):
        saved = settings(profile)
        return [int(saved[f"launcher_favorite_{i}"])
                for i in range(int(saved["launcher_favorite_count"]))]

    def seed(profile, values):
        if "enabled_apps" in values:
            for bit, name in enumerate(("lists", "habits", "practices", "diary", "lumi")):
                values["app_used_" + name] = int(bool(int(values["enabled_apps"]) & (1 << bit)))
        with sqlite3.connect(profile / "inbe.db", timeout=3) as db:
            for name, value in values.items():
                db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                           "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value",
                           (user, name, str(value)))

    @contextlib.contextmanager
    def application(profile, name, width=900, height=720):
        app_env = env | {"APP_DATA_ROOT": str(profile)}
        log_path = OUTPUT / (name + ".log")
        with log_path.open("w") as log:
            app = subprocess.Popen([str(BINARY)], cwd=ROOT, env=app_env,
                                   stdout=log, stderr=subprocess.STDOUT)
            window = ""
            try:
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    assert app.poll() is None, log_path.read_text()
                    found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                                           env=env, capture_output=True, text=True, timeout=5)
                    if found.returncode == 0 and (profile / "inbe.db").exists():
                        window = found.stdout.splitlines()[0]
                        break
                    time.sleep(.1)
                assert window, "App did not map its own window"
                command("xdotool", "windowsize", window, str(width), str(height))
                command("xdotool", "windowmove", window, "0", "0")
                command("xdotool", "windowfocus", window)
                time.sleep(.8)
                yield window, log_path
                assert app.poll() is None, log_path.read_text()
                assert "frame rejected" not in log_path.read_text(), log_path.read_text()
            except BaseException:
                if window and app.poll() is None:
                    capture(window, name + "-failure")
                raise
            finally:
                stop(app)

    layouts = ((900, 720), (390, 844))
    if arguments.layout == "desktop":
        layouts = layouts[:1]
    elif arguments.layout == "mobile":
        layouts = layouts[1:]
    for width, height in layouts:
        mobile = width < 500
        name = "mobile" if mobile else "desktop"
        with tempfile.TemporaryDirectory(prefix="inbe-launcher-") as temporary:
            profile = Path(temporary)
            with application(profile, name + "-language", width, height) as (window, log):
                first = capture(window, name + "-first-language")
                with sqlite3.connect(profile / "inbe.db") as db:
                    user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
                assert settings(profile)["language_setup_done"] == "0", "Fresh start skipped the language picker"
                assert settings(profile)["apps_setup_done"] == "0"
                assert favorites(profile) == [12, 1, 2, 3, 11], "Desktop defaults omitted installed apps"
                assert settings(profile)["theme"] == "9" and settings(profile)["theme_source"] == "0"
                assert settings(profile)["theme_mode"] == "2"
            # Merely opening and closing the picker does not complete setup.
            with application(profile, name + "-language-restart", width, height) as (window, log):
                assert settings(profile)["language_setup_done"] == "0"
                click(window, width // 2, height // 2 + 63)
                assert settings(profile)["language_setup_done"] == "1", log.read_text()
                capture(window, name + "-first-apps")
                # Practices is the third pinned card in the same grid as the rest.
                click(window, 170 if not mobile else 100, 328)
                assert settings(profile)["apps_setup_done"] == "1", log.read_text()
                assert settings(profile)["main_tab"] == "1", log.read_text()
            seed(profile, {"language": "en", "language_system": 0, "language_setup_done": 1,
                           "apps_setup_done": 1, "enabled_apps": 31, "lumi_introduced": 1,
                           "main_tab": 1, "tutorial_seen": 1, "habits_guide_seen": 1,
                           "ui_scale": 10, "navigation_placement": 0, "theme": 9,
                           "theme_source": 0, "theme_mode": 2, "cells_auto_update": 0,
                           "apps_last_update_check": 1900000000,
                           "launcher_favorite_count": 2, "launcher_favorite_0": 1,
                           "launcher_favorite_1": 2})
            apps_point = (330, height - 42) if mobile else (44, height - 144)
            pinned_first = (100, 228) if mobile else (170, 228)
            more_first = (100, 364) if mobile else (170, 364)
            with application(profile, name, width, height) as (window, log):
                page = capture(window, name + "-practice")
                if not mobile:
                    assert page.getpixel((3, height - 80)) == page.getpixel((width - 3, height - 80)), "Navigation and page use different default palettes"
                    click(window, 44, height - 60)
                    capture(window, name + "-profile")
                    before = log.read_text()
                    click(window, 110, 28)
                    assert log.read_text().count("screen=") == before.count("screen="), "Profile still has a root back button"
                click(window, *apps_point, hold=.35)
                capture(window, name + "-apps")
                assert favorites(profile) == [1, 2], "Opening Apps changed pinned cards"
                # Holding is an ordinary click. It opens the app and never pins it.
                click(window, *more_first, hold=.85)
                assert favorites(profile) == [1, 2], "Holding an app changed its pin"
                assert settings(profile)["main_tab"] == "3", log.read_text()
                click(window, *apps_point)
                drag(window, more_first, pinned_first, name + "-pin-diary")
                assert favorites(profile) == [11, 1, 2], "Dragging into Pinned did not place Diary first"
                capture(window, name + "-pinned-diary")
                # Pinned has one extra row; More now begins at y=384.
                drag(window, pinned_first, (100 if mobile else 170, 400), name + "-unpin-diary")
                assert favorites(profile) == [1, 2], "Dragging into More did not remove the shortcut"
                dock_target = (30, height - 42) if mobile else (44, 55)
                drag(window, more_first, dock_target, name + "-dock-diary")
                assert favorites(profile) == [11, 1, 2], "Dragging a card to navigation did not place it"
                capture(window, name + "-dock-placed")
                if not mobile:
                    # Footer actions remain at the bottom after favorites change.
                    click(window, 44, height - 60)
                    assert not "frame rejected" in log.read_text()
                    capture(window, name + "-profile-after-drag")
                else:
                    key(window, "Escape")
            with application(profile, name + "-restart", width, height) as (window, log):
                assert favorites(profile) == [11, 1, 2], "Restart changed personal pins"
                assert settings(profile)["language_setup_done"] == "1"
                capture(window, name + "-preserved-pins")
    print("Launcher: first-run language, desktop defaults, clean sections, click/hold/drag, profile and persistence passed")
