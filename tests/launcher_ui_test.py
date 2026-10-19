"""Exercise the app launcher with disposable data on a private Xvfb display.

The app runs with Kryon's test driver: cards, pins and actions are found in
its widget tree by label and pressed through its own pointer path.
"""

import contextlib
import argparse
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile
import time

from PIL import Image, ImageDraw

from ui_driver import UiDriver

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/launcher-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
parser = argparse.ArgumentParser()
parser.add_argument("binary")
parser.add_argument("--layout", choices=("all", "desktop", "mobile"), default="all")
parser.add_argument("--drag-only", action="store_true")
parser.add_argument("--dock-only", action="store_true")
parser.add_argument("--properties-only", action="store_true",
                    help="Rename an app and change its icon in Apps › Properties")
parser.add_argument("--with-tray", action="store_true",
                    help="Enable the desktop tray using the caller's locale settings")
arguments = parser.parse_args()
BINARY = Path(arguments.binary).resolve()
DESKTOP_ENV = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS")
assert all(not os.environ.get(key) for key in DESKTOP_ENV), "Inherited desktop environment"
# Each favorite route's name in the navigation and on its Apps card.
ROUTE_LABELS = {12: "Lumi", 1: "Habits", 2: "Practice", 3: "Lists", 11: "Diary"}
TRANSITION = re.compile(r"ROUTE switch.*screen=\d+->(\d+)")


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def wait_for(predicate, message, timeout=10):
    deadline = time.monotonic() + timeout
    while True:
        result = predicate()
        if result:
            return result
        assert time.monotonic() < deadline, message() if callable(message) else message
        time.sleep(.05)


with contextlib.ExitStack() as stack:
    driver = UiDriver(OUTPUT / "driver")
    env = {key: value for key, value in os.environ.items() if key not in DESKTOP_ENV}
    env.update(YUE_DESKTOP_RECOVERY="0", APP_NO_TRAY="1", SDL_AUDIODRIVER="dummy",
               INBE_DEBUG_ROUTE="1")
    env.update(driver.environment())
    if arguments.with_tray:
        env.pop("APP_NO_TRAY", None)
    display_log = stack.enter_context((OUTPUT / "display.log").open("w"))
    display = subprocess.Popen(["Xvfb", "-displayfd", "1", "-screen", "0", "1280x1000x24",
                                "-nolisten", "tcp"], env=env, stdout=subprocess.PIPE, stderr=display_log)
    stack.callback(stop, display)
    number = display.stdout.readline().decode().strip()
    display.stdout.close()
    assert number.isdecimal(), "Private display did not start"
    env["DISPLAY"] = ":" + number

    def command(*args):
        return subprocess.run(args, env=env, check=True, capture_output=True,
                              text=True, timeout=5).stdout.strip()

    def capture(window, name):
        path = OUTPUT / (name + ".png")
        command("import", "-window", window, str(path))
        with Image.open(path) as image:
            return image.convert("RGB").copy()

    def key(window, name, changed):
        """Press a key the app reads from raylib directly, not through the
        test driver, until the screen shows its effect."""
        for attempt in range(3):
            command("xdotool", "windowfocus", window)
            command("xdotool", "keydown", "--clearmodifiers", name)
            time.sleep(.15)
            command("xdotool", "keyup", name)
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if changed():
                    return
                time.sleep(.05)
        raise AssertionError(f"{name} had no effect: {driver.text()}")

    def database(profile):
        # Read-only: a read-write connection that closes while the app has
        # lost its own lock would checkpoint and delete the WAL it writes to.
        uri = (profile / "inbe.db").as_uri() + "?mode=ro"
        return contextlib.closing(sqlite3.connect(uri, uri=True, timeout=3))

    def settings(profile):
        with database(profile) as db:
            return dict(db.execute("SELECT key,value FROM settings WHERE user_id=?", (user,)))

    def wait_setting(profile, name, expected, message=None):
        wait_for(lambda: settings(profile).get(name) == str(expected),
                 lambda: message or f"{name} is {settings(profile).get(name)!r}, not {expected!r}")

    def favorites(profile):
        saved = settings(profile)
        return [int(saved[f"launcher_favorite_{i}"])
                for i in range(int(saved["launcher_favorite_count"]))]

    def seed(profile, values):
        values.setdefault("launcher_guide_seen", 1)
        if "enabled_apps" in values:
            for bit, name in enumerate(("lists", "habits", "practices", "diary", "lumi")):
                values["app_used_" + name] = int(bool(int(values["enabled_apps"]) & (1 << bit)))
        with contextlib.closing(sqlite3.connect(profile / "inbe.db", timeout=3)) as db, db:
            for name, value in values.items():
                db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                           "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value",
                           (user, name, str(value)))

    def transitions(log):
        return TRANSITION.findall(log.read_text())

    def wait_transition(log, before, screen, message):
        """A new route switch, the last of which opens screen."""
        wait_for(lambda: len(transitions(log)) > before and transitions(log)[-1] == str(screen),
                 lambda: f"{message}: {transitions(log)}")

    def by_index(tree):
        return {node["index"]: node for node in tree}

    def under(tree, node, kind):
        nodes = by_index(tree)
        parent = nodes.get(node["parent"])
        while parent is not None:
            if parent["kind"] == kind:
                return True
            parent = nodes.get(parent["parent"])
        return False

    def navigation(tree=None):
        """The visible navigation's buttons in order, Apps last."""
        tree = tree if tree is not None else driver.tree()
        return [node for node in tree if node["kind"] == "button" and node["visible"]
                and under(tree, node, "navigation_bar")]

    def pin(label):
        matches = [node for node in navigation() if node["label"] == label]
        assert matches, f"No {label} in the navigation: {driver.text()}"
        return matches[0]

    def cards():
        """The Apps cards in Pinned and in More apps, in order."""
        tree = driver.tree()
        headings = {node["label"]: node for node in tree
                    if node["kind"] == "text" and node["label"] in ("Pinned", "More apps")}
        # Each section's shared Apps group sits inside the page's scroll.
        grid = [node for node in tree if node["kind"] == "button"
                and under(tree, node, "scroll") and not under(tree, node, "navigation_bar")
                and node["label"] not in ("Install", "App options")]
        more_top = headings["More apps"]["y"] if "More apps" in headings else float("inf")
        pinned = [node for node in grid if node["y"] < more_top]
        more = [node for node in grid if node["y"] >= more_top]
        return pinned, more, tree

    def corner(card, tree):
        """The install or options symbol in a card's top-right corner."""
        inside = [node for node in tree if node["label"] in ("Install", "App options")
                  and card["x"] <= node["x"] and node["x"] + node["width"] <= card["x"] + card["width"]
                  and card["y"] <= node["y"] and node["y"] + node["height"] <= card["y"] + card["height"]]
        assert len(inside) == 1, f"{card['label']} has no corner symbol: {inside}"
        assert inside[0]["x"] + inside[0]["width"] / 2 > card["x"] + card["width"] / 2, "Symbol is not at the right"
        assert inside[0]["y"] + inside[0]["height"] / 2 < card["y"] + card["height"] / 2, "Symbol is not at the top"
        return inside[0]

    def press(node, hold=0.0):
        """Press one widget found in the tree, held for a while if asked."""
        if hold <= 0:
            selector = dict(key=node["key"])
            if node["label"]:
                selector["label"] = node["label"]
            driver.press(**selector)
            return
        x, y = UiDriver.center(node)
        driver.pointer(x, y)
        driver.pointer(x, y, down=True)
        time.sleep(hold)
        driver.pointer(x, y, down=False)
        driver.release_pointer()

    def drag(start, end):
        driver.drag(UiDriver.center(start), end, steps=12)
        driver.wait_idle(frames=2, timeout=2)

    def to_pixels(node, tree):
        """A node's bounds in window pixels; the tree is in zoomed units,
        offset by the camera."""
        screen = tree[0]
        scale = window_size[0] / screen["width"]
        return ((node["x"] - screen["x"]) * scale, (node["y"] - screen["y"]) * scale,
                node["width"] * scale, node["height"] * scale)

    def tap_pixel(x, y):
        """Press and release at a window pixel where no widget may be."""
        screen = driver.tree()[0]
        scale = screen["width"] / window_size[0]
        point = (screen["x"] + x * scale, screen["y"] + y * scale)
        driver.pointer(*point)
        driver.pointer(*point, down=True)
        driver.pointer(*point, down=False)
        driver.release_pointer()

    def apps_open():
        return bool(driver.find(label="Pinned", visible=True))

    def open_apps(hold=0.0):
        press(pin("Apps"), hold)
        driver.wait(label="Pinned")

    def open_profile(log):
        """Profile, an Apps action, replaces Apps with its own page."""
        before = len(transitions(log))
        driver.press(label="Profile", role="button")
        driver.wait_gone(label="Pinned")
        driver.wait(label="Profile", role="title_bar")
        wait_for(lambda: transitions(log) and transitions(log)[-1] == "10",
                 lambda: f"Apps did not open Profile: {transitions(log)[before:]}")

    # The window's size in pixels, for widgets' bounds in zoomed units.
    window_size = [0, 0]

    @contextlib.contextmanager
    def application(profile, name, width=900, height=720, scale=1.0):
        app_env = env | {"APP_DATA_ROOT": str(profile)}
        log_path = OUTPUT / (name + ".log")
        with log_path.open("w") as log:
            app = subprocess.Popen([str(BINARY)], cwd=ROOT, env=app_env,
                                   stdout=log, stderr=subprocess.STDOUT)
            driver.attach(app, log_path)
            try:
                deadline = time.monotonic() + 20
                window = ""
                while time.monotonic() < deadline:
                    assert app.poll() is None, log_path.read_text()
                    found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                                           env=env, capture_output=True, text=True, timeout=5)
                    if found.returncode == 0 and (profile / "inbe.db").exists():
                        window = found.stdout.splitlines()[0]
                        break
                    time.sleep(.1)
                assert window, "App did not map its own window"
                command("xdotool", "windowsize", window, str(width), str(height))
                command("xdotool", "windowmove", window, "0", "0")
                window_size[:] = [width, height]

                def resized():
                    screen = driver.tree()[0]
                    return (abs(screen["width"] * scale - width) < 1 and
                            abs(screen["height"] * scale - height) < 1)
                wait_for(resized, "App did not lay out its resized window")
                driver.wait_idle(frames=3)
                yield window, log_path
                assert app.poll() is None, log_path.read_text()
                assert "frame rejected" not in log_path.read_text(), log_path.read_text()
                assert "portable subset" not in log_path.read_text(), log_path.read_text()
            finally:
                stop(app)

    if arguments.dock_only:
        with tempfile.TemporaryDirectory(prefix="inbe-dock-") as temporary:
            profile = Path(temporary)
            user = None
            with application(profile, "dock-initialize"):
                with database(profile) as db:
                    user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
            routes = [12, 1, 2, 3, 11]
            seed(profile, {"language": "en", "language_system": 0, "language_setup_done": 1,
                           "apps_setup_done": 1, "enabled_apps": 31, "lumi_introduced": 1,
                           "main_tab": 3, "tutorial_seen": 1, "habits_guide_seen": 1, "lumi_guides_seen": 127,
                           "theme": 9, "theme_source": 0, "theme_mode": 2,
                           "package_updates_allowed": 0, "apps_last_update_check": 1900000000})
            cases = [(390, 844, 0, 10, count) for count in (3, 4, 5)]
            cases += [(320, 844, 0, 10, 5), (390, 844, 4, 10, 5),
                      (390, 844, 0, 15, 5), (900, 500, 1, 10, 5),
                      (900, 500, 3, 10, 5)]
            # With three pins, Diary (main_tab 3) opens unpinned under its
            # return bar; the bar must not move the sidebar's pins or Apps.
            cases += [(900, 500, 1, 10, 3), (900, 500, 3, 10, 3)]
            screens = {12: 23, 1: 11, 2: 0, 3: 16, 11: 22}
            for width, height, placement, zoom, count in cases:
                name = f"dock-{width}-{height}-{placement}-{zoom}-{count}"
                seed(profile, {"navigation_placement": placement, "ui_scale": zoom,
                               "main_tab": 3, "launcher_favorite_count": count} |
                     {f"launcher_favorite_{i}": route for i, route in enumerate(routes[:count])})
                with application(profile, name, width, height, zoom / 10) as (window, log):
                    scale = zoom / 10
                    vertical = placement in (1, 3)
                    tree = driver.tree()
                    items = navigation(tree)
                    expected = [ROUTE_LABELS[route] for route in routes[:count]] + ["Apps"]
                    assert [item["label"] for item in items] == expected, \
                        f"{name}: the navigation shows {[item['label'] for item in items]}"
                    # Every pin and Apps fits whole in the window, side by side.
                    placed = [to_pixels(item, tree) for item in items]
                    for item, (x, y, w, h) in zip(items, placed):
                        assert item["visible_width"] >= item["width"] - 1 and \
                            item["visible_height"] >= item["height"] - 1, f"{name}: {item['label']} is cut off"
                        assert x >= -1 and y >= -1 and x + w <= width + 1 and y + h <= height + 1, \
                            f"{name}: {item['label']} lies outside the window at {(x, y, w, h)}"
                    for first, second in zip(placed, placed[1:]):
                        if vertical:
                            assert first[1] + first[3] <= second[1] + 0.5, f"{name}: pins overlap"
                        else:
                            assert first[0] + first[2] <= second[0] + 0.5, f"{name}: pins overlap"
                    if not vertical:
                        image = capture(window, name)
                        bar = [node for node in tree if node["kind"] == "navigation_bar"][0]
                        _, bar_y, _, bar_height = to_pixels(bar, tree)
                        edge = round(bar_y + bar_height) if placement == 4 else height
                        strip = image.crop((round(12 * scale), edge - max(1, round(5 * scale)),
                                            width - round(12 * scale), edge))
                        if 11 in routes[:count]:
                            active_x, _, active_width, _ = placed[routes[:count].index(11)]
                            center = active_x + active_width / 2 - round(12 * scale)
                            radius = active_width / 2 + round(4 * scale)
                            ImageDraw.Draw(strip).rectangle(
                                (round(center - radius), 0, round(center + radius), strip.height),
                                fill=strip.getpixel((0, 0)))
                        assert all(low == high for low, high in strip.getextrema()), \
                            f"{name}: dock still draws an underline or scrollbar"
                    for route, item in zip(routes[:count], items):
                        before = len(transitions(log))
                        press(item)
                        wait_transition(log, before, screens[route],
                                        f"{name}: pin {route} is not reachable")
                        # Opening another app, with or without Diary's
                        # return bar, never moves the pins or Apps.
                        tree = driver.tree()
                        moved = [to_pixels(node, tree) for node in navigation(tree)]
                        assert moved == placed, f"{name}: the navigation moved: {placed} -> {moved}"
                    open_apps()
                    open_profile(log)
                    assert favorites(profile) == routes[:count], "Dock clicks changed pins"
                if vertical and count == 3:
                    # The pins above were reached under Diary's return bar;
                    # its Back arrow opening Apps proves the bar was shown.
                    seed(profile, {"main_tab": 3})
                    with application(profile, name + "-back", width, height) as (window, log):
                        driver.press(label="Back to Apps", role="button")
                        driver.wait(label="Pinned")
                        open_profile(log)
            print("Fitted dock: 3–5 pins, narrow windows, zoom, top/bottom and both rails passed")
        raise SystemExit(0)

    if arguments.properties_only:
        with tempfile.TemporaryDirectory(prefix="inbe-properties-") as temporary:
            profile = Path(temporary)
            user = None
            with application(profile, "properties-initialize"):
                with database(profile) as db:
                    user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
            seed(profile, {"language": "en", "language_system": 0, "language_setup_done": 1,
                           "apps_setup_done": 1, "enabled_apps": 31, "lumi_introduced": 1,
                           "main_tab": 1, "tutorial_seen": 1, "habits_guide_seen": 1, "lumi_guides_seen": 127,
                           "theme": 9, "theme_source": 0, "theme_mode": 2, "package_updates_allowed": 0,
                           "apps_last_update_check": 1900000000, "launcher_favorite_count": 2,
                           "launcher_favorite_0": 1, "launcher_favorite_1": 2})

            def labels():
                return [item["label"] for item in navigation()]

            def open_properties(label):
                pinned, more, tree = cards()
                card = next(card for card in pinned + more if card["label"] == label)
                press(corner(card, tree))
                driver.press(label="Properties", role="selectable")
                driver.wait(label="Name", role="text_field")

            with application(profile, "properties") as (window, log):
                open_apps()
                # Without an update offer the options carry no dot, and the
                # old separate update symbol is gone.
                assert not driver.find(label="Update available"), "The separate update symbol is back"
                assert labels() == ["Habits", "Practice", "Apps"], labels()
                open_properties("Habits")
                driver.press(label="Name", role="text_field")
                driver.key("a", control=True)
                driver.type("Rituals")
                # The app's own icon comes first, labelled with its own name.
                driver.wait(label="Habits", role="button")
                driver.press(label="leaf", role="button")
                driver.press(label="Save", role="button")
                wait_setting(profile, "app_title_habits", "Rituals", "Save did not keep the new name")
                wait_setting(profile, "app_icon_habits", "leaf", "Save did not keep the chosen icon")
                driver.wait_gone(label="Save", role="button")
                # The new name is the app's name on its card and in navigation.
                wait_for(lambda: labels() == ["Rituals", "Practice", "Apps"], lambda: f"Navigation shows {labels()}")
                pinned, more, tree = cards()
                assert pinned[0]["label"] == "Rituals", pinned
                assert favorites(profile) == [1, 2], "Properties changed the pins"
                # Cancel leaves the name and icon as they are.
                open_properties("Rituals")
                driver.press(label="Cancel", role="button")
                driver.wait_gone(label="Save", role="button")
                assert settings(profile)["app_title_habits"] == "Rituals"
                assert settings(profile)["app_icon_habits"] == "leaf"
            with application(profile, "properties-restart") as (window, log):
                assert labels() == ["Rituals", "Practice", "Apps"], f"Restart lost the name: {labels()}"
                open_apps()
                # An empty name and the app's own icon restore both.
                open_properties("Rituals")
                driver.press(label="Name", role="text_field")
                driver.key("a", control=True)
                driver.key("backspace")
                driver.press(label="Habits", role="button")
                driver.press(label="Save", role="button")
                wait_setting(profile, "app_title_habits", "", "Saving an empty name kept the old one")
                wait_setting(profile, "app_icon_habits", "", "Choosing the app's own icon kept the old one")
                wait_for(lambda: labels() == ["Habits", "Practice", "Apps"], lambda: f"Navigation shows {labels()}")
                open_profile(log)
        print("Launcher properties: rename, icon, cancel, restart and restore passed")
        raise SystemExit(0)

    layouts = ((900, 720), (390, 844))
    if arguments.layout == "desktop":
        layouts = layouts[:1]
    elif arguments.layout == "mobile":
        layouts = layouts[1:]
    for width, height in layouts:
        mobile = width < 500
        name = "mobile" if mobile else "desktop"
        with tempfile.TemporaryDirectory(prefix="inbe-launcher-") as temporary:
            profile = Path(temporary)
            user = None
            with application(profile, name + "-language", width, height) as (window, log):
                driver.wait(label="Choose Language")
                with database(profile) as db:
                    user = db.execute("SELECT id FROM users WHERE kind='local' LIMIT 1").fetchone()[0]
                assert settings(profile)["language_setup_done"] == "0", "Fresh start skipped the language picker"
                assert settings(profile)["apps_setup_done"] == "0"
                assert favorites(profile) == [12, 1, 2], "New profiles do not pin Lumi, Habits and Practice"
                assert settings(profile)["enabled_apps"] == "22", "New profiles do not install Lumi, Habits and Practice"
                assert settings(profile)["theme"] == "9" and settings(profile)["theme_source"] == "0"
                assert settings(profile)["theme_mode"] == "2"
            # Merely opening and closing the picker does not complete setup.
            with application(profile, name + "-language-restart", width, height) as (window, log):
                assert settings(profile)["language_setup_done"] == "0"
                driver.press(label="Next", role="button")
                driver.wait(label="Optional audio")
                driver.press(label="Skip for now", role="button")
                wait_setting(profile, "language_setup_done", 1, log.read_text())
                driver.wait(label="Pinned")
                assert settings(profile).get("launcher_guide_seen", "0") == "0"
                for step in range(1, 4):
                    driver.wait(label=f"Step {step} of 3")
                    key(window, "Right", lambda: not driver.find(label=f"Step {step} of 3", visible=True))
                wait_setting(profile, "launcher_guide_seen", 1, "Apps guide did not finish")
                # Opening Apps never asks about automatic updates; available
                # updates appear on each app's card instead.
                driver.wait_idle(frames=3)
                assert not driver.find(label="Don't allow", visible=True), "Apps asked about automatic updates"
                assert "package_updates_allowed" not in settings(profile)
                # Practice is the third pinned card in the same grid as the rest.
                pinned, more, tree = cards()
                assert [card["label"] for card in pinned] == ["Lumi", "Habits", "Practice"], pinned
                assert [round(card["x"]) for card in pinned] == [round(card["x"]) for card in more[:len(pinned)]], \
                    "Pinned and More apps cards use different columns"
                press(pinned[2])
                wait_setting(profile, "apps_setup_done", 1, log.read_text())
                wait_setting(profile, "main_tab", 1, log.read_text())
            seed(profile, {"language": "en", "language_system": 0, "language_setup_done": 1,
                           "apps_setup_done": 1, "enabled_apps": 31, "lumi_introduced": 1,
                           "main_tab": 1, "tutorial_seen": 1, "habits_guide_seen": 1, "lumi_guides_seen": 127,
                           "ui_scale": 10, "navigation_placement": 0, "theme": 9,
                           "theme_source": 0, "theme_mode": 2, "package_updates_allowed": 0,
                           "apps_last_update_check": 1900000000,
                           "launcher_favorite_count": 2, "launcher_favorite_0": 1,
                           "launcher_favorite_1": 2})
            with application(profile, name, width, height) as (window, log):
                driver.wait(label="Start Practice")
                if not mobile:
                    # Desktop keeps Apps in the sidebar's bottom corner.
                    tree = driver.tree()
                    apps_x, apps_y, apps_width, apps_height = to_pixels(pin("Apps"), tree)
                    assert apps_x < 88 and apps_y + apps_height > height - 100, "Apps left the sidebar's bottom corner"
                    driver.wait_idle(frames=3)
                    page = capture(window, name + "-practice")
                    assert page.getpixel((3, height - 80)) == page.getpixel((width - 3, height - 80)), "Navigation and page use different default palettes"
                    before = len(transitions(log))
                    # The bottom corner opens Apps; Profile is no longer
                    # hard-pinned there and is an Apps action instead.
                    open_apps()
                    assert len(transitions(log)) == before, "Profile remains hard-pinned at the bottom"
                    open_profile(log)
                    driver.press(label="Back", role="button")
                    driver.wait(label="Pinned")
                    assert settings(profile)["main_tab"] == "1", "Profile Back changed the selected app"
                    open_profile(log)
                else:
                    tree = driver.tree()
                    apps_x, apps_y, apps_width, apps_height = to_pixels(pin("Apps"), tree)
                    assert apps_y + apps_height > height - 60 and apps_x > width / 2, "Apps left the dock's end"
                open_apps(hold=.35)
                # The title's corner no longer closes Apps.
                tap_pixel(width - 42, 44)
                driver.wait_idle(frames=3)
                assert apps_open(), "The Apps title corner still dismisses the page"
                open_profile(log)
                open_apps()
                assert favorites(profile) == [1, 2], "Opening Apps changed pinned cards"
                if not mobile:
                    # The grid fills the page, beyond the old drawer.
                    pinned, more, tree = cards()
                    grid = by_index(tree)[pinned[0]["parent"]]
                    content = tree[0]["width"] - [node for node in tree if node["kind"] == "navigation_bar"][0]["width"]
                    assert grid["width"] >= content - 40, "Apps did not fill the desktop content area"
                    assert pinned[1]["label"] == "Practice"
                    press(pinned[1])
                    driver.wait_gone(label="Pinned")
                    assert settings(profile)["main_tab"] == "1", "Apps did not fill the desktop content area"
                    open_apps()
                    key(window, "Escape", lambda: not apps_open())
                    assert settings(profile)["main_tab"] == "1", "Closing Apps changed the current page"
                    open_apps()
                # Holding is an ordinary click. It opens the app and never pins it.
                pinned, more, tree = cards()
                assert more[0]["label"] == "Diary", more
                press(more[0], hold=.85)
                wait_setting(profile, "main_tab", 3, log.read_text())
                assert favorites(profile) == [1, 2], "Holding an app changed its pin"
                open_apps()
                pinned, more, tree = cards()
                drag(more[0], UiDriver.center(pinned[0]))
                wait_for(lambda: favorites(profile) == [11, 1, 2], "Dragging into Pinned did not place Diary first")
                pinned, more, tree = cards()
                assert [card["label"] for card in pinned] == ["Diary", "Habits", "Practice"], pinned
                # Pinned has one extra row; drop Diary on the first of More.
                drag(pinned[0], UiDriver.center(more[0]))
                wait_for(lambda: favorites(profile) == [1, 2], "Dragging into More did not remove the shortcut")
                pinned, more, tree = cards()
                assert more[0]["label"] == "Diary", more
                drag(more[0], UiDriver.center(navigation(tree)[0]))
                wait_for(lambda: favorites(profile) == [11, 1, 2], "Dragging a card to navigation did not place it")
                assert [item["label"] for item in navigation()] == ["Diary", "Habits", "Practice", "Apps"]
                # Profile stays in Apps after favorite changes.
                assert apps_open(), "Dragging closed Apps"
                open_profile(log)
                assert "frame rejected" not in log.read_text()
            with application(profile, name + "-restart", width, height) as (window, log):
                assert favorites(profile) == [11, 1, 2], "Restart changed personal pins"
                assert settings(profile)["language_setup_done"] == "1"
                assert [item["label"] for item in navigation()] == ["Diary", "Habits", "Practice", "Apps"]
            with application(profile, name + "-manage", width, height) as (window, log):
                open_apps()
                with database(profile) as db:
                    habit_count = db.execute("SELECT COUNT(*) FROM habits").fetchone()[0]
                selected_tab = settings(profile)["main_tab"]
                # Habits is the second pinned card. Uninstall in its options
                # menu removes the installation and shortcut, retaining data.
                pinned, more, tree = cards()
                assert pinned[1]["label"] == "Habits", pinned
                action = corner(pinned[1], tree)
                assert action["label"] == "App options"
                press(action)
                driver.press(label="Uninstall", role="selectable")
                wait_setting(profile, "app_used_habits", 0, "Trash did not uninstall Habits")
                assert favorites(profile) == [11, 2], "Uninstall left a pinned shortcut"
                with database(profile) as db:
                    assert db.execute("SELECT COUNT(*) FROM habits").fetchone()[0] == habit_count
                # The same app is now first in More; Install is in the same
                # options menu in its card's corner.
                pinned, more, tree = cards()
                assert more[0]["label"] == "Habits", more
                action = corner(more[0], tree)
                assert action["label"] == "App options"
                press(action)
                driver.press(label="Install", role="selectable")
                wait_setting(profile, "app_used_habits", 1, "Install did not restore Habits")
                assert favorites(profile) == [11, 2], "Installing unexpectedly changed pins"
                assert settings(profile)["main_tab"] == selected_tab, "Install opened another app"
            if not mobile:
                # Overflow must leave Apps reachable on either side.
                all_favorites = [12, 1, 2, 3, 11]
                for placement, side in ((1, "left"), (3, "right")):
                    seed(profile, {"navigation_placement": placement,
                                   "launcher_favorite_count": len(all_favorites)} |
                         {f"launcher_favorite_{i}": route for i, route in enumerate(all_favorites)})
                    with application(profile, name + "-short-" + side, width, 500) as (window, log):
                        tree = driver.tree()
                        apps = pin("Apps")
                        x, y, w, h = to_pixels(apps, tree)
                        assert (x < 88) == (side == "left") and y + h <= 500, "Overflow hid Apps"
                        open_apps()
                        open_profile(log)
                        assert favorites(profile) == all_favorites
                seed(profile, {"navigation_placement": 1, "launcher_favorite_count": 0})
                with application(profile, name + "-empty", width, height) as (window, log):
                    assert [item["label"] for item in navigation()] == ["Apps"], "Empty favorites hid Apps"
                    open_apps()
                    open_profile(log)
                    assert favorites(profile) == []
    print("Launcher: first-run language, desktop defaults, clean sections, click/hold/drag, profile and persistence passed")
