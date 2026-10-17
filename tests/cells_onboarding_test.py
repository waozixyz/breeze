"""Verify first-start Apps, existing profiles and temporary mini practices.

The app runs with Kryon's test driver: controls are found in its widget tree
and pressed through its own pointer path.
"""

import contextlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

from ui_driver import UiDriver

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "build/cells-onboarding-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
assert int(os.environ["DISPLAY"].split(":")[-1].split(".")[0]) >= 300
driver = UiDriver(OUTPUT / "driver")
ENV = os.environ.copy()
ENV.update(APP_NO_TRAY="1", INBE_DEBUG_ROUTE="1", YUE_DESKTOP_RECOVERY="0")
ENV.update(driver.environment())


def command(*args):
    return subprocess.run(
        args, env=ENV, check=True, capture_output=True, text=True, timeout=5
    ).stdout.strip()


def wait_for(predicate, message, timeout=10):
    deadline = time.monotonic() + timeout
    while True:
        result = predicate()
        if result:
            return result
        assert time.monotonic() < deadline, message() if callable(message) else message
        time.sleep(0.05)


def key(window, name, changed):
    """Press a key the app reads from raylib directly, not through the test
    driver, until its effect shows; a dropped key is sent again."""
    for attempt in range(3):
        command("xdotool", "windowfocus", window)
        command("xdotool", "keydown", "--clearmodifiers", name)
        time.sleep(0.15)
        command("xdotool", "keyup", name)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if changed():
                return
            time.sleep(0.05)
    raise AssertionError(f"{name} had no effect")


def database(profile):
    # Read-only while the app runs: a read-write connection that closes
    # while the app has lost its own lock would checkpoint and delete the WAL
    # the app still writes to.
    uri = (profile / "inbe.db").as_uri() + "?mode=ro"
    return contextlib.closing(sqlite3.connect(uri, uri=True, timeout=5))


def settings(profile):
    with database(profile) as db:
        return dict(db.execute("SELECT key,value FROM settings"))


def wait_setting(profile, key, expected):
    wait_for(lambda: settings(profile).get(key) == str(expected),
             lambda: (key, expected, settings(profile)))


def wait_log(log, text):
    wait_for(lambda: text in log.read_text(), lambda: log.read_text())


def practice_counter():
    """The breath count in the practice's circle."""
    counts = [node for node in driver.tree() if node["kind"] == "text" and node["visible"]
              and node["label"].isdecimal() and node["height"] >= 100]
    assert counts, "Expanded practice counter missing"
    return counts[0]["label"]


@contextlib.contextmanager
def application(profile, label, *, mini=False, feature=None, graceful_close=False,
                mobile=False):
    environment = ENV | {"APP_DATA_ROOT": str(profile)}
    log_path = OUTPUT / f"{label}.log"
    with log_path.open("w") as log:
        app = subprocess.Popen(
            [sys.argv[1], *(["--mini"] if mini else []),
             *(["--feature", feature] if feature else [])], cwd=ROOT, env=environment,
            stdout=log, stderr=subprocess.STDOUT,
        )
        driver.attach(app, log_path)
        try:
            deadline = time.monotonic() + 20
            window = ""
            while time.monotonic() < deadline:
                assert app.poll() is None, log_path.read_text()
                found = subprocess.run(
                    ["xdotool", "search", "--all", "--onlyvisible", "--pid",
                     str(app.pid), "--name", "Inner Breeze"],
                    env=environment, text=True, capture_output=True, timeout=2,
                )
                if found.returncode == 0 and (profile / "inbe.db").exists():
                    window = found.stdout.splitlines()[0]
                    break
                time.sleep(0.1)
            assert window, (log_path.read_text(), found.stdout, found.stderr, list(profile.iterdir()))
            width = 393 if mobile else 400 if mini else 900
            height = 800 if mobile else 720
            command("xdotool", "windowsize", window, str(width), str(height))
            wait_for(lambda: driver.tree()[0]["width"] == width, "The app did not take its window size")
            driver.wait_idle(frames=3)
            yield window, log_path
            if graceful_close:
                assert app.wait(timeout=10) == 0, log_path.read_text()
            else:
                assert app.poll() is None, log_path.read_text()
        finally:
            if app.poll() is None:
                app.terminate()
                try:
                    app.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    app.kill()
                    app.wait(timeout=3)


result = {"display": os.environ["DISPLAY"], "deployment": False}
with tempfile.TemporaryDirectory(prefix="inbe-app-choices-") as temporary:
    profile = Path(temporary)
    # First start requires language confirmation before opening the Apps library.
    with application(profile, "fresh-apps") as (window, log):
        driver.wait(label="Choose Language")
        assert settings(profile)["language_setup_done"] == "0"
        driver.press(label="Next", role="button")
        wait_setting(profile, "language_setup_done", 1)
        driver.wait(label="Pinned")
        saved = settings(profile)
        assert saved["apps_setup_done"] == "0"
        assert saved["language_setup_done"] == "1"
        # A new profile comes with Lumi, Habits and Practice, pinned in that
        # order. They are defaults, not choices: stored at time 1 and not
        # queued, so an account's apps replace them after sign-in.
        assert saved["enabled_apps"] == "22"
        assert saved["launcher_favorite_count"] == "3"
        assert [int(saved[f"launcher_favorite_{i}"]) for i in range(3)] == [12, 1, 2]
        with database(profile) as db:
            defaults = {key: (value, updated) for key, value, updated in db.execute(
                "SELECT key,value,updated_at FROM settings WHERE key LIKE 'app_used_%'")}
            queued = db.execute("SELECT COUNT(*) FROM sync_outbox WHERE entity_type IN "
                                "('app_preference','app_order')").fetchone()[0]
        assert defaults == {f"app_used_{name}": (str(int(name in ("habits", "practices", "lumi"))), 1)
                            for name in ("lists", "habits", "practices", "diary", "lumi", "leaderboard")}, defaults
        assert queued == 0, "a new profile queued its default apps"
        assert "app_order" not in saved, "a new profile sent its default pins"
    # Closing before opening a tile keeps first-start Apps on restart.
    with application(profile, "resume-apps") as (window, log):
        driver.wait(label="Pinned")
        # Right steps through Lumi's guide's three steps to the end.
        for step in range(1, 4):
            driver.wait(label=f"Step {step} of 3")
            key(window, "Right", lambda: not driver.find(label=f"Step {step} of 3", visible=True))
        wait_setting(profile, "launcher_guide_seen", 1)
        # With the guide finished, Apps asks once about app updates.
        driver.wait(label="Allow", role="button")
        driver.press(label="Don't allow", role="button")
        wait_setting(profile, "package_updates_allowed", 0)
        driver.wait_gone(label="Don't allow")
        driver.press(label="Find an app", role="text_field")
        driver.type("Lists")
        driver.wait(label="Find an app", role="text_field", value="Lists")
        # Lists is not installed, so its card is the first in More apps.
        more_apps = driver.wait(label="More apps")
        cards = [node for node in driver.find(role="button", visible=True)
                 if node["y"] > more_apps["y"] and node["label"] not in ("Install", "Uninstall")
                 and node["y"] < driver.wait(label="Profile", role="button")["y"]]
        assert cards and cards[0]["label"] == "Lists", cards
        driver.press(key=cards[0]["key"], label="Lists")
        wait_setting(profile, "apps_setup_done", 1)
        wait_setting(profile, "main_tab", 2)
        wait_log(log, "screen=21->16")
    with sqlite3.connect(profile / "inbe.db") as db:
        user = db.execute("SELECT id FROM users WHERE kind='local'").fetchone()[0]
        db.execute("INSERT INTO elist_lists(id,user_id,title,sort_order,deleted_at,updated_at) VALUES(?,?,?,0,0,1)",
                   ("choice-preserved-list", user, "Saved while Lists is enabled"))
        values = {"habits_guide_seen": 1, "lumi_guides_seen": 127, "tutorial_seen": 1, "package_updates_allowed": 0,
                  "apps_last_update_check": 1900000000}
        for key_name, value in values.items():
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                       "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user, key_name, str(value)))
    # Mini is explicitly temporary Practice, independently of saved choices.
    for mask in (1, 0):
        with sqlite3.connect(profile / "inbe.db") as db:
            db.execute("DELETE FROM settings WHERE key LIKE 'app_used_%'")
            db.execute("UPDATE settings SET value=? WHERE key='enabled_apps'", (str(mask),))
            db.execute("UPDATE settings SET value='0' WHERE key='exercise_type'")
            db.execute("UPDATE settings SET value='1' WHERE key='advanced_session_controls'")
            before = list(db.iterdump())
        with application(profile, f"mini-mask-{mask}", mini=True) as (window, log):
            driver.press(label="Start Practice", role="button")
            wait_log(log, "screen=0->1")
            driver.wait(label="Pause", role="button")
        with sqlite3.connect(profile / "inbe.db") as db:
            assert list(db.iterdump()) == before, "Mini changed the persisted profile"
        assert settings(profile)["enabled_apps"] == str(mask)
        # Expanding an active mini session must preserve both its ticking
        # and the full profile's selection through a later normal save/close.
        with application(
            profile, f"mini-expand-{mask}", mini=True, graceful_close=True
        ) as (window, log):
            driver.press(label="Start Practice", role="button")
            wait_log(log, "screen=0->1")
            driver.press(label="Open full app", role="button")
            command("xdotool", "windowmove", window, "0", "0")
            # The practice goes on in the full window, which can shrink it again.
            driver.wait(label="Minimize", role="button")
            wait_for(lambda: driver.tree()[0]["width"] == 900, lambda: driver.tree()[0])
            # Breathing displays its countdown/breath count in the circle,
            # rather than Patterns' top elapsed-time status; it must change.
            first_count = practice_counter()
            wait_for(lambda: practice_counter() != first_count,
                     "Expanded mini practice counter stopped advancing")
            assert settings(profile)["enabled_apps"] == str(mask)
            # Active practice uses the whole window. Its established pause
            # then close action returns to the full profile before Settings.
            driver.press(label="Pause", role="button")
            driver.wait(contains="play", role="button")
            driver.press(label="Close", role="button")
            driver.wait(label="Apps", role="button")
            assert [node for node in driver.tree() if node["kind"] == "navigation_bar"], \
                "Closing the practice did not return to the full app"
            # A real full-app settings action, zooming in and back, saves
            # the unchanged selection with every other setting.
            scale = settings(profile).get("ui_scale")
            driver.key("=", control=True)
            wait_for(lambda: settings(profile).get("ui_scale") != scale, "Zooming saved nothing")
            driver.key("0", control=True)
            wait_setting(profile, "ui_scale", 10)
            assert settings(profile)["enabled_apps"] == str(mask)
            # Ctrl+Q follows the owned window's normal quit and app_destroy
            # path, rather than relying on process termination for this check.
            key(window, "ctrl+q", lambda: "APP: quit requested" in log.read_text())
        assert settings(profile)["enabled_apps"] == str(mask)
        with sqlite3.connect(profile / "inbe.db") as db:
            assert db.execute("SELECT id FROM users WHERE kind='local'").fetchone()[0] == user
            assert db.execute("SELECT title FROM elist_lists WHERE id='choice-preserved-list'").fetchone()[0] == "Saved while Lists is enabled"
        with application(profile, f"restart-after-expand-{mask}") as (window, log):
            assert settings(profile)["enabled_apps"] == str(mask)
    # One host runtime can explicitly open disabled children, preserving data.
    with sqlite3.connect(profile / "inbe.db") as db:
        db.execute("DELETE FROM settings WHERE key LIKE 'app_used_%'")
        db.execute("UPDATE settings SET value='0' WHERE key='enabled_apps'")
    with application(profile, "explicit-habits", feature="habits") as (window, log):
        wait_setting(profile, "enabled_apps", 2)
        wait_log(log, "screen=6->11")
        driver.wait(label="+ New Habit", role="button")
        command("xprop", "-id", window, "-f", "_HARMONY_APP_FEATURE", "32c",
                "-set", "_HARMONY_APP_FEATURE", "4")
        wait_setting(profile, "enabled_apps", 6)
        wait_log(log, "screen=11->0")
        assert "not found" in command("xprop", "-id", window, "_HARMONY_APP_FEATURE")
        driver.wait(label="Start Practice", role="button")
        command("xprop", "-id", window, "-f", "_HARMONY_APP_FEATURE", "32c",
                "-set", "_HARMONY_APP_FEATURE", "2")
        wait_log(log, "screen=0->11")
        with database(profile) as db:
            assert db.execute("SELECT id FROM users WHERE kind='local'").fetchone()[0] == user
            assert db.execute("SELECT title FROM elist_lists WHERE id='choice-preserved-list'").fetchone()[0] == "Saved while Lists is enabled"
    # Upgrading keeps the selected page and repairs missing selected shortcuts.
    with sqlite3.connect(profile / "inbe.db") as db:
        db.execute("DELETE FROM settings WHERE key IN ('enabled_apps','apps_setup_done') OR key LIKE 'app_used_%'")
        db.execute("DELETE FROM settings WHERE key IN ('lumi_introduced','leaderboard_introduced')")
        # This represents an established profile whose existing guides are done.
        db.execute("UPDATE settings SET value='1' WHERE key IN ('tutorial_seen','habits_guide_seen')")
        db.execute("UPDATE settings SET value='0' WHERE key='main_tab'")
    with application(profile, "existing-profile") as (window, log):
        # Upgrading also installs Leaderboard once, without pinning it.
        wait_setting(profile, "enabled_apps", 55)
        wait_setting(profile, "main_tab", 0)
        routes = [int(settings(profile)[f"bottom_nav_route_{index}"])
                  for index in range(int(settings(profile)["bottom_nav_route_count"]))]
        assert 12 in routes and routes[-1] == 4, routes
        # Sidebar order survives the earlier choices; open Lists through the
        # same app route rather than assuming a fixed shortcut position.
        command("xprop", "-id", window, "-f", "_HARMONY_APP_FEATURE", "32c",
                "-set", "_HARMONY_APP_FEATURE", "1")
        wait_log(log, "->16")
    result.update(
        first_start_apps_library=True, system_language=True,
        default_apps_lumi_habits_practice=True, default_apps_not_sent=True, restart_in_onboarding=True,
        open_tile_completes_setup=True, explicit_feature_cli=True,
        same_runtime_feature_property=True, mini_lists_only_and_zero_apps=True,
        mini_starts_practice_without_profile_writes=True,
        mini_expansion_preserves_selection_and_session=True,
        mini_expansion_clock_advances=True,
        mini_expansion_explicit_save_and_graceful_quit=True,
        data_and_identity_preserved=True, existing_profile_keeps_all_apps=True,
        upgrade_keeps_selected_page_and_repairs_shortcuts=True,
    )
(OUTPUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
