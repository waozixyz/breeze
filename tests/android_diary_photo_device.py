#!/usr/bin/env python3
"""Exercise Diary images only in the private inbe-diary-photo Android 14 AVD.

The emulator must run under private Xvfb with inherited desktop variables
scrubbed. This test refuses physical phones and every other AVD.
Run with: python3 tests/android_diary_photo_device.py test --apk DEBUG_APK
"""
import argparse
import io
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import time
import xml.etree.ElementTree as ET

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
PACKAGE = "xyz.waozi.inbe.debug"
ACTIVITY = PACKAGE + "/xyz.waozi.inbe.MainActivity"
APP_FILES = "files/inbe"
TEXT = "A diary entry with photos"


class Device:
    def __init__(self, adb, serial, output):
        if not re.fullmatch(r"emulator-\d+", serial):
            raise ValueError("Only a private emulator is allowed")
        self.adb_path = adb
        self.serial = serial
        self.output = output
        output.mkdir(parents=True, exist_ok=True)
        self.wait(lambda: self.probe("getprop", "sys.boot_completed") == "1", "Android boot", 180)
        assert self.shell("getprop", "ro.kernel.qemu") == "1"
        assert self.shell("getprop", "ro.boot.qemu.avd_name") == "inbe-diary-photo"
        assert self.shell("getprop", "ro.build.version.sdk") == "34"

    def adb(self, *arguments, binary=False):
        result = subprocess.run([self.adb_path, "-s", self.serial, *map(str, arguments)],
                                check=True, capture_output=True, timeout=60)
        return result.stdout if binary else result.stdout.decode().strip()

    def shell(self, *arguments):
        return self.adb("shell", *arguments)

    def probe(self, *arguments):
        result = subprocess.run([self.adb_path, "-s", self.serial, "shell", *arguments],
                                capture_output=True, text=True, timeout=10)
        return result.stdout.strip() if result.returncode == 0 else ""

    def wait(self, predicate, description, seconds=20):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            result = predicate()
            if result:
                return result
            time.sleep(0.5)
        raise AssertionError("Timed out waiting for " + description)

    def start(self):
        self.shell("am", "start", "-W", "-n", ACTIVITY)
        time.sleep(2)

    def stop(self):
        self.shell("am", "force-stop", PACKAGE)

    def snapshot(self, name):
        # The complete screen belongs to this dedicated emulator, launched on
        # the test's private display. No real desktop or phone is captured.
        data = self.adb("exec-out", "screencap", "-p", binary=True)
        image = Image.open(io.BytesIO(data)).convert("RGB")
        image.save(self.output / (name + ".png"))
        return image

    def private_bytes(self, name):
        return self.adb("exec-out", "run-as", PACKAGE, "cat", name, binary=True)

    def put_private(self, source, destination):
        transfer = "/data/local/tmp/inbe-diary-photo-fixture"
        self.adb("push", source, transfer)
        self.shell("run-as", PACKAGE, "cp", transfer, destination)
        self.shell("rm", "-f", transfer)

    def settings(self, **values):
        self.stop()
        database = self.output / "inbe.db"
        for suffix in ("", "-wal"):
            result = subprocess.run([self.adb_path, "-s", self.serial, "exec-out", "run-as", PACKAGE,
                                     "cat", APP_FILES + "/inbe.db" + suffix], capture_output=True, timeout=20)
            local = Path(str(database) + suffix)
            if result.returncode == 0:
                local.write_bytes(result.stdout)
            elif suffix:
                local.unlink(missing_ok=True)
            else:
                raise AssertionError("Inbe did not create its private database")
        with sqlite3.connect(database) as db:
            owner = db.execute("SELECT id FROM users LIMIT 1").fetchone()[0]
            assert re.fullmatch(r"[a-z0-9-]+", owner)
            for key, value in values.items():
                db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,?) "
                           "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value",
                           (owner, key, str(value), int(time.time())))
            db.commit()
            db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        self.put_private(database, APP_FILES + "/inbe.db")
        self.shell("run-as", PACKAGE, "rm", "-f", APP_FILES + "/inbe.db-wal", APP_FILES + "/inbe.db-shm")
        return owner

    def prepare(self, apk):
        self.adb("install", "-r", "-t", apk)
        self.shell("pm", "clear", PACKAGE)
        # The app's unrelated first-run notification prompt must not cover
        # Diary. No photo or storage permission is granted by this test.
        self.shell("pm", "grant", PACKAGE, "android.permission.POST_NOTIFICATIONS")
        self.shell("input", "keyevent", "KEYCODE_WAKEUP")
        self.shell("wm", "dismiss-keyguard")
        self.shell("settings", "put", "global", "window_animation_scale", "0")
        self.shell("settings", "put", "global", "transition_animation_scale", "0")
        self.shell("settings", "put", "global", "animator_duration_scale", "0")
        self.start()
        owner = self.settings(enabled_apps=8, main_tab=3, language="en", language_setup_done=1,
                              apps_setup_done=1, launcher_guide_seen=1, tutorial_seen=1,
                              lumi_guides_seen=127, package_updates_allowed=0,
                              theme=7, theme_source=0, theme_mode=1, dark_mode=0, ui_scale=10)
        day = self.shell("date", "+%F")
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", day)
        directory = APP_FILES + "/diary/" + owner
        self.shell("run-as", PACKAGE, "mkdir", "-p", directory)
        entry = self.output / "entry.json"
        entry.write_text(json.dumps(dict(version=1, date=day, text=TEXT, photos=[])))
        entry_path = directory + "/" + day + ".json"
        self.put_private(entry, entry_path)
        self.output.joinpath("context.json").write_text(json.dumps(dict(entry=entry_path, directory=directory)))
        pictures = "/sdcard/Pictures/DiaryCheck"
        self.shell("mkdir", "-p", pictures)
        for filename, mode, size, color, format in (
                ("diary-red.jpg", "RGB", (3200, 2400), (241, 52, 71), "JPEG"),
                ("diary-blue.png", "RGBA", (256, 192), (24, 90, 220, 128), "PNG")):
            source = self.output / filename
            Image.new(mode, size, color).save(source, format=format)
            self.adb("push", source, pictures + "/" + filename)
            self.shell("am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
                       "-d", "file://" + pictures + "/" + filename)
        self.start()
        self.snapshot("prepared-light")
        print("Android 14 emulator prepared: text-only diary, two local images, sage light, scale 10.", flush=True)

    def entry(self):
        context = json.loads(self.output.joinpath("context.json").read_text())
        value = json.loads(self.private_bytes(context["entry"]))
        assert value["text"] == TEXT, "Photo action changed diary text"
        return value

    def count(self, expected):
        return self.wait(lambda: self.entry() if len(self.entry()["photos"]) == expected else None,
                         str(expected) + " saved attachments", 30)

    def nodes(self):
        self.shell("uiautomator", "dump", "/sdcard/diary-picker.xml")
        return ET.fromstring(self.shell("cat", "/sdcard/diary-picker.xml")).iter("node")

    def tap_node(self, node):
        values = list(map(int, re.findall(r"\d+", node.attrib["bounds"])))
        assert len(values) == 4
        self.shell("input", "tap", (values[0] + values[2]) // 2, (values[1] + values[3]) // 2)

    def open_picker(self, name):
        # Verified on this test AVD at 480x960 and scale 10. Refuse another
        # geometry instead of sending coordinates intended for this fixture.
        assert self.snapshot(name + "-before").size == (480, 960)
        self.shell("input", "tap", "442", "158")
        self.wait(lambda: "com.google.android.providers.media.module/" in
                  self.shell("dumpsys", "window", "windows"), "Android system photo picker")
        time.sleep(1)

    def choose(self, color, expected_count, name):
        self.open_picker(name)
        screen = self.snapshot(name + "-picker")
        choices = []
        for node in self.nodes():
            if not node.attrib.get("resource-id", "").endswith(":id/icon_thumbnail"):
                continue
            left, top, right, bottom = map(int, re.findall(r"\d+", node.attrib["bounds"]))
            red, green, blue = screen.getpixel(((left + right) // 2, (top + bottom) // 2))
            if (color == "red" and red > 200 and green < 120 and blue < 120) or (
                    color == "blue" and blue > 200 and red < 180 and green < 200):
                choices.append(node)
        assert len(choices) == 1, "The picker did not show exactly one matching test photo"
        self.tap_node(choices[0])
        entry = self.count(expected_count)
        context = json.loads(self.output.joinpath("context.json").read_text())
        data = self.private_bytes(context["directory"] + "/" + entry["photos"][-1]["file"])
        image = Image.open(io.BytesIO(data))
        assert 0 < len(data) <= 512 * 1024
        assert max(image.size) <= 1600
        if color == "red":
            assert image.format == "JPEG" and image.size == (1600, 1200)
        else:
            assert image.format == "PNG" and image.mode == "RGBA"
            assert image.size == (256, 192) and image.getpixel((100, 100))[3] == 128
        self.wait(lambda: self.shell("run-as", PACKAGE, "ls", "cache/imports") == "",
                  "consumed picker cache cleanup")
        self.show_photo(color, name)
        print(name + ": saved " + image.format + " " + str(image.size) + ", " + str(len(data)) + " bytes", flush=True)
        return len(data)

    def cancel(self, name):
        before = self.entry()
        self.open_picker(name)
        cancel = [node for node in self.nodes() if node.attrib.get("content-desc") == "Cancel"]
        assert len(cancel) == 1
        self.tap_node(cancel[0])
        time.sleep(1)
        assert self.entry() == before, "Cancelling the picker changed the entry"

    def show_photo(self, color, name):
        self.shell("input", "swipe", "350", "820", "350", "250", "600")
        time.sleep(0.5)
        if "mInputShown=true" in self.shell("dumpsys", "input_method"):
            self.shell("input", "keyevent", "KEYCODE_BACK")
            time.sleep(0.5)
        screen = self.snapshot(name + "-visible")
        # Bound the check to Diary's photo area, excluding the system bars.
        pixels = screen.crop((16, 220, 464, 750)).getcolors(448 * 530)
        if color == "red":
            total = sum(count for count, (red, green, blue) in pixels
                        if red > 200 and green < 120 and blue < 120)
        else:
            total = sum(count for count, (red, green, blue) in pixels
                        if blue > 80 and blue > red + 40 and blue > green + 30)
        assert total > 1000, "The saved " + color + " image did not render"

    def check(self):
        permissions = self.shell("dumpsys", "package", PACKAGE)
        for permission in ("android.permission.READ_MEDIA_IMAGES", "android.permission.READ_EXTERNAL_STORAGE"):
            assert permission not in permissions, "Photo-library access was unexpectedly requested"
        sizes = {}
        for dark in (0, 1):
            name = "sage-dark" if dark else "sage-light"
            if dark:
                self.settings(theme_mode=2, dark_mode=1)
                self.start()
                self.count(1)
                self.show_photo("red", name + "-restored")
            self.cancel(name + "-cancel")
            if not dark:
                sizes["red"] = self.choose("red", 1, name + "-red")
            sizes["blue"] = self.choose("blue", 2, name + "-blue")
            self.shell("input", "tap", "88", "818")
            self.show_photo("red", name + "-previous")
            self.shell("input", "tap", "390", "818")
            self.show_photo("blue", name + "-next")
            self.shell("input", "tap", "240", "818")
            saved = self.count(1)
            assert "diary-" in saved["photos"][0]["name"]
            self.stop()
            self.start()
            assert self.entry() == saved
            self.show_photo("red", name + "-restart")
            print(name + ": picker cancellation, two images, browsing, removal, restart and rendering passed", flush=True)
        self.shell("input", "tap", "240", "818")
        saved = self.count(0)
        self.stop()
        self.start()
        assert self.entry() == saved
        self.snapshot("text-only-after-removal")
        result = dict(android_sdk=34, avd="inbe-diary-photo", resolution=[480, 960], scale=10,
                      themes=["sage_light", "sage_dark"], image_bytes=sizes,
                      passed=["system picker", "no photo-library permissions", "picker cancellation",
                              "JPEG resizing", "PNG alpha", "multiple attachments", "browse and remove",
                              "import cache cleanup", "app restart", "text-only compatibility"],
                      status="Local debug APK on an isolated emulator; no phone install or publication")
        self.output.joinpath("result.json").write_text(json.dumps(result, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "check", "test", "snapshot"))
    parser.add_argument("--adb", default="/home/wao/Android/Sdk/platform-tools/adb")
    parser.add_argument("--serial", default="emulator-5578")
    parser.add_argument("--apk", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "build/android-diary-photo-device/runtime")
    args = parser.parse_args()
    device = Device(args.adb, args.serial, args.output)
    try:
        if args.action in ("prepare", "test"):
            if not args.apk:
                parser.error("prepare requires --apk")
            device.prepare(args.apk)
        if args.action in ("check", "test"):
            device.check()
        if args.action == "snapshot":
            device.snapshot("current")
    except Exception:
        device.snapshot("failure")
        raise
    finally:
        if args.action == "test":
            device.stop()


if __name__ == "__main__":
    main()
