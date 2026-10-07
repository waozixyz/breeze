"""Scroll archived chat and open Telegram settings on an owned private display."""
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

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/lumi-history-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
DISPLAY_KEYS = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS")
assert all(not os.environ.get(key) for key in DISPLAY_KEYS), "Inherited desktop environment"
BINARY = Path(sys.argv[1]).resolve()


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
    env = {key: value for key, value in os.environ.items() if key not in DISPLAY_KEYS}
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
        with (OUTPUT / (label + ".log")).open("w") as log:
            app = subprocess.Popen([str(BINARY), "--bundle", str(ROOT / "build/inbe-full.zib")],
                                   cwd=ROOT, env=env, stdout=log, stderr=log)
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
                time.sleep(.8)
                yield window
                assert app.poll() is None, "Chat crashed"
            finally:
                stop(app)

    def capture(window, label):
        path = OUTPUT / (label + ".png")
        command("import", "-window", window, str(path))
        text = command("tesseract", str(path), "stdout", "-l", "eng", "--psm", "6")
        (OUTPUT / (label + ".txt")).write_text(text)
        return text

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
        time.sleep(.5)

    with application("initialize"):
        pass
    with sqlite3.connect(profile / "inbe.db") as db:
        user = db.execute("SELECT id FROM users LIMIT 1").fetchone()[0]
        settings = dict(enabled_apps="31", main_tab="4", language="en", language_setup_done="1",
                        apps_setup_done="1", lumi_introduced="1", tutorial_seen="1",
                        cells_auto_update="0", lumi_archive_migrated="1")
        settings.update({"app_used_" + name: "1" for name in ("lumi", "habits", "lists", "diary", "practices")})
        for key, value in settings.items():
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                       "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user, key, value))
        for index in range(1, 141):
            value = json.dumps(dict(time=index, user=1, kind=0, payload="",
                                   text=f"History message {index:03}"))
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1)",
                       (user, f"cell.lumi.message.test-{index:03}", value))

    with application("history") as window:
        action(window, "lumi")
        latest = capture(window, "latest")
        assert "140" in latest, latest
        assert not re.search(r"\bOlder\b|\bNewer\b|Chat on Telegram", latest), latest
        command("xdotool", "mousemove", "--window", window, "550", "280")
        earliest = 140
        for batch in range(10):
            command("xdotool", "click", "--repeat", "40", "--delay", "25", "4")
            time.sleep(.3)
            text = capture(window, "scrolled")
            values = [int(value) for value in re.findall(r"History message\s+(\d{1,3})", text)]
            if values:
                earliest = min(earliest, *values)
            if earliest == 1:
                break
        assert earliest == 1, ("Could not scroll through both older batches", earliest)
        with sqlite3.connect(profile / "inbe.db") as db:
            assert db.execute("SELECT COUNT(*) FROM settings WHERE key LIKE 'cell.lumi.message.%'").fetchone()[0] == 140
        action(window, "settings")
        capture(window, "settings")
        command("xdotool", "mousemove", "--window", window, "330", "435")
        command("xdotool", "mousedown", "1")
        time.sleep(.15)
        command("xdotool", "mouseup", "1")
        time.sleep(.5)
        text = capture(window, "telegram")
        normalized = " ".join(text.split())
        assert "Continue your Lumi chat" in normalized and "Connect your sync account first" in normalized, text
        command("xdotool", "windowsize", window, "390", "720")
        time.sleep(.5)
        text = capture(window, "telegram-narrow")
        assert "Connect your sync account first" in " ".join(text.split()), text
    (OUTPUT / "result.json").write_text(json.dumps(dict(passed=True, archived=140, earliest_visible=earliest)) + "\n")
print("Scrolling to the oldest archived message and Telegram settings passed")
