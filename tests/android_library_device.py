#!/usr/bin/env python3
"""Library on the shared USB Moto, through Kryon's private test-driver files.

Run only after the release and render sessions have released the device.
The verification app's profile, driver directory and local bundles are renamed
aside and restored even when a case fails. Captures come from the USB Moto.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import sqlite3
import subprocess
import time

from library_reader_cases import LibraryReaderCases
from ui_driver import UiDriver, escape

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "backup/library/moto"
SERIAL = "ZE2223BQZT"
PACKAGE = "xyz.waozi.inbe.verification"
ACTIVITY = PACKAGE + "/xyz.waozi.inbe.MainActivity"
PROFILE = "files/inbe"
DRIVER = "files/kryon-test-driver"
EXTERNAL = "/sdcard/Android/data/" + PACKAGE + "/files"
TRANSFER = "/data/local/tmp/breeze-library-test"


class Device:
    def __init__(self):
        OUTPUT.mkdir(parents=True, exist_ok=True)
        self.state_path = OUTPUT / "state.json"
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {}
        assert self.adb("get-state").stdout.strip() == b"device"
        assert self.shell("getprop", "ro.product.model") == "moto e6 play"
        assert self.shell("getprop", "ro.build.version.sdk") == "28"

    def adb(self, *args, check=True, data=None, timeout=60):
        return subprocess.run(["adb", "-s", SERIAL, *map(str, args)], input=data,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=timeout, check=check)

    def shell(self, *args, check=True):
        return self.adb("shell", shlex.join(list(map(str, args))), check=check).stdout.decode().strip()

    def private(self, *args, check=True):
        return self.shell("run-as", PACKAGE, *args, check=check)

    def exists(self, path):
        command = "test -e " + shlex.quote(path)
        return self.adb("shell", shlex.join(["run-as", PACKAGE, "sh", "-c", command]),
                        check=False).returncode == 0

    def save(self):
        pending = self.state_path.with_suffix(".tmp")
        pending.write_text(json.dumps(self.state, indent=2) + "\n")
        pending.replace(self.state_path)

    def foreground(self):
        activities = self.shell("dumpsys", "activity", "activities")
        return next((line.strip() for line in activities.splitlines() if "mResumedActivity:" in line), "")

    def owns_foreground(self):
        current = self.foreground()
        assert PACKAGE + "/" in current, "Verification app is not foreground: " + current

    def capture(self, name):
        self.owns_foreground()
        (OUTPUT / (name + ".png")).write_bytes(self.adb("exec-out", "screencap", "-p").stdout)

    def stop(self):
        self.shell("am", "force-stop", PACKAGE)

    def start(self):
        result = self.shell("am", "start", "-W", "-n", ACTIVITY, "--ez", "local_node_app", "true")
        assert "Error:" not in result, result
        self.owns_foreground()

    def put_private(self, source, destination):
        self.shell("mkdir", "-p", TRANSFER)
        remote = TRANSFER + "/" + source.name
        self.adb("push", source, remote)
        self.shell("chmod", "644", remote)
        self.private("cp", remote, destination)
        self.shell("rm", "-f", remote)

    def prepare(self, apk, bundle):
        sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
        if not sdk:
            sdk = next(line.split("=", 1)[1] for line in
                       (ROOT / "droid/local.properties").read_text().splitlines() if line.startswith("sdk.dir="))
        aapt = sorted(Path(sdk).glob("build-tools/*/aapt"))[-1]
        manifest = subprocess.check_output([str(aapt), "dump", "badging", str(apk)], text=True)
        assert re.search(r"^package: name='([^']+)'", manifest, re.M)[1] == PACKAGE
        assert "application-debuggable" in manifest, "Only the separate debug verification instance is allowed"
        assert not self.state.get("isolated"), "Restore the previous Library test before starting another"
        current = self.foreground()
        assert " xyz.waozi.inbe/" not in current, "The owner's regular app is foreground"
        for path in (PROFILE, DRIVER):
            assert not self.exists(path + ".library-preserved"), "Preserved test data already exists: " + path
        self.stop()
        # Install before isolating data: package replacement may restore data
        # or prepare the app's files, and must not touch the fresh test profile.
        self.adb("install", "-r", "-t", apk, timeout=180)
        self.state = dict(originating_chat="-1000000002", task="codex-projects-library-bookshelf",
                          time=datetime.now(timezone.utc).isoformat(), foreground_before=current,
                          apk_sha256=hashlib.sha256(apk.read_bytes()).hexdigest(),
                          library_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(),
                          isolated=True, preserved=[], external=[])
        self.save()
        for path in (PROFILE, DRIVER):
            if self.exists(path):
                self.private("mv", path, path + ".library-preserved")
                self.state["preserved"].append(path)
                self.save()
        self.private("mkdir", "-p", DRIVER, PROFILE)
        self.private("touch", DRIVER + "/.library-test", PROFILE + "/.library-test")
        self.private("mkdir", "-p", EXTERNAL)
        names = self.private("ls", "-1", EXTERNAL).splitlines()
        for name in names:
            if name.endswith(".zx"):
                assert re.fullmatch(r"[A-Za-z0-9_.-]+", name), "Unexpected local bundle name"
                path = EXTERNAL + "/" + name
                assert not self.exists(path + ".library-preserved")
                self.private("mv", path, path + ".library-preserved")
                self.state["external"].append(path)
                self.save()
        self.put_private(bundle, EXTERNAL + "/library.zx")
        self.state["local_bundle_added"] = True
        self.save()
        self.start()
        driver = AndroidDriver(self)
        driver.tree()
        self.stop()
        self.private("touch", PROFILE + "/.library-test")
        database = OUTPUT / "test-profile.db"
        for suffix in ("", "-wal"):
            result = self.adb("exec-out", "run-as", PACKAGE, "cat", PROFILE + "/inbe.db" + suffix, check=False)
            local = Path(str(database) + suffix)
            if result.returncode == 0:
                local.write_bytes(result.stdout)
            else:
                local.unlink(missing_ok=True)
        with sqlite3.connect(database) as db:
            user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
            seeded = dict(language="en", language_system=0, language_setup_done=1, apps_setup_done=1,
                          tutorial_seen=1, habits_guide_seen=1, lumi_guides_seen=127, launcher_guide_seen=1,
                          package_updates_allowed=0, apps_last_update_check=1900000000,
                          node_apps_checked_at=int(time.time()), audio_enabled=0, sync_enabled=0,
                          node_app_slot_0="library", app_used_library=1)
            for key, value in seeded.items():
                db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                           "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user, key, str(value)))
            db.commit()
            standalone = OUTPUT / "seeded-profile.db"
            with sqlite3.connect(standalone) as target:
                db.backup(target)
        self.put_private(standalone, PROFILE + "/inbe.db")
        assert self.private("sha256sum", PROFILE + "/inbe.db").split()[0] == hashlib.sha256(standalone.read_bytes()).hexdigest()
        self.private("rm", "-f", PROFILE + "/inbe.db-wal", PROFILE + "/inbe.db-shm")
        self.start()
        return AndroidDriver(self)

    def restore(self):
        if not self.state.get("isolated"):
            return
        self.stop()
        for path in (PROFILE, DRIVER):
            if path in self.state.get("cleaned", []):
                continue
            if self.exists(path):
                assert self.exists(path + "/.library-test"), "Refusing to remove unmarked data: " + path
                self.private("rm", "-rf", path)
            if path in self.state["preserved"]:
                self.private("mv", path + ".library-preserved", path)
            self.state.setdefault("cleaned", []).append(path)
            self.save()
        if self.state.get("local_bundle_added") and self.exists(EXTERNAL + "/library.zx"):
            digest = self.private("sha256sum", EXTERNAL + "/library.zx").split()[0]
            assert digest == self.state["library_sha256"], "Local Library bundle changed during the test"
            self.private("rm", "-f", EXTERNAL + "/library.zx")
        for path in list(self.state["external"]):
            self.private("mv", path + ".library-preserved", path)
            self.state["external"].remove(path)
            self.save()
        self.shell("rm", "-rf", TRANSFER)
        self.state["isolated"] = False
        self.state["restored"] = True
        self.save()


class AndroidDriver(UiDriver):
    """UiDriver's assertions and gestures, with Android's private file transport."""
    def __init__(self, phone):
        self.phone = phone
        super().__init__(OUTPUT / "driver")

    def reset(self):
        self.phone.private("rm", "-f", DRIVER + "/command", DRIVER + "/reply", DRIVER + "/reply.tmp")

    def send(self, verb, timeout=30, **fields):
        if verb in ("press", "pointer", "type", "key"):
            self.phone.owns_foreground()
        self.serial += 1
        parts = [str(self.serial), verb]
        for name, value in fields.items():
            if value is not None:
                parts.append(name + "=" + escape(int(value) if isinstance(value, bool) else value))
        local = self.directory / "command"
        local.write_text("\t".join(parts) + "\n")
        self.phone.private("rm", "-f", DRIVER + "/reply")
        self.phone.put_private(local, DRIVER + "/command.tmp")
        self.phone.private("mv", DRIVER + "/command.tmp", DRIVER + "/command")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = self.phone.adb("exec-out", "run-as", PACKAGE, "cat", DRIVER + "/reply", check=False)
            if result.returncode == 0:
                try:
                    reply = json.loads(result.stdout)
                except json.JSONDecodeError:
                    # The native driver can still be writing its response.
                    # Keep the pending serial until a complete JSON reply arrives.
                    time.sleep(.05)
                    continue
                if reply.get("serial") == self.serial:
                    self.phone.private("rm", "-f", DRIVER + "/reply")
                    if verb == "tree":
                        self.last = reply
                    return reply
            time.sleep(.05)
        raise self._failure("Kryon Android driver did not answer: " + verb)


def chapter_text(number):
    source = (ROOT / "apps/library/tao_te_ching.zi").read_text()
    return re.search(rf"^TAO_{number} :: #string END\n(.*?)\nEND;$", source, re.M | re.S)[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "restore"))
    parser.add_argument("--apk", type=Path)
    parser.add_argument("--bundle", type=Path, default=ROOT / "build/node-apps/library.zx")
    args = parser.parse_args()
    phone = Device()
    if args.action == "restore":
        phone.restore()
        return
    if args.apk is None:
        parser.error("run requires --apk")
    try:
        driver = phone.prepare(args.apk.resolve(strict=True), args.bundle.resolve(strict=True))
        cases = LibraryReaderCases(driver, chapter_text, capture=phone.capture)
        saved = cases.exercise()
        # Also enter through Android's real touch path, independently of the
        # shared widget test driver used for the detailed reader cases.
        area = driver.wait(key=27502)
        left = int(area["visible_x"] + area["visible_width"] * .12)
        right = int(area["visible_x"] + area["visible_width"] * .88)
        middle = int(area["visible_y"] + area["visible_height"] / 2)
        before = cases.page_number()
        phone.owns_foreground()
        phone.shell("input", "swipe", right, middle, left, middle, 250)
        cases.wait_page(before + 1)
        phone.capture("reader-touch")
        phone.shell("input", "swipe", left, middle, right, middle, 250)
        cases.wait_page(before)
        phone.stop()
        phone.start()
        driver.reset()
        cases.resume(saved)
        phone.state["result"] = "passed"
        phone.state["cases"] = ["wooden bookshelf with cover title and author", "swipes and arrows",
                                "Android touch swipes", "inline icon tools", "contents", "font reflow",
                                "saved page", "selected passage and multiline note", "book theme", "cold restart"]
        phone.save()
        print("Moto Library: cover shelf, paging, contents, font reflow, resume and annotations passed through Kryon's driver")
    finally:
        phone.restore()


if __name__ == "__main__":
    main()
