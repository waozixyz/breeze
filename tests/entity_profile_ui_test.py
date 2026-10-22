"""Entity edits reuse Inbe's account and survive restart on a private display."""
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
                       SDL_VIDEODRIVER="x11", SDL_AUDIODRIVER="dummy", LIBGL_ALWAYS_SOFTWARE="1")
    display_log = stack.enter_context((OUTPUT / "display.log").open("w"))
    display = subprocess.Popen(["Xvfb", "-displayfd", "1", "-screen", "0", "1100x900x24",
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
        driver.wait(label="Name", role="text_field")
        assert len(driver.find(role="title_bar", visible=True)) == 1

    with application("edit", seed=True) as process:
        before = credentials()
        identities = {value for _, key, value in before if key == "sync_public_id" and value}
        assert len(identities) == 1 and len(next(iter(identities))) == 64, "Fixture account missing"
        owner = next(iter(identities))
        open_profile()
        driver.press(label="Dew balance", role="button")
        driver.wait(label="Dew balance", role="title_bar")
        driver.press(label="Back", role="button")
        driver.wait(label="Name", role="text_field")
        driver.press(label="Name", role="text_field")
        driver.key("a", control=True)
        driver.type("Entity desktop fixture")
        driver.key("enter")
        shared = Path(environment["ENTITY_DATA"]) / "profiles" / owner / "profile.json"
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if shared.exists() and json.loads(shared.read_text()).get("name") == "Entity desktop fixture":
                break
            time.sleep(.05)
        document = json.loads(shared.read_text())
        assert document["name"] == "Entity desktop fixture", "Profile edit was not saved"
        assert document["owner_id"] == owner, "Entity used a different account"
        assert credentials() == before, "Editing Entity changed Inbe account keys"
        assert not (Path(environment["ENTITY_DATA"]) / "account.key").exists(), "Entity made another account"
        window = subprocess.check_output(["xdotool", "search", "--onlyvisible", "--pid", str(process.pid)],
                                         env=environment, text=True).splitlines()[0]
        subprocess.run(["import", "-window", window, str(OUTPUT / "profile.png")],
                       env=environment, check=True)

    with application("restart"):
        open_profile()
        field = driver.wait(label="Name", role="text_field")
        assert field.get("value") == "Entity desktop fixture", "Profile edit was lost after restart"
        assert credentials() == before, "Restart changed Inbe account keys"
        assert json.loads(shared.read_text())["owner_id"] == owner

print("Entity desktop: profile editing, existing host account, saved name and restart passed")
