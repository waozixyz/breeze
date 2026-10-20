#!/usr/bin/env python3
"""Library from More apps on a private display: the shelf starts the Tao Te
Ching at its first chapter, the chapter buttons turn pages, the contents open
any chapter, and after a restart the shelf continues where reading stopped.

The node's offer comes from a local package (INBE_NODE_APP_FILE), so nothing
is downloaded or published. Buttons and text are found in the app's widget
tree through Kryon's test driver.
"""
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import time

from ui_driver import UiDriver

assert int(os.environ.get("DISPLAY", ":0").split(":")[-1].split(".")[0]) >= 300
ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(sys.argv[1]).resolve()
PACKAGE = Path(sys.argv[2]).resolve()
OUTPUT = ROOT / "build/library-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
WIDTH, HEIGHT = 390, 844
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
    """Chapter number's words, as the bundle's book source holds them."""
    source = (ROOT / "apps/library/tao_te_ching.zi").read_text()
    return re.search(rf"^TAO_{number} :: #string END\n(.*?)\nEND;$", source, re.M | re.S)[1]


def first_line(number):
    return chapter_text(number).splitlines()[0]


def shown(number):
    driver.wait(label=f"Chapter {number}")
    driver.wait(contains=first_line(number))


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
    try:
        driver.press(label="Apps", role="button")
        # More apps offers Library because the node (here, the local file) does.
        driver.press(label="Library", role="button")
        driver.wait(label="Tao Te Ching")
        driver.press(label="Start reading", role="button")
        shown(1)
        driver.press(label="Next chapter", role="button")
        shown(2)
        driver.press(label="Previous chapter", role="button")
        shown(1)
        driver.wait_idle(frames=3)
        previous = driver.find(label="Previous chapter", role="button")
        assert len(previous) == 1 and not previous[0]["enabled"], \
            ("the first chapter offers a previous one", previous)
        # Back leaves the chapter for the contents, then the shelf.
        command("xdotool", "windowfocus", window)
        command("xdotool", "key", "Escape")
        driver.press(label="3", role="button")
        shown(3)
    finally:
        stop(app)
    app, window = launch(profile, "continue")
    try:
        driver.press(label="Apps", role="button")
        driver.press(label="Library", role="button")
        driver.press(label="Continue at chapter 3", role="button")
        shown(3)
    finally:
        stop(app)
print("Library: start, turn pages both ways, open a chapter from the contents and continue after a restart passed")
