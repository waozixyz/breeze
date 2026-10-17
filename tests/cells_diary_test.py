"""Verify standalone Diary editing, restart and calendar on an owned test window."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "build/cells-diary-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
assert int(os.environ["DISPLAY"].split(":")[-1].split(".")[0]) >= 300
ENV = os.environ.copy()
ENV.update(APP_NO_TRAY="1", YUE_DESKTOP_RECOVERY="0")
ENV.pop("INBE_DIARY_IMPORT", None)
ENV.pop("HARMONY_DATA_ROOT", None)


def command(*args):
    return subprocess.run(args, env=ENV, text=True, capture_output=True,
                          check=True, timeout=5).stdout.strip()


def tap(window, x, y):
    command("xdotool", "mousemove", "--window", window, str(x), str(y))
    command("xdotool", "mousedown", "1")
    time.sleep(0.08)
    command("xdotool", "mouseup", "1")
    time.sleep(0.3)


def capture(window, name):
    raw = OUTPUT / f"{name}.xwd"
    command("xwd", "-silent", "-id", window, "-out", str(raw))
    command("convert", str(raw), str(OUTPUT / f"{name}.png"))
    raw.unlink()


def pixels_like(path, matches):
    with Image.open(path) as image:
        rgb = image.convert("RGB")
    pixels = rgb.load()
    return [(x, y) for y in range(rgb.height) for x in range(rgb.width) if matches(pixels[x, y])]


def red_pixels(path):
    return pixels_like(path, lambda color: color[0] > 200 and color[1] < 100 and color[2] < 120)


def purple_pixels(path):
    return pixels_like(path, lambda color: abs(color[0] - 128) < 24 and abs(color[1] - 72) < 24 and
                       abs(color[2] - 176) < 24)


def wait_for_text(entry, matches, message):
    deadline = time.monotonic() + 10
    while not matches(json.loads(entry.read_text())["text"]):
        assert time.monotonic() < deadline, message
        time.sleep(0.1)


@contextlib.contextmanager
def application(profile, label, import_source=None, size=(900, 720)):
    with (OUTPUT / f"{label}.log").open("w") as log:
        environment = ENV | {"APP_DATA_ROOT": str(profile)}
        if import_source is not None:
            environment["INBE_DIARY_IMPORT"] = str(import_source)
        app = subprocess.Popen([sys.argv[1], "--bundle", str(ROOT / "build/cells/diary.zib")],
                               cwd=ROOT, env=environment,
                               stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                assert app.poll() is None, "Diary exited before mapping its window"
                result = subprocess.run(["xdotool", "search", "--all", "--onlyvisible", "--pid", str(app.pid)],
                                        env=ENV, text=True, capture_output=True, timeout=2)
                if result.returncode == 0 and result.stdout.strip():
                    window = result.stdout.splitlines()[0]
                    break
                time.sleep(0.1)
            else:
                raise AssertionError("Standalone Diary window did not appear")
            command("xdotool", "windowsize", window, str(size[0]), str(size[1]))
            command("xdotool", "windowfocus", window)
            time.sleep(1.5)
            # Fresh profiles can show the first-run Lumi guide over the editor.
            tap(window, size[0] // 2 + 112, 114)
            yield window
            assert app.poll() is None, "Diary crashed"
        finally:
            if app.poll() is None:
                app.terminate()
                try:
                    app.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    app.kill()
                    app.wait(timeout=3)


with tempfile.TemporaryDirectory(prefix="inbe-diary-ui-") as temporary:
    profile = Path(temporary)
    # The desktop picker runs zenity, which answers with the picked file.
    picked = profile / "IMG_DIARY.jpg"
    Image.new("RGB", (400, 300), (128, 72, 176)).save(picked, "JPEG", quality=90)
    tools = profile / "bin"
    tools.mkdir()
    (tools / "zenity").write_text(f"#!/bin/sh\nprintf '%s\\n' '{picked}'\n")
    (tools / "zenity").chmod(0o755)
    ENV["PATH"] = f"{tools}:{ENV['PATH']}"
    with application(profile, "edit") as window:
        capture(window, "standalone")
        tap(window, 430, 280)
        command("xdotool", "type", "--clearmodifiers", "A saved Diary entry")
        deadline = time.monotonic() + 10
        while True:
            entries = list((profile / "diary").glob("*/????-??-??.json"))
            if entries and json.loads(entries[0].read_text())["text"] == "A saved Diary entry":
                entry = entries[0]
                break
            assert time.monotonic() < deadline, "Diary text was not saved"
            time.sleep(0.1)
        capture(window, "saved")
        # Typing within a moment of another change joins its undo step.
        time.sleep(1.2)
        tap(window, 700, 86)  # Insert current time.
        wait_for_text(entry, lambda text: "**" in text, "Time insertion was not saved")
        with_time = json.loads(entry.read_text())["text"]
        tap(window, 556, 86)  # Undo.
        wait_for_text(entry, lambda text: text == "A saved Diary entry", "Undo did not restore the entry")
        tap(window, 604, 86)  # Redo.
        wait_for_text(entry, lambda text: text == with_time, "Redo did not restore the time")
        tap(window, 652, 86)  # Spelling needs a signed-in account.
        time.sleep(0.5)
        capture(window, "spelling-without-account")
        assert json.loads(entry.read_text())["text"] == with_time, "Spelling changed the entry without an account"
        # The photo button adds the picked photo to the account's photo
        # library, under the day it was added, and embeds its place there on
        # its own line at the caret, which is at the entry's end.
        tap(window, 748, 86)
        wait_for_text(entry, lambda text: "](photos/" in text, "A picked photo was not embedded")
        digest = hashlib.sha256(picked.read_bytes()).hexdigest()
        place = time.strftime("photos/%Y/%m/%d/") + digest + ".jpg"
        with_photo = json.loads(entry.read_text())
        assert with_photo["text"] == with_time + "\n![IMG_DIARY.jpg](" + place + ")\n", with_photo["text"]
        assert with_photo["photos"] == [], "A library photo was listed as a Diary file"
        library = list((profile / "media").glob("*/" + digest))
        assert len(library) == 1 and library[0].read_bytes() == picked.read_bytes()
        time.sleep(0.5)
        capture(window, "picked-photo")
        purple = purple_pixels(OUTPUT / "picked-photo.png")
        assert len(purple) > 20000, "The picked photo is not drawn inside the entry"
        # A click on the photo puts the caret at the end of its line; text
        # typed there joins the photo's line, and the photo stays.
        tap(window, sum(x for x, y in purple) // len(purple), sum(y for x, y in purple) // len(purple))
        command("xdotool", "type", "--clearmodifiers", " right after")
        wait_for_text(entry, lambda text: ") right after\n" in text, "Text typed after the photo was not saved")
        after_photo = json.loads(entry.read_text())
        assert after_photo["text"] == with_time + "\n![IMG_DIARY.jpg](" + place + ") right after\n", after_photo["text"]
        time.sleep(0.5)
        capture(window, "text-after-photo")
        assert len(purple_pixels(OUTPUT / "text-after-photo.png")) > 20000, \
            "The photo was not drawn while its line was edited"
        # Away from that line its Markdown hides and the photo stays under
        # the text.
        command("xdotool", "key", "--clearmodifiers", "ctrl+End")
        time.sleep(0.5)
        capture(window, "text-beside-photo")
        assert len(purple_pixels(OUTPUT / "text-beside-photo.png")) > 20000, \
            "The photo was not drawn under the text typed after it"
        saved = json.loads(entry.read_text())
        tap(window, 288, 86)  # Calendar.
        capture(window, "calendar")
    with application(profile, "restart") as window:
        capture(window, "restored")
        assert json.loads(entry.read_text()) == saved
        tap(window, 748, 34)  # Next day saves before changing selection.
        capture(window, "today-limit")
        assert list((profile / "diary").glob("*/????-??-??.json")) == [entry]
        assert json.loads(entry.read_text()) == saved
    source = profile / "harmony-fixture"
    source.mkdir()
    original = dict(saved, text="Harmony entry", photos=[dict(file="photo-local.bin", name="A photo")])
    (source / entry.name).write_text(json.dumps(original))
    photo_path = source / "photo-local.bin"
    Image.new("RGB", (64, 64), (241, 52, 71)).save(photo_path, format="PNG")
    photo_bytes = photo_path.read_bytes()
    (source / "photo-link.bin").symlink_to(source / "photo-local.bin")
    migrated = profile / "migrated-profile"
    with application(migrated, "migration", source) as window:
        targets = list((migrated / "diary").glob("*/" + entry.name))
        assert len(targets) == 1
        target = targets[0]
        assert json.loads(target.read_text()) == original
        assert (target.parent / "photo-local.bin").read_bytes() == photo_bytes
        assert not (target.parent / "photo-link.bin").exists()
        assert json.loads((source / entry.name).read_text()) == original
        command("xdotool", "mousemove", "--window", window, "700", "680")
        command("xdotool", "click", "--repeat", "10", "--delay", "80", "5")
        time.sleep(0.5)
        capture(window, "imported-photo")
        with Image.open(OUTPUT / "imported-photo.png") as image:
            colors = image.convert("RGB").getcolors(image.width * image.height)
            red = sum(count for count, color in colors
                      if color[0] > 200 and color[1] < 100 and color[2] < 120)
            assert red > 1000, "Imported Diary photo did not render from its private asset"
    (source / entry.name).write_text(json.dumps(dict(original, text="Changed source")))
    with application(migrated, "migration-restart", source):
        assert json.loads(target.read_text()) == original, "import overwrote an existing Inbe entry"

    # An older entry's photo list reads as photos inside the entry at phone
    # width and the reporter's scale in both sage modes, one of them not on
    # this device. Viewing writes nothing; a tap on a photo under the entry
    # embeds it at the caret, which starts at the entry's end.
    blue_path = source / "photo-blue.bin"
    Image.new("RGB", (100, 60), (24, 90, 220)).save(blue_path, format="JPEG")
    (source / entry.name).write_text(json.dumps(dict(original, photos=[
        *original["photos"], dict(file=blue_path.name, name="Blue photo"),
        dict(file="photo-missing.bin", name="Missing photo")])))
    files = ["photo-local.bin", blue_path.name, "photo-missing.bin"]
    for dark in (0, 1):
        phone = profile / f"phone-{dark}"
        phone_source = profile / f"phone-source-{dark}"
        phone_source.mkdir()
        for name in (entry.name, "photo-local.bin", blue_path.name):
            (phone_source / name).write_bytes((source / name).read_bytes())
        # Initialize an isolated profile before setting its appearance.
        with application(phone, f"phone-init-{dark}", phone_source):
            pass
        with sqlite3.connect(phone / "inbe.db") as database:
            owner = database.execute("select user_id from settings limit 1").fetchone()[0]
            for key, value in {"theme": 7, "theme_source": 0, "theme_mode": 1 + dark,
                               "dark_mode": dark, "ui_scale": 10}.items():
                database.execute("insert into settings(user_id,key,value,updated_at) values(?,?,?,?) "
                                 "on conflict(user_id,key) do update set value=excluded.value",
                                 (owner, key, str(value), int(time.time())))
        with application(phone, f"sage-{dark}", size=(390, 844)) as window:
            phone_entry = next((phone / "diary").glob("*/" + entry.name))
            stored = phone_entry.read_text()
            time.sleep(0.5)
            capture(window, f"sage-{dark}-inline")
            red = red_pixels(OUTPUT / f"sage-{dark}-inline.png")
            # The photo inside the entry is far larger than its tile below.
            assert len(red) > 20000, "Photo not drawn inside the entry at phone scale"
            bottom = max(y for x, y in red)
            tile = [(x, y) for x, y in red if y > bottom - 60]
            assert 1000 < len(tile) < 20000, "The day's photos are not shown under the entry"
            assert phone_entry.read_text() == stored, "Viewing the day rewrote its entry"
            tap(window, sum(x for x, y in tile) // len(tile), sum(y for x, y in tile) // len(tile))
            deadline = time.monotonic() + 5
            while json.loads(phone_entry.read_text())["text"].count("](diary:photo-local.bin)") != 2:
                assert time.monotonic() < deadline, "A tapped photo was not embedded in the entry"
                time.sleep(0.1)
            saved_photo = json.loads(phone_entry.read_text())
            assert saved_photo["text"].startswith(original["text"] + "\n\n![A photo](diary:photo-local.bin)")
            assert [row["file"] for row in saved_photo["photos"]] == files
        with application(phone, f"sage-{dark}-restart", size=(390, 844)):
            assert json.loads(phone_entry.read_text()) == saved_photo
            assert (phone_entry.parent / "photo-local.bin").read_bytes() == photo_bytes
    print("Standalone Diary: native editing, delayed save, time insertion, undo, redo, spelling without an account, a picked photo in the photo library and inside the entry, text typed right after the photo, calendar, restart and day navigation passed")
    print("Harmony import: text and photo bytes copied, originals preserved, symlinks skipped and existing entries retained")
    print("Diary photos: older photo lists inside the entry, a missing file, no writes on viewing, a tapped day photo embedded, and restart at phone width in light/dark sage passed")
