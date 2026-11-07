"""The real shop shows complete purchase totals and scrolls at phone/desktop sizes."""
import os
import hashlib
import json
import re
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
BUNDLE = ROOT / "build/inbe-full.zx"


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


candidate = {"binary": str(BINARY), "binary_sha256": digest(BINARY),
             "bundle": str(BUNDLE), "bundle_sha256": digest(BUNDLE)}


def capture(process, destination):
    window = subprocess.check_output(
        ["xdotool", "search", "--onlyvisible", "--pid", str(process.pid)], text=True).splitlines()[0]
    subprocess.run(["import", "-window", window, str(destination)], check=True)


for width, height, scale in [(390, 844, 10), (900, 720, 10), (390, 844, 20)]:
    name = f"{width}-{height}-{scale}"
    driver = UiDriver(OUTPUT / name)
    with tempfile.TemporaryDirectory(prefix="inbe-shop-test-", dir=OUTPUT) as directory, \
            (OUTPUT / f"{name}.log").open("w") as log:
        process = subprocess.Popen([
            str(BINARY), "--screenshot", str(Path(directory) / "start.png"),
            "--bundle", str(BUNDLE), "--feature", "habits",
            "--screenshot-scene", "habits_shop", "--screenshot-width", str(width),
            "--screenshot-height", str(height), "--screenshot-ui-scale", str(scale),
            "--screenshot-theme", "0", "--screenshot-dark", "0"], cwd=ROOT,
            env=os.environ | {"APP_SHOT_WINDOW": "1", "APP_NO_TRAY": "1",
                              "INBE_SCREENSHOT_DATA_ROOT": str(Path(directory) / "data")} | driver.environment(),
            stdout=log, stderr=subprocess.STDOUT)
        driver.attach(process, OUTPUT / f"{name}.log")
        try:
            driver.wait(label="Soda", visible=False, timeout=60)
            driver.wait(label="Activity", visible=False)
            driver.wait(label="Purchase statistics", visible=False)
            nodes = driver.tree()
            statistics = next(node for node in nodes if node["label"] == "Purchase statistics")
            rewards = next(node for node in nodes if node["label"] == "Your rewards")
            metrics = [node for node in nodes if node["kind"] == "text" and
                       statistics["y"] < node["y"] < rewards["y"]]
            # Twelve persisted purchases exceed the ten-entry Activity limit.
            # Original prices are 5,8,11,14,17,20, each bought twice: 150 coins.
            assert sum(node["label"] == "12" for node in metrics) == 3, (name, metrics)
            assert any(node["label"] == "150" for node in metrics), (name, metrics)
            for label in ("Purchases", "Coins spent", "Last 7 days", "Last 30 days"):
                metric = next(node for node in metrics if node["label"] == label)
                assert metric["x"] >= 0 and metric["x"] + metric["width"] <= width, (name, metric)
            per_reward = [node for node in nodes if node["kind"] == "text" and
                          node["label"] == "Purchases: 2 · Last 30 days: 2"]
            assert len(per_reward) == 6, (name, "each reward retains both purchases", per_reward)
            capture(process, OUTPUT / f"{name}-statistics.png")
            viewport = next(node for node in driver.tree() if node["kind"] == "scroll" and node["visible"])
            driver.pointer(viewport["visible_x"] + viewport["visible_width"] / 2,
                           viewport["visible_y"] + viewport["visible_height"] / 2, wheel=-100)
            driver.release_pointer()
            driver.wait_idle(frames=30)
            nodes = driver.tree()
            activity = next(node for node in nodes if node["label"] == "Activity")
            # Activity mixes earnings and purchases in timestamp order.
            # Both signed whole coins and half coins must remain reachable.
            movements = [node for node in nodes if node["kind"] == "text" and
                         re.fullmatch(r"[+-](?:[0-9]+½?|½)", node["label"]) and
                         node["y"] > activity["y"]]
            assert len(movements) == 10, (name, "fixture must have ten coin movements", movements)
            last = max(movements, key=lambda node: node["y"])
            assert last["visible"] and last["visible_height"] >= last["height"] - 1, \
                (name, "last activity is clipped at the scroll limit", last)
            days = [node for node in nodes if node["label"] == "Today" and node["y"] > activity["y"]]
            last_day = max(days, key=lambda node: node["y"])
            assert last_day["visible"] and last_day["visible_height"] >= last_day["height"] - 1,                 (name, "last activity date is clipped", last_day)
            for node in movements:
                if node["visible"]:
                    assert node["visible_x"] >= 0 and node["visible_x"] + node["visible_width"] <= width, \
                        (name, "amount overlaps the right edge", node)
            names = {"Soda", "Movie night", "Pizza", "Ice cream", "Sleep in", "New book"}
            for node in nodes:
                if node["kind"] == "text" and node["label"] in names:
                    assert node["width"] > 20, (name, "reward name has no readable column", node)
            time.sleep(4.2)
            capture(process, OUTPUT / f"{name}.png")
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
assert digest(BINARY) == candidate["binary_sha256"], "candidate binary changed during UI test"
assert digest(BUNDLE) == candidate["bundle_sha256"], "candidate package changed during UI test"
(OUTPUT / "candidate.json").write_text(json.dumps(candidate, indent=2) + "\n")
print("Shop: full purchase totals, per-reward frequency and complete activity at phone, desktop and 200% zoom")
