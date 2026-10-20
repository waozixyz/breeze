"""Scroll archived chat and open Profile's Telegram page on an owned private display.

The app is driven through Kryon's test driver: it reports its widget tree and
takes wheel turns and presses through its own input path.
"""
import ast
import contextlib
import json
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
OUTPUT = ROOT / "build/lumi-history-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
DISPLAY_KEYS = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS")
assert all(not os.environ.get(key) for key in DISPLAY_KEYS), "Inherited desktop environment"
BINARY = Path(sys.argv[1]).resolve()


def release_announced(db, user):
    """This version's release notes count as already shared, so Lumi adds no
    update message to the chat under test."""
    version = re.search(r'VersionString :: "([^"]+)"', (ROOT / "src/core/version.zi").read_text())[1]
    db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
               "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value",
               (user, "lumi_release_announced", version))


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


with tempfile.TemporaryDirectory(prefix="inbe-chat-history-") as directory, contextlib.ExitStack() as stack:
    profile = Path(directory)
    driver = UiDriver(OUTPUT / "driver")
    env = {key: value for key, value in os.environ.items() if key not in DISPLAY_KEYS}
    env.update(driver.environment())
    env.update(APP_DATA_ROOT=str(profile), HOME=directory, XDG_CONFIG_HOME=directory,
               APP_NO_TRAY="1", SDL_AUDIODRIVER="dummy", SDL_VIDEODRIVER="x11",
               LIBGL_ALWAYS_SOFTWARE="1", YUE_DESKTOP_RECOVERY="0")
    display_log = stack.enter_context((OUTPUT / "display.log").open("w"))
    display = subprocess.Popen(["Xvfb", "-displayfd", "1", "-screen", "0", "1280x900x24",
                                "-nolisten", "tcp"], env=env, stdout=subprocess.PIPE, stderr=display_log)
    stack.callback(stop, display)
    number = display.stdout.readline().decode().strip()
    assert number.isdecimal()
    display.stdout.close()
    env["DISPLAY"] = ":" + number

    def command(*args):
        return subprocess.run(args, env=env, check=True, capture_output=True,
                              text=True, timeout=20).stdout.strip()

    @contextlib.contextmanager
    def application(label):
        log_path = OUTPUT / (label + ".log")
        with log_path.open("w") as log:
            app = subprocess.Popen([str(BINARY), "--bundle", str(ROOT / "build/inbe-full.zib")],
                                   cwd=ROOT, env=env, stdout=log, stderr=log)
            driver.attach(app, log_path)
            try:
                deadline = time.monotonic() + 20
                while True:
                    assert app.poll() is None, "Owned test app exited"
                    result = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                                            env=env, capture_output=True, text=True, timeout=3)
                    if result.returncode == 0 and (profile / "inbe.db").exists():
                        window = result.stdout.splitlines()[0]
                        break
                    assert time.monotonic() < deadline, "Owned app window did not appear"
                    time.sleep(.1)
                command("xdotool", "windowsize", window, "900", "720")
                driver.wait(role="screen")
                driver.wait_idle(frames=3)
                yield window
                assert app.poll() is None, "Chat crashed"
            finally:
                stop(app)

    def state(window):
        prop = command("xprop", "-id", window, "_HARMONY_APP_STATE")
        return json.loads(ast.literal_eval(prop.split(" = ", 1)[1]))

    def action(window, view):
        request = "history-" + view
        command("xprop", "-id", window, "-f", "_HARMONY_APP_ACTION", "8s", "-set",
                "_HARMONY_APP_ACTION", json.dumps(dict(control="mcp.open_view", request_id=request,
                                                        arguments={"view": view})))
        deadline = time.monotonic() + 10
        while state(window)["last_request_id"] != request:
            assert time.monotonic() < deadline, "View did not open"
            time.sleep(.1)
        assert state(window)["last_request_ok"]
        driver.wait_idle(frames=3)

    def history_numbers():
        """The numbers of the archived messages the chat shows."""
        return [int(match.group(1)) for label in driver.labels()
                if (match := re.fullmatch(r"History message (\d{3})", label))]

    def wait_screen_width(width):
        deadline = time.monotonic() + 5
        while driver.wait(role="screen", visible=None)["width"] != width:
            assert time.monotonic() < deadline, f"The window did not become {width} wide"
            time.sleep(.05)
        driver.wait_idle(frames=3)

    with application("initialize"):
        pass
    with sqlite3.connect(profile / "inbe.db") as db:
        user = db.execute("SELECT id FROM users LIMIT 1").fetchone()[0]
        settings = dict(enabled_apps="31", main_tab="4", language="en", language_setup_done="1",
                        apps_setup_done="1", launcher_guide_seen="1", lumi_introduced="1", tutorial_seen="1",
                        package_updates_allowed="0", lumi_archive_migrated="1", lumi_guides_seen="127",
                        # Switched offline, Lumi opens on its chat rather than its terms.
                        lumi_online="0")
        settings.update({"app_used_" + name: "1" for name in ("lumi", "habits", "lists", "diary", "practices")})
        for key, value in settings.items():
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                       "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user, key, value))
        release_announced(db, user)
        for index in range(1, 141):
            value = json.dumps(dict(time=index, user=1, kind=0, payload="",
                                   text=f"History message {index:03}"))
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1)",
                       (user, f"cell.lumi.message.test-{index:03}", value))

    with application("history") as window:
        action(window, "lumi")
        driver.wait(label="History message 140")
        latest = driver.text()
        assert not re.search(r"\bOlder\b|\bNewer\b|Chat on Telegram", latest), latest
        chat_area = driver.wait(key=300100)  # Lumi's chat, from apps/lumi/lumi_view.zi.
        x, y = UiDriver.center(chat_area)
        earliest = min(history_numbers())
        for batch in range(20):
            driver.pointer(x, y, wheel=40)
            driver.wait_idle(frames=2, timeout=2)
            earliest = min(earliest, *history_numbers())
            if earliest == 1:
                break
        driver.release_pointer()
        assert earliest == 1, ("Could not scroll through both older batches", earliest)
        with sqlite3.connect(profile / "inbe.db") as db:
            assert db.execute("SELECT COUNT(*) FROM settings WHERE key LIKE 'cell.lumi.message.test-%'").fetchone()[0] == 140
        # Telegram lives in Profile: Apps, Profile, then its Telegram card.
        driver.press(label="Apps", role="button")
        driver.press(label="Profile", role="button")
        driver.wait(label="No account connected")
        page = driver.wait(role="scroll")
        x, y = UiDriver.center(page)
        for _ in range(10):
            driver.pointer(x, y, wheel=-1)
        driver.release_pointer()
        # The shared Self profile lists Telegram among Inner Breeze's extensions.
        driver.press(label="Telegram")
        driver.wait(contains="Connect your sync account first")
        driver.wait(contains="Telegram input", role="title_bar")
        normalized = " ".join(driver.text().split())
        assert "Telegram input" in normalized and "Connect your sync account first" in normalized, normalized
        command("xdotool", "windowsize", window, "390", "720")
        wait_screen_width(390)
        text = driver.text()
        assert "Connect your sync account first" in " ".join(text.split()), text
    (OUTPUT / "result.json").write_text(json.dumps(dict(passed=True, archived=140, earliest_visible=earliest)) + "\n")
print("Scrolling to the oldest archived message and Profile's Telegram page passed")
