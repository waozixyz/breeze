#!/usr/bin/env python3
"""Leaderboard opens as its own unpinned app, offers every installed practice
and ranks saved friend results."""
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

from ui_driver import UiDriver

assert int(os.environ.get("DISPLAY", ":0").split(":")[-1].split(".")[0]) >= 300
root = Path(__file__).resolve().parents[1]
binary = Path(sys.argv[1]).resolve()
output = root / "build/leaderboard-ui-test"
output.mkdir(parents=True, exist_ok=True)
WIDTH, HEIGHT = 390, 844
LEADERBOARD_ROUTE = 9
RANKED = re.compile(r"(\d+)\. @(\w+)$")
PRACTICES = {"Wim Hof Breathing", "Meditation", "Sun Salutation", "Breathing Patterns",
             "Tai Chi", "Astral Projection", "7-Minute Workout"}
# A private command folder, so concurrent runs never answer each other.
driver_directory = tempfile.TemporaryDirectory(prefix="inbe-leaderboard-driver-")
driver = UiDriver(driver_directory.name)


def command(*args):
    return subprocess.check_output(args, text=True, timeout=5).strip()


def rows():
    """The board's ranked rows, top first: each friend's name and values."""
    nodes = [node for node in driver.tree() if node["visible"]]
    ranked = []
    for node in nodes:
        match = RANKED.match(node["label"])
        if match:
            values = [cell["label"] for cell in sorted(nodes, key=lambda cell: cell["x"])
                      if cell["parent"] == node["parent"] and cell["y"] == node["y"]
                      and cell["x"] > node["x"] and cell["kind"] == "text"]
            ranked.append((node["y"], int(match.group(1)), match.group(2), values))
    ranked.sort()
    assert [rank for _, rank, _, _ in ranked] == list(range(1, len(ranked) + 1)), \
        f"ranks are out of order: {ranked}"
    return [(name, values) for _, _, name, values in ranked]


def board(expected, timeout=10):
    """The ranked rows once they list the expected names, or as they stand."""
    deadline = time.monotonic() + timeout
    while True:
        shown = rows()
        if [name for name, _ in shown] == expected or time.monotonic() >= deadline:
            return shown
        time.sleep(0.05)


def practice_grid(expected, timeout=10):
    """The practice buttons as rows of labels, top row first, once they show
    the expected practices."""
    deadline = time.monotonic() + timeout
    while True:
        buttons = [node for node in driver.find(role="button", visible=True)
                   if node["label"] in PRACTICES]
        grid = {}
        for node in buttons:
            grid.setdefault(node["y"], []).append(node)
        shown = [[node["label"] for node in sorted(row, key=lambda cell: cell["x"])]
                 for _, row in sorted(grid.items())]
        if shown == expected or time.monotonic() >= deadline:
            return shown
        time.sleep(0.05)


def selected_practice():
    chosen = [node["label"] for node in driver.find(role="button", visible=True)
              if node["label"] in PRACTICES and node["selected"]]
    assert len(chosen) == 1, f"selected practices: {chosen}"
    return chosen[0]


def choose(label):
    """Press a practice or column tab and wait until it shows as selected."""
    driver.press(label=label, role="button")
    deadline = time.monotonic() + 10
    while not any(node["selected"] for node in driver.find(label=label, role="button", visible=True)):
        assert time.monotonic() < deadline, f"{label} did not become selected"
        time.sleep(0.05)
    driver.wait_idle(frames=2, timeout=2)


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def launch(profile, name):
    log_path = output / (name + ".log")
    log = log_path.open("w")
    app = subprocess.Popen([str(binary)], cwd=root,
                           env=os.environ | {"APP_DATA_ROOT": str(profile)} | driver.environment(),
                           stdout=log, stderr=subprocess.STDOUT)
    driver.attach(app, log_path)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        assert app.poll() is None, log_path.read_text()
        found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                               capture_output=True, text=True)
        if found.returncode == 0 and (profile / "inbe.db").exists():
            window = found.stdout.splitlines()[0]
            command("xdotool", "windowsize", window, str(WIDTH), str(HEIGHT))
            command("xdotool", "windowmove", window, "0", "0")
            # Wait until the app lays out the phone-sized window.
            while True:
                screen = next(node for node in driver.tree() if node["kind"] == "screen")
                if (screen["width"], screen["height"]) == (WIDTH, HEIGHT):
                    break
                assert time.monotonic() < deadline, f"the app kept a {screen['width']}x{screen['height']} layout"
                time.sleep(0.05)
            driver.wait_idle(frames=3)
            return app, window
        time.sleep(0.1)
    stop(app)
    raise AssertionError("Inbe did not map its window")


with tempfile.TemporaryDirectory(prefix="inbe-leaderboard-") as directory:
    profile = Path(directory)
    app, _ = launch(profile, "first-start")
    stop(app)
    with sqlite3.connect(profile / "inbe.db") as db:
        user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
        saved = dict(db.execute("SELECT key,value FROM settings WHERE user_id=?", (user,)))
        favorites = [int(saved[f"launcher_favorite_{i}"])
                     for i in range(int(saved.get("launcher_favorite_count", 0)))]
        # A new profile adds Leaderboard from More apps.
        assert not int(saved["enabled_apps"]) & 32, "Leaderboard was installed for a new profile"
        assert LEADERBOARD_ROUTE not in favorites, "Leaderboard was pinned by default"
        settings = {"language": "en", "language_system": 0, "language_setup_done": 1,
                    "apps_setup_done": 1, "app_used_leaderboard": 1, "main_tab": 5, "tutorial_seen": 1,
                    "habits_guide_seen": 1, "lumi_guides_seen": 127, "launcher_guide_seen": 1, "package_updates_allowed": 0,
                    "apps_last_update_check": 1900000000,
                    # Pinned here, so the page has no "back to Apps" bar and
                    # the controls keep fixed positions.
                    "launcher_favorite_count": 4, "launcher_favorite_0": 12,
                    "launcher_favorite_1": 1, "launcher_favorite_2": 2,
                    "launcher_favorite_3": LEADERBOARD_ROUTE,
                    # Astral Projection first in the saved Practice order.
                    "practice_order": 1503124}
        for key, value in settings.items():
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                       "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value",
                       (user, key, str(value)))
        river, maple, cedar = "a" * 64, "b" * 64, "d" * 64
        snapshots = {
            "leaderboard.breathing.whm.streak": {"rows": [
                {"user_id_hash": river, "alias": "river", "value": 12, "label": "12"},
                {"user_id_hash": maple, "alias": "maple", "value": 30, "label": "30"}]},
            "leaderboard.breathing.whm.avg_hold": {"rows": [
                {"user_id_hash": river, "value": 95, "label": "95"},
                {"user_id_hash": maple, "value": 61, "label": "61"}]},
            "leaderboard.breathing.meditation.streak": {"rows": [
                {"user_id_hash": river, "alias": "river", "value": 2, "label": "2"}]},
            "leaderboard.breathing.meditation.avg_time": {"rows": [
                {"user_id_hash": river, "value": 900, "label": "0:15"}]},
            "leaderboard.breathing.astral_projection.streak": {"rows": [
                {"user_id_hash": maple, "alias": "maple", "value": 3, "label": "3"},
                {"user_id_hash": river, "alias": "river", "value": 5, "label": "5"}]},
            # Old achievement boards are never shown: Habits and Lumi rank nothing.
            "leaderboard.apps.habits.achievements": {"rows": [
                {"user_id_hash": river, "alias": "river", "value": 8, "label": "8"}]},
            # A friend without results yet still appears, at zero.
            "friends.list": {"friends": [{"user_id_hash": river, "alias": "river"},
                                         {"user_id_hash": cedar, "alias": "cedar"}]},
        }
        for kind, value in snapshots.items():
            db.execute("INSERT OR REPLACE INTO social_snapshots(user_id,kind,json,updated_at) "
                       "VALUES(?,?,?,1)", (user, kind, json.dumps(value)))
    # Wim Hof, Meditation, Breathing Patterns, Astral Projection and the
    # 7-Minute Workout come with the app. Sun Salutation was never
    # downloaded, and Tai Chi's pack without an account that bought it is not
    # installed.
    packages = profile / "packages"
    packages.mkdir(exist_ok=True)
    shutil.copyfile(root / "build/practice-content/taichi.zib", packages / "practice-taichi.zib")
    app, window = launch(profile, "board")
    try:
        # Installed practices only, in Practice's order, two per row on phones.
        expected = [["Astral Projection", "Wim Hof Breathing"], ["Breathing Patterns", "Meditation"],
                    ["7-Minute Workout"]]
        grid = practice_grid(expected)
        assert grid == expected, f"installed practices: {grid}"
        assert selected_practice() == "Wim Hof Breathing"
        streak = board(["maple", "river", "cedar"])
        assert [name for name, _ in streak] == ["maple", "river", "cedar"], f"streak order: {streak}"
        assert dict(streak)["cedar"][0] == "0", f"a friend without results is not at zero: {streak}"
        choose("Avg hold")
        average = board(["river", "maple", "cedar"])
        assert [name for name, _ in average] == ["river", "maple", "cedar"], f"average hold order: {average}"
        # Meditation is on the second row of the phone grid.
        choose("Meditation")
        meditation = board(["river", "cedar"])
        assert [name for name, _ in meditation] == ["river", "cedar"] and "0:15" in dict(meditation)["river"], \
            f"meditation: {meditation}"
        choose("Breathing Patterns")
        patterns = board(["cedar", "river"])
        assert sorted(name for name, _ in patterns) == ["cedar", "river"], f"breathing patterns: {patterns}"
        # Astral Projection ranks its own board, by streak only.
        choose("Astral Projection")
        astral = board(["river", "maple", "cedar"])
        assert [name for name, _ in astral] == ["river", "maple", "cedar"], f"astral projection: {astral}"
        assert not driver.find(label="Avg hold", role="button", visible=True), "Astral Projection ranks an average"
        # Only apps with a ranking are offered. Without a game that reported
        # a score, that is Practice alone, so there is nothing to choose.
        assert not driver.find(role="combo_box", visible=True), "an app without a ranking was offered"
        for other in ("Habits", "Lumi", "Leaderboard"):
            assert not driver.find(label=other, role="option"), f"{other} has no ranking but was offered"
        log = (output / "board.log").read_text()
        assert "frame rejected" not in log, log
        assert app.poll() is None, log
    finally:
        stop(app)
    # A downloaded Sun Salutation joins the board in Practice's order.
    shutil.copyfile(root / "build/practice-content/sunsalutation.zib", packages / "practice-sunsalutation.zib")
    app, window = launch(profile, "with-sun-salutation")
    try:
        expected = [["Astral Projection", "Wim Hof Breathing"], ["Breathing Patterns", "Meditation"],
                    ["Sun Salutation", "7-Minute Workout"]]
        grid = practice_grid(expected)
        assert grid == expected, f"after download: {grid}"
        log = (output / "with-sun-salutation.log").read_text()
        assert "frame rejected" not in log, log
        assert app.poll() is None, log
    finally:
        stop(app)
# About lists every app's version, so it must cover the seventh one too.
with tempfile.TemporaryDirectory(prefix="inbe-about-") as directory:
    shot = output / "about.png"
    shot.unlink(missing_ok=True)
    about = subprocess.Popen([str(binary), "--screenshot", str(shot), "--screenshot-scene", "settings_about",
                              "--screenshot-width", "900", "--screenshot-height", "720"], cwd=root,
                             env=os.environ | {"APP_DATA_ROOT": directory}, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True)
    try:
        stdout, stderr = about.communicate(timeout=60)
    finally:
        stop(about)
        # Screenshots keep their profile in a per-process folder.
        shutil.rmtree(Path("/tmp") / f"inbe-screenshot-{about.pid}", ignore_errors=True)
    assert about.returncode == 0 and shot.exists(), stdout[-4000:] + stderr[-2000:]
    assert "out of bounds" not in stdout + stderr, stdout[-4000:]
driver_directory.cleanup()
print("Leaderboard: unpinned install, installed practices in order, saved ranks, average hold, "
      "meditation time, patterns, Astral Projection, only ranked apps offered, "
      "a downloaded practice joining and About passed")
