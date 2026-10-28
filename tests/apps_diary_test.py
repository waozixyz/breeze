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

from ui_driver import UiDriver

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "build/apps-diary-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
assert int(os.environ["DISPLAY"].split(":")[-1].split(".")[0]) >= 400
ENV = os.environ.copy()
ENV.update(APP_NO_TRAY="1", YUE_DESKTOP_RECOVERY="0")
ENV.pop("INBE_DIARY_IMPORT", None)
ENV.pop("HARMONY_DATA_ROOT", None)
# Widgets are found and keys typed through Kryon's test driver.
driver = UiDriver(OUTPUT / "driver")


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


def ink_bottom(path, box):
    """The lowest row in box that differs from the box's background."""
    left, top, right, bottom = box
    with Image.open(path) as image:
        rgb = image.convert("RGB")
    pixels = rgb.load()
    background = pixels[right - 2, bottom - 2]
    lowest = -1
    for y in range(top, bottom):
        for x in range(left, right):
            if sum(abs(a - b) for a, b in zip(pixels[x, y], background)) > 90:
                lowest = y
                break
    return lowest


def library_has(profile, digest):
    """Whether the profile's photo library keeps the photo with this hash:
    its file, and its record in the account's entity data."""
    if not list((profile / "media").glob("*/" + digest)):
        return False
    with sqlite3.connect(profile / "inbe.db", timeout=3) as database:
        return database.execute("select count(*) from settings where key=?",
                                ("entity.photos." + digest,)).fetchone()[0] == 1


def wait_for_text(entry, matches, message):
    deadline = time.monotonic() + 10
    while not matches(json.loads(entry.read_text())["text"]):
        assert time.monotonic() < deadline, f"{message}: {json.loads(entry.read_text())['text']!r}"
        time.sleep(0.1)


@contextlib.contextmanager
def application(profile, label, import_source=None, size=(900, 720)):
    with (OUTPUT / f"{label}.log").open("w") as log:
        environment = ENV | {"APP_DATA_ROOT": str(profile)} | driver.environment()
        if import_source is not None:
            environment["INBE_DIARY_IMPORT"] = str(import_source)
        app = subprocess.Popen([sys.argv[1], "--bundle", str(ROOT / "build/apps/diary.zx")],
                               cwd=ROOT, env=environment,
                               stdout=log, stderr=subprocess.STDOUT)
        driver.attach(app)
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
            if driver.find(label="Close", role="button", visible=True):
                driver.press(label="Close", role="button")
                driver.wait_gone(label="Close", role="button")
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
        driver.wait_gone(contains="Achievement unlocked", timeout=20)
        driver.press(label="Insert time", role="button")
        wait_for_text(entry, lambda text: "**" in text, "Time insertion was not saved")
        with_time = json.loads(entry.read_text())["text"]
        driver.press(label="Undo")
        wait_for_text(entry, lambda text: text == "A saved Diary entry", "Undo did not restore the entry")
        driver.press(label="Redo")
        wait_for_text(entry, lambda text: text == with_time, "Redo did not restore the time")
        driver.press(label="Correct spelling")
        time.sleep(0.5)
        capture(window, "spelling-without-account")
        assert json.loads(entry.read_text())["text"] == with_time, "Spelling changed the entry without an account"
        # The photo button adds the picked photo to the account's photo
        # library, under the day it was added, and embeds its place there on
        # its own line at the caret, which is at the entry's end.
        driver.press(label="Attach photo")
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
        driver.key("down")
        time.sleep(0.5)
        capture(window, "text-beside-photo")
        assert len(purple_pixels(OUTPUT / "text-beside-photo.png")) > 20000, \
            "The photo was not drawn under the text typed after it"
        # While typing at the end of a line with an empty line under it, one
        # caret shows, on the typed line: the frame that takes a key never
        # draws a second one at the start of the line below.
        driver.key("enter")
        driver.key("up")
        area = driver.find(role="text_area")[0]
        assert area["value"][area["cursor"] - 1:area["cursor"] + 1] == "\n\n", "The caret is not on the empty line"
        box = (area["x"] + 6, area["y"] + 6, area["x"] + area["width"] - 6, area["y"] + area["height"] - 6)
        typed_rows = []
        for index, letter in enumerate("Typed"):
            driver.type(letter)
            capture(window, f"typing-{index}")
            typed_rows.append(ink_bottom(OUTPUT / f"typing-{index}.png", box))
        wait_for_text(entry, lambda text: text.endswith(") right after\nTyped\n"), "Typing under the photo was not saved")
        time.sleep(0.5)
        capture(window, "typed")
        settled = ink_bottom(OUTPUT / "typed.png", box)
        assert max(typed_rows) <= settled + 2, f"A second caret showed under the typed line: {typed_rows} > {settled}"
        saved = json.loads(entry.read_text())
        driver.press(label="Calendar")
        capture(window, "calendar")
    with application(profile, "restart") as window:
        capture(window, "restored")
        assert json.loads(entry.read_text()) == saved
        driver.press(label="›")
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
            # The entry's photos join the photo library, the one Photos
            # shows, under the entry's day, without rewriting the entry.
            local_digest = hashlib.sha256(photo_bytes).hexdigest()
            library_place = "photos/{}/{}/{}/{}.png".format(entry.name[:4], entry.name[5:7],
                                                            entry.name[8:10], local_digest)
            deadline = time.monotonic() + 20
            while not library_has(phone, local_digest):
                assert time.monotonic() < deadline, "The entry's photo did not join the photo library"
                time.sleep(0.2)
            time.sleep(0.5)
            capture(window, f"sage-{dark}-inline")
            red = red_pixels(OUTPUT / f"sage-{dark}-inline.png")
            assert len(red) > 20000, "Photo not drawn inside the entry at phone scale"
            assert phone_entry.read_text() == stored, "Viewing the day rewrote its entry"
            # The icon opens a separate day gallery without resizing the entry.
            driver.wait(label="Show gallery")
            assert not driver.find(label="A photo", role="image"), "The gallery was open when the day opened"
            driver.press(label="Show gallery")
            driver.wait(label="Hide gallery")
            driver.wait(label="A photo", role="image")
            capture(window, f"sage-{dark}-day-gallery")
            # The entry's Diary file and its library photo are one picture,
            # listed once; a tap embeds the library's.
            assert len(driver.find(label="A photo", role="image")) == 1, "The gallery listed a photo twice"
            driver.press(label="A photo")
            deadline = time.monotonic() + 5
            while "](" + library_place + ")" not in json.loads(phone_entry.read_text())["text"]:
                assert time.monotonic() < deadline, "A tapped photo was not embedded in the entry"
                time.sleep(0.1)
            saved_photo = json.loads(phone_entry.read_text())
            assert saved_photo["text"].startswith(original["text"] + "\n\n![A photo](diary:photo-local.bin)")
            assert saved_photo["text"].count("](diary:photo-local.bin)") == 1
            assert [row["file"] for row in saved_photo["photos"]] == files
            # Undo takes the tapped photo out again; redo puts it back.
            driver.press(label="Undo")
            wait_for_text(phone_entry, lambda text: library_place not in text, "Undo kept the tapped photo")
            driver.press(label="Redo")
            wait_for_text(phone_entry, lambda text: text == saved_photo["text"], "Redo did not restore the tapped photo")
            # Another day opens with its gallery closed, and so does this one
            # when it opens again.
            driver.wait(label="Show gallery")
            driver.press(label="Show gallery")
            driver.press(label="‹")
            driver.press(label="›")
            driver.wait(label="Show gallery")
            assert not driver.find(label="A photo", role="image"), "The gallery stayed open on another day"
        with application(phone, f"sage-{dark}-restart", size=(390, 844)):
            assert json.loads(phone_entry.read_text()) == saved_photo
            assert (phone_entry.parent / "photo-local.bin").read_bytes() == photo_bytes
    # A day with more photos than the gallery shows at once and an entry
    # longer than its box, with large photos between its lines. The wheel
    # over the entry scrolls it, over its photos too, and the page around it
    # stays, and a sideways swipe leaves it. The separate gallery scrolls
    # vertically; a drag does not embed the photo it starts on, and a
    # tap on a photo scrolled into view embeds it.
    many_source = profile / "many-source"
    many_source.mkdir()
    many_names = [f"many-{index:02d}.png" for index in range(24)]
    lines = []
    for index, name in enumerate(many_names):
        Image.new("RGB", (400, 300), ((29 * index) % 256, 40 + (7 * index) % 180, 220 - (5 * index) % 200)).save(many_source / name)
        lines += [f"Line {index} of a long day" for _ in range(3)]
        if index < 4:
            lines.append(f"![Photo {index}](diary:{name})")
    many_text = "\n".join(lines) + "\n"
    (many_source / entry.name).write_text(json.dumps(dict(original, text=many_text, photos=[
        dict(file=name, name=f"Photo {index}") for index, name in enumerate(many_names)])))
    many = profile / "many-photos"
    with application(many, "many-photos", many_source, size=(390, 640)) as window:
        many_entry = next((many / "diary").glob("*/" + entry.name))
        deadline = time.monotonic() + 20
        while not all(library_has(many, hashlib.sha256((many_source / name).read_bytes()).hexdigest())
                      for name in many_names):
            assert time.monotonic() < deadline, "The day's photos did not join the photo library"
            time.sleep(0.2)
        area = driver.wait(role="text_area")
        probe = (area["x"] + 40, area["y"] + 30)

        def top_line():
            """The entry's line at the top of its box: where a click there puts the caret."""
            driver.pointer(*probe)
            driver.pointer(*probe, down=True)
            driver.pointer(*probe)
            driver.release_pointer()
            driver.wait_idle(frames=2, timeout=2)
            node = driver.find(role="text_area")[0]
            return node["value"][:node["cursor"]].count("\n")

        def wheel(point, amount, times, sideways=False):
            for _ in range(times):
                if sideways:
                    driver.pointer(*point, wheel_x=amount)
                else:
                    driver.pointer(*point, wheel=amount)
            driver.release_pointer()
            driver.wait_idle(frames=3, timeout=3)

        def page_top():
            return driver.find(role="text_area")[0]["y"]

        assert top_line() == 0, "The entry did not open at its start"
        entry_page = page_top()
        middle = (area["x"] + area["width"] / 2, area["y"] + area["height"] / 2)
        wheel(middle, -2.0, 4)
        scrolled = top_line()
        assert scrolled > 0, "The wheel over the entry did not scroll it"
        assert page_top() == entry_page, "The page moved instead of the entry"
        wheel(middle, -3.0, 40)
        end = top_line()
        assert end > scrolled, f"The wheel did not scroll on through the photos: {scrolled} -> {end}"
        wheel(middle, 3.0, 60)
        assert top_line() == 0, "The wheel did not scroll the entry back to its start"
        wheel(middle, 2.0, 4, sideways=True)
        assert top_line() == 0, "A sideways swipe scrolled the entry"
        assert json.loads(many_entry.read_text())["text"].count("](") == 4, "Scrolling changed the entry"

        driver.press(label="Show gallery")
        driver.wait(label="Hide gallery")
        driver.wait_idle(frames=3, timeout=5)

        def tiles():
            return sorted((node for node in driver.find(role="image") if node["label"].startswith("Photo ")),
                          key=lambda node: (node["y"], node["x"]))

        assert not driver.find(role="text_area"), "The gallery still shares the entry's viewport"
        strip = [node for node in driver.tree() if node["kind"] == "scroll" and node["key"] == 290302][0]
        shown = tiles()
        capture(window, "day-gallery-grid")
        assert len(shown) == len(many_names), [node["label"] for node in shown]
        assert shown[-1]["y"] + shown[-1]["height"] > strip["y"] + strip["height"], "The grid has no scrollable rows"
        assert shown[0]["visible_height"] == shown[0]["height"], "The first grid row is clipped"
        first_y = shown[0]["y"]
        over_strip = (strip["x"] + strip["width"] / 2, strip["y"] + strip["height"] / 2)
        wheel(over_strip, -1.0, 2)
        assert tiles()[0]["y"] < first_y, "The wheel did not move the gallery down"
        wheel(over_strip, 1.0, 4)
        assert tiles()[0]["y"] == first_y, "The wheel did not move the gallery back"
        before_drag = json.loads(many_entry.read_text())["text"]
        driver.drag((over_strip[0], over_strip[1] + 150), (over_strip[0], over_strip[1] - 150))
        driver.wait_idle(frames=3, timeout=3)
        assert tiles()[0]["y"] < first_y - 100, "A drag did not move the gallery"
        time.sleep(0.5)
        assert json.loads(many_entry.read_text())["text"] == before_drag, "A drag embedded a photo"
        wheel(over_strip, -3.0, 20)
        last = tiles()[-1]
        assert last["visible"] and last["visible_y"] + last["visible_height"] <= strip["y"] + strip["height"], \
            "The wheel did not reach the gallery's end"
        driver.press(label=last["label"])
        number = int(last["label"].split()[-1])
        digest = hashlib.sha256((many_source / many_names[number]).read_bytes()).hexdigest()
        wait_for_text(many_entry, lambda text: digest + ".png)" in text, "A tap on a scrolled photo did not embed it")

    print("Standalone Diary: native editing, delayed save, time insertion, undo, redo, spelling without an account, a picked photo in the photo library and inside the entry, text typed right after the photo, one caret while typing, calendar, restart and day navigation passed")
    print("Harmony import: text and photo bytes copied, originals preserved, symlinks skipped and existing entries retained")
    print("Diary photos: older photo lists inside the entry and in the photo library, a missing file, no writes on viewing, the separate day gallery closed on every day it opens, each picture listed once, a tapped photo embedded and undone, and restart at phone width in light/dark sage passed")
    print("Diary scrolling: the wheel scrolls a long entry through its photos and back without moving the page, a sideways swipe leaves it, and the wheel and a vertical drag move the separate gallery grid, where a drag embeds nothing and a tap on a photo scrolled into view embeds it")
