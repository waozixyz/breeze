#!/usr/bin/env python3
"""Back from navigation Data exits once; Profile Data returns to its hub, whose Back returns to Apps.
Data lives in Profile, so the Settings hub no longer lists it.

Titles, buttons and the navigation are found in the app's widget tree
through Kryon's test driver; routes are read from the app's debug log."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from ui_driver import UiDriver

assert int(os.environ.get("DISPLAY", ":0").split(":")[-1].split(".")[0]) >= 300
root = Path(__file__).resolve().parents[1]
binary = Path(sys.argv[1]).resolve()
output = root / "build/data-back-ui-test"
output.mkdir(parents=True, exist_ok=True)
driver = UiDriver(output / "driver")
# The navigation's buttons share one focus group: the rail on wide windows,
# the dock on phones.
NAVIGATION = 6600


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


def switches(logfile, baseline):
    return re.findall(r"ROUTE switch frame=\d+ screen=(\d+)->(\d+)", logfile.read_text()[baseline:])


def title(expected):
    """Waits for the title bar to name the screen, then for it to settle."""
    driver.wait(label=expected, role="title_bar")
    driver.wait_idle(frames=3)


def settings_lists_data():
    return [node["label"] for node in driver.tree()
            if node["visible"] and re.search(r"\bdata\b", node["label"], re.IGNORECASE)]


def open_practice(name):
    shortcuts = driver.find(label="Practice", role="button", focus_id=NAVIGATION, visible=True)
    assert len(shortcuts) == 1, f"{name}: the Practice navigation shortcut is missing or ambiguous: {shortcuts}"
    driver.press(label="Practice", role="button", focus_id=NAVIGATION)
    # An unselected favorite can be partially offscreen in the scrolling
    # dock. Selecting it must then reveal the whole label.
    shortcut = wait_for(lambda: next(iter(node for node in driver.find(
        label="Practice", role="button", focus_id=NAVIGATION, visible=True) if node["selected"]), None),
        f"{name}: selecting Practice did not select its navigation shortcut")
    driver.wait_idle(frames=3)
    shortcut = driver.find(key=shortcut["key"], visible=True)[0]
    whole = (shortcut["visible_x"], shortcut["visible_y"], shortcut["visible_width"], shortcut["visible_height"]) == \
        (shortcut["x"], shortcut["y"], shortcut["width"], shortcut["height"])
    assert whole, f"{name}: selecting Practice did not reveal its complete navigation label: {shortcut}"


def profile_focus_and_activity(name, window):
    field = driver.wait(label="Name", role="text_field")
    driver.press(key=field["key"], role="text_field")
    driver.pointer(field["x"] + field["width"] / 2,
                   field["y"] + field["height"] / 2, wheel=-8)
    driver.wait_idle(frames=4)
    scrolled = driver.find(key=field["key"])[0]
    assert scrolled["y"] < field["y"] - 80, (name, "focused input prevented scrolling", field, scrolled)
    assert scrolled["focused"], (name, "scrolling discarded input focus", scrolled)
    for _ in range(8):
        later = driver.find(key=field["key"])[0]
        assert abs(later["y"] - scrolled["y"]) < 1, (name, "focused input snapped the view back", scrolled, later)
    # Reveal Activity through the same scroll path, keeping the field focused.
    for _ in range(15):
        activity = driver.find(label="Activity", role="button", visible=True)
        if activity and activity[0]["visible_height"] == activity[0]["height"]:
            break
        driver.pointer(field["x"] + field["width"] / 2, 300, wheel=2)
        driver.wait_idle(frames=3)
    driver.press(label="Activity", role="button")
    title("Activity")
    buttons = {node["label"] for node in driver.find(role="button")}
    repeated = buttons & {"Activity", "Data", "Friends", "Telegram", "Achievements", "Account", "Connect Account"}
    assert not repeated, (name, "Activity repeats Profile destinations", repeated)
    assert "Days active" in driver.text() or "Active days" in driver.text(), (name, driver.text())
    subprocess.run(["import", "-window", window, str(output / f"{name}-activity.png")], check=True)
    driver.press(label="Back", role="button")
    title("Profile")
    for _ in range(15):
        achievements = driver.find(label="Achievements", role="button", visible=True)
        if achievements and achievements[0]["visible_height"] == achievements[0]["height"]:
            break
        driver.pointer(field["x"] + field["width"] / 2, 300, wheel=-2)
        driver.wait_idle(frames=3)
    driver.press(label="Achievements", role="button")
    driver.wait(label="Achievements", role="text")
    assert len(driver.find(label="Back", role="button")) == 1, (name, "duplicate embedded Back controls")
    driver.wait_idle(frames=4)
    subprocess.run(["import", "-window", window, str(output / f"{name}-achievements.png")], check=True)
    driver.press(label="Back", role="button")
    title("Profile")


for scene in ("data_from_navigation", "profile_data", "settings_overview"):
    sizes = ((360, 740),) if scene == "settings_overview" else ((900, 720), (360, 740))
    for width, height in sizes:
        name = f"{scene}-{width}"
        logfile = output / f"{name}.log"
        initial = output / f"{name}.png"
        env = os.environ.copy()
        env.update(APP_SHOT_WINDOW="1", APP_NO_TRAY="1", INBE_DEBUG_ROUTE="1",
                   SDL_VIDEODRIVER="x11", YUE_DESKTOP_RECOVERY="0")
        env.update(driver.environment())
        with logfile.open("w") as log:
            app = subprocess.Popen([str(binary), "--screenshot", str(initial),
                "--bundle", str(root / "build/inbe-full.zib"),
                "--screenshot-scene", scene, "--screenshot-width", str(width),
                "--screenshot-height", str(height), "--screenshot-ui-scale", "10"],
                cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
            driver.attach(app, logfile)
            try:
                deadline = time.monotonic() + 30
                window = ""
                while time.monotonic() < deadline:
                    assert app.poll() is None, logfile.read_text()[-2000:]
                    found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                        capture_output=True, text=True)
                    database = Path('/tmp') / f'inbe-screenshot-{app.pid}' / 'inbe.db'
                    if found.returncode == 0 and found.stdout.strip() and database.is_file():
                        window = found.stdout.splitlines()[0]
                        break
                    time.sleep(0.1)
                assert window, "private child did not become ready"
                if scene == "settings_overview":
                    title("Settings")
                    driver.wait(label="Appearance", role="button")
                    assert not settings_lists_data(), f"Settings still lists Data: {settings_lists_data()}"
                    continue
                title("Data")
                baseline = len(logfile.read_text())
                driver.press(label="Back", role="button")
                if scene == "data_from_navigation":
                    wait_for(lambda: switches(logfile, baseline), f"{name}: Back did not leave Data")
                    driver.wait_idle(frames=3)
                    after = logfile.read_text()[baseline:]
                    assert switches(logfile, baseline) == [("10", "16")], (name, switches(logfile, baseline),
                                                                           after[-1200:])
                else:
                    title("Profile")
                    assert switches(logfile, baseline) == [], (name, "Profile Data skipped its parent",
                                                               switches(logfile, baseline))
                    profile_focus_and_activity(name, window)
                    # The Profile hub's Back returns to Apps: one switch
                    # leaves Profile, and Data was not skipped on the way.
                    driver.press(label="Back", role="button")
                    wait_for(lambda: switches(logfile, baseline), f"{name}: Profile hub Back did not leave Profile")
                    driver.wait(label="Apps", role="text")
                    driver.wait_idle(frames=3)
                    left = switches(logfile, baseline)
                    assert len(left) == 1 and left[0][0] == "10", (name, "Profile hub Back did not leave Profile once",
                                                                   left)
                    open_practice(name)
                    wait_for(lambda: switches(logfile, baseline)[-1][1] == "0",
                             f"{name}: Practice did not open: {switches(logfile, baseline)}")
                assert "APP: frame rejected with status" not in logfile.read_text()
            finally:
                app.terminate()
                try:
                    app.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    app.kill()
                    app.wait(timeout=5)
                shutil.rmtree(Path('/tmp') / f'inbe-screenshot-{app.pid}', ignore_errors=True)
print("Profile focus scrolling and Activity; Data Back: navigation exits once; Profile Data returns to its hub, whose Back returns to Apps; Settings lists no Data")
