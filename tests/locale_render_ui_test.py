"""Render every shipped locale and its cell picker in disposable profiles."""
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/locale-render-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
assert int(os.environ["DISPLAY"].split(":")[-1].split(".")[0]) >= 300


def command(environment, *args):
    return subprocess.run(args, env=environment, text=True, capture_output=True,
                          check=True, timeout=5).stdout.strip()


def capture(environment, window, label):
    raw = OUTPUT / f"{label}.xwd"
    command(environment, "xwd", "-silent", "-id", window, "-out", str(raw))
    command(environment, "convert", str(raw), str(OUTPUT / f"{label}.png"))
    raw.unlink()
    with Image.open(OUTPUT / f"{label}.png") as screenshot:
        return screenshot.convert("RGB").copy()


languages = [line.split("|")[0] for line in (ROOT / "locales/index.txt").read_text().splitlines()
             if "|" in line and not line.startswith("#")]
with tempfile.TemporaryDirectory(prefix="inbe-locales-") as temporary:
    # All languages must exercise the same artifacts, even while an Android
    # build regenerates the shared cell bundles in the checkout.
    binary = Path(temporary) / "inbe"
    bundle = Path(temporary) / "inbe.zib"
    shutil.copy2(sys.argv[1], binary)
    shutil.copy2(ROOT / "build/inbe.zib", bundle)
    for language in languages:
        profile = Path(temporary) / language
        profile.mkdir()
        environment = os.environ | {"APP_DATA_ROOT": str(profile), "LANGUAGE": language,
                                    "APP_NO_TRAY": "1"}
        log_path = OUTPUT / f"{language}.log"
        with log_path.open("w") as log:
            app = subprocess.Popen([str(binary), "--bundle", str(bundle)],
                                   cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 20
                window = ""
                while time.monotonic() < deadline:
                    assert app.poll() is None, log_path.read_text()
                    found = subprocess.run(["xdotool", "search", "--all", "--onlyvisible", "--pid",
                                            str(app.pid)], env=environment, text=True,
                                           capture_output=True, timeout=2)
                    if found.returncode == 0 and found.stdout.strip():
                        window = found.stdout.splitlines()[0]
                        break
                    time.sleep(0.1)
                assert window, f"{language}: no application window"
                command(environment, "xdotool", "windowsize", window, "900", "720")
                command(environment, "xdotool", "windowfocus", window)
                deadline = time.monotonic() + 30
                while "APP PROBE: drawing ended" not in log_path.read_text():
                    assert app.poll() is None, log_path.read_text()
                    assert time.monotonic() < deadline, f"{language}: first frame did not finish"
                    time.sleep(0.1)
                time.sleep(0.2)
                language_frame = capture(environment, window, f"{language}-language")
                command(environment, "xdotool", "mousemove", "--window", window, "450", "425")
                command(environment, "xdotool", "mousedown", "1")
                time.sleep(0.08)
                command(environment, "xdotool", "mouseup", "1")
                deadline = time.monotonic() + 5
                while True:
                    with sqlite3.connect(profile / "inbe.db") as db:
                        settings = dict(db.execute("SELECT key,value FROM settings"))
                    if settings.get("language_setup_done") == "1":
                        break
                    assert time.monotonic() < deadline, (language, settings)
                    time.sleep(0.1)
                # Accepting the detected language retains system-language mode.
                # Its stored code is empty so future device-language changes work.
                assert settings["language"] == "", (language, settings["language"])
                # Persisting the choice precedes reloading the locale fonts.
                # Wait for the cell instructions to replace the empty region
                # below the language title, including on slower CJK font loads.
                deadline = time.monotonic() + 30
                while True:
                    assert app.poll() is None, log_path.read_text()
                    cell_frame = capture(environment, window, f"{language}-cells")
                    difference = ImageChops.difference(language_frame, cell_frame).crop(
                        (240, 65, 660, 150))
                    red, green, blue = difference.split()
                    strongest = ImageChops.lighter(ImageChops.lighter(red, green), blue)
                    changed = sum(strongest.histogram()[11:])
                    if changed > 500:
                        break
                    assert time.monotonic() < deadline, f"{language}: cell picker did not render"
                    time.sleep(0.2)
                assert "portable execution failed" not in log_path.read_text(), log_path.read_text()
                assert "APP: frame rejected" not in log_path.read_text(), log_path.read_text()
            finally:
                if app.poll() is None:
                    app.terminate()
                    try:
                        app.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        app.kill()
                        app.wait(timeout=3)
print(f"All {len(languages)} locales rendered language setup and the real cell picker")
