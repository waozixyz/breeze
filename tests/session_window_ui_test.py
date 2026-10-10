"""A practice's minimize button keeps it running in a small window over the page
it was started from, on an owned private display."""
import ast
import contextlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/session-window-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
DISPLAY_KEYS = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS")
assert all(not os.environ.get(key) for key in DISPLAY_KEYS), "Inherited desktop environment"
BINARY = Path(sys.argv[1]).resolve()
DESKTOP_ONLY = "--desktop-only" in sys.argv[2:]
SCREEN_START, SCREEN_SESSION, SCREEN_HABITS, SCREEN_LUMI = 0, 1, 11, 23
PRACTICES = {"whm": 1, "meditation": 2, "sun_salutation": 3, "patterns": 4}
# The window starts 220 by 320 units at the top right of the 390-unit phone
# page, 8 units in and 72 down. Its picture sits below a 40-unit button row
# with an 8-unit margin and 46 units of text below; maximize and close are
# centered 60 and 24 units from its right edge, 20 down, and its resize
# corner 16 units in from the bottom right.
WINDOW = (162, 72, 220, 320)
MINIMIZE = (308, 38)


def window_parts(left, top, width, height):
    return dict(picture=(left + 8, top + 40, width - 16, height - 94),
                maximize=(left + width - 60, top + 20), close=(left + width - 24, top + 20),
                grip=(left + width - 16, top + height - 16), card=(left + 12, top + 12))


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


with tempfile.TemporaryDirectory(prefix="inbe-session-window-") as directory, contextlib.ExitStack() as stack:
    profile = Path(directory)
    env = {key: value for key, value in os.environ.items() if key not in DISPLAY_KEYS}
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
        with (OUTPUT / (label + ".log")).open("w") as log:
            app = subprocess.Popen([str(BINARY), "--bundle", str(ROOT / "build/inbe-full.zib")],
                                   cwd=ROOT, env=env, stdout=log, stderr=log)
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
                time.sleep(.8)
                yield window
                assert app.poll() is None, "App crashed"
            finally:
                stop(app)

    def capture(window, label):
        path = OUTPUT / (label + ".png")
        command("import", "-window", window, str(path))
        return path

    def words(window, label):
        """Words on screen with their boxes in window coordinates."""
        path = capture(window, label)
        large = OUTPUT / "ocr.png"
        command("convert", str(path), "-resize", "200%", str(large))
        rows = command("tesseract", str(large), "stdout", "-l", "eng", "--psm", "11",
                       "-c", "tessedit_create_tsv=1").splitlines()
        found = []
        for row in rows[1:]:
            cells = row.split("\t")
            if len(cells) == 12 and cells[11].strip():
                left, top, width, height = (int(value) / 2 for value in cells[6:10])
                found.append((cells[11].strip(), left, top, width, height))
        (OUTPUT / (label + ".txt")).write_text("\n".join(f"{w} {l:.0f},{t:.0f}" for w, l, t, *_ in found))
        return found

    def line_middle(window, label, text):
        """The center of the text line holding the word, from its first word to its last."""
        found = words(window, label)
        anchor = next((item for item in found if text.lower() in item[0].lower()), None)
        if not anchor:
            return None
        row = [item for item in found if abs(item[2] - anchor[2]) < 6]
        left = min(item[1] for item in row)
        right = max(item[1] + item[3] for item in row)
        return (left + right) / 2, anchor[2] + anchor[4] / 2

    def find(window, label, text, region=lambda x, y: True):
        for word, left, top, width, height in words(window, label):
            if text.lower() in word.lower() and region(left, top):
                return left + width / 2, top + height / 2, left, top
        return None

    def state(window):
        prop = command("xprop", "-id", window, "_HARMONY_APP_STATE")
        return json.loads(ast.literal_eval(prop.split(" = ", 1)[1]))

    def action(window, control, request, arguments=None):
        command("xprop", "-id", window, "-f", "_HARMONY_APP_ACTION", "8s", "-set",
                "_HARMONY_APP_ACTION", json.dumps(dict(control=control, request_id=request,
                                                       arguments=arguments or {})))
        deadline = time.monotonic() + 10
        while state(window)["last_request_id"] != request:
            assert time.monotonic() < deadline, "Action was not handled: " + control
            time.sleep(.1)
        assert state(window)["last_request_ok"], control
        time.sleep(.6)

    def wait_screen(window, screen, why):
        deadline = time.monotonic() + 6
        while state(window)["screen"] != screen:
            assert time.monotonic() < deadline, (why, state(window))
            time.sleep(.1)

    def click(window, x, y):
        command("xdotool", "mousemove", "--window", window, str(int(x)), str(int(y)))
        command("xdotool", "mousedown", "1")
        time.sleep(.12)
        command("xdotool", "mouseup", "1")
        time.sleep(.6)

    def swipe(window, start, end):
        # Hold the press for a frame first, so the app sees it where it starts.
        args = ["xdotool", "mousemove", "--window", window, str(int(start[0])), str(int(start[1])),
                "mousedown", "1", "sleep", "0.15"]
        for step in range(1, 9):
            x = start[0] + (end[0] - start[0]) * step / 8
            y = start[1] + (end[1] - start[1]) * step / 8
            args += ["sleep", "0.03", "mousemove", "--window", window, str(int(x)), str(int(y))]
        command(*args, "sleep", "0.05", "mouseup", "1")
        time.sleep(.8)

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

    def wait_running(window, why):
        assert state(window)["practice_running"], (why, state(window))

    with application("initialize", 390, 720):
        pass
    with sqlite3.connect(profile / "inbe.db") as db:
        user = db.execute("SELECT id FROM users LIMIT 1").fetchone()[0]
        # Lumi is pinned first: a practice must still minimize to the page it
        # was started from, not to the first pinned app.
        values = dict(enabled_apps="31", main_tab="1", language="en", language_setup_done="1",
                      apps_setup_done="1", launcher_guide_seen="1", lumi_introduced="1", tutorial_seen="1",
                      cells_auto_update="0", habits_guide_seen="1", launcher_favorite_count="3",
                      launcher_favorite_0="12", launcher_favorite_1="1", launcher_favorite_2="2")
        values.update({"app_used_" + name: "1" for name in ("lumi", "habits", "lists", "diary", "practices")})
        for key, value in values.items():
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                       "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user, key, value))

    # Every practice minimizes to Practice, where it was started, and keeps
    # its live picture moving in the window until maximize returns to it.
    parts = window_parts(*WINDOW)
    for practice, screen in ({} if DESKTOP_ONLY else PRACTICES).items():
        with application(practice, 390, 720) as window:
            action(window, "mcp.open_view", "open-" + practice, {"view": "practices"})
            action(window, f"practice.{practice}.start", "start-" + practice)
            wait_screen(window, screen, practice + " did not start")
            click(window, *MINIMIZE)
            wait_screen(window, SCREEN_START, practice + " did not minimize to Practice")
            wait_running(window, practice + " stopped when minimized")
            with Image.open(capture(window, practice + "-card")) as image:
                card = image.convert("RGB").getpixel(parts["card"])
            picture = region(window, practice + "-picture", parts["picture"])
            drawn = differing(picture, card)
            assert drawn > picture.width * picture.height * 0.03, (practice, "shows no picture", drawn)
            # Sun Salutation holds each pose for seconds before moving on.
            first = region(window, practice + "-first", WINDOW)
            deadline = time.monotonic() + 15
            while True:
                time.sleep(1)
                later = region(window, practice + "-later", WINDOW)
                if changed(first, later) > 40:
                    break
                assert time.monotonic() < deadline, practice + " stopped moving in its window"
            assert state(window)["screen"] == SCREEN_START
            wait_running(window, practice + " stopped in its window")
            click(window, *parts["maximize"])
            wait_screen(window, screen, "Maximize did not return to " + practice)
            wait_running(window, practice + " ended when maximized")

    phone_dock = lambda x, y: y > 640
    if not DESKTOP_ONLY:
        with application("phone", 390, 720) as window:
            # Started from Habits, the practice minimizes back to Habits.
            action(window, "mcp.open_view", "open-habits", {"view": "habits"})
            wait_screen(window, SCREEN_HABITS, "Habits did not open")
            action(window, "practice.whm.start", "start-whm")
            wait_screen(window, SCREEN_SESSION, "Breathing did not start")
            assert find(window, "practice", "Lumi", phone_dock) is None, "Navigation shows during a practice"
            click(window, *MINIMIZE)
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
            round_line = find(window, "window", "ROUND")
            assert round_line and WINDOW[1] < round_line[3] < WINDOW[1] + WINDOW[3], \
                ("The window does not show the round below its circle", round_line)

            # Maximize returns to the practice.
            click(window, *parts["maximize"])
            wait_screen(window, SCREEN_SESSION, "Maximize did not return to the practice")

            # Practice opens its home while the practice keeps running in the
            # window, and Start returns to that practice instead of a new one.
            click(window, *MINIMIZE)
            wait_screen(window, SCREEN_HABITS, "Minimize did not return to Habits again")
            action(window, "mcp.open_view", "open-practice", {"view": "practices"})
            wait_screen(window, SCREEN_START, "Practice did not open its home while minimized")
            wait_running(window, "Opening Practice ended the minimized practice")
            assert find(window, "practice-home-window", "ROUND"), "The window is missing on Practice"
            # OCR misses dark text on the light button; it spans the content width.
            start = (find(window, "practice-home", "Start", lambda x, y: y > 400) or
                     find(window, "practice-home-label", "Practice", lambda x, y: 500 < y < 600) or
                     (195, 550))
            click(window, start[0], start[1])
            wait_screen(window, SCREEN_SESSION, "Start did not return to the running practice")
            wait_running(window, "Start ended the running practice")

            # The X asks right over the open app; Cancel keeps the practice.
            click(window, *MINIMIZE)
            wait_screen(window, SCREEN_HABITS, "Minimize did not return to Habits for the X")
            click(window, *parts["close"])
            deadline = time.monotonic() + 4
            while not (find(window, "exit", "Session?") or find(window, "exit", "progress")):
                assert time.monotonic() < deadline, "Ending from the window did not ask first"
                time.sleep(.3)
            assert state(window)["screen"] == SCREEN_HABITS, "The X left the open app to ask"
            wait_running(window, "The practice ended before the answer")
            # Cancel sits left of Exit, below the centered prompt's title.
            cancel = find(window, "exit-cancel", "Cancel") or (147, 400)
            click(window, cancel[0], cancel[1])
            time.sleep(.5)
            assert state(window)["screen"] == SCREEN_HABITS and state(window)["practice_running"], \
                ("Cancel did not keep the practice running over Habits", state(window))

            # The corner handle makes the window taller; its round line moves
            # down with the window's bottom.
            before = find(window, "before-resize", "ROUND")
            swipe(window, parts["grip"], (parts["grip"][0], parts["grip"][1] + 60))
            after = find(window, "after-resize", "ROUND")
            assert before and after and 40 < after[3] - before[3] < 80, ("The window did not resize", before, after)
            assert state(window)["screen"] == SCREEN_HABITS, "Resizing opened the practice"
            height = WINDOW[3] + after[3] - before[3]

            # The window stays while moving between apps.
            lumi = find(window, "dock", "Lumi", phone_dock)
            assert lumi, "The navigation is missing beside the practice window"
            click(window, lumi[0], lumi[1])
            wait_screen(window, SCREEN_LUMI, "Lumi did not open")
            wait_running(window, "Opening Lumi ended the practice")
            assert find(window, "lumi-window", "ROUND"), "The practice window did not stay over Lumi"

            # The window moves with a drag and returns to the practice on a tap.
            picture = window_parts(WINDOW[0], WINDOW[1], WINDOW[2], height)["picture"]
            middle = (picture[0] + picture[2] / 2, picture[1] + picture[3] / 2)
            swipe(window, middle, (middle[0] - 120, middle[1] + 200))
            moved = find(window, "moved", "ROUND")
            assert moved and moved[3] > after[3] + 150, ("The window did not follow the drag", after, moved)
            assert state(window)["screen"] == SCREEN_LUMI, "Dragging the window opened the practice"
            click(window, moved[0], moved[1] - 60)
            wait_screen(window, SCREEN_SESSION, "Tapping the window did not return to the practice")
            wait_running(window, "Tapping the window ended the practice")

            # Exit ends the practice and keeps the open app.
            click(window, *MINIMIZE)
            wait_screen(window, SCREEN_HABITS, "Minimize did not return to Habits at the end")
            # The round line is centered in the window, 21 units above its bottom.
            middle = line_middle(window, "before-exit", "ROUND")
            assert middle, "The window is missing before the X"
            left = middle[0] - WINDOW[2] / 2
            top = middle[1] - (height - 21)
            click(window, *window_parts(left, top, WINDOW[2], height)["close"])
            deadline = time.monotonic() + 4
            while not (find(window, "exit-again", "Session?") or find(window, "exit-again", "progress")):
                assert time.monotonic() < deadline, "The X did not ask a second time"
                time.sleep(.3)
            click(window, 243, 400)
            deadline = time.monotonic() + 4
            while state(window)["practice_running"]:
                assert time.monotonic() < deadline, "Exit did not end the practice"
                time.sleep(.2)
            assert state(window)["screen"] == SCREEN_HABITS, ("Ending left the open app", state(window))
            assert not find(window, "after-exit", "ROUND"), "The window stayed after the practice ended"

    rail = lambda x, y: x < 100
    with application("desktop", 900, 720) as window:
        action(window, "mcp.open_view", "open-habits-desktop", {"view": "habits"})
        action(window, "practice.whm.start", "start-whm-desktop")
        wait_screen(window, SCREEN_SESSION, "Breathing did not start on desktop")
        assert find(window, "desktop-practice", "Lumi", rail) is None, "The sidebar shows during a practice"
        click(window, 818, 38)
        wait_screen(window, SCREEN_HABITS, "Minimize did not return to Habits on desktop")
        assert find(window, "desktop-minimized", "Lumi", rail), "The sidebar did not return"
        assert find(window, "desktop-window", "ROUND"), "The practice window is not shown on desktop"
        wait_running(window, "Minimizing ended the practice on desktop")

        # Detach into an actual process-owned window. Its resize and input
        # must never reach the main application's page.
        assert find(window, "desktop-card", "ROUND"), "The desktop practice card is missing"
        # The card's right edge stays eight units inside the 900-unit viewport.
        click(window, 900 - 8 - 96, 72 + 20)
        deadline = time.monotonic() + 8
        detached = None
        while detached is None:
            candidates = command("xdotool", "search", "--onlyvisible", "--name", "Inner Breeze").splitlines()
            for candidate in candidates:
                if candidate != window:
                    main_pid = command("xprop", "-id", window, "_NET_WM_PID").split(" = ")[-1]
                    other_pid = command("xprop", "-id", candidate, "_NET_WM_PID").split(" = ")[-1]
                    if main_pid == other_pid:
                        detached = candidate
                        break
            assert time.monotonic() < deadline, "Detach did not create an owned desktop window"
            time.sleep(.1)
        assert find(detached, "detached-live", "Breathing"), "Detached window has no live practice"
        wait_running(window, "Detaching ended the practice")
        first = region(detached, "detached-picture-first", (8, 40, 244, 226))
        time.sleep(.5)
        second = region(detached, "detached-picture-second", (8, 40, 244, 226))
        assert changed(first, second) > 100, "Detached breathing picture stopped animating"
        command("xdotool", "windowsize", detached, "340", "400")
        time.sleep(.5)
        geometry = command("xdotool", "getwindowgeometry", "--shell", window)
        assert "WIDTH=900" in geometry and "HEIGHT=720" in geometry, geometry
        wait_screen(window, SCREEN_HABITS, "Detached resize changed the main page")
        assert find(detached, "detached-resized", "Breathing"), "Resizing lost the live picture"

        # The detached window remains active when the main window is hidden,
        # including profiles without a tray icon.
        command("xdotool", "windowunmap", window)
        time.sleep(.4)
        wait_running(window, "Hiding the main window ended the detached practice")

        # The attach control returns only the small card to the open page.
        click(detached, 340 - 96, 20)
        time.sleep(.5)
        wait_screen(window, SCREEN_HABITS, "Attaching changed the open page")
        wait_running(window, "Attaching ended the practice")
        assert find(window, "desktop-attached", "ROUND"), "Attaching did not restore the card"

        # A second detach followed by a picture tap restores the full practice.
        click(window, 900 - 8 - 96, 72 + 20)
        time.sleep(.5)
        candidates = command("xdotool", "search", "--onlyvisible", "--name", "Inner Breeze").splitlines()
        detached = next(candidate for candidate in candidates if candidate != window)
        click(detached, 130, 140)
        wait_screen(window, SCREEN_SESSION, "Detached picture tap did not restore the practice")
        wait_running(window, "Restoring from the detached window ended the practice")

if DESKTOP_ONLY:
    print("Desktop practice window: detach, animate, resize, hide main window, attach and restore passed")
else:
    print("Session window: all practice pictures, card controls and detached desktop windows passed")
