#!/usr/bin/env python3
"""Practice starts keep sliding navigation paint inside the app viewport.

Use the real app and Kryon tree on a private display. On Android the pixels
outside this viewport belong to the system bars and survive retained frames.
"""
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

from PIL import Image
from ui_driver import UiDriver

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/practice-start-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
ENV = {key: value for key, value in os.environ.items() if key not in (
    "DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS",
    "SESSION_MANAGER", "GDK_DISPLAY")}
ENV.update(HARMONY_DESKTOP_RECOVERY="0", YUE_DESKTOP_RECOVERY="0", APP_NO_TRAY="1",
           SDL_AUDIODRIVER="dummy", SDL_VIDEODRIVER="x11")


def stop(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def command(*arguments):
    return subprocess.check_output(arguments, env=ENV, text=True, timeout=10).strip()


def state(window):
    value = command("xprop", "-id", window, "_HARMONY_APP_STATE")
    return json.loads(ast.literal_eval(value.split(" = ", 1)[1]))


def navigation_inside_viewport(nodes):
    root = next(node for node in nodes if node["kind"] == "screen")
    navigation = {node["index"] for node in nodes if node["kind"] == "navigation_bar"}
    descendants = set(navigation)
    for node in nodes:
        if node["parent"] in descendants:
            descendants.add(node["index"])
        if node["index"] not in descendants or not node["visible"]:
            continue
        x, y = node["visible_x"], node["visible_y"]
        width, height = node["visible_width"], node["visible_height"]
        assert x >= root["x"] - 1 and y >= root["y"] - 1 and \
            x + width <= root["x"] + root["width"] + 1 and \
            y + height <= root["y"] + root["height"] + 1, \
            ("Sliding navigation escapes the content viewport", root, node)
    return bool(navigation)


with contextlib.ExitStack() as stack:
    display_log = stack.enter_context((OUTPUT / "display.log").open("w"))
    display = subprocess.Popen(["Xvfb", "-noreset", "-displayfd", "1", "-screen", "0",
                                "1000x1000x24", "-nolisten", "tcp"], env=ENV,
                               stdout=subprocess.PIPE, stderr=display_log)
    stack.callback(stop, display)
    number = display.stdout.readline().decode().strip()
    display.stdout.close()
    assert number.isdecimal() and display.poll() is None, "Private display did not start"
    ENV["DISPLAY"] = ":" + number
    driver = UiDriver(OUTPUT / "driver")
    ENV.update(driver.environment())
    profile = Path(stack.enter_context(tempfile.TemporaryDirectory(dir=OUTPUT, prefix="profile-")))
    ENV["APP_DATA_ROOT"] = str(profile)

    @contextlib.contextmanager
    def application(label):
        log_path = OUTPUT / (label + ".log")
        with log_path.open("w") as log:
            app = subprocess.Popen([sys.argv[1]], cwd=ROOT, env=ENV, stdout=log, stderr=log)
            driver.attach(app, log_path)
            try:
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    assert app.poll() is None, "App exited during startup"
                    found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                                           env=ENV, capture_output=True, text=True, timeout=5)
                    if found.returncode == 0 and (profile / "inbe.db").exists():
                        window = found.stdout.splitlines()[0]
                        command("xdotool", "windowsize", window, "390", "844")
                        driver.wait(role="screen")
                        yield window
                        break
                    time.sleep(.1)
                else:
                    raise AssertionError("App window did not appear")
            finally:
                stop(app)

    with application("initialize"):
        driver.wait_idle()

    for placement, edge in ((2, "bottom"), (4, "top"), (1, "left"), (3, "right")):
        for page, tab in (("practice", 1), ("lumi", 4)):
            with sqlite3.connect(profile / "inbe.db") as db:
                user = db.execute("SELECT id FROM users LIMIT 1").fetchone()[0]
                settings = dict(language="en", language_setup_done=1, apps_setup_done=1,
                                tutorial_seen=1, habits_guide_seen=1, lumi_guides_seen=127,
                                launcher_guide_seen=1, lumi_introduced=1, lumi_online=0,
                                package_updates_allowed=0, enabled_apps=63, main_tab=tab,
                                theme=9, theme_source=0, theme_mode=1, ui_scale=10,
                                navigation_placement=placement, picture_in_picture=0,
                                voice_narration_enabled=0, guide_narration_enabled=0, audio_enabled=0, music_volume=0,
                                app_last_seen_version="2.1.63")
                for key, value in settings.items():
                    db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                               "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value",
                               (user, key, str(value)))
            label = edge + "-" + page
            with application(label) as window:
                for repetition in range(2):
                    if page == "practice":
                        driver.press(label="Start Practice", settle=False)
                    else:
                        driver.press(role="text_area")
                        driver.type("start whm")
                        driver.key("enter")
                    deadline = time.monotonic() + 8
                    try:
                        while True:
                            nodes = driver.tree()
                            has_navigation = navigation_inside_viewport(nodes)
                            if state(window)["practice_running"] and not has_navigation:
                                break
                            assert time.monotonic() < deadline, "Practice navigation did not retract"
                        assert state(window)["screen"] == 1, "WHM did not start"
                        path = OUTPUT / (label + "-" + str(repetition) + ".png")
                        command("import", "-window", window, str(path))
                        with Image.open(path) as picture:
                            # Empty strips under the old dock and beside the circle
                            # must contain only canvas, not the old page or dock.
                            for bounds in ((0, 760, 390, 840), (0, 100, 30, 260),
                                           (360, 100, 390, 260)):
                                assert len(picture.crop(bounds).getcolors(2) or []) == 1, \
                                    (label, repetition, "Stale paint below navigation", bounds)
                    except BaseException:
                        (OUTPUT / (label + "-failure.json")).write_text(json.dumps(driver.last, indent=2))
                        raise
                    driver.press(label="Close")
                    driver.press(label="Exit")
                    driver.press(label="Practice" if page == "practice" else "Lumi", role="button")
                    if page == "practice":
                        driver.wait(label="Start Practice")
                    else:
                        driver.wait(role="text_area")
print("Practice starts: mono scale 10, all navigation edges, Lumi and Practice, repeated starts stay clipped and clear")
