"""A habit's day screen and its entry dialog, drawn by the Habits package.

Run by habit_day_ui_test.sh on its own Xvfb display. Screenshot mode seeds a
temporary database: a habit that asks four questions about a meal, one that
measures a fasting window with a span running, and a habit linked to Wim Hof
sessions of three rounds a day. The test drives the screens through Kryon's
test driver: the entry dialog types an answer and saves it, a day's entries
open, delete and are added without answers, a running span ends, and a
session's rounds are changed and deleted.
"""

import contextlib
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile

from ui_driver import UiDriver

assert os.environ.get("INBE_UI_TEST_XVFB") == "1", "Run tests/habit_day_ui_test.sh"
assert not os.environ.get("WAYLAND_DISPLAY") and not os.environ.get("DBUS_SESSION_BUS_ADDRESS")
BINARY = sys.argv[1]
ROOT = Path(__file__).resolve().parents[1]
TEST_DIR = ROOT / "build/habit-day-ui-test"
TEST_DIR.mkdir(parents=True, exist_ok=True)
# The buttons' keys, fixed by apps/habits/habit_day_view.zi.
DELETE_ENTRY, SAVE_ENTRY, DONE, SKIP = 5730001, 5730002, 5730003, 5730004
EDIT_FIRST, DELETE_FIRST, END_SPAN, ADD_ENTRY = 5740000, 5740001, 5739990, 5739991
ROUND_EDIT = 5760000


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
        temporary = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="inbe-habit-day-")))
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


def entries(database, habit, extra=""):
    return int(sql(database, "SELECT COUNT(*) FROM habit_entries WHERE deleted_at=0 AND "
                             f"habit_id=(SELECT id FROM habits WHERE name='{habit}' AND deleted_at=0)"
                             + extra) or 0)


def wait_for(driver, predicate, message):
    for _ in range(200):
        if predicate():
            return
        driver.wait_idle(frames=1)
    raise Failure(f"FAIL {message} ({TEST_DIR})")


def fields(driver):
    """The dialog's typed answers, top to bottom."""
    return sorted((node for node in driver.tree()
                   if node["kind"] == "text_field" and node["visible"]),
                  key=lambda node: node["y"])


with scene("habit_questions_dialog") as (driver, database):
    driver.wait(key=DONE)
    driver.wait(label="First meal")
    before = entries(database, "First meal")
    # The number answer is the first field: change its 2 to 3.
    number = fields(driver)[0]
    expect(number["value"], "2", "the number answer the scene set")
    driver.press(key=number["key"])
    driver.key("end")
    driver.key("backspace")
    driver.type("3")
    wait_for(driver, lambda: fields(driver)[0]["value"] == "3", "the typed number")
    expect(fields(driver)[1]["value"], "Oatmeal with berries", "the text answer")
    driver.press(key=DONE)
    driver.wait_gone(key=DONE)
    wait_for(driver, lambda: entries(database, "First meal") == before + 1, "Done saved the entry")
    answers = sql(database, "SELECT answers FROM habit_entries WHERE deleted_at=0 AND "
                            "habit_id=(SELECT id FROM habits WHERE name='First meal') "
                            "ORDER BY updated_at DESC LIMIT 1")
    for value in ('"3"', "Oatmeal with berries", '"yes"'):
        if value not in answers:
            raise Failure(f"FAIL the saved answers lack {value}: {answers} ({TEST_DIR})")
print("PASS the entry dialog types an answer and Done saves the entry")

with scene("habit_day_entries") as (driver, database):
    driver.wait(label="Entries")
    driver.wait(key=EDIT_FIRST)
    driver.press(key=EDIT_FIRST)
    driver.wait(key=SAVE_ENTRY)
    driver.press(label="Cancel")
    driver.wait_gone(key=SAVE_ENTRY)
    before = entries(database, "First meal")
    driver.press(key=DELETE_FIRST)
    wait_for(driver, lambda: entries(database, "First meal") == before - 1, "the entry deleted")
    driver.press(key=ADD_ENTRY)
    driver.wait(key=SKIP)
    driver.press(key=SKIP)
    driver.wait_gone(key=SKIP)
    wait_for(driver, lambda: entries(database, "First meal") == before, "Skip recorded an entry")
    driver.press(label="Close", role="button")
    driver.wait_gone(label="Entries")
print("PASS a day's entries open, delete, and are added without answers")

with scene("habit_span_day") as (driver, database):
    driver.wait(key=END_SPAN)
    running = " AND ended_at=0"
    expect(entries(database, "Fasting window", running), 1, "the span running")
    driver.press(key=END_SPAN)
    wait_for(driver, lambda: entries(database, "Fasting window", running) == 0, "the span ended")
    driver.wait_gone(key=END_SPAN)
print("PASS End now ends a running span")

with scene("habit_session_day") as (driver, database):
    driver.wait(label="Round 3")
    driver.press(key=ROUND_EDIT)
    driver.key("backspace")
    driver.key("backspace")
    driver.key("backspace")
    driver.type("99")
    driver.key("enter")
    driver.wait(label="99s")
    # Each round's delete button follows its edit button.
    driver.press(key=ROUND_EDIT + 2 * 2 + 1)
    driver.wait_gone(label="Round 3")
    driver.wait(label="Round 2")
    driver.wait(label="99s")
print("PASS a session's round is changed with the keyboard and another deleted")
