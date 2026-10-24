#!/usr/bin/env python3
"""Arcade from More apps on a private display: Chess inside it, and Chess's replacement.

The first profile installs a local Arcade package (INBE_NODE_APP_FILE), opens
Chess from Arcade's library, plays the computer, queues that nested record for
the profile's sync, goes back to the library and restores the game after a
restart. Local packages have their own trust domain, so this game is Arcade's
own, not an account's earlier Chess games.

Two more profiles use only the node's cached offers. With Arcade offered,
More apps leaves Chess out. An account that installed Chess gets Arcade
installed once, keeps Chess and its saved game while Arcade cannot run here,
and loses only the Chess install once a signed Arcade runs and carries it.
Nothing is published; with --offline the wrapper runs without a network.
"""
import argparse
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile
import time

from ui_driver import UiDriver

assert int(os.environ.get("DISPLAY", ":0").split(":")[-1].split(".")[0]) >= 300
ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("binary", type=Path)
parser.add_argument("package", type=Path, help="an Arcade package, arcade.zx")
parser.add_argument("--offline", action="store_true", help="the node cannot be reached")
args = parser.parse_args()
BINARY = args.binary.resolve(strict=True)
PACKAGE = args.package.resolve(strict=True)
assert PACKAGE.name == "arcade.zx", "INBE_NODE_APP_FILE names the app by its file: arcade.zx"
OUTPUT = ROOT / "build/arcade-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
WIDTH, HEIGHT = 390, 844
SQUARE_KEY = 8010
PIECE_KEY = 8400
START = {"a": "Rook", "b": "Knight", "c": "Bishop", "d": "Queen",
         "e": "King", "f": "Bishop", "g": "Knight", "h": "Rook"}
SAVED_CHESS = "v=1;level=0;color=w;moves=e2e4 e7e5"
driver = UiDriver(OUTPUT / "driver")


def wait_for(predicate, message, timeout=30):
    deadline = time.monotonic() + timeout
    while True:
        value = predicate()
        if value:
            return value
        if time.monotonic() >= deadline:
            driver.tree()
            raise driver._failure(message)
        time.sleep(0.05)


def square_index(square):
    return (8 - int(square[1])) * 8 + ord(square[0]) - ord("a")


def square_name(index):
    return "abcdefgh"[index % 8] + str(8 - index // 8)


def board():
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
    after = dict(pieces)
    after[move[2:4]] = after.pop(move[0:2])
    return after


def button(label):
    """A visible button whose label matches, ignoring case."""
    found = [node for node in driver.tree() if node["kind"] == "button" and node["visible"] and
             node["label"].lower() == label.lower()]
    return found[0] if found else None


def press_button(label):
    node = wait_for(lambda: button(label), f"no {label} button")
    driver.press(key=node["key"])


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def launch(profile, name, local_package=True):
    log_path = OUTPUT / (name + ".log")
    log = log_path.open("w")
    environment = os.environ | {"APP_DATA_ROOT": str(profile)} | driver.environment()
    if local_package:
        environment["INBE_NODE_APP_FILE"] = str(PACKAGE)
    app = subprocess.Popen([str(BINARY)], cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT)
    driver.attach(app, log_path)
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        assert app.poll() is None, log_path.read_text()
        found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                               capture_output=True, text=True)
        if found.returncode == 0 and (profile / "inbe.db").exists():
            window = found.stdout.splitlines()[0]
            subprocess.run(["xdotool", "windowsize", window, str(WIDTH), str(HEIGHT)], check=True)
            subprocess.run(["xdotool", "windowmove", window, "0", "0"], check=True)
            driver.wait_idle(frames=3)
            return app
        time.sleep(0.1)
    stop(app)
    raise AssertionError("Inbe did not map its window")


def settings(profile, user):
    with sqlite3.connect(profile / "inbe.db", timeout=3) as db:
        return {key: value for key, value in
                db.execute("SELECT key,value FROM settings WHERE user_id=?", (user,))}


def prepare(profile, extra):
    """A profile past setup, with no update or catalog read due."""
    app = launch(profile, "first-start-" + profile.name, local_package=False)
    stop(app)
    with sqlite3.connect(profile / "inbe.db") as db:
        user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
        seeded = {"language": "en", "language_system": 0, "language_setup_done": 1, "apps_setup_done": 1,
                  "tutorial_seen": 1, "habits_guide_seen": 1, "lumi_guides_seen": 127, "launcher_guide_seen": 1,
                  "package_updates_allowed": 0, "apps_last_update_check": 1900000000,
                  "node_apps_checked_at": int(time.time())} | extra
        for key, value in seeded.items():
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                       "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user, key, str(value)))
    return user


def arcade_record_entry(profile, user):
    """Chess's saved game inside Arcade, keyed to its verified nested identity."""
    for key, value in settings(profile, user).items():
        if re.fullmatch(r"nested\.[0-9a-f]{64}\.computer", key):
            return key, value
    return "", ""


def queued_entity(profile, key):
    with sqlite3.connect(profile / "inbe.db", timeout=3) as db:
        row = db.execute("SELECT entity_type FROM sync_outbox WHERE entity_id=?",
                         (key,)).fetchone()
        return row[0] if row else ""


def saved_moves(profile, user):
    _, record = arcade_record_entry(profile, user)
    return record.split("moves=")[1].split() if "moves=" in record else []


def library_shows_chess():
    driver.wait(label="Arcade")
    return wait_for(lambda: button("Chess"), "Arcade's library has no Chess card")


with tempfile.TemporaryDirectory(prefix="inbe-arcade-") as directory:
    # Arcade from More apps, with Chess inside it.
    profile = Path(directory) / "arcade"
    profile.mkdir()
    user = prepare(profile, {})
    assert settings(profile, user).get("app_used_arcade") is None, "Arcade was installed for a new profile"
    app = launch(profile, "install")
    try:
        driver.press(label="Apps", role="button")
        press_button("arcade")
        library_shows_chess()
        press_button("Chess")
        driver.wait(label="Hard", role="button")
        driver.press(label="Easy", role="button")
        driver.press(label="Start", role="button")
        driver.wait(label="Your move")
        driver.wait_gone(label="Apps", role="button")
        position = start_position()
        wait_for(lambda: board() == position, f"start position: {board()}")
        driver.press(key=SQUARE_KEY + square_index("e2"))
        driver.press(key=SQUARE_KEY + square_index("e4"))
        moves = wait_for(lambda: (found if len(found := saved_moves(profile, user)) == 2 else None),
                         "the computer did not answer e4 inside Arcade")
        assert moves[0] == "e2e4", moves
        position = play(play(position, "e2e4"), moves[1])
        wait_for(lambda: board() == position, f"the board does not show {moves}")
        stored = settings(profile, user)
        assert stored.get("app_used_arcade") == "1", stored.get("app_used_arcade")
        assert stored.get("node_app_slot_0") == "arcade", stored.get("node_app_slot_0")
        record_key, _ = arcade_record_entry(profile, user)
        assert record_key, "Arcade's Chess progress is not in the profile's nested records"
        assert queued_entity(profile, record_key) == "app_record", "Arcade progress was not queued for profile sync"
        assert "cell.chess.computer" not in stored, "a local Arcade wrote an account's Chess records"
        # Back leaves Chess for Arcade's library.
        press_button("Back")
        library_shows_chess()
        log = (OUTPUT / "install.log").read_text()
        assert "frame rejected" not in log and app.poll() is None, log
    finally:
        stop(app)
    app = launch(profile, "restart")
    try:
        driver.press(label="Apps", role="button")
        press_button("arcade")
        library_shows_chess()
        press_button("Chess")
        driver.wait(label="Your move")
        wait_for(lambda: board() == position, f"the saved game was not restored: {board()}")
        log = (OUTPUT / "restart.log").read_text()
        assert "frame rejected" not in log and app.poll() is None, log
    finally:
        stop(app)

    # With Arcade offered, More apps leaves Chess out.
    profile = Path(directory) / "offers"
    profile.mkdir()
    user = prepare(profile, {"node_apps_offers": "chess|Chess\narcade|Arcade",
                             "node_app_size_chess": 1517150, "node_app_size_arcade": 4194304})
    app = launch(profile, "offers", local_package=False)
    try:
        driver.press(label="Apps", role="button")
        wait_for(lambda: button("Arcade"), "More apps does not offer Arcade")
        assert button("Chess") is None, "More apps still offers Chess next to Arcade"
    finally:
        stop(app)

    # An account that installed Chess is not given Arcade: More apps offers
    # it with the download symbol, and Chess and its game stay.
    profile = Path(directory) / "replace"
    profile.mkdir()
    user = prepare(profile, {"node_apps_offers": "arcade|Arcade", "node_app_size_arcade": 4194304,
                             "app_used_chess": 1, "cell.chess.computer": SAVED_CHESS})
    app = launch(profile, "replace", local_package=False)
    try:
        driver.press(label="Apps", role="button")
        card = wait_for(lambda: button("Arcade"), "More apps does not offer Arcade to an account with Chess")
        corner = [node for node in driver.tree() if node["label"] == "Download" and
                  card["x"] <= node["x"] and node["x"] + node["width"] <= card["x"] + card["width"] + 49 and
                  card["y"] <= node["y"] and node["y"] + node["height"] <= card["y"] + card["height"]]
        assert len(corner) == 1, "Arcade's card has no download symbol"
        assert corner[0]["x"] + corner[0]["width"] / 2 > card["x"] + card["width"] / 2, \
            "Arcade's download symbol is not at the end of its row"
        driver.wait_idle(frames=30)
        stored = settings(profile, user)
        assert stored.get("app_used_arcade") != "1", "Arcade was installed for an account with Chess"
        assert stored.get("app_used_chess") == "1", "Chess left before Arcade was installed"
        assert stored.get("cell.chess.computer") == SAVED_CHESS, "Chess's saved game changed"
        log = (OUTPUT / "replace.log").read_text()
        assert app.poll() is None, log
    finally:
        stop(app)
print("Arcade: installed from More apps, Chess played inside it and restored after a restart; "
      "Chess left out of More apps next to Arcade, and an account with Chess is offered Arcade to download")
