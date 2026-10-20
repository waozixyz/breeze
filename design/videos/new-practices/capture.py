#!/usr/bin/env python3
"""Capture review screens with Inbe's existing screenshot and UI harnesses."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUTPUT = ROOT / "build/videos/new-practices"
BINARY = ROOT / "build/bin/linux/inbe-linux-x86_64"
BUNDLE = ROOT / "build/inbe-full.zib"
SPEC = importlib.util.spec_from_file_location("screenshots", ROOT / "scripts/screenshot-harness.py")
HARNESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HARNESS)

SCENES = [
    ("01-practice", "home", ["Meditation", "Workout", "Wim Hof"]),
    ("02-astral", "astral_projection_home", ["Astral Projection"]),
    ("02-astral-session", "astral_projection_session", []),
    ("03-workout", "workout_home", ["Workout"]),
    ("04-yoga", "sun_salutation_pose_5", []),
    ("05-tai-chi", "tai_chi_session", []),
    ("06-habits", "promo_habits", ["Habits"]),
    ("08-diary", "diary", ["morning walk"]),
    ("09-lumi", "lumi_customize_light", ["theme forest", "Settings changed"]),
    ("10-apps", "apps_library", ["Apps", "Lumi", "Diary"]),
]


def environment(profile):
    env = dict(os.environ)
    for name in ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS",
                 "SESSION_MANAGER", "APP_SHOT_WINDOW", "APP_DATA_ROOT", "INBE_DATA_ROOT"):
        env.pop(name, None)
    env.update(INBE_SCREENSHOT_DATA_ROOT=str(profile), YUE_DESKTOP_RECOVERY="0",
               APP_NO_TRAY="1", SDL_VIDEODRIVER="x11", SDL_AUDIODRIVER="dummy",
               LIBGL_ALWAYS_SOFTWARE="1")
    return env


def arguments(scene, path):
    return [str(BINARY), "--bundle", str(BUNDLE), "--screenshot", str(path),
            "--screenshot-scene", scene, "--screenshot-width", "1080",
            "--screenshot-height", "2160", "--screenshot-ui-scale", "25",
            "--screenshot-theme", "2", "--screenshot-dark", "0"]


def capture():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (HERE / "screens").mkdir(exist_ok=True)
    provenance = {"binary": HARNESS.digest(BINARY), "bundle": HARNESS.digest(BUNDLE), "screens": []}
    for key, scene, expected in SCENES:
        selected = [value for value in sys.argv[1:] if not value.startswith("--")]
        if selected and key not in selected:
            continue
        path = HERE / "screens" / f"{key}.png"
        with tempfile.TemporaryDirectory(prefix="profile-", dir=OUTPUT) as profile:
            if scene.startswith("tai_chi"):
                cache = Path(profile) / "packages"
                cache.mkdir()
                for name in ("taichi", "taichi.en"):
                    shutil.copyfile(ROOT / "build/practice-content" / f"{name}.zib",
                                    cache / f"practice-{name}.zib")
            with (OUTPUT / f"{key}.log").open("w") as log:
                HARNESS.run_capture(["xvfb-run", "-a", "-n", "300", "-s",
                    "-screen 0 1080x2160x24", *arguments(scene, path)],
                    environment(Path(profile)), log, timeout=60)
        text = HARNESS.check_image(path, (1080, 2160), expected)
        (OUTPUT / f"{key}.txt").write_text(text)
        provenance["screens"].append({"key": key, "scene": scene, "sha256": HARNESS.digest(path)})
        print(f"Captured {key}", flush=True)
    assert provenance["binary"] == HARNESS.digest(BINARY), "Binary changed during capture"
    assert provenance["bundle"] == HARNESS.digest(BUNDLE), "Bundle changed during capture"
    (ROOT / "backup/video-review/capture.json").write_text(json.dumps(provenance, indent=2) + "\n")


def extras():
    sys.path.insert(0, str(ROOT / "tests"))
    from ui_driver import UiDriver
    with tempfile.TemporaryDirectory(prefix="extras-", dir=OUTPUT) as temporary:
        temporary = Path(temporary)
        env = environment(temporary)
        with (OUTPUT / "display.log").open("w") as log:
            display = subprocess.Popen(["Xvfb", "-displayfd", "1", "-screen", "0",
                                        "1080x2160x24", "-nolisten", "tcp"],
                                       env=env, stdout=subprocess.PIPE, stderr=log)
            number = display.stdout.readline().decode().strip()
            display.stdout.close()
            assert number.isdecimal()
            env["DISPLAY"] = ":" + number
            try:
                for key, scene in (("03-workout-session", "workout_home"),
                                   ("06-shop", "promo_habits"), ("07-radio", "apps_library"),
                                   ("08-diary", "diary")):
                    selected = [value for value in sys.argv[1:] if not value.startswith("--")]
                    if selected and key not in selected:
                        continue
                    profile = temporary / key
                    profile.mkdir()
                    driver = UiDriver(profile / "driver")
                    app_env = env | driver.environment() | {
                        "INBE_SCREENSHOT_DATA_ROOT": str(profile), "APP_SHOT_WINDOW": "1",
                        "INBE_NODE_APP_FILE": str(ROOT / "build/node-apps/radio.zib")}
                    if key.startswith("08"):
                        picker = profile / "bin"
                        picker.mkdir()
                        image = ROOT / "design/promo-film/three/plates/lake.jpg"
                        (picker / "zenity").write_text("#!/bin/sh\nprintf '%s\\n' '" + str(image) + "'\n")
                        (picker / "zenity").chmod(0o755)
                        app_env["PATH"] = str(picker) + ":" + app_env["PATH"]
                    log_path = OUTPUT / f"{key}.log"
                    with log_path.open("w") as app_log:
                        app = subprocess.Popen(arguments(scene, profile / "unused.png"),
                                               cwd=ROOT, env=app_env, stdout=app_log,
                                               stderr=subprocess.STDOUT)
                        driver.attach(app, log_path)
                        try:
                            driver.wait(role="button")
                            if key.startswith("03"):
                                driver.press(label="Start Practice", role="button")
                                time.sleep(7)
                            elif key.startswith("06"):
                                driver.press(key=4120, role="button")
                                for name in ("A quiet tea break", "An afternoon with a book"):
                                    driver.press(role="text_field", index=0)
                                    driver.type(name)
                                    driver.press(label="Add", role="button")
                            elif key.startswith("07"):
                                driver.press(label="radio", role="button")
                                driver.wait(label="PLAY", role="button", timeout=20)
                            else:
                                driver.press(label="Attach photo", role="button")
                                time.sleep(2)
                                driver.press(label="Today", role="button")
                            # Let achievement notices clear before the base frame.
                            time.sleep(6)
                            found = subprocess.check_output(["xdotool", "search", "--onlyvisible",
                                                             "--pid", str(app.pid)], env=env, text=True)
                            window = found.splitlines()[0]
                            subprocess.run(["import", "-window", window,
                                            str(HERE / "screens" / f"{key}.png")],
                                           env=env, check=True, timeout=15)
                            (OUTPUT / f"{key}.txt").write_text(driver.text())
                            print(f"Captured {key}", flush=True)
                        finally:
                            app.terminate()
                            app.wait(timeout=10)
            finally:
                display.terminate()
                display.wait(timeout=10)


def receipt():
    record = {
        "binary_sha256": HARNESS.digest(BINARY),
        "bundle_sha256": HARNESS.digest(BUNDLE),
        "screens": {path.name: HARNESS.digest(path)
                    for path in sorted((HERE / "screens").glob("*.png"))},
        "privacy": "Private Xvfb; disposable demo profiles; no owner data or live desktop capture",
        "status": "Owner section selection pending; no publication",
    }
    (ROOT / "backup/video-review/screens.json").write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    if "--extras" in sys.argv:
        extras()
    else:
        capture()
        if len(sys.argv) == 1:
            extras()
    receipt()
