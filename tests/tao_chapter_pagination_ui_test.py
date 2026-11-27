#!/usr/bin/env python3
"""Regress the actual Tao reader on an owned Xvfb with disposable account data."""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import tempfile
import time

from library_reader_cases import LibraryReaderCases
from ui_driver import UiDriver

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/library-reader-test/ui"
OUTPUT.mkdir(parents=True, exist_ok=True)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("binary", type=Path)
parser.add_argument("--package", type=Path, default=ROOT / "build/node-apps/library.zx")
parser.add_argument("--capture-baseline", action="store_true")
args = parser.parse_args()
CAPTURES = ROOT / "backup/tao-chapter-pagination" / ("before" if args.capture_baseline else "after")
CAPTURES.mkdir(parents=True, exist_ok=True)
DESKTOP_ENV = ("DISPLAY", "WAYLAND_DISPLAY", "WAYLAND_SOCKET", "XAUTHORITY",
               "DBUS_SESSION_BUS_ADDRESS", "DBUS_SYSTEM_BUS_ADDRESS", "GDK_DISPLAY",
               "SESSION_MANAGER", "XDG_RUNTIME_DIR")
env = {key: value for key, value in os.environ.items() if key not in DESKTOP_ENV}
env.update(HARMONY_DESKTOP_RECOVERY="0", YUE_DESKTOP_RECOVERY="0", ZIRAN_DESKTOP_RECOVERY="0",
           SDL_VIDEODRIVER="x11", SDL_AUDIODRIVER="dummy", LIBGL_ALWAYS_SOFTWARE="1", APP_NO_TRAY="1",
           https_proxy="http://127.0.0.1:9", http_proxy="http://127.0.0.1:9", NO_PROXY="")
source = (ROOT / "apps/library/src/native/tao_te_ching.zi").read_text()
titles = re.findall(r'^"([^"]+)",?$', source.split("TaoTeChingChapterTitle", 1)[0], re.M)


def chapter_text(number):
    return re.search(rf"^TAO_{number} :: #string END\n(.*?)\nEND;$", source, re.M | re.S)[1]


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


with contextlib.ExitStack() as stack:
    display_log = stack.enter_context((OUTPUT / "display.log").open("w"))
    display = subprocess.Popen(["Xvfb", "-noreset", "-displayfd", "1", "-screen", "0", "1280x1000x24",
                                "-nolisten", "tcp"], env=env, stdout=subprocess.PIPE, stderr=display_log)
    stack.callback(stop, display)
    number = display.stdout.readline().decode().strip()
    display.stdout.close()
    assert number.isdecimal() and display.poll() is None, "Private Xvfb did not start"
    server = Path(f"/proc/{display.pid}")
    assert server.stat().st_uid == os.getuid()
    assert server.joinpath("exe").resolve() == Path(shutil.which("Xvfb")).resolve()
    assert b"-displayfd\x001\x00" in server.joinpath("cmdline").read_bytes()
    env["DISPLAY"] = ":" + number
    driver = UiDriver(OUTPUT / "driver")
    env.update(driver.environment())
    profile = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="profile-", dir=OUTPUT)))
    env.update(APP_DATA_ROOT=str(profile), INBE_NODE_APP_FILE=str(args.package.resolve()))

    def command(*command_args):
        return subprocess.check_output(command_args, env=env, text=True, timeout=10).strip()

    def launch(name):
        log_path = OUTPUT / (name + ".log")
        log = stack.enter_context(log_path.open("w"))
        process = subprocess.Popen([str(args.binary.resolve())], cwd=ROOT, env=env,
                                   stdout=log, stderr=subprocess.STDOUT)
        stack.callback(stop, process)
        driver.attach(process, log_path)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            assert process.poll() is None, "Test app exited"
            found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(process.pid)],
                                   env=env, capture_output=True, text=True)
            if found.returncode == 0 and (profile / "inbe.db").exists():
                window = found.stdout.splitlines()[0]
                command("xdotool", "windowsize", window, "390", "640")
                driver.wait_idle(frames=3)
                return process, window
            time.sleep(.1)
        raise AssertionError("Test app did not map a window")

    app, window = launch("initialize")
    stop(app)
    with sqlite3.connect(profile / "inbe.db") as db:
        user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
        seeded = {"language": "en", "language_system": 0, "language_setup_done": 1, "apps_setup_done": 1,
                  "theme": 4, "ui_scale": 10, "tutorial_seen": 1, "habits_guide_seen": 1,
                  "lumi_guides_seen": 127, "launcher_guide_seen": 1, "package_updates_allowed": 0,
                  "apps_last_update_check": 1900000000, "node_apps_checked_at": int(time.time()),
                  "voice_narration_enabled": 0, "guide_narration_enabled": 0}
        for key, value in seeded.items():
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                       "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user, key, str(value)))
    app, window = launch("pagination")
    cases = LibraryReaderCases(driver, chapter_text)
    driver.press(label="Apps", role="button")
    cases.open_library()
    cases.open_book("Picture book")

    def open_chapter(chapter):
        cases.open_tools("Contents")
        for _ in range(82):
            matches = driver.find(key=27200 + chapter, role="button", visible=True)
            if matches:
                if not args.capture_baseline:
                    assert matches[0]["label"] == titles[chapter - 1], matches[0]
                driver.press(key=27200 + chapter, role="button")
                driver.wait_idle(frames=3)
                return
            driver.pointer(*driver.center(driver.wait(key=27605)), wheel=-3)
            driver.release_pointer()
            driver.wait_idle(frames=3)
        raise AssertionError("Chapter missing from contents")

    receipt = {"private_display": env["DISPLAY"], "xvfb_pid": display.pid, "app_pid": app.pid,
               "window": window, "binary_sha256": digest(args.binary.resolve()),
               "package_sha256": digest(args.package.resolve()), "pages": [], "captures": {}}
    receipt["sources"] = {str(path.relative_to(ROOT)): digest(path) for path in
                          [ROOT / "apps/library/src/native/library.zi", ROOT / "apps/library/src/native/books.zi",
                           ROOT / "apps/library/src/native/tao_te_ching.zi"]}
    if not args.capture_baseline:
        for name in ("library_model.zi", "library_ui.tsx"):
            folder = "ui" if name.endswith(".tsx") else "native"
            source = ROOT / "apps/library/src" / folder / name
            receipt["sources"][str(source.relative_to(ROOT))] = digest(source)
    if args.capture_baseline:
        for name in ("library.zi", "books.zi"):
            receipt["sources"]["apps/library/" + name] = digest(CAPTURES / name)

    def capture(name):
        assert display.poll() is None and app.poll() is None
        assert command("xdotool", "getwindowpid", window) == str(app.pid)
        path = CAPTURES / (name + ".png")
        command("import", "-window", window, str(path))
        receipt["captures"][path.name] = digest(path)

    def snapshot():
        heading = driver.wait(key=27501)
        art = bool(driver.find(key=27503, role="image", visible=True))
        if art and not args.capture_baseline:
            cases.picture_page(heading["label"])
            text = ""
            text_y = None
            text_height = 0
        else:
            text = cases.page_text()
            passage = driver.wait(key=27502)
            text_y = passage["y"]
            text_height = passage["height"]
        return {"heading": heading["label"], "text": text, "page": cases.page_label(),
                "art": art, "heading_y": heading["y"],
                "text_y": text_y, "text_height": text_height}

    def turn(direction):
        before = cases.page_number()
        driver.key(direction)
        cases.wait_page(before + (1 if direction == "right" else -1))

    def chapter_pages(chapter, capture_prefix=None):
        open_chapter(chapter)
        collected = []
        for index in range(30):
            page = snapshot()
            if not args.capture_baseline:
                assert page["heading"] == titles[chapter - 1], page
                assert page["art"] == (index == 0), page
            collected.append(page)
            if capture_prefix and index < 2:
                capture(f"{capture_prefix}-page-{index + 1}")
            turn("right")
            if driver.wait(key=27501)["label"] != page["heading"]:
                break
        else:
            raise AssertionError("Chapter never ended")
        assert len(collected) > 1, collected
        assert " ".join(" ".join(page["text"] for page in collected).split()) == " ".join(chapter_text(chapter).split())
        # Cross the chapter boundary backwards, then retrace every page.
        for expected in reversed(collected):
            turn("left")
            assert snapshot() == expected, (snapshot(), expected)
        if not args.capture_baseline:
            assert collected[1]["heading_y"] < collected[0]["heading_y"]
            assert collected[1]["text_height"] > collected[0]["text_height"]
        receipt["pages"].append(collected)
        return collected

    chapter_pages(39, "chapter-39")
    if not args.capture_baseline:
        turn("right")
        anchored = snapshot()
        # Theme keeps the page, bounds and progress exactly the same.
        driver.press(key=27704, role="button")
        driver.wait_idle(frames=3)
        assert snapshot() == anchored
        capture("theme-continuation")
        # Each reflow must retain the previous page's stable text position.
        for width, height in ((390, 550), (520, 844), (390, 640)):
            command("xdotool", "windowsize", window, str(width), str(height))
            driver.wait_idle(frames=5)
            page = snapshot()
            assert " ".join(anchored["text"].split()[:4]) in " ".join(page["text"].split()), (anchored, page)
            chapter_pages(39, f"resize-{width}-{height}")
            turn("right")
            anchored = snapshot()
        cases.open_tools("Font")
        for _ in range(5):
            driver.press(label="+", role="button")
        cases.close_tools()
        assert " ".join(anchored["text"].split()[:4]) in " ".join(snapshot()["text"].split())
        chapter_pages(39, "larger-font")
        turn("right")
        anchored = snapshot()
        cases.open_tools("Font")
        driver.press(key=27631)
        driver.press(label="Noto Sans", role="selectable")
        cases.close_tools()
        assert " ".join(anchored["text"].split()[:4]) in " ".join(snapshot()["text"].split())
        chapter_pages(39, "noto-font")
        turn("right")
        saved = snapshot()
        driver.press(label="Back", role="button")
        cases.open_book("Picture book")
        assert snapshot() == saved, (snapshot(), saved)
        stop(app)
        app, window = launch("resume")
        driver.press(label="Apps", role="button")
        cases.open_library()
        cases.open_book("Picture book")
        assert snapshot() == saved, (snapshot(), saved)
    (CAPTURES / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print("Tao chapter pagination baseline captured" if args.capture_baseline else
      "Tao separate centered picture/title pages, complete text, backward navigation, resize/font/theme reflow and resume: passed")
