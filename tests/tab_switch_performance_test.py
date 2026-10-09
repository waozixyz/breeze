"""Measure real dock clicks with a disposable profile and an owned Xvfb."""
import ast
import contextlib
import json
import os
from pathlib import Path
import re
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/tab-switch-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
DISPLAY_KEYS = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS")
assert all(not os.environ.get(key) for key in DISPLAY_KEYS), "Inherited desktop environment"
BINARY = Path(sys.argv[1]).resolve()
LABEL = sys.argv[2]
WIDTH, HEIGHT = (390, 844) if "--mobile" in sys.argv else (900, 720)
RAPID = "--rapid" in sys.argv


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


with tempfile.TemporaryDirectory(prefix="inbe-tab-switch-") as temporary, contextlib.ExitStack() as stack:
    profile = Path(temporary)
    env = {key: value for key, value in os.environ.items() if key not in DISPLAY_KEYS}
    env.update(YUE_DESKTOP_RECOVERY="0", APP_NO_TRAY="1", SDL_AUDIODRIVER="dummy",
               SDL_VIDEODRIVER="x11", LIBGL_ALWAYS_SOFTWARE="1",
               APP_DATA_ROOT=str(profile), APP_PROFILE="1", INBE_DEBUG_ROUTE="1")
    display_log = stack.enter_context((OUTPUT / (LABEL + "-display.log")).open("w"))
    display = subprocess.Popen(["Xvfb", "-displayfd", "1", "-screen", "0", "1280x1000x24",
                                "-nolisten", "tcp"], env=env, stdout=subprocess.PIPE, stderr=display_log)
    stack.callback(stop, display)
    number = display.stdout.readline().decode().strip()
    display.stdout.close()
    assert number.isdecimal(), "Private Xvfb failed to start"
    env["DISPLAY"] = ":" + number

    def command(*args):
        return subprocess.check_output(args, env=env, text=True, timeout=5).strip()

    @contextlib.contextmanager
    def application(name):
        log_path = OUTPUT / (LABEL + "-" + name + ".log")
        with log_path.open("w") as log:
            app = subprocess.Popen([str(BINARY)], cwd=ROOT, env=env,
                                   stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 20
                window = ""
                while time.monotonic() < deadline:
                    assert app.poll() is None, log_path.read_text()[-3000:]
                    found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                                           env=env, capture_output=True, text=True, timeout=2)
                    if found.returncode == 0 and found.stdout.strip():
                        for candidate in found.stdout.splitlines():
                            property_text = command("xprop", "-id", candidate, "_HARMONY_APP_STATE")
                            if "harmony.app-state.v1" in property_text:
                                window = candidate
                                break
                        if window:
                            break
                    time.sleep(.05)
                assert window, "Owned test window did not appear"
                deadline = time.monotonic() + 20
                while "APP PROBE: drawing ended" not in log_path.read_text():
                    assert app.poll() is None, log_path.read_text()[-3000:]
                    assert time.monotonic() < deadline, "App did not draw its first frame"
                    time.sleep(.05)
                if name != "prepare":
                    command("xdotool", "windowsize", window, str(WIDTH), str(HEIGHT))
                    command("xdotool", "windowmove", window, "0", "0")
                    deadline = time.monotonic() + 20
                    ready = OUTPUT / (LABEL + "-" + name + "-ready.png")
                    while True:
                        assert app.poll() is None, log_path.read_text()[-3000:]
                        command("import", "-window", window, str(ready))
                        with Image.open(ready) as image:
                            if image.size == (WIDTH, HEIGHT) and any(
                                    high - low > 24 for low, high in image.convert("RGB").getextrema()):
                                break
                        assert time.monotonic() < deadline, "App did not render the requested viewport"
                        time.sleep(.05)
                    command("xdotool", "windowfocus", window)
                    time.sleep(.2)
                yield app, window, log_path
            finally:
                stop(app)

    with application("prepare"):
        pass
    with sqlite3.connect(profile / "inbe.db") as db:
        user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
        values = {"language": "en", "language_system": 0, "language_setup_done": 1,
                  "apps_setup_done": 1, "enabled_apps": 31, "lumi_introduced": 1,
                  "cells_auto_update": 0, "apps_last_update_check": 1900000000,
                  "tutorial_seen": 1, "habits_guide_seen": 1, "launcher_guide_seen": 1,
                  "ui_scale": 10, "navigation_placement": 0 if WIDTH < 500 else 1,
                  "navigation_collapsed": 0, "launcher_favorite_count": 5, "main_tab": 3,
                  **{f"launcher_favorite_{i}": route for i, route in enumerate((3, 1, 2, 11, 12))},
                  **{f"app_used_{name}": 1 for name in ("lists", "habits", "practices", "diary", "lumi")}}
        for key, value in values.items():
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                       "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user, key, str(value)))

    samples = []
    with application("clicks") as (app, window, log_path):
        def state():
            prop = command("xprop", "-id", window, "_HARMONY_APP_STATE")
            if " = " not in prop:
                return {}
            return json.loads(ast.literal_eval(prop.split(" = ", 1)[1]))

        command("import", "-window", window, str(OUTPUT / (LABEL + "-initial.png")))
        points = [(44, 60 + i * 84) for i in range(5)] if WIDTH >= 500 else [
            (round(12 + i * 62 + 27), HEIGHT - 26) for i in range(5)]
        screens = (16, 11, 0, 22, 23)
        names = ("lists", "habits", "practices", "diary", "lumi")
        for cycle in range(3):
            for name, expected, (x, y) in zip(names, screens, points):
                command("xdotool", "mousemove", "--window", window, str(x), str(y))
                time.sleep(.01 if RAPID else .08)
                command("xdotool", "mousedown", "1")
                time.sleep(.05 if RAPID else .08)
                started = time.monotonic()
                command("xdotool", "mouseup", "1")
                deadline = started + 2
                while state().get("screen") != expected:
                    assert app.poll() is None, "Application exited during navigation"
                    if time.monotonic() >= deadline:
                        command("import", "-window", window, str(OUTPUT / (LABEL + "-failure.png")))
                        raise AssertionError(f"{name} click was lost: {log_path.read_text()[-2000:]}")
                    time.sleep(.005)
                elapsed = (time.monotonic() - started) * 1000
                assert elapsed < 150, f"{name} took {elapsed:.1f} ms after release"
                with sqlite3.connect(profile / "inbe.db") as db:
                    saved_tab = db.execute("SELECT value FROM settings WHERE user_id=? AND key='main_tab'",
                                           (user,)).fetchone()[0]
                    expected_tab = (2, 0, 1, 3, 4)[names.index(name)]
                    assert int(saved_tab) == expected_tab, f"{name}: saved tab {saved_tab}, expected {expected_tab}"
                samples.append({"cycle": cycle, "tab": name, "response_ms": round(elapsed, 2)})
                print(json.dumps(samples[-1]), flush=True)
                if name == "practices" and cycle == 0:
                    time.sleep(.18)
                    screenshot = OUTPUT / (LABEL + "-practices.png")
                    command("import", "-window", window, str(screenshot))
                    with Image.open(screenshot) as image:
                        if WIDTH < 500:
                            apps = image.crop((WIDTH - 74, HEIGHT - 48, WIDTH - 14, HEIGHT - 4))
                        else:
                            apps = image.crop((14, 465, 74, 495))
                        assert any(high - low > 24 for low, high in apps.convert("RGB").getextrema()), \
                            "Practice content covered the Apps shortcut"
                if not RAPID:
                    time.sleep(.16)
        # Finish on Lists so restart cannot pass by returning to the default tab.
        x, y = points[0]
        command("xdotool", "mousemove", "--window", window, str(x), str(y))
        time.sleep(.02)
        command("xdotool", "mousedown", "1")
        time.sleep(.03)
        command("xdotool", "mouseup", "1")
        deadline = time.monotonic() + 2
        while state().get("screen") != screens[0]:
            assert time.monotonic() < deadline, "Final Lists click was lost"
            time.sleep(.005)
        time.sleep(4)
        command("import", "-window", window, str(OUTPUT / (LABEL + "-final.png")))
        log = log_path.read_text()
        assert "frame rejected" not in log and "portable execution failed" not in log, log[-3000:]
        reports = [float(value) for value in re.findall(r"PROFILE: frame avg=([\d.]+)", log)]
        result = {"viewport": [WIDTH, HEIGHT], "private_display": True, "samples": samples,
                  "median_response_ms": round(statistics.median(s["response_ms"] for s in samples), 2),
                  "max_response_ms": max(s["response_ms"] for s in samples), "frame_ms": reports}
        (OUTPUT / (LABEL + ".json")).write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result), flush=True)

    with application("restart") as (app, window, log_path):
        prop = command("xprop", "-id", window, "_HARMONY_APP_STATE")
        restored = json.loads(ast.literal_eval(prop.split(" = ", 1)[1]))
        assert restored["screen"] == 16, "Restart did not restore the last tab"
        with sqlite3.connect(profile / "inbe.db") as db:
            pins = [int(db.execute("SELECT value FROM settings WHERE user_id=? AND key=?",
                                   (user, f"launcher_favorite_{i}")).fetchone()[0]) for i in range(5)]
            assert pins == [3, 1, 2, 11, 12], "Switching tabs changed pins"
        print("Last tab and pins survive restart", flush=True)
