"""Check rendered labels and navigation contrast on an owned Xvfb display."""

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from PIL import Image

from ui_driver import UiDriver

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


def assert_selection(image, bounds, name, expected="apps", below_label=12, node=None):
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
    # Small navigation labels contain antialiased strokes with few fully
    # opaque pixels. Check their presence separately from the 4.5:1 ink test.
    ink_count = sum(count for count, color in colors if contrast(color, fill) >= 2)
    assert ink_count >= 8, f"{name}: label has no readable glyph strokes"
    ratio = contrast(ink, fill)
    assert ratio >= 4.5, f"{name}: active label contrast is {ratio:.2f}:1"
    # The tile is the widget the app reports there: its label, and the
    # active route or app.
    if node is not None:
        assert node["label"].lower() == expected, f"{name}: {expected} label is missing: {node['label']}"
        assert node["selected"], f"{name}: {expected} is not shown as active"
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
                            ("missing-label", "readable glyph strokes"),
                            ("faint-label", "readable glyph strokes")):
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


def assert_app_entry(image, bounds, name, node):
    tile = image.crop(bounds)
    width, height = tile.size
    fill = tile.getpixel((width // 2, 6))
    label = tile.crop((60, 8, width - 8, height - 8))
    colors = label.getcolors(label.width * label.height)
    _, ink = max(colors, key=lambda entry: contrast(entry[1], fill))
    ink_count = sum(count for count, color in colors if contrast(color, fill) >= 3)
    assert ink_count >= 8, f"{name}: app name has no readable glyph interiors"
    ratio = contrast(ink, fill)
    assert ratio >= 4.5, f"{name}: app name contrast is {ratio:.2f}:1"
    assert node["label"] == "Practice", f"{name}: Practice label is missing"
    assert not node["selected"], f"{name}: last-opened app is highlighted"
    return {"label_contrast": round(ratio, 2), "selected": False}


def assert_app_entry_regressions_rejected(image, bounds, name, node):
    left, top, right, bottom = bounds
    fill = image.getpixel(((left + right) // 2, top + 6))
    missing = image.copy()
    missing.paste(fill, (left + 60, top + 8, right - 8, bottom - 8))
    for broken, entry, message in ((missing, node, "no readable glyph interiors"),
                                   (image, node | {"selected": True}, "last-opened app is highlighted")):
        try:
            assert_app_entry(broken, bounds, name, entry)
        except AssertionError as error:
            assert message in str(error), f"App entry failed for an unrelated reason: {error}"
        else:
            raise AssertionError("App entry oracle accepted a missing name or highlighted app")


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
        "appearance_range_percent": [220, 250] if arguments.quick else [100, 250],
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
    driver = UiDriver(OUTPUT / "driver")
    environment = {key: value for key, value in os.environ.items() if key not in DESKTOP_ENV}
    environment.update(driver.environment())
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

        def settle(seconds=.25, frames=3):
            """Let hover and press transitions run, then draw a few more frames."""
            time.sleep(seconds)
            first = driver.send("status")["frame"]
            deadline = time.monotonic() + 20
            while driver.send("status")["frame"] < first + frames:
                assert time.monotonic() < deadline, "The app stopped drawing frames"
                time.sleep(.02)

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
                driver.attach(app, log_path)
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
                    driver.wait_idle(frames=3)
                    nodes = driver.tree()
                    screen = next(node for node in nodes if node["kind"] == "screen")
                    factor = width / screen["width"]

                    def on_screen(node, bottom=height):
                        """A widget's box in window pixels, as a crop box."""
                        left = round((node["x"] - screen["x"]) * factor)
                        top = round((node["y"] - screen["y"]) * factor)
                        right = round((node["x"] + node["width"] - screen["x"]) * factor)
                        lower = round((node["y"] + node["height"] - screen["y"]) * factor)
                        return left, top, right, min(lower, bottom - 1)

                    def point(x, y, down=False):
                        """Hold the app's pointer at window pixels x, y."""
                        driver.pointer(screen["x"] + x / factor, screen["y"] + y / factor, down=down)

                    # Rest the pointer in the top right corner, away from every control.
                    point(width - 2, 2)
                    settle()

                    def capture(suffix=""):
                        target = OUTPUT / (name + suffix + ".png")
                        command("import", "-window", window, str(target))
                        with Image.open(target) as image:
                            assert image.size == (width, height), f"{name}: wrong viewport"
                            return image.convert("RGB").copy()

                    yield window, capture, on_screen, point
                    assert app.poll() is None, log_path.read_text()
                    for failure in ("frame rejected", "portable execution failed", "portable subset"):
                        assert failure not in log_path.read_text(), log_path.read_text()
                finally:
                    stop(app)
                    shutil.rmtree(Path("/tmp") / f"inbe-screenshot-{app.pid}", ignore_errors=True)

        def in_navigation(nodes, label):
            bars = {node["index"] for node in nodes if node["kind"] == "navigation_bar"}
            return next(node for node in nodes if node["label"] == label and node["parent"] in bars)

        def in_page(nodes, label):
            bars = {node["index"] for node in nodes if node["kind"] == "navigation_bar"}
            return next(node for node in nodes if node["label"] == label and node["kind"] == "button"
                        and node["parent"] not in bars)

        # Every app palette must distinguish the active route at rest, on hover
        # and while pressed, on the actual desktop and phone compositions.
        layouts = () if arguments.appearance_only else ((900, 720, "desktop"), (390, 844, "phone"))
        for width, height, layout in layouts:
            for theme in ([9] if arguments.quick else range(13)):
                for dark in (0, 1):
                    name = f"selection-{layout}-{theme}-{dark}"
                    # Desktop Apps sits in the sidebar's bottom corner; the
                    # phone's compact dock is 56 units tall at the bottom edge.
                    below_label = 12 if layout == "desktop" else 6
                    with application(name, "launcher", width, height, theme=theme,
                                     dark=dark) as (window, capture, on_screen, point):
                        nodes = driver.tree()
                        apps = in_navigation(nodes, "Apps")
                        assert len(driver.find(key=apps["key"])) == 1, f"{name}: two widgets share a key"
                        bounds = on_screen(apps)
                        if layout == "desktop":
                            assert bounds[0] < 100 and bounds[3] > height - 120, \
                                f"{name}: Apps left the sidebar's bottom corner: {bounds}"
                        else:
                            assert bounds[1] >= height - 60, f"{name}: Apps left the bottom dock: {bounds}"
                        middle = ((bounds[0] + bounds[2]) // 2, (bounds[1] + bounds[3]) // 2)
                        for state in ("idle", "hover", "pressed"):
                            if state != "idle":
                                point(*middle, down=state == "pressed")
                                settle()
                            image = capture("-" + state)
                            selected = driver.find(key=apps["key"])[0]
                            metrics = assert_selection(image, bounds, name + "-" + state,
                                                       below_label=below_label, node=selected)
                            evidence.append({"case": name, "state": state, **metrics})
                            if (layout == "desktop" and dark == 0 and state == "idle"
                                    and theme == (9 if arguments.quick else 0)):
                                assert_regressions_rejected(image, bounds, name)
                                evidence.append({"case": name, "negative_controls": 4})
                        # Release away from Apps to isolate the pointer-state
                        # checks from navigation.
                        point(width - 2, 2, down=True)
                        point(width - 2, 2)
                        settle(.15)
                        # This fixture pins Habits then Practice. List entries
                        # stack vertically and keep the last-opened app ordinary.
                        nodes = driver.tree()
                        practice = in_page(nodes, "Practice")
                        assert len(driver.find(key=practice["key"])) == 1, f"{name}: two widgets share a key"
                        pinned = [node for node in nodes if node["parent"] == practice["parent"]
                                  and node["kind"] == "button" and node["width"] == practice["width"]]
                        pinned.sort(key=lambda node: (node["y"], node["x"]))
                        assert pinned.index(practice) == 1, f"{name}: Practice is not the second pinned card"
                        card = on_screen(practice)
                        middle = ((card[0] + card[2]) // 2, (card[1] + card[3]) // 2)
                        for state in ("idle", "hover", "pressed"):
                            if state != "idle":
                                point(*middle, down=state == "pressed")
                                settle()
                            image = capture("-card-" + state)
                            selected = driver.find(key=practice["key"])[0]
                            metrics = assert_app_entry(image, card, name + "-card-" + state, selected)
                            if state == "idle":
                                ordinary = on_screen(in_page(driver.tree(), "Habits"))
                                normal_fill = image.getpixel(((ordinary[0] + ordinary[2]) // 2, ordinary[1] + 6))
                                assert image.getpixel(((card[0] + card[2]) // 2, card[1] + 6)) == normal_fill, \
                                    f"{name}: last-opened app has a different fill"
                            if layout == "desktop" and dark == 0 and state == "idle" and theme == (9 if arguments.quick else 0):
                                assert_app_entry_regressions_rejected(image, card, name, selected)
                                metrics["negative_controls"] = 2
                            evidence.append({"case": name, "state": "card-" + state, **metrics})
                        # Finish the held press outside the card so it cannot open
                        # a route before the fixture's last frame is checked.
                        point(width - 2, 2, down=True)
                        point(width - 2, 2)
                        settle(.15)
            print(f"Selection palettes passed for {layout}", flush=True)

        # Narrow Appearance labels must wrap and remain reachable when enlarged,
        # including the reported 220%/250% failures: each label scrolls wholly
        # into the page, inside the phone's width and above its dock, and its
        # box shows every line it wraps to (Kryon reports hidden_lines). The
        # pixel-reference test covers small glyphs down to 50%, and the zoom
        # test checks a readable title at all 21 scale values.
        scales = (22, 25) if arguments.quick else range(10, 26)
        for scale in scales:
            labels = ("style", "color theme", "mode", "scale factor",
                      "navigation position", "material", "mono", "light",
                      "automatic", f"{scale * 10}%")
            name = f"appearance-phone-{scale * 10}"
            with application(name, "theme_selection", 390, 844, scale=scale) as (window, capture, on_screen, point):
                shown = {}
                frames = 0
                for frames in range(1, 19):
                    nodes = driver.tree()
                    screen = next(node for node in nodes if node["kind"] == "screen")
                    for node in nodes:
                        label = node["label"].lower()
                        whole = (node["visible"] and
                                 abs(node["visible_x"] - node["x"]) < .5 and
                                 abs(node["visible_y"] - node["y"]) < .5 and
                                 abs(node["visible_width"] - node["width"]) < .5 and
                                 abs(node["visible_height"] - node["height"]) < .5 and
                                 node["x"] >= screen["x"] and
                                 node["x"] + node["width"] <= screen["x"] + screen["width"])
                        if label in labels and whole:
                            shown[label] = node
                    if all(label in shown for label in labels):
                        break
                    # One wheel step down over the page, as a person scrolls.
                    driver.pointer(screen["x"] + screen["width"] * .54, screen["y"] + screen["height"] * .3,
                                   wheel=-1)
                    driver.wait_idle(frames=2, timeout=2)
                for label in labels:
                    assert label in shown, f"{name}: {label} label is clipped, missing or unreachable: {sorted(shown)}"
                    assert shown[label]["hidden_lines"] == 0, \
                        f"{name}: {label} label wraps to {shown[label]['hidden_lines']} lines its box cuts off"
                evidence.append({"case": name, "labels": " ".join(sorted(shown)), "scroll_frames": frames})


if __name__ == "__main__":
    main()
