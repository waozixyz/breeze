"""Select Lumi messages like Telegram on an owned window: hold, sweep, copy, delete."""
import contextlib
import csv
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/lumi-selection-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
assert int(os.environ["DISPLAY"].split(":")[-1].split(".")[0]) >= 300
ENV = os.environ.copy()
# The chat column is 720 wide in a 900 wide window; the selection bar's
# controls are 44 square in its top row.
LEFT, WIDTH, BAR_Y = 90, 720, 34


def command(*args):
    return subprocess.run(args, env=ENV, text=True, capture_output=True,
                          check=True, timeout=5).stdout.strip()


def capture(window, label):
    raw = OUTPUT / f"{label}.xwd"
    command("xwd", "-silent", "-id", window, "-out", str(raw))
    command("convert", str(raw), str(OUTPUT / f"{label}.png"))
    raw.unlink()
    return OUTPUT / f"{label}.png"


def tap(window, x, y):
    command("xdotool", "mousemove", "--window", window, str(x), str(y))
    time.sleep(0.15)
    command("xdotool", "mousedown", "1")
    time.sleep(0.15)
    command("xdotool", "mouseup", "1")
    time.sleep(0.4)


def hold(window, start, end=None):
    """Hold a message past half a second, then sweep to another one."""
    command("xdotool", "mousemove", "--window", window, str(start[0]), str(start[1]))
    time.sleep(0.15)
    command("xdotool", "mousedown", "1")
    time.sleep(0.9)
    if end is not None:
        for step in range(1, 6):
            x = start[0] + (end[0] - start[0]) * step // 5
            y = start[1] + (end[1] - start[1]) * step // 5
            command("xdotool", "mousemove", "--window", window, str(x), str(y))
            time.sleep(0.1)
    command("xdotool", "mouseup", "1")
    time.sleep(0.4)


def word_at(window, label, word):
    """Where a rendered word is, found with OCR."""
    result = command("tesseract", str(capture(window, label)), "stdout", "--psm", "11",
                     "-c", "tessedit_create_tsv=1")
    for item in csv.DictReader(io.StringIO(result), delimiter="\t"):
        if (item.get("text") or "").strip().lower() == word:
            return (int(item["left"]) + int(item["width"]) // 2,
                    int(item["top"]) + int(item["height"]) // 2)
    raise AssertionError(f"{word!r} is not on screen")


def lowest_word(window, label, word):
    """The lowest place a rendered word appears, found with OCR."""
    result = command("tesseract", str(capture(window, label)), "stdout", "--psm", "11",
                     "-c", "tessedit_create_tsv=1")
    places = [(int(item["left"]) + int(item["width"]) // 2, int(item["top"]) + int(item["height"]) // 2)
              for item in csv.DictReader(io.StringIO(result), delimiter="\t")
              if (item.get("text") or "").strip().lower() == word]
    assert places, f"{word!r} is not on screen"
    return max(places, key=lambda place: place[1])


def send(window, text):
    command("xdotool", "mousemove", "--window", window, "400", "680")
    command("xdotool", "mousedown", "1")
    time.sleep(0.1)
    command("xdotool", "mouseup", "1")
    time.sleep(0.3)
    command("xdotool", "type", "--delay", "20", text)
    command("xdotool", "keydown", "Return")
    time.sleep(0.1)
    command("xdotool", "keyup", "Return")
    time.sleep(0.6)


def records(profile):
    with sqlite3.connect(profile / "inbe.db") as db:
        rows = db.execute("SELECT value FROM settings WHERE key LIKE 'cell.lumi.message.%' "
                          "ORDER BY CAST(json_extract(value,'$.time') AS INTEGER),key").fetchall()
    return [json.loads(row[0]) for row in rows]


@contextlib.contextmanager
def application(profile, label):
    with (OUTPUT / f"{label}.log").open("w") as log:
        app = subprocess.Popen([sys.argv[1], "--bundle", str(ROOT / "build/cells/lumi.zib")],
                               cwd=ROOT, env=ENV | {"APP_DATA_ROOT": str(profile), "APP_NO_TRAY": "1"},
                               stdout=log, stderr=subprocess.STDOUT)
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
            command("xdotool", "windowfocus", "--sync", window)
            time.sleep(1.5)
            yield window
            assert app.poll() is None, "Lumi crashed"
        finally:
            if app.poll() is None:
                app.terminate()
                app.wait(timeout=5)


with tempfile.TemporaryDirectory(prefix="inbe-lumi-selection-") as temporary:
    profile = Path(temporary)
    with application(profile, "select") as window:
        send(window, "alpha note")
        send(window, "omega note")
        texts = [record["text"] for record in records(profile)]
        assert texts[0] == "alpha note" and texts[2] == "omega note" and len(texts) == 4, texts

        # Holding a message selects it; sweeping selects through another.
        hold(window, word_at(window, "before-hold", "alpha"), word_at(window, "before-sweep", "omega"))
        capture(window, "selected")
        tap(window, LEFT + WIDTH - 2 * 44 - 4 + 22, BAR_Y)  # Copy.
        copied = command("xclip", "-selection", "clipboard", "-o")
        assert copied == "\n\n".join(texts[:3]), copied
        capture(window, "copied")

        # Delete asks first, then removes only the held message everywhere.
        hold(window, word_at(window, "before-delete", "alpha"))
        tap(window, LEFT + WIDTH - 22, BAR_Y)  # Delete.
        capture(window, "confirm-delete")
        tap(window, LEFT + WIDTH - 50, BAR_Y)  # Confirm.
        deadline = time.monotonic() + 5
        while not records(profile)[0].get("deleted"):
            assert time.monotonic() < deadline, "Delete did not reach the archive"
            time.sleep(0.1)
        after = records(profile)
        assert after[0]["deleted"] is True and after[0]["text"] == "—"
        assert [record["text"] for record in after[1:]] == texts[1:]
        capture(window, "deleted")
    with application(profile, "restart") as window:
        capture(window, "restarted")
        try:
            word_at(window, "restarted-check", "alpha")
            raise AssertionError("A deleted message came back after restart")
        except AssertionError as error:
            if "came back" in str(error):
                raise
# Dragging to the top edge scrolls through older pages while selecting.
with tempfile.TemporaryDirectory(prefix="inbe-lumi-selection-scroll-") as temporary:
    profile = Path(temporary)
    with application(profile, "scroll-initialize"):
        pass
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
        newest = lowest_word(window, "scroll-start", "history")
        command("xdotool", "mousemove", "--window", window, str(newest[0]), str(newest[1]))
        time.sleep(0.15)
        command("xdotool", "mousedown", "1")
        time.sleep(0.9)
        for y in range(newest[1], 20, -40):
            command("xdotool", "mousemove", "--window", window, str(newest[0]), str(y))
            time.sleep(0.05)
        command("xdotool", "mousemove", "--window", window, str(newest[0]), "20")
        time.sleep(6.0)
        command("xdotool", "mouseup", "1")
        time.sleep(0.4)
        capture(window, "scroll-selected")
        tap(window, LEFT + WIDTH - 2 * 44 - 4 + 22, BAR_Y)  # Copy.
        copied = command("xclip", "-selection", "clipboard", "-o")
        assert "History message 045" in copied and "History message 001" in copied, copied[:200]
        assert copied.count("History message") == 45, copied.count("History message")
print("Lumi selection: hold, sweep, edge scrolling through older pages, copy, delete with confirmation, synced deletion and restart passed")
