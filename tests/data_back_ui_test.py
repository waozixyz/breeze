#!/usr/bin/env python3
"""Back from navigation Data exits once; Profile Data returns to its hub."""
import os
from pathlib import Path
import re
import subprocess
import sys
import time

assert int(os.environ.get("DISPLAY", ":0").split(":")[-1].split(".")[0]) >= 300
root = Path(__file__).resolve().parents[1]
binary = Path(sys.argv[1]).resolve()
output = root / "build/data-back-ui-test"
output.mkdir(parents=True, exist_ok=True)


def command(*args):
    return subprocess.check_output(args, text=True, timeout=5).strip()


def click(window, x, y):
    command("xdotool", "mousemove", "--window", window, str(x), str(y),
            "mousedown", "1", "sleep", "0.12", "mouseup", "1")
    time.sleep(0.5)


for scene in ("data_from_navigation", "profile_data", "settings_overview"):
    sizes = ((360, 740),) if scene == "settings_overview" else ((900, 720), (360, 740))
    for width, height in sizes:
        name = f"{scene}-{width}"
        logfile = output / f"{name}.log"
        initial = output / f"{name}.png"
        env = os.environ.copy()
        env.update(APP_SHOT_WINDOW="1", APP_NO_TRAY="1", INBE_DEBUG_ROUTE="1",
                   SDL_VIDEODRIVER="x11", YUE_DESKTOP_RECOVERY="0")
        with logfile.open("w") as log:
            app = subprocess.Popen([str(binary), "--screenshot", str(initial),
                "--screenshot-scene", scene, "--screenshot-width", str(width),
                "--screenshot-height", str(height), "--screenshot-ui-scale", "10"],
                cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 15
                window = ""
                while time.monotonic() < deadline:
                    assert app.poll() is None, logfile.read_text()[-2000:]
                    found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                        capture_output=True, text=True)
                    database = Path('/tmp') / f'inbe-screenshot-{app.pid}' / 'inbe.db'
                    if found.returncode == 0 and found.stdout.strip() and database.is_file():
                        window = found.stdout.splitlines()[0]
                        break
                    time.sleep(0.1)
                assert window, "private child did not become ready"
                command("xdotool", "windowfocus", "--sync", window)
                time.sleep(0.5)
                if scene == "settings_overview":
                    click(window, width // 2, 156)
                    assert "screen=6->10" in logfile.read_text(), "Settings Data did not open"
                baseline = len(logfile.read_text())
                back_x = 224 + 26 if width >= 640 else 26
                click(window, back_x, 24)
                after = logfile.read_text()[baseline:]
                switches = re.findall(r"ROUTE switch frame=\d+ screen=(\d+)->(\d+)", after)
                if scene == "data_from_navigation":
                    assert switches == [("10", "16")], (name, switches, after[-1200:])
                elif scene == "settings_overview":
                    assert switches == [("10", "6")], (name, switches, after[-1200:])
                else:
                    assert switches == [], (name, "Profile Data skipped its parent", switches)
                    command("import", "-window", window, str(output / f"{name}-hub.png"))
                    click(window, back_x, 24)
                    after = logfile.read_text()[baseline:]
                    switches = re.findall(r"ROUTE switch frame=\d+ screen=(\d+)->(\d+)", after)
                    assert switches == [("10", "0")], (name, switches, after[-1200:])
                time.sleep(0.5)
                command("import", "-window", window, str(output / f"{name}-after.png"))
                assert "APP: frame rejected with status" not in logfile.read_text()
            finally:
                app.terminate()
                try:
                    app.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    app.kill()
                    app.wait(timeout=5)
print("Data Back: navigation exits once; Profile Data returns to its hub; Settings Data returns to Settings")
