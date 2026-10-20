"""First-run audio choices, language corrections and guide mute privately."""
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
    driver.wait_idle(frames=3, timeout=2)
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
            sizes = [node["label"] for node in driver.find(role="text", visible=True)
                     if re.fullmatch(r"[1-9][0-9]* (?:KB|MB)", node["label"])]
            assert len(sizes) == 2, driver.text()
            assert "Choose voices" not in driver.text()
            assert "Voice instructions download" not in driver.text()
            assert driver.wait(label="Guide voice", role="toggle")["selected"]
            assert driver.wait(label="Practice voice", role="toggle")["selected"]
            saved(profile, "guide_narration_enabled", 1)
            saved(profile, "voice_narration_enabled", 1)
            capture(window, name + "-optional-audio")
            driver.press(label="Practice voice", role="toggle")
            driver.press(label="Guide voice", role="toggle")
            driver.wait(label="Continue", role="button")
            assert not driver.find(label="Download selected", role="button", visible=True)
            assert not driver.find(label="Skip for now", role="button", visible=True)
            driver.press(label="Guide voice", role="toggle")
            back = driver.wait(label="Back", role="button")
            assert back["width"] >= 48 and back["height"] >= 48
            driver.press(label="Back", role="button")
            driver.wait(label="Choose Language")
            saved(profile, "audio_setup_step", 0)
            saved(profile, "language_setup_done", 0)
            driver.press(key=260, role="dropdown")
            driver.press(label="Español", role="option")
            driver.press(key=261, role="button")
            driver.wait(key=262, role="toggle")
            saved(profile, "language", "es")
            saved(profile, "audio_setup_step", 1)
            assert driver.wait(key=262, role="toggle")["selected"]
            assert not driver.wait(key=263, role="toggle")["selected"]
            assert not re.findall(r"downloading pack [^\s]+", log.read_text())
        # A language preview survives restart without completing first-run setup.
        with application(profile, name + "-language-restart", width, height) as (window, log):
            driver.wait(key=266, role="button")
            saved(profile, "language", "es")
            saved(profile, "language_setup_done", 0)
            assert driver.wait(key=262, role="toggle")["selected"]
            assert not driver.wait(key=263, role="toggle")["selected"]
            driver.press(key=264, role="button")
            saved(profile, "audio_setup_step", 2)
            # Back is available even after downloads have started.
            driver.press(key=266, role="button")
            driver.wait(key=260, role="dropdown")
            saved(profile, "audio_setup_step", 0)
            saved(profile, "language_setup_done", 0)
            driver.press(key=260, role="dropdown")
            driver.press(label="English", role="option")
            driver.press(label="Next", role="button")
            driver.wait(label="Optional audio")
            saved(profile, "language", "en")
            saved(profile, "guide_narration_enabled", 1)
            saved(profile, "voice_narration_enabled", 0)
            downloads = set(re.findall(r"downloading pack ([^\s]+)", log.read_text()))
            assert downloads <= {"guide/es"}, downloads
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
            saved(profile, "guide_narration_muted", 1)
            saved(profile, "guide_narration_enabled", 1)
            driver.wait(label="Step 1 of 3")
            saved(profile, "voice_narration_enabled", 0)
            driver.press(contains="Hi, I'm Lumi", role="text", settle=False)
            capture(window, name + "-muted-guide")
        with application(profile, name + "-muted-restart", width, height):
            driver.wait(label="Step 1 of 3")
            driver.wait(label="Enable guide voice", role="button")
            driver.press(label="Enable guide voice", role="button", settle=False)
            saved(profile, "guide_narration_muted", 0)
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
            assert not driver.find(key=83113, role="button", visible=True)
            capture(window, name + "-guide-without-voice")
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
                    if enabled:
                        driver.wait(label="Mute guide voice", role="button")
                    else:
                        assert not driver.find(key=83113, role="button", visible=True)

with tempfile.TemporaryDirectory(prefix="inbe-practice-audio-") as temporary:
    profile = Path(temporary)
    with application(profile, "practice-only", 900, 720) as (window, log):
        driver.wait(label="Choose Language")
        driver.press(label="Next", role="button")
        driver.wait(label="Optional audio")
        driver.press(label="Guide voice", role="toggle")
        driver.press(label="Download selected", role="button")
        driver.wait(label="Retry downloads", role="button", timeout=30)
        downloads = set(re.findall(r"downloading pack ([^\s]+)", log.read_text()))
        # Practice voices only: every narrated practice in this language.
        assert downloads == {"sunsalutation/en", "astral_projection/en"}, downloads
        saved(profile, "guide_narration_enabled", 0)
        saved(profile, "voice_narration_enabled", 1)

print("Default audio choices, Back, language persistence, offline retry and guide mute passed on desktop and mobile")
