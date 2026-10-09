"""Check rendered labels and navigation contrast on an owned Xvfb display."""

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

from PIL import Image, ImageOps, ImageStat

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/native-visual-test"
DESKTOP_ENV = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "GDK_DISPLAY",
               "DBUS_SESSION_BUS_ADDRESS", "SESSION_MANAGER")


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def contrast(first, second):
    def luminance(color):
        channels = [value / 255 for value in color]
        linear = [value / 12.92 if value <= .04045 else
                  ((value + .055) / 1.055) ** 2.4 for value in channels]
        return sum(value * weight for value, weight in
                   zip(linear, (.2126, .7152, .0722)))
    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + .05) / (dark + .05)


def ocr_has_label(recognized, label):
    """Whether OCR found a label. CI's tesseract 5.3.4 sometimes reads one
    letter of a large single word wrong ("materlal"), so a one-word label
    also matches a word of the same length with one different letter."""
    if label in recognized:
        return True
    if " " in label or len(label) < 5:
        return False
    for word in recognized.split():
        if len(word) == len(label) and sum(a != b for a, b in zip(word, label)) == 1:
            return True
    return False


def read_text(image, name, single_line=False):
    # Normalize the OCR input only; assertions inspect the original pixels.
    OUTPUT.mkdir(parents=True, exist_ok=True)
    gray = ImageOps.grayscale(image)
    if ImageStat.Stat(gray).mean[0] < 128:
        gray = ImageOps.invert(gray)
    gray = ImageOps.autocontrast(gray)
    resampling = Image.Resampling.NEAREST if single_line else Image.Resampling.LANCZOS
    gray = gray.resize((gray.width * 3, gray.height * 3), resampling)
    path = OUTPUT / (name + "-ocr.png")
    gray.save(path)
    result = subprocess.run(["tesseract", str(path), "stdout", "--psm",
                             "7" if single_line else "11"],
                            check=True, text=True, capture_output=True, timeout=10)
    path.unlink()
    return " ".join(re.findall(r"[a-z0-9%]+", result.stdout.lower()))


def assert_selection(image, bounds, name, expected="apps", below_label=12):
    tile = image.crop(bounds)
    width, height = tile.size
    # Sample the flat fill, top outline and surrounding page separately.
    fill = tile.getpixel((width // 2, 6))
    outside = image.getpixel((bounds[0] + width // 2, bounds[1] - 3))
    edge = tile.getpixel((width // 2, 1))
    assert fill != outside, f"{name}: active app has no visible fill"
    assert contrast(edge, outside) >= 3, f"{name}: active outline blends into the page"
    label = tile.crop((8, height // 2 + 5, width - 8, height - below_label))
    colors = label.getcolors(label.width * label.height)
    _, ink = max(colors, key=lambda entry: contrast(entry[1], fill))
    ink_count = sum(count for count, color in colors if contrast(color, fill) >= 3)
    assert ink_count >= 8, f"{name}: label has no readable glyph interiors"
    ratio = contrast(ink, fill)
    assert ratio >= 4.5, f"{name}: active label contrast is {ratio:.2f}:1"
    recognized = read_text(label, name, single_line=True).replace(" ", "")
    assert expected in recognized, f"{name}: {expected} label is clipped or missing: {recognized}"
    return {"label_contrast": round(ratio, 2),
            "outline_contrast": round(contrast(edge, outside), 2)}


def assert_regressions_rejected(image, bounds, name):
    """Prove the oracle rejects the defects it is meant to guard against."""
    left, top, right, bottom = bounds
    fill = image.getpixel(((left + right) // 2, top + 6))
    outside = image.getpixel(((left + right) // 2, top - 3))
    label = (left + 8, top + (bottom - top) // 2 + 5, right - 8, bottom - 12)
    for defect, message in (("fill", "no visible fill"),
                            ("outline", "outline blends"),
                            ("missing-label", "readable glyph interiors"),
                            ("faint-label", "readable glyph interiors")):
        broken = image.copy()
        if defect == "fill":
            broken.putpixel(((left + right) // 2, top + 6), outside)
        elif defect == "outline":
            broken.putpixel(((left + right) // 2, top + 1), outside)
        elif defect == "missing-label":
            broken.paste(fill, label)
        else:
            text = broken.crop(label)
            faint = tuple(round(channel * .8 + (255 - channel) * .2) for channel in fill)
            pixels = text.load()
            for y in range(text.height):
                for x in range(text.width):
                    pixels[x, y] = faint if contrast(pixels[x, y], fill) > 1.2 else fill
            broken.paste(text, label)
        try:
            assert_selection(broken, bounds, name + "-" + defect)
        except AssertionError as error:
            assert message in str(error), f"{defect}: failed for an unrelated reason: {error}"
        else:
            raise AssertionError(f"Visual oracle accepted {defect}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("binary", type=Path)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--appearance-only", action="store_true",
                        help="Investigate label layout without rerunning the palette matrix")
    arguments = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    evidence = []
    receipt = {
        "status": "running",
        "quick": arguments.quick,
        "binary_sha256": hashlib.sha256(arguments.binary.read_bytes()).hexdigest(),
        "appearance_only": arguments.appearance_only,
        "expected_checks": ((0 if arguments.appearance_only else (25 if arguments.quick else 313))
                            + (2 if arguments.quick else 16)),
        "appearance_ocr_range_percent": [220, 250] if arguments.quick else [100, 250],
        "checks": evidence,
    }
    result_path = OUTPUT / "results.json"
    result_path.write_text(json.dumps(receipt, indent=2) + "\n")
    try:
        run_cases(arguments, evidence)
        assert len(evidence) == receipt["expected_checks"], "Incomplete visual matrix"
        receipt["status"] = "passed"
    except BaseException as error:
        receipt["status"] = "failed"
        receipt["error"] = str(error)
        raise
    finally:
        result_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"Native visual checks: {len(evidence)} text and navigation checks passed", flush=True)


def run_cases(arguments, evidence):
    environment = {key: value for key, value in os.environ.items() if key not in DESKTOP_ENV}
    environment.update(YUE_DESKTOP_RECOVERY="0", APP_NO_TRAY="1",
                       SDL_VIDEODRIVER="x11", SDL_AUDIODRIVER="dummy",
                       LIBGL_ALWAYS_SOFTWARE="1", APP_SHOT_WINDOW="1", LANGUAGE="en")
    with contextlib.ExitStack() as stack:
        display_log = stack.enter_context((OUTPUT / "display.log").open("w"))
        display = subprocess.Popen(["Xvfb", "-displayfd", "1", "-screen", "0",
                                    "1280x1000x24", "-nolisten", "tcp"],
                                   env=environment, stdout=subprocess.PIPE, stderr=display_log)
        stack.callback(stop, display)
        number = display.stdout.readline().decode().strip()
        display.stdout.close()
        assert number.isdecimal(), "Private display did not start"
        environment["DISPLAY"] = ":" + number

        def command(*args):
            return subprocess.run(args, env=environment, check=True, capture_output=True,
                                  text=True, timeout=5).stdout.strip()

        @contextlib.contextmanager
        def application(name, scene, width, height, scale=10, theme=9, dark=0):
            path = OUTPUT / (name + ".png")
            log_path = OUTPUT / (name + ".log")
            with log_path.open("w") as log:
                app = subprocess.Popen([str(arguments.binary.resolve()), "--screenshot", str(path),
                                        "--screenshot-scene", scene, "--screenshot-width", str(width),
                                        "--screenshot-height", str(height), "--screenshot-ui-scale", str(scale),
                                        "--screenshot-theme", str(theme), "--screenshot-dark", str(dark)],
                                       cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT)
                try:
                    deadline = time.monotonic() + 20
                    window = ""
                    while time.monotonic() < deadline:
                        assert app.poll() is None, log_path.read_text()
                        found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                                               env=environment, capture_output=True, text=True, timeout=2)
                        if found.returncode == 0 and (Path("/tmp") / f"inbe-screenshot-{app.pid}" / "inbe.db").exists():
                            window = found.stdout.splitlines()[0]
                            break
                        time.sleep(.1)
                    assert window, f"{name}: app did not finish its first frame"
                    command("xdotool", "windowfocus", window)
                    command("xdotool", "mousemove", "--window", window, str(width - 2), "2")
                    time.sleep(.6)

                    def capture(suffix=""):
                        target = OUTPUT / (name + suffix + ".png")
                        command("import", "-window", window, str(target))
                        with Image.open(target) as image:
                            assert image.size == (width, height), f"{name}: wrong viewport"
                            return image.convert("RGB").copy()

                    yield window, capture
                    assert app.poll() is None, log_path.read_text()
                    for failure in ("frame rejected", "portable execution failed", "portable subset"):
                        assert failure not in log_path.read_text(), log_path.read_text()
                finally:
                    stop(app)
                    shutil.rmtree(Path("/tmp") / f"inbe-screenshot-{app.pid}", ignore_errors=True)

        # Every app palette must distinguish the active route at rest, on hover
        # and while pressed, on the actual desktop and phone compositions.
        layouts = () if arguments.appearance_only else ((900, 720, "desktop"), (390, 844, "phone"))
        for width, height, layout in layouts:
            for theme in ([9] if arguments.quick else range(13)):
                for dark in (0, 1):
                    name = f"selection-{layout}-{theme}-{dark}"
                    # The phone's compact dock is 56 units tall at the bottom edge.
                    bounds = (12, 192, 76, 264) if layout == "desktop" else (261, 788, 377, 843)
                    below_label = 12 if layout == "desktop" else 6
                    with application(name, "launcher", width, height, theme=theme, dark=dark) as (window, capture):
                        for state in ("idle", "hover", "pressed"):
                            if state != "idle":
                                command("xdotool", "mousemove", "--window", window,
                                        str((bounds[0] + bounds[2]) // 2), str((bounds[1] + bounds[3]) // 2))
                            if state == "pressed":
                                command("xdotool", "mousedown", "1")
                            time.sleep(.25)
                            image = capture("-" + state)
                            metrics = assert_selection(image, bounds, name + "-" + state,
                                                       below_label=below_label)
                            evidence.append({"case": name, "state": state, **metrics})
                            if (layout == "desktop" and dark == 0 and state == "idle"
                                    and theme == (9 if arguments.quick else 0)):
                                assert_regressions_rejected(image, bounds, name)
                                evidence.append({"case": name, "negative_controls": 4})
                        # Cancel activation: releasing inside Apps toggles the
                        # launcher and would make the next card assertion inspect
                        # the Practice page instead of the app library.
                        command("xdotool", "mousemove", "--window", window, str(width - 2), "2")
                        time.sleep(.15)
                        command("xdotool", "mouseup", "1")
                        card = (500, 184, 880, 272) if layout == "desktop" else (201, 184, 370, 272)
                        command("xdotool", "mousemove", "--window", window, str(width - 2), "2")
                        for state in ("idle", "hover", "pressed"):
                            if state != "idle":
                                command("xdotool", "mousemove", "--window", window,
                                        str((card[0] + card[2]) // 2), str((card[1] + card[3]) // 2))
                            if state == "pressed":
                                command("xdotool", "mousedown", "1")
                            time.sleep(.25)
                            image = capture("-card-" + state)
                            # App cards show their download size on a muted line just
                            # below the name; read the name above that line.
                            metrics = assert_selection(image, card, name + "-card-" + state, "practice",
                                                       below_label=17)
                            evidence.append({"case": name, "state": "card-" + state, **metrics})
                        # Finish the held press outside the card so it cannot open
                        # a route before the fixture's last frame is checked.
                        command("xdotool", "mousemove", "--window", window, str(width - 2), "2")
                        time.sleep(.15)
                        command("xdotool", "mouseup", "1")
            print(f"Selection palettes passed for {layout}", flush=True)

        # Narrow Appearance labels must wrap and remain reachable when enlarged,
        # including the reported 220%/250% failures. The pixel-reference test
        # covers small glyphs down to 50%; OCR cannot reliably read 6px letters.
        # The separate zoom test checks a readable title at all 21 scale values.
        scales = (22, 25) if arguments.quick else range(10, 26)
        for scale in scales:
            labels = ("style", "color theme", "mode", "scale factor",
                      "navigation position", "material", "mono", "light",
                      "automatic", f"{scale * 10}%")
            name = f"appearance-phone-{scale * 10}"
            with application(name, "theme_selection", 390, 844, scale=scale) as (window, capture):
                texts = []
                for step in range(18):
                    image = capture(f"-scroll-{step}")
                    texts.append(read_text(image.crop((0, 0, 390, max(1, 844 - round(84 * scale / 10)))),
                                           name + str(step)))
                    if all(label in " ".join(texts) for label in labels):
                        break
                    command("xdotool", "mousemove", "--window", window, "210", "250")
                    command("xdotool", "click", "5")
                    time.sleep(.15)
                recognized = " ".join(texts)
                for label in labels:
                    assert ocr_has_label(recognized, label), f"{name}: {label} label is clipped, missing or unreachable: {recognized}"
                evidence.append({"case": name, "labels": recognized, "scroll_frames": len(texts)})


if __name__ == "__main__":
    main()
