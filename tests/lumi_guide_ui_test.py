"""Lumi's practice guide on a private Xvfb display: she types each step,
a tap shows the whole text, the next tap goes on, and the keys still work.

Run it inside a private D-Bus, with the desktop's display scrubbed:
    env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
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
    env.update(YUE_DESKTOP_RECOVERY="0", APP_NO_TRAY="1", SDL_AUDIODRIVER="dummy")
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

    def capture(window, name):
        path = OUTPUT / (name + ".png")
        command("import", "-window", window, str(path))
        with Image.open(path) as image:
            return image.convert("RGB").copy()

    def text(window, name):
        """The words on screen, read from enlarged captures. The small step
        label over the picture reads best in larger grey."""
        image = capture(window, name)
        enlarged = OUTPUT / (name + "-ocr.png")
        image.resize((image.width * 2, image.height * 2)).save(enlarged)
        grey = OUTPUT / (name + "-ocr-grey.png")
        image.convert("L").resize((image.width * 3, image.height * 3)).save(grey)
        return " ".join((command("tesseract", str(enlarged), "stdout", "--psm", "11") + " " +
                         command("tesseract", str(grey), "stdout", "--psm", "11")).lower().split())

    def click(window, x, y):
        command("xdotool", "mousemove", "--window", window, str(x), str(y))
        time.sleep(.12)
        command("xdotool", "mousedown", "1")
        time.sleep(.1)
        command("xdotool", "mouseup", "1")
        time.sleep(.5)

    def key(window, name):
        command("xdotool", "windowfocus", window)
        command("xdotool", "keydown", "--clearmodifiers", name)
        time.sleep(.12)
        command("xdotool", "keyup", name)
        time.sleep(.5)

    def settings(profile, user):
        with sqlite3.connect(profile / "inbe.db", timeout=3) as db:
            return dict(db.execute("SELECT key,value FROM settings WHERE user_id=?", (user,)))

    def seed(profile, user, values):
        with sqlite3.connect(profile / "inbe.db", timeout=3) as db:
            for name, value in values.items():
                db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                           "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value",
                           (user, name, str(value)))

    @contextlib.contextmanager
    def application(profile, name):
        app_env = env | {"APP_DATA_ROOT": str(profile)}
        log_path = OUTPUT / (name + ".log")
        with log_path.open("w") as log:
            app = subprocess.Popen([str(BINARY)], cwd=ROOT, env=app_env,
                                   stdout=log, stderr=subprocess.STDOUT)
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
            time.sleep(1)
        with sqlite3.connect(profile / "inbe.db") as db:
            user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
        seed(profile, user, {"language": "en", "language_system": 0, "language_setup_done": 1,
                             "apps_setup_done": 1, "launcher_guide_seen": 1, "main_tab": 1,
                             "tutorial_seen": 0, "tutorial_step": 0, "habits_guide_seen": 1, "lumi_guides_seen": 127,
                             "package_updates_allowed": 0, "apps_last_update_check": 1900000000})
        with application(profile, "guide") as (window, log):
            # A first start has only Wim Hof installed, so there is no
            # carousel step: the guide begins at Start. Lumi flies in and
            # starts typing her first line; it is not all there yet.
            time.sleep(1.6)
            typing = text(window, "1-typing")
            assert "step 1 of 2" in typing, typing
            assert "follow along" not in typing, "The first line appeared at once: " + typing
            # A tap on the bubble shows the whole line and stays on it.
            click(window, 450, 460)
            shown = text(window, "2-shown")
            assert "step 1 of 2" in shown and "follow along" in shown, shown
            assert settings(profile, user).get("tutorial_step", "0") == "0"
            # The next tap, anywhere but a button, goes to the next step.
            click(window, 120, 120)
            second = text(window, "3-second")
            assert "step 2 of 2" in second, second
            assert settings(profile, user)["tutorial_step"] == "1"
            # Left goes back and Right goes on, whatever is typed.
            key(window, "Left")
            assert "step 1 of 2" in text(window, "4-back")
            key(window, "Right")
            assert "step 2 of 2" in text(window, "5-again")
            # Escape closes the guide for good.
            key(window, "Escape")
            closed = text(window, "6-closed")
            assert "step 1 of 2" not in closed and "step 2 of 2" not in closed, closed
            assert settings(profile, user)["tutorial_seen"] == "1"
print("Lumi guide UI test passed")
