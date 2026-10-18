#!/usr/bin/env python3
"""Photos from More apps on a private display, with a library seeded in the
profile as another device's sync would leave it: the gallery draws each
photo's preview under its day, Add photo takes a camera JPEG stored sideways
through the desktop picker (a stand-in zenity on PATH) and makes its upright
preview with the real image decoder, and its tile opens it whole and
upright.

The node's offer comes from a local package (INBE_NODE_APP_FILE), so nothing
is downloaded or published. Buttons, tiles and headings are found in the
app's widget tree through Kryon's test driver; pixels are read only to see
that the photos are really drawn, once for the gallery and once for the
opened photo.
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

from ui_driver import UiDriver

assert int(os.environ.get("DISPLAY", ":0").split(":")[-1].split(".")[0]) >= 300
ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(sys.argv[1]).resolve()
PACKAGE = Path(sys.argv[2]).resolve()
OUTPUT = ROOT / "build/photos-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
WIDTH, HEIGHT = 390, 844
# Each seeded photo is one flat, distinct color, so its tile is found by it.
COLORS = [(214, 64, 52), (38, 120, 196), (58, 160, 92), (232, 168, 40)]
NAMES = ["Lake.jpg", "Morning.jpg", "Forest.jpg", "Field.jpg"]
PICKED = (128, 72, 176)
PICKED_NAME = "IMG_UPRIGHT.jpg"
driver = UiDriver(OUTPUT / "driver")


def command(*args):
    return subprocess.check_output(args, text=True, timeout=10).strip()


def system_back(window):
    command("xdotool", "windowfocus", window)
    command("xdotool", "keydown", "Escape")
    time.sleep(0.1)
    command("xdotool", "keyup", "Escape")


def capture(window, name):
    path = OUTPUT / (name + ".png")
    command("import", "-window", window, str(path))
    with Image.open(path) as image:
        return image.convert("RGB").copy()


def near(pixel, color, tolerance=18):
    return all(abs(a - b) <= tolerance for a, b in zip(pixel, color))


def area_of(image, color, region=None):
    """The bounding box of the pixels of `color` inside region, or None."""
    left, top, right, bottom = region or (0, 0, image.width, image.height)
    xs, ys = [], []
    for y in range(max(0, top), min(image.height, bottom), 2):
        for x in range(max(0, left), min(image.width, right), 2):
            if near(image.getpixel((x, y)), color):
                xs.append(x)
                ys.append(y)
    if len(xs) < 40:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def window_box(node):
    """Where a widget is drawn in the window: left, top, right, bottom.

    While a node app shows, the tree's screen starts above the window by
    the title bar's height, so its bounds are shifted from the pixels.
    """
    screen = driver.tree()[0]
    left = round(node["visible_x"] - screen["x"])
    top = round(node["visible_y"] - screen["y"])
    return left, top, left + round(node["visible_width"]), top + round(node["visible_height"])


def share_of(image, node, color):
    """How much of a widget's visible box is drawn in `color`."""
    left, top, right, bottom = window_box(node)
    pixels = [image.getpixel((x, y)) for y in range(top + 2, bottom - 2, 2) for x in range(left + 2, right - 2, 2)]
    return sum(1 for pixel in pixels if near(pixel, color)) / max(1, len(pixels))


def tile(name):
    """The drawn preview of a photo in the gallery, found by its name."""
    return driver.wait(label=name, role="image")


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def launch(profile, name, extra=None):
    log_path = OUTPUT / (name + ".log")
    log = log_path.open("w")
    app = subprocess.Popen([str(BINARY)], cwd=ROOT,
                           env=os.environ | {"APP_DATA_ROOT": str(profile), "INBE_NODE_APP_FILE": str(PACKAGE)} |
                           (extra or {}) | driver.environment(),
                           stdout=log, stderr=subprocess.STDOUT)
    driver.attach(app, log_path)
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        assert app.poll() is None, log_path.read_text()
        found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                               capture_output=True, text=True)
        if found.returncode == 0 and (profile / "inbe.db").exists():
            window = found.stdout.splitlines()[0]
            command("xdotool", "windowsize", window, str(WIDTH), str(HEIGHT))
            command("xdotool", "windowmove", window, "0", "0")
            driver.wait_idle(frames=3)
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
            seed_photo(db, user, folder, COLORS[0], "2026-10-12", "2026-10-12T18:30:00", NAMES[0], (1200, 800)),
            seed_photo(db, user, folder, COLORS[1], "2026-10-12", "2026-10-12T09:10:00", NAMES[1], (800, 1200)),
            seed_photo(db, user, folder, COLORS[2], "2026-09-03", "2026-09-03T12:00:00", NAMES[2], (1000, 1000)),
            seed_photo(db, user, folder, COLORS[3], "2026-09-03", "2026-09-03T08:00:00", NAMES[3], (1600, 900)),
        ]
        # A synced preview whose original has not reached this device yet.
        (folder / photos[2]).unlink()
    # A camera's portrait photo: stored 1200 by 800, Exif orientation 6.
    picked = profile / PICKED_NAME
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
        driver.press(label="Apps", role="button")
        # More apps offers Photos because the node (here, the local file) does.
        driver.press(label="Photos", role="button")
        # Every photo's preview is drawn under its day, the newest day first.
        tiles = [tile(name) for name in NAMES]
        driver.wait_idle(frames=3)
        tiles = [tile(name) for name in NAMES]
        assert tiles[0]["y"] < tiles[2]["y"], f"the newer day is not first: {tiles}"
        days = sorted(driver.find(role="heading", visible=True), key=lambda node: node["y"])
        assert len(days) == 2, f"one heading per day: {[node['label'] for node in days]}"
        for node in tiles[:2]:
            assert days[0]["y"] < node["y"] < days[1]["y"], f"{node['label']} is not under its day"
        for node in tiles[2:]:
            assert node["y"] > days[1]["y"], f"{node['label']} is not under its day"
        for node in tiles:
            assert abs(node["width"] - node["height"]) <= 1, f"tiles are square: {node}"
        # Add photo: the picked file is kept once with an upright preview.
        driver.press(label="Add photo", role="button")
        added = driver.wait(label=PICKED_NAME, role="image")
        driver.wait_idle(frames=3)
        digest = hashlib.sha256(picked.read_bytes()).hexdigest()
        with sqlite3.connect(profile / "inbe.db", timeout=3) as db:
            stored = dict(db.execute("SELECT key,value FROM settings WHERE user_id=?", (user,)))
        assert stored.get("app_used_photos") == "1", stored.get("app_used_photos")
        item = json.loads(stored[f"cell.media.{digest}"])
        assert item["name"] == PICKED_NAME and item["type"] == "jpg", item
        assert (folder / digest).read_bytes() == picked.read_bytes(), "the original is not kept as picked"
        with Image.open(folder / (digest + ".preview")) as preview:
            assert preview.format == "JPEG" and preview.size == (341, 512), preview.size
            # Upright: the white band stored on the left is now on top.
            assert near(preview.convert("RGB").getpixel((170, 20)), (250, 250, 250), 24), "the preview is not upright"
        # The gallery really draws every preview, the added one too.
        tiles = [tile(name) for name in NAMES]
        added = driver.wait(label=PICKED_NAME, role="image")
        gallery = capture(window, "gallery")
        for node, color in zip(tiles + [added], COLORS + [PICKED]):
            share = share_of(gallery, node, color)
            assert share > 0.3, f"{node['label']} is not drawn ({share:.2f}); see {OUTPUT / 'gallery.png'}"
        driver.press(label=NAMES[2], role="image")
        driver.wait(label="All photos", role="button")
        assert not driver.find(contains="Loading the full photo"), "loading text covers the preview"
        assert driver.wait(label=NAMES[2], role="image")["height"] > tiles[2]["height"] * 2
        driver.press(label="Back", role="button")
        driver.wait(label="Add photo", role="button")
        assert driver.find(label=NAMES[2], role="image"), "Back lost the gallery"
        # Its tile opens it whole and upright: portrait, white band on top.
        driver.press(label=PICKED_NAME, role="image")
        driver.wait(label="All photos", role="button")
        whole_node = driver.wait(label=PICKED_NAME, role="image")
        assert whole_node["height"] > added["height"] * 2, "the photo is not shown whole"
        driver.wait_gone(contains="Loading the full photo")
        driver.wait_idle(frames=3)
        viewer = capture(window, "viewer")
        whole = area_of(viewer, PICKED, window_box(whole_node))
        assert whole and (whole[3] - whole[1]) > (whole[2] - whole[0]), f"portrait viewer {whole}"
        assert (whole[3] - whole[1]) > added["height"] * 2, "the photo is not shown whole"
        band = viewer.getpixel(((whole[0] + whole[2]) // 2, max(0, whole[1] - 12)))
        assert near(band, (250, 250, 250), 24), f"the original is not upright: {band}"
        system_back(window)
        driver.wait(label="Add photo", role="button")
        assert driver.find(label=PICKED_NAME, role="image"), "system Back did not return to the gallery"
        driver.press(label="Back", role="button")
        driver.wait(label="Find an app", role="text_field")
        log = (OUTPUT / "gallery.log").read_text()
        assert "frame rejected" not in log and app.poll() is None, log
    finally:
        stop(app)

    # A saved Photos pin must survive restart and draw in either dock layout.
    with sqlite3.connect(profile / "inbe.db") as db:
        slot = db.execute("SELECT key FROM settings WHERE user_id=? AND key LIKE 'node_app_slot_%' "
                          "AND value='photos'", (user,)).fetchone()[0]
        route = 14 + int(slot.rsplit("_", 1)[1])
        pins = {"launcher_favorite_count": 1, "launcher_favorite_0": route,
                "navigation_placement": 1}
        for key, value in pins.items():
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                       "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user, key, str(value)))
    app, window = launch(profile, "pinned")
    try:
        command("xdotool", "windowsize", window, "900", "720")
        driver.wait_idle(frames=3)
        pin = driver.wait(label="Photos", role="button")
        assert pin["visible"], "Photos pin is missing from the sidebar"
        driver.press(label="Photos", role="button")
        driver.wait(label="Add photo", role="button")
        assert not driver.find(label="Back", role="button"), "pinned Photos still has an Apps return bar"
        driver.press(label=PICKED_NAME, role="image")
        driver.wait(label="All photos", role="button")
        system_back(window)
        driver.wait(label="Add photo", role="button")
        capture(window, "pinned-sidebar")
    finally:
        stop(app)
    with sqlite3.connect(profile / "inbe.db") as db:
        db.execute("UPDATE settings SET value='0' WHERE user_id=? AND key='navigation_placement'", (user,))
    app, window = launch(profile, "pinned-mobile")
    try:
        pin = driver.wait(label="Photos", role="button")
        assert window_box(pin)[1] > HEIGHT - 100, "Photos pin is missing from bottom navigation"
        capture(window, "pinned-mobile")
    finally:
        stop(app)
print(f"Photos: offered in More apps, a gallery of previews by day, a sideways camera photo added upright "
      f"through the desktop picker and opened whole; Back returns to the gallery, previews stay clear, "
      f"and saved pins appear in the sidebar and bottom navigation; see {OUTPUT}")
