"""Habit creation and a counting habit's dialog, drawn by Habits.

Run by habits_count_ui_test.sh on its own Xvfb display. Screenshot mode
seeds a temporary database with a habit counted three times today out of a
target of three and opens its count dialog; the test drives it through
Kryon's test driver: the steps count the day down and up, Close and Done
close it, and a habit that asks questions opens its day from Entries.
The ordinary New Habit flow also edits and saves details, schedules and
tracking options before a habit exists, at phone and desktop widths.
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
def scene(name, width=411):
    """The app showing one screenshot scene, with its driver and database."""
    label = name + "-" + str(width)
    driver = UiDriver(TEST_DIR / ("driver-" + label))
    with contextlib.ExitStack() as stack:
        temporary = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="inbe-habits-count-")))
        log_path = TEST_DIR / (label + ".log")
        log = stack.enter_context(log_path.open("w"))
        # The scene's own capture goes to the temporary folder and is removed
        # with it; the window stays open for the test.
        app = subprocess.Popen(
            [BINARY, "--screenshot", str(temporary / "start.png"),
             "--screenshot-scene", name, "--screenshot-width", str(width),
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


def in_dialog(tree, node):
    """Whether a widget belongs to the open dialog, not to the habit list
    behind it, whose day circles show counts too."""
    nodes = {other["index"]: other for other in tree}
    while node["parent"] in nodes:
        node = nodes[node["parent"]]
        if node["kind"] == "modal":
            return True
    return False


def shown_count(driver):
    """The large count between the dialog's day and its target."""
    target = driver.wait(contains="Daily target")
    tree = driver.tree()
    days = [node for node in tree if node["visible"] and node["kind"] == "text"
            and node["label"] == "Today" and node["y"] < target["y"] and overlaps(node, target)
            and in_dialog(tree, node)]
    if not days:
        raise Failure(f"FAIL the dialog shows no day ({TEST_DIR})")
    day = max(days, key=lambda node: node["y"])
    numbers = [node for node in tree
               if node["visible"] and node["kind"] == "text" and node["label"].isdigit()
               and day["y"] < node["y"] < target["y"] and overlaps(node, target)
               and in_dialog(tree, node)]
    if len(numbers) != 1:
        raise Failure(f"FAIL the dialog shows {len(numbers)} counts ({TEST_DIR})")
    return int(numbers[0]["label"])


def wait_count(driver, value, message):
    deadline = time.monotonic() + 10
    while shown_count(driver) != value:
        if time.monotonic() >= deadline:
            expect(shown_count(driver), value, message)
        time.sleep(0.05)


def scroll_to(driver, **selector):
    for _ in range(24):
        nodes = driver.find(visible=True, **selector)
        if nodes:
            return nodes[0]
        driver.pointer(200, 450, wheel=-3)
        driver.release_pointer()
        driver.wait_idle(frames=4)
    return driver.wait(**selector)


def reveal(driver, width, **selector):
    """Find a form control after scrolling in either direction."""
    for _ in range(40):
        matches = driver.find(**selector)
        if matches:
            node = matches[0]
            if node["visible"] and 60 <= node["y"] and node["y"] + node["height"] <= 690:
                return node
            direction = 2 if node["y"] < 60 else -2
        else:
            direction = -2
        driver.pointer(width // 2, 450, wheel=direction)
        driver.release_pointer()
        driver.wait_idle(frames=2)
    return driver.wait(**selector)


def wait_selected(driver, selected, **selector):
    deadline = time.monotonic() + 10
    while True:
        nodes = driver.find(**selector)
        if nodes and nodes[0]["selected"] == selected:
            return
        if time.monotonic() >= deadline:
            raise Failure(f"FAIL selection {selector}: expected {selected}, got {nodes}")
        driver.wait_idle(frames=2)


for width in (411, 1100):
    with scene("habits_overview", width) as (driver, database):
        driver.press(label="+ New Habit", role="button")
        driver.wait(label="Create habit", role="button")
        # Change tracking before entering a name, through the ordinary New
        # Habit action rather than a scene that opens the editor directly.
        for difficulty in ("Easy", "Medium", "Hard", "Very hard"):
            reveal(driver, width, label=difficulty, role="button")
            driver.press(label=difficulty, role="button")
            wait_selected(driver, True, label=difficulty, role="button")
        reveal(driver, width, key=7606)
        driver.press(key=7606)
        wait_selected(driver, True, key=7606)
        reveal(driver, width, focus_id=7607, role="text_field")
        driver.press(focus_id=7607, role="text_field")
        driver.key("a", control=True)
        driver.type("-2.5")
        driver.wait(focus_id=7607, value="-2.5")
        reveal(driver, width, key=7610)
        driver.press(key=7610)
        wait_selected(driver, True, key=7610)
        reveal(driver, width, key=7630)
        driver.press(key=7630)
        driver.press(key=9120)
        driver.press(label="Done", role="button")
        driver.wait_gone(key=9120)
        reveal(driver, width, key=7760)
        driver.press(key=7760)
        reveal(driver, width, focus_id=7720, role="text_field")
        driver.press(focus_id=7720, role="text_field")
        driver.type("How did it go?")
        driver.wait(focus_id=7720, value="How did it go?")
        reveal(driver, width, key=7710)
        driver.press(key=7710)
        wait_selected(driver, False, key=7710)
        reveal(driver, width, key=7562)
        driver.press(key=7562)
        wait_selected(driver, True, key=7562)
        reveal(driver, width, key=7531)
        driver.press(key=7531)
        wait_selected(driver, True, key=7531)
        reveal(driver, width, focus_id=7512, role="text_area")
        driver.press(focus_id=7512, role="text_area")
        driver.type("Set every option before creating")
        driver.wait(focus_id=7512, value="Set every option before creating")
        reveal(driver, width, focus_id=7622, role="text_field")
        driver.press(focus_id=7622, role="text_field")
        driver.key("a", control=True)
        driver.type("250")
        driver.wait(focus_id=7622, value="250")
        reveal(driver, width, key=7612)
        driver.press(key=7612)
        wait_selected(driver, True, key=7612)
        wait_selected(driver, False, key=7610)
        driver.press(key=7612)
        wait_selected(driver, False, key=7612)
        reveal(driver, width, key=7610)
        driver.press(key=7610)
        wait_selected(driver, True, key=7610)
        # Returning to the top and typing the name must keep the draft's
        # tracking choices, and Create must store those same choices.
        reveal(driver, width, focus_id=7511, role="text_field")
        driver.press(focus_id=7511, role="text_field")
        name = "New habit options " + str(width)
        driver.type(name)
        driver.press(label="Create habit", role="button")
        expect(sql(database, "SELECT difficulty||':'||custom_coins||':'||coin_halves||':'||"
                   "counter_enabled||':'||counter_target||':'||span FROM habits "
                   "WHERE name='" + name + "' AND deleted_at=0"),
               "2:1:-5:1:250:0", "new habit keeps all tracking options")
        expect(sql(database, "SELECT description||':'||icon||':'||weekdays||':'||"
                   "(sync_activity!=0)||':'||json_extract(questions,'$[0].text') FROM habits "
                   "WHERE name='" + name + "' AND deleted_at=0"),
               "Set every option before creating:2:126:1:How did it go?",
               "new habit keeps details, schedule, practices and questions")
    print("PASS new-habit details, schedule, difficulty, coins, counter, span, "
          f"practices and questions at {width}px")


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

with scene("habit_count_zero") as (driver, database):
    driver.wait(key=DONE)
    expect(driver.wait(contains="Daily target")["label"], "Daily target  0", "zero target text")
    expect(shown_count(driver), 0, "zero count before recording")
    driver.press(key=PLUS)
    wait_count(driver, 1, "record an occurrence")
    driver.press(key=PLUS)
    wait_count(driver, 2, "record a second occurrence")
    driver.press(key=MINUS)
    wait_count(driver, 1, "correct an occurrence")
    driver.press(key=MINUS)
    wait_count(driver, 0, "correct back to zero")
    driver.press(key=DONE)
    driver.wait_gone(key=DONE)
    expect(sql(database, "SELECT count||':'||completed FROM habit_days d JOIN habits h ON h.id=d.habit_id "
               "WHERE h.counter_target=0 AND d.local_date=CAST(strftime('%Y%m%d','now','localtime') AS INTEGER)"),
           "0:1", "confirmed zero stays zero and succeeds")
print("PASS zero-target counts record occurrences and confirm a successful zero")

with scene("habit_edit") as (driver, database):
    driver.press(focus_id=7511, role="text_field")
    driver.type("Reverse habit")
    scroll_to(driver, key=7606)
    driver.press(key=7606)
    scroll_to(driver, focus_id=7607, role="text_field")
    driver.press(focus_id=7607, role="text_field")
    driver.key("a", control=True)
    driver.type("-2")
    driver.wait(focus_id=7607, value="-2")
    scroll_to(driver, key=7610)
    driver.press(key=7610)
    scroll_to(driver, key=7620)
    driver.press(key=7620)
    driver.wait(focus_id=7622, value="0")
    driver.press(key=7621)
    driver.wait(focus_id=7622, value="1")
    driver.press(focus_id=7622, role="text_field")
    driver.key("a", control=True)
    driver.type("0")
    driver.wait(focus_id=7622, value="0")
    driver.pointer(200, 450, wheel=12)
    driver.release_pointer()
    driver.wait_idle(frames=4)
    scroll_to(driver, focus_id=7607, role="text_field")
    driver.pointer(200, 450, wheel=-7)
    driver.release_pointer()
    driver.wait_idle(frames=5)
    window = subprocess.check_output([
        "xdotool", "search", "--onlyvisible", "--pid", str(driver.process.pid)], text=True)
    subprocess.run(["import", "-window", window.splitlines()[0],
                    str(TEST_DIR / "zero-target-negative-coins.png")], check=True)
    driver.press(label="Create habit", role="button")
    expect(sql(database, "SELECT counter_target||':'||custom_coins||':'||coin_halves "
               "FROM habits WHERE name='Reverse habit' AND deleted_at=0"),
           "0:1:-4", "editor saves a zero target and negative coins per occurrence")
print("PASS the habit editor accepts zero by step and typing, and custom negative coins")

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
