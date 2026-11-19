#!/usr/bin/env python3
"""Verify practice-start pixels on the USB Moto with a disposable profile.

Run against the separately installed debug verification APK. Its profile is
renamed aside and restored even on failure. Captures contain only test data.
"""
import argparse
import contextlib
import io
import json
from pathlib import Path
import shlex
import sqlite3
import subprocess
import time

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "backup/practice-start/moto"
PACKAGE = "xyz.waozi.inbe.verification"
PROFILE = "files/inbe"
PRESERVED = PROFILE + ".practice-start-preserved"
SERIAL = "ZE2223BQZT"


def adb(*arguments, check=True, timeout=60):
    return subprocess.run(["adb", "-s", SERIAL, *map(str, arguments)], check=check,
                          capture_output=True, timeout=timeout)


def shell(*arguments, check=True):
    return adb("shell", shlex.join(list(map(str, arguments))), check=check).stdout.decode().strip()


def private(*arguments):
    return shell("run-as", PACKAGE, *arguments)


def exists(path):
    return adb("shell", shlex.join(["run-as", PACKAGE, "sh", "-c", "test -e " + shlex.quote(path)]),
               check=False).returncode == 0


def stop():
    shell("am", "force-stop", PACKAGE)


def start():
    result = shell("am", "start", "-W", "-n", PACKAGE + "/xyz.waozi.inbe.MainActivity")
    assert "Error:" not in result, result
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        time.sleep(1)
        if capture("startup").getpixel((10, 300)) != (0, 0, 0):
            return
    pid = shell("pidof", PACKAGE).split()[0]
    log = shell("logcat", "-d", "--pid=" + pid, "-t", "150")
    (OUTPUT / "startup-failure.log").write_text(log)
    raise AssertionError("Native app UI did not become ready; see startup-failure.log")


def capture(label):
    activities = shell("dumpsys", "activity", "activities")
    assert any(PACKAGE + "/" in line for line in activities.splitlines() if "mResumedActivity:" in line)
    data = adb("exec-out", "screencap", "-p").stdout
    (OUTPUT / (label + ".png")).write_bytes(data)
    return Image.open(io.BytesIO(data)).convert("RGB")


def tap_start_practice(picture):
    # The wide green Start Practice button is unique in this seeded mono page.
    # Use pixels because UIAutomator can refuse idle snapshots during animation.
    rows = []
    for y in range(900, 1450):
        left = picture.getpixel((60, y))
        if left == picture.getpixel((360, y)) == picture.getpixel((660, y)) and \
                left[1] > left[0] + 10 and left[1] > left[2] + 10:
            rows.append(y)
    assert rows, "Start Practice button did not appear"
    bottom = rows[-1]
    top = bottom
    for row in reversed(rows[:-1]):
        if row != top - 1:
            break
        top = row
    assert bottom - top > 20, "Start Practice button was clipped"
    shell("input", "tap", 360, (top + bottom) // 2)


def bars_clear(picture):
    width, height = picture.size
    assert (width, height) == (720, 1560), "This oracle is for the USB Moto's three-button navigation"
    for bounds in ((2, height - 48, 42, height - 4), (width - 42, height - 48, width - 2, height - 4),
                   (2, 4, 24, 42), (width - 24, 4, width - 2, 42)):
        assert picture.crop(bounds).getextrema() == ((0, 0), (0, 0), (0, 0)), \
            ("Practice navigation painted over Android system bars", bounds)


def put_database(path):
    remote = "/data/local/tmp/breeze-practice-start.db"
    adb("push", path, remote)
    shell("chmod", "644", remote)
    private("cp", remote, PROFILE + "/inbe.db")
    shell("rm", "-f", remote)
    private("rm", "-f", PROFILE + "/inbe.db-wal", PROFILE + "/inbe.db-shm")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--page", choices=("practice", "lumi", "all"), default="all")
    args = parser.parse_args()
    assert shell("getprop", "ro.product.model") == "moto e6 play"
    assert shell("getprop", "ro.build.version.sdk") == "28"
    assert not exists(PRESERVED), "Restore an earlier interrupted practice-start test first"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    state = dict(isolated=False, restored=False, preserved=False)
    status = OUTPUT / "state.json"

    def save():
        status.write_text(json.dumps(state, indent=2) + "\n")

    stop()
    try:
        if exists(PROFILE):
            private("mv", PROFILE, PRESERVED)
            state["preserved"] = True
        state["isolated"] = True
        save()
        private("mkdir", "-p", PROFILE)
        private("touch", PROFILE + "/.practice-start-test")
        start()
        stop()
        database = OUTPUT / "fixture.db"
        for suffix in ("", "-wal"):
            result = adb("exec-out", "run-as", PACKAGE, "cat", PROFILE + "/inbe.db" + suffix, check=False)
            path = Path(str(database) + suffix)
            if result.returncode == 0:
                path.write_bytes(result.stdout)
            else:
                path.unlink(missing_ok=True)
        pages = ("practice", "lumi") if args.page == "all" else (args.page,)
        for page in pages:
            for placement, edge in ((2, "bottom"), (4, "top")):
                with contextlib.closing(sqlite3.connect(database)) as db:
                    user = db.execute("SELECT id FROM users LIMIT 1").fetchone()[0]
                    settings = dict(language="en", language_setup_done=1, apps_setup_done=1,
                                    tutorial_seen=1, habits_guide_seen=1, lumi_guides_seen=127,
                                    launcher_guide_seen=1, lumi_introduced=1, lumi_online=0,
                                    package_updates_allowed=0, enabled_apps=63,
                                    main_tab=1 if page == "practice" else 4, theme=9,
                                    theme_source=0, theme_mode=1, ui_scale=10,
                                    navigation_placement=placement, picture_in_picture=0,
                                    voice_narration_enabled=0, guide_narration_enabled=0,
                                    audio_enabled=0, music_volume=0,
                                    app_last_seen_version="2.1.63")
                    for key, value in settings.items():
                        db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                                   "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value",
                                   (user, key, str(value)))
                    db.commit()
                    with contextlib.closing(sqlite3.connect(OUTPUT / "seed.db")) as target:
                        db.backup(target)
                        target.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                for repetition in range(2):
                    put_database(OUTPUT / "seed.db")
                    start()
                    if "mInputShown=true" in shell("dumpsys", "input_method"):
                        shell("input", "keyevent", "4")
                        time.sleep(.5)
                    label = page + "-" + edge + "-" + str(repetition)
                    before = capture(label + "-before")
                    bars_clear(before)
                    if page == "practice":
                        tap_start_practice(before)
                    else:
                        # Tap the drawn composer, not Android's hidden IME bridge.
                        # Its position is fixed in this 720x1560 mono/scale-10 fixture.
                        shell("input", "tap", 150, 1308 if edge == "bottom" else 1418)
                        time.sleep(1)
                        shell("input", "text", "start%swhm")
                        time.sleep(1)
                        capture(label + "-typed")
                        if "mInputShown=true" in shell("dumpsys", "input_method"):
                            shell("input", "keyevent", "4")
                        time.sleep(.5)
                        # Android's multiline Enter is not the visible Send action.
                        shell("input", "tap", 650, 1308 if edge == "bottom" else 1418)
                    # IME delivery and local intent handling are asynchronous.
                    # Animated practice screens need not become UIAutomator-idle.
                    deadline = time.monotonic() + 15
                    while True:
                        time.sleep(.6)
                        picture = capture(label + "-running")
                        red, green, blue = picture.getpixel((280, 740))
                        if green > red + 10 and green > blue + 10:
                            break
                        assert time.monotonic() < deadline, \
                            (label, "The WHM practice circle did not appear")
                    bars_clear(picture)
                    canvas = picture.getpixel((10, 300))
                    assert picture.crop((10, 1380, 710, 1470)).getextrema() == \
                        tuple((channel, channel) for channel in canvas), \
                        (label, "Stale paint remains below the practice")
                    time.sleep(1)
                    bars_clear(capture(label + "-settled"))
                    stop()
                    print(label + ": practice visible, system bars and lower page clear", flush=True)
        state["result"] = "passed"
    finally:
        stop()
        if exists(PROFILE):
            assert exists(PROFILE + "/.practice-start-test"), "Refusing to remove unmarked data"
            private("rm", "-rf", PROFILE)
        if state["preserved"]:
            private("mv", PRESERVED, PROFILE)
        state.update(isolated=False, restored=True)
        save()
    print("USB Moto practice starts: mono scale 10, Lumi and Practice, repeated top/bottom starts leave system bars clear")


if __name__ == "__main__":
    main()
