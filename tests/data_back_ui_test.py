#!/usr/bin/env python3
"""Back from navigation Data exits once; Profile Data returns to its hub."""
import csv
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from PIL import Image, ImageOps
from native_visual_test import read_text

assert int(os.environ.get("DISPLAY", ":0").split(":")[-1].split(".")[0]) >= 300
root = Path(__file__).resolve().parents[1]
binary = Path(sys.argv[1]).resolve()
output = root / "build/data-back-ui-test"
output.mkdir(parents=True, exist_ok=True)


def command(*args):
    return subprocess.check_output(args, text=True, timeout=5).strip()


def click(window, x, y):
    command("xdotool", "mousemove", "--window", window, str(x), str(y),
            "mousedown", "1", "sleep", "0.12", "mouseup", "1")
    time.sleep(0.5)


def capture_title(window, name, width):
    path = output / (name + ".png")
    command("import", "-window", window, str(path))
    with Image.open(path) as image:
        left = 88 if width >= 640 else 0
        return read_text(image.crop((left, 0, width, 64)), name)


def open_practice(window, name, width, height):
    path = output / (name + "-navigation.png")
    ocr_path = output / (name + "-navigation-ocr.png")
    command("import", "-window", window, str(path))
    with Image.open(path) as image:
        gray = ImageOps.autocontrast(ImageOps.grayscale(image))
        gray.resize((width * 3, height * 3)).save(ocr_path)
    text = command("tesseract", str(ocr_path), "stdout", "--psm", "11",
                   "-c", "tessedit_create_tsv=1")
    ocr_path.unlink()
    words = [word for word in csv.DictReader(io.StringIO(text), delimiter="\t")
             # An unselected favorite can be partially offscreen in the
             # scrolling dock. Selecting it must then reveal the whole label.
             if word.get("text", "").lower().startswith("pract")
             and (int(word["left"]) < 88 * 3 if width >= 640
                  else int(word["top"]) > (height - 84) * 3)]
    assert len(words) == 1, "The rendered Practice navigation shortcut is missing or ambiguous"
    word = words[0]
    click(window, (int(word["left"]) + int(word["width"]) // 2) // 3,
          (int(word["top"]) + int(word["height"]) // 2) // 3)
    command("import", "-window", window, str(path))
    with Image.open(path) as image:
        dock = image.crop((0, 0, 88, height)) if width >= 640 else image.crop((0, height - 84, width, height))
        assert "practice" in read_text(dock, name + "-selected-navigation"), \
            "Selecting Practice did not reveal its complete navigation label"


for scene in ("data_from_navigation", "profile_data", "settings_overview"):
    sizes = ((360, 740),) if scene == "settings_overview" else ((900, 720), (360, 740))
    for width, height in sizes:
        name = f"{scene}-{width}"
        logfile = output / f"{name}.log"
        initial = output / f"{name}.png"
        env = os.environ.copy()
        env.update(APP_SHOT_WINDOW="1", APP_NO_TRAY="1", INBE_DEBUG_ROUTE="1",
                   SDL_VIDEODRIVER="x11", YUE_DESKTOP_RECOVERY="0")
        with logfile.open("w") as log:
            app = subprocess.Popen([str(binary), "--screenshot", str(initial),
                "--bundle", str(root / "build/inbe-full.zib"),
                "--screenshot-scene", scene, "--screenshot-width", str(width),
                "--screenshot-height", str(height), "--screenshot-ui-scale", "10"],
                cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 15
                window = ""
                while time.monotonic() < deadline:
                    assert app.poll() is None, logfile.read_text()[-2000:]
                    found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                        capture_output=True, text=True)
                    database = Path('/tmp') / f'inbe-screenshot-{app.pid}' / 'inbe.db'
                    if found.returncode == 0 and found.stdout.strip() and database.is_file():
                        window = found.stdout.splitlines()[0]
                        break
                    time.sleep(0.1)
                assert window, "private child did not become ready"
                command("xdotool", "windowfocus", "--sync", window)
                time.sleep(0.5)
                if scene == "settings_overview":
                    assert "settings" in capture_title(window, name + "-initial", width)
                    click(window, width // 2, 156)
                    assert "screen=6->10" in logfile.read_text(), "Settings Data did not open"
                title = capture_title(window, name + "-data", width)
                assert "data" in title, (name, "Data did not render before Back", title)
                baseline = len(logfile.read_text())
                back_x = 88 + 26 if width >= 640 else 26
                click(window, back_x, 24)
                after = logfile.read_text()[baseline:]
                switches = re.findall(r"ROUTE switch frame=\d+ screen=(\d+)->(\d+)", after)
                if scene == "data_from_navigation":
                    assert switches == [("10", "16")], (name, switches, after[-1200:])
                elif scene == "settings_overview":
                    assert switches == [("10", "6")], (name, switches, after[-1200:])
                    assert "settings" in capture_title(window, name + "-parent", width)
                else:
                    assert switches == [], (name, "Profile Data skipped its parent", switches)
                    command("import", "-window", window, str(output / f"{name}-hub.png"))
                    assert "profile" in capture_title(window, name + "-parent", width)
                    # The Profile hub has no leading Back action. A second
                    # click in its former location must not skip the hub.
                    click(window, back_x, 24)
                    assert not re.findall(r"ROUTE switch frame=\d+ screen=(\d+)->(\d+)",
                                          logfile.read_text()[baseline:]), "Profile hub kept a hidden Back action"
                    open_practice(window, name, width, height)
                    after = logfile.read_text()[baseline:]
                    switches = re.findall(r"ROUTE switch frame=\d+ screen=(\d+)->(\d+)", after)
                    assert switches == [("10", "0")], (name, switches, after[-1200:])
                time.sleep(0.5)
                command("import", "-window", window, str(output / f"{name}-after.png"))
                assert "APP: frame rejected with status" not in logfile.read_text()
            finally:
                app.terminate()
                try:
                    app.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    app.kill()
                    app.wait(timeout=5)
                shutil.rmtree(Path('/tmp') / f'inbe-screenshot-{app.pid}', ignore_errors=True)
print("Data Back: navigation exits once; Profile Data returns to its hub; Settings Data returns to Settings")
