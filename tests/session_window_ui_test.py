"""A practice's minimize button keeps it running in a small window while another
app is open, on an owned private display."""
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

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/session-window-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
DISPLAY_KEYS = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS")
assert all(not os.environ.get(key) for key in DISPLAY_KEYS), "Inherited desktop environment"
BINARY = Path(sys.argv[1]).resolve()
SCREEN_SESSION, SCREEN_HABITS, SCREEN_LUMI = 1, 11, 23


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

    def find(window, label, text, region=lambda x, y: True):
        for word, left, top, width, height in words(window, label):
            if text.lower() in word.lower() and region(left, top):
                return left + width / 2, top + height / 2, left, top
        return None

    def state(window):
        prop = command("xprop", "-id", window, "_HARMONY_APP_STATE")
        return json.loads(ast.literal_eval(prop.split(" = ", 1)[1]))

    def action(window, control, request):
        command("xprop", "-id", window, "-f", "_HARMONY_APP_ACTION", "8s", "-set",
                "_HARMONY_APP_ACTION", json.dumps(dict(control=control, request_id=request, arguments={})))
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

    with application("initialize", 390, 720):
        pass
    with sqlite3.connect(profile / "inbe.db") as db:
        user = db.execute("SELECT id FROM users LIMIT 1").fetchone()[0]
        values = dict(enabled_apps="31", main_tab="1", language="en", language_setup_done="1",
                      apps_setup_done="1", launcher_guide_seen="1", lumi_introduced="1", tutorial_seen="1",
                      cells_auto_update="0", habits_guide_seen="1", launcher_favorite_count="3",
                      launcher_favorite_0="1", launcher_favorite_1="2", launcher_favorite_2="12")
        values.update({"app_used_" + name: "1" for name in ("lumi", "habits", "lists", "diary", "practices")})
        for key, value in values.items():
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                       "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user, key, value))

    phone_dock = lambda x, y: y > 640
    with application("phone", 390, 720) as window:
        action(window, "practice.whm.start", "start-whm")
        wait_screen(window, SCREEN_SESSION, "Breathing did not start")
        assert find(window, "practice", "Lumi", phone_dock) is None, "Navigation shows during a practice"

        # Minimize, beside the close button, opens the first pinned app with
        # the practice still running in its small window.
        click(window, 308, 38)
        wait_screen(window, SCREEN_HABITS, "Minimize did not open the first pinned app")
        first = state(window)
        assert first["practice_running"] and first["practice"] == 0, first
        deadline = time.monotonic() + 20
        later = state(window)
        while (later["round"], later["breath"]) <= (first["round"], first["breath"]):
            assert later["practice_running"] and later["screen"] == SCREEN_HABITS, later
            assert time.monotonic() < deadline, ("Breathing stopped behind Habits", first["breath"], later["breath"])
            time.sleep(.5)
            later = state(window)
        card = find(window, "window", "Hof")
        assert card, "The practice window is not shown over Habits"
        assert card[1] < 200, ("The window does not start at the top", card)
        assert find(window, "window-round", "ROUND"), "The practice window does not show the round"

        # The window stays while moving between apps.
        lumi = find(window, "dock", "Lumi", phone_dock)
        assert lumi, "The navigation is missing beside the practice window"
        click(window, lumi[0], lumi[1])
        wait_screen(window, SCREEN_LUMI, "Lumi did not open")
        assert state(window)["practice_running"]
        card = find(window, "lumi-window", "Hof")
        assert card, "The practice window did not stay over Lumi"

        # The window moves with a drag and returns to the practice on a tap.
        swipe(window, (card[0], card[1] + 12), (card[0] - 120, card[1] + 300))
        moved = find(window, "moved", "Hof")
        assert moved and moved[1] > card[1] + 200, ("The window did not follow the drag", card, moved)
        assert state(window)["screen"] == SCREEN_LUMI, "Dragging the window opened the practice"
        click(window, moved[0], moved[1] + 12)
        wait_screen(window, SCREEN_SESSION, "Tapping the window did not return to the practice")
        assert state(window)["practice_running"]

        # The X asks before ending the practice, from its own screen.
        click(window, 308, 38)
        wait_screen(window, SCREEN_HABITS, "Minimize did not work a second time")
        card = find(window, "habits-window", "Wim")
        assert card, "The practice window is not shown after minimizing again"
        name_left, name_top = card[2], card[3]
        click(window, name_left - 14 + 212 - 24, name_top - 10 + 24)
        wait_screen(window, SCREEN_SESSION, "The X did not return to the practice to end it")
        deadline = time.monotonic() + 4
        while not (find(window, "exit", "Cancel") or find(window, "exit", "Session?")):
            assert time.monotonic() < deadline, "Ending from the window did not ask first"
            time.sleep(.3)
        assert state(window)["practice_running"], "The practice ended before the answer"

    rail = lambda x, y: x < 100
    with application("desktop", 900, 720) as window:
        action(window, "practice.whm.start", "start-whm-desktop")
        wait_screen(window, SCREEN_SESSION, "Breathing did not start on desktop")
        assert find(window, "desktop-practice", "Lumi", rail) is None, "The sidebar shows during a practice"
        click(window, 818, 38)
        wait_screen(window, SCREEN_HABITS, "Minimize did not open the first pinned app on desktop")
        assert find(window, "desktop-minimized", "Lumi", rail), "The sidebar did not return"
        assert find(window, "desktop-window", "Hof"), "The practice window is not shown on desktop"
        assert state(window)["practice_running"]

print("Session window: minimize keeps a practice running in a draggable window that returns or asks to end")
