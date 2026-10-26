#!/usr/bin/env python3
"""Download Arcade and a game from the live node on the USB Moto.

Uses the separate verification app and restores its profile and test-driver
files. No local package override, seeded offer, or screen capture is used.
Run through desktop_run: python3 tests/android_arcade_device.py run --apk APK
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shlex
import sqlite3
import subprocess
import time

from android_library_device import AndroidDriver, Device, PACKAGE, PROFILE, DRIVER, ROOT, SERIAL
from ui_driver import UiDriver

OUTPUT = ROOT / "backup/arcade/moto"
TRANSFER = "/data/local/tmp/breeze-arcade-test"
MARKER = "/.arcade-test"


class ArcadeDriver(AndroidDriver):
    def __init__(self, phone):
        self.phone = phone
        UiDriver.__init__(self, OUTPUT / "driver")


class ArcadeDevice(Device):
    def __init__(self):
        OUTPUT.mkdir(parents=True, exist_ok=True)
        self.state_path = OUTPUT / "state.json"
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {}
        assert self.adb("get-state").stdout.strip() == b"device"
        assert self.shell("getprop", "ro.product.model") == "moto e6 play"
        assert self.shell("getprop", "ro.build.version.sdk") == "28"

    def owns_foreground(self):
        windows = self.shell("dumpsys", "window", "windows")
        focus = next((line for line in windows.splitlines() if "mCurrentFocus=" in line), "")
        assert PACKAGE + "/" in focus, "The verification app is not foreground: " + focus

    def start(self):
        self.shell("input", "keyevent", "KEYCODE_WAKEUP")
        self.shell("wm", "dismiss-keyguard")
        result = self.shell("am", "start", "-n", PACKAGE + "/xyz.waozi.inbe.MainActivity",
                            "-a", "android.intent.action.MAIN", "-c", "android.intent.category.LAUNCHER")
        assert "Error:" not in result, result
        deadline = time.monotonic() + 30
        while True:
            try:
                self.owns_foreground()
                return
            except AssertionError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(.5)

    def put_private(self, source, destination):
        self.shell("mkdir", "-p", TRANSFER)
        remote = TRANSFER + "/" + source.name
        self.adb("push", source, remote)
        self.shell("chmod", "644", remote)
        self.private("cp", remote, destination)
        self.shell("rm", "-f", remote)

    def fingerprint(self, path):
        command = "cd " + shlex.quote(path) + " && find . -type f -exec sha256sum {} \\;"
        lines = self.private("sh", "-c", command).splitlines()
        return hashlib.sha256("\n".join(sorted(lines)).encode()).hexdigest()

    def database(self, name):
        path = OUTPUT / name
        for suffix in ("", "-wal"):
            result = self.adb("exec-out", "run-as", PACKAGE, "cat", PROFILE + "/inbe.db" + suffix,
                              check=False)
            target = Path(str(path) + suffix)
            if result.returncode == 0:
                target.write_bytes(result.stdout)
            else:
                target.unlink(missing_ok=True)
        return path

    def prepare(self, apk):
        assert not self.state.get("isolated"), "Restore the interrupted Arcade test first"
        assert self.adb("shell", "pidof", PACKAGE, check=False).returncode != 0, "Verification app is already running"
        windows = self.shell("dumpsys", "window", "windows")
        focus = next((line for line in windows.splitlines() if "mCurrentFocus=" in line), "")
        assert not any(package + "/" in focus for package in ("xyz.waozi.inbe", "xyz.waozi.inbe.debug")), "The owner's app is foreground"
        sdk = next(line.split("=", 1)[1] for line in (ROOT / "droid/local.properties").read_text().splitlines()
                   if line.startswith("sdk.dir="))
        aapt = sorted(Path(sdk).glob("build-tools/*/aapt"))[-1]
        manifest = subprocess.check_output([str(aapt), "dump", "badging", str(apk)], text=True)
        assert re.search(r"^package: name='([^']+)'", manifest, re.M)[1] == PACKAGE
        assert "application-debuggable" in manifest
        for path in (PROFILE, DRIVER):
            assert not self.exists(path + ".arcade-preserved"), "An earlier preserved profile needs restoration"
            evidence = path + ".arcade-evidence"
            if self.exists(evidence):
                assert self.exists(evidence + MARKER), "Refusing to replace unmarked test evidence"
                archive = self.adb("exec-out", "run-as", PACKAGE, "tar", "cf", "-", evidence).stdout
                (OUTPUT / (Path(path).name + "-previous.tar")).write_bytes(archive)
                self.private("rm", "-rf", evidence)
        self.adb("install", "-r", str(apk), timeout=180)
        self.state = dict(isolated=True, preserved=[], cases=[], apk_sha256=hashlib.sha256(apk.read_bytes()).hexdigest(),
                          started_at=datetime.now(timezone.utc).isoformat(), source="live https://api.waozi.xyz")
        self.save()
        for path in (PROFILE, DRIVER):
            if self.exists(path):
                record = dict(path=path, fingerprint=self.fingerprint(path))
                self.private("mv", path, path + ".arcade-preserved")
                self.state["preserved"].append(record)
                self.save()
            self.private("mkdir", "-p", path)
            self.private("touch", path + MARKER)
        self.start()
        driver = ArcadeDriver(self)
        driver.tree()
        self.stop()
        with sqlite3.connect(self.database("initial.db")) as database:
            user = database.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
            settings = dict(language="en", language_system=0, language_setup_done=1, apps_setup_done=1,
                            tutorial_seen=1, habits_guide_seen=1, lumi_guides_seen=127, launcher_guide_seen=1,
                            package_updates_allowed=0, apps_last_update_check=1900000000, audio_enabled=0,
                            sync_enabled=0)
            for key, value in settings.items():
                database.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                                 "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value",
                                 (user, key, str(value)))
            assert not database.execute("SELECT 1 FROM settings WHERE key='app_used_arcade' AND value='1'").fetchone()
            database.commit()
            seeded = OUTPUT / "seeded.db"
            with sqlite3.connect(seeded) as target:
                database.backup(target)
        self.put_private(seeded, PROFILE + "/inbe.db")
        self.private("rm", "-f", PROFILE + "/inbe.db-wal", PROFILE + "/inbe.db-shm")
        self.start()
        return ArcadeDriver(self)

    def case(self, name, **details):
        self.state["cases"].append(dict(name=name, **details))
        self.save()
        print(name, flush=True)

    def restore(self):
        if not self.state.get("isolated"):
            return
        self.stop()
        assert self.adb("shell", "pidof", PACKAGE, check=False).returncode != 0
        for path in (PROFILE, DRIVER):
            if path in self.state.get("restored_paths", []):
                continue
            if self.exists(path):
                assert self.exists(path + MARKER), "Refusing to replace unmarked app data"
                destination = path + ".arcade-evidence"
                assert not self.exists(destination), "Previous test evidence must be retained"
                self.private("mv", path, destination)
            original = next((item for item in self.state["preserved"] if item["path"] == path), None)
            if original:
                self.private("mv", path + ".arcade-preserved", path)
                assert self.fingerprint(path) == original["fingerprint"], "Restored data differs from the original"
            self.state.setdefault("restored_paths", []).append(path)
            self.save()
        self.state.update(isolated=False, restored=True)
        self.save()
        print("Verification app profile and driver restored with file hashes verified", flush=True)


def download(driver):
    actions = driver.find(label="Download", role="button", visible=True)
    assert actions, driver.text()
    driver.press(key=max(actions, key=lambda node: node["width"])["key"])


def library(driver):
    driver.wait(label="Shovey", role="button", timeout=120)


def exercise(phone, driver):
    if not driver.find(label="Find an app", role="text_field", visible=True):
        driver.press(label="Apps", role="button")
    driver.wait(label="Arcade", role="button", timeout=90)
    driver.press(label="Arcade", role="button")
    driver.wait(label="Cancel", role="button")
    phone.case("Arcade asks for download consent before installation")
    download(driver)
    library(driver)
    phone.case("Arcade downloaded from the live node and opened its game library")
    cover = driver.find(label="Apfelwurm", role="button", visible=True)
    for attempt in range(12):
        if cover:
            break
        driver.pointer(350, 850, wheel=-4)
        driver.release_pointer()
        cover = driver.find(label="Apfelwurm", role="button", visible=True)
    assert cover, "Apfelwurm is not reachable in the Arcade library"
    driver.press(key=cover[0]["key"])
    driver.wait(label="Download", role="button")
    download(driver)
    driver.wait(label="How do you want to move?", role="text", timeout=120)
    driver.press(label="Swipe", role="button")
    driver.wait(label="Pause", role="button", timeout=60)
    phone.case("Apfelwurm downloaded through Arcade and entered its playable screen")
    phone.stop()
    with sqlite3.connect(phone.database("installed.db")) as database:
        installed = database.execute("SELECT value FROM settings WHERE key='app_used_arcade'").fetchone()
        assert installed and installed[0] == "1", "Arcade installation was not persisted"
    phone.start()
    driver.reset()
    if not driver.find(label="Shovey", role="button", visible=True):
        driver.press(label="Apps", role="button")
        driver.press(label="Arcade", role="button")
    library(driver)
    assert not driver.find(label="Cancel", role="button", visible=True), "Arcade asked to download again after restart"
    phone.case("Arcade installation persisted and reopened after a process restart")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "restore"))
    parser.add_argument("--apk", type=Path)
    args = parser.parse_args()
    phone = ArcadeDevice()
    if args.action == "restore":
        phone.restore()
        return
    if args.apk is None:
        parser.error("run requires --apk")
    try:
        driver = phone.prepare(args.apk.resolve(strict=True))
        exercise(phone, driver)
        phone.state["passed"] = True
        phone.save()
    finally:
        phone.restore()


if __name__ == "__main__":
    main()
