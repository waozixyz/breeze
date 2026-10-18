"""Unsaved habit drafts, using synthetic data on a private display."""
import contextlib
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile

from ui_driver import UiDriver

assert int(os.environ.get("DISPLAY", ":0").split(":")[-1].split(".")[0]) >= 300
ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(sys.argv[1]).resolve()
OUTPUT = ROOT / "build/habit-unsaved-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
NAME = 7511
PROMPT = "Save your changes to this habit before leaving?"


@contextlib.contextmanager
def editor(name, scene="habit_edit"):
    driver = UiDriver(OUTPUT / ("driver-" + name))
    with tempfile.TemporaryDirectory(prefix="inbe-habit-unsaved-") as folder:
        log_path = OUTPUT / (name + ".log")
        with log_path.open("w") as log:
            bundle = os.environ.get("INBE_TEST_BUNDLE")
            app = subprocess.Popen(
                [str(BINARY), *(["--bundle", bundle] if bundle else []),
                 "--screenshot", str(Path(folder) / "initial.png"),
                 "--screenshot-scene", scene, "--screenshot-width", "411",
                 "--screenshot-height", "760"], cwd=ROOT,
                env=os.environ | {"APP_SHOT_WINDOW": "1"} | driver.environment(),
                stdout=log, stderr=subprocess.STDOUT)
            database = Path(f"/tmp/inbe-screenshot-{app.pid}/inbe.db")
            driver.attach(app, log_path)
            try:
                if scene == "habit_edit":
                    driver.wait(focus_id=NAME, role="text_field")
                else:
                    driver.wait(label="Delete Habit", role="button")
                yield driver, database, app
                assert app.poll() is None, log_path.read_text()
            finally:
                if app.poll() is None:
                    app.terminate()
                try:
                    app.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    app.kill()
                    app.wait(timeout=5)
                shutil.rmtree(database.parent, ignore_errors=True)


def name_draft(driver, name):
    driver.press(focus_id=NAME, role="text_field")
    driver.key("a", control=True)
    if name:
        driver.type(name)
    else:
        driver.key("backspace")
    driver.wait(focus_id=NAME, value=name)


def saved(database, name):
    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=3) as db:
        return db.execute("SELECT count(*) FROM habits WHERE name=? AND deleted_at=0", (name,)).fetchone()[0]


with editor("unchanged") as (driver, database, app):
    driver.press(label="Back", role="button")
    driver.wait(label="+ New Habit", role="button")
    assert not driver.find(label=PROMPT), "unchanged form prompted"

with editor("keep-discard") as (driver, database, app):
    name_draft(driver, "Unsaved habit")
    driver.press(label="Back", role="button")
    driver.wait(label=PROMPT)
    # Capture only this test process's window on its private display.
    found = subprocess.check_output(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)], text=True)
    subprocess.run(["import", "-window", found.splitlines()[0], str(OUTPUT / "prompt.png")], check=True)
    driver.press(label="Keep editing", role="button")
    driver.wait(focus_id=NAME, value="Unsaved habit")
    assert not saved(database, "Unsaved habit"), "keeping the draft saved it"
    driver.press(label="Back", role="button")
    driver.press(label="Discard", role="button")
    driver.wait(label="+ New Habit", role="button")
    assert not saved(database, "Unsaved habit"), "discard wrote the draft"

with editor("save") as (driver, database, app):
    name_draft(driver, "Saved from prompt")
    driver.press(label="Back", role="button")
    driver.press(label="Save", role="button")
    driver.wait(label="+ New Habit", role="button")
    assert saved(database, "Saved from prompt") == 1, "Save lost or duplicated the habit"

with editor("invalid") as (driver, database, app):
    name_draft(driver, " ")
    driver.press(label="Back", role="button")
    driver.press(label="Save", role="button")
    driver.wait(label="Enter a habit name.")
    driver.wait(focus_id=NAME, value=" ")

with editor("escape") as (driver, database, app):
    name_draft(driver, "Escape draft")
    driver.key("escape")
    driver.wait(label=PROMPT)
    driver.press(label="Keep editing", role="button")
    driver.wait(focus_id=NAME, value="Escape draft")
    assert not saved(database, "Escape draft"), "Escape saved the draft"

with editor("delete", "habit_edit_questions") as (driver, database, app):
    def habit_count():
        with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=3) as db:
            return db.execute("SELECT COUNT(*) FROM habits WHERE deleted_at=0").fetchone()[0]

    count = habit_count()
    driver.press(label="Delete Habit", role="button")
    driver.wait(label="Cancel", role="button")
    driver.press(label="Cancel", role="button")
    driver.wait(label="Delete Habit", role="button")
    assert habit_count() == count, "Cancel deleted a habit"
    driver.press(label="Delete Habit", role="button")
    driver.wait(label="Cancel", role="button")
    driver.press(label="Delete", role="button")
    driver.wait(label="+ New Habit", role="button")
    assert habit_count() == count - 1, "Delete did not remove exactly the edited habit"

print("Habit confirmations: unchanged Back, Keep editing, Discard, Save, validation, Escape, Cancel and Delete passed")
