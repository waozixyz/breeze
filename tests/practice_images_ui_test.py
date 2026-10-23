#!/usr/bin/env python3
"""Every practice shows its picture, and a running Sun Salutation its figure."""
import ast
import contextlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

from PIL import Image, ImageChops, ImageStat

from ui_driver import UiDriver

DISPLAY_KEYS = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS")
assert all(not os.environ.get(key) for key in DISPLAY_KEYS), "Inherited desktop environment"
root = Path(__file__).resolve().parents[1]
binary = Path(sys.argv[1]).resolve()
output = root / "build/practice-images-ui-test"
output.mkdir(parents=True, exist_ok=True)
WIDTH, HEIGHT = 390, 844
PRACTICES = ("wim-hof", "patterns", "meditation", "astral-projection",
             "sun-salutation", "tai-chi", "workout")
driver = UiDriver(output / "driver")
environment = os.environ | driver.environment() | {
    "SDL_VIDEODRIVER": "x11", "SDL_AUDIODRIVER": "dummy",
    "YUE_DESKTOP_RECOVERY": "0", "APP_NO_TRAY": "1"}


def command(*args):
    return subprocess.check_output(args, env=environment, text=True, timeout=5).strip()


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


def state(window):
    value = command("xprop", "-id", window, "_HARMONY_APP_STATE")
    assert " = " in value, "App has not published its state"
    return json.loads(ast.literal_eval(value.split(" = ", 1)[1]))


def pause(window, paused, request):
    control = "practice.pause" if paused else "practice.resume"
    command("xprop", "-id", window, "-f", "_HARMONY_APP_ACTION", "8s", "-set",
            "_HARMONY_APP_ACTION", json.dumps(dict(control=control, request_id=request)))
    deadline = time.monotonic() + 5
    while state(window)["last_request_id"] != request:
        assert time.monotonic() < deadline, "Pause action was not handled"
        time.sleep(.05)
    actual = state(window)
    assert actual["last_request_ok"] and actual["paused"] == paused, actual


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
    app = subprocess.Popen([str(binary)], cwd=root, env=environment | {"APP_DATA_ROOT": str(profile)},
                           stdout=log, stderr=subprocess.STDOUT)
    driver.attach(app, output / (name + ".log"))
    for _ in range(200):
        assert app.poll() is None, (output / (name + ".log")).read_text()
        found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                               env=environment, capture_output=True, text=True)
        if found.returncode == 0 and (profile / "inbe.db").exists():
            window = found.stdout.splitlines()[0]
            command("xdotool", "windowsize", window, str(WIDTH), str(HEIGHT))
            command("xdotool", "windowmove", window, "0", "0")
            time.sleep(1.5)
            return app, window
        time.sleep(0.1)
    stop(app)
    raise AssertionError("Inbe did not map its window")


with tempfile.TemporaryDirectory(prefix="inbe-practice-images-") as directory, contextlib.ExitStack() as stack:
    display_log = stack.enter_context((output / "display.log").open("w"))
    display = subprocess.Popen(["Xvfb", "-noreset", "-displayfd", "1", "-screen", "0", "1280x900x24",
                                "-nolisten", "tcp"], env=environment,
                               stdout=subprocess.PIPE, stderr=display_log)
    stack.callback(stop, display)
    number = display.stdout.readline().decode().strip()
    display.stdout.close()
    assert number.isdecimal() and display.poll() is None, "Private display did not start"
    server = Path(f"/proc/{display.pid}")
    assert server.stat().st_uid == os.getuid(), "Private X server has another owner"
    assert server.joinpath("exe").resolve() == Path(shutil.which("Xvfb")).resolve(), "Unexpected X server"
    assert b"-displayfd\x001\x00" in server.joinpath("cmdline").read_bytes(), "Unexpected display allocation source"
    display_log.write(f"Verified owned Xvfb pid={display.pid} display=:{number}\n")
    display_log.flush()
    environment["DISPLAY"] = ":" + number
    profile = Path(directory)
    cache = profile / "packages"
    cache.mkdir()
    # Start the real practice offline. A cover on the Install screen must
    # never count as the running guide, even though both contain a picture.
    for name in ("sunsalutation", "guide.en"):
        shutil.copyfile(root / "build/practice-content" / (name + ".zib"),
                        cache / ("practice-" + name + ".zib"))
    app, _ = launch(profile, "first-start")
    stop(app)
    with sqlite3.connect(profile / "inbe.db") as db:
        user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
        settings = {"language": "en", "language_system": 0, "language_setup_done": 1,
                    "apps_setup_done": 1, "main_tab": 1, "tutorial_seen": 1,
                    "habits_guide_seen": 1, "lumi_guides_seen": 127, "launcher_guide_seen": 1, "package_updates_allowed": 0,
                    "voice_narration_enabled": 0, "music_volume": 0,
                    "sun_salutation_character": 0,
                    "sun_salutation_start_seconds": 6, "sun_salutation_end_seconds": 6,
                    "apps_last_update_check": 1900000000}
        for key, value in settings.items():
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                       "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value",
                       (user, key, str(value)))
    app, window = launch(profile, "practice")
    try:
        missing = []
        for index, practice in enumerate(PRACTICES):
            if 0 < index < 4:
                click(window, 324, 620)  # The next meditation practice.
            elif index == 4:
                click(window, 145, 24)  # Yoga.
            elif index == 5:
                click(window, 235, 24)  # Martial arts.
            elif index == 6:
                click(window, 325, 24)  # Workout.
            if not pictured(capture(window, practice), (0, 40, WIDTH, 420)):
                missing.append(practice)
        click(window, 145, 24)  # Yoga.
        driver.wait(label="Start Practice", role="button")
        driver.press(label="How to", role="button")
        driver.wait(contains="Mountain")
        capture(window, "sun-salutation-guide")
        driver.press(label="Back", role="button")
        driver.press(label="Start Practice", role="button")
        driver.wait(label="Next", role="button")
        actual = state(window)
        assert actual["practice_running"] and actual["screen"] == 3, actual
        deadline = time.monotonic() + 5
        while any(node["kind"] == "navigation_bar" and node["visible"] for node in driver.tree()):
            assert time.monotonic() < deadline, "Practice navigation did not retract"
            time.sleep(.05)
        next_button = driver.wait(label="Next", role="button")
        assert next_button["height"] >= 44 and next_button["y"] + next_button["height"] <= HEIGHT, \
            "Practice controls are clipped"
        figure = (24, 240, WIDTH - 24, round(next_button["y"] - 18))
        running = capture(window, "sun-salutation-running")
        if not pictured(running, figure):
            missing.append("sun-salutation figure")
        # This interior patch contains the jade cloth and its wrap shadow,
        # whose green channels are 143 and 123. Retained-frame alpha errors
        # add dark seams between the opaque, adjoining illustration pieces.
        cloth = running.crop((175, 450, 195, 510))
        assert cloth.getchannel("G").getextrema()[0] >= 115, \
            "The retained guide has dark seams across its clothing"
        driver.press(label="Next", role="button", settle=False)
        time.sleep(.5)
        first = capture(window, "sun-salutation-moving-first").crop(figure)
        time.sleep(1)
        second = capture(window, "sun-salutation-moving-second").crop(figure)
        assert ImageChops.difference(first, second).getbbox(), "The live guide did not move"
        pause(window, True, "practice-images-pause")
        time.sleep(.2)
        first = capture(window, "sun-salutation-paused-first").crop(figure)
        time.sleep(.6)
        second = capture(window, "sun-salutation-paused-second").crop(figure)
        assert not ImageChops.difference(first, second).getbbox(), "The paused guide kept moving"
        pause(window, False, "practice-images-resume")
        time.sleep(.5)
        resumed = capture(window, "sun-salutation-resumed").crop(figure)
        assert ImageChops.difference(second, resumed).getbbox(), "The guide did not resume"
        assert not missing, "Practice pictures are missing: " + ", ".join(missing)
        assert app.poll() is None, (output / "practice.log").read_text()
    finally:
        stop(app)
print("All seven practice covers, Sun Salutation guide, real session, animation, pause and resume passed")
