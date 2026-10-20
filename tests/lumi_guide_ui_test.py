"""Lumi's practice guide on a private Xvfb display: she types each step,
a tap shows the whole text, the next tap goes on, and the keys still work.

The app is driven through Kryon's test driver: the guide is found in its
widget tree and tapped through its own pointer path. The guide reads Left,
Right and Escape outside the driver, so those keys are sent to the app's own
window with xdotool.

Run it inside a private D-Bus, with the desktop's display scrubbed:
    env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \\
        dbus-run-session -- python3 tests/lumi_guide_ui_test.py BINARY
"""

import contextlib
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
OUTPUT = ROOT / "build/lumi-guide-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
BINARY = Path(sys.argv[1]).resolve()
DESKTOP_ENV = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY")
assert all(not os.environ.get(key) for key in DESKTOP_ENV), "Inherited desktop environment"
# Only a private bus, such as dbus-run-session's, may be passed on.
USER_BUS = "unix:path=" + os.environ.get("XDG_RUNTIME_DIR", "/run/user/%d" % os.getuid()) + "/bus"
assert os.environ.get("DBUS_SESSION_BUS_ADDRESS", "") != USER_BUS, "Inherited the desktop's session bus"
WIDTH, HEIGHT = 900, 720
# Pixels this far from the bubble's colour are ink.
INK = 60


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def inside(point, node):
    x, y = point
    return (node["x"] <= x < node["x"] + node["width"] and
            node["y"] <= y < node["y"] + node["height"])


with contextlib.ExitStack() as stack:
    driver = UiDriver(OUTPUT / "driver")
    env = {key: value for key, value in os.environ.items() if key not in DESKTOP_ENV}
    env.update(YUE_DESKTOP_RECOVERY="0", APP_NO_TRAY="1", SDL_AUDIODRIVER="dummy")
    env.update(driver.environment())
    # Lumi speaks; keep her voice off the desktop's sound server.
    runtime = stack.enter_context(tempfile.TemporaryDirectory(prefix="runtime-", dir=OUTPUT))
    env.update(XDG_RUNTIME_DIR=runtime, PULSE_SERVER="unix:" + runtime + "/no-pulse")
    display_log = stack.enter_context((OUTPUT / "display.log").open("w"))
    display = subprocess.Popen(["Xvfb", "-displayfd", "1", "-screen", "0", "1280x1000x24",
                                "-nolisten", "tcp"], env=env, stdout=subprocess.PIPE,
                               stderr=display_log)
    stack.callback(stop, display)
    number = display.stdout.readline().decode().strip()
    display.stdout.close()
    assert number.isdecimal(), "Private display did not start"
    env["DISPLAY"] = ":" + number

    def command(*args):
        return subprocess.run(args, env=env, check=True, capture_output=True,
                              text=True, timeout=20).stdout.strip()

    def tap(point):
        """Tap the app at a point of its widget tree, through its pointer."""
        driver.pointer(*point)
        driver.pointer(*point, down=True)
        driver.pointer(*point, down=False)
        driver.release_pointer()

    def key(window, name):
        """Left, Right and Escape reach the guide outside the test driver.
        The key stays down for a few frames, so a slow frame cannot miss it."""
        command("xdotool", "windowfocus", window)
        command("xdotool", "keydown", "--clearmodifiers", name)
        time.sleep(.15)
        wait_frames(3)
        command("xdotool", "keyup", name)
        wait_frames(2)

    def settings(profile, user):
        with sqlite3.connect(profile / "inbe.db", timeout=3) as db:
            return dict(db.execute("SELECT key,value FROM settings WHERE user_id=?", (user,)))

    def wait_setting(profile, user, name, value):
        deadline = time.monotonic() + 5
        while settings(profile, user).get(name, "0") != value:
            assert time.monotonic() < deadline, (name, value, settings(profile, user).get(name))
            time.sleep(.05)

    def seed(profile, user, values):
        with sqlite3.connect(profile / "inbe.db", timeout=3) as db:
            for name, value in values.items():
                db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                           "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value",
                           (user, name, str(value)))

    def landed_lumi(title):
        """Lumi's picture once her flight to the bubble has ended: she is
        beside its title and only bobs there."""
        places = []
        deadline = time.monotonic() + 10
        while True:
            found = driver.find(label="Lumi", role="image", visible=True)
            if found and found[-1]["y"] + found[-1]["height"] >= title["y"]:
                places.append(found[-1])
            else:
                places = []
            recent = places[-3:]
            if len(recent) == 3 and all(abs(place["x"] - recent[0]["x"]) < 4 and
                                        abs(place["y"] - recent[0]["y"]) < 8 for place in recent):
                return recent[-1]
            assert time.monotonic() < deadline, "Lumi did not land by the guide"
            time.sleep(.1)

    def wait_frames(count):
        """Let the app draw a few more frames."""
        first = driver.send("status")["frame"]
        deadline = time.monotonic() + 5
        while driver.send("status")["frame"] < first + count:
            assert time.monotonic() < deadline, "The app stopped drawing"
            time.sleep(.02)

    def ink(image, box, skip):
        """How many pixels in box differ from its most common colour,
        leaving out the rectangle skip."""
        crop = image.crop(box)
        histogram = crop.histogram()
        background = max(range(256), key=lambda value: histogram[value])
        pixels = crop.load()
        count = 0
        for y in range(crop.height):
            for x in range(crop.width):
                if skip[0] <= box[0] + x < skip[2] and skip[1] <= box[1] + y < skip[3]:
                    continue
                if abs(pixels[x, y] - background) > INK:
                    count += 1
        return count

    def still_typing(window, title, paragraph, lumi):
        """The one pixel check: while Lumi types, the step's title is drawn
        but the last line of her text is not there yet."""
        screen = driver.wait(role="screen")
        path = OUTPUT / "typing.png"
        command("import", "-window", window, str(path))
        with Image.open(path) as captured:
            image = captured.convert("L")
        scale = image.width / screen["width"]

        def box(node, top_part=0.0, margin=0):
            left = (node["x"] - screen["x"]) * scale
            top = (node["y"] - screen["y"] + node["height"] * top_part) * scale
            return (round(left) - margin, round(top) - margin,
                    round(left + node["width"] * scale) + margin,
                    round((node["y"] - screen["y"] + node["height"]) * scale) + margin)

        lumi_box = box(lumi, margin=round(12 * scale))
        title_ink = ink(image, box(title), lumi_box)
        last_line_ink = ink(image, box(paragraph, top_part=0.5), lumi_box)
        assert title_ink > 0, "The guide's step title is not drawn"
        assert last_line_ink == 0, f"The whole step appeared at once ({last_line_ink} ink pixels)"
        # A failure keeps the capture to look at; a pass leaves none behind.
        path.unlink()

    @contextlib.contextmanager
    def application(profile, name):
        app_env = env | {"APP_DATA_ROOT": str(profile)}
        log_path = OUTPUT / (name + ".log")
        with log_path.open("w") as log:
            app = subprocess.Popen([str(BINARY)], cwd=ROOT, env=app_env,
                                   stdout=log, stderr=subprocess.STDOUT)
            driver.attach(app, log_path)
            try:
                window = ""
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline and not window:
                    assert app.poll() is None, log_path.read_text()
                    found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid",
                                            str(app.pid)], env=env, capture_output=True,
                                           text=True, timeout=5)
                    if found.returncode == 0 and (profile / "inbe.db").exists():
                        window = found.stdout.splitlines()[0]
                    time.sleep(.1)
                assert window, "App did not map its own window"
                command("xdotool", "windowsize", window, str(WIDTH), str(HEIGHT))
                command("xdotool", "windowmove", window, "0", "0")
                command("xdotool", "windowfocus", window)
                yield window, log_path
                assert app.poll() is None, log_path.read_text()
                assert "frame rejected" not in log_path.read_text(), log_path.read_text()
            finally:
                stop(app)

    with tempfile.TemporaryDirectory(prefix="inbe-lumi-guide-", dir=OUTPUT) as temporary:
        profile = Path(temporary)
        with application(profile, "initialize"):
            driver.wait(role="screen")
            driver.wait_idle(frames=3)
        with sqlite3.connect(profile / "inbe.db") as db:
            user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
        seed(profile, user, {"language": "en", "language_system": 0, "language_setup_done": 1,
                             "apps_setup_done": 1, "launcher_guide_seen": 1, "main_tab": 1,
                             "tutorial_seen": 0, "tutorial_step": 0, "habits_guide_seen": 1, "lumi_guides_seen": 255,
                             "package_updates_allowed": 0, "apps_last_update_check": 1900000000})
        with application(profile, "guide") as (window, log):
            # Bundled practices make the carousel the first of three steps.
            # Lumi flies in and starts typing; the whole line is not there yet.
            title = driver.wait(label="Step 1 of 3")
            paragraph = driver.wait(contains="your practices", role="text")
            lumi = landed_lumi(title)
            still_typing(window, title, paragraph, lumi)
            # A tap on the bubble, while she types, shows the whole line and
            # stays on it.
            driver.press(contains="your practices", role="text", settle=False)
            wait_frames(3)
            driver.wait(label="Step 1 of 3")
            assert settings(profile, user).get("tutorial_step", "0") == "0", "The tap left the typed step"
            # The next tap, anywhere but a button, goes to the next step:
            # the whole line was there.
            guide = driver.wait(key=83100, role="modal")
            bubble = driver.wait(contains="your practices", role="text")
            point = (guide["x"] + 32, guide["y"] + 120)
            assert inside(point, guide) and not inside(point, bubble), point
            assert not [node for node in driver.find(role="button", visible=True)
                        if inside(point, node) and node["key"] in (83110, 83111, 83112)], point
            tap(point)
            driver.wait(label="Step 2 of 3")
            wait_setting(profile, user, "tutorial_step", "1")
            # Left goes back and Right goes on, whatever is typed.
            key(window, "Left")
            driver.wait(label="Step 1 of 3")
            key(window, "Right")
            driver.wait(label="Step 2 of 3")
            key(window, "Right")
            driver.wait(label="Step 3 of 3")
            wait_setting(profile, user, "tutorial_step", "2")
            key(window, "Left")
            driver.wait(label="Step 2 of 3")
            # Escape closes the guide for good.
            key(window, "Escape")
            driver.wait_gone(label="Step 2 of 3")
            assert not driver.find(label="Step 1 of 3"), "Escape went back instead of closing"
            assert not driver.find(label="Step 3 of 3"), "Escape advanced instead of closing"
            wait_setting(profile, user, "tutorial_seen", "1")
print("Lumi guide UI test passed")
