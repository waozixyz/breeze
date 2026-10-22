#!/usr/bin/env python3
"""Apps from the node open only once they are on this device.

Radio is installed on the account, as from another device, but its package
never reached this one; Photos is only offered. The network is cut off, so
nothing downloads. Tapping Radio's pin in the navigation, either app in
Apps, or launching with --app radio must not open them, and "Installing
this app" is never drawn. The app runs on a private Xvfb display; widgets
come from Kryon's test driver and routes from the app's debug log, never
from screenshots.
"""
import contextlib
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import time

from ui_driver import UiDriver

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/node-app-not-installed-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
BINARY = Path(sys.argv[1]).resolve()
DESKTOP_ENV = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS")
assert all(not os.environ.get(key) for key in DESKTOP_ENV), "Inherited desktop environment"
WIDTH, HEIGHT = 390, 844
# ScreenNodeApp, the screen of an app the node offers.
NODE_APP_SCREEN = "26"
# The navigation's buttons share this focus group.
NAVIGATION = 6600
# Routes: Diary, then the app in the node's first slot.
DIARY_ROUTE, FIRST_NODE_APP_ROUTE = 11, 14
SWITCH = re.compile(r"ROUTE switch frame=\d+ screen=(\d+)->(\d+)")


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def wait(predicate, description, timeout=30):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        value = predicate()
        if value:
            return value
        time.sleep(.05)
    raise AssertionError(description)


with contextlib.ExitStack() as stack:
    profile = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="inbe-node-closed-")))
    env = {key: value for key, value in os.environ.items() if key not in DESKTOP_ENV}
    for key in ("HARMONY_DATA_ROOT", "INBE_DIARY_IMPORT", "INBE_NODE_APP_FILE"):
        env.pop(key, None)
    # Offline: a download Radio or Photos asks for fails at once.
    env.update(YUE_DESKTOP_RECOVERY="0", APP_NO_TRAY="1", SDL_AUDIODRIVER="dummy",
               APP_DATA_ROOT=str(profile), INBE_DEBUG_ROUTE="1",
               https_proxy="http://127.0.0.1:9", http_proxy="http://127.0.0.1:9", NO_PROXY="")
    display_log = stack.enter_context((OUTPUT / "display.log").open("w"))
    display = subprocess.Popen(["Xvfb", "-displayfd", "1", "-screen", "0", "1200x1000x24",
                                "-nolisten", "tcp"], env=env, stdout=subprocess.PIPE, stderr=display_log)
    stack.callback(stop, display)
    number = display.stdout.readline().decode().strip()
    display.stdout.close()
    assert number.isdecimal(), "Private display did not start"
    env["DISPLAY"] = ":" + number
    driver = UiDriver(OUTPUT / "driver")
    env.update(driver.environment())

    @contextlib.contextmanager
    def application(name, *arguments):
        log_path = OUTPUT / (name + ".log")
        with log_path.open("w") as log:
            app = subprocess.Popen([str(BINARY), *arguments], cwd=ROOT, env=env,
                                   stdout=log, stderr=subprocess.STDOUT)
            driver.attach(app, log_path)
            try:
                def window():
                    assert app.poll() is None, log_path.read_text()[-4000:]
                    result = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                                            env=env, capture_output=True, text=True, timeout=5)
                    return result.stdout.splitlines()[0] if result.returncode == 0 else None
                owned_window = wait(window, "App did not map a window")
                subprocess.run(["xdotool", "windowsize", owned_window, str(WIDTH), str(HEIGHT)],
                               env=env, check=True, capture_output=True)
                wait(lambda: (profile / "inbe.db").exists(), "Database was not created")
                wait(lambda: driver.tree(), "App did not draw")
                yield owned_window, log_path
                assert app.poll() is None, log_path.read_text()[-4000:]
            finally:
                stop(app)

    def settings():
        uri = (profile / "inbe.db").as_uri() + "?mode=ro"
        with contextlib.closing(sqlite3.connect(uri, uri=True, timeout=3)) as db:
            return dict(db.execute("SELECT key,value FROM settings WHERE user_id=?", (user,)))

    def stays_closed(log_path, step):
        """No route reaches an app's screen, and the installing notice never shows."""
        driver.wait_idle(frames=5, timeout=3)
        # Long enough for a deferred switch or a download failure to land.
        time.sleep(1.0)
        driver.wait_idle(frames=3, timeout=3)
        opened = [switch for switch in SWITCH.findall(log_path.read_text()) if switch[1] == NODE_APP_SCREEN]
        assert not opened, f"{step}: an app that is not installed opened: {opened}"
        text = driver.text(visible=False)
        assert "Installing this app" not in text and "node_app_installing" not in text, \
            f"{step}: the installing notice was drawn:\n{text}"

    def apps_open():
        return driver.find(label="Find an app", role="text_field", visible=True)

    def grid_cards(label):
        """Apps cards with this label, outside the navigation."""
        return [node for node in driver.find(label=label, role="button", visible=True)
                if node.get("focus_id") != NAVIGATION and node["width"] > 60]

    with application("initialize"):
        pass
    with contextlib.closing(sqlite3.connect(profile / "inbe.db")) as db, db:
        user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
        seeded = dict(language="en", language_system=0, language_setup_done=1, apps_setup_done=1,
                      enabled_apps=63, lumi_introduced=1, tutorial_seen=1, habits_guide_seen=1,
                      launcher_guide_seen=1, lumi_guides_seen=127, main_tab=3,
                      # No update check or catalog read is due.
                      package_updates_allowed=0, apps_last_update_check=1900000000,
                      node_apps_checked_at=int(time.time()),
                      node_apps_offers="radio|Radio\nphotos|Photos\n",
                      node_app_size_radio=120000, node_app_size_photos=150000,
                      # Radio is on the account in this device's first slot,
                      # without its package; it is pinned after Diary.
                      node_app_slot_0="radio", app_used_radio=1,
                      launcher_favorite_count=2, launcher_favorite_0=DIARY_ROUTE,
                      launcher_favorite_1=FIRST_NODE_APP_ROUTE)
        for name in ("lists", "habits", "practices", "diary", "lumi", "leaderboard"):
            seeded["app_used_" + name] = 1
        for key, value in seeded.items():
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                       "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user, key, str(value)))

    with application("taps") as (window, log_path):
        driver.wait(label="Apps", role="button", focus_id=NAVIGATION)
        stays_closed(log_path, "start")

        # Radio's pin in the navigation.
        driver.press(label="Radio", role="button", focus_id=NAVIGATION)
        stays_closed(log_path, "navigation pin")

        # Radio's card in Apps: Apps stays open on its list.
        driver.press(label="Apps", role="button", focus_id=NAVIGATION)
        wait(apps_open, "Apps did not open")
        radio = wait(lambda: grid_cards("Radio"), "Radio has no card in Apps")[0]
        driver.press(key=radio["key"], label="Radio")
        stays_closed(log_path, "Apps card")
        assert apps_open(), "Tapping an app that is not installed closed Apps"

        # Photos is only offered: the tap installs it on the account, as
        # before, and does not open it.
        driver.press(label="Find an app", role="text_field")
        driver.type("Photos")
        photos = wait(lambda: grid_cards("Photos"), "Photos is not offered in Apps")[0]
        driver.press(key=photos["key"], label="Photos")
        wait(lambda: settings().get("app_used_photos") == "1", "The Photos tap was not taken")
        stays_closed(log_path, "offered app")
        assert apps_open(), "Tapping an offered app closed Apps"

    # A launcher's shortcut asks for Radio by name: Inbe starts on its own
    # page, with its navigation, instead of on Radio's.
    with application("launcher", "--app", "radio") as (window, log_path):
        driver.wait(label="Apps", role="button", focus_id=NAVIGATION)
        stays_closed(log_path, "launcher shortcut")
        driver.wait(label="Apps", role="button", focus_id=NAVIGATION)
        title = subprocess.run(["xdotool", "getwindowname", window], env=env,
                               capture_output=True, text=True, timeout=5).stdout.strip()
        assert title != "Radio", "The launcher opened Radio"

print("Apps from the node that are not on this device stay closed from the navigation, "
      "Apps, an offer and a launcher shortcut, and never show the installing notice")
