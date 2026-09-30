"""Click the real navigation rail on the display owned by the shell harness."""

import os
from pathlib import Path
import subprocess
import sys
import time

from PIL import Image


root = Path(__file__).resolve().parent.parent
output = root / "build/native-navigation-test"
output.mkdir(parents=True, exist_ok=True)
assert int(os.environ["DISPLAY"].split(":")[-1].split(".")[0]) >= 300
env = os.environ.copy()
for name in ("WAYLAND_DISPLAY", "GDK_DISPLAY"):
    env.pop(name, None)
env["APP_NO_TRAY"] = "1"
env["APP_SHOT_WINDOW"] = "1"


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


log_path = output / "app.log"
with log_path.open("w") as log:
    app = subprocess.Popen(
        [sys.argv[1], "--screenshot", str(output / "home.png"),
         "--screenshot-scene", "home", "--screenshot-width", "900",
         "--screenshot-height", "720"],
        cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        deadline = time.monotonic() + 10
        window = ""
        while time.monotonic() < deadline:
            assert app.poll() is None, "app exited during startup"
            found = subprocess.run(
                ["xdotool", "search", "--all", "--onlyvisible", "--pid",
                 str(app.pid), "--name", "Inner Breeze"],
                env=env, capture_output=True, text=True, timeout=2,
            )
            if found.returncode == 0 and found.stdout.strip():
                window = found.stdout.splitlines()[0]
                break
            time.sleep(0.1)
        assert window, "the app did not map its own window"
        command("xdotool", "windowfocus", window)
        time.sleep(0.5)
        before = capture(window, "home")
        assert before.size == (900, 720), before.size
        for name, y in (("lists", 145), ("habits", 210),
                        ("practice", 275), ("settings", 670)):
            prior = before.getpixel((20, y))
            command("xdotool", "mousemove", "--window", window, "110", str(y))
            command("xdotool", "mousedown", "1")
            time.sleep(0.1)
            command("xdotool", "mouseup", "1")
            # Let the page transition finish before clicking the next route.
            # Its first changed pixel can appear while input is still blocked.
            time.sleep(0.4)
            deadline = time.monotonic() + 3
            changed = False
            while time.monotonic() < deadline:
                time.sleep(0.1)
                after = capture(window, name)
                color = after.getpixel((20, y))
                if sum(abs(a - b) for a, b in zip(prior, color)) > 30:
                    changed = True
                    break
            assert changed, f"navigation did not activate {name}"
            assert "APP: frame rejected with status" not in log_path.read_text()
            before = after
    finally:
        if app.poll() is None:
            app.terminate()
            try:
                app.wait(timeout=1)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=2)

print("Native navigation: lists, habits, practice and settings clicks passed")
