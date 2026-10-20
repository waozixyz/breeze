"""A practice's minimize button keeps it running in a small window over the page
it was started from, on an owned private display."""
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

from PIL import Image
from Xlib import X, display as xdisplay, protocol

from ui_driver import UiDriver

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/session-window-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
DISPLAY_KEYS = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS")
assert all(not os.environ.get(key) for key in DISPLAY_KEYS), "Inherited desktop environment"
BINARY = Path(sys.argv[1]).resolve()
DESKTOP_ONLY = "--desktop-only" in sys.argv[2:]
SCREEN_START, SCREEN_SESSION, SCREEN_HABITS, SCREEN_LUMI = 0, 1, 11, 23
SCREEN_SETTINGS, SCREEN_LISTS, SCREEN_DIARY = 6, 16, 22
PRACTICES = {"whm": 1, "meditation": 2, "sun_salutation": 3, "patterns": 4}
# The window starts 220 by 320 units at the top right of the 390-unit phone
# page, 8 units in and 72 down. Its picture sits below a 40-unit button row
# with an 8-unit margin and 46 units of text below.
WINDOW = (162, 72, 220, 320)


def window_parts(left, top, width, height):
    return dict(picture=(left + 8, top + 40, width - 16, height - 94), card=(left + 12, top + 12))


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def inside(outer, point):
    x, y = point
    return (outer["x"] <= x <= outer["x"] + outer["width"] and
            outer["y"] <= y <= outer["y"] + outer["height"])


with tempfile.TemporaryDirectory(prefix="inbe-session-window-") as directory, contextlib.ExitStack() as stack:
    profile = Path(directory)
    driver = UiDriver(OUTPUT / "driver")
    env = {key: value for key, value in os.environ.items() if key not in DISPLAY_KEYS}
    env.update(driver.environment())
    env.update(APP_DATA_ROOT=str(profile), HOME=directory, XDG_CONFIG_HOME=directory,
               APP_NO_TRAY="1", SDL_AUDIODRIVER="dummy", SDL_VIDEODRIVER="x11",
               LIBGL_ALWAYS_SOFTWARE="1", YUE_DESKTOP_RECOVERY="0")
    display_log = stack.enter_context((OUTPUT / "display.log").open("w"))
    display = subprocess.Popen(["Xvfb", "-displayfd", "1", "-screen", "0", "1280x900x24",
                                "-nolisten", "tcp"], env=env, stdout=subprocess.PIPE, stderr=display_log)
    stack.callback(stop, display)
    number = display.stdout.readline().decode().strip()
    assert number.isdecimal()
    display.stdout.close()
    env["DISPLAY"] = ":" + number

    def command(*args):
        return subprocess.run(args, env=env, check=True, capture_output=True,
                              text=True, timeout=20).stdout.strip()

    @contextlib.contextmanager
    def application(label, width, height):
        log_path = OUTPUT / (label + ".log")
        with log_path.open("w") as log:
            app = subprocess.Popen([str(BINARY), "--bundle", str(ROOT / "build/inbe-full.zib")],
                                   cwd=ROOT, env=env, stdout=log, stderr=log)
            driver.attach(app, log_path)
            try:
                deadline = time.monotonic() + 20
                while True:
                    assert app.poll() is None, "Owned test app exited"
                    result = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                                            env=env, capture_output=True, text=True, timeout=3)
                    if result.returncode == 0 and (profile / "inbe.db").exists():
                        window = result.stdout.splitlines()[0]
                        break
                    assert time.monotonic() < deadline, "Owned app window did not appear"
                    time.sleep(.1)
                command("xdotool", "windowsize", window, str(width), str(height))
                driver.wait_idle(frames=3)
                yield window
                assert app.poll() is None, "App crashed"
            finally:
                stop(app)

    def capture(window, label):
        path = OUTPUT / (label + ".png")
        command("import", "-window", window, str(path))
        return path

    def state(window):
        # A loaded machine can show the window a few frames before the app
        # publishes its first state.
        deadline = time.monotonic() + 10
        while True:
            prop = command("xprop", "-id", window, "_HARMONY_APP_STATE")
            if " = " in prop:
                return json.loads(ast.literal_eval(prop.split(" = ", 1)[1]))
            assert time.monotonic() < deadline, "The app did not publish its state"
            time.sleep(.2)

    def action(window, control, request, arguments=None):
        command("xprop", "-id", window, "-f", "_HARMONY_APP_ACTION", "8s", "-set",
                "_HARMONY_APP_ACTION", json.dumps(dict(control=control, request_id=request,
                                                       arguments=arguments or {})))
        deadline = time.monotonic() + 10
        while state(window)["last_request_id"] != request:
            assert time.monotonic() < deadline, "Action was not handled: " + control
            time.sleep(.1)
        assert state(window)["last_request_ok"], control
        driver.wait_idle(frames=2, timeout=2)

    def wait_screen(window, screen, why):
        deadline = time.monotonic() + 6
        while state(window)["screen"] != screen:
            assert time.monotonic() < deadline, (why, state(window))
            time.sleep(.1)

    def wait_running(window, why):
        assert state(window)["practice_running"], (why, state(window))

    def shown(**selector):
        return driver.find(visible=True, **selector)

    def navigation(label):
        """The navigation's button for an app, when it shows."""
        nodes = driver.tree()
        bars = {node["index"] for node in nodes if node["kind"] == "navigation_bar"}
        return next((node for node in nodes if node["label"] == label and node["visible"]
                     and node["parent"] in bars), None)

    def screen_origin(nodes):
        return next(node for node in nodes if node["kind"] == "screen")

    def practice_window():
        """The practice window's card and the widgets around it, or None."""
        nodes = driver.tree()
        maximize = [node for node in nodes if node["label"] == "Maximize" and node["visible"]]
        if not maximize:
            return None
        assert len(maximize) == 1, maximize
        centre = UiDriver.center(maximize[0])
        # The card is submitted right before its buttons, after the page
        # under it.
        cards = [node for node in nodes if node["kind"] == "button" and node["visible"]
                 and node["index"] < maximize[0]["index"] and inside(node, centre)]
        assert cards, "The practice window has no card"
        card = max(cards, key=lambda node: node["index"])
        return dict(card=card, nodes=nodes)

    def in_window(label, kind=None):
        """A widget of the practice window: its round line, buttons or Breath.

        The window draws its picture and lines before its card and its
        buttons after it, above the page under it."""
        window_card = practice_window()
        if window_card is None:
            return None
        card = window_card["card"]
        for node in window_card["nodes"]:
            if not node["visible"] or not node["label"].startswith(label):
                continue
            if kind is not None and node["kind"] != kind:
                continue
            if not inside(card, UiDriver.center(node)):
                continue
            if node["kind"] == "button" and node["index"] <= card["index"]:
                continue
            return node
        return None

    def press_window(label):
        node = in_window(label, kind="button")
        assert node, f"The practice window has no {label} button: {driver.text()}"
        driver.press(key=node["key"])

    def round_line(why, timeout=5):
        """The round line in the practice window, once the page shows it."""
        deadline = time.monotonic() + timeout
        while True:
            node = in_window("ROUND", kind="text")
            if node:
                return node
            assert time.monotonic() < deadline, f"{why}: {driver.text()}"
            time.sleep(.05)

    def window_box(window_card):
        """The practice window's card in window pixels."""
        card = window_card["card"]
        origin = screen_origin(window_card["nodes"])
        return (round(card["x"] - origin["x"]), round(card["y"] - origin["y"]),
                round(card["width"]), round(card["height"]))

    def region(window, label, box):
        left, top, width, height = box
        with Image.open(capture(window, label)) as image:
            return image.convert("RGB").crop((left, top, left + width, top + height))

    def differing(image, color):
        data = image.tobytes()
        return sum(1 for index in range(0, len(data), 3)
                   if max(abs(data[index + channel] - color[channel]) for channel in range(3)) > 24)

    def changed(first, second):
        one, two = first.tobytes(), second.tobytes()
        return sum(1 for index in range(0, len(one), 3)
                   if max(abs(one[index + channel] - two[index + channel]) for channel in range(3)) > 24)

    def tap(x, y):
        driver.pointer(x, y)
        driver.pointer(x, y, down=True)
        driver.pointer(x, y, down=False)

    def double_tap(x, y):
        # One frame each, so both presses land well within the double tap's
        # 0.35 seconds.
        driver.pointer(x, y)
        driver.pointer(x, y, down=True)
        driver.pointer(x, y, down=False)
        driver.pointer(x, y, down=True)
        driver.pointer(x, y, down=False)

    def save_settings(values):
        with sqlite3.connect(profile / "inbe.db") as db:
            user = db.execute("SELECT id FROM users LIMIT 1").fetchone()[0]
            for key, value in values.items():
                db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                           "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user, key, value))

    # Meditation and Breathing Patterns come with the app; Sun Salutation is
    # a download. Its narration and Lumi's guide download by themselves in
    # the app's language; their copies are already here, so the test reaches
    # no server.
    packages = profile / "packages"
    packages.mkdir(exist_ok=True)
    for name in ("sunsalutation", "sunsalutation.en", "guide.en"):
        shutil.copyfile(ROOT / "build/practice-content" / (name + ".zib"), packages / f"practice-{name}.zib")

    with application("initialize", 390, 720):
        pass
    # Lumi is pinned first: a practice must still minimize to the page it
    # was started from, not to the first pinned app.
    values = dict(enabled_apps="31", main_tab="1", language="en", language_setup_done="1",
                  apps_setup_done="1", launcher_guide_seen="1", lumi_introduced="1", tutorial_seen="1",
                  package_updates_allowed="0", habits_guide_seen="1", lumi_guides_seen="127", launcher_favorite_count="3",
                  launcher_favorite_0="12", launcher_favorite_1="1", launcher_favorite_2="2",
                  picture_in_picture="0")
    values.update({"app_used_" + name: "1" for name in ("lumi", "habits", "lists", "diary", "practices")})
    save_settings(values)

    # Every practice minimizes to Practice, where it was started, and keeps
    # its live picture moving in the window until maximize returns to it.
    for practice, screen in ({} if DESKTOP_ONLY else PRACTICES).items():
        with application(practice, 390, 720) as window:
            action(window, "mcp.open_view", "open-" + practice, {"view": "practices"})
            action(window, f"practice.{practice}.start", "start-" + practice)
            wait_screen(window, screen, practice + " did not start")
            driver.press(label="Minimize")
            wait_screen(window, SCREEN_START, practice + " did not minimize to Practice")
            wait_running(window, practice + " stopped when minimized")
            driver.wait(label="Maximize")
            box = window_box(practice_window())
            assert box == WINDOW, (practice, "window is not at the top right of the page", box)
            parts = window_parts(*box)
            first = region(window, practice + "-first", box)
            background = first.getpixel((parts["card"][0] - box[0], parts["card"][1] - box[1]))
            picture = first.crop((8, 40, 8 + parts["picture"][2], 40 + parts["picture"][3]))
            drawn = differing(picture, background)
            assert drawn > picture.width * picture.height * 0.03, (practice, "shows no picture", drawn)
            # Sun Salutation holds each pose for seconds before moving on.
            deadline = time.monotonic() + 15
            while True:
                time.sleep(1)
                later = region(window, practice + "-later", box)
                if changed(first, later) > 40:
                    break
                assert time.monotonic() < deadline, practice + " stopped moving in its window"
            # A breathing circle must not bake a font at a new size each frame.
            log = OUTPUT / (practice + ".log")
            baked = log.read_text().count("FONT: Data loaded")
            time.sleep(4)
            assert log.read_text().count("FONT: Data loaded") == baked, \
                (practice, "bakes new font sizes while its window animates")
            assert state(window)["screen"] == SCREEN_START
            wait_running(window, practice + " stopped in its window")
            press_window("Maximize")
            wait_screen(window, screen, "Maximize did not return to " + practice)
            wait_running(window, practice + " ended when maximized")

    if not DESKTOP_ONLY:
        with application("phone", 390, 720) as window:
            # Started from Habits, the practice minimizes back to Habits.
            action(window, "mcp.open_view", "open-habits", {"view": "habits"})
            wait_screen(window, SCREEN_HABITS, "Habits did not open")
            action(window, "practice.whm.start", "start-whm")
            wait_screen(window, SCREEN_SESSION, "Breathing did not start")
            driver.wait(label="Minimize")
            assert navigation("Lumi") is None, "Navigation shows during a practice"
            driver.press(label="Minimize")
            wait_screen(window, SCREEN_HABITS, "Minimize did not return to Habits")
            first = state(window)
            wait_running(window, "Minimizing ended the practice")
            deadline = time.monotonic() + 20
            later = state(window)
            while (later["round"], later["breath"]) <= (first["round"], first["breath"]):
                assert later["practice_running"] and later["screen"] == SCREEN_HABITS, later
                assert time.monotonic() < deadline, ("Breathing stopped behind Habits", first["breath"], later["breath"])
                time.sleep(.5)
                later = state(window)
            line = round_line("The window does not show the round below its circle")
            picture = window_parts(*WINDOW)["picture"]
            assert picture[1] + picture[3] < line["y"] < WINDOW[1] + WINDOW[3], \
                ("The window does not show the round below its circle", line)

            # Maximize returns to the practice.
            press_window("Maximize")
            wait_screen(window, SCREEN_SESSION, "Maximize did not return to the practice")

            # Practice opens its home while the practice keeps running in the
            # window, and Start returns to that practice instead of a new one.
            driver.press(label="Minimize")
            wait_screen(window, SCREEN_HABITS, "Minimize did not return to Habits again")
            action(window, "mcp.open_view", "open-practice", {"view": "practices"})
            wait_screen(window, SCREEN_START, "Practice did not open its home while minimized")
            wait_running(window, "Opening Practice ended the minimized practice")
            round_line("The window is missing on Practice")
            driver.press(label="Start Practice", role="button")
            wait_screen(window, SCREEN_SESSION, "Start did not return to the running practice")
            wait_running(window, "Start ended the running practice")

            # The X asks right over the open app; Cancel keeps the practice.
            driver.press(label="Minimize")
            wait_screen(window, SCREEN_HABITS, "Minimize did not return to Habits for the X")
            press_window("Close")
            driver.wait(contains="progress", timeout=4)
            assert state(window)["screen"] == SCREEN_HABITS, "The X left the open app to ask"
            wait_running(window, "The practice ended before the answer")
            cancel = driver.wait(label="Cancel", role="button")
            exit_button = driver.wait(label="Exit", role="button")
            assert cancel["x"] < exit_button["x"], "Cancel is not left of Exit"
            driver.press(label="Cancel", role="button")
            driver.wait_gone(contains="progress")
            assert state(window)["screen"] == SCREEN_HABITS and state(window)["practice_running"], \
                ("Cancel did not keep the practice running over Habits", state(window))

            # The corner handle makes the window taller; its round line moves
            # down with the window's bottom.
            before = round_line("The window is missing before the resize")
            grip = in_window("Resize", kind="button")
            assert grip, "The window has no corner handle"
            x, y = UiDriver.center(grip)
            driver.drag((x, y), (x, y + 60))
            driver.wait_idle(frames=2)
            after = round_line("The window is missing after the resize")
            assert 40 < after["y"] - before["y"] < 80, ("The window did not resize", before, after)
            assert state(window)["screen"] == SCREEN_HABITS, "Resizing opened the practice"
            height = WINDOW[3] + after["y"] - before["y"]

            # The window stays while moving between apps.
            lumi = navigation("Lumi")
            assert lumi, "The navigation is missing beside the practice window"
            driver.press(key=lumi["key"])
            wait_screen(window, SCREEN_LUMI, "Lumi did not open")
            wait_running(window, "Opening Lumi ended the practice")
            round_line("The practice window did not stay over Lumi")

            # It stays over every other page too, including the Apps screen
            # that covers the page.
            for view, screen in (("lists", SCREEN_LISTS), ("diary", SCREEN_DIARY),
                                 ("settings", SCREEN_SETTINGS)):
                action(window, "mcp.open_view", "open-" + view + "-window", {"view": view})
                wait_screen(window, screen, view + " did not open")
                wait_running(window, "Opening " + view + " ended the practice")
                round_line("The practice window did not stay over " + view)
            apps = navigation("Apps")
            assert apps, "The Apps button is missing beside the practice window"
            driver.press(key=apps["key"])
            driver.wait(label="Find an app", role="text_field")
            wait_running(window, "Opening Apps ended the practice")
            round_line("The practice window did not stay over Apps")
            # Its buttons work there too: maximize leaves Apps for the practice.
            press_window("Maximize")
            wait_screen(window, SCREEN_SESSION, "Maximize over Apps did not return to the practice")
            wait_running(window, "Maximize over Apps ended the practice")
            driver.wait_gone(label="Find an app")
            driver.press(label="Minimize")
            driver.wait(label="Maximize")
            wait_running(window, "Minimizing after Apps ended the practice")
            action(window, "mcp.open_view", "open-lumi-again", {"view": "lumi"})
            wait_screen(window, SCREEN_LUMI, "Lumi did not open after Apps")

            # The window moves with a drag and returns to the practice on a tap.
            card = practice_window()["card"]
            assert abs(card["height"] - height) < 1, ("The window lost its height", card, height)
            picture = window_parts(card["x"], card["y"], card["width"], card["height"])["picture"]
            middle = (picture[0] + picture[2] / 2, picture[1] + picture[3] / 2)
            driver.drag(middle, (middle[0] - 120, middle[1] + 200))
            driver.wait_idle(frames=2)
            moved = round_line("The window is missing after the drag")
            assert moved["y"] > after["y"] + 150, ("The window did not follow the drag", after, moved)
            assert state(window)["screen"] == SCREEN_LUMI, "Dragging the window opened the practice"
            x, y = UiDriver.center(moved)
            tap(x, y - 60)
            wait_screen(window, SCREEN_SESSION, "Tapping the window did not return to the practice")
            wait_running(window, "Tapping the window ended the practice")

            # Exit ends the practice and keeps the open app.
            driver.press(label="Minimize")
            wait_screen(window, SCREEN_HABITS, "Minimize did not return to Habits at the end")
            round_line("The window is missing before the X")
            press_window("Close")
            driver.wait(contains="progress", timeout=4)
            driver.press(label="Exit", role="button")
            deadline = time.monotonic() + 4
            while state(window)["practice_running"]:
                assert time.monotonic() < deadline, "Exit did not end the practice"
                time.sleep(.2)
            assert state(window)["screen"] == SCREEN_HABITS, ("Ending left the open app", state(window))
            driver.wait_gone(label="Maximize")
            assert not in_window("ROUND") and not shown(contains="ROUND"), \
                "The window stayed after the practice ended"

    # A held breath ends right from the window, the way the practice is set
    # to end it: with its Breath button, or with a double tap. A single tap
    # set to double tap stays on the open page.
    for double_tap_mode in (() if DESKTOP_ONLY else (False, True)):
        mode = "double-tap" if double_tap_mode else "button"
        save_settings(dict(advanced_session_controls="1",
                           double_tap_to_breathe="1" if double_tap_mode else "0"))

        def holding():
            """The practice's screen shows the held breath's Breath button or double tap hint."""
            if double_tap_mode:
                return bool(shown(contains="Double tap"))
            return bool(shown(label="BREATH", role="button"))

        with application("breathe-" + mode, 390, 720) as window:
            action(window, "mcp.open_view", "open-habits-" + mode, {"view": "habits"})
            wait_screen(window, SCREEN_HABITS, "Habits did not open to breathe from the window")
            action(window, "practice.whm.start", "start-whm-" + mode)
            wait_screen(window, SCREEN_SESSION, "Breathing did not start to breathe from the window")
            # Next skips the countdown and the breaths to the held breath.
            for step in range(4):
                driver.wait_idle(frames=2)
                if holding():
                    break
                driver.press(label="Next")
            else:
                assert False, "Next did not reach the held breath"
            driver.press(label="Minimize")
            wait_screen(window, SCREEN_HABITS, "Minimize did not return to Habits during the held breath")
            wait_running(window, "Minimizing ended the held breath")
            driver.wait(label="Maximize")
            offered = in_window("BREATH", kind="button")
            card = practice_window()["card"]
            parts = window_parts(card["x"], card["y"], card["width"], card["height"])
            middle = (parts["picture"][0] + parts["picture"][2] / 2, parts["picture"][1] + 60)
            if double_tap_mode:
                assert not offered, "The window shows Breath while set to double tap"
                tap(*middle)
                # Wait out the double tap's 0.35 seconds before the next tap.
                time.sleep(.6)
                assert state(window)["screen"] == SCREEN_HABITS, "A single tap left the open page"
                double_tap(*middle)
            else:
                assert offered, "The window does not offer Breath during the held breath"
                assert inside(card, UiDriver.center(offered)), "Breath is outside the window"
                driver.press(key=offered["key"])
                driver.wait_gone(label="BREATH")
            driver.wait_idle(frames=2)
            assert state(window)["screen"] == SCREEN_HABITS, "Breathing from the window left the open page"
            wait_running(window, "Breathing from the window ended the practice")
            press_window("Maximize")
            wait_screen(window, SCREEN_SESSION, "Maximize did not return after breathing from the window")
            driver.wait(label="Minimize")
            driver.wait_idle(frames=2)
            assert not holding(), "The practice is still holding the breath after breathing from the window"
    save_settings(dict(advanced_session_controls="0", double_tap_to_breathe="0"))

    # On desktop, minimizing opens the practice in its own window, never the
    # in-app card, unless picture-in-picture is turned off.
    save_settings(dict(picture_in_picture="1"))
    with application("desktop", 900, 720) as window:
        def practice_window_id():
            deadline = time.monotonic() + 8
            while True:
                candidates = command("xdotool", "search", "--onlyvisible", "--name", "Inner Breeze").splitlines()
                main_pid = command("xprop", "-id", window, "_NET_WM_PID").split(" = ")[-1]
                for candidate in candidates:
                    if candidate != window and \
                            command("xprop", "-id", candidate, "_NET_WM_PID").split(" = ")[-1] == main_pid:
                        return candidate
                assert time.monotonic() < deadline, "Minimize did not open an owned desktop window"
                time.sleep(.1)

        def animating(detached, label, why):
            """The practice window's own picture keeps moving."""
            first = region(detached, label + "-first", (8, 40, 244, 226))
            deadline = time.monotonic() + 5
            while True:
                time.sleep(.5)
                second = region(detached, label + "-second", (8, 40, 244, 226))
                if changed(first, second) > 100:
                    return
                assert time.monotonic() < deadline, why

        action(window, "mcp.open_view", "open-habits-desktop", {"view": "habits"})
        action(window, "practice.whm.start", "start-whm-desktop")
        wait_screen(window, SCREEN_SESSION, "Breathing did not start on desktop")
        driver.wait(label="Minimize")
        assert navigation("Lumi") is None, "The sidebar shows during a practice"
        driver.press(label="Minimize")
        wait_screen(window, SCREEN_HABITS, "Minimize did not return to Habits on desktop")
        driver.wait(label="Lumi", role="button")
        lumi = navigation("Lumi")
        assert lumi and UiDriver.center(lumi)[0] - screen_origin(driver.last["nodes"])["x"] < 100, \
            "The sidebar did not return"
        wait_running(window, "Minimizing ended the practice on desktop")
        detached = practice_window_id()
        assert practice_window() is None and not shown(contains="ROUND"), "Desktop still shows the in-app card"

        # Its resize and input must never reach the main application's page.
        # The test driver reads only the main window, so this window's live
        # practice shows in its moving picture.
        animating(detached, "detached-picture", "The practice window stopped animating")
        command("xdotool", "windowsize", detached, "340", "400")
        geometry = command("xdotool", "getwindowgeometry", "--shell", window)
        assert "WIDTH=900" in geometry and "HEIGHT=720" in geometry, geometry
        wait_screen(window, SCREEN_HABITS, "Resizing the practice window changed the main page")
        animating(detached, "detached-resized", "Resizing lost the live picture")

        # The practice window stays active when the main window is hidden,
        # including profiles without a tray icon.
        command("xdotool", "windowunmap", window)
        time.sleep(.4)
        wait_running(window, "Hiding the main window ended the practice")
        command("xdotool", "windowmap", window)
        time.sleep(.4)

        # Closing the window, as a window manager asks it to, brings the
        # practice back to the app.
        connection = xdisplay.Display(env["DISPLAY"])
        target = connection.create_resource_object("window", int(detached))
        target.send_event(protocol.event.ClientMessage(window=target,
            client_type=connection.intern_atom("WM_PROTOCOLS"),
            data=(32, [connection.intern_atom("WM_DELETE_WINDOW"), X.CurrentTime, 0, 0, 0])),
            event_mask=X.NoEventMask)
        connection.close()
        wait_screen(window, SCREEN_SESSION, "Closing the practice window did not return the practice")
        wait_running(window, "Closing the practice window ended the practice")

        # A picture tap in a reopened window also restores the full practice.
        # The driver does not reach that window, so the tap is the X pointer's.
        driver.press(label="Minimize")
        wait_screen(window, SCREEN_HABITS, "Minimize did not return to Habits again")
        detached = practice_window_id()
        command("xdotool", "mousemove", "--window", detached, "130", "140")
        command("xdotool", "mousedown", "1")
        time.sleep(.12)
        command("xdotool", "mouseup", "1")
        wait_screen(window, SCREEN_SESSION, "A picture tap did not restore the practice")
        wait_running(window, "Restoring from the practice window ended the practice")

if DESKTOP_ONLY:
    print("Desktop practice window: open on minimize, animate, resize, hide main window, close and restore passed")
else:
    print("Session window: all practice pictures, card controls and detached desktop windows passed")
