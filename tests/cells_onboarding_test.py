"""Verify real onboarding choices and restarts on a private display/profile."""

import contextlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "build/cells-onboarding-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
assert int(os.environ["DISPLAY"].split(":")[-1].split(".")[0]) >= 300
ENV = os.environ.copy()
ENV.update(APP_NO_TRAY="1", INBE_DEBUG_ROUTE="1", YUE_DESKTOP_RECOVERY="0")


def command(*args):
    return subprocess.run(
        args, env=ENV, check=True, capture_output=True, text=True, timeout=5
    ).stdout.strip()


def capture(window, name):
    raw = OUTPUT / f"{name}.xwd"
    png = OUTPUT / f"{name}.png"
    command("xwd", "-silent", "-id", window, "-out", str(raw))
    command("convert", str(raw), str(png))
    raw.unlink()
    with Image.open(png) as image:
        return image.convert("RGB").copy()


def tap(window, x, y):
    command("xdotool", "mousemove", "--window", window, str(x), str(y))
    command("xdotool", "mousedown", "1")
    time.sleep(0.08)
    command("xdotool", "mouseup", "1")
    time.sleep(0.5)


def settings(profile):
    with sqlite3.connect(profile / "inbe.db", timeout=5) as db:
        return dict(db.execute("SELECT key,value FROM settings"))


def wait_setting(profile, key, expected):
    deadline = time.monotonic() + 10
    while settings(profile).get(key) != str(expected):
        assert time.monotonic() < deadline, (key, expected, settings(profile))
        time.sleep(0.1)


def scroll_picker(window, bottom):
    command("xdotool", "mousemove", "--window", window, "450", "500")
    command("xdotool", "click", "--repeat", "10", "--delay", "70", "5" if bottom else "4")
    time.sleep(0.4)


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
            width = "393" if mobile else "400" if mini else "900"
            command("xdotool", "windowsize", window, width, "800" if mobile else "720")
            command("xdotool", "windowfocus", window)
            time.sleep(1)
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
    # Keep package-network timing out of layout and selection assertions.
    for prepared in (profile, profile / "recommended"):
        with application(prepared, "prepare-" + prepared.name) as (window, log):
            with sqlite3.connect(prepared / "inbe.db") as db:
                user = db.execute("SELECT id FROM users LIMIT 1").fetchone()[0]
                db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                           "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value",
                           (user, "apps_last_update_check", "1900000000"))
    with application(profile / "recommended", "fresh-recommended") as (window, log):
        tap(window, 450, 425)
        wait_setting(profile / "recommended", "language_setup_done", 1)
        capture(window, "recommended-cells")
        tap(window, 450, 676)
        wait_setting(profile / "recommended", "enabled_apps", 22)
        wait_setting(profile / "recommended", "main_tab", 4)
        assert "screen=21->23" in log.read_text(), log.read_text()
        time.sleep(1)
        assert "screen=23->21" not in log.read_text(), "Router restored the chooser after opening Lumi"
        capture(window, "recommended-lumi-home")
    with application(profile, "fresh-language") as (window, log):
        capture(window, "fresh-language")
        assert settings(profile)["apps_setup_done"] == "0"
        tap(window, 450, 425)
        wait_setting(profile, "language_setup_done", 1)
        assert "screen=8->21" in log.read_text(), log.read_text()
        assert settings(profile)["apps_setup_done"] == "0"
        capture(window, "after-language-apps")
        scroll_picker(window, True)
        tap(window, 618, 566)
        wait_setting(profile, "cells_auto_update", 0)
    # Restart between language and app selection must still show the chooser.
    with application(profile, "resume-chooser") as (window, log):
        capture(window, "resumed-apps")
        assert settings(profile)["cells_auto_update"] == "0"
        scroll_picker(window, True)
        tap(window, 618, 566)
        wait_setting(profile, "cells_auto_update", 1)
        scroll_picker(window, False)
        tap(window, 260, 218)  # Lumi off
        tap(window, 260, 290)  # Habits off
        tap(window, 260, 362)  # Practices off
        tap(window, 260, 474)  # Optional Lists on
        tap(window, 450, 676)
        wait_setting(profile, "enabled_apps", 1)
        wait_setting(profile, "apps_setup_done", 1)
        assert "screen=21->16" in log.read_text(), log.read_text()
        capture(window, "lists-only")
    with sqlite3.connect(profile / "inbe.db") as db:
        user = db.execute("SELECT id FROM users WHERE kind='local'").fetchone()[0]
        db.execute(
            "INSERT INTO elist_lists(id,user_id,title,sort_order,deleted_at,updated_at) VALUES(?,?,?,0,0,1)",
            ("choice-preserved-list", user, "Saved while Lists is enabled"),
        )
        db.execute("UPDATE settings SET value='0' WHERE key='apps_setup_done'")
    # The chooser can select no apps; Settings remains usable and data is kept.
    with application(profile, "choose-none") as (window, log):
        tap(window, 260, 474)  # Lists off
        tap(window, 450, 676)
        wait_setting(profile, "enabled_apps", 0)
        assert "screen=21->6" in log.read_text(), log.read_text()
        capture(window, "settings-no-apps")
    with application(profile, "restart-none") as (window, log):
        capture(window, "restart-settings-no-apps")
        assert settings(profile)["enabled_apps"] == "0"
        with sqlite3.connect(profile / "inbe.db") as db:
            assert db.execute("SELECT title FROM elist_lists WHERE id='choice-preserved-list'").fetchone()[0] == "Saved while Lists is enabled"
            assert db.execute("SELECT id FROM users WHERE kind='local'").fetchone()[0] == user
        tap(window, 330, 382)  # Apps & sidebar.
        capture(window, "apps-sidebar-none")
        tap(window, 825, 166)  # Add Habits from the unified list.
        wait_setting(profile, "enabled_apps", 2)
        capture(window, "settings-habits-reenabled")
    with sqlite3.connect(profile / "inbe.db") as db:
        db.execute("UPDATE settings SET value='1' WHERE key='habits_guide_seen'")
    with application(profile, "mobile-apps", mobile=True) as (window, log):
        tap(window, 295, 774)  # Settings in the bottom navigation.
        tap(window, 196, 486)  # Apps & sidebar in the narrow settings hub.
        capture(window, "mobile-apps-before")
        for cycle in range(3):
            tap(window, 335, 268)  # Add the bundled Diary app.
            wait_setting(profile, "enabled_apps", 10)
            tap(window, 335, 156)  # Hide Diary; its package stays installed.
            wait_setting(profile, "enabled_apps", 2)
        capture(window, "mobile-apps-after")
    # Mini is explicitly temporary Practice, independently of saved choices.
    for mask in (1, 0):
        with sqlite3.connect(profile / "inbe.db") as db:
            db.execute("DELETE FROM settings WHERE key LIKE 'app_used_%'")
            db.execute("UPDATE settings SET value=? WHERE key='enabled_apps'", (str(mask),))
            db.execute("UPDATE settings SET value='0' WHERE key='exercise_type'")
            db.execute("UPDATE settings SET value='1' WHERE key='advanced_session_controls'")
            before = list(db.iterdump())
        with application(profile, f"mini-mask-{mask}", mini=True) as (window, log):
            capture(window, f"mini-mask-{mask}-menu")
            tap(window, 200, 614)
            deadline = time.monotonic() + 10
            while "screen=0->1" not in log.read_text():
                assert time.monotonic() < deadline, log.read_text()
                time.sleep(0.1)
            capture(window, f"mini-mask-{mask}-practice")
        with sqlite3.connect(profile / "inbe.db") as db:
            assert list(db.iterdump()) == before, "Mini changed the persisted profile"
        assert settings(profile)["enabled_apps"] == str(mask)
        # Expanding an active mini session must preserve both its ticking
        # and the full profile's selection through a later normal save/close.
        with application(
            profile, f"mini-expand-{mask}", mini=True, graceful_close=True
        ) as (window, log):
            tap(window, 200, 614)
            assert "screen=0->1" in log.read_text(), log.read_text()
            tap(window, 366, 34)
            command("xdotool", "windowmove", window, "0", "0")
            time.sleep(1)
            command("xdotool", "mousemove", "--window", window, "20", "20")
            first = capture(window, f"mini-expanded-{mask}-session")
            # Breathing displays its countdown/breath count in the circle,
            # rather than Patterns' top elapsed-time status. Isolate its dark
            # numeral from the light animated circle and require it to change.
            counter = (425, 330, 475, 390)
            first_count = first.crop(counter).convert("L").point(
                lambda value: 255 if value < 130 else 0
            )
            assert first_count.getbbox(), "Expanded practice counter missing"
            deadline = time.monotonic() + 10
            while True:
                time.sleep(1.1)
                advanced = capture(window, f"mini-expanded-{mask}-advanced")
                advanced_count = advanced.crop(counter).convert("L").point(
                    lambda value: 255 if value < 130 else 0
                )
                if ImageChops.difference(first_count, advanced_count).getbbox():
                    break
                assert time.monotonic() < deadline, "Expanded mini practice counter stopped advancing"
            geometry = command("xdotool", "getwindowgeometry", "--shell", window)
            assert "WIDTH=900" in geometry, geometry
            assert settings(profile)["enabled_apps"] == str(mask)
            # Active practice uses the whole window. Its established pause
            # then close action returns to the full profile before Settings.
            tap(window, 450, 692)  # The enabled breathing controls' Pause.
            tap(window, 866, 38)
            deadline = time.monotonic() + 10
            while log.read_text().count("APP PROBE: app init complete") < 2:
                assert time.monotonic() < deadline, log.read_text()
                time.sleep(0.1)
            capture(window, f"mini-expanded-{mask}-exited")
            # A real full-app settings action saves the unchanged selection.
            tap(window, 110, 670)
            tap(window, 330, 382)  # Apps & sidebar retains the selection.
            capture(window, f"mini-expanded-{mask}-apps")
            assert settings(profile)["enabled_apps"] == str(mask)
            # Ctrl+Q follows the owned window's normal quit and app_destroy
            # path, rather than relying on process termination for this check.
            command("xdotool", "keydown", "ctrl+q")
            time.sleep(0.15)
            command("xdotool", "keyup", "ctrl+q")
            deadline = time.monotonic() + 10
            while "APP: quit requested" not in log.read_text():
                assert time.monotonic() < deadline, log.read_text()
                time.sleep(0.1)
        assert settings(profile)["enabled_apps"] == str(mask)
        with sqlite3.connect(profile / "inbe.db") as db:
            assert db.execute("SELECT id FROM users WHERE kind='local'").fetchone()[0] == user
            assert db.execute("SELECT title FROM elist_lists WHERE id='choice-preserved-list'").fetchone()[0] == "Saved while Lists is enabled"
        with application(profile, f"restart-after-expand-{mask}") as (window, log):
            capture(window, f"restart-after-expand-{mask}")
            assert settings(profile)["enabled_apps"] == str(mask)
    # One host runtime can explicitly open disabled children, preserving data.
    with sqlite3.connect(profile / "inbe.db") as db:
        db.execute("DELETE FROM settings WHERE key LIKE 'app_used_%'")
        db.execute("UPDATE settings SET value='0' WHERE key='enabled_apps'")
    with application(profile, "explicit-habits", feature="habits") as (window, log):
        wait_setting(profile, "enabled_apps", 2)
        assert "screen=6->11" in log.read_text(), log.read_text()
        capture(window, "explicit-habits")
        command("xprop", "-id", window, "-f", "_HARMONY_APP_FEATURE", "32c",
                "-set", "_HARMONY_APP_FEATURE", "4")
        wait_setting(profile, "enabled_apps", 6)
        assert "screen=11->0" in log.read_text(), log.read_text()
        assert "not found" in command("xprop", "-id", window, "_HARMONY_APP_FEATURE")
        capture(window, "same-runtime-practices")
        command("xprop", "-id", window, "-f", "_HARMONY_APP_FEATURE", "32c",
                "-set", "_HARMONY_APP_FEATURE", "2")
        deadline = time.monotonic() + 10
        while "screen=0->11" not in log.read_text():
            assert time.monotonic() < deadline, log.read_text()
            time.sleep(0.1)
        capture(window, "same-runtime-habits")
        with sqlite3.connect(profile / "inbe.db") as db:
            assert db.execute("SELECT id FROM users WHERE kind='local'").fetchone()[0] == user
            assert db.execute("SELECT title FROM elist_lists WHERE id='choice-preserved-list'").fetchone()[0] == "Saved while Lists is enabled"
    # Upgrading keeps the selected page and repairs missing selected shortcuts.
    with sqlite3.connect(profile / "inbe.db") as db:
        db.execute("DELETE FROM settings WHERE key IN ('enabled_apps','apps_setup_done') OR key LIKE 'app_used_%'")
        db.execute("DELETE FROM settings WHERE key='lumi_introduced'")
        # This represents an established profile whose existing guides are done.
        db.execute("UPDATE settings SET value='1' WHERE key IN ('tutorial_seen','habits_guide_seen')")
        db.execute("UPDATE settings SET value='0' WHERE key='main_tab'")
    with application(profile, "existing-profile") as (window, log):
        capture(window, "existing-profile-all-apps")
        wait_setting(profile, "enabled_apps", 23)
        wait_setting(profile, "main_tab", 0)
        routes = [int(settings(profile)[f"bottom_nav_route_{index}"])
                  for index in range(int(settings(profile)["bottom_nav_route_count"]))]
        assert 12 in routes and routes[-1] == 4, routes
        # Sidebar order survives the earlier choices; open Lists through the
        # same app route rather than assuming a fixed shortcut position.
        command("xprop", "-id", window, "-f", "_HARMONY_APP_FEATURE", "32c",
                "-set", "_HARMONY_APP_FEATURE", "1")
        wait_for_lists = time.monotonic() + 10
        while "->16" not in log.read_text():
            assert time.monotonic() < wait_for_lists, log.read_text()
            time.sleep(0.1)
        capture(window, "existing-data-lists")
    result.update(
        lumi_first_recommended_default_home=True,
        language_then_apps=True, restart_in_onboarding=True,
        auto_update_switch_persists=True,
        lists_only=True, zero_apps_settings=True, restart_choices=True,
        settings_reenable=True, explicit_feature_cli=True, same_runtime_feature_property=True, mini_lists_only_and_zero_apps=True,
        mini_starts_practice_without_profile_writes=True,
        mini_expansion_preserves_selection_and_session=True,
        mini_expansion_clock_advances=True,
        mini_expansion_explicit_save_and_graceful_quit=True,
        data_and_identity_preserved=True, existing_profile_keeps_all_apps=True,
        upgrade_keeps_selected_page_and_repairs_shortcuts=True,
        narrow_layout_repeated_diary_add_remove=True,
    )
(OUTPUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
