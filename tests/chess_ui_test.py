#!/usr/bin/env python3
"""Chess from More apps on a private display: install, play the computer, restart.

The node's offer comes from a local package (INBE_NODE_APP_FILE), so nothing
is downloaded or published. Buttons, squares and pieces are found in the
app's widget tree through Kryon's test driver; pixels are read once, to see
that the moved piece is really drawn.
"""
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

from PIL import Image

from ui_driver import UiDriver

assert int(os.environ.get("DISPLAY", ":0").split(":")[-1].split(".")[0]) >= 300
ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(sys.argv[1]).resolve()
PACKAGE = Path(sys.argv[2]).resolve()
OUTPUT = ROOT / "build/chess-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
WIDTH, HEIGHT = 390, 844
IVORY = (246, 241, 231)
# Chess keys each square's box and the piece drawn on it by the square's
# index on the board as drawn, from a8 (0) to h1 (63).
SQUARE_KEY = 8010
PIECE_KEY = 8400
START = {"a": "Rook", "b": "Knight", "c": "Bishop", "d": "Queen",
         "e": "King", "f": "Bishop", "g": "Knight", "h": "Rook"}
driver = UiDriver(OUTPUT / "driver")


def command(*args):
    return subprocess.check_output(args, text=True, timeout=10).strip()


def capture(window, name):
    path = OUTPUT / (name + ".png")
    command("import", "-window", window, str(path))
    with Image.open(path) as image:
        return image.convert("RGB").copy()


def wait_for(predicate, message, timeout=20):
    deadline = time.monotonic() + timeout
    while True:
        value = predicate()
        if value:
            return value
        if time.monotonic() >= deadline:
            driver.tree()
            raise driver._failure(message)
        time.sleep(0.05)


def square_index(square, flipped=False):
    file = ord(square[0]) - ord("a")
    rank = int(square[1]) - 1
    column = 7 - file if flipped else file
    row = rank if flipped else 7 - rank
    return row * 8 + column


def square_name(index):
    return "abcdefgh"[index % 8] + str(8 - index // 8)


def board():
    """Every piece drawn, by the square it stands on."""
    return {square_name(node["key"] - PIECE_KEY): node["label"] for node in driver.tree()
            if node["kind"] == "image" and node["visible"] and PIECE_KEY <= node["key"] < PIECE_KEY + 64}


def start_position():
    pieces = {}
    for file, piece in START.items():
        pieces[file + "1"] = piece
        pieces[file + "8"] = piece
        pieces[file + "2"] = "Pawn"
        pieces[file + "7"] = "Pawn"
    return pieces


def play(pieces, move):
    """The board after a move in coordinate notation, such as e2e4."""
    after = dict(pieces)
    after[move[2:4]] = after.pop(move[0:2])
    return after


def selected(label):
    return driver.find(label=label, role="button", visible=True)[0]["selected"]


def window_point(x, y):
    """Where a point of the widget tree is drawn in the window.

    While a node app shows, the tree's screen starts above the window by
    the title bar's height, so its bounds are shifted from the pixels.
    """
    screen = driver.tree()[0]
    return round(x - screen["x"]), round(y - screen["y"])


def ivory_share(image, square):
    """How much of a square's middle is the ivory of the white pieces."""
    node = driver.find(key=SQUARE_KEY + square_index(square))[0]
    x, y = window_point(*UiDriver.center(node))
    cell = round(node["width"])
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


def settings(profile, user):
    with sqlite3.connect(profile / "inbe.db", timeout=3) as db:
        return {key: (value, updated) for key, value, updated in
                db.execute("SELECT key,value,updated_at FROM settings WHERE user_id=?", (user,))}


def saved_moves(profile, user):
    record = settings(profile, user).get("cell.chess.computer", ("", 0))[0]
    return record.split("moves=")[1].split() if "moves=" in record else []


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
        driver.press(label="Apps", role="button")
        driver.press(label="Chess", role="button")
        # A new game starts on Medium until another level is chosen.
        driver.wait(label="Hard", role="button")
        assert selected("Medium") and not selected("Easy"), "Medium is not the starting level"
        driver.press(label="Easy", role="button")
        wait_for(lambda: selected("Easy") and not selected("Medium"), "Easy was not chosen")
        driver.press(label="Start", role="button")
        driver.wait(label="Your move")
        driver.wait(label="Chessboard", role="button")
        position = start_position()
        assert board() == position, f"start position: {board()}"
        driver.press(key=SQUARE_KEY + square_index("e2"))
        driver.press(key=SQUARE_KEY + square_index("e4"))
        position = play(position, "e2e4")
        # The computer answers, then it is our move again.
        moves = wait_for(lambda: (found if len(found := saved_moves(profile, user)) == 2 else None),
                         "the computer did not answer e4")
        assert moves[0] == "e2e4", moves
        position = play(position, moves[1])
        wait_for(lambda: board() == position, f"the board does not show {moves}")
        driver.wait(label="Your move")
        driver.wait_idle(frames=3)
        after = capture(window, "after-move")
        assert ivory_share(after, "e4") > 0.2 and ivory_share(after, "e2") < 0.05, \
            f"e4 was not drawn; see {OUTPUT / 'after-move.png'}"
        stored = settings(profile, user)
        assert stored["app_used_chess"][0] == "1" and stored["app_used_chess"][1] > 1, stored.get("app_used_chess")
        assert stored["node_app_slot_0"][0] == "chess", stored.get("node_app_slot_0")
        record = stored["cell.chess.computer"][0]
        assert "level=0;color=w;" in record and len(record.split("moves=")[1].split()) == 2, record
        # Friends need an account; without one the tab says how to sign in.
        driver.press(label="Friends", role="button")
        driver.wait(contains="Sign in")
        log = (OUTPUT / "install.log").read_text()
        assert "frame rejected" not in log and app.poll() is None, log
    finally:
        stop(app)
    # After a restart Chess is still installed and the game continues.
    app, window = launch(profile, "restart")
    try:
        driver.press(label="Apps", role="button")
        driver.press(label="Chess", role="button")
        driver.wait(label="Your move")
        wait_for(lambda: board() == position, f"the saved game was not restored: {board()}")
        log = (OUTPUT / "restart.log").read_text()
        assert "frame rejected" not in log and app.poll() is None, log
    finally:
        stop(app)
print("Chess: offered in More apps, installed, played against the computer and restored after a restart")
