#!/usr/bin/env python3
"""Photos from More apps on a private display, with a library seeded in the
profile as another device's sync would leave it: the gallery draws each
photo's preview under its day, Add photo takes a camera JPEG stored sideways
through the desktop picker (a stand-in zenity on PATH) and makes its upright
preview with the real image decoder, and its tile opens it whole and
upright.

The node's offer comes from a local package (INBE_NODE_APP_FILE), so nothing
is downloaded or published. Only "Apps", "Photos" and "Add" are found by
OCR; the rest is read from pixels.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

from PIL import Image, ImageDraw

assert int(os.environ.get("DISPLAY", ":0").split(":")[-1].split(".")[0]) >= 300
ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(sys.argv[1]).resolve()
PACKAGE = Path(sys.argv[2]).resolve()
OUTPUT = ROOT / "build/photos-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
WIDTH, HEIGHT = 390, 844
# Each seeded photo is one flat, distinct color, so its tile is found by it.
COLORS = [(214, 64, 52), (38, 120, 196), (58, 160, 92), (232, 168, 40)]
PICKED = (128, 72, 176)


def command(*args):
    return subprocess.check_output(args, text=True, timeout=10).strip()


def capture(window, name):
    path = OUTPUT / (name + ".png")
    command("import", "-window", window, str(path))
    with Image.open(path) as image:
        return image.convert("RGB").copy()


def click(window, x, y):
    command("xdotool", "mousemove", "--window", window, str(x), str(y))
    time.sleep(0.12)
    command("xdotool", "mousedown", "1")
    time.sleep(0.15)
    command("xdotool", "mouseup", "1")
    time.sleep(0.6)


def words(window, name):
    image = capture(window, name)
    gray = image.convert("L").resize((image.width * 3, image.height * 3))
    path = OUTPUT / (name + "-ocr.png")
    gray.save(path)
    result = subprocess.run(["tesseract", str(path), "stdout", "--psm", "11", "-c", "tessedit_create_tsv=1"],
                            check=True, text=True, capture_output=True, timeout=20)
    found = []
    for line in result.stdout.splitlines()[1:]:
        fields = line.split("\t")
        if len(fields) == 12 and fields[11].strip():
            left, top, width, height = map(int, fields[6:10])
            found.append((fields[11].strip(), (left + width // 2) // 3, (top + height // 2) // 3))
    return found


def tap_word(window, word, name, attempts=12):
    for attempt in range(attempts):
        for text, x, y in words(window, f"{name}-{attempt}"):
            if text.strip(".,:;!").lower() == word.lower():
                click(window, x, y)
                return
        time.sleep(0.5)
    raise AssertionError(f"no '{word}' to tap; see {OUTPUT / name}")


def near(pixel, color, tolerance=18):
    return all(abs(a - b) <= tolerance for a, b in zip(pixel, color))


def area_of(image, color):
    """The bounding box of the pixels of `color`, or None."""
    xs, ys = [], []
    for y in range(0, image.height, 2):
        for x in range(0, image.width, 2):
            if near(image.getpixel((x, y)), color):
                xs.append(x)
                ys.append(y)
    if len(xs) < 40:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def wait_area(window, color, name, attempts=30):
    for attempt in range(attempts):
        found = area_of(capture(window, f"{name}"), color)
        if found:
            return found
        time.sleep(0.4)
    return None


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def launch(profile, name, extra=None):
    log = (OUTPUT / (name + ".log")).open("w")
    app = subprocess.Popen([str(BINARY)], cwd=ROOT,
                           env=os.environ | {"APP_DATA_ROOT": str(profile), "INBE_NODE_APP_FILE": str(PACKAGE)} |
                           (extra or {}),
                           stdout=log, stderr=subprocess.STDOUT)
    for _ in range(300):
        assert app.poll() is None, (OUTPUT / (name + ".log")).read_text()
        found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                               capture_output=True, text=True)
        if found.returncode == 0 and (profile / "inbe.db").exists():
            window = found.stdout.splitlines()[0]
            command("xdotool", "windowsize", window, str(WIDTH), str(HEIGHT))
            command("xdotool", "windowmove", window, "0", "0")
            time.sleep(1.5)
            return app, window
        time.sleep(0.1)
    stop(app)
    raise AssertionError("Inbe did not map its window")


def jpeg(image, quality=88):
    data = io.BytesIO()
    image.save(data, "JPEG", quality=quality)
    return data.getvalue()


def seed_photo(db, user, folder, color, day, taken, name, size):
    """A photo and its preview, as the media library stores them."""
    image = Image.new("RGB", size, color)
    ImageDraw.Draw(image).ellipse((size[0] // 4, size[1] // 4, size[0] // 2, size[1] // 2),
                                  fill=tuple(min(255, c + 30) for c in color))
    original = jpeg(image)
    digest = hashlib.sha256(original).hexdigest()
    preview_image = image.copy()
    preview_image.thumbnail((512, 512))
    preview = jpeg(preview_image, 80)
    preview_digest = hashlib.sha256(preview).hexdigest()
    (folder / digest).write_bytes(original)
    (folder / (digest + ".preview")).write_bytes(preview)
    item = {"hash": digest, "size": len(original), "type": "jpg", "name": name, "day": day,
            "taken": taken, "added": 1792224000, "trashed": 0}
    preview_record = {"hash": preview_digest, "size": len(preview), "type": "jpg"}
    for key, value in ((f"cell.media.{digest}", item), (f"cell.media.preview.{digest}", preview_record)):
        db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1792224000)",
                   (user, key, json.dumps(value, separators=(",", ":"))))
    return digest


with tempfile.TemporaryDirectory(prefix="inbe-photos-") as directory:
    profile = Path(directory)
    app, _ = launch(profile, "first-start")
    stop(app)
    with sqlite3.connect(profile / "inbe.db") as db:
        user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
        seeded = {"language": "en", "language_system": 0, "language_setup_done": 1, "apps_setup_done": 1,
                  "tutorial_seen": 1, "habits_guide_seen": 1, "lumi_guides_seen": 127, "launcher_guide_seen": 1,
                  "package_updates_allowed": 0, "apps_last_update_check": 1900000000,
                  "node_apps_checked_at": int(time.time())}
        for key, value in seeded.items():
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                       "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user, key, str(value)))
        folder = profile / "media" / user
        folder.mkdir(parents=True)
        photos = [
            seed_photo(db, user, folder, COLORS[0], "2026-10-12", "2026-10-12T18:30:00", "Lake.jpg", (1200, 800)),
            seed_photo(db, user, folder, COLORS[1], "2026-10-12", "2026-10-12T09:10:00", "Morning.jpg", (800, 1200)),
            seed_photo(db, user, folder, COLORS[2], "2026-09-03", "2026-09-03T12:00:00", "Forest.jpg", (1000, 1000)),
            seed_photo(db, user, folder, COLORS[3], "2026-09-03", "2026-09-03T08:00:00", "Field.jpg", (1600, 900)),
        ]
    # A camera's portrait photo: stored 1200 by 800, Exif orientation 6.
    picked = profile / "IMG_UPRIGHT.jpg"
    sideways = Image.new("RGB", (1200, 800), PICKED)
    ImageDraw.Draw(sideways).rectangle((0, 0, 300, 800), fill=(250, 250, 250))
    exif = sideways.getexif()
    exif[0x0112] = 6
    sideways.save(picked, "JPEG", quality=90, exif=exif)
    # The desktop picker runs zenity, which answers with the picked file.
    tools = profile / "bin"
    tools.mkdir()
    (tools / "zenity").write_text(f"#!/bin/sh\nprintf '%s\\n' '{picked}'\n")
    (tools / "zenity").chmod(0o755)
    app, window = launch(profile, "gallery", {"PATH": f"{tools}:{os.environ['PATH']}"})
    try:
        tap_word(window, "Apps", "open-apps")
        tap_word(window, "Photos", "more-apps")
        # Every photo's preview is drawn, the newest day first.
        boxes = [wait_area(window, color, f"gallery-{index}") for index, color in enumerate(COLORS)]
        gallery = capture(window, "gallery")
        assert all(boxes), f"missing tiles {boxes}; see {OUTPUT / 'gallery.png'}"
        assert boxes[0][1] < boxes[2][1], "the newer day is not first"
        for box in boxes:
            width, height = box[2] - box[0], box[3] - box[1]
            assert abs(width - height) <= 6, f"tiles are square: {box}"
        # Add photo: the picked file is kept once with an upright preview.
        tap_word(window, "Add", "add-photo")
        tile = wait_area(window, PICKED, "added")
        capture(window, "added")
        assert tile, f"the added photo has no tile; see {OUTPUT / 'added.png'}"
        digest = hashlib.sha256(picked.read_bytes()).hexdigest()
        with sqlite3.connect(profile / "inbe.db", timeout=3) as db:
            stored = dict(db.execute("SELECT key,value FROM settings WHERE user_id=?", (user,)))
        assert stored.get("app_used_photos") == "1", stored.get("app_used_photos")
        item = json.loads(stored[f"cell.media.{digest}"])
        assert item["name"] == "IMG_UPRIGHT.jpg" and item["type"] == "jpg", item
        assert (folder / digest).read_bytes() == picked.read_bytes(), "the original is not kept as picked"
        with Image.open(folder / (digest + ".preview")) as preview:
            assert preview.format == "JPEG" and preview.size == (341, 512), preview.size
            # Upright: the white band stored on the left is now on top.
            assert near(preview.convert("RGB").getpixel((170, 20)), (250, 250, 250), 24), "the preview is not upright"
        # Its tile opens it whole and upright: portrait, white band on top.
        left, top, right, bottom = tile
        click(window, (left + right) // 2, (top + bottom) // 2)
        whole = wait_area(window, PICKED, "viewer")
        viewer = capture(window, "viewer")
        assert whole and (whole[3] - whole[1]) > (whole[2] - whole[0]), f"portrait viewer {whole}"
        assert (whole[3] - whole[1]) > (bottom - top) * 2, "the photo is not shown whole"
        band = viewer.getpixel(((whole[0] + whole[2]) // 2, max(0, whole[1] - 12)))
        assert near(band, (250, 250, 250), 24), f"the original is not upright: {band}"
        log = (OUTPUT / "gallery.log").read_text()
        assert "frame rejected" not in log and app.poll() is None, log
    finally:
        stop(app)
print(f"Photos: offered in More apps, a gallery of previews by day, a sideways camera photo added upright "
      f"through the desktop picker and opened whole; see {OUTPUT}")
