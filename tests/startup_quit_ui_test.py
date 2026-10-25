"""First-run Apps, saved preferences and Quit on a private display/profile."""
import contextlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

from ui_driver import UiDriver, UiDriverError

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/startup-quit-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
BINARY = Path(sys.argv[1]).resolve()
KEYS = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS")
assert all(not os.environ.get(key) for key in KEYS), "Inherited desktop environment"


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


with tempfile.TemporaryDirectory(prefix="inbe-startup-quit-") as temporary, contextlib.ExitStack() as stack:
    # A private command folder, so concurrent runs never answer each other.
    driver = UiDriver(Path(temporary) / "driver")
    env = {key: value for key, value in os.environ.items() if key not in KEYS}
    env.pop("INBE_DIARY_IMPORT", None)
    env.update(driver.environment())
    env.update(YUE_DESKTOP_RECOVERY="0", APP_NO_TRAY="1", SDL_AUDIODRIVER="dummy",
               INBE_DEBUG_ROUTE="1")
    display_log = stack.enter_context((OUTPUT / "display.log").open("w"))
    server = subprocess.Popen(["Xvfb", "-noreset", "-displayfd", "1", "-screen", "0", "1280x900x24",
                               "-nolisten", "tcp"], env=env, stdout=subprocess.PIPE, stderr=display_log)
    stack.callback(stop, server)
    number = server.stdout.readline().decode().strip()
    server.stdout.close()
    assert number.isdecimal()
    env["DISPLAY"] = ":" + number

    def command(*args):
        return subprocess.run(args, env=env, check=True, capture_output=True,
                              text=True, timeout=5).stdout.strip()

    def settings(profile):
        with sqlite3.connect(profile / "inbe.db", timeout=3) as db:
            return dict(db.execute("SELECT key,value FROM settings"))

    def wait_log(log, text, message):
        deadline = time.monotonic() + 5
        while text not in log.read_text():
            assert time.monotonic() < deadline, message + "\n" + log.read_text()
            time.sleep(.05)

    def in_navigation(label):
        """The sidebar's button with this label."""
        nodes = driver.tree()
        bars = {node["index"] for node in nodes if node["kind"] == "navigation_bar"}
        matches = [node for node in nodes if node["label"] == label and node["parent"] in bars
                   and node["visible"]]
        assert len(matches) == 1, f"the sidebar has {len(matches)} {label} buttons"
        return matches[0]

    @contextlib.contextmanager
    def application(profile, name, *args, preview=False):
        log_path = OUTPUT / (name + ".log")
        with log_path.open("w") as log:
            environment = env | {"APP_DATA_ROOT": str(profile)}
            if preview:
                environment["APP_SHOT_WINDOW"] = "1"
            app = subprocess.Popen([str(BINARY), *args], cwd=ROOT, env=environment,
                                   stdout=log, stderr=subprocess.STDOUT)
            driver.attach(app, log_path)
            try:
                deadline = time.monotonic() + 15
                window = ""
                while time.monotonic() < deadline:
                    assert app.poll() is None, log_path.read_text()
                    found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                                           env=env, capture_output=True, text=True, timeout=2)
                    if found.returncode == 0 and found.stdout.strip():
                        window = found.stdout.splitlines()[0]
                        break
                    time.sleep(.05)
                assert window, log_path.read_text()
                command("xdotool", "windowsize", window, "900", "720")
                # Wait until the app lays out the resized window and settles.
                while True:
                    screen = next(node for node in driver.tree() if node["kind"] == "screen")
                    if (screen["width"], screen["height"]) == (900, 720):
                        break
                    assert time.monotonic() < deadline + 15, \
                        f"{name}: the app kept a {screen['width']}x{screen['height']} layout"
                    time.sleep(.05)
                driver.wait_idle(frames=3)
                yield app, window, log_path
                assert "frame rejected" not in log_path.read_text(), log_path.read_text()
            finally:
                stop(app)
                # Preview windows keep their profile in a per-process folder.
                shutil.rmtree(Path("/tmp") / f"inbe-screenshot-{app.pid}", ignore_errors=True)

    receipts = {}
    # Both root artifacts open the ready-to-use Apps library and migrate old
    # navigation settings without rewriting an owner's saved app preferences.
    for full in (False, True):
        profile = Path(temporary) / ("full" if full else "base")
        args = ["--bundle", str(ROOT / "build/inbe-full.zx")] if full else []
        with application(profile, profile.name + "-prepare", *args):
            pass
        with sqlite3.connect(profile / "inbe.db") as db:
            user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
            values = {"language": "en", "language_system": 0, "language_setup_done": 1,
                      "apps_setup_done": 0, "enabled_apps": 22, "lumi_introduced": 1,
                      "package_updates_allowed": 0, "apps_last_update_check": 1900000000,
                      "tutorial_seen": 1, "habits_guide_seen": 1, "lumi_guides_seen": 127, "launcher_guide_seen": 1,
                      "ui_scale": 10,
                      "navigation_placement": 1, "navigation_collapsed": 0,
                      "bottom_nav_route_count": 2, "bottom_nav_route_0": 0,
                      "bottom_nav_route_1": 4}
            for bit, name in enumerate(("lists", "habits", "practices", "diary", "lumi", "leaderboard")):
                values["app_used_" + name] = int(bool(int(values["enabled_apps"]) & (1 << bit)))
            for key, value in values.items():
                db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,2) "
                           "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at", (user, key, str(value)))
        with application(profile, profile.name + "-all", *args) as (app, window, log):
            # The Apps library lists every app, with Profile and Settings.
            driver.wait(label="Apps", role="text")
            for label in ("Lumi", "Habits", "Practice", "Lists", "Diary", "Profile", "Settings"):
                assert driver.find(label=label, role="button", visible=True), \
                    f"{profile.name}: Apps omitted {label}\n" + driver.text()
            # Opening the first app completes setup; the library itself does
            # not require a separate Next button or overwrite preferences.
            # Practice is the third favorite in the sidebar.
            driver.press(key=in_navigation("Practice")["key"])
            deadline = time.monotonic() + 5
            while settings(profile).get("apps_setup_done") != "1":
                assert time.monotonic() < deadline, "Apps setup did not complete\n" + log.read_text()
                time.sleep(.05)
            saved = settings(profile)
            assert saved["enabled_apps"] == "22", "Startup changed saved app preferences"
            order = [int(saved[f"launcher_favorite_{i}"]) for i in range(int(saved["launcher_favorite_count"]))]
            assert order == [12, 1, 2], "Defaults are not Lumi, Habits and Practice: " + str(order)
            wait_log(log, "->0", "Practices click was ignored")
            # Diary is not installed; its card below the divider installs and
            # opens it. Apps sits in the sidebar's bottom corner.
            apps = in_navigation("Apps")
            screen = next(node for node in driver.tree() if node["kind"] == "screen")
            assert apps["y"] - screen["y"] > 720 - 120, f"Apps left the sidebar's bottom corner: {apps}"
            driver.press(key=apps["key"])
            driver.wait(label="Pinned")
            driver.press(label="Diary", role="button")
            wait_log(log, "screen=0->22", "Diary click was ignored")
            driver.wait(label="Diary", role="title_bar")
            selected = settings(profile)
            assert selected["enabled_apps"] == "30", "Opening Diary changed unrelated app choices"
            receipts[profile.name] = dict(selection=int(selected["enabled_apps"]), order=order)
        with application(profile, profile.name + "-restart", *args):
            saved = settings(profile)
            assert saved["enabled_apps"] == "30", "Restart lost the explicit Diary choice"
            restored = [int(saved[f"launcher_favorite_{i}"]) for i in range(int(saved["launcher_favorite_count"]))]
            assert restored == order, "Restart lost a selected app: " + str(restored)

    # Preview windows used to discard the close dialog result forever. The
    # prompt must also appear and work above the Apps overlay.
    for scene in ("close_prompt", "close_prompt_over_apps"):
        with application(Path(temporary) / (scene + "-escape"), "escape-" + scene, "--screenshot",
                         str(Path(temporary) / (scene + "-escape.png")), "--screenshot-scene", scene,
                         "--screenshot-width", "900", "--screenshot-height", "720",
                         preview=True) as (app, window, log):
            driver.wait(contains="keep Inner Breeze running")
            command("xdotool", "windowfocus", window)
            command("xdotool", "keydown", "Escape")
            time.sleep(.12)
            command("xdotool", "keyup", "Escape")
            deadline = time.monotonic() + 5
            while driver.find(contains="keep Inner Breeze running", visible=True):
                assert time.monotonic() < deadline, "Escape did not dismiss the close prompt\n" + driver.text()
                time.sleep(.05)
            assert app.poll() is None, "Escape quit the app behind the close prompt"
            if scene == "close_prompt_over_apps":
                driver.wait(label="Pinned")
            receipts[scene + "_escape"] = "dismissed without quitting"
        with application(Path(temporary) / scene, "quit-" + scene, "--screenshot",
                         str(Path(temporary) / (scene + ".png")), "--screenshot-scene", scene,
                         "--screenshot-width", "900", "--screenshot-height", "720",
                         preview=True) as (app, window, log):
            driver.wait(contains="keep Inner Breeze running")
            if scene == "close_prompt_over_apps":
                assert driver.find(label="Pinned", visible=True), "The Apps overlay is not open"
            quit_button = driver.wait(label="Quit", role="button")
            started = time.monotonic()
            try:
                pressed = driver.press(label="Quit", role="button")
            except UiDriverError:
                # The app may exit before it answers the press.
                assert app.poll() is not None, "Pressing Quit failed\n" + log.read_text()
            else:
                assert pressed["hit"] == quit_button["index"], \
                    f"{scene}: the press reached widget {pressed['hit']}, not Quit, so the prompt is covered"
            try:
                status = app.wait(timeout=1)
            except subprocess.TimeoutExpired:
                raise AssertionError(scene + ": a single Quit click did not exit promptly\n" + log.read_text())
            assert status == 0, log.read_text()
            receipts[scene + "_quit_seconds"] = round(time.monotonic() - started, 3)
    (OUTPUT / "receipt.json").write_text(json.dumps(receipts, indent=2) + "\n")
    print(json.dumps(receipts))
