"""Diary-linked day taps preserve entries and completions through the real UI."""

import contextlib
import datetime
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

from ui_driver import UiDriver

ROOT = Path(os.environ.get("INBE_TEST_ROOT", Path(__file__).resolve().parents[1]))
OUTPUT = ROOT / "build/habit-diary-ui-test"
WIDTH = 1100


def reveal(driver, **selector):
    for _ in range(60):
        nodes = driver.find(visible=True, **selector)
        if nodes:
            return nodes[0]
        all_nodes = driver.find(**selector)
        direction = 6 if all_nodes and all_nodes[0]["y"] < 0 else -6
        driver.send("pointer", x=WIDTH // 2, y=520, wheel=direction)
        driver.release_pointer()
    return driver.wait(**selector)


def rows(database, query, parameters=()):
    with contextlib.closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as db:
        return db.execute(query, parameters).fetchall()


def snapshot(database):
    return tuple(rows(database, query) for query in (
        "SELECT * FROM habit_days ORDER BY habit_id,local_date",
        "SELECT * FROM habit_entries ORDER BY id",
        "SELECT key,value FROM settings WHERE key LIKE 'cell.diary.file.%' ORDER BY key",
    ))


def wait_for(driver, predicate):
    deadline = time.monotonic() + 20
    while not predicate():
        assert time.monotonic() < deadline, "Expected stored diary completion"
        driver.wait_idle(frames=2)


with tempfile.TemporaryDirectory(prefix="profile-", dir=OUTPUT) as directory:
    profile = Path(directory)
    driver = UiDriver(OUTPUT / "driver")
    environment = os.environ | driver.environment() | {
        "HOME": str(profile / "home"),
        "INBE_SCREENSHOT_DATA_ROOT": str(profile / "data"),
        "APP_SHOT_WINDOW": "1", "APP_NO_TRAY": "1",
    }
    for variable, folder in (("XDG_CONFIG_HOME", "config"), ("XDG_DATA_HOME", "share"),
                             ("XDG_CACHE_HOME", "cache"), ("XDG_STATE_HOME", "state"),
                             ("XDG_RUNTIME_DIR", "runtime")):
        environment[variable] = str(profile / folder)
        (profile / folder).mkdir(mode=0o700)
    (profile / "home").mkdir()
    environment["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={profile / 'runtime' / 'no-session-bus'}"
    environment.pop("INBE_DIARY_IMPORT", None)
    with (OUTPUT / "app.log").open("w") as log:
        app = subprocess.Popen([
            sys.argv[1], "--screenshot", str(profile / "start.png"),
            "--screenshot-scene", "habits_overview", "--screenshot-width", str(WIDTH),
            "--screenshot-height", "900",
        ], env=environment, stdout=log, stderr=subprocess.STDOUT)
        try:
            driver.attach(app, OUTPUT / "app.log")
            database = profile / "data/inbe.db"
            driver.wait(label="+ New Habit", role="button")
            # A normal habit still toggles the same day twice.
            regular = 5200000 + 3 * 16
            before = rows(database, "SELECT completed,count FROM habit_days WHERE habit_id="
                          "(SELECT id FROM habits WHERE name='Push ups') AND local_date=?",
                          (int(datetime.date.today().strftime("%Y%m%d")),))
            driver.press(key=regular)
            changed = rows(database, "SELECT completed,count FROM habit_days WHERE habit_id="
                           "(SELECT id FROM habits WHERE name='Push ups') AND local_date=?",
                           (int(datetime.date.today().strftime("%Y%m%d")),))
            assert changed != before, "Regular habit tap did not toggle completion"
            driver.press(key=regular)
            print("PASS regular habit day taps still toggle completion", flush=True)

            driver.press(label="+ New Habit", role="button")
            reveal(driver, contains="Link", role="button")
            driver.press(contains="Link", role="button")
            driver.press(key=9120)
            assert driver.wait(key=9120)["selected"], "Practice did not select"
            driver.press(label="Diary entry", role="checkbox")
            practice = driver.wait(key=9120)
            assert not practice["enabled"] and not practice["selected"], \
                "Diary must clear and disable other links"
            driver.press(label="Diary entry", role="checkbox")
            assert driver.wait(key=9120)["enabled"], "Deselecting Diary did not restore practice choices"
            driver.press(label="Diary entry", role="checkbox")
            driver.press(label="Done", role="button")
            reveal(driver, focus_id=7511, role="text_field")
            driver.press(focus_id=7511, role="text_field")
            driver.type("Diary navigation regression")
            reveal(driver, key=7559)
            driver.press(key=7559)
            reveal(driver, key=90077)
            driver.press(key=90077)
            driver.press(label="Create habit", role="button")
            habit_id = rows(database, "SELECT id FROM habits WHERE name='Diary navigation regression'")[0][0]
            assert rows(database, "SELECT sync_activity FROM habits WHERE id=?", (habit_id,)) == [(16777216,)]
            assert rows(database, "SELECT icon FROM habits WHERE id=?", (habit_id,)) == [(77,)]
            print("PASS Diary clears other links, disables them, and saves an exclusive link", flush=True)
            diary_day = 5200000 + 6 * 16

            before = snapshot(database)
            driver.press(key=diary_day + 1)
            driver.wait(role="text_area", value="")
            assert snapshot(database) == before, "Opening an empty diary day wrote data"
            assert driver.wait(label="›", role="button")["enabled"], "Selected date was not yesterday"
            driver.press(label="Habits")
            before = snapshot(database)
            driver.press(key=diary_day)
            driver.wait(role="text_area", value="")
            assert not driver.wait(label="›", role="button")["enabled"], "Selected date was not today"
            assert snapshot(database) == before, "Opening today's diary wrote data"
            print("PASS empty linked days open the exact diary date without writes", flush=True)

            driver.press(role="text_area")
            driver.type("Keep this diary entry and its habit completion")
            driver.press(label="Habits")
            today = int(datetime.date.today().strftime("%Y%m%d"))
            wait_for(driver, lambda: rows(database,
                "SELECT completed FROM habit_days WHERE habit_id=? AND local_date=? AND completed=1",
                (habit_id, today)))
            before = snapshot(database)
            driver.press(key=diary_day)
            driver.wait(role="text_area", value="Keep this diary entry and its habit completion")
            assert snapshot(database) == before, "Completed linked day tap changed diary or completion data"
            print("PASS completed linked day opens its diary and preserves all entries and completions", flush=True)
            driver.press(label="Habits")
            # The achievement toast can arrive as Habits opens and cover Statistics.
            driver.wait_idle(frames=2, timeout=2)
            deadline = time.monotonic() + 20
            while True:
                statistics = driver.wait(key=4121)
                pointer = driver.pointer(*driver.center(statistics))
                if pointer["hit"] == statistics["index"]:
                    break
                assert time.monotonic() < deadline, "Statistics stayed covered"
            pressed = driver.press(key=4121, settle=False)
            assert pressed["hit"] == pressed["nodes"][0]["index"], "Pointer did not reach Statistics"
            driver.wait(label="All habits")
            driver.wait(label="Daily completions")
            legend = {"label": "Diary navigation regression", "role": "button"}
            reveal(driver, **legend)
            driver.press(**legend)
            assert driver.wait(**legend)["selected"]
            reveal(driver, key=6100000 + 29)
            driver.wait(key=6100000 + 29, label=f"{today} · 1")
            driver.press(key=6100000 + 29)
            driver.wait(label=f"Diary navigation regression · {today} · 1")
            assert snapshot(database) == before, "Statistics changed habit or diary data"
            print("PASS all-habits statistics opens beside Shop and graphs the linked diary completion", flush=True)
            driver.press(label="Apps", role="button")
            driver.wait(label="Pinned")
            driver.press(focus_id=6792, role="button")
            reveal(driver, label="Completed habits")
            reveal(driver, label="Diary navigation regression")
            assert snapshot(database) == before, "Profile Activity changed habit or diary data"
            print("PASS Profile Activity includes the completed habit with its saved Diary icon", flush=True)
        finally:
            if app.poll() is None:
                app.terminate()
            try:
                app.wait(timeout=5)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=5)
