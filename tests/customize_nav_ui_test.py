"""Open Customize Nav with a held pointer and verify the new page stays visible."""

import os
from pathlib import Path
import subprocess
import sys
import time

from PIL import Image, ImageChops

root = Path(__file__).resolve().parent.parent
output = root / "build/customize-nav-test"
output.mkdir(parents=True, exist_ok=True)
assert int(os.environ["DISPLAY"].split(":")[-1].split(".")[0]) >= 300
env = os.environ.copy()
for name in ("WAYLAND_DISPLAY", "GDK_DISPLAY"):
    env.pop(name, None)
env.update(APP_NO_TRAY="1", APP_SHOT_WINDOW="1", SDL_AUDIODRIVER="dummy",
           INBE_DEBUG_ROUTE="1")


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


expected_env = env.copy()
expected_env.pop("APP_SHOT_WINDOW", None)
expected_result = subprocess.run([
    sys.argv[1], "--screenshot", str(output / "expected.png"),
    "--screenshot-scene", "customize_nav", "--screenshot-width", "900",
    "--screenshot-height", "720"], cwd=root, env=expected_env,
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
assert expected_result.returncode in (0, 1), expected_result.returncode
assert (output / "expected.png").is_file(), "expected screenshot was not written"

log_path = output / "app.log"
with log_path.open("w") as log:
    app = subprocess.Popen([
        sys.argv[1], "--screenshot", str(output / "theme.png"),
        "--screenshot-scene", "theme_selection", "--screenshot-width", "900",
        "--screenshot-height", "720"], cwd=root, env=env, stdout=log,
        stderr=subprocess.STDOUT, start_new_session=True)
    try:
        deadline = time.monotonic() + 10
        window = ""
        while time.monotonic() < deadline:
            assert app.poll() is None, "app exited during startup"
            found = subprocess.run(
                ["xdotool", "search", "--onlyvisible", "--pid",
                 str(app.pid)], env=env, capture_output=True, text=True,
                timeout=2)
            if found.returncode == 0 and found.stdout.strip():
                window = found.stdout.splitlines()[0]
                break
            time.sleep(0.1)
        assert window, "the app did not map its own window"
        command("xdotool", "windowfocus", window)
        time.sleep(0.5)

        # Keep the pointer down across route-change frames. A leaked press must
        # not activate the back action or any control on Customize Nav.
        command("xdotool", "mousemove", "--window", window, "560", "620")
        command("xdotool", "mousedown", "1")
        time.sleep(0.3)
        command("xdotool", "mouseup", "1")
        time.sleep(0.5)
        actual = capture(window, "after-click")

        with Image.open(output / "expected.png") as expected_image:
            expected = expected_image.convert("RGB")
        difference = ImageChops.difference(actual, expected)
        histogram = difference.histogram()
        changed = sum(sum(histogram[channel * 256 + 1:(channel + 1) * 256]) for channel in range(3))
        changed_ratio = changed / (expected.width * expected.height * 3)
        assert changed_ratio < 0.002, f"Customize Nav changed after opening: {changed_ratio:.4%}"

        log_text = log_path.read_text()
        assert "ROUTE request frame=" in log_text, "Customize Nav button did not route"
        assert "12->" not in log_text, f"Customize Nav closed after opening: {log_text}"
    finally:
        if app.poll() is None:
            app.terminate()
            try:
                app.wait(timeout=1)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=2)

print("Customize Nav: held opening click stays on the Customize Nav page")
