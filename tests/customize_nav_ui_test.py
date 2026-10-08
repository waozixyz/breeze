"""Open cell settings with a held click using an isolated profile on Xvfb."""

import contextlib
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

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
    env = os.environ.copy()
    env.update(APP_DATA_ROOT=str(profile), APP_NO_TRAY="1",
               SDL_AUDIODRIVER="dummy", INBE_DEBUG_ROUTE="1", YUE_DESKTOP_RECOVERY="0")

    def command(*args):
        return subprocess.run(args, env=env, check=True, capture_output=True,
                              text=True, timeout=5).stdout.strip()

    @contextlib.contextmanager
    def application(name):
        log_path = OUTPUT / (name + ".log")
        with log_path.open("w") as log:
            app = subprocess.Popen([str(BINARY)], cwd=ROOT, env=env,
                                   stdout=log, stderr=subprocess.STDOUT)
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
                command("xdotool", "windowfocus", window)
                time.sleep(.6)
                yield window, log_path
                assert app.poll() is None, log_path.read_text()
                assert "frame rejected" not in log_path.read_text(), log_path.read_text()
            finally:
                if app.poll() is None:
                    app.terminate()
                app.wait(timeout=5)

    def settings():
        with sqlite3.connect(profile / "inbe.db", timeout=3) as db:
            return dict(db.execute("SELECT key,value FROM settings"))

    def click(window, x, y, hold=.12):
        command("xdotool", "mousemove", "--window", window, str(x), str(y))
        time.sleep(.15)
        command("xdotool", "mousedown", "1")
        time.sleep(hold)
        command("xdotool", "mouseup", "1")
        time.sleep(.5)

    with application("prepare"):
        pass
    with sqlite3.connect(profile / "inbe.db") as db:
        user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
        values = {"language": "en", "language_system": 0, "language_setup_done": 1,
                  "apps_setup_done": 1, "enabled_apps": 22, "lumi_introduced": 1,
                  "main_tab": 1, "tutorial_seen": 1, "habits_guide_seen": 1, "ui_scale": 10,
                  "navigation_placement": 0 if NARROW else 1, "navigation_collapsed": 0,
                  "cells_auto_update": 0, "apps_last_update_check": 1900000000,
                  "launcher_favorite_count": 2, "launcher_favorite_0": 12, "launcher_favorite_1": 1,
                  "bottom_nav_route_count": 4, "bottom_nav_route_0": 12,
                  "bottom_nav_route_1": 1, "bottom_nav_route_2": 2, "bottom_nav_route_3": 4}
        for key, value in values.items():
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                       "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user, key, str(value)))

    with application("app") as (window, log):
        click(window, *( (325, 802) if NARROW else (44, 316) ))
        click(window, *( (282, 724) if NARROW else (220, 684) ))
        click(window, *( (195, 489) if NARROW else (200, 381) ), hold=PRESS_SECONDS)
        command("import", "-window", window, str(OUTPUT / "after-click.png"))
        saved = settings()
        assert saved["launcher_favorite_count"] == "2", "Opening press changed favorites"
        assert saved["enabled_apps"] == "22", "Opening press changed cell choices"
        # Unpinning proves that the direct entry opened favorites settings.
        click(window, *( (336, 130) if NARROW else (826, 148) ))
        saved = settings()
        assert saved["launcher_favorite_count"] == "1", "Unpin control did not open"
        assert saved["launcher_favorite_0"] == "1", saved
        assert saved["enabled_apps"] == "22", "Unpinning changed app choices"
        assert "screen=6->12" not in log.read_text(), log.read_text()

print("Apps and favorites: a held Settings entry keeps favorites; unpin preserves app choices")
