"""Exercise the app launcher with disposable data on a private Xvfb display."""

import contextlib
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import time

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/launcher-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
BINARY = Path(sys.argv[1]).resolve()
DESKTOP_ENV = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS")
assert all(not os.environ.get(key) for key in DESKTOP_ENV), "Inherited desktop environment"


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


with contextlib.ExitStack() as stack:
    env = {key: value for key, value in os.environ.items() if key not in DESKTOP_ENV}
    env.update(YUE_DESKTOP_RECOVERY="0", APP_NO_TRAY="1", SDL_AUDIODRIVER="dummy",
               INBE_DEBUG_ROUTE="1")
    display_log = stack.enter_context((OUTPUT / "display.log").open("w"))
    display = subprocess.Popen(["Xvfb", "-displayfd", "1", "-screen", "0", "1280x1000x24",
                                "-nolisten", "tcp"], env=env, stdout=subprocess.PIPE, stderr=display_log)
    stack.callback(stop, display)
    number = display.stdout.readline().decode().strip()
    display.stdout.close()
    assert number.isdecimal(), "Private display did not start"
    env["DISPLAY"] = ":" + number

    def command(*args):
        return subprocess.run(args, env=env, check=True, capture_output=True,
                              text=True, timeout=5).stdout.strip()

    def capture(window, name):
        path = OUTPUT / (name + ".png")
        command("import", "-window", window, str(path))
        with Image.open(path) as image:
            return image.convert("RGB").copy()

    def click(window, x, y, hold=.12):
        command("xdotool", "mousemove", "--window", window, str(x), str(y))
        time.sleep(.12)
        command("xdotool", "mousedown", "1")
        time.sleep(hold)
        command("xdotool", "mouseup", "1")
        time.sleep(.4)

    def key(window, name):
        command("xdotool", "windowfocus", window)
        command("xdotool", "keydown", "--clearmodifiers", name)
        time.sleep(.12)
        command("xdotool", "keyup", name)
        time.sleep(.4)

    def settings(profile):
        with sqlite3.connect(profile / "inbe.db", timeout=3) as db:
            return dict(db.execute("SELECT key,value FROM settings WHERE user_id=?", (user,)))

    def favorites(profile):
        saved = settings(profile)
        return [int(saved[f"launcher_favorite_{i}"])
                for i in range(int(saved["launcher_favorite_count"]))]

    def seed(profile, values):
        with sqlite3.connect(profile / "inbe.db", timeout=3) as db:
            for name, value in values.items():
                db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                           "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value",
                           (user, name, str(value)))

    @contextlib.contextmanager
    def application(profile, name, width=900, height=720):
        app_env = env | {"APP_DATA_ROOT": str(profile)}
        log_path = OUTPUT / (name + ".log")
        with log_path.open("w") as log:
            app = subprocess.Popen([str(BINARY)], cwd=ROOT, env=app_env,
                                   stdout=log, stderr=subprocess.STDOUT)
            window = ""
            try:
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    assert app.poll() is None, log_path.read_text()
                    found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                                           env=env, capture_output=True, text=True, timeout=2)
                    if found.returncode == 0 and (profile / "inbe.db").exists():
                        window = found.stdout.splitlines()[0]
                        break
                    time.sleep(.1)
                assert window, "App did not map its own window"
                command("xdotool", "windowsize", window, str(width), str(height))
                command("xdotool", "windowmove", window, "0", "0")
                command("xdotool", "windowfocus", window)
                time.sleep(.8)
                yield window, log_path
                assert app.poll() is None, log_path.read_text()
                assert "frame rejected" not in log_path.read_text(), log_path.read_text()
            except BaseException:
                if window and app.poll() is None:
                    capture(window, name + "-failure")
                raise
            finally:
                stop(app)

    for width, height in ((900, 720), (390, 844)):
        mobile = width < 500
        name = "mobile" if mobile else "desktop"
        with tempfile.TemporaryDirectory(prefix="inbe-launcher-") as temporary:
            profile = Path(temporary)
            with application(profile, name + "-prepare", width, height):
                pass
            with sqlite3.connect(profile / "inbe.db") as db:
                user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
                db.execute("INSERT INTO elist_lists(id,user_id,title,sort_order,deleted_at,updated_at) "
                           "VALUES('launcher-preserved-list',?,'Keep this list',0,0,1)", (user,))
                db.execute("INSERT INTO habits(id,user_id,name,color_r,color_g,color_b,sync_mode,"
                           "sync_activity,sort_order,updated_at) "
                           "VALUES('launcher-preserved-habit',?,'Keep this habit',1,2,3,0,0,0,1)", (user,))
            seed(profile, {"language": "en", "language_system": 0, "language_setup_done": 1,
                           "apps_setup_done": 1, "enabled_apps": 22, "lumi_introduced": 1,
                           "main_tab": 1, "tutorial_seen": 1, "habits_guide_seen": 1,
                           "ui_scale": 10, "navigation_placement": 0, "theme": 10,
                           "theme_source": 0, "theme_mode": 2, "cells_auto_update": 0,
                           "apps_last_update_check": 1900000000,
                           "bottom_nav_route_count": 4, "bottom_nav_route_0": 12,
                           "bottom_nav_route_1": 1, "bottom_nav_route_2": 2, "bottom_nav_route_3": 4,
                           "launcher_favorite_count": 2, "launcher_favorite_0": 1, "launcher_favorite_1": 2})
            apps_point = (325, height - 42) if mobile else (44, 316)
            search_point = (100, 136) if mobile else (180, 104)
            tile_point = (100, 268) if mobile else (220, 220)

            with application(profile, name, width, height) as (window, log):
                click(window, *apps_point, hold=.35)
                capture(window, name + "-launcher")
                assert favorites(profile) == [1, 2], "Opening changed favorites"
                assert settings(profile)["enabled_apps"] == "22", "Opening changed available apps"
                click(window, *search_point)
                command("xdotool", "type", "--clearmodifiers", "--delay", "70", "DIaRy")
                time.sleep(.4)
                capture(window, name + "-search")
                click(window, *tile_point)
                assert settings(profile)["main_tab"] == "3", "Search result did not open Diary"
                assert int(settings(profile)["enabled_apps"]) & 8, "Opening hidden Diary did not enable it"
                assert "->22" in log.read_text(), "Diary route did not activate"
                click(window, *apps_point)
                key(window, "Escape")
                # Escape closes the drawer without quitting or changing the selected app.
                assert settings(profile)["main_tab"] == "3"
                click(window, *apps_point)
                # Holding a search result pins without activating or enabling it.
                def search_app(label):
                    click(window, *((348, 138) if mobile else (382, 106)))
                    click(window, *search_point)
                    command("xdotool", "type", "--clearmodifiers", "--delay", "50", label)
                    time.sleep(.3)

                search_app("Diary")
                click(window, *tile_point, hold=1.8)
                assert favorites(profile) == [1, 2, 11], "Hold did not append a third favorite exactly once"
                assert settings(profile)["main_tab"] == "3", "Hold activated an app"
                capture(window, name + "-held-pin")
                for label, expected in (("Lists", [1, 2, 11, 3]), ("Lumi", [1, 2, 11, 3, 12])):
                    search_app(label)
                    click(window, *tile_point, hold=.85)
                    assert favorites(profile) == expected, "Hold did not pin " + label
                    assert settings(profile)["main_tab"] == "3", "Hold opened " + label
                assert int(settings(profile)["enabled_apps"]) == 30, "Pinning changed app availability"
                # Moving out of a tile cancels a pending hold and its release.
                command("xdotool", "mousemove", "--window", window, str(tile_point[0]), str(tile_point[1]))
                command("xdotool", "mousedown", "1")
                time.sleep(.2)
                command("xdotool", "mousemove", "--window", window, "10", "80")
                time.sleep(.85)
                command("xdotool", "mouseup", "1")
                time.sleep(.3)
                assert favorites(profile) == [1, 2, 11, 3, 12], "Cancelled hold changed pins"
                key(window, "Escape")
                if mobile:
                    command("xdotool", "mousemove", "--window", window, "160", str(height - 42))
                    time.sleep(.3)
                    before = capture(window, name + "-dock-before-scroll")
                    command("xdotool", "click", "--repeat", "6", "--delay", "80", "5")
                    time.sleep(.6)
                    after = capture(window, name + "-dock-after-scroll")
                    dock_crop = (12, height - 84, width - 120, height)
                    assert ImageChops.difference(before.crop(dock_crop), after.crop(dock_crop)).getbbox(), "Pinned dock did not scroll"
                    apps_crop = (width - 100, height - 84, width, height)
                    assert ImageChops.difference(before.crop(apps_crop), after.crop(apps_crop)).getbbox() is None, "Scrolling moved Apps"
                # Apps stays accessible beside the larger, scrollable dock.
                large_apps = (width - 56, height - 42) if mobile else (44, min(112 + 5 * 84, height - 188) + 36)
                click(window, *large_apps)
                capture(window, name + "-all-favorites")

            with application(profile, name + "-pinned-restart", width, height) as (window, log):
                click(window, *large_apps)
                assert favorites(profile) == [1, 2, 11, 3, 12], "Restart truncated saved favorites"
                capture(window, name + "-all-favorites-restart")
                # Search results stay at a stable position even with several favorite rows.
                def search_app(label):
                    click(window, *((348, 138) if mobile else (382, 106)))
                    click(window, *search_point)
                    command("xdotool", "type", "--clearmodifiers", "--delay", "50", label)
                    time.sleep(.3)

                for label, expected in (("Habits", [2, 11, 3, 12]), ("Practice", [11, 3, 12]),
                                        ("Diary", [3, 12]), ("Lists", [12]), ("Lumi", [])):
                    search_app(label)
                    click(window, *tile_point, hold=.85)
                    assert favorites(profile) == expected, "Hold did not unpin " + label
                click(window, *((348, 138) if mobile else (382, 106)))
                time.sleep(.3)
                capture(window, name + "-empty")

            with application(profile, name + "-restart", width, height) as (window, log):
                assert favorites(profile) == [], "Restart restored unwanted default shortcuts"
                assert settings(profile)["main_tab"] == "3", "An unpinned app did not survive restart"
                # With no favorites the Apps button occupies the first desktop slot or mobile center.
                click(window, *( (195, height - 42) if mobile else (44, 148) ))
                click(window, *search_point)
                command("xdotool", "type", "--clearmodifiers", "--delay", "50", "no-such-app")
                time.sleep(.3)
                capture(window, name + "-no-results")
                click(window, *( (348, 138) if mobile else (382, 106) ))
                capture(window, name + "-cleared")
                # Profile and Settings remain reachable without any favorite.
                footer_y = height - (84 if mobile else 0) - 36
                click(window, *( (100, footer_y) if mobile else (44, height - 52) ))
                assert "->10" in log.read_text(), "Profile could not be reached"
                click(window, *( (195, height - 42) if mobile else (44, 148) ))
                click(window, *( (282, footer_y) if mobile else (220, footer_y) ))
                assert "->6" in log.read_text(), "Settings could not be reached"
                for label, main_tab, screen in (("Habits", 0, 11), ("Lists", 2, 16),
                                                ("Lumi", 4, 23), ("Practice", 1, 0), ("Diary", 3, 22)):
                    click(window, *( (195, height - 42) if mobile else (44, 148) ))
                    click(window, *search_point)
                    command("xdotool", "type", "--clearmodifiers", "--delay", "50", label)
                    time.sleep(.3)
                    click(window, *tile_point)
                    assert settings(profile)["main_tab"] == str(main_tab), label + " did not open"
                    assert "->" + str(screen) in log.read_text(), label + " route was not reached"
                assert favorites(profile) == [], "Opening apps added unwanted shortcuts"
                assert settings(profile)["enabled_apps"] == "31", "Bundled apps were not made available"

            # Existing navigation preferences migrate in order, and user data is retained.
            seed(profile, {"bottom_nav_route_count": 6, "bottom_nav_route_0": 12,
                           "bottom_nav_route_1": 1, "bottom_nav_route_2": 2,
                           "bottom_nav_route_3": 11, "bottom_nav_route_4": 3, "bottom_nav_route_5": 4})
            with sqlite3.connect(profile / "inbe.db") as db:
                db.execute("DELETE FROM settings WHERE user_id=? AND key LIKE 'launcher_favorite_%'", (user,))
                assert db.execute("SELECT title FROM elist_lists WHERE id='launcher-preserved-list'").fetchone()[0] == "Keep this list"
                assert db.execute("SELECT name FROM habits WHERE id='launcher-preserved-habit'").fetchone()[0] == "Keep this habit"
            with application(profile, name + "-migration", width, height) as (window, log):
                # A navigation action saves the migrated preferences through the normal app path.
                click(window, *( (70, height - 42) if mobile else (44, 148) ))
                assert favorites(profile) == [12, 1, 2, 11, 3], ("Legacy shortcut order was not fully migrated", favorites(profile))
            print(name + ": search, app activation, held pins, all favorites, empty favorites, restart, utility routes and migration passed")

    # Short windows must scroll the library while keeping navigation visible.
    with tempfile.TemporaryDirectory(prefix="inbe-launcher-short-") as temporary:
        profile = Path(temporary)
        with application(profile, "short-prepare", 390, 480):
            pass
        with sqlite3.connect(profile / "inbe.db") as db:
            user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
        seed(profile, {"language_setup_done": 1, "apps_setup_done": 1, "lumi_introduced": 1,
                       "tutorial_seen": 1, "habits_guide_seen": 1, "enabled_apps": 31, "ui_scale": 10,
                       "language": "en", "language_system": 0, "navigation_placement": 0,
                       "launcher_favorite_count": 2, "launcher_favorite_0": 1, "launcher_favorite_1": 2,
                       "cells_auto_update": 0, "apps_last_update_check": 1900000000})
        with application(profile, "short", 390, 480) as (window, log):
            click(window, 325, 438)
            command("xdotool", "mousemove", "--window", window, "190", "270")
            time.sleep(.4)
            before = capture(window, "short-before-scroll")
            command("xdotool", "mousemove", "--window", window, "190", "270")
            command("xdotool", "click", "--repeat", "8", "--delay", "80", "5")
            time.sleep(.5)
            after = capture(window, "short-after-scroll")
            assert ImageChops.difference(before.crop((20, 148, 370, 320)), after.crop((20, 148, 370, 320))).getbbox(), "Short library did not scroll"
            assert ImageChops.difference(before.crop((0, 396, 390, 480)), after.crop((0, 396, 390, 480))).getbbox() is None, "Scrolling moved the dock"

print("Launcher UI tests passed on owned private windows")
