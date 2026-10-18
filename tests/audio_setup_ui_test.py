"""First-run audio consent and persistent guide mute on a private display."""
import contextlib
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import time

from ui_driver import UiDriver

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/audio-setup-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
assert int(os.environ["DISPLAY"].split(":")[-1].split(".")[0]) >= 300
BINARY = Path(sys.argv[1]).resolve()
driver = UiDriver(OUTPUT / "driver")
# Deliberately offline: a failure must leave the app usable and retryable.
ENV = os.environ | driver.environment() | {
    "APP_NO_TRAY": "1", "YUE_DESKTOP_RECOVERY": "0", "SDL_AUDIODRIVER": "dummy",
    "LANGUAGE": "en", "https_proxy": "http://127.0.0.1:9", "NO_PROXY": "",
}


def settings(profile):
    uri = (profile / "inbe.db").as_uri() + "?mode=ro"
    with contextlib.closing(sqlite3.connect(uri, uri=True, timeout=5)) as db:
        return dict(db.execute("SELECT key,value FROM settings"))


def saved(profile, name, value):
    deadline = time.monotonic() + 10
    while settings(profile).get(name) != str(value):
        assert time.monotonic() < deadline, (name, value, settings(profile))
        time.sleep(.05)


@contextlib.contextmanager
def application(profile, name, width, height):
    path = OUTPUT / (name + ".log")
    with path.open("w") as log:
        app = subprocess.Popen([str(BINARY), "--bundle", str(ROOT / "build/inbe-full.zib")],
            cwd=ROOT, env=ENV | {"APP_DATA_ROOT": str(profile)},
            stdout=log, stderr=subprocess.STDOUT)
        driver.attach(app, path)
        try:
            deadline = time.monotonic() + 30
            while True:
                assert app.poll() is None, path.read_text()
                found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                    env=ENV, capture_output=True, text=True)
                if found.returncode == 0 and (profile / "inbe.db").exists():
                    break
                assert time.monotonic() < deadline, path.read_text()
                time.sleep(.1)
            window = found.stdout.splitlines()[0]
            subprocess.run(["xdotool", "windowsize", window, str(width), str(height)],
                env=ENV, check=True)
            driver.wait(role="screen")
            yield window, path
            assert "frame rejected" not in path.read_text(), path.read_text()
        finally:
            app.terminate()
            try:
                app.wait(timeout=5)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=5)


def capture(window, name):
    subprocess.run(["import", "-window", window, str(OUTPUT / (name + ".png"))],
        env=ENV, check=True)


for name, width, height in (("desktop", 900, 720), ("mobile", 390, 844)):
    with tempfile.TemporaryDirectory(prefix="inbe-audio-") as temporary:
        profile = Path(temporary)
        with application(profile, name + "-language", width, height) as (window, log):
            driver.wait(label="Choose Language")
            assert "downloading pack guide/" not in log.read_text()
            driver.press(label="Next", role="button")
            driver.wait(label="Optional audio")
            saved(profile, "language_setup_done", 0)
            saved(profile, "audio_setup_step", 1)
            driver.wait(label="Guide voice", role="text")
            driver.wait(label="Practice voice", role="text")
            assert not driver.wait(label="Guide voice", role="toggle")["selected"]
            assert not driver.wait(label="Practice voice", role="toggle")["selected"]
            driver.press(label="Guide voice", role="toggle")
            saved(profile, "guide_narration_enabled", 1)
            assert "downloading pack guide/" not in log.read_text(), log.read_text()
            capture(window, name + "-optional-audio")
        # An interrupted selection returns to optional audio without downloading.
        with application(profile, name + "-restart", width, height) as (window, log):
            driver.wait(label="Optional audio")
            assert driver.wait(label="Guide voice", role="toggle")["selected"]
            assert "downloading pack guide/" not in log.read_text()
            driver.press(label="Download selected", role="button")
            saved(profile, "audio_setup_step", 2)
            driver.wait(label="Retry downloads", role="button", timeout=30)
            assert set(re.findall(r"downloading pack ([^\s]+)", log.read_text())) == {"guide/en"}
            saved(profile, "voice_narration_enabled", 0)
            capture(window, name + "-offline")
            driver.press(label="Retry downloads", role="button")
            driver.wait(label="Retry downloads", role="button", timeout=30)
            driver.press(label="Continue", role="button")
            saved(profile, "language_setup_done", 1)
            driver.wait(label="Step 1 of 3")
            button = driver.wait(label="Mute guide voice", role="button")
            assert button["width"] >= 44 and button["height"] >= 44
            driver.press(label="Mute guide voice", role="button", settle=False)
            saved(profile, "guide_narration_enabled", 0)
            driver.wait(label="Step 1 of 3")
            saved(profile, "voice_narration_enabled", 0)
            driver.press(contains="Hi, I'm Lumi", role="text", settle=False)
            capture(window, name + "-muted-guide")
        with application(profile, name + "-muted-restart", width, height):
            driver.wait(label="Step 1 of 3")
            driver.wait(label="Enable guide voice", role="button")
            driver.press(label="Enable guide voice", role="button", settle=False)
            saved(profile, "guide_narration_enabled", 1)
            saved(profile, "voice_narration_enabled", 0)
    with tempfile.TemporaryDirectory(prefix="inbe-audio-skip-") as temporary:
        profile = Path(temporary)
        with application(profile, name + "-skip", width, height) as (window, log):
            driver.wait(label="Choose Language")
            driver.press(label="Next", role="button")
            driver.wait(label="Optional audio")
            driver.press(label="Skip for now", role="button")
            saved(profile, "language_setup_done", 1)
            driver.wait(label="Step 1 of 3")
            driver.wait(label="Enable guide voice", role="button")
            assert "downloading pack guide/" not in log.read_text()
        if name == "desktop":
            # A profile from before the separate guide setting inherits its
            # existing narration choice instead of seeing first-run setup.
            for enabled in (0, 1):
                with sqlite3.connect(profile / "inbe.db") as db:
                    db.execute("DELETE FROM settings WHERE key='guide_narration_enabled'")
                    db.execute("UPDATE settings SET value=? WHERE key='voice_narration_enabled'", (str(enabled),))
                with application(profile, "existing-" + str(enabled), width, height):
                    driver.wait(label="Step 1 of 3")
                    driver.wait(label="Mute guide voice" if enabled else "Enable guide voice", role="button")

print("Optional audio consent, offline retry, restart, and independent guide mute passed on desktop and mobile")
