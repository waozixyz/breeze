"""Run the same Diary bundle standalone and in Werkzeug on a private display."""
import argparse
import contextlib
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import time

from PIL import Image
from ui_driver import UiDriver


def wait(predicate, message, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(.05)
    raise AssertionError(message)


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--player", required=True, type=Path)
    parser.add_argument("--werk", required=True, type=Path)
    parser.add_argument("--diary", required=True, type=Path)
    parser.add_argument("--calculator", required=True, type=Path)
    parser.add_argument("--inbe", required=True, type=Path)
    args = parser.parse_args()
    for name, value in vars(args).items():
        setattr(args, name, value.resolve())
    root = Path(__file__).resolve().parents[1]
    output = root / "build/portable-apps-test"
    output.mkdir(parents=True, exist_ok=True)
    desktop = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS")
    assert all(not os.environ.get(key) for key in desktop), "Inherited desktop environment"
    env = {key: value for key, value in os.environ.items() if key not in desktop}
    for key in ("HARMONY_DATA_ROOT", "INBE_DIARY_IMPORT", "INBE_NODE_APP_FILE"):
        env.pop(key, None)
    env.update(YUE_DESKTOP_RECOVERY="0", SDL_AUDIODRIVER="dummy")

    with contextlib.ExitStack() as stack:
        temporary = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="portable-apps-")))
        diary = temporary / "diary.zx"
        calculator = temporary / "calculator.zx"
        shutil.copyfile(args.diary, diary)
        shutil.copyfile(args.calculator, calculator)
        assert not (temporary / "inbe.zx").exists()
        picked = temporary / "picked.png"
        Image.new("RGB", (400, 300), (128, 72, 176)).save(picked)
        tools = temporary / "bin"
        tools.mkdir()
        (tools / "zenity").write_text('#!/bin/sh\nprintf "%s\\n" "$PORTABLE_TEST_PHOTO"\n')
        (tools / "zenity").chmod(0o700)
        env.update(PATH=str(tools) + ":" + env["PATH"], PORTABLE_TEST_PHOTO=str(picked),
                   XDG_CACHE_HOME=str(temporary / "cache"),
                   WERK_ASSETS=str(args.werk.parent))
        display_log = stack.enter_context((output / "display.log").open("w"))
        display = subprocess.Popen(["Xvfb", "-noreset", "-displayfd", "1", "-screen", "0", "1200x900x24",
                                    "-nolisten", "tcp"], env=env, stdout=subprocess.PIPE, stderr=display_log)
        stack.callback(stop, display)
        number = display.stdout.readline().decode().strip()
        display.stdout.close()
        assert number.isdecimal(), "Private display failed"
        env["DISPLAY"] = ":" + number

        def command(*arguments):
            return subprocess.run(arguments, env=env, check=True, capture_output=True,
                                  text=True, timeout=5).stdout.strip()

        def tap(window, x, y):
            command("xdotool", "mousemove", "--window", window, str(x), str(y))
            command("xdotool", "mousedown", "1")
            time.sleep(.05)
            command("xdotool", "mouseup", "1")
            time.sleep(.12)

        def screenshot(window, name):
            raw = output / (name + ".xwd")
            target = output / (name + ".png")
            command("xwd", "-silent", "-id", window, "-out", str(raw))
            command("convert", str(raw), str(target))
            raw.unlink()
            return target

        def quit_window(window):
            # Send SDL's ordinary close request to this owned window only.
            x11 = ctypes.CDLL("libX11.so.6")
            x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
            x11.XOpenDisplay.restype = ctypes.c_void_p
            x11.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
            x11.XInternAtom.restype = ctypes.c_ulong
            x11.XSendEvent.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int,
                                      ctypes.c_long, ctypes.c_void_p]
            x11.XCloseDisplay.argtypes = [ctypes.c_void_p]

            class Message(ctypes.Structure):
                _fields_ = [("type", ctypes.c_int), ("serial", ctypes.c_ulong),
                            ("sent", ctypes.c_int), ("display", ctypes.c_void_p),
                            ("window", ctypes.c_ulong), ("message_type", ctypes.c_ulong),
                            ("format", ctypes.c_int), ("data", ctypes.c_long * 5)]

            class Event(ctypes.Union):
                _fields_ = [("message", Message), ("padding", ctypes.c_long * 24)]

            connection = x11.XOpenDisplay(env["DISPLAY"].encode())
            assert connection
            try:
                event = Event()
                event.message.type = 33
                event.message.display = connection
                event.message.window = int(window)
                event.message.message_type = x11.XInternAtom(connection, b"WM_PROTOCOLS", 0)
                event.message.format = 32
                event.message.data[0] = x11.XInternAtom(connection, b"WM_DELETE_WINDOW", 0)
                assert x11.XSendEvent(connection, int(window), 0, 0, ctypes.byref(event))
            finally:
                x11.XCloseDisplay(connection)

        @contextlib.contextmanager
        def application(host, profile, label, bundle=diary):
            child_env = env | {"KRYON_APP_DATA": str(profile), "WERK_DATA": str(profile)}
            arguments = ([str(args.player), str(bundle)] if host == "standalone" else
                         [str(args.werk), "--bundle", str(bundle)])
            with (output / (label + ".log")).open("w") as log:
                child = subprocess.Popen(arguments, cwd=temporary, env=child_env,
                                         stdout=log, stderr=subprocess.STDOUT)
                try:
                    def mapped():
                        assert child.poll() is None, f"{label} exited before mapping"
                        result = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(child.pid)],
                                                env=env, text=True, capture_output=True, timeout=2)
                        return result.stdout.splitlines()[0] if result.returncode == 0 else None
                    window = wait(mapped, label + " window missing")
                    command("xdotool", "windowsize", window, "900", "720")
                    command("xdotool", "windowfocus", window)
                    time.sleep(.5)
                    yield child, window
                finally:
                    stop(child)

        def document(profile):
            matches = list(profile.rglob("????-??-??.json"))
            return matches[0] if matches else None

        def text(profile):
            path = document(profile)
            return json.loads(path.read_text())["text"] if path else ""

        for host in ("standalone", "werk"):
            profile = temporary / host
            prefix = host + " entry"
            offset = 0 if host == "standalone" else 56
            with application(host, profile, host + "-edit") as (child, window):
                tap(window, 400, 250 + offset)
                command("xdotool", "type", "--clearmodifiers", prefix)
                wait(lambda: text(profile) == prefix, host + " edit did not save")
                tap(window, 748, 86 + offset)
                wait(lambda: "](photos/" in text(profile), host + " photo did not attach")
                image = screenshot(window, host + "-photo")
                with Image.open(image) as shot:
                    pixels = shot.convert("RGB").tobytes()
                    purple = sum(abs(r - 128) < 24 and abs(g - 72) < 24 and abs(b - 176) < 24
                                 for r, g, b in zip(pixels[::3], pixels[1::3], pixels[2::3]))
                assert purple > 20000, host + " photo did not render"
                stored = list(profile.rglob("*.png"))
                assert len(stored) == 1 and stored[0].read_bytes() == picked.read_bytes()
                tap(window, 400, 250 + offset)
                command("xdotool", "key", "ctrl+End")
                # Move the caret in a separate input frame before typing.
                time.sleep(.1)
                command("xdotool", "type", "--clearmodifiers", " saved on exit")
                quit_window(window)
                assert child.wait(timeout=10) == 0, host + " failed to close cleanly"
                wait(lambda: text(profile).endswith(" saved on exit"), host + " lost the last edit on close")
                expected = text(profile)
            with application(host, profile, host + "-restart") as (child, window):
                assert text(profile) == expected
                screenshot(window, host + "-restart")
            damaged = document(profile)
            damaged.write_bytes(b'{"text": damaged fixture')
            before = damaged.read_bytes()
            with application(host, profile, host + "-read-error") as (child, window):
                quit_window(window)
                assert child.wait(timeout=10) == 0
            assert damaged.read_bytes() == before, host + " overwrote an unreadable entry"
            assert hashlib.sha256(diary.read_bytes()).digest() == hashlib.sha256(args.diary.read_bytes()).digest()

        with application("standalone", temporary / "calculator-data", "calculator", calculator) as (child, window):
            screenshot(window, "calculator")
        rejected = subprocess.run([str(args.werk), "--bundle", str(calculator)], cwd=temporary,
                                  env=env | {"WERK_DATA": str(temporary / "reserved-id")},
                                  capture_output=True, timeout=10)
        assert rejected.returncode == 1, "External bundle replaced a built-in tool"

        driver = UiDriver(output / "driver")
        profile = temporary / "inbe"
        inbe_env = env | driver.environment() | {
            "APP_DATA_ROOT": str(profile), "APP_NO_TRAY": "1",
            "INBE_NODE_APP_FILE": str(calculator), "INBE_DEBUG_ROUTE": "1"}

        @contextlib.contextmanager
        def inbe(label, *arguments):
            log_path = output / (label + ".log")
            with log_path.open("w") as log:
                child = subprocess.Popen([str(args.inbe), *arguments], cwd=root, env=inbe_env,
                                         stdout=log, stderr=subprocess.STDOUT)
                driver.attach(child, log_path)
                try:
                    wait(lambda: (profile / "inbe.db").exists(), "Inbe did not create its test database")
                    wait(driver.tree, "Inbe did not draw")
                    yield child
                finally:
                    stop(child)

        with inbe("inbe-initialize"):
            pass
        with sqlite3.connect(profile / "inbe.db") as db:
            user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
            settings = dict(language="en", language_system=0, language_setup_done=1,
                            apps_setup_done=1, enabled_apps=63, lumi_introduced=1,
                            tutorial_seen=1, launcher_guide_seen=1, lumi_guides_seen=127,
                            main_tab=3, package_updates_allowed=0, apps_last_update_check=1900000000)
            for key, value in settings.items():
                db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                           "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user, key, str(value)))
        with inbe("inbe-calculator-install") as child:
            driver.press(label="Apps", role="button")
            def calculator_card():
                return next((node for node in driver.find(role="button")
                             if node["label"].lower() == "calculator" and node["width"] > 100), None)
            card = wait(calculator_card, "Local Calculator offer missing")
            driver.press(key=card["key"], label=card["label"])
            driver.wait(label="C", role="button")
            for label in ("2", "+", "3", "="):
                driver.press(label=label, role="button")
            driver.wait(label="5", role="text")
            driver.press(label="C", role="button")
            window = command("xdotool", "search", "--onlyvisible", "--pid", str(child.pid)).splitlines()[0]
            command("xdotool", "windowfocus", window)
            command("xdotool", "type", "--clearmodifiers", "7*6")
            command("xdotool", "key", "Return")
            driver.wait(label="42", role="text")
        with inbe("inbe-calculator-restart", "--app", "calculator"):
            driver.wait(label="C", role="button")
        print("One unchanged Diary bundle: standalone and Werkzeug editing, photo bytes/rendering, save on close and restart passed without inbe.zx")
        print("Werkzeug Calculator opened standalone and in Inbe, calculated by keypad and keyboard, and reopened after restart")


if __name__ == "__main__":
    main()
