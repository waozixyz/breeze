"""Exercise WHM rendering with a synthetic profile and an owned private display."""
import ast
import contextlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/whm-animation-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
DISPLAY_KEYS = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS")
assert all(not os.environ.get(key) for key in DISPLAY_KEYS)
BINARY = Path(sys.argv[1]).resolve()


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


with tempfile.TemporaryDirectory(prefix="inbe-whm-frames-") as temporary, contextlib.ExitStack() as stack:
    env = {key: value for key, value in os.environ.items() if key not in DISPLAY_KEYS}
    env.update(APP_DATA_ROOT=temporary, APP_NO_TRAY="1", APP_PROFILE="1",
               SDL_AUDIODRIVER="dummy", SDL_VIDEODRIVER="x11", LIBGL_ALWAYS_SOFTWARE="1",
               YUE_DESKTOP_RECOVERY="0", INBE_DEBUG_ROUTE="1")
    log_path = OUTPUT / "frames.log"
    log = stack.enter_context(log_path.open("w"))
    display = subprocess.Popen(["Xvfb", "-displayfd", "1", "-screen", "0", "1080x1000x24",
                                "-nolisten", "tcp"], env=env, stdout=subprocess.PIPE, stderr=log)
    stack.callback(stop, display)
    number = display.stdout.readline().decode().strip()
    display.stdout.close()
    assert number.isdecimal(), "Private display did not start"
    env["DISPLAY"] = ":" + number
    app = subprocess.Popen([str(BINARY), "--bundle", str(ROOT / "build/inbe-full.zib")],
                           cwd=ROOT, env=env, stdout=log, stderr=log)
    stack.callback(stop, app)

    def command(*arguments):
        return subprocess.check_output(arguments, env=env, text=True, timeout=5).strip()

    def wait(read, predicate, label):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            assert app.poll() is None, log_path.read_text()[-2000:]
            try:
                value = read()
                if predicate(value):
                    return value
            except (subprocess.CalledProcessError, ValueError, SyntaxError, IndexError):
                pass
            time.sleep(0.05)
        raise AssertionError(label)

    window = wait(lambda: command("xdotool", "search", "--onlyvisible", "--pid", str(app.pid))
                  .splitlines()[0], bool, "Owned app window")
    command("xdotool", "windowsize", window, "390", "844")
    command("xdotool", "windowfocus", window)

    def state():
        prop = command("xprop", "-id", window, "_HARMONY_APP_STATE")
        return json.loads(ast.literal_eval(prop.split(" = ", 1)[1]))

    wait(state, lambda value: value.get("interface") == "harmony.app-state.v1", "App state")
    command("xprop", "-id", window, "-f", "_HARMONY_APP_ACTION", "8s", "-set",
            "_HARMONY_APP_ACTION", json.dumps({"control": "practice.whm.start", "request_id": "whm-frames"}))
    started = wait(state, lambda value: value.get("last_request_id") == "whm-frames" and
                   value.get("last_request_ok") and value.get("practice_running"), "WHM start")
    initial_reports = len(re.findall(r"PROFILE: frame", log_path.read_text()))
    deadline = time.monotonic() + 14
    while time.monotonic() < deadline:
        assert app.poll() is None, "Owned test app exited"
        time.sleep(0.1)
    progressed = state()
    assert progressed["practice_running"] and not progressed["paused"]
    assert (progressed["round"], progressed["breath"]) > (started["round"], started["breath"])
    reports = re.findall(r"PROFILE: frame avg=([\d.]+) max=([\d.]+).*?sync avg=([\d.]+) "
                         r"max=([\d.]+) fps=([\d.]+)", log_path.read_text())[initial_reports + 1:]
    assert len(reports) >= 4, "Not enough measured animation frames"
    measurements = [{"cpuAverageMs": float(cpu), "cpuMaxMs": float(peak),
                     "syncAverageMs": float(sync), "syncMaxMs": float(sync_peak), "fps": float(fps)}
                    for cpu, peak, sync, sync_peak, fps in reports]
    assert min(row["fps"] for row in measurements) >= 55, measurements
    assert max(row["cpuAverageMs"] for row in measurements) < 8, measurements
    result = {"passed": True, "privateDisplay": True, "syntheticProfile": True,
              "screenshots": False, "practiceContinued": True, "measurements": measurements}
    (OUTPUT / "frames.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
