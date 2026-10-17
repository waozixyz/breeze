#!/usr/bin/env python3
"""Chess from More apps on a private display: install, play the computer, restart.

The node's offer comes from a local package (INBE_NODE_APP_FILE), so nothing
is downloaded or published. Taps find their buttons by the words drawn.
"""
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

from PIL import Image

assert int(os.environ.get("DISPLAY", ":0").split(":")[-1].split(".")[0]) >= 300
ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(sys.argv[1]).resolve()
PACKAGE = Path(sys.argv[2]).resolve()
OUTPUT = ROOT / "build/chess-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
WIDTH, HEIGHT = 390, 844
FRAME_EDGE = (110, 76, 54)
IVORY = (246, 241, 231)


def command(*args):
    return subprocess.check_output(args, text=True, timeout=10).strip()


def capture(window, name):
    path = OUTPUT / (name + ".png")
    command("import", "-window", window, str(path))
    with Image.open(path) as image:
        return image.convert("RGB").copy()


def click(window, x, y):
    command("xdotool", "mousemove", "--window", window, str(x), str(y))
    time.sleep(0.12)
    command("xdotool", "mousedown", "1")
    time.sleep(0.15)
    command("xdotool", "mouseup", "1")
    time.sleep(0.5)


def words(window, name):
    """Each word drawn and the center of its box, read at three times the size."""
    image = capture(window, name)
    gray = image.convert("L").resize((image.width * 3, image.height * 3))
    path = OUTPUT / (name + "-ocr.png")
    gray.save(path)
    result = subprocess.run(["tesseract", str(path), "stdout", "--psm", "11", "-c", "tessedit_create_tsv=1"],
                            check=True, text=True, capture_output=True, timeout=20)
    found = []
    for line in result.stdout.splitlines()[1:]:
        fields = line.split("\t")
        if len(fields) == 12 and fields[11].strip():
            left, top, width, height = map(int, fields[6:10])
            found.append((fields[11].strip(), (left + width // 2) // 3, (top + height // 2) // 3))
    return found


def tap_word(window, word, name, attempts=20):
    """Taps the first drawn word equal to `word`, waiting for it to appear."""
    for attempt in range(attempts):
        for text, x, y in words(window, f"{name}-{attempt}"):
            if text.strip(".,:;!").lower() == word.lower():
                click(window, x, y)
                return
        time.sleep(0.5)
    raise AssertionError(f"no '{word}' to tap; see {OUTPUT / name}")


def wait_for(window, word, name, attempts=40):
    for attempt in range(attempts):
        if any(text.strip(".,:;!").lower() == word.lower() for text, _, _ in words(window, f"{name}-{attempt}")):
            return
        time.sleep(0.5)
    raise AssertionError(f"'{word}' never appeared; see {OUTPUT / name}")


def board_bounds(image):
    """The board inside its brown frame: left, top and square size."""
    width, height = image.size
    rows = [y for y in range(height) if sum(1 for x in range(0, width, 2)
                                             if image.getpixel((x, y)) == FRAME_EDGE) > 40]
    columns = [x for x in range(width) if sum(1 for y in range(0, height, 2)
                                              if image.getpixel((x, y)) == FRAME_EDGE) > 40]
    assert rows and columns, "no board frame drawn"
    top, bottom = rows[0], rows[-1]
    left, right = columns[0], columns[-1]
    edge = 3
    size = min(right - left, bottom - top) - edge * 2
    return left + edge, top + edge, size // 8


def square_center(bounds, square, flipped=False):
    left, top, cell = bounds
    file = ord(square[0]) - ord("a")
    rank = int(square[1]) - 1
    column = 7 - file if flipped else file
    row = rank if flipped else 7 - rank
    return left + column * cell + cell // 2, top + row * cell + cell // 2


def ivory_share(image, bounds, square):
    """How much of a square is the ivory of the white pieces."""
    x, y = square_center(bounds, square)
    cell = bounds[2]
    pixels = [image.getpixel((x + dx, y + dy)) for dx in range(-cell // 4, cell // 4)
              for dy in range(-cell // 4, cell // 4)]
    return sum(1 for pixel in pixels if all(abs(a - b) < 12 for a, b in zip(pixel, IVORY))) / len(pixels)


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def launch(profile, name):
    log = (OUTPUT / (name + ".log")).open("w")
    app = subprocess.Popen([str(BINARY)], cwd=ROOT,
                           env=os.environ | {"APP_DATA_ROOT": str(profile), "INBE_NODE_APP_FILE": str(PACKAGE)},
                           stdout=log, stderr=subprocess.STDOUT)
    for _ in range(300):
        assert app.poll() is None, (OUTPUT / (name + ".log")).read_text()
        found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                               capture_output=True, text=True)
        if found.returncode == 0 and (profile / "inbe.db").exists():
            window = found.stdout.splitlines()[0]
            command("xdotool", "windowsize", window, str(WIDTH), str(HEIGHT))
            command("xdotool", "windowmove", window, "0", "0")
            time.sleep(1.5)
            return app, window
        time.sleep(0.1)
    stop(app)
    raise AssertionError("Inbe did not map its window")


def settings(profile, user):
    with sqlite3.connect(profile / "inbe.db", timeout=3) as db:
        return {key: (value, updated) for key, value, updated in
                db.execute("SELECT key,value,updated_at FROM settings WHERE user_id=?", (user,))}


with tempfile.TemporaryDirectory(prefix="inbe-chess-") as directory:
    profile = Path(directory)
    app, _ = launch(profile, "first-start")
    stop(app)
    with sqlite3.connect(profile / "inbe.db") as db:
        user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
        saved = dict(db.execute("SELECT key,value FROM settings WHERE user_id=?", (user,)))
        assert saved.get("app_used_chess") is None, "Chess was installed for a new profile"
        # No network: the node's list was just read, and updates wait.
        seeded = {"language": "en", "language_system": 0, "language_setup_done": 1, "apps_setup_done": 1,
                  "tutorial_seen": 1, "habits_guide_seen": 1, "lumi_guides_seen": 127, "launcher_guide_seen": 1,
                  "package_updates_allowed": 0, "apps_last_update_check": 1900000000,
                  "node_apps_checked_at": int(time.time())}
        for key, value in seeded.items():
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                       "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user, key, str(value)))
    app, window = launch(profile, "install")
    try:
        # More apps lists Chess because the node (here, the local file) offers it.
        tap_word(window, "Apps", "open-apps")
        tap_word(window, "Chess", "more-apps")
        # The selected level (Medium) is drawn filled, which OCR misses.
        wait_for(window, "Hard", "setup")
        capture(window, "setup")
        tap_word(window, "Easy", "choose-easy")
        tap_word(window, "Start", "start")
        wait_for(window, "move", "your-move")
        before = capture(window, "board")
        bounds = board_bounds(before)
        assert ivory_share(before, bounds, "e2") > 0.2 and ivory_share(before, bounds, "e4") < 0.05, "start position"
        click(window, *square_center(bounds, "e2"))
        click(window, *square_center(bounds, "e4"))
        time.sleep(1.0)
        after = capture(window, "after-move")
        assert ivory_share(after, bounds, "e4") > 0.2 and ivory_share(after, bounds, "e2") < 0.05, "e4 was not played"
        # The computer answers, then it is our move again.
        wait_for(window, "move", "reply")
        stored = settings(profile, user)
        assert stored["app_used_chess"][0] == "1" and stored["app_used_chess"][1] > 1, stored.get("app_used_chess")
        assert stored["node_app_slot_0"][0] == "chess", stored.get("node_app_slot_0")
        record = stored["cell.chess.computer"][0]
        assert "level=0;color=w;" in record and len(record.split("moves=")[1].split()) == 2, record
        # Friends need an account; without one the tab says how to sign in.
        tap_word(window, "Friends", "friends")
        wait_for(window, "Sign", "sign-in")
        capture(window, "friends")
        log = (OUTPUT / "install.log").read_text()
        assert "frame rejected" not in log and app.poll() is None, log
    finally:
        stop(app)
    # After a restart Chess is still installed and the game continues.
    app, window = launch(profile, "restart")
    try:
        tap_word(window, "Apps", "reopen-apps")
        tap_word(window, "Chess", "reopen-chess")
        wait_for(window, "move", "restored")
        restored = capture(window, "restored")
        assert ivory_share(restored, board_bounds(restored), "e4") > 0.2, "the saved game was not restored"
        log = (OUTPUT / "restart.log").read_text()
        assert "frame rejected" not in log and app.poll() is None, log
    finally:
        stop(app)
print("Chess: offered in More apps, installed, played against the computer and restored after a restart")
