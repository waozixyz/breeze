"""Measure a full Lumi history using only an owned private display/profile."""
import contextlib
import json
import os
from pathlib import Path
import re
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/lumi-performance-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
DISPLAY_KEYS = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS")
assert all(not os.environ.get(key) for key in DISPLAY_KEYS), "Inherited desktop environment"
BINARY = Path(sys.argv[1]).resolve()
LABEL = sys.argv[2]


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


with tempfile.TemporaryDirectory(prefix="inbe-lumi-performance-") as temporary, contextlib.ExitStack() as stack:
    profile = Path(temporary)
    env = {key: value for key, value in os.environ.items() if key not in DISPLAY_KEYS}
    env.update(YUE_DESKTOP_RECOVERY="0", APP_NO_TRAY="1", SDL_AUDIODRIVER="dummy",
               SDL_VIDEODRIVER="x11", LIBGL_ALWAYS_SOFTWARE="1",
               APP_DATA_ROOT=str(profile), APP_PROFILE="1", INBE_DEBUG_ROUTE="1")
    display_log = stack.enter_context((OUTPUT / (LABEL + "-display.log")).open("w"))
    server = subprocess.Popen(["Xvfb", "-displayfd", "1", "-screen", "0", "900x720x24",
                               "-nolisten", "tcp"], env=env, stdout=subprocess.PIPE, stderr=display_log)
    stack.callback(stop, server)
    number = server.stdout.readline().decode().strip()
    server.stdout.close()
    assert number.isdecimal()
    env["DISPLAY"] = ":" + number

    def command(*args):
        return subprocess.check_output(args, env=env, text=True, timeout=5).strip()

    @contextlib.contextmanager
    def application(name):
        log_path = OUTPUT / (LABEL + "-" + name + ".log")
        with log_path.open("w") as log:
            app = subprocess.Popen([str(BINARY)], cwd=ROOT, env=env,
                                   stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 20
                window = ""
                while time.monotonic() < deadline:
                    assert app.poll() is None, log_path.read_text()
                    found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                                           env=env, capture_output=True, text=True, timeout=2)
                    if found.returncode == 0 and found.stdout.strip():
                        window = found.stdout.splitlines()[0]
                        break
                    time.sleep(.1)
                assert window, "Owned test window did not appear"
                command("xdotool", "windowsize", window, "900", "720")
                command("xdotool", "windowfocus", window)
                time.sleep(1)
                yield app, window, log_path
            finally:
                stop(app)

    with application("prepare"):
        pass
    history = [{"user": index % 2, "text": "A longer message about today's habits and practices.\n" * 8}
               for index in range(64)]
    with sqlite3.connect(profile / "inbe.db") as db:
        user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
        values = {"language": "en", "language_system": 0, "language_setup_done": 1,
                  "apps_setup_done": 1, "enabled_apps": 31, "lumi_introduced": 1,
                  "cells_auto_update": 0, "apps_last_update_check": 1900000000,
                  "tutorial_seen": 1, "habits_guide_seen": 1, "ui_scale": 10,
                  "navigation_placement": 1, "navigation_collapsed": 0,
                  "main_tab": 4, "lumi_chat": json.dumps(history)}
        for key, value in values.items():
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                       "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user, key, str(value)))

    samples = []
    with application("history") as (app, window, log_path):
        deadline = time.monotonic() + 28
        while time.monotonic() < deadline:
            assert app.poll() is None, "Lumi exited during sustained rendering"
            command("xdotool", "mousemove", "--window", window, "600", str(300 + len(samples) % 2))
            if len(samples) % 5 == 0:
                command("xdotool", "click", "5" if len(samples) % 10 == 0 else "4")
            status = Path(f"/proc/{app.pid}/status").read_text()
            samples.append(int(re.search(r"VmRSS:\s+(\d+)", status)[1]))
            time.sleep(.2)
        log = log_path.read_text()
        reports = [float(value) for value in re.findall(r"PROFILE: frame avg=([\d.]+)", log)]
        assert len(reports) >= 2, "Lumi did not finish enough frames to measure"
        assert "portable execution failed" not in log and "frame rejected" not in log, log[-2000:]
        initial_memory = statistics.median(samples[20:40])
        final_memory = statistics.median(samples[-20:])
        assert final_memory - initial_memory < 16 * 1024, "Lumi memory keeps growing"
        result = {"history_messages": 64, "frame_ms": statistics.median(reports[1:]),
                  "rss_initial_kib": initial_memory, "rss_final_kib": final_memory,
                  "reports": len(reports), "private_display": True}
        (OUTPUT / (LABEL + ".json")).write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))
