#!/usr/bin/env python3
"""Check selection on the dedicated Android 14 AVD, never a physical phone.

Uses a fresh debug-app profile. Run the AVD on private Xvfb with inherited
desktop variables scrubbed, then pass the current x86_64 debug APK.
"""
import argparse
import csv
import io
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import time

from PIL import ImageOps

from android_diary_photo_device import APP_FILES, PACKAGE, ROOT, Device


TEXT = "Calm breathing keeps my diary clear."


class SelectionDevice(Device):
    def prepare(self, apk, dark=0):
        if apk:
            self.adb("install", "-r", "-t", apk)
        self.shell("pm", "clear", PACKAGE)
        self.shell("pm", "grant", PACKAGE, "android.permission.POST_NOTIFICATIONS")
        self.shell("input", "keyevent", "KEYCODE_WAKEUP")
        self.shell("wm", "dismiss-keyguard")
        self.start()
        owner = self.settings(enabled_apps=31, main_tab=3, language="en", language_setup_done=1,
                              apps_setup_done=1, launcher_guide_seen=1, tutorial_seen=1,
                              lumi_guides_seen=127, lumi_online=0, lumi_archive_migrated=1,
                              package_updates_allowed=0, theme=7, theme_source=0,
                              theme_mode=2 if dark else 1, dark_mode=dark, ui_scale=10,
                              **{"cell.lumi.message.selection-fixture": json.dumps(dict(
                                  time=1, user=0, kind=0, payload="", text="Gentle breathing brings calm."))})
        day = self.shell("date", "+%F")
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", day)
        directory = APP_FILES + "/diary/" + owner
        self.shell("run-as", PACKAGE, "mkdir", "-p", directory)
        self.entry_path = directory + "/" + day + ".json"
        fixture = self.output / "entry.json"
        fixture.write_text(json.dumps(dict(version=1, date=day, text=TEXT, photos=[])))
        self.put_private(fixture, self.entry_path)
        self.output.joinpath("context.json").write_text(json.dumps(dict(entry=self.entry_path)))
        self.start()
        self.snapshot("prepared")

    def word(self, name, target, minimum_y=0):
        path = self.output / (name + ".png")
        assert self.snapshot(name).size == (480, 960)
        for mode in (11, 6):
            output = subprocess.run(["tesseract", str(path), "stdout", "--psm", str(mode),
                                     "-c", "tessedit_create_tsv=1"],
                                    capture_output=True, text=True, check=True, timeout=20).stdout
            words = [row for row in csv.DictReader(io.StringIO(output), delimiter="\t")
                     if row["text"].strip(".,:").lstrip("I|").lower() == target.split()[0].lower()
                     and int(row["top"]) >= minimum_y
                     and int(row["top"]) < (960 if target == "Message" else 600)]
            if len(words) == 1:
                row = words[0]
                return int(row["left"]) + int(row["width"]) // 2, int(row["top"]) + int(row["height"]) // 2
        raise AssertionError("Expected one rendered word: " + target)

    def hold_word(self, name, word):
        x, y = self.word(name, word)
        self.shell("input", "swipe", x, y, x, y, 900)
        time.sleep(0.5)
        self.snapshot(name + "-selected")

    def menu(self, command):
        matches = [node for node in self.nodes() if node.attrib.get("text") == command
                   or node.attrib.get("content-desc") == command]
        if matches:
            assert len(matches) == 1
            self.tap_node(matches[0])
        else:
            # NativeActivity's floating popup is rendered but not exposed by
            # UIAutomator on this image. OCR its largest connected background.
            screen = self.snapshot("menu-" + command.replace(" ", "-"))
            pixels = screen.load()
            remaining = {(x, y) for y in range(30, 600) for x in range(480)
                         if pixels[x, y] == (66, 66, 66)}
            largest = set()
            while remaining:
                todo = [remaining.pop()]
                component = set(todo)
                while todo:
                    x, y = todo.pop()
                    for point in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                        if point in remaining:
                            remaining.remove(point)
                            component.add(point)
                            todo.append(point)
                if len(component) > len(largest):
                    largest = component
            assert len(largest) > 1000, "Native toolbar did not render"
            left = min(x for x, y in largest)
            top = min(y for x, y in largest)
            right = max(x for x, y in largest) + 1
            bottom = max(y for x, y in largest) + 1
            crop = ImageOps.invert(screen.crop((left, top, right, bottom)))
            path = self.output / "toolbar-ocr.png"
            crop.resize((crop.width * 3, crop.height * 3)).save(path)
            output = subprocess.run(["tesseract", str(path), "stdout", "--psm", "6",
                                     "-c", "tessedit_create_tsv=1"], capture_output=True,
                                    text=True, check=True, timeout=60).stdout
            words = [row for row in csv.DictReader(io.StringIO(output), delimiter="\t")
                     if row["text"].strip("|.,:").lower() == command.split()[0].lower()]
            assert len(words) == 1, (command, output)
            row = words[0]
            x = left + (int(row["left"]) + int(row["width"]) // 2) // 3
            y = top + (int(row["top"]) + int(row["height"]) // 2) // 3
            self.shell("input", "tap", x, y)
        time.sleep(0.5)

    def text(self):
        return json.loads(self.private_bytes(self.entry_path))["text"]

    def check(self, apk):
        for dark in (0, 1):
            name = "sage-dark" if dark else "sage-light"
            # Give each theme its own profile. After startup, navigate in the
            # actual UI rather than rewriting a live profile's SQLite records.
            self.prepare(apk, dark)
            self.hold_word(name + "-diary-copy", "breathing")
            self.menu("Copy")
            self.hold_word(name + "-diary-replace", "Calm")
            self.menu("Paste")
            expected = "breathing breathing keeps my diary clear."
            self.wait(lambda: self.text() == expected, "Diary paste saved")
            # A real IME key, rather than adb's synthetic hardware typing.
            self.shell("input", "tap", 240, 807)
            self.wait(lambda: self.text() != expected, "continued IME typing")
            typed = self.text()
            assert typed in ("breathingg breathing keeps my diary clear.",
                             "breathingG breathing keeps my diary clear."), typed
            self.snapshot(name + "-diary-paste-typed")
            self.stop()
            self.start()
            assert self.text() == typed
            self.snapshot(name + "-diary-restart")

            self.shell("input", "tap", 66, 929)
            time.sleep(2)
            self.hold_word(name + "-chat-copy", "Gentle")
            self.menu("Copy")
            # Empty composer must still offer Paste on long-press.
            time.sleep(6)  # Let Android's clipboard preview stop covering it.
            x, y = self.word(name + "-composer-empty", "Message")
            self.shell("input", "tap", x, y)
            time.sleep(2)
            assert self.snapshot(name + "-composer-focused").size == (480, 960)
            # The open IME moves this fixture's composer to y=575 in both
            # themes. The dark placeholder has intentionally low contrast.
            self.shell("input", "swipe", 70, 575, 70, 575, 900)
            time.sleep(1)
            self.menu("Paste")
            time.sleep(2)
            self.snapshot(name + "-chat-pasted")
            self.shell("input", "tap", 240, 807)
            time.sleep(2)
            self.snapshot(name + "-chat-typed")
            self.shell("input", "swipe", 45, 570, 45, 570, 900)
            time.sleep(1)
            self.menu("Cut")
            time.sleep(2)
            self.snapshot(name + "-composer-cut")
            # Verify the exact composer text through the OS clipboard and
            # persisted Diary data; caret blinking can confuse screenshot OCR.
            self.shell("input", "tap", 414, 645)  # Apps, above the open IME.
            time.sleep(2)
            x, y = self.word(name + "-apps", "Diary")
            self.shell("input", "tap", x, y)
            time.sleep(2)
            self.hold_word(name + "-composer-roundtrip", "keeps")
            self.menu("Paste")
            expected = typed.replace("keeps", "Gentleg")
            self.wait(lambda: self.text() == expected, "composer clipboard round trip")
            self.stop()
            database_path = self.output / "checked.db"
            database_path.write_bytes(self.private_bytes(APP_FILES + "/inbe.db"))
            for suffix in ("-wal", "-shm"):
                Path(str(database_path) + suffix).unlink(missing_ok=True)
            wal = self.probe("run-as", PACKAGE, "ls", APP_FILES + "/inbe.db-wal")
            if wal:
                Path(str(database_path) + "-wal").write_bytes(self.private_bytes(APP_FILES + "/inbe.db-wal"))
            with sqlite3.connect(database_path) as database:
                keys = database.execute("SELECT key FROM settings WHERE key LIKE 'cell.lumi.message.%'").fetchall()
                assert keys == [("cell.lumi.message.selection-fixture",)], "The check must never send a message"
            print(name + ": Diary copy/paste/IME typing/save/restart and offline chat word copy/composer paste passed",
                  flush=True)
        self.output.joinpath("result.json").write_text(json.dumps(dict(
            android_sdk=34, avd="inbe-diary-photo", scale=10,
            themes=["sage_light", "sage_dark"],
            passed=["long press", "native toolbar", "Diary copy/paste", "IME typing",
                    "Diary save/restart", "chat word copy", "unsent composer paste",
                    "composer IME typing/cut and exact clipboard round trip"],
            status="Local debug APK on a private emulator; no physical phone, send, push or release"), indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "check", "test", "snapshot"))
    parser.add_argument("--adb", default="/home/wao/Android/Sdk/platform-tools/adb")
    parser.add_argument("--serial", default="emulator-5578")
    parser.add_argument("--apk", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "build/android-text-selection-device")
    args = parser.parse_args()
    device = SelectionDevice(args.adb, args.serial, args.output)
    try:
        if args.action in ("prepare", "test"):
            if not args.apk:
                parser.error("prepare requires --apk")
        if args.action == "prepare":
            device.prepare(args.apk)
        if args.action in ("check", "test"):
            device.check(args.apk)
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
