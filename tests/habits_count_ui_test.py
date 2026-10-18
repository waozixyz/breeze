"""A counting habit's count dialog, drawn by the Habits package.

Run by habits_count_ui_test.sh on its own Xvfb display. Screenshot mode
seeds a temporary database with a habit counted three times today out of a
target of three and opens its count dialog; the test drives it through
Kryon's test driver: the steps count the day down and up, Close and Done
close it, and a habit that asks questions opens its day from Entries.
"""

import contextlib
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

from ui_driver import UiDriver

assert os.environ.get("INBE_UI_TEST_XVFB") == "1", "Run tests/habits_count_ui_test.sh"
assert not os.environ.get("WAYLAND_DISPLAY") and not os.environ.get("DBUS_SESSION_BUS_ADDRESS")
BINARY = sys.argv[1]
ROOT = Path(__file__).resolve().parents[1]
TEST_DIR = ROOT / "build/habits-count-ui-test"
TEST_DIR.mkdir(parents=True, exist_ok=True)
# The dialog's buttons, fixed by apps/habits/habits_view.zi.
MINUS, PLUS, SESSIONS, DONE, ENTRIES = 5720000, 5720001, 5720002, 5720003, 5720004


class Failure(AssertionError):
    pass


def expect(actual, expected, message):
    if actual != expected:
        raise Failure(f"FAIL {message}: got {actual!r}, expected {expected!r} ({TEST_DIR})")


@contextlib.contextmanager
def scene(name):
    """The app showing one screenshot scene, with its driver and database."""
    driver = UiDriver(TEST_DIR / ("driver-" + name))
    with contextlib.ExitStack() as stack:
        temporary = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="inbe-habits-count-")))
        log_path = TEST_DIR / (name + ".log")
        log = stack.enter_context(log_path.open("w"))
        # The scene's own capture goes to the temporary folder and is removed
        # with it; the window stays open for the test.
        app = subprocess.Popen(
            [BINARY, "--screenshot", str(temporary / "start.png"),
             "--screenshot-scene", name, "--screenshot-width", "411",
             "--screenshot-height", "760"],
            env=os.environ | {"APP_SHOT_WINDOW": "1"} | driver.environment(),
            stdout=log, stderr=subprocess.STDOUT)
        database = Path(f"/tmp/inbe-screenshot-{app.pid}/inbe.db")

        def cleanup():
            if app.poll() is None:
                app.terminate()
            try:
                app.wait(timeout=5)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=5)
            shutil.rmtree(database.parent, ignore_errors=True)
        stack.callback(cleanup)
        driver.attach(app, log_path)
        yield driver, database


def sql(database, query):
    # Read-only, so closing it never checkpoints the running app's WAL.
    uri = database.as_uri() + "?mode=ro"
    with contextlib.closing(sqlite3.connect(uri, uri=True, timeout=2)) as db:
        row = db.execute(query).fetchone()
        return "" if row is None or row[0] is None else str(row[0])


def counted_habit(database):
    """The third habit, which the scenes count."""
    return sql(database, "SELECT name FROM habits WHERE deleted_at=0 "
                         "ORDER BY sort_order LIMIT 1 OFFSET 2")


def overlaps(node, other):
    return node["x"] < other["x"] + other["width"] and other["x"] < node["x"] + node["width"]


def shown_count(driver):
    """The large count between the dialog's day and its target."""
    target = driver.wait(contains="Daily target")
    tree = driver.tree()
    days = [node for node in tree if node["visible"] and node["kind"] == "text"
            and node["label"] == "Today" and node["y"] < target["y"] and overlaps(node, target)]
    if not days:
        raise Failure(f"FAIL the dialog shows no day ({TEST_DIR})")
    day = max(days, key=lambda node: node["y"])
    numbers = [node for node in tree
               if node["visible"] and node["kind"] == "text" and node["label"].isdigit()
               and day["y"] < node["y"] < target["y"] and overlaps(node, target)]
    if len(numbers) != 1:
        raise Failure(f"FAIL the dialog shows {len(numbers)} counts ({TEST_DIR})")
    return int(numbers[0]["label"])


def wait_count(driver, value, message):
    deadline = time.monotonic() + 10
    while shown_count(driver) != value:
        if time.monotonic() >= deadline:
            expect(shown_count(driver), value, message)
        time.sleep(0.05)


with scene("habit_count_dialog") as (driver, database):
    driver.wait(key=DONE)
    name = counted_habit(database)
    driver.wait(label=name)
    expect(driver.wait(contains="Daily target")["label"], "Daily target  3", "target text")
    expect(shown_count(driver), 3, "count before stepping")
    # Without questions or linked sessions there are no Entries or sessions.
    expect(driver.find(key=ENTRIES, visible=True), [], "Entries without questions")
    expect(driver.find(key=SESSIONS, visible=True), [], "sessions without linked practice")

    driver.press(key=PLUS)
    wait_count(driver, 4, "count after plus")
    driver.press(key=MINUS)
    wait_count(driver, 3, "count after a minus")
    driver.press(key=MINUS)
    wait_count(driver, 2, "count after two minuses")

    driver.press(label="Close")
    driver.wait_gone(key=DONE)
    expect(driver.find(contains="Daily target", visible=True), [], "dialog after Close")
print("PASS the count dialog steps the day's count and closes")

with scene("habit_count_questions") as (driver, database):
    driver.wait(key=ENTRIES)
    driver.wait(label="Entries")
    driver.press(key=DONE)
    driver.wait_gone(key=DONE)
print("PASS Done closes the dialog of a habit that asks questions")

with scene("habit_count_questions") as (driver, database):
    driver.press(key=ENTRIES)
    driver.wait_gone(key=DONE)
    driver.wait_gone(contains="Daily target")
    # The day's page closes with its title bar's Close.
    driver.wait(label="Close", role="button")
print("PASS Entries opens the day of a habit that asks questions")
