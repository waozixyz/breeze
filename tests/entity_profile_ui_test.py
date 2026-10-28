"""Entity Profile preserves the host account, picture and inline Dew on a private display."""
import contextlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

from ui_driver import UiDriver

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/entity-profile-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
BINARY = Path(sys.argv[1]).resolve()
FRIENDS_ONLY = "--friends-only" in sys.argv[2:]
IDENTITY_ONLY = "--identity-only" in sys.argv[2:]
DESKTOP_ENV = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS",
               "SESSION_MANAGER", "GDK_DISPLAY")
assert all(not os.environ.get(key) for key in DESKTOP_ENV), "Inherited desktop environment"


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


with contextlib.ExitStack() as stack:
    profile = Path(stack.enter_context(tempfile.TemporaryDirectory(dir=OUTPUT, prefix="profile-")))
    driver = UiDriver(profile / "driver")
    environment = {key: value for key, value in os.environ.items() if key not in DESKTOP_ENV}
    environment.update(driver.environment())
    environment.update(APP_DATA_ROOT=str(profile), INBE_SCREENSHOT_DATA_ROOT=str(profile),
                       APP_NO_TRAY="1", APP_SHOT_WINDOW="1", YUE_DESKTOP_RECOVERY="0",
                       SDL_VIDEODRIVER="x11", SDL_AUDIODRIVER="dummy", LIBGL_ALWAYS_SOFTWARE="1",
                       https_proxy="http://127.0.0.1:9", http_proxy="http://127.0.0.1:9", NO_PROXY="")
    display_log = stack.enter_context((OUTPUT / "display.log").open("w"))
    display = subprocess.Popen(["Xvfb", "-noreset", "-displayfd", "1", "-screen", "0", "1100x900x24",
                                "-nolisten", "tcp"], env=environment,
                               stdout=subprocess.PIPE, stderr=display_log)
    stack.callback(stop, display)
    number = display.stdout.readline().decode().strip()
    display.stdout.close()
    assert number.isdecimal(), "Private display did not start"
    environment["DISPLAY"] = ":" + number

    def query(sql):
        uri = (profile / "inbe.db").as_uri() + "?mode=ro"
        with contextlib.closing(sqlite3.connect(uri, uri=True, timeout=3)) as database:
            return database.execute(sql).fetchall()

    def credentials():
        return query("SELECT user_id,key,value FROM settings WHERE key IN "
                     "('sync_public_id','sync_public_key','sync_private_key') ORDER BY user_id,key")

    @contextlib.contextmanager
    def application(name, seed=False):
        command = [str(BINARY)]
        if seed:
            command += ["--screenshot", str(OUTPUT / "initial.png"),
                        "--screenshot-scene", "navigation_profile", "--screenshot-width", "900",
                        "--screenshot-height", "720"]
        log_path = OUTPUT / (name + ".log")
        with log_path.open("w") as log:
            process = subprocess.Popen(command, cwd=ROOT, env=environment,
                                       stdout=log, stderr=subprocess.STDOUT)
            driver.attach(process, log_path)
            try:
                driver.wait(label="Apps", role="button")
                yield process
                assert "frame rejected" not in log_path.read_text()
                assert process.poll() is None, "Entity test app exited unexpectedly"
            finally:
                stop(process)

    def open_profile():
        driver.press(label="Apps", role="button")
        driver.wait(label="Pinned")
        account = driver.wait(focus_id=6792, role="button")
        settings = driver.wait(label="Settings", role="button")
        assert account["x"] + account["width"] <= settings["x"], "Profile is not left of Settings"
        driver.press(focus_id=6792, role="button")
        driver.wait(label="Change picture", role="button")
        if not FRIENDS_ONLY and not IDENTITY_ONLY:
            driver.wait(label="Dew balance", role="text")
            assert not driver.find(label="Dew balance", role="button"), "Dew is still a separate shortcut"
        assert not driver.find(label="Name", role="text_field"), "Removed Name field is visible"
        assert not driver.find(label="Intention", role="text_field"), "Removed Intention field is visible"
        assert len(driver.find(role="title_bar", visible=True)) == 1

    with application("seed", seed=True):
        before = credentials()
        identities = {value for _, key, value in before if key == "sync_public_id" and value}
        assert len(identities) == 1 and len(next(iter(identities))) == 64, "Fixture account missing"
        owner = next(iter(identities))
    with sqlite3.connect(profile / "inbe.db") as database:
        user = database.execute("SELECT user_id FROM settings WHERE key='sync_public_id' "
                                "AND value=? LIMIT 1", (owner,)).fetchone()[0]
        # The navigation preview disables sync. Enable its fixture account so
        # the shared Profile can show Dew; the proxy above keeps it offline.
        for key, value in (("profile_display_name", "Existing desktop name"),
                           ("profile_intention", "Existing private intention"),
                           ("sync_enabled", "1"),
                           ("sync_server_url", "https://api.waozi.xyz")):
            database.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,2) "
                             "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value,"
                             "updated_at=excluded.updated_at", (user, key, value))
    shared = Path(environment["ENTITY_DATA"]) / "profiles" / owner / "profile.json"
    if shared.exists():
        saved = json.loads(shared.read_text())
        saved.update(name="Existing desktop name", intention="Existing private intention")
        shared.write_text(json.dumps(saved) + "\n")
    if not FRIENDS_ONLY:
        with application("edit"):
            open_profile()
            driver.press(label="Public ID", role="button")
            driver.wait(label=owner, role="text")
            driver.press(label=owner, role="button")
            copied = subprocess.check_output(["xclip", "-o", "-selection", "clipboard"],
                                             env=environment, text=True, timeout=5)
            assert copied == owner, "Entity's public ID did not reach the system clipboard"
            assert display.poll() is None and Path(f"/proc/{display.pid}/exe").resolve().name == "Xvfb"
            window = subprocess.check_output(["xdotool", "search", "--onlyvisible", "--pid", str(driver.process.pid)],
                                             env=environment, text=True, timeout=5).splitlines()[0]
            assert subprocess.check_output(["xdotool", "getwindowpid", window],
                                           env=environment, text=True, timeout=5).strip() == str(driver.process.pid)
            subprocess.run(["import", "-window", window, str(OUTPUT / "public-id.png")], env=environment, check=True)
            driver.press(label="Done", role="button")
            if IDENTITY_ONLY:
                assert credentials() == before, "Showing and copying an ID changed account keys"
                print("Entity public ID: full dialog, QR composition, native clipboard and account preservation passed")
                sys.exit(0)
            driver.wait(label="Manage data", role="button")
            for label in ("Today", "Active days", "Sessions"):
                driver.wait(label=label, role="text", visible=False)
            assert not driver.find(label="Progress", role="button"), "Activity still uses a separate row"
            driver.press(label="Change picture", role="button")
            driver.wait(focus_id=76401, role="button")
            driver.press(focus_id=76401, role="button")
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                if shared.exists() and json.loads(shared.read_text()).get("picture") == 1:
                    break
                time.sleep(.05)
            document = json.loads(shared.read_text())
            assert document["picture"] == 1, "Picture edit was not saved"
            assert document["name"] == "Existing desktop name", "Hidden name was changed"
            assert document["intention"] == "Existing private intention", "Hidden intention was changed"
            assert document["owner_id"] == owner, "Entity used a different account"
            assert credentials() == before, "Editing Entity changed Inbe account keys"
            assert not (Path(environment["ENTITY_DATA"]) / "account.key").exists(), "Entity made another account"
            driver.wait(label="Dew balance", role="text")
        with application("restart"):
            open_profile()
            driver.press(label="Change picture", role="button")
            selected = driver.wait(focus_id=76401, role="button")
            assert selected.get("selected"), "Picture edit was lost after restart"
            assert credentials() == before, "Restart changed Inbe account keys"
            assert json.loads(shared.read_text())["owner_id"] == owner

    with sqlite3.connect(profile / "inbe.db") as database:
        user = database.execute("SELECT user_id FROM settings WHERE key='sync_public_id' "
                                "AND length(value)=64 LIMIT 1").fetchone()[0]
        friends = {"friends": [{"user_id_hash": "a" * 64, "alias": "willow", "profile_icon": 55},
                               {"user_id_hash": "b" * 64, "alias": "river", "profile_icon": 1},
                               {"user_id_hash": "c" * 64, "alias": "fern"}]}
        database.execute("INSERT INTO social_snapshots(user_id,kind,json,updated_at) VALUES(?,?,?,2) "
                         "ON CONFLICT(user_id,kind) DO UPDATE SET json=excluded.json",
                         (user, "friends.list", json.dumps(friends)))
    with application("friends") as process:
        open_profile()
        driver.press(label="Friends", role="button")
        field = driver.wait(focus_id=810, role="text_field")
        driver.press(focus_id=810, role="text_field")
        driver.type("@soft_keyboard_friend")
        assert driver.wait(focus_id=810, role="text_field")["value"] == "@soft_keyboard_friend", "Friends discarded typed text"
        driver.key("backspace")
        assert driver.wait(focus_id=810, role="text_field")["value"] == "@soft_keyboard_frien", "Friends discarded edits"
        assert not [node for node in driver.find(label="Friends", role="text", visible=True)
                    if node["y"] > 80], "Duplicate Friends heading remains in the page"
        rows = [driver.wait(label="@" + name, role="button") for name in ("willow", "river", "fern")]
        for row in rows:
            picture = driver.wait(label=row["label"], role="image")
            assert picture["width"] >= 40 and picture["height"] >= 40, picture
            assert picture["x"] + picture["width"] < row["x"], "Picture overlaps friend name"
        for first, second in zip(rows, rows[1:]):
            assert second["y"] - first["y"] >= 64, "Friend rows lack spacing"
        assert credentials() == before, "Friends changed account keys"
        destination = os.environ.get("BREEZE_FRIENDS_CAPTURE")
        if destination:
            assert display.poll() is None
            assert Path(f"/proc/{display.pid}/exe").resolve().name == "Xvfb"
            assert "-displayfd" in display.args and number.isdecimal()
            window = subprocess.check_output(["xdotool", "search", "--onlyvisible", "--pid", str(process.pid)],
                                             env=environment, text=True).splitlines()[0]
            assert subprocess.check_output(["xdotool", "getwindowpid", window], env=environment,
                                           text=True).strip() == str(process.pid)
            output = Path(destination)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.with_suffix(".source.txt").write_text(repr((display.pid, display.args, number, process.pid, window)))
            subprocess.run(["import", "-window", window, str(output)], env=environment, check=True)

    with sqlite3.connect(profile / "inbe.db") as database:
        user = database.execute("SELECT user_id FROM settings WHERE key='sync_public_id' "
                                "AND length(value)=64 LIMIT 1").fetchone()[0]
        choices = {"enabled_apps": "2", "app_used_habits": "1", "app_used_lists": "0",
                   "app_used_practices": "0", "app_used_diary": "0", "app_used_lumi": "0",
                   "app_used_leaderboard": "0", "node_app_slot_0": "photos",
                   "app_used_photos": "1", "package_updates_allowed": "0"}
        for key, value in choices.items():
            database.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,2) "
                             "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value,"
                             "updated_at=excluded.updated_at",
                             (user, key, value))
    if not FRIENDS_ONLY:
        with application("about-installed"):
            driver.press(label="Apps", role="button")
            driver.press(label="Settings", role="button")
            driver.press(label="About", role="button")
            driver.wait(label="App versions", role="text")
            labels = [node["label"] for node in driver.tree() if node["visible"]]
            versions = [label for label in labels if " · " in label]
            assert any(label.startswith("Habits · ") for label in versions), versions
            assert not any(label.startswith(("Photos · ", "Lists · ", "Practice · ",
                                             "Diary · ", "Lumi · ", "Leaderboard · "))
                           for label in versions), versions
            assert "Show beta apps" not in labels, "Removed beta setting is still visible"

print("Friends profile pictures, legacy choices, fallback picture, spaced rows and account preservation passed" if FRIENDS_ONLY else "Entity desktop: inline Dew/Activity, preserved hidden fields, host account, saved picture, restart and installed-only About passed")
