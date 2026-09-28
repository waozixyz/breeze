"""Follow the normal app's Settings > Appearance > Customize route."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


root = Path(__file__).resolve().parent.parent
assert int(os.environ["DISPLAY"].split(":")[-1].split(".")[0]) >= 300


def command(env, *args):
    return subprocess.run(args, env=env, check=True, text=True,
                          capture_output=True, timeout=5).stdout.strip()


def click(env, window, x, y, duration=0.08):
    command(env, "xdotool", "mousemove", "--window", window, str(x), str(y))
    time.sleep(0.1)
    command(env, "xdotool", "mousedown", "1")
    time.sleep(duration)
    command(env, "xdotool", "mouseup", "1")
    time.sleep(0.35)


with tempfile.TemporaryDirectory(prefix="inbe-customize-") as data_root:
    env = os.environ.copy()
    for name in ("WAYLAND_DISPLAY", "GDK_DISPLAY", "APP_SHOT_WINDOW"):
        env.pop(name, None)
    env.update(APP_NO_TRAY="1", SDL_AUDIODRIVER="dummy",
               INBE_DEBUG_ROUTE="1", APP_DATA_ROOT=data_root)
    log_path = Path(data_root) / "app.log"
    with log_path.open("w") as log:
        app = subprocess.Popen([sys.argv[1]], cwd=root, env=env,
                               stdout=log, stderr=subprocess.STDOUT)
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
            assert window, "normal app window did not appear"
            command(env, "xdotool", "windowsize", window, "900", "720")
            command(env, "xdotool", "windowfocus", window)
            time.sleep(0.5)

            # A fresh data root opens language selection first.
            click(env, window, 450, 423)
            assert "screen=8->0" in log_path.read_text(), "language step did not finish"
            click(env, window, 110, 670)
            assert "screen=0->6" in log_path.read_text(), "Settings did not open"
            click(env, window, 320, 325)
            click(env, window, 650, 576, duration=0.02)
            routes = log_path.read_text()
            assert "screen=6->12" in routes, "Customize did not open"
            assert "screen=12->" not in routes, "Customize closed on its opening click"

            click(env, window, 32, 24, duration=0.2)
            assert "screen=12->6" in log_path.read_text(), \
                "Back did not return to Appearance"
        finally:
            if app.poll() is None:
                app.terminate()
                try:
                    app.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    app.kill()
                    app.wait(timeout=2)

print("Normal app: quick Customize click stays; Back returns to Appearance")
