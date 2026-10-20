"""Select Lumi messages like Telegram on an owned window: hold, sweep, copy, delete.

The app is driven through Kryon's test driver: messages are found in its
widget tree and held, swept and pressed through its own pointer path.
"""
import contextlib
import json
import os
import re
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

from ui_driver import UiDriver

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/lumi-selection-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
assert int(os.environ["DISPLAY"].split(":")[-1].split(".")[0]) >= 300
ENV = os.environ.copy()
driver = UiDriver(OUTPUT / "driver")
# A hold selects a message after half a second.
HOLD_SECONDS = 0.9


def release_announced(db, user):
    """This version's release notes count as already shared, so Lumi adds no
    update message to the chat under test."""
    version = re.search(r'VersionString :: "([^"]+)"', (ROOT / "src/core/version.zi").read_text())[1]
    db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
               "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value",
               (user, "lumi_release_announced", version))


def command(*args):
    return subprocess.run(args, env=ENV, text=True, capture_output=True,
                          check=True, timeout=5).stdout.strip()


def place(label):
    """The centre of the message that says label."""
    return UiDriver.center(driver.wait(label=label, role="text"))


def hold(start, end=None):
    """Hold a message past half a second, then sweep to another one."""
    driver.pointer(*start)
    driver.pointer(*start, down=True)
    time.sleep(HOLD_SECONDS)
    if end is not None:
        for step in range(1, 6):
            driver.pointer(start[0] + (end[0] - start[0]) * step / 5,
                           start[1] + (end[1] - start[1]) * step / 5, down=True)
    finish = end if end is not None else start
    driver.pointer(*finish, down=False)
    driver.release_pointer()
    driver.wait(role="button", label="Copy")


def selected_messages():
    return [node for node in driver.find(role="checkbox", visible=True) if node["selected"]]


def clipboard(expected=None):
    """The clipboard's text, once the app has written it."""
    deadline = time.monotonic() + 5
    while True:
        try:
            copied = command("xclip", "-selection", "clipboard", "-o")
        except subprocess.CalledProcessError:
            copied = None
        if copied is not None and (expected is None or expected(copied)):
            return copied
        assert time.monotonic() < deadline, f"The clipboard holds {copied!r}"
        time.sleep(0.1)


def send(profile, text):
    before = len(records(profile))
    driver.press(role="text_area")
    driver.type(text)
    driver.wait(role="text_area", value=text)
    driver.key("enter")
    deadline = time.monotonic() + 8
    while len(records(profile)) < before + 2:
        assert time.monotonic() < deadline, f"Lumi did not answer {text!r}"
        time.sleep(0.1)
    driver.wait(label=text, role="text")


def records(profile):
    with sqlite3.connect(profile / "inbe.db") as db:
        rows = db.execute("SELECT value FROM settings WHERE key LIKE 'cell.lumi.message.%' "
                          "ORDER BY CAST(json_extract(value,'$.time') AS INTEGER),key").fetchall()
    return [json.loads(row[0]) for row in rows]


@contextlib.contextmanager
def application(profile, label):
    log_path = OUTPUT / f"{label}.log"
    with log_path.open("w") as log:
        app = subprocess.Popen([sys.argv[1], "--bundle", str(ROOT / "build/cells/lumi.zib")],
                               cwd=ROOT, env=ENV | driver.environment() |
                               {"APP_DATA_ROOT": str(profile), "APP_NO_TRAY": "1"},
                               stdout=log, stderr=subprocess.STDOUT)
        driver.attach(app, log_path)
        try:
            deadline = time.monotonic() + 20
            while True:
                assert app.poll() is None, "Lumi exited"
                found = subprocess.run(["xdotool", "search", "--all", "--onlyvisible", "--pid", str(app.pid)],
                                       env=ENV, text=True, capture_output=True, timeout=5)
                if found.returncode == 0 and found.stdout.strip():
                    window = found.stdout.splitlines()[0]
                    break
                assert time.monotonic() < deadline, "Lumi window did not appear"
                time.sleep(0.1)
            command("xdotool", "windowsize", window, "900", "720")
            driver.wait(role="screen")
            driver.wait_idle(frames=3)
            yield window
            assert app.poll() is None, "Lumi crashed"
        finally:
            if app.poll() is None:
                app.terminate()
                app.wait(timeout=5)


def keep_offline(profile):
    """Switched offline and with its guide seen, Lumi opens on its chat
    rather than its online terms or guide."""
    with sqlite3.connect(profile / "inbe.db") as db:
        user = db.execute("SELECT id FROM users LIMIT 1").fetchone()[0]
        for key, value in (("lumi_online", "0"), ("lumi_guides_seen", "127")):
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                       "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value",
                       (user, key, value))
        release_announced(db, user)
        db.execute("DELETE FROM settings WHERE key LIKE 'cell.lumi.message.release-inbe-%'")


with tempfile.TemporaryDirectory(prefix="inbe-lumi-selection-") as temporary:
    profile = Path(temporary)
    with application(profile, "select-initialize"):
        pass
    keep_offline(profile)
    with application(profile, "select") as window:
        send(profile, "alpha note")
        send(profile, "omega note")
        texts = [record["text"] for record in records(profile)]
        assert texts[0] == "alpha note" and texts[2] == "omega note" and len(texts) == 4, texts

        # Holding a message selects it; sweeping selects through another.
        hold(place("alpha note"), place("omega note"))
        assert len(selected_messages()) == 3, selected_messages()
        driver.press(label="Copy", role="button")
        copied = clipboard(lambda text: text == "\n\n".join(texts[:3]))
        assert copied == "\n\n".join(texts[:3]), copied
        driver.wait_gone(label="Copy", role="button")

        # Delete asks first, then removes only the held message everywhere.
        hold(place("alpha note"))
        assert len(selected_messages()) == 1, selected_messages()
        driver.press(label="Delete", role="button")
        driver.wait(contains="Delete the selected messages?")
        assert not records(profile)[0].get("deleted"), "Delete did not ask first"
        driver.press(label="Delete", role="button")
        deadline = time.monotonic() + 5
        while not records(profile)[0].get("deleted"):
            assert time.monotonic() < deadline, "Delete did not reach the archive"
            time.sleep(0.1)
        after = records(profile)
        assert after[0]["deleted"] is True and after[0]["text"] == "—"
        assert [record["text"] for record in after[1:]] == texts[1:]
        driver.wait_gone(label="alpha note", role="text")
        driver.wait(label="omega note", role="text")
    with application(profile, "restart") as window:
        driver.wait(label="omega note", role="text")
        driver.wait_idle(frames=3)
        assert not driver.find(label="alpha note"), "A deleted message came back after restart"
# Dragging to the top edge scrolls through older pages while selecting.
with tempfile.TemporaryDirectory(prefix="inbe-lumi-selection-scroll-") as temporary:
    profile = Path(temporary)
    with application(profile, "scroll-initialize"):
        pass
    keep_offline(profile)
    with sqlite3.connect(profile / "inbe.db") as db:
        user = db.execute("SELECT id FROM users LIMIT 1").fetchone()[0]
        db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                   "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value",
                   (user, "lumi_archive_migrated", "1"))
        for index in range(1, 46):
            value = json.dumps(dict(time=index, user=1, kind=0, payload="",
                                    text=f"History message {index:03}"))
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1)",
                       (user, f"cell.lumi.message.test-{index:03}", value))
    with application(profile, "scroll") as window:
        # The newest message is the lowest one in the chat.
        newest = place("History message 045")
        top = driver.wait(role="screen")["y"] + 20
        driver.pointer(*newest)
        driver.pointer(*newest, down=True)
        time.sleep(HOLD_SECONDS)
        y = newest[1]
        while y > top:
            driver.pointer(newest[0], y, down=True)
            y -= 40
        driver.pointer(newest[0], top, down=True)
        # Held at the top edge, the chat scrolls on through the older pages
        # until the oldest message shows and the sweep has reached it.
        driver.wait(label="History message 001", role="text", timeout=30)
        driver.wait_idle(frames=5, timeout=10, required=True)
        driver.pointer(newest[0], top, down=False)
        driver.release_pointer()
        driver.press(label="Copy", role="button")
        copied = clipboard(lambda text: "History message 001" in text)
        assert "History message 045" in copied and "History message 001" in copied, copied[:200]
        assert copied.count("History message") == 45, copied.count("History message")
print("Lumi selection: hold, sweep, edge scrolling through older pages, copy, delete with confirmation, synced deletion and restart passed")
