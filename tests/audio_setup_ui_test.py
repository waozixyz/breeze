"""First-run voice guidance in the device's language, and guide mute, privately."""
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
def application(profile, name, width, height, language="en"):
    path = OUTPUT / (name + ".log")
    with path.open("w") as log:
        app = subprocess.Popen([str(BINARY), "--bundle", str(ROOT / "build/inbe-full.zx")],
            cwd=ROOT, env=ENV | {"APP_DATA_ROOT": str(profile), "LANGUAGE": language},
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


QUESTION = "Add voice guidance?"


def downloads(log):
    return set(re.findall(r"downloading pack ([^\s]+)", log.read_text()))


for name, width, height in (("desktop", 900, 720), ("mobile", 390, 844)):
    with tempfile.TemporaryDirectory(prefix="inbe-audio-") as temporary:
        profile = Path(temporary)
        with application(profile, name + "-question", width, height) as (window, log):
            driver.wait(label=QUESTION)
            saved(profile, "language_setup_done", 0)
            # First run follows the device language, so nothing is stored.
            assert settings(profile).get("language", "") == ""
            sizes = [node["label"] for node in driver.find(role="text", visible=True)
                     if re.fullmatch(r"[1-9][0-9]* (?:KB|MB)", node["label"])]
            assert len(sizes) == 1, driver.text()
            assert not driver.find(role="toggle", visible=True), "Onboarding still offers a choice per voice"
            assert not driver.find(label="Back", role="button", visible=True)
            for label in ("Download", "Not now"):
                button = driver.wait(label=label, role="button")
                assert button["width"] >= 48 and button["height"] >= 48
            assert not downloads(log)
            capture(window, name + "-voice-question")
        # Closing the app before answering asks again, still without downloading.
        with application(profile, name + "-download", width, height) as (window, log):
            driver.wait(label=QUESTION)
            saved(profile, "language_setup_done", 0)
            assert not downloads(log)
            driver.press(label="Download", role="button")
            saved(profile, "language_setup_done", 1)
            saved(profile, "guide_narration_enabled", 1)
            saved(profile, "voice_narration_enabled", 1)
            assert settings(profile).get("language", "") == ""
            driver.wait(label="Step 1 of 3")
            # Download fetches the guide's and every narrated practice's voice
            # in the background. Offline, each attempt fails and stays
            # downloadable where it is today.
            expected = {"guide/en", "sunsalutation/en", "astral_projection/en", "workout/en"}
            deadline = time.monotonic() + 60
            while not downloads(log) >= expected and time.monotonic() < deadline:
                time.sleep(0.2)
            assert downloads(log) == expected, downloads(log)
            button = driver.wait(label="Mute guide voice", role="button")
            assert button["width"] >= 44 and button["height"] >= 44
            driver.press(label="Mute guide voice", role="button", settle=False)
            saved(profile, "guide_narration_muted", 1)
            saved(profile, "guide_narration_enabled", 1)
            driver.wait(label="Step 1 of 3")
            saved(profile, "voice_narration_enabled", 1)
            driver.press(contains="Hi, I'm Lumi", role="text", settle=False)
            capture(window, name + "-muted-guide")
        with application(profile, name + "-muted-restart", width, height):
            driver.wait(label="Step 1 of 3")
            driver.wait(label="Enable guide voice", role="button")
            driver.press(label="Enable guide voice", role="button", settle=False)
            saved(profile, "guide_narration_muted", 0)
            saved(profile, "guide_narration_enabled", 1)
            saved(profile, "voice_narration_enabled", 1)
    with tempfile.TemporaryDirectory(prefix="inbe-audio-skip-") as temporary:
        profile = Path(temporary)
        with application(profile, name + "-skip", width, height) as (window, log):
            driver.wait(label=QUESTION)
            driver.press(label="Not now", role="button")
            saved(profile, "language_setup_done", 1)
            saved(profile, "guide_narration_enabled", 0)
            saved(profile, "voice_narration_enabled", 0)
            driver.wait(label="Step 1 of 3")
            assert not driver.find(key=83113, role="button", visible=True)
            capture(window, name + "-guide-without-voice")
            assert not downloads(log)
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

# The question comes in the device's language, or in English when Inner
# Breeze has no translation for it, and the profile keeps following the device.
for language, question in (("es", "¿Añadir guía por voz?"), ("xx", QUESTION)):
    with tempfile.TemporaryDirectory(prefix="inbe-audio-language-") as temporary:
        profile = Path(temporary)
        with application(profile, "language-" + language, 900, 720, language) as (window, log):
            driver.wait(label=question)
            driver.press(key=265, role="button")
            saved(profile, "language_setup_done", 1)
            assert settings(profile).get("language", "") == "", settings(profile)
            assert not downloads(log)

print("Voice guidance question, Download, Not now, device language and guide mute passed on desktop and mobile")
