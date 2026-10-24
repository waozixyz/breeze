"""Zoom the real app with Ctrl and the wheel on the display owned by the shell harness."""

import io
import os
from pathlib import Path
import sqlite3
import shutil
import subprocess
import sys
import tempfile
import time

from PIL import Image

from native_visual_test import contrast
from ui_driver import UiDriver


root = Path(__file__).resolve().parent.parent
output = root / "build/native-zoom-test"
output.mkdir(parents=True, exist_ok=True)
for stale in output.glob("*.png"):
    stale.unlink()
assert int(os.environ["DISPLAY"].split(":")[-1].split(".")[0]) >= 300
data = Path(tempfile.mkdtemp(prefix="inbe-zoom-", dir=output))
# A private command folder, so concurrent runs never answer each other.
driver = UiDriver(data / "driver")
env = os.environ.copy()
for name in ("WAYLAND_DISPLAY", "GDK_DISPLAY", "DBUS_SESSION_BUS_ADDRESS"):
    env.pop(name, None)
env.update(driver.environment())
env["APP_NO_TRAY"] = "1"
env["XDG_DATA_HOME"] = str(data / "data")
env["XDG_CONFIG_HOME"] = str(data / "config")
env["XDG_CACHE_HOME"] = str(data / "cache")
os.makedirs(env["XDG_DATA_HOME"])
TITLE = "Add voice guidance?"


def command(*args):
    return subprocess.run(args, env=env, check=True, text=True,
                          capture_output=True, timeout=5).stdout.strip()


def capture(window):
    """The window's pixels, read from the private display without a file."""
    raw = subprocess.run(["xwd", "-silent", "-id", window], env=env, check=True,
                         capture_output=True, timeout=5).stdout
    png = subprocess.run(["convert", "xwd:-", "png:-"], input=raw, check=True,
                         capture_output=True, timeout=10).stdout
    with Image.open(io.BytesIO(png)) as image:
        return image.convert("RGB")


def frames(count):
    """Wait until the app has drawn some more frames."""
    first = driver.send("status")["frame"]
    deadline = time.monotonic() + 20
    while driver.send("status")["frame"] < first + count:
        assert time.monotonic() < deadline, "the app stopped drawing frames"
        time.sleep(0.01)


def zoomed_tree(tenths, window_width):
    """The widgets once a settled frame lays out the window at this scale.

    The layout is the window divided by the scale, as a browser page zoom.
    """
    expected = window_width * 10 / tenths
    deadline = time.monotonic() + 10
    while True:
        screen = next(node for node in driver.tree() if node["kind"] == "screen")
        if abs(screen["width"] - expected) < 1.5:
            break
        assert time.monotonic() < deadline, \
            f"{tenths * 10}%: the layout is {screen['width']} wide, not {expected:.1f}"
        time.sleep(0.02)
    driver.wait_idle(frames=3)
    nodes = driver.tree()
    screen = next(node for node in nodes if node["kind"] == "screen")
    assert abs(screen["width"] - expected) < 1.5, f"{tenths * 10}%: the layout changed scale again"
    return screen, nodes


def content_width(screen, nodes, window_width):
    """Width in window pixels of everything the screen lays out.

    Canvas fills are boxes across the whole screen at every scale (to within
    a unit, as the view's width is whole); they are background, not laid-out
    content.
    """
    def background(node):
        return (node["kind"] == "box" and node["x"] <= screen["x"] + 1 and
                node["x"] + node["width"] >= screen["x"] + screen["width"] - 1)

    shown = [node for node in nodes
             if node["visible"] and node["kind"] != "screen" and not background(node)]
    assert shown, "nothing was laid out"
    left = min(node["visible_x"] for node in shown)
    right = max(node["visible_x"] + node["visible_width"] for node in shown)
    return (right - left) * window_width / screen["width"]


def check_title(window, tenths, base, window_width):
    """The title is laid out, scaled and drawn as readable glyphs at this scale.

    The widget tree says what the title is and where it sits; one capture of
    its box then shows that its glyphs are drawn at that size.
    """
    percent = tenths * 10
    screen, nodes = zoomed_tree(tenths, window_width)
    titles = [node for node in nodes if node["label"] == TITLE and node["visible"]]
    assert len(titles) == 1, f"{percent}%: expected one {TITLE} title, found {len(titles)}"
    title = titles[0]
    assert (title["visible_width"], title["visible_height"]) == (title["width"], title["height"]), \
        f"{percent}%: the title is clipped: {title}"
    # Kryon drivers since 4320dc3f report text lines a box cuts off.
    assert title.get("hidden_lines", 0) == 0, f"{percent}%: the title box cuts off text lines"
    if base is not None:
        # Text measures the same in layout units at every scale, so its box
        # grows in window pixels exactly as the zoom does.
        assert abs(title["width"] - base["width"]) <= max(2, base["width"] * .03) and \
            abs(title["height"] - base["height"]) <= 2, \
            f"{percent}%: the title measures {title['width']}x{title['height']}, " \
            f"not {base['width']}x{base['height']}"
    image = capture(window)
    assert image.width == window_width, f"{percent}%: the window is {image.width} pixels wide"
    factor = window_width / screen["width"]
    box = (round((title["x"] - screen["x"]) * factor), round((title["y"] - screen["y"]) * factor),
           round((title["x"] + title["width"] - screen["x"]) * factor),
           round((title["y"] + title["height"] - screen["y"]) * factor))
    try:
        assert_title_pixels(image, box, percent)
    except AssertionError:
        image.save(output / f"title-{percent}.png")
        raise
    return title, screen, nodes


def assert_title_pixels(image, box, percent):
    """Contrasting ink fills the title's box across and down, and stays in it."""
    left, top, right, bottom = box
    width, height = right - left, bottom - top
    assert width > 20 and height > 6, f"{percent}%: the title box is only {width}x{height} pixels"
    colors = image.crop(box).getcolors(width * height)
    _, background = max(colors)
    ratios = {}

    def ratio(color):
        if color not in ratios:
            ratios[color] = contrast(color, background)
        return ratios[color]

    _, ink = max(colors, key=lambda entry: ratio(entry[1]))
    assert ratio(ink) >= 4.5, f"{percent}%: title contrast is {ratio(ink):.2f}:1"
    strong = sum(count for count, color in colors if ratio(color) >= 4.5)
    assert strong >= max(8, width * height * .06), \
        f"{percent}%: title lost readable glyph interiors ({strong} strong pixels in {width}x{height})"
    pixels = image.load()
    marked = [(x, y) for x in range(max(0, left - height), min(image.width, right + height))
              for y in range(top, bottom) if ratio(pixels[x, y]) >= 2]
    columns = sorted({x - left for x, _ in marked if left <= x < right})
    rows = sorted({y - top for x, y in marked if left <= x < right})
    # Glyphs drawn smaller than measured leave part of the box empty.
    assert columns and columns[-1] - columns[0] >= width * .9, \
        f"{percent}%: title ink spans {columns[-1] - columns[0] if columns else 0} of {width} pixels"
    sixths = {column * 6 // width for column in columns}
    assert sixths == set(range(6)), f"{percent}%: title ink leaves part of its box empty: {sorted(sixths)}"
    assert rows[-1] - rows[0] >= height * .5, \
        f"{percent}%: title ink is only {rows[-1] - rows[0]} of {height} pixels tall"
    # Glyphs drawn larger than measured spill over the box's ends.
    spilled = [x for x, _ in marked if not left - 2 <= x < right + 2]
    assert not spilled, f"{percent}%: {len(spilled)} title pixels are drawn outside its box"


def saved_scale():
    database = Path(env["XDG_DATA_HOME"]) / "inbe/inbe.db"
    if not database.exists():
        return None
    # The file can exist before the app creates its tables on a slow runner.
    try:
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True, timeout=2) as db:
            row = db.execute("select value from settings where key = 'ui_scale'").fetchone()
    except sqlite3.OperationalError:
        return None
    return int(row[0]) if row else None


def wait_for_scale(expected, seconds=5):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if saved_scale() == expected:
            return True
        time.sleep(0.1)
    return False


def wheel(direction, notches, control=True):
    """Hold the real Ctrl key and turn the wheel one notch per frame.

    Ctrl goes through the X server, as a person holds it; each notch reaches
    the app through the test driver in a frame of its own, so a slow frame
    cannot merge notches or see a notch after Ctrl was let go.
    """
    screen = next(node for node in driver.tree() if node["kind"] == "screen")
    x = screen["x"] + screen["width"] / 2
    y = screen["y"] + screen["height"] / 2
    if control:
        command("xdotool", "keydown", "ctrl")
        frames(2)
    for _ in range(notches):
        driver.pointer(x, y, wheel=direction)
    if control:
        command("xdotool", "keyup", "ctrl")
    frames(2)


log_path = output / "app.log"
with log_path.open("w") as log:
    app = subprocess.Popen([sys.argv[1]], cwd=root, env=env, stdout=log,
                           stderr=subprocess.STDOUT, start_new_session=True)
    driver.attach(app, log_path)
    try:
        driver.wait(label=TITLE, timeout=30)
        deadline = time.monotonic() + 15
        window = ""
        while time.monotonic() < deadline:
            assert app.poll() is None, "app exited during startup"
            found = subprocess.run(
                ["xdotool", "search", "--all", "--onlyvisible", "--pid",
                 str(app.pid), "--name", "Inner Breeze"],
                env=env, capture_output=True, text=True, timeout=2)
            if found.returncode == 0 and found.stdout.strip():
                window = found.stdout.splitlines()[0]
                break
            time.sleep(0.1)
        assert window, "the app did not map its own window"
        # The real Ctrl key goes to the focused window.
        command("xdotool", "windowfocus", window)
        geometry = dict(line.split("=", 1) for line in
                        command("xdotool", "getwindowgeometry", "--shell", window).splitlines())
        window_width = int(geometry["WIDTH"])
        assert wait_for_scale(10, 10), f"default scale is {saved_scale()}"
        base, screen, nodes = check_title(window, 10, None, window_width)
        normal = content_width(screen, nodes, window_width)

        # Ctrl and the wheel rescale the whole window and move the setting.
        wheel(+1, 3)
        assert wait_for_scale(13), f"scale after three notches is {saved_scale()}"
        _, screen, nodes = check_title(window, 13, base, window_width)
        ratio = content_width(screen, nodes, window_width) / normal
        assert 1.25 < ratio < 1.35, f"130% drew the content {ratio:.2f} times wider"

        # The wheel without Ctrl keeps its meaning and leaves the scale alone.
        wheel(-1, 3, control=False)
        frames(3)
        assert saved_scale() == 13, "a plain wheel changed the scale"

        # Zooming back out returns to the layout the app started with.
        wheel(-1, 3)
        assert wait_for_scale(10), f"scale after zooming back is {saved_scale()}"
        _, screen, nodes = check_title(window, 10, base, window_width)
        ratio = content_width(screen, nodes, window_width) / normal
        assert 0.98 < ratio < 1.02, f"zooming back left the content {ratio:.2f} times wider"

        # The limits match the Appearance slider: 50% to 250%.
        wheel(-1, 20)
        assert wait_for_scale(5), f"the low limit is {saved_scale()}"
        check_title(window, 5, base, window_width)
        # Every supported scale must remain usable, including fractional ones.
        for tenths in range(6, 26):
            wheel(+1, 1)
            assert wait_for_scale(tenths), f"expected {tenths}, got {saved_scale()}"
            check_title(window, tenths, base, window_width)
        wheel(+1, 3)
        assert wait_for_scale(25), f"the high limit is {saved_scale()}"

        # Ctrl+0 resets to 100%.
        # Hold Ctrl across several frames, as a person does, with each key
        # change landing in a frame of its own.
        command("xdotool", "keydown", "ctrl")
        frames(3)
        command("xdotool", "keydown", "0")
        frames(3)
        command("xdotool", "keyup", "0")
        frames(3)
        command("xdotool", "keyup", "ctrl")
        assert wait_for_scale(10), f"Ctrl+0 left the scale at {saved_scale()}"
        assert "APP: frame rejected with status" not in log_path.read_text()
    finally:
        if app.poll() is None:
            app.terminate()
            try:
                app.wait(timeout=2)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=2)
        shutil.rmtree(data)

print("Native zoom: title laid out and drawn at its scaled size at every scale from 50% to 250%, "
      "Ctrl+wheel persistence, limits and Ctrl+0 passed")
