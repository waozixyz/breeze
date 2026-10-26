#!/usr/bin/env python3
"""Arcade from More apps on a private display: Shovey inside it, and Chess's replacement.

The first profile installs a local Arcade package (INBE_NODE_APP_FILE) through
Apps' download dialog, opens Shovey's Classic from Arcade's library, moves
Shovey, queues that nested record for the profile's sync, goes back to the
library and finds Shovey where it was left after a restart. Local packages
have their own trust domain, so this progress is Arcade's own.

Two more profiles use only the node's cached offers. With Arcade offered,
More apps leaves Chess out. An account that installed Chess gets Arcade
installed once, keeps Chess and its saved game while Arcade cannot run here,
and loses only the Chess install once a signed Arcade runs and carries it.
Nothing is published; with --offline the wrapper runs without a network.
"""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile
import threading
import time

from ui_driver import UiDriver

assert int(os.environ.get("DISPLAY", ":0").split(":")[-1].split(".")[0]) >= 300
ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("binary", type=Path)
parser.add_argument("package", type=Path, help="an Arcade package, arcade.zx")
parser.add_argument("--offline", action="store_true", help="the node cannot be reached")
parser.add_argument("--downloads-only", action="store_true",
                    help="Check the rounded library, add-on downloads and offline games")
args = parser.parse_args()
if args.offline:
    # A new network namespace starts with loopback down; the download check
    # serves its games on it.
    import fcntl, socket, struct
    try:
        fcntl.ioctl(socket.socket(), 0x8914, struct.pack("16sH14s", b"lo", 0x49, b""))
    except OSError:
        pass
BINARY = args.binary.resolve(strict=True)
PACKAGE = args.package.resolve(strict=True)
assert PACKAGE.name == "arcade.zx", "INBE_NODE_APP_FILE names the app by its file: arcade.zx"
OUTPUT = ROOT / "build/arcade-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
WIDTH, HEIGHT = 390, 844
# A tap on the cell beside Shovey moves him there; portrait steps are left,
# up, right and down on the screen.
STEPS = ((-1, 0), (0, -1), (1, 0), (0, 1))
SAVED_CHESS = "v=1;level=0;color=w;moves=e2e4 e7e5"
driver = UiDriver(OUTPUT / "driver")
local_game_origin = ""


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
        if local_game_origin:
            environment["INBE_LOCAL_PACKAGE_ORIGIN"] = local_game_origin
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


def arcade_records(profile, user):
    """Shovey's records inside Arcade, keyed to its verified nested identity."""
    return {key: value for key, value in settings(profile, user).items()
            if re.fullmatch(r"(?:local\.)?nested\.[0-9a-f]{64}\.[a-z0-9._-]+", key)}


def queued_entity(profile, key):
    with sqlite3.connect(profile / "inbe.db", timeout=3) as db:
        row = db.execute("SELECT entity_type FROM sync_outbox WHERE entity_id=?",
                         (key,)).fetchone()
        return row[0] if row else ""


def library_shows_shovey():
    """Arcade's cover: Shovey's Classic card and its Play button."""
    driver.wait(label="Classic", role="text", timeout=30)
    return wait_for(lambda: button("Play"), "Arcade's library has no Shovey card")


def open_arcade():
    """Arcade from Apps. Before it is on the device, Apps asks first: Download
    beside Cancel confirms, then Open once it is ready."""
    driver.press(label="Apps", role="button")
    press_button("arcade")
    deadline = time.monotonic() + 60
    while driver.find(label="Find an app", role="text_field", visible=True):
        assert time.monotonic() < deadline, "Arcade did not open: " + ", ".join(driver.labels())
        cancel = driver.find(label="Cancel", role="button", visible=True)
        if cancel:
            downloads = driver.find(label="Download", role="button", visible=True)
            nearest = min(range(len(downloads)), key=lambda at: abs(downloads[at]["y"] - cancel[0]["y"]))
            driver.press(label="Download", role="button", visible=True, index=nearest)
        elif driver.find(label="Ready to open", role="text", visible=True):
            driver.press(label="Open", role="button", visible=True)
        time.sleep(0.1)


def play_classic():
    """Play on the cover opens the level; Shovey's first questions are
    answered as a player would: no level downloads, swipe and tap."""
    press_button("Play")
    deadline = time.monotonic() + 30
    while not driver.find(contains="Level 1 / ", role="text", visible=True) or \
            driver.find(label="Not now", role="button", visible=True) or \
            driver.find(label="How do you want to move?", role="text", visible=True):
        assert time.monotonic() < deadline, "Shovey's level did not open: " + ", ".join(driver.labels())
        if driver.find(label="Not now", role="button", visible=True):
            driver.press(label="Not now", role="button")
        elif driver.find(label="How do you want to move?", role="text", visible=True):
            driver.press(contains="Swipe")
        time.sleep(0.1)


def shovey_cell():
    found = [node for node in driver.tree() if node["label"] == "Shovey" and node["kind"] == "image" and
             node["visible"]]
    return (round(found[0]["x"]), round(found[0]["y"])) if found else None


def move_shovey():
    """Tap beside Shovey until he moves; return where he stands."""
    start = wait_for(shovey_cell, "Shovey is not on the board")
    me = [node for node in driver.tree() if node["label"] == "Shovey" and node["kind"] == "image"][0]
    for dx, dy in STEPS:
        x, y = me["x"] + me["width"] * (0.5 + dx), me["y"] + me["height"] * (0.5 + dy)
        for down in (False, True, False):
            driver.pointer(x, y, down=down)
            driver.wait_idle(frames=1, timeout=1)
        driver.release_pointer()
        driver.wait_idle(frames=12, timeout=4)
        now = shovey_cell()
        if now and now != start:
            return now
    raise AssertionError("Shovey did not move from " + str(start))


def check_download_library():
    global local_game_origin
    metadata = json.loads(PACKAGE.with_suffix('.json').read_text())
    entries = {entry['sha256']: entry for entry in metadata['children']}
    # The library art downloads with Arcade; only games wait for consent.
    art = (metadata.get('art') or {}).get('sha256', '')
    requested = []
    offline = False

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            digest = self.path.removeprefix('/api/v2/packages/inbe.arcade/').removesuffix('.zx')
            if digest != art:
                requested.append(digest)
            if offline or (digest not in entries and digest != art):
                self.send_error(503)
                return
            data = (PACKAGE.parent / 'arcade.games' / (digest + '.zx')).read_bytes()
            self.send_response(200)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    def reveal(label):
        driver.pointer(WIDTH / 2, HEIGHT / 2, wheel=80)
        driver.wait_idle(frames=3)
        for _ in range(15):
            if node := button(label):
                return node
            driver.pointer(WIDTH / 2, HEIGHT / 2, wheel=-8)
            driver.wait_idle(frames=3)
        raise driver._failure('Cover is not reachable: ' + label)

    def download():
        actions = driver.find(label='Download', role='button', visible=True)
        action = max(actions, key=lambda node: node['width'])
        driver.press(key=action['key'])

    server = HTTPServer(('127.0.0.1', 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    local_game_origin = 'http://127.0.0.1:' + str(server.server_port)
    try:
        with tempfile.TemporaryDirectory(prefix='inbe-arcade-downloads-', dir=OUTPUT) as directory:
            profile = Path(directory)
            user = prepare(profile, {})
            app = launch(profile, 'downloads')
            try:
                open_arcade()
                reveal('Shovey')
                assert not button('Play') and not button('Next'), 'Arcade must use clickable covers'
                assert not driver.find(label='Monkey') and not driver.find(label='Chess')
                assert not requested, 'The library must not predownload games'
                driver.press(key=reveal('Shovey Editor')['key'])
                driver.wait(contains='Shovey (required)', role='text')
                driver.press(label='Cancel', role='button')
                assert not requested, 'Cancel must not download games'
                driver.press(key=reveal('Shovey Editor')['key'])
                driver.wait(label='Download', role='button')
                download()
                driver.wait(label='New level', role='text', timeout=60)
                assert len(requested) == 2, 'The editor must download itself and its required game'
                driver.press(label='Back', role='button')
                driver.press(key=reveal('Shovey')['key'])
                deadline = time.monotonic() + 30
                while True:
                    assert time.monotonic() < deadline, driver.text()
                    if driver.find(label='Not now', role='button', visible=True):
                        driver.press(label='Not now', role='button')
                    elif driver.find(label='How do you want to move?', role='text', visible=True):
                        driver.press(contains='Swipe')
                    elif driver.find(label='Restart', role='button', visible=True):
                        break
                    time.sleep(.05)
                saved_cell = move_shovey()
                record = wait_for(lambda: next(((key, value) for key, value in
                    arcade_records(profile, user).items() if key.endswith('.local.campaign')), None),
                    'Shovey did not keep its local campaign')
                assert record[0].startswith('local.nested.')
                assert not queued_entity(profile, record[0]), 'Local play must stay on the device'
                backs = driver.find(label='Back', role='button', visible=True)
                driver.press(key=backs[-1]['key'])
                driver.press(key=reveal('Apfelwurm')['key'])
                driver.wait(label='Download', role='button')
                download()
                # Its cover is the title: Apfelwurm asks once how to move, then plays.
                driver.wait(label='How do you want to move?', role='text', timeout=60)
                driver.press(label='Swipe', role='button')
                driver.wait(label='Pause', role='button')
                assert len(requested) == 3, 'Each game must download once'
            finally:
                stop(app)
            offline = True
            before = list(requested)
            app = launch(profile, 'downloads-offline')
            try:
                open_arcade()
                driver.press(key=reveal('Shovey')['key'])
                driver.wait(label='Restart', role='button')
                wait_for(lambda: shovey_cell() == saved_cell, 'Shovey did not restore its saved position')
                assert arcade_records(profile, user)[record[0]] == record[1]
                assert requested == before, 'Cached games must open without a download'
            finally:
                stop(app)
    finally:
        server.shutdown()
        worker.join(timeout=5)
        server.server_close()
        local_game_origin = ''
    print('Inbe Arcade: rounded covers, add-on consent/cancel, shared assets, all game downloads, private saves and offline reopen passed')


if args.downloads_only:
    check_download_library()
    raise SystemExit(0)


with tempfile.TemporaryDirectory(prefix="inbe-arcade-") as directory:
    # Arcade from More apps, with Shovey inside it.
    profile = Path(directory) / "arcade"
    profile.mkdir()
    user = prepare(profile, {})
    assert settings(profile, user).get("app_used_arcade") is None, "Arcade was installed for a new profile"
    app = launch(profile, "install")
    try:
        open_arcade()
        library_shows_shovey()
        play_classic()
        driver.wait_gone(label="Apps", role="button")
        cell = move_shovey()
        records = wait_for(lambda: {key: value for key, value in arcade_records(profile, user).items()
                                    if key.endswith(".campaign")} or None,
                           "Shovey's progress is not in the profile's nested records")
        stored = settings(profile, user)
        assert stored.get("app_used_arcade") == "1", stored.get("app_used_arcade")
        assert stored.get("node_app_slot_0") == "arcade", stored.get("node_app_slot_0")
        record_key = next(iter(records))
        wait_for(lambda: queued_entity(profile, record_key) == "app_record",
                 "Arcade progress was not queued for profile sync")
        # Shovey's own Back, below Inbe's title bar, leaves the level for
        # Arcade's library.
        backs = [node for node in driver.tree() if node["kind"] == "button" and node["visible"] and
                 node["label"] == "Back"]
        driver.press(key=max(backs, key=lambda node: node["y"])["key"])
        library_shows_shovey()
        log = (OUTPUT / "install.log").read_text()
        assert "frame rejected" not in log and app.poll() is None, log
    finally:
        stop(app)
    app = launch(profile, "restart")
    try:
        open_arcade()
        library_shows_shovey()
        play_classic()
        wait_for(lambda: shovey_cell() == cell, f"Shovey was not restored where he was left: {shovey_cell()}")
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
print("Arcade: installed from More apps, Shovey played inside it and restored after a restart; "
      "Chess left out of More apps next to Arcade, and an account with Chess is offered Arcade to download")
