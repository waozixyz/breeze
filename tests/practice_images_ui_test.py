#!/usr/bin/env python3
"""Every practice shows its picture, and a running Sun Salutation its figure."""
import ast
import contextlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

from PIL import Image, ImageChops, ImageStat

from ui_driver import UiDriver

DISPLAY_KEYS = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS")
assert all(not os.environ.get(key) for key in DISPLAY_KEYS), "Inherited desktop environment"
root = Path(__file__).resolve().parents[1]
binary = Path(sys.argv[1]).resolve()
bundle = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None
output = root / "build/practice-images-ui-test"
output.mkdir(parents=True, exist_ok=True)
WIDTH, HEIGHT = 390, 844
PRACTICES = (
    ("wim-hof", "Wim Hof Breathing"),
    ("patterns", "Steady Box Breath"),
    ("meditation", "Meditation"),
    ("astral-projection", "Astral Projection"),
    ("sun-salutation", "Sun Salutation"),
    ("tai-chi", "Tai Chi"),
    ("workout", "7-Minute Workout"),
    ("workout-short", "4-Minute Workout"),
)
driver = UiDriver(output / "driver")
environment = os.environ | driver.environment() | {
    "SDL_VIDEODRIVER": "x11", "SDL_AUDIODRIVER": "dummy",
    "HARMONY_DESKTOP_RECOVERY": "0", "YUE_DESKTOP_RECOVERY": "0", "APP_NO_TRAY": "1"}
# The banner skies follow the local clock. Run where it is just past midnight:
# the sun or moon is then near the top of its arc, inside a narrow card.
environment["TZ"] = "SKY-%d" % ((24 - time.gmtime().tm_hour) % 24)


def command(*args):
    return subprocess.check_output(args, env=environment, text=True, timeout=5).strip()


def capture(window, name):
    path = output / (name + ".png")
    command("import", "-window", window, str(path))
    with Image.open(path) as image:
        return image.convert("RGB").copy()


def pictured(image, box):
    """A loaded picture varies; a missing one leaves the flat page colour."""
    return max(ImageStat.Stat(image.crop(box)).stddev) > 12


def has_foreground_detail(image):
    # The sky and backdrop fade still vary when a tint flattens the figures
    # and landscapes. Sample the warm colors and shading in the artwork itself.
    foreground = image.crop((80, 185, WIDTH - 80, 375))
    colors = {(red // 12, green // 12, blue // 12)
              for red, green, blue in foreground.getdata()
              if red > 55 and red > green + 12 and red > blue + 27}
    return len(colors) >= 24


def matching_pixels(image, match):
    return [(x, y) for y in range(image.height) for x in range(image.width)
            if match(*image.getpixel((x, y)))]


def workout_outfit(figure, upright=False):
    top = matching_pixels(figure, lambda r, g, b: 45 <= r <= 95 and g >= r + 45 and g >= b + 9)
    leggings = matching_pixels(figure, lambda r, g, b: 22 <= r <= 48 and 52 <= g <= 83 and 0 <= b - g <= 7)
    assert len(top) >= 125 and len(leggings) >= 450, ("Workout top or leggings missing", len(top), len(leggings))
    if upright:
        top_y = sorted(y for x, y in top)[len(top) * 9 // 10]
        hip_y = sorted(y for x, y in leggings)[len(leggings) // 12]
        assert hip_y > top_y, "The top overlaps the leggings in the standing pose"
        center = sorted(x for x, y in leggings)[len(leggings) // 2]
        waist = figure.crop((center - 16, top_y, center + 16, hip_y))
        assert len(matching_pixels(waist, lambda r, g, b: r >= 207 and 10 <= r - g <= 55 and g > b)) >= 20, \
            "The crop top's waist opening is missing"
        ankle_y = max(y for x, y in leggings)
        assert ankle_y - hip_y >= 65, "The fitted leggings end above the ankles"


def changed_pixels(before, after, bounds, minimum):
    return sum(max(pixel) >= minimum for pixel in
               ImageChops.difference(before.crop(bounds), after.crop(bounds)).getdata())


def moving_sky(window, name, first):
    # Sample above the square, figure and vapour: clouds drift and stars flicker.
    bounds = (52, 59, WIDTH - 42, 127)
    counts = []
    for sample in range(1, 4):
        time.sleep(1.1)
        image = capture(window, f"{name}-sky-{sample}")
        counts.append(changed_pixels(first, image, bounds, 4))
    assert max(counts) >= 60, (name, "The live sky did not change", counts)
    print(f"{name} live sky: {max(counts)} changing pixels", flush=True)


def log_tail(path):
    with path.open("rb") as log:
        log.seek(max(0, path.stat().st_size - 4000))
        return log.read(4000).decode(errors="replace")


def state(window):
    value = command("xprop", "-id", window, "_HARMONY_APP_STATE")
    assert " = " in value, "App has not published its state"
    return json.loads(ast.literal_eval(value.split(" = ", 1)[1]))


def pause(window, paused, request):
    control = "practice.pause" if paused else "practice.resume"
    command("xprop", "-id", window, "-f", "_HARMONY_APP_ACTION", "8s", "-set",
            "_HARMONY_APP_ACTION", json.dumps(dict(control=control, request_id=request)))
    deadline = time.monotonic() + 5
    while state(window)["last_request_id"] != request:
        assert time.monotonic() < deadline, "Pause action was not handled"
        time.sleep(.05)
    actual = state(window)
    assert actual["last_request_ok"] and actual["paused"] == paused, actual


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def launch(profile, name):
    log_path = output / (name + ".log")
    arguments = [str(binary)] + (["--bundle", str(bundle)] if bundle else [])
    with log_path.open("w") as log:
        app = subprocess.Popen(arguments, cwd=root, env=environment | {"APP_DATA_ROOT": str(profile)},
                               stdout=log, stderr=subprocess.STDOUT)
    driver.attach(app, log_path)
    for _ in range(200):
        assert app.poll() is None, log_tail(log_path)
        found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                               env=environment, capture_output=True, text=True)
        if found.returncode == 0 and (profile / "inbe.db").exists():
            window = found.stdout.splitlines()[0]
            return app, window
        time.sleep(0.1)
    stop(app)
    raise AssertionError("Inbe did not map its window")


with tempfile.TemporaryDirectory(prefix="profile-", dir=output) as directory, contextlib.ExitStack() as stack:
    profile = Path(directory)
    for name in ("HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME", "XDG_RUNTIME_DIR"):
        path = profile / name.lower()
        path.mkdir(mode=0o700)
        environment[name] = str(path)
    display_log = stack.enter_context((output / "display.log").open("w"))
    display = subprocess.Popen(["Xvfb", "-noreset", "-displayfd", "1", "-screen", "0", "1280x900x24",
                                "-nolisten", "tcp"], env=environment,
                               stdout=subprocess.PIPE, stderr=display_log)
    stack.callback(stop, display)
    number = display.stdout.readline().decode().strip()
    display.stdout.close()
    assert number.isdecimal() and display.poll() is None, "Private display did not start"
    server = Path(f"/proc/{display.pid}")
    assert server.stat().st_uid == os.getuid(), "Private X server has another owner"
    assert server.joinpath("exe").resolve() == Path(shutil.which("Xvfb")).resolve(), "Unexpected X server"
    assert b"-displayfd\x001\x00" in server.joinpath("cmdline").read_bytes(), "Unexpected display allocation source"
    display_log.write(f"Verified owned Xvfb pid={display.pid} display=:{number}\n")
    display_log.flush()
    environment["DISPLAY"] = ":" + number
    cache = profile / "packages"
    cache.mkdir()
    # Start the real practice offline. A cover on the Install screen must
    # never count as the running guide, even though both contain a picture.
    for name in ("sunsalutation", "guide.en"):
        shutil.copyfile(root / "build/practice-content" / (name + ".zx"),
                        cache / ("practice-" + name + ".zx"))
    app, _ = launch(profile, "first-start")
    stop(app)
    with sqlite3.connect(profile / "inbe.db") as db:
        user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
        settings = {"language": "en", "language_system": 0, "language_setup_done": 1,
                    "apps_setup_done": 1, "main_tab": 1, "tutorial_seen": 1,
                    "theme": 0, "theme_mode": 2, "theme_source": 0,
                    "habits_guide_seen": 1, "lumi_guides_seen": 127, "launcher_guide_seen": 1, "package_updates_allowed": 0,
                    "voice_narration_enabled": 0, "music_volume": 0,
                    "sun_salutation_character": 0,
                    "sun_salutation_start_seconds": 6, "sun_salutation_end_seconds": 6,
                    "apps_last_update_check": 1900000000}
        for key, value in settings.items():
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                       "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value",
                       (user, key, str(value)))
    app, window = launch(profile, "practice")
    try:
        driver.wait(label="Wim Hof Breathing", role="text")
        command("xdotool", "windowsize", window, str(WIDTH), str(HEIGHT))
        command("xdotool", "windowmove", window, "0", "0")
        command("xdotool", "windowfocus", window)
        deadline = time.monotonic() + 5
        while capture(window, "viewport").size != (WIDTH, HEIGHT):
            assert time.monotonic() < deadline, "Practice did not render the requested viewport"
            time.sleep(.05)
        missing = []
        flattened = []
        banner_skies = {}
        for index, (practice, title) in enumerate(PRACTICES):
            if index:
                command("xdotool", "key", "Right")
            driver.wait(label=title, role="text")
            # Complete the card slide before sampling this practice's artwork.
            time.sleep(0.6)
            image = capture(window, practice)
            banner_skies[practice] = image.crop((60, 58, WIDTH // 2, 144))
            if practice == "wim-hof" and settings["theme_mode"] == 2:
                # The rendered moon stays inside the narrow card, even behind a cloud.
                sky_band = image.crop((3, 44, WIDTH - 3, 200))
                moon = sum(red > 150 and green > 155 and blue > 150 for red, green, blue in sky_band.getdata())
                assert moon >= 30, f"Wim Hof's moon is missing from the narrow card ({moon} pixels)"
            if practice in ("wim-hof", "patterns"):
                moving_sky(window, f"{practice}-night", image)
                driver.press(label="Light", role="button")
                driver.wait(label="Dark", role="button")
                time.sleep(.7)
                moving_sky(window, f"{practice}-day", capture(window, f"{practice}-day"))
                driver.press(label="Dark", role="button")
                driver.wait(label="Light", role="button")
                time.sleep(.7)
            if practice == "patterns":
                for phase in ("Inhale", "Hold", "Exhale"):
                    assert not driver.find(label=phase, role="text", visible=True)
                image = capture(window, "patterns-marker-start")
                time.sleep(1.2)
                advanced = capture(window, "patterns-inhale-progress")
                changed = changed_pixels(image, advanced, (90, 150, WIDTH - 90, 346), 24)
                assert 25 < changed < 600, f"Expected a moving marker on the square, got {changed} pixels"
            if not pictured(image, (0, 40, WIDTH, 420)):
                missing.append(practice)
            elif not has_foreground_detail(image):
                flattened.append(practice)
        assert not flattened, "Dark practice cards lost the artwork detail: " + ", ".join(flattened)
        for index, (name, sky_image) in enumerate(banner_skies.items()):
            for other, previous in list(banner_skies.items())[:index]:
                changes = max(ImageStat.Stat(ImageChops.difference(sky_image, previous)).mean)
                assert changes > 1, f"{name} and {other} still show the same sky"
        for title in ("7-Minute Workout", "Tai Chi", "Sun Salutation"):
            command("xdotool", "key", "Left")
            driver.wait(label=title, role="text")
        driver.wait(label="Start Practice", role="button")
        sky = (55, 52, WIDTH - 55, 225)
        first_sky = capture(window, "sun-salutation-banner-first").crop(sky)
        time.sleep(8)
        next_sky = capture(window, "sun-salutation-banner-eight-seconds").crop(sky)
        changed = sum(max(pixel) >= 6 for pixel in ImageChops.difference(first_sky, next_sky).getdata())
        assert changed >= 100, f"Visible Sun Salutation banner changed only {changed} pixels"
        print(f"Visible Sun Salutation banner changed {changed} pixels over eight seconds", flush=True)
        driver.press(label="How to", role="button")
        driver.wait(contains="Mountain")
        capture(window, "sun-salutation-guide")
        driver.press(label="Back", role="button")
        driver.press(label="Start Practice", role="button")
        driver.wait(label="Settle in", role="text")
        driver.wait(label="Next", role="button")
        actual = state(window)
        assert actual["practice_running"] and actual["screen"] == 3, actual
        deadline = time.monotonic() + 5
        while any(node["kind"] == "navigation_bar" and node["visible"] for node in driver.tree()):
            assert time.monotonic() < deadline, "Practice navigation did not retract"
            time.sleep(.05)
        next_button = driver.wait(label="Next", role="button")
        assert next_button["height"] >= 44 and next_button["y"] + next_button["height"] <= HEIGHT, \
            "Practice controls are clipped"
        figure = (24, 240, WIDTH - 24, round(next_button["y"] - 18))
        running = capture(window, "sun-salutation-running")
        if not pictured(running, figure):
            missing.append("sun-salutation figure")
        workout_outfit(running.crop(figure), upright=True)
        driver.press(label="Next", role="button", settle=False)
        driver.wait(label="Step 1", role="text")
        driver.wait(label="Mountain pose", role="text")
        time.sleep(.5)
        first = capture(window, "sun-salutation-moving-first").crop(figure)
        time.sleep(1.5)
        second = capture(window, "sun-salutation-mountain-prayer").crop(figure)
        assert ImageChops.difference(first, second).getbbox(), "The live guide did not move"
        assert ImageChops.difference(running.crop(figure), second).getbbox(), "Mountain reused the intro pose"
        pause(window, True, "practice-images-pause")
        time.sleep(.2)
        first = capture(window, "sun-salutation-paused-first").crop(figure)
        time.sleep(.6)
        second = capture(window, "sun-salutation-paused-second").crop(figure)
        assert not ImageChops.difference(first, second).getbbox(), "The paused guide kept moving"
        pause(window, False, "practice-images-resume")
        time.sleep(.5)
        resumed = capture(window, "sun-salutation-resumed").crop(figure)
        assert ImageChops.difference(second, resumed).getbbox(), "The guide did not resume"
        driver.wait(label="Standing forward fold", role="text")
        time.sleep(2)
        descent = capture(window, "sun-salutation-fold-descent")
        time.sleep(2.7)
        fold = capture(window, "sun-salutation-forward-fold")
        assert ImageChops.difference(descent.crop(figure), fold.crop(figure)).getbbox(), \
            "The guide did not continue into the fold"
        workout_outfit(descent.crop(figure))
        workout_outfit(fold.crop(figure))
        for step, name in (("Low lunge", "lunge"), ("Plank", "plank"),
                           ("Knees, chest and chin", "lowering-to-floor"),
                           ("Downward-facing dog", "downward-dog")):
            driver.wait(label=step, role="text", timeout=25)
            time.sleep(2)
            workout_outfit(capture(window, f"sun-salutation-{name}").crop(figure))
        assert not missing, "Practice pictures are missing: " + ", ".join(missing)
        assert app.poll() is None, log_tail(output / "practice.log")
    finally:
        stop(app)
print("Eight practice covers, day and night sky motion, the Box marker, and Sun Salutation outfit and playback passed")
