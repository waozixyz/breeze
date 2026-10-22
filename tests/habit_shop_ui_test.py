"""The real shop can scroll through its full activity at phone and desktop sizes."""
import os
import shutil
from pathlib import Path
import subprocess
import sys
import time
import tempfile

from ui_driver import UiDriver

assert os.environ.get("INBE_UI_TEST_XVFB") == "1"
assert not os.environ.get("WAYLAND_DISPLAY") and not os.environ.get("DBUS_SESSION_BUS_ADDRESS")
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/habit-shop-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
BINARY = Path(sys.argv[1]).resolve()
for width, height, scale in [(390, 844, 10), (900, 720, 10), (390, 844, 20)]:
    name = f"{width}-{height}-{scale}"
    driver = UiDriver(OUTPUT / name)
    with tempfile.TemporaryDirectory(prefix="inbe-shop-test-") as directory, \
            (OUTPUT / f"{name}.log").open("w") as log:
        process = subprocess.Popen([
            str(BINARY), "--screenshot", str(Path(directory) / "start.png"),
            "--bundle", str(ROOT / "build/inbe-full.zib"), "--feature", "habits",
            "--screenshot-scene", "habits_shop", "--screenshot-width", str(width),
            "--screenshot-height", str(height), "--screenshot-ui-scale", str(scale),
            "--screenshot-theme", "0", "--screenshot-dark", "0"], cwd=ROOT,
            env=os.environ | {"APP_SHOT_WINDOW": "1", "APP_NO_TRAY": "1"} | driver.environment(),
            stdout=log, stderr=subprocess.STDOUT)
        driver.attach(process, OUTPUT / f"{name}.log")
        try:
            driver.wait(label="Soda", visible=False, timeout=60)
            driver.wait(label="Activity", visible=False)
            viewport = next(node for node in driver.tree() if node["kind"] == "scroll" and node["visible"])
            driver.pointer(viewport["visible_x"] + viewport["visible_width"] / 2,
                           viewport["visible_y"] + viewport["visible_height"] / 2, wheel=-100)
            driver.release_pointer()
            driver.wait_idle(frames=30)
            nodes = driver.tree()
            activity = next(node for node in nodes if node["label"] == "Activity")
            spending = [node for node in nodes if node["label"].startswith("-") and
                        any(char.isdigit() for char in node["label"]) and node["y"] > activity["y"]]
            assert len(spending) == 10, (name, "fixture must have ten purchases", spending)
            last = max(spending, key=lambda node: node["y"])
            assert last["visible"] and last["visible_height"] >= last["height"] - 1, \
                (name, "last activity is clipped at the scroll limit", last)
            days = [node for node in nodes if node["label"] == "Today" and node["y"] > activity["y"]]
            last_day = max(days, key=lambda node: node["y"])
            assert last_day["visible"] and last_day["visible_height"] >= last_day["height"] - 1,                 (name, "last activity date is clipped", last_day)
            for node in spending:
                if node["visible"]:
                    assert node["visible_x"] >= 0 and node["visible_x"] + node["visible_width"] <= width, \
                        (name, "amount overlaps the right edge", node)
            names = {"Soda", "Movie night", "Pizza", "Ice cream", "Sleep in", "New book"}
            for node in nodes:
                if node["kind"] == "text" and node["label"] in names:
                    assert node["width"] > 20, (name, "reward name has no readable column", node)
            time.sleep(4.2)
            window = subprocess.check_output(
                ["xdotool", "search", "--onlyvisible", "--pid", str(process.pid)], text=True).splitlines()[0]
            subprocess.run(["import", "-window", window, str(OUTPUT / f"{name}.png")], check=True)
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            shutil.rmtree(Path(f"/tmp/inbe-screenshot-{process.pid}"), ignore_errors=True)
print("Shop: complete activity is reachable at phone, desktop and 200% zoom")
