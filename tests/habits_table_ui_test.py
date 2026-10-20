"""The habit table on a private display, driven through Kryon's test driver.

Run by habits_table_ui_test.sh on its own Xvfb display: day columns that
stay put while details or the inactive habits open, check-ins and undo,
details and the icon editor, inactive habits, dragged rows with edge
scrolling, and a held Backspace in a text field.
"""

import contextlib
import datetime
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

from PIL import Image

from ui_driver import UiDriver

assert os.environ.get("INBE_UI_TEST_XVFB") == "1", "Run tests/habits_table_ui_test.sh"
assert not os.environ.get("WAYLAND_DISPLAY") and not os.environ.get("DBUS_SESSION_BUS_ADDRESS")
BINARY = sys.argv[1]
ROOT = Path(__file__).resolve().parents[1]
TEST_DIR = ROOT / "build/habits-table-ui-test"
TEST_DIR.mkdir(parents=True, exist_ok=True)
ORDER = "Meditation|Yoga|Sit ups|Push ups|Cold Shower|Jumping Rope"
# Rows and their day circles have no labels; their ids are fixed by
# src/screens/habits_screen.zi (row 4200 + index, circle 5200000 + ...).
ROW_KEYS = range(4200, 4300)
DAY_KEYS = range(5200000, 5300000)
driver = UiDriver(TEST_DIR / "driver")


class Failure(AssertionError):
    pass


def expect(actual, expected, message):
    if actual != expected:
        raise Failure(f"FAIL {message}: got {actual!r}, expected {expected!r} ({TEST_DIR})")


def wait_for(predicate, message, timeout=10):
    deadline = time.monotonic() + timeout
    while True:
        result = predicate()
        if result:
            return result
        if time.monotonic() >= deadline:
            raise Failure(f"FAIL {message() if callable(message) else message} ({TEST_DIR})")
        time.sleep(.05)


with contextlib.ExitStack() as stack:
    temporary = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="inbe-habits-table-")))
    log = stack.enter_context((TEST_DIR / "app.log").open("w"))
    # Screenshot mode seeds its own temporary database; the window stays
    # open for the test. Its own start capture goes to a temporary folder.
    app = subprocess.Popen(
        [BINARY, "--screenshot", str(temporary / "start.png"),
         "--screenshot-scene", "habits_overview", "--screenshot-width", "411",
         "--screenshot-height", "760", "--screenshot-theme", "4", "--screenshot-dark", "1"],
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
    driver.attach(app, TEST_DIR / "app.log")

    def command(*args):
        return subprocess.run(args, check=True, capture_output=True, text=True, timeout=10).stdout.strip()

    def find_window():
        found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                               capture_output=True, text=True, timeout=5)
        return found.stdout.split()[0] if found.returncode == 0 and database.exists() else ""
    window = wait_for(find_window, "isolated app startup", timeout=20)

    def sql(query):
        # Read-only, so closing it never checkpoints the running app's WAL.
        uri = database.as_uri() + "?mode=ro"
        with contextlib.closing(sqlite3.connect(uri, uri=True, timeout=2)) as db:
            row = db.execute(query).fetchone()
            return "" if row is None or row[0] is None else str(row[0])

    def order():
        return sql("SELECT group_concat(name,'|') FROM (SELECT name FROM habits "
                   "WHERE deleted_at=0 ORDER BY sort_order)")

    def day_count():
        return int(sql("SELECT COALESCE(SUM(completed),0) FROM habit_days WHERE "
                       "habit_id=(SELECT id FROM habits WHERE name='Yoga')"))

    def completed_date():
        return sql("SELECT local_date FROM habit_days WHERE habit_id=(SELECT id FROM habits "
                   "WHERE name='Yoga') AND completed=1")

    def deactivated():
        return sql("SELECT deactivated FROM habits WHERE name='Yoga'")

    def resize(width, height):
        command("xdotool", "windowmove", "--sync", window, "0", "0")
        command("xdotool", "windowsize", "--sync", window, str(width), str(height))
        wait_for(lambda: (driver.tree()[0]["width"], driver.tree()[0]["height"]) == (width, height),
                 f"the table did not take the {width}x{height} window")
        driver.wait_idle(frames=3)

    def header():
        """The day columns' names and bounds, today first."""
        tree = driver.tree()
        today = [node for node in tree if node["label"] == "Today" and node["visible"]]
        assert today, "the table has no day columns"
        return [(node["label"], node["x"], node["y"], node["width"], node["height"])
                for node in sorted(tree, key=lambda node: node["x"])
                if node["kind"] == "text" and node["visible"] and node["y"] == today[0]["y"]
                and node["height"] == today[0]["height"] and node["x"] >= today[0]["x"]]

    def rows():
        return [node for node in driver.tree()
                if node["kind"] == "button" and node["key"] in ROW_KEYS and node["visible"]]

    def row_named(name):
        names = [node for node in driver.tree() if node["label"] == name
                 and node["kind"] == "text" and node["visible"]]
        assert names, f"{name}'s row is missing"
        middle = names[0]["y"] + names[0]["height"] / 2
        matches = [row for row in rows() if row["y"] <= middle <= row["y"] + row["height"]]
        assert matches, f"{name} has no row"
        return matches[0], names[0]

    def cell(row, column):
        """The day circle in a row under one day column."""
        matches = [node for node in driver.tree() if node["key"] in DAY_KEYS and node["visible"]
                   and node["x"] == column[1] and node["y"] <= row["y"] + row["height"] / 2
                   <= node["y"] + node["height"]]
        assert matches, f"no day circle under {column[0]}"
        return matches[0]

    def tap(x, y):
        driver.pointer(x, y)
        driver.pointer(x, y, down=True)
        driver.pointer(x, y, down=False)
        driver.release_pointer()

    def press(node):
        tap(*UiDriver.center(node))

    def drag(start, end):
        driver.drag(start, end, steps=12)
        driver.wait_idle(frames=2, timeout=2)

    def capture(name):
        path = TEST_DIR / (name + ".png")
        command("import", "-window", window, str(path))
        with Image.open(path) as image:
            return image.convert("RGB").copy()

    def scrollbar_shown(image, top, bottom):
        """Whether the table's scrollbar shows beside the rows between two
        heights: at the panel's right edge, its thumb is lighter than the
        table beside it."""
        def distance(first, second):
            return sum(abs(a - b) for a, b in zip(first, second))
        lines = 0
        shown = 0
        for y in range(int(top), int(bottom), 4):
            page = image.getpixel((image.width - 3, y))
            edge = image.width - 3
            while edge > 12 and distance(image.getpixel((edge, y)), page) <= 12:
                edge -= 1
            lines += 1
            if distance(image.getpixel((edge - 5, y)), image.getpixel((edge - 12, y))) > 60:
                shown += 1
        return lines > 0 and shown * 5 >= lines * 4

    def header_pixel_y():
        tree = driver.tree()
        screen = tree[0]
        today = [node for node in tree if node["label"] == "Today" and node["visible"]][0]
        scale = screen_pixels[0] / screen["width"]
        return (today["y"] - screen["y"] + today["height"] / 2) * scale

    def details_open():
        return bool(driver.find(contains="streak", visible=True))

    def setting(key):
        return sql("SELECT value FROM settings WHERE key='" + key + "'")

    def inactive_header():
        return driver.wait(contains="Inactive habits", role="button")

    screen_pixels = [411, 760]
    # The screenshot scene seeds its habits after the window and database
    # appear; wait for the seed instead of assuming a fixed startup time.
    wait_for(lambda: database.exists() and order() == ORDER,
             lambda: f"initial order: got {order()!r}, expected {ORDER!r}")
    driver.wait(contains="Inactive habits", role="button")

    # Opening a habit's details or the inactive habits never makes a scrollbar
    # appear and the day columns move or drop: when either would need room to
    # scroll, the scrollbar shows from the start. In a window this short, each
    # of them alone makes the table scroll.
    def steady_columns(width, height, name):
        screen_pixels[:] = [width, height]
        resize(width, height)
        closed = header()
        if len(closed) < 4:
            raise Failure(f"FAIL the {name} table shows only {len(closed)} days ({TEST_DIR})")
        header_y = header_pixel_y()
        if not scrollbar_shown(capture(name + "-closed"), header_y + 30, header_y + 200):
            raise Failure(f"FAIL the {name} table shows no scrollbar before anything opens "
                          f"({TEST_DIR}/{name}-closed.png)")
        # Yoga's row is the second below the day names; its icon, at the
        # start of the row before the first day, opens it.
        yoga = rows()[1]
        first_day = cell(yoga, closed[0])
        icon = (yoga["x"] + (first_day["x"] - yoga["x"]) / 2, yoga["y"] + yoga["height"] / 2)
        if width >= 300:
            assert driver.find(label="Yoga", visible=True), "a phone's rows hide names"
        tap(*icon)
        wait_for(details_open, f"Yoga's details did not open in the {name} table")
        if width < 300:
            assert driver.find(label="Yoga", visible=True), "a narrow expanded card hides its name"
        driver.wait_idle(frames=3)
        expect(header(), closed, f"opening Yoga moved the {name} table's day columns")
        tap(*icon)
        wait_for(lambda: not details_open(), f"Yoga's details did not close in the {name} table")
        driver.press(contains="Inactive habits", role="button")
        driver.wait(contains="Drag a habit here")
        driver.wait_idle(frames=3)
        expect(header(), closed, f"opening the inactive habits moved the {name} table's day columns")
        driver.press(contains="Inactive habits", role="button")
        driver.wait_gone(contains="Drag a habit here")

    steady_columns(390, 660, "phone")
    steady_columns(1024, 660, "desktop")
    # A table that fits with everything open shows no scrollbar.
    screen_pixels[:] = [411, 1000]
    resize(411, 1000)
    header_y = header_pixel_y()
    if scrollbar_shown(capture("tall"), header_y + 30, header_y + 200):
        raise Failure(f"FAIL a table with room for everything shows a scrollbar ({TEST_DIR}/tall.png)")
    screen_pixels[:] = [411, 760]
    resize(411, 760)
    print("PASS steady columns: opening a habit or the inactive habits keeps the day columns at a phone's and a desktop's width")

    # Dragging the border between the names and the days widens the name
    # column; the day columns move right with it.
    resize_handle = driver.wait(key=4100000, role="button")
    handle_center = UiDriver.center(resize_handle)
    drag(handle_center, (handle_center[0] + 170, handle_center[1]))
    wait_for(lambda: setting("habits_name_width") == "320",
             lambda: "the resized name width was not saved: " + setting("habits_name_width"))
    assert len(header()) >= 4, "resizing the name column dropped below four days"
    # The widest name column still leaves four days, and its rows keep their names.
    assert driver.find(label="Yoga", visible=True), "the widest name column hides row names"
    yoga = rows()[1]
    first_day = cell(yoga, header()[0])
    icon = (yoga["x"] + (first_day["x"] - yoga["x"]) / 2, yoga["y"] + yoga["height"] / 2)
    tap(*icon)
    wait_for(details_open, "the icon-only row did not open its details")
    assert driver.find(label="Yoga", visible=True), "an icon-only expanded card hides its name"
    tap(*icon)
    wait_for(lambda: not details_open(), "the icon-only details did not close")
    # The day columns where the wider name column left them: today first,
    # then yesterday and the day before, named by their weekdays in the header.
    columns = header()
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    before_yesterday = today - datetime.timedelta(days=2)
    expect(columns[0][0], "Today", "the header starts with today")
    expect(columns[1][0], yesterday.strftime("%a"), "the header names yesterday")
    expect(columns[2][0], before_yesterday.strftime("%a"), "the header names the day before")
    yoga, yoga_name = row_named("Yoga")
    before = day_count()
    press(cell(yoga, columns[0]))
    wait_for(lambda: day_count() == before + 1, "today check-in")
    expect(completed_date(), today.strftime("%Y%m%d"), "the first column marks today")
    press(cell(yoga, columns[0]))
    wait_for(lambda: day_count() == before, "today undo")
    press(cell(yoga, columns[1]))
    wait_for(lambda: completed_date() == yesterday.strftime("%Y%m%d"),
             "the second column marks yesterday")
    press(cell(yoga, columns[1]))
    wait_for(lambda: day_count() == before, "yesterday undo")
    start = UiDriver.center(cell(yoga, columns[0]))
    drag(start, (start[0] + 150, start[1]))
    expect(day_count(), before, "a drag over the days marks none")
    # A tap on the name opens the habit's details below its row; another closes them.
    driver.press(label="Yoga")
    wait_for(details_open, "the open habit shows its streak")
    # Opening scrolls the list so the whole card shows; wait until it rests.
    driver.wait_idle(frames=3)
    driver.wait(label="This week")
    # The open details make the table scroll; its scrollbar already showed, so
    # the day columns stay where they were.
    expect(header(), columns, "opening Yoga moved the day columns")
    # Its editor opens from the last of the details' actions, at the table's
    # right edge above the figures, and gives Yoga an icon.
    yoga, yoga_name = row_named("Yoga")
    figures = driver.wait(label="Current streak")
    actions = [node for node in driver.tree() if node["kind"] == "button" and node["visible"]
               and node["width"] == node["height"] and not node["label"]
               and yoga["y"] + yoga["height"] <= node["y"] < figures["y"]]
    expect(len(actions), 3, "the open habit's actions")
    driver.press(key=actions[-1]["key"])
    driver.wait(label="Edit Habit", role="title_bar")
    # The third choice is the second icon, a person sitting in meditation.
    icon_title = driver.wait(label="Icon")
    choices = [node for node in driver.tree() if node["kind"] == "button" and node["visible"]
               and icon_title["y"] < node["y"] < icon_title["y"] + icon_title["height"] + 60]
    choices.sort(key=lambda node: node["x"])
    driver.press(key=choices[2]["key"])
    driver.press(label="Save", role="button")
    wait_for(lambda: sql("SELECT icon FROM habits WHERE name='Yoga'") == "2", "the chosen icon is saved")
    driver.wait_gone(label="Edit Habit", role="title_bar")
    driver.wait_idle(frames=3)
    if details_open():
        raise Failure(f"FAIL the details stayed open ({TEST_DIR})")
    expect(order(), ORDER, "taps keep the order")
    print("PASS habit table: day columns, check-ins, undo, drag cancellation, details, icon")

    # Dragged onto the inactive habits' header at the end of the table, Yoga
    # becomes inactive: it keeps its data and leaves the habits.
    yoga, yoga_name = row_named("Yoga")
    drag(UiDriver.center(yoga_name), UiDriver.center(inactive_header()))
    wait_for(lambda: deactivated() == "1", "a habit dropped on the inactive habits becomes inactive")
    expect(order(), ORDER, "deactivating keeps the order")
    if driver.find(label="Yoga", visible=True):
        raise Failure(f"FAIL Yoga is still in the table ({TEST_DIR})")
    shown = inactive_header()
    driver.press(key=shown["key"])
    listed = driver.wait(label="Yoga")
    if listed["y"] < shown["y"]:
        raise Failure("FAIL Yoga is not listed among the inactive habits")
    meditation, meditation_name = row_named("Meditation")
    driver.press(label="Yoga")
    driver.wait_idle(frames=3)
    expect(deactivated(), "1", "a tap does not reactivate")
    # Dropped on Meditation's row, Yoga becomes active in Meditation's place.
    drag(UiDriver.center(driver.wait(label="Yoga")), UiDriver.center(meditation_name))
    wait_for(lambda: deactivated() == "0", "a drag into the table reactivates Yoga")
    wait_for(lambda: order() == "Yoga|Meditation|Sit ups|Push ups|Cold Shower|Jumping Rope",
             lambda: f"Yoga takes the place it was dropped on: {order()}")
    # The dropdown stays, so a habit can be dragged into it again.
    inactive_header()
    print("PASS inactive habits: dragged into the dropdown, hidden from the table, dragged back into place")

    # With a mouse, a row follows a press that moves at once and takes the
    # place of the row it is dropped on.
    meditation, meditation_name = row_named("Meditation")
    push, push_name = row_named("Push ups")
    drag(UiDriver.center(meditation_name), UiDriver.center(push_name))
    wait_for(lambda: order() == "Yoga|Sit ups|Push ups|Meditation|Cold Shower|Jumping Rope",
             lambda: f"a dragged row takes the place it was dropped on: {order()}")
    # In a shorter window, a row held at the bottom edge of the table scrolls it
    # down to the last habit, which is out of sight at first.
    screen_pixels[:] = [411, 520]
    resize(411, 520)
    if driver.find(label="Jumping Rope", visible=True):
        raise Failure("FAIL Jumping Rope is already in sight, so nothing needs to scroll")
    yoga, yoga_name = row_named("Yoga")
    table = [node for node in driver.tree() if node["kind"] == "scroll" and node["visible"]][0]
    x, y = UiDriver.center(yoga_name)
    edge = table["y"] + table["height"] - 10
    driver.pointer(x, y)
    driver.pointer(x, y, down=True)
    for step in range(1, 13):
        driver.pointer(x, y + (edge - y) * step / 12, down=True)
    # Holding the row there scrolls the table for a while.
    time.sleep(1.5)
    # Lifted off the edge, the dragged copy no longer covers the last row.
    driver.pointer(x, edge - 200, down=True)
    try:
        jumping = driver.wait(label="Jumping Rope", timeout=3)
    except AssertionError:
        driver.pointer(x, edge - 200, down=False)
        driver.release_pointer()
        raise Failure("FAIL holding a row at the edge did not scroll the table")
    driver.pointer(x, UiDriver.center(jumping)[1], down=True)
    driver.pointer(x, UiDriver.center(jumping)[1], down=False)
    driver.release_pointer()
    wait_for(lambda: order() == "Sit ups|Push ups|Meditation|Cold Shower|Jumping Rope|Yoga",
             lambda: f"a row dragged down the scrolled table goes last: {order()}")
    print("PASS habit rows: dragged into another place and scrolled at the edge")

    # Holding Backspace keeps deleting, as in any text editor: a new habit typed
    # as "Walkx", cleared with one held Backspace and typed again is "Run".
    driver.press(label="+ New Habit", role="button")
    name_title = driver.wait(label="Name")
    field = [node for node in driver.find(role="text_field", visible=True)
             if node["y"] >= name_title["y"] + name_title["height"]][0]
    driver.press(key=field["key"])
    driver.type("Walkx")
    driver.wait(role="text_field", value="Walkx")
    # The driver presses keys once; a held key's repeat needs a real key.
    command("xdotool", "windowfocus", "--sync", window)
    command("xdotool", "keydown", "BackSpace")
    time.sleep(1.6)
    command("xdotool", "keyup", "BackSpace")
    wait_for(lambda: driver.find(role="text_field", value="", visible=True),
             "a held Backspace did not keep deleting")
    driver.type("Run")
    driver.wait(role="text_field", value="Run")
    driver.press(label="Create habit", role="button")
    wait_for(lambda: sql("SELECT COUNT(*) FROM habits WHERE name='Run' AND deleted_at=0") == "1",
             "a held Backspace deleted the whole name")
    print("PASS text fields: a held Backspace keeps deleting")
    print(f"Captures: {TEST_DIR}")
