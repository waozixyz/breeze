#!/usr/bin/env python3
"""Exercise launcher pins on the development Moto, preserving its debug profile.

Run through desktop_run on omega. Never operates the Pixel or production Inbe.
The separate prepare/restore steps keep recovery possible after an interrupted
test. Private backups and screenshots stay in the project's ignored backup/.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import sqlite3
import subprocess
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "backup/launcher/moto"
PACKAGE = "xyz.waozi.inbe.debug"
ACTIVITY = "xyz.waozi.inbe.MainActivity"
SERIAL = "ZE2223BQZT"
PROFILE = "files/inbe"
PRESERVED = "files/inbe.launcher-preserved"
spec = importlib.util.spec_from_file_location("phone_check", ROOT / "scripts/phone-check.py")
phone_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(phone_check)


class LauncherDevice:
    def __init__(self):
        for key in ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS"):
            os.environ.pop(key, None)
        self.phone = phone_check.Phone("local", SERIAL)
        self._nodes_cache = None
        self._nodes_time = 0.0
        for attempt in range(10):
            try:
                if self.phone.adb("get-state").decode().strip() == "device":
                    break
            except subprocess.CalledProcessError:
                pass
            time.sleep(1)
        else:
            raise AssertionError("Moto is not connected and authorized")
        self.wait(lambda: self.shell("getprop", "ro.product.model").strip() == "moto e6 play", "development Moto identity")
        self.wait(lambda: self.shell("getprop", "ro.build.version.sdk").strip() == "28", "Android 9 identity")
        OUTPUT.mkdir(parents=True, exist_ok=True)
        self.state_path = OUTPUT / "state.json"
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {}

    def shell(self, *args):
        if args[0] in ("input", "am", "wm"):
            self._nodes_cache = None
        read_only = args[0] in ("getprop", "dumpsys", "cat", "date", "uiautomator", "pm")
        if args[0] == "run-as" and len(args) > 2:
            read_only = args[2] in ("ls", "cat", "sha256sum")
        for attempt in range(8 if read_only else 1):
            try:
                return self.phone.shell(*args, timeout=20 if read_only else 60)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                if not read_only or attempt == 7:
                    raise
                subprocess.run(["adb", "-s", SERIAL, "reconnect", "offline"], capture_output=True, timeout=15)
                time.sleep(1)

    def private(self, *args):
        return self.shell("run-as", PACKAGE, *args)

    def save(self):
        pending = self.state_path.with_suffix(".tmp")
        pending.write_text(json.dumps(self.state, indent=2) + "\n")
        pending.replace(self.state_path)

    def case(self, name, **details):
        self.state.setdefault("cases", []).append(dict(name=name, apk_sha256=self.state.get("apk_sha256"), **details))
        self.save()
        print(name, flush=True)

    def stop(self):
        self.shell("am", "force-stop", PACKAGE)

    def start(self, name=None):
        args = ["am", "start", "-W", "-n", PACKAGE + "/" + ACTIVITY]
        if name:
            args += ["-a", "xyz.waozi.inbe.action.OPEN_APP", "--es", "app_name", name,
                     "-d", "inbe-app://launch/" + name]
        else:
            args += ["-a", "android.intent.action.MAIN", "-c", "android.intent.category.LAUNCHER"]
        result = self.shell(*args)
        assert "Error:" not in result, result
        self.wait(lambda: any(node.get("package") == PACKAGE and self.label(node) for node in self.nodes()), "app rendered", seconds=40)

    def wait(self, callback, description, seconds=25):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            value = callback()
            if value:
                return value
            time.sleep(.5)
        raise AssertionError("Timed out: " + description)

    def focused(self):
        return next((line.strip() for line in self.shell("dumpsys", "window", "windows").splitlines()
                     if "mCurrentFocus=" in line), "")

    def snapshot(self, name, launcher=False):
        focus = self.focused()
        allowed = (PACKAGE + "/", "com.motorola.launcher3/", "com.android.launcher3/") if launcher else (PACKAGE + "/",)
        assert any(package in focus for package in allowed), "Unexpected foreground: " + focus
        data = self.phone.adb("exec-out", "screencap", "-p")
        (OUTPUT / (name + ".png")).write_bytes(data)
        return name

    def nodes(self):
        if self._nodes_cache is not None and time.monotonic() - self._nodes_time < 1:
            return self._nodes_cache
        path = "/data/local/tmp/inbe-launcher-test.xml"
        for attempt in range(5):
            result = self.shell("uiautomator", "dump", "--compressed", path)
            if "dumped to" in result:
                xml = self.shell("cat", path)
                self._nodes_cache = list(ET.fromstring(xml).iter("node"))
                self._nodes_time = time.monotonic()
                return self._nodes_cache
            time.sleep(1)
        raise AssertionError("Android did not expose the current UI tree")

    @staticmethod
    def label(node):
        return node.get("text") or node.get("content-desc", "")

    @staticmethod
    def bounds(node):
        values = tuple(map(int, re.findall(r"\d+", node.get("bounds", ""))))
        assert len(values) == 4
        return values

    def tap(self, node):
        left, top, right, bottom = self.bounds(node)
        self.shell("input", "tap", (left + right) // 2, (top + bottom) // 2)
        time.sleep(.8)

    def find(self, label):
        return [node for node in self.nodes() if node.get("text") == label or node.get("content-desc") == label]

    def tap_label(self, label):
        nodes = self.wait(lambda: self.find(label), label)
        interactive = [node for node in nodes if node.get("clickable") == "true"]
        self.tap((interactive or nodes)[-1])

    def drawer(self, label):
        assert self.state.get("isolated")
        # A fresh activity also recovers a menu left open by an interrupted
        # test, whose modal correctly hides the underlying navigation.
        self.stop()
        self.start()
        self.tap_label("Apps")
        self.tap_label("Find an app")
        self.shell("input", "text", shlex.quote(label))
        self.shell("input", "keyevent", "KEYCODE_BACK")
        self.wait(lambda: self.find("App options"), "filtered app options")

    def pin(self, name):
        assert self.state.get("isolated")
        labels = dict(lumi="Lumi", habits="Habits", practices="Practice", lists="Lists",
                      diary="Diary", leaderboard="Leaderboard")
        assert name in labels
        self.drawer(labels[name])
        self.snapshot("pin-" + name + "-before")
        self.tap_label("App options")
        self.wait(lambda: self.find("Install to launcher"), "pin menu item")
        self.snapshot("pin-" + name + "-menu")
        self.state["pending_pin"] = name
        self.save()
        self.tap_label("Install to launcher")
        time.sleep(1)
        self.snapshot("pin-" + name + "-requested", launcher=True)
        print(json.dumps([dict(label=self.label(node), bounds=node.get("bounds"),
                               kind=node.get("class"), package=node.get("package"))
                          for node in self.nodes() if self.label(node)], indent=2))

    def menu(self):
        self.drawer("Diary")
        assert not self.find("Install to launcher"), "Pin action is outside the menu"
        assert self.find("Clear search"), "Nonempty search has no clear action"
        self.snapshot("search-nonempty")
        self.tap_label("Clear search")
        assert not self.find("Clear search"), "Empty search still shows clear action"
        self.shell("input", "keyevent", "KEYCODE_BACK")
        for title in ("Diary", "Habits", "Lists", "Lumi", "Practice", "Leaderboard"):
            assert self.find(title), "Clearing search did not restore " + title
        self.snapshot("search-cleared")
        self.shell("input", "keyevent", "KEYCODE_BACK")
        self.drawer("Diary")
        search_field = self.find("Find an app")[0]
        self.tap_label("App options")
        assert self.find("Install to launcher") and self.find("Uninstall")
        self.snapshot("compact-options-menu")
        initial = "Unpin" if self.find("Unpin") else "Pin"
        changed = "Pin" if initial == "Unpin" else "Unpin"
        self.tap_label(initial)
        self.tap_label("App options")
        assert self.find(changed), "Pin toggle did not update the menu"
        self.tap_label(changed)
        self.tap_label("App options")
        assert self.find(initial), "Restoring the pin did not update the menu"
        self.tap(search_field)
        assert not self.find("Install to launcher")
        assert self.find("App options") and self.find("Find an app")
        self.case("Compact menu, outside dismissal and conditional clear search passed")

    def shortcuts(self):
        report = self.shell("dumpsys", "shortcut")
        (OUTPUT / "shortcuts-latest.txt").write_text(report)
        section = report.split("Package: " + PACKAGE + "  UID:", 1)[1].split("\n      Package:", 1)[0]
        self._shortcut_section = section
        return set(re.findall(r"ShortcutInfo \{id=inbe\.app\.([a-z0-9_-]+),", section))

    def confirm(self, cancel=False):
        name = self.state.get("pending_pin")
        assert name
        self.wait(lambda: self.find("Add to Home screen"), "Android pin confirmation")
        self.tap_label("CANCEL" if cancel else "ADD AUTOMATICALLY")
        self.wait(lambda: not self.find("Add to Home screen"), "pin dialog closed")
        ids = self.shortcuts()
        assert (name not in ids) if cancel else (name in ids), (name, ids)
        if not cancel:
            self.state.setdefault("created", [])
            if name not in self.state["created"]:
                self.state["created"].append(name)
        self.state.pop("pending_pin", None)
        self.save()
        self.case(("Canceled pin leaves no shortcut: " if cancel else "Android pinned shortcut: ") + name)

    def home_icon(self, name):
        titles = dict(diary="Diary", habits="Habits", practices="Practice", lists="Lists",
                      lumi="Lumi", leaderboard="Leaderboard")
        self.shell("input", "keyevent", "KEYCODE_WAKEUP")
        self.shell("wm", "dismiss-keyguard")
        self.shell("input", "keyevent", "KEYCODE_HOME")
        for direction in ("left", "left", "right", "right", "right", "right"):
            nodes = [node for node in self.nodes() if self.label(node) == titles[name]
                     and node.get("package") == "com.motorola.launcher3"
                     and node.get("clickable") == "true"]
            if nodes:
                return nodes[0]
            start, end = (610, 110) if direction == "left" else (110, 610)
            self.shell("input", "swipe", start, 750, end, 750, 350)
            time.sleep(.6)
        raise AssertionError("Home icon not found: " + name)

    def launch(self, name):
        assert name in self.state.get("created", [])
        self.stop()
        icon = self.home_icon(name)
        self.snapshot("home-" + name, launcher=True)
        self.tap(icon)
        self.wait(lambda: PACKAGE + "/" in self.focused(), "pinned app foreground")
        self.wait(lambda: len([node for node in self.nodes() if node.get("package") == PACKAGE and self.label(node)]) >= 2, "pinned app content", seconds=40)
        labels = [self.label(node) for node in self.nodes() if node.get("package") == PACKAGE]
        assert "Apps" not in labels, "Harness navigation is visible in pinned " + name
        assert len([label for label in labels if label]) >= 2, "Pinned app has no content"
        self.state.setdefault("launch_labels", {})[name] = labels
        self.save()
        self.snapshot("standalone-" + name)
        if name == "diary":
            assert "Calendar" in labels and "Attach photo" in labels
            text = subprocess.run(["tesseract", str(OUTPUT / "standalone-diary.png"), "stdout"],
                                  check=True, capture_output=True, text=True).stdout
            assert "Launcher device test: preserved Diary entry." in text, text
        self.shell("input", "keyevent", "KEYCODE_HOME")
        self.tap(self.home_icon(name))
        self.wait(lambda: PACKAGE + "/" in self.focused(), "warm pinned app foreground")
        assert not self.find("Apps")
        self.snapshot("warm-" + name)
        self.start()
        assert self.find("Apps"), "Normal Inbe launch did not restore navigation"
        self.case("Real home icon cold launch, resume and normal Inbe return: " + name)

    def duplicate(self):
        before = self.shortcuts()
        assert "diary" in before
        self.drawer("Diary")
        self.tap_label("App options")
        self.tap_label("Install to launcher")
        self.wait(lambda: self.find("Added to your launcher."), "existing shortcut updated")
        assert PACKAGE + "/" in self.focused(), "Duplicate install opened a new confirmation"
        assert self.shortcuts() == before, "Duplicate install changed shortcut identities"
        self.snapshot("duplicate-updates-existing")
        self.case("Installing again updates the existing home shortcut without a duplicate")

    def switch(self):
        expected = self.state["launch_labels"]
        for name in ("diary", "lists", "habits", "practices", "lumi", "leaderboard"):
            other = {label for key, labels in expected.items() if key != name for label in labels}
            unique = {label for label in expected[name] if label} - other
            assert unique, "No distinct UI to verify for " + name
            self.tap(self.home_icon(name))
            self.wait(lambda: any(self.label(node) in unique for node in self.nodes()
                                  if node.get("package") == PACKAGE), "warm switch to " + name, seconds=40)
            assert not self.find("Apps")
            self.snapshot("switch-" + name)
        self.case("Warm switching between all six home icons opens the correct app")

    def run(self):
        assert self.state.get("isolated") and self.state.get("apk_install_verified")
        assert not self.state.get("pending_pin"), "Resolve the pending confirmation before continuing"
        cases = self.state.get("cases", [])
        last_update = max((index for index, case in enumerate(cases)
                           if case["name"] == "Updated debug APK verified on device"), default=-1)
        verified = {case["name"] for case in cases[last_update + 1:]}
        if "Compact menu, outside dismissal and conditional clear search passed" not in verified:
            self.menu()
        for name in ("diary", "habits", "lists", "practices", "lumi", "leaderboard"):
            if name not in self.state.get("created", []):
                self.pin(name)
                self.confirm()
            if "Real home icon cold launch, resume and normal Inbe return: " + name not in verified:
                self.launch(name)
        if "Installing again updates the existing home shortcut without a duplicate" not in verified:
            self.duplicate()
        if "Warm switching between all six home icons opens the correct app" not in verified:
            self.switch()
        self.case("All six app home icons passed on the verified final debug APK")

    def observe_remove(self):
        assert self.state.get("isolated") and self.state.get("created")
        icon = self.home_icon(self.state["created"][0])
        left, top, right, bottom = self.bounds(icon)
        x, y = (left + right) // 2, (top + bottom) // 2
        hold = subprocess.Popen(["adb", "-s", SERIAL, "shell", "input", "swipe",
                                 str(x), str(y), str(x), str(y), "20000"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            time.sleep(1.5)
            self._nodes_cache = None
            targets = [node for node in self.nodes() if self.label(node) == "Remove"]
            assert len(targets) == 1, "Launcher did not expose its Remove target"
            self.snapshot("cleanup-remove-target", launcher=True)
            self.state["remove_target"] = self.bounds(targets[0])
            self.save()
        finally:
            hold.communicate(timeout=35)

    def cleanup(self):
        assert self.state.get("isolated") and not self.state.get("pending_pin")
        self.stop()
        if self.state.get("created") and not self.state.get("remove_target"):
            self.observe_remove()
        target = self.state.get("remove_target")
        assert not self.state.get("created") or (target and len(target) == 4)
        self.shortcuts()
        preserved = set(re.findall(r"ShortcutInfo \{id=([a-z0-9_.-]+),", self._shortcut_section))
        preserved = {name for name in preserved if not name.startswith("inbe.app.")}
        for name in list(self.state.get("created", [])):
            if name in self.shortcuts():
                icon = self.home_icon(name)
                left, top, right, bottom = self.bounds(icon)
                self.state["pending_removal"] = name
                self.save()
                self.shell("input", "draganddrop", (left + right) // 2, (top + bottom) // 2,
                           (target[0] + target[2]) // 2, (target[1] + target[3]) // 2, 700)
                self.wait(lambda: name not in self.shortcuts(), "remove only test icon " + name)
            self.state["created"].remove(name)
            self.state.pop("pending_removal", None)
            self.save()
        assert not self.shortcuts(), "A test shortcut remains pinned"
        after = set(re.findall(r"ShortcutInfo \{id=([a-z0-9_.-]+),", self._shortcut_section))
        assert after == preserved, "Cleanup changed an unrelated shortcut"
        self.case("Test home icons removed; original launcher shortcuts preserved")

    def update(self, apk):
        assert self.state.get("isolated")
        assert phone_check.apk_identity(apk)["package"] == PACKAGE
        self.stop()
        self.state["apk_sha256"] = hashlib.sha256(apk.read_bytes()).hexdigest()
        self.state["apk_install_verified"] = False
        self.save()
        self.phone.adb("install", "-r", str(apk), timeout=300)
        installed = self.shell("pm", "path", PACKAGE).strip().removeprefix("package:")
        assert self.shell("sha256sum", installed).split()[0] == self.state["apk_sha256"]
        self.state["apk_install_verified"] = True
        self.save()
        self.case("Updated debug APK verified on device")

    def settings(self, **values):
        assert self.state.get("isolated"), "Only the test profile may be edited"
        self.stop()
        database = OUTPUT / "test.db"
        for suffix in ("", "-wal"):
            result = subprocess.run(["adb", "-s", SERIAL, "exec-out", "run-as", PACKAGE,
                                     "cat", PROFILE + "/inbe.db" + suffix], capture_output=True, timeout=30)
            local = Path(str(database) + suffix)
            if result.returncode == 0:
                local.write_bytes(result.stdout)
            elif suffix:
                local.unlink(missing_ok=True)
            else:
                raise AssertionError("The isolated app did not create its database")
        with sqlite3.connect(database) as db:
            user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
            assert re.fullmatch(r"[a-z0-9-]+", user)
            for key, value in values.items():
                db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                           "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user, key, str(value)))
            db.commit()
            db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        self.put(database, PROFILE + "/inbe.db")
        self.private("rm", "-f", PROFILE + "/inbe.db-wal", PROFILE + "/inbe.db-shm")
        self.state["test_user"] = user
        self.save()
        return user

    def put(self, source, destination):
        transfer = "/data/local/tmp/inbe-launcher-fixture"
        self.phone.adb("push", str(source), transfer)
        self.private("cp", transfer, destination)
        self.shell("rm", "-f", transfer)

    def prepare(self, apk):
        assert not self.state.get("isolated"), "Restore the previous test profile first"
        identity = phone_check.apk_identity(apk)
        assert identity["package"] == PACKAGE
        assert not self.shortcuts(), "Preserve existing app pins; this check needs a clean debug launcher baseline"
        if (OUTPUT / "original-profile.tar").exists():
            snapshot = ROOT / "backup/snapshots" / ("launcher-moto-" + str(time.time_ns()))
            snapshot.mkdir(parents=True)
            for name in ("original-profile.tar", "previous-debug.apk", "state.json"):
                previous = OUTPUT / name
                if previous.exists():
                    shutil.copyfile(previous, snapshot / name)
        self.stop()
        entries = self.private("ls", "files").splitlines()
        assert Path(PRESERVED).name not in entries, "Preserved profile already exists; restore it first"
        self.state = dict(serial=SERIAL, identity=identity,
                          apk_sha256=hashlib.sha256(apk.read_bytes()).hexdigest(), cases=[])
        original = self.phone.adb("exec-out", "run-as", PACKAGE, "tar", "-cf", "-", PROFILE, timeout=300)
        (OUTPUT / "original-profile.tar").write_bytes(original)
        self.state["original_profile_sha256"] = hashlib.sha256(original).hexdigest()
        installed = self.shell("pm", "path", PACKAGE).strip().removeprefix("package:")
        assert installed.startswith("/data/app/") and installed.endswith("base.apk")
        self.phone.adb("pull", installed, str(OUTPUT / "previous-debug.apk"))
        self.save()
        self.private("mv", PROFILE, PRESERVED)
        self.state["isolated"] = True
        self.save()
        result = self.phone.adb("install", "-r", str(apk), timeout=300).decode()
        assert "Success" in result, result
        self.configure()

    def configure(self):
        assert self.state.get("isolated")
        installed = self.shell("pm", "path", PACKAGE).strip().removeprefix("package:")
        assert re.fullmatch(r"/data/app/[A-Za-z0-9_./=+-]+/base.apk", installed)
        actual = self.shell("sha256sum", installed).split()[0]
        assert actual == self.state["apk_sha256"], "Installed APK differs from the requested test build"
        self.state["apk_install_verified"] = True
        self.save()
        self.shell("input", "keyevent", "KEYCODE_WAKEUP")
        self.shell("wm", "dismiss-keyguard")
        self.start()
        self.wait(lambda: "inbe.db" in self.private("ls", PROFILE), "fresh database")
        values = dict(language="en", language_system=0, language_setup_done=1, apps_setup_done=1,
                      enabled_apps=63, main_tab=0, launcher_guide_seen=1, tutorial_seen=1,
                      lumi_introduced=1, lumi_guides_seen=127, habits_guide_seen=1, lumi_online=0,
                      package_updates_allowed=0, apps_last_update_check=1900000000,
                      guide_narration_enabled=0, voice_narration_enabled=0, sound_volume=0,
                      ui_scale=10)
        for name in ("lists", "habits", "practices", "diary", "lumi", "leaderboard"):
            values["app_used_" + name] = 1
        user = self.settings(**values)
        day = self.shell("date", "+%F").strip()
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", day)
        self.private("mkdir", "-p", PROFILE + "/diary/" + user)
        fixture = OUTPUT / "diary-fixture.json"
        fixture.write_text(json.dumps(dict(version=1, date=day,
            text="Launcher device test: preserved Diary entry.", photos=[])))
        self.put(fixture, PROFILE + "/diary/" + user + "/" + day + ".json")
        self.start()
        self.snapshot("prepared")
        self.case("New APK installed on Moto with original data set aside safely")

    def restore(self):
        assert self.state.get("isolated"), "No isolated profile to restore"
        self.stop()
        entries = self.private("ls", "files").splitlines()
        if Path(PRESERVED).name in entries:
            self.state["restore_started"] = True
            self.save()
            # Only the fresh profile created by prepare is removed. Its original
            # remains in the preserved directory and the binary backup above.
            self.private("rm", "-rf", PROFILE)
            self.private("mv", PRESERVED, PROFILE)
        else:
            # A disconnect after mv must never remove the restored original.
            assert self.state.get("restore_started") and Path(PROFILE).name in entries
        original = self.phone.adb("exec-out", "run-as", PACKAGE, "tar", "-cf", "-", PROFILE, timeout=300)
        assert hashlib.sha256(original).hexdigest() == self.state["original_profile_sha256"]
        self.state["isolated"] = False
        self.state["restore_started"] = False
        self.save()
        self.case("Original debug profile restored byte for byte; production app untouched")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "configure", "inspect", "pin", "confirm", "cancel", "menu", "launch", "update", "run", "cleanup", "restore"))
    parser.add_argument("--apk", type=Path)
    parser.add_argument("--app")
    args = parser.parse_args()
    device = LauncherDevice()
    if args.phase == "prepare":
        assert args.apk
        device.prepare(args.apk.resolve(strict=True))
    elif args.phase == "configure":
        device.configure()
    elif args.phase == "restore":
        device.restore()
    elif args.phase == "pin":
        device.pin(args.app)
    elif args.phase == "menu":
        device.menu()
    elif args.phase == "run":
        device.run()
    elif args.phase == "cleanup":
        device.cleanup()
    elif args.phase in ("confirm", "cancel"):
        device.confirm(cancel=args.phase == "cancel")
    elif args.phase == "launch":
        device.launch(args.app)
    elif args.phase == "update":
        assert args.apk
        device.update(args.apk.resolve(strict=True))
    else:
        assert device.state.get("isolated"), "Inspection is limited to the isolated test profile"
        device.snapshot("inspect", launcher=True)
        print(json.dumps([dict(label=device.label(node), bounds=node.get("bounds"),
                               kind=node.get("class"), package=node.get("package"))
                          for node in device.nodes() if device.label(node)], indent=2))


if __name__ == "__main__":
    try:
        main()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        def readable(value):
            return value.decode(errors="replace") if isinstance(value, bytes) else str(value or "")
        print("Device command failed:", error.cmd, flush=True)
        print(readable(error.stderr)[-2000:], flush=True)
        if error.stdout and error.cmd[3:4] != ["exec-out"]:
            print(readable(error.stdout)[-2000:], flush=True)
        raise
