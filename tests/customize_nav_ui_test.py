"""Arrange pinned cards with dragging on a private display.

The app runs with Kryon's test driver: Apps and its cards are found in the
widget tree and dragged with the app's own pointer.
"""

import contextlib
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

from ui_driver import UiDriver

ROOT = Path(__file__).resolve().parents[1]
assert int(os.environ["DISPLAY"].split(":")[-1].split(".")[0]) >= 300
NARROW = os.environ.get("INBE_TEST_NARROW") == "1"
WIDTH, HEIGHT = (390, 844) if NARROW else (900, 720)
OUTPUT = ROOT / "build/customize-nav-test" / f"{WIDTH}x{HEIGHT}"
OUTPUT.mkdir(parents=True, exist_ok=True)
BINARY = Path(sys.argv[1]).resolve()
PRESS_SECONDS = float(os.environ.get("INBE_TEST_PRESS_SECONDS", "0.3"))

with tempfile.TemporaryDirectory(prefix="inbe-settings-entry-") as temporary:
    profile = Path(temporary)
    driver = UiDriver(OUTPUT / "driver")
    env = os.environ.copy()
    env.update(APP_DATA_ROOT=str(profile), APP_NO_TRAY="1",
               SDL_AUDIODRIVER="dummy", INBE_DEBUG_ROUTE="1", YUE_DESKTOP_RECOVERY="0")
    env.update(driver.environment())

    def command(*args):
        return subprocess.run(args, env=env, check=True, capture_output=True,
                              text=True, timeout=5).stdout.strip()

    @contextlib.contextmanager
    def application(name):
        log_path = OUTPUT / (name + ".log")
        with log_path.open("w") as log:
            app = subprocess.Popen([str(BINARY)], cwd=ROOT, env=env,
                                   stdout=log, stderr=subprocess.STDOUT)
            driver.attach(app, log_path)
            try:
                deadline = time.monotonic() + 15
                window = ""
                while time.monotonic() < deadline:
                    assert app.poll() is None, log_path.read_text()
                    found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                                           env=env, capture_output=True, text=True, timeout=2)
                    if found.returncode == 0 and (profile / "inbe.db").exists():
                        window = found.stdout.splitlines()[0]
                        break
                    time.sleep(.05)
                assert window, log_path.read_text()
                command("xdotool", "windowsize", window, str(WIDTH), str(HEIGHT))
                command("xdotool", "windowmove", window, "0", "0")
                deadline = time.monotonic() + 10
                while driver.tree()[0]["width"] != WIDTH:
                    assert time.monotonic() < deadline, "The app did not take its window size"
                    time.sleep(.05)
                driver.wait_idle(frames=3)
                yield window, log_path
                assert app.poll() is None, log_path.read_text()
                assert "frame rejected" not in log_path.read_text(), log_path.read_text()
            finally:
                if app.poll() is None:
                    app.terminate()
                app.wait(timeout=5)

    def settings():
        # Read-only, so closing it never checkpoints the running app's WAL.
        uri = (profile / "inbe.db").as_uri() + "?mode=ro"
        with contextlib.closing(sqlite3.connect(uri, uri=True, timeout=3)) as db:
            return dict(db.execute("SELECT key,value FROM settings"))

    def cards():
        """Apps' cards in Pinned and in More apps, in order."""
        tree = driver.tree()
        parents = {node["index"]: node for node in tree}
        more_top = [node for node in tree if node["kind"] == "separator"][0]["y"]
        def in_scroll(node):
            # Each section's shared Apps group sits inside the page's scroll.
            parent = parents.get(node["parent"])
            while parent is not None and parent["kind"] != "navigation_bar":
                if parent["kind"] == "scroll":
                    return True
                parent = parents.get(parent["parent"])
            return False
        grid = [node for node in tree if node["kind"] == "button" and node["visible"]
                and in_scroll(node) and node["label"] not in ("Install", "Uninstall", "Download", "App options", "Move app")]
        return ([node for node in grid if node["y"] < more_top],
                [node for node in grid if node["y"] >= more_top])

    with application("prepare"):
        pass
    with sqlite3.connect(profile / "inbe.db") as db:
        user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
        values = {"language": "en", "language_system": 0, "language_setup_done": 1,
                  "apps_setup_done": 1, "enabled_apps": 22, "lumi_introduced": 1,
                  "main_tab": 1, "tutorial_seen": 1, "habits_guide_seen": 1, "lumi_guides_seen": 127,
                  "launcher_guide_seen": 1, "ui_scale": 10,
                  "navigation_placement": 0 if NARROW else 1, "navigation_collapsed": 0,
                  "package_updates_allowed": 0, "apps_last_update_check": 1900000000,
                  "launcher_favorite_count": 2, "launcher_favorite_0": 12, "launcher_favorite_1": 1,
                  "bottom_nav_route_count": 4, "bottom_nav_route_0": 12,
                  "bottom_nav_route_1": 1, "bottom_nav_route_2": 2, "bottom_nav_route_3": 4}
        for bit, name in enumerate(("lists", "habits", "practices", "diary", "lumi", "leaderboard")):
            values["app_used_" + name] = int(bool(int(values["enabled_apps"]) & (1 << bit)))
        for key, value in values.items():
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,2) "
                       "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at", (user, key, str(value)))

    with application("app") as (window, log):
        # Apps, at the end of the navigation, opens with a held press.
        apps = driver.wait(label="Apps", role="button")
        x, y = UiDriver.center(apps)
        driver.pointer(x, y)
        driver.pointer(x, y, down=True)
        time.sleep(PRESS_SECONDS)
        driver.pointer(x, y, down=False)
        driver.release_pointer()
        driver.wait(label="Pinned")
        saved = settings()
        assert saved["launcher_favorite_count"] == "2", "Opening Apps changed pins"
        assert saved["enabled_apps"] == "22", "Opening Apps changed app choices"
        # A card moves from Pinned to More; no separate editing or pin control.
        pinned, more = cards()
        assert [card["label"] for card in pinned] == ["Lumi", "Habits"], pinned
        handle = next(node for node in driver.find(label="Move app", role="button", visible=True)
                      if abs(node["y"] + node["height"] / 2 - pinned[0]["y"] - pinned[0]["height"] / 2) < 2)
        driver.drag(UiDriver.center(handle), UiDriver.center(more[0]), steps=12)
        deadline = time.monotonic() + 5
        while settings()["launcher_favorite_count"] != "1":
            assert time.monotonic() < deadline, "Dragging to More did not remove the pin"
            time.sleep(.05)
        saved = settings()
        assert saved["launcher_favorite_0"] == "1", saved
        assert saved["enabled_apps"] == "22", "Dragging changed app choices"
        pinned, more = cards()
        assert [card["label"] for card in pinned] == ["Habits"], pinned
print("Apps: dragging arranges pins and preserves app choices")
