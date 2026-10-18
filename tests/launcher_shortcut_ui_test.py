"""Pin a real app and launch its desktop entry, using only a private display."""
import contextlib
import os
from pathlib import Path
import sqlite3
import signal
import subprocess
import sys
import tempfile
import time

from PIL import Image
from ui_driver import UiDriver

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/launcher-shortcut-ui-test"
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


def wait(predicate, description, timeout=30):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        value = predicate()
        if value:
            return value
        time.sleep(.05)
    raise AssertionError(description)


with contextlib.ExitStack() as stack:
    temporary = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="inbe pin % ")))
    profile = temporary / "profile"
    profile.mkdir()
    data = temporary / "share"
    data.mkdir()
    env = {key: value for key, value in os.environ.items() if key not in DESKTOP_ENV}
    env.pop("HARMONY_DATA_ROOT", None)
    env.pop("INBE_DIARY_IMPORT", None)
    env.pop("INBE_NODE_APP_FILE", None)
    env.update(YUE_DESKTOP_RECOVERY="0", APP_NO_TRAY="1", SDL_AUDIODRIVER="dummy",
               APP_DATA_ROOT=str(profile), XDG_DATA_HOME=str(data), INBE_DEBUG_ROUTE="1")
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
                subprocess.run(["xdotool", "windowsize", owned_window, "1100", "900"],
                               env=env, check=True, capture_output=True)
                wait(lambda: (profile / "inbe.db").exists(), "Database was not created")
                wait(lambda: driver.tree(), "App did not draw")
                yield owned_window
                assert app.poll() is None, log_path.read_text()[-4000:]
            finally:
                stop(app)

    with application("initialize"):
        pass
    with sqlite3.connect(profile / "inbe.db") as db:
        user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
        settings = dict(language="en", language_system=0, language_setup_done=1,
                        apps_setup_done=1, enabled_apps=63, lumi_introduced=1,
                        tutorial_seen=1, habits_guide_seen=1, launcher_guide_seen=1,
                        lumi_guides_seen=127, main_tab=3, package_updates_allowed=0,
                        apps_last_update_check=1900000000)
        for name in ("lists", "habits", "practices", "diary", "lumi", "leaderboard"):
            settings["app_used_" + name] = 1
        for key, value in settings.items():
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                       "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user, key, str(value)))

    with application("pin") as window:
        driver.press(label="Apps", role="button")
        driver.wait(label="Pin to launcher", role="button")
        # Match each pin to its app card by geometry, so identical action labels
        # do not accidentally test a different installed app.
        cards = driver.find(label="Diary", role="button")
        card = next(node for node in cards if node["width"] > 100)
        pins = driver.find(label="Pin to launcher", role="button")
        pin = next(node for node in pins if abs(node["x"] - card["x"]) < 1 and
                   0 < node["y"] - card["y"] < card["height"] + 10)
        driver.press(key=pin["key"], label="Pin to launcher")
        driver.wait(label="Added to your launcher.", role="text")
        entry = data / "applications/xyz.waozi.inbe.diary.desktop"
        assert entry.is_file()
        subprocess.run(["desktop-file-validate", str(entry)], check=True, capture_output=True)
        text = entry.read_text()
        assert "Name=Diary\n" in text and "--app diary\n" in text
        icon_path = Path(next(line[5:] for line in text.splitlines() if line.startswith("Icon=")))
        with Image.open(icon_path) as icon:
            assert icon.size == (128, 128) and icon.convert("RGB").getextrema()[0][0] < 100
        driver.press(key=pin["key"], label="Pin to launcher")
        assert len(list((data / "applications").glob("*.desktop"))) == 1
        subprocess.run(["import", "-window", window, str(OUTPUT / "apps.png")],
                       env=env, check=True, capture_output=True)

    # Ask the desktop's actual entry parser to launch it. Remove the inherited
    # profile so only the escaped Exec assignment can select our existing data.
    entry_env = env.copy()
    entry_env.pop("APP_DATA_ROOT")
    with (OUTPUT / "desktop-entry.log").open("w") as log:
        subprocess.run(["gio", "launch", str(entry)], env=entry_env, check=True,
                       stdout=log, stderr=subprocess.STDOUT, timeout=10)

        def launched_window():
            result = subprocess.run(["xdotool", "search", "--onlyvisible", "--class",
                                     "xyz.waozi.inbe.diary"], env=env,
                                    capture_output=True, text=True, timeout=5)
            return result.stdout.splitlines()[0] if result.returncode == 0 else None

        window = wait(launched_window, "The installed desktop entry did not open Diary")
        result = subprocess.run(["xdotool", "getwindowpid", window], env=env,
                                check=True, capture_output=True, text=True)
        pid = int(result.stdout.strip())
        assert Path(f"/proc/{pid}/exe").resolve() == BINARY, "Launcher opened an unrelated process"
        try:
            # The process's own environment must name the disposable profile,
            # including its space and percent characters, exactly.
            process_env = Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
            assert os.fsencode("APP_DATA_ROOT=" + str(profile)) in process_env
        finally:
            os.kill(pid, signal.SIGTERM)
            try:
                wait(lambda: not Path(f"/proc/{pid}/exe").exists(), "Pinned Diary did not stop", timeout=5)
            except AssertionError:
                assert Path(f"/proc/{pid}/exe").resolve() == BINARY
                os.kill(pid, signal.SIGKILL)
                wait(lambda: not Path(f"/proc/{pid}/exe").exists(), "Pinned Diary did not stop", timeout=5)

    for name, title in (("diary", "Diary"), ("lists", "Lists"), ("habits", "Habits"),
                        ("practices", "Practice"), ("lumi", "Lumi"), ("leaderboard", "Leaderboard")):
        with application("launch-" + name, "--app", name) as window:
            def opened():
                result = subprocess.run(["xdotool", "getwindowname", window], env=env,
                                        capture_output=True, text=True, timeout=5)
                return result.stdout.strip() == title
            wait(opened, "Named app did not open: " + name)
            assert not driver.find(label="Apps", role="button"), "Harness navigation is still visible"
            identity = subprocess.run(["xprop", "-id", window, "WM_CLASS"], env=env,
                                      check=True, capture_output=True, text=True).stdout
            assert "xyz.waozi.inbe." + name in identity, identity
            if name == "diary":
                driver.wait_idle(frames=5)
                assert "Could not read this entry" not in driver.text(), driver.text()
                subprocess.run(["import", "-window", window, str(OUTPUT / "diary.png")],
                               env=env, check=True, capture_output=True)

    node_bundle = ROOT / "build/node-apps/chess.zib"
    assert node_bundle.is_file(), "Run make node-apps before this check"
    env["INBE_NODE_APP_FILE"] = str(node_bundle)
    with application("install-node-app"):
        driver.press(label="Apps", role="button")
        def chess_card():
            return next((node for node in driver.find(role="button")
                         if node["label"].lower() == "chess" and node["width"] > 100), None)
        card = wait(chess_card, "The locally offered Chess package did not appear")
        driver.press(key=card["key"], label=card["label"])
        driver.wait(label="Apps", role="button")
        driver.press(label="Apps", role="button")
        card = wait(chess_card, "The installed Chess package did not appear")
        pin = next(node for node in driver.find(label="Pin to launcher", role="button")
                   if abs(node["x"] - card["x"]) < 1 and
                   0 < node["y"] - card["y"] < card["height"] + 10)
        node_title = card["label"]
        driver.press(key=pin["key"], label="Pin to launcher")
        driver.wait(label="Added to your launcher.", role="text")
        entry = data / "applications/xyz.waozi.inbe.chess.desktop"
        assert "--app chess\n" in entry.read_text()

    # A shortcut names the package, rather than its transient slot number.
    with sqlite3.connect(profile / "inbe.db") as db:
        db.execute("UPDATE settings SET value='' WHERE user_id=? AND key='node_app_slot_0'", (user,))
        db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?, 'node_app_slot_3', 'chess',1) "
                   "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user,))
    with application("launch-node-after-slot-change", "--app", "chess") as window:
        def node_opened():
            result = subprocess.run(["xdotool", "getwindowname", window], env=env,
                                    capture_output=True, text=True, timeout=5)
            return result.stdout.strip() == node_title
        wait(node_opened, "The pinned node app did not follow its new slot")
        assert not driver.find(label="Apps", role="button"), "Harness navigation is still visible"

print("Launcher pin, icon, duplicate prevention, desktop entry, profile, six bundled apps and relocated node app passed")
