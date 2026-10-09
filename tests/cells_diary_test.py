"""Verify standalone Diary editing, restart and calendar on an owned test window."""
import contextlib
import json
import os
from pathlib import Path
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


@contextlib.contextmanager
def application(profile, label, import_source=None):
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
            command("xdotool", "windowsize", window, "900", "720")
            command("xdotool", "windowfocus", window)
            time.sleep(1.5)
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
        tap(window, 430, 200)  # Insert current time.
        deadline = time.monotonic() + 10
        while "**" not in json.loads(entry.read_text())["text"]:
            assert time.monotonic() < deadline, "Time insertion was not saved"
            time.sleep(0.1)
        saved = json.loads(entry.read_text())
        tap(window, 430, 148)  # Calendar.
        capture(window, "calendar")
    with application(profile, "restart") as window:
        capture(window, "restored")
        assert json.loads(entry.read_text()) == saved
        tap(window, 745, 96)  # Next day saves before changing selection.
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
    print("Standalone Diary: native editing, delayed save, time insertion, calendar, restart and day navigation passed")
    print("Harmony import: text and photo bytes copied, originals preserved, symlinks skipped and existing entries retained")
