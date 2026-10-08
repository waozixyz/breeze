"""Zoom the real app with Ctrl and the wheel on the display owned by the shell harness."""

import os
from pathlib import Path
import sqlite3
import shutil
import subprocess
import sys
import tempfile
import time

from PIL import Image, ImageChops


root = Path(__file__).resolve().parent.parent
output = root / "build/native-zoom-test"
output.mkdir(parents=True, exist_ok=True)
assert int(os.environ["DISPLAY"].split(":")[-1].split(".")[0]) >= 300
data = Path(tempfile.mkdtemp(prefix="inbe-zoom-", dir=output))
env = os.environ.copy()
for name in ("WAYLAND_DISPLAY", "GDK_DISPLAY", "DBUS_SESSION_BUS_ADDRESS"):
    env.pop(name, None)
env["APP_NO_TRAY"] = "1"
env["XDG_DATA_HOME"] = str(data / "data")
env["XDG_CONFIG_HOME"] = str(data / "config")
env["XDG_CACHE_HOME"] = str(data / "cache")
os.makedirs(env["XDG_DATA_HOME"])


def command(*args):
    return subprocess.run(args, env=env, check=True, text=True,
                          capture_output=True, timeout=5).stdout.strip()


def capture(window, name):
    raw = output / f"{name}.xwd"
    png = output / f"{name}.png"
    command("xwd", "-silent", "-id", window, "-out", str(raw))
    command("convert", str(raw), str(png))
    raw.unlink()
    with Image.open(png) as image:
        return image.convert("RGB").copy()


def content_width(image):
    """Width of everything drawn on the flat background."""
    background = Image.new("RGB", image.size, image.getpixel((5, 5)))
    drawn = ImageChops.difference(image, background).convert("L")
    box = drawn.point(lambda value: 255 if value > 24 else 0).getbbox()
    assert box, "nothing was drawn"
    return box[2] - box[0]


def saved_scale():
    database = Path(env["XDG_DATA_HOME"]) / "inbe/inbe.db"
    if not database.exists():
        return None
    with sqlite3.connect(f"file:{database}?mode=ro", uri=True, timeout=2) as db:
        row = db.execute("select value from settings where key = 'ui_scale'").fetchone()
    return int(row[0]) if row else None


def wait_for_scale(expected, seconds=5):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if saved_scale() == expected:
            return True
        time.sleep(0.1)
    return False


def wheel(window, direction, notches, control=True):
    command("xdotool", "mousemove", "--window", window, "450", "400")
    if control:
        command("xdotool", "keydown", "ctrl")
    for _ in range(notches):
        command("xdotool", "click", "4" if direction > 0 else "5")
        time.sleep(0.12)
    if control:
        command("xdotool", "keyup", "ctrl")
    time.sleep(0.6)


log_path = output / "app.log"
with log_path.open("w") as log:
    app = subprocess.Popen([sys.argv[1]], cwd=root, env=env, stdout=log,
                           stderr=subprocess.STDOUT, start_new_session=True)
    try:
        deadline = time.monotonic() + 15
        window = ""
        while time.monotonic() < deadline:
            assert app.poll() is None, "app exited during startup"
            found = subprocess.run(
                ["xdotool", "search", "--all", "--onlyvisible", "--pid",
                 str(app.pid), "--name", "Inner Breeze"],
                env=env, capture_output=True, text=True, timeout=2)
            if found.returncode == 0 and found.stdout.strip():
                window = found.stdout.splitlines()[0]
                break
            time.sleep(0.1)
        assert window, "the app did not map its own window"
        command("xdotool", "windowfocus", window)
        assert wait_for_scale(10, 10), f"default scale is {saved_scale()}"
        time.sleep(1.0)
        normal = capture(window, "normal")

        # Ctrl and the wheel rescale the whole window and move the setting.
        wheel(window, +1, 3)
        zoomed_in = capture(window, "zoomed-in")
        assert wait_for_scale(13), f"scale after three notches is {saved_scale()}"
        ratio = content_width(zoomed_in) / content_width(normal)
        assert 1.25 < ratio < 1.35, f"130% drew the content {ratio:.2f} times wider"

        # The wheel without Ctrl keeps its meaning and leaves the scale alone.
        wheel(window, -1, 3, control=False)
        assert saved_scale() == 13, "a plain wheel changed the scale"

        # Zooming back out returns to the layout the app started with.
        wheel(window, -1, 3)
        restored = capture(window, "restored")
        assert wait_for_scale(10), f"scale after zooming back is {saved_scale()}"
        ratio = content_width(restored) / content_width(normal)
        assert 0.98 < ratio < 1.02, f"zooming back left the content {ratio:.2f} times wider"

        # The limits match the Appearance slider: 50% to 250%.
        wheel(window, -1, 20)
        assert wait_for_scale(5), f"the low limit is {saved_scale()}"
        capture(window, "scale-50")
        # Every supported scale must remain usable, including fractional ones.
        for tenths in range(6, 26):
            wheel(window, +1, 1)
            assert wait_for_scale(tenths), f"expected {tenths}, got {saved_scale()}"
            if tenths in (7, 10, 13, 17, 20, 25):
                capture(window, f"scale-{tenths * 10}")
        wheel(window, +1, 3)
        assert wait_for_scale(25), f"the high limit is {saved_scale()}"

        # Ctrl+0 resets to 100%.
        # Hold Ctrl across several frames, as a person does.
        command("xdotool", "keydown", "ctrl")
        time.sleep(0.2)
        command("xdotool", "keydown", "0")
        time.sleep(0.3)
        command("xdotool", "keyup", "0")
        time.sleep(0.3)
        command("xdotool", "keyup", "ctrl")
        assert wait_for_scale(10), f"Ctrl+0 left the scale at {saved_scale()}"
        assert "APP: frame rejected with status" not in log_path.read_text()
    finally:
        if app.poll() is None:
            app.terminate()
            try:
                app.wait(timeout=2)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=2)
        shutil.rmtree(data)

print("Native zoom: every scale from 50% to 250%, Ctrl+wheel persistence, limits and Ctrl+0 passed")
