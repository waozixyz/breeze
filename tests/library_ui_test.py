#!/usr/bin/env python3
"""Exercise Library's actual package with a disposable profile and private Xvfb.
Book covers, gestures, reflow, resume and annotations use Kryon's widget tree.
Optional captures verify the private X server and the app window first."""
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import time

from ui_driver import UiDriver
from library_reader_cases import LibraryReaderCases

assert int(os.environ.get("DISPLAY", ":0").split(":")[-1].split(".")[0]) >= 300
ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(sys.argv[1]).resolve()
PACKAGE = Path(sys.argv[2]).resolve()
OUTPUT = ROOT / "build/library-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
WIDTH, HEIGHT = int(os.environ.get("INBE_LIBRARY_TEST_WIDTH", "390")), 844
driver = UiDriver(OUTPUT / "driver")


def command(*args):
    return subprocess.check_output(args, text=True, timeout=10).strip()


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def launch(profile, name):
    log_path = OUTPUT / (name + ".log")
    log = log_path.open("w")
    app = subprocess.Popen([str(BINARY)], cwd=ROOT,
                           env=os.environ | {"APP_DATA_ROOT": str(profile), "INBE_NODE_APP_FILE": str(PACKAGE)} |
                           driver.environment(),
                           stdout=log, stderr=subprocess.STDOUT)
    driver.attach(app, log_path)
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        assert app.poll() is None, log_path.read_text()
        found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                               capture_output=True, text=True)
        if found.returncode == 0 and (profile / "inbe.db").exists():
            window = found.stdout.splitlines()[0]
            command("xdotool", "windowsize", window, str(WIDTH), str(HEIGHT))
            command("xdotool", "windowmove", window, "0", "0")
            driver.wait_idle(frames=3)
            return app, window
        time.sleep(0.1)
    stop(app)
    raise AssertionError("Inbe did not map its window")


def chapter_text(number):
    source = (ROOT / "apps/library/tao_te_ching.zi").read_text()
    return re.search(rf"^TAO_{number} :: #string END\n(.*?)\nEND;$", source, re.M | re.S)[1]


def capture(name):
    destination = os.environ.get("BREEZE_LIBRARY_CAPTURE")
    if not destination:
        return
    if name == "opening":
        driver.wait(key=27800, timeout=2)
        time.sleep(.06)
    display = os.environ["DISPLAY"].split(".")[0]
    servers = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            args = (entry / "cmdline").read_bytes().split(b"\0")
            executable = (entry / "exe").resolve(strict=True)
            if executable.name == "Xvfb" and display.encode() in args:
                servers.append((entry.name, [arg.decode() for arg in args if arg]))
        except (OSError, ValueError):
            continue
    assert len(servers) == 1, ("Private Xvfb source could not be verified", display, servers)
    assert command("xdotool", "getwindowpid", window) == str(app.pid)
    output = Path(destination)
    output.mkdir(parents=True, exist_ok=True)
    (output / "capture-source.txt").write_text(repr((display, servers, app.pid, window)) + "\n")
    subprocess.run(["import", "-window", window, str(output / (name + ".png"))], check=True)


with tempfile.TemporaryDirectory(prefix="inbe-library-") as directory:
    profile = Path(directory)
    app, _ = launch(profile, "first-start")
    stop(app)
    with sqlite3.connect(profile / "inbe.db") as db:
        user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
        seeded = {"language": "en", "language_system": 0, "language_setup_done": 1, "apps_setup_done": 1,
                  "tutorial_seen": 1, "habits_guide_seen": 1, "lumi_guides_seen": 127, "launcher_guide_seen": 1,
                  "package_updates_allowed": 0, "apps_last_update_check": 1900000000,
                  "node_apps_checked_at": int(time.time())}
        for key, value in seeded.items():
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                       "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user, key, str(value)))
    app, window = launch(profile, "reading")
    cases = LibraryReaderCases(driver, chapter_text, lambda: (OUTPUT / "reading.log").read_text(), capture)
    try:
        saved = cases.exercise()
    finally:
        stop(app)
    app, window = launch(profile, "continue")
    try:
        cases.resume(saved)
    finally:
        stop(app)
print("Library bookshelf, swipe and arrow pages, contents, font reflow, resume and annotations persist after restart")
