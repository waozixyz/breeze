#!/usr/bin/env python3
"""Verify live Android PiP only on the private inbe-picture-window emulator."""
import argparse
import io
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import time

from PIL import Image, ImageChops


PACKAGE = "xyz.waozi.inbe.debug"
ACTIVITY = PACKAGE + "/xyz.waozi.inbe.MainActivity"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", default="emulator-5572")
    parser.add_argument("--apk", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("build/android-picture-window/runtime"))
    args = parser.parse_args()
    if not re.fullmatch(r"emulator-\d+", args.serial):
        parser.error("This test never operates on physical phones.")

    def adb(*command, binary=False):
        result = subprocess.run([args.adb, "-s", args.serial, *map(str, command)],
                                capture_output=True, timeout=30, check=True)
        return result.stdout if binary else result.stdout.decode().strip()

    if adb("shell", "getprop", "ro.kernel.qemu") != "1" or adb(
            "shell", "getprop", "ro.boot.qemu.avd_name") != "inbe-picture-window":
        raise RuntimeError("Only the isolated inbe-picture-window AVD is permitted.")
    if "android.software.picture_in_picture" not in adb("shell", "pm", "list", "features"):
        raise RuntimeError("The test emulator does not support picture-in-picture.")
    args.output.mkdir(parents=True, exist_ok=True)
    adb("install", "-r", "-t", args.apk)
    adb("shell", "pm", "grant", PACKAGE, "android.permission.POST_NOTIFICATIONS")

    def start():
        result = adb("shell", "am", "start", "-W", "-n", ACTIVITY)
        if "Status: ok" not in result:
            raise RuntimeError("Inbe failed to start: " + result)

    # All data in this named emulator is a disposable test fixture. Bypass
    # first-run setup, without installing or changing data on a real phone.
    adb("shell", "am", "force-stop", PACKAGE)
    start()
    time.sleep(2)
    adb("shell", "am", "force-stop", PACKAGE)
    database = args.output / "inbe.db"
    for suffix in ("", "-wal"):
        result = subprocess.run([args.adb, "-s", args.serial, "exec-out", "run-as", PACKAGE,
                                 "cat", "files/inbe/inbe.db" + suffix], capture_output=True, timeout=30)
        local = Path(str(database) + suffix)
        if result.returncode == 0:
            local.write_bytes(result.stdout)
        elif suffix == "":
            raise RuntimeError("Inbe did not initialize the fixture database.")
        else:
            local.unlink(missing_ok=True)
    with sqlite3.connect(database) as db:
        user = db.execute("SELECT id FROM users LIMIT 1").fetchone()[0]
        settings = dict(enabled_apps="31", main_tab="1", language="en",
                        language_setup_done="1", apps_setup_done="1",
                        launcher_guide_seen="1", tutorial_seen="1", cells_auto_update="0")
        for key, value in settings.items():
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                       "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user, key, value))
        db.commit()
        db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    adb("push", database, "/data/local/tmp/inbe-picture-fixture.db")
    adb("shell", "run-as", PACKAGE, "cp", "/data/local/tmp/inbe-picture-fixture.db", "files/inbe/inbe.db")
    adb("shell", "run-as", PACKAGE, "rm", "-f", "files/inbe/inbe.db-wal", "files/inbe/inbe.db-shm")

    def activities():
        return adb("shell", "dumpsys", "activity", "activities")

    def identity():
        match = re.search(r"ActivityRecord\{([\w]+) u0 " + re.escape(ACTIVITY), activities())
        if not match:
            raise RuntimeError("Inbe's activity is missing.")
        return adb("shell", "pidof", PACKAGE), match[1]

    def pinned_bounds():
        match = re.search(r"\* Task\{[^\n]*" + re.escape(PACKAGE) +
                          r"[^\n]*mode=pinned[^\n]*\n\s*mBounds=Rect\((\d+), (\d+) - (\d+), (\d+)\)", activities())
        return tuple(map(int, match.groups())) if match else None

    def wait_for(predicate, description, seconds=20):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            result = predicate()
            if result:
                return result
            time.sleep(.5)
        raise RuntimeError(description)

    def geometry():
        lines = adb("logcat", "-d", "--pid=" + identity()[0], "-v", "raw", "-s", "InbeGeometry:I", "*:S")
        matches = list(re.finditer(r"sample=(\d+).*screen=(\d+)x(\d+).*practice=(-?\d+) paused=(\d+)", lines))
        return tuple(map(int, matches[-1].groups())) if matches else None

    def active():
        sample = geometry()
        return sample if sample and sample[-2:] == (0, 0) else None

    def frame(name, bounds=None):
        data = adb("exec-out", "screencap", "-p", binary=True)
        image = Image.open(io.BytesIO(data)).convert("RGB")
        # Captures belong only to this private emulator, never a real desktop
        # or phone. Keep just Inbe's owned PiP rectangle for animation evidence.
        if bounds:
            left, top, right, bottom = bounds
            image = image.crop((left + 8, top + 8, right - 8, bottom - 8))
        image.save(args.output / (name + ".png"))
        return image

    def begin_practice():
        adb("shell", "am", "force-stop", PACKAGE)
        start()
        wait_for(geometry, "Inbe did not draw its initial native frame.")
        adb("shell", "am", "start", "-W", "-n", ACTIVITY,
            "-a", "xyz.waozi.inbe.action.START_PRACTICE", "--ei", "practice_id", "0")
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if active():
                return identity()
            time.sleep(.5)
        # Locate the rendered Start Practice label instead of assuming a
        # device resolution or fixed position.
        screenshot = args.output / "start-page.png"
        frame("start-page")
        text = subprocess.check_output(["tesseract", str(screenshot), "stdout", "tsv"],
                                       text=True, stderr=subprocess.DEVNULL, timeout=30)
        words = [line.split("\t") for line in text.splitlines()[1:]]
        start_word = next((word for word in words if len(word) == 12 and word[11] == "Start"), None)
        if not start_word:
            raise RuntimeError("The Start Practice button is not visible.")
        x, y, width, height = map(int, start_word[6:10])
        adb("shell", "input", "tap", x + width // 2, y + height // 2)
        wait_for(active, "The breathing practice did not start.")
        return identity()

    def detach_card():
        # These two controls were visually verified on this test AVD. Refuse
        # a different resolution rather than send guessed coordinates.
        if frame("before-manual-detach").size != (480, 960):
            raise RuntimeError("Manual controls require the 480x960 test AVD.")
        adb("shell", "input", "swipe", "356", "93", "356", "93", "300")
        time.sleep(1)
        frame("manual-card")
        adb("shell", "input", "swipe", "324", "174", "324", "174", "300")

    previous = adb("shell", "appops", "get", PACKAGE, "PICTURE_IN_PICTURE")
    mode = re.search(r"PICTURE_IN_PICTURE: (\w+)", previous)
    previous_mode = mode[1] if mode else "default"
    report = {"passed": False, "cases": []}
    try:
        adb("shell", "appops", "set", PACKAGE, "PICTURE_IN_PICTURE", "allow")
        original = begin_practice()
        adb("shell", "input", "keyevent", "KEYCODE_HOME")
        def settled_picture():
            bounds = pinned_bounds()
            sample = active()
            if bounds and sample and sample[1:3] == (bounds[2] - bounds[0], bounds[3] - bounds[1]):
                return bounds
            return None

        wait_for(settled_picture, "The floating practice was reset, paused or did not resize.")
        time.sleep(1)
        bounds = settled_picture()
        if not bounds:
            raise RuntimeError("The picture-in-picture transition did not settle.")
        if identity() != original:
            raise RuntimeError("Entering PiP recreated the activity or restarted the app.")
        first = frame("floating-first", bounds)
        changed = 0
        for attempt in range(6):
            time.sleep(2)
            if identity() != original or not active():
                raise RuntimeError("The floating practice stopped.")
            later = frame("floating-live", bounds)
            pixels = ImageChops.difference(first, later).tobytes()
            changed = sum(max(pixels[i:i + 3]) > 24 for i in range(0, len(pixels), 3))
            if changed > 40:
                break
        if changed <= 40:
            raise RuntimeError("The floating practice does not animate.")
        report["cases"].append({"case": "automatic floating and live animation", "changed_pixels": changed})

        adb("shell", "am", "start", "-W", "-a", "android.settings.SETTINGS")
        time.sleep(2)
        if not pinned_bounds() or identity() != original or not active():
            raise RuntimeError("The practice did not survive switching to another app.")
        report["cases"].append({"case": "practice remains live over another app"})
        start()
        wait_for(lambda: not pinned_bounds(), "The practice did not return from PiP.")
        wait_for(lambda: (current if (current := active()) and current[2] > 500 else None),
                 "Returning from PiP lost the active practice or kept a small surface.")
        if identity() != original:
            raise RuntimeError("Returning from PiP recreated the activity or kept a small surface.")
        frame("returned-practice")
        report["cases"].append({"case": "return preserves activity and running practice"})

        detach_card()
        wait_for(settled_picture, "The manual detach button did not open Android PiP.")
        if identity() != original:
            raise RuntimeError("Manual detachment restarted the practice.")
        report["cases"].append({"case": "manual detach opens the existing practice"})

        adb("shell", "appops", "set", PACKAGE, "PICTURE_IN_PICTURE", "ignore")
        begin_practice()
        adb("shell", "input", "keyevent", "KEYCODE_HOME")
        time.sleep(3)
        if pinned_bounds():
            raise RuntimeError("Inbe entered PiP despite denied permission.")
        report["cases"].append({"case": "denied permission prevents automatic floating"})
        start()
        wait_for(active, "The denied-permission practice did not return.")
        detach_card()
        def settings_focused():
            windows = adb("shell", "dumpsys", "window")
            current = next((line for line in windows.splitlines() if "mCurrentFocus=" in line), "")
            (args.output / "permission-window-state.txt").write_text(current + "\n")
            return "com.android.settings" in current

        wait_for(settings_focused, "The manual detach button did not open PiP permission settings.")
        if pinned_bounds():
            raise RuntimeError("Manual detachment ignored denied permission.")
        report["cases"].append({"case": "manual detach opens settings when permission is denied"})
        report["passed"] = True
        print("Android PiP: automatic floating, live animation, other app, return and denied permission passed.")
    finally:
        adb("shell", "appops", "set", PACKAGE, "PICTURE_IN_PICTURE", previous_mode)
        adb("shell", "am", "force-stop", PACKAGE)
        (args.output / "result.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
