"""The top-up modal shows one exchange quote on an isolated desktop."""
import contextlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from ui_driver import UiDriver


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build/dew-topup-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
BINARY = Path(sys.argv[1]).resolve()
DESKTOP_ENV = ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS",
               "SESSION_MANAGER", "GDK_DISPLAY")
assert all(not os.environ.get(key) for key in DESKTOP_ENV), "Inherited desktop environment"


def stop(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


with contextlib.ExitStack() as stack:
    profile = Path(stack.enter_context(tempfile.TemporaryDirectory(dir=OUTPUT, prefix="profile-")))
    driver = UiDriver(profile / "driver")
    environment = {key: value for key, value in os.environ.items() if key not in DESKTOP_ENV}
    environment.update(driver.environment())
    environment.update(APP_DATA_ROOT=str(profile), INBE_SCREENSHOT_DATA_ROOT=str(profile),
                       APP_NO_TRAY="1", APP_SHOT_WINDOW="1", YUE_DESKTOP_RECOVERY="0",
                       SDL_VIDEODRIVER="x11", SDL_AUDIODRIVER="dummy", LIBGL_ALWAYS_SOFTWARE="1",
                       https_proxy="http://127.0.0.1:9", http_proxy="http://127.0.0.1:9", NO_PROXY="")
    display_log = stack.enter_context((OUTPUT / "display.log").open("w"))
    display = subprocess.Popen(["Xvfb", "-noreset", "-displayfd", "1", "-screen", "0", "600x1000x24",
                                "-nolisten", "tcp"], env=environment,
                               stdout=subprocess.PIPE, stderr=display_log)
    stack.callback(stop, display)
    number = display.stdout.readline().decode().strip()
    display.stdout.close()
    assert number.isdecimal(), "Private display did not start"
    environment["DISPLAY"] = ":" + number
    log_path = OUTPUT / "app.log"
    log = stack.enter_context(log_path.open("w"))
    process = subprocess.Popen([str(BINARY), "--screenshot", str(OUTPUT / "topup.png"),
                                "--screenshot-scene", "dew_top_up", "--screenshot-width", "480",
                                "--screenshot-height", "900"], cwd=ROOT, env=environment,
                               stdout=log, stderr=subprocess.STDOUT)
    stack.callback(stop, process)
    driver.attach(process, log_path)
    driver.wait(contains="1000 Dew", role="text", visible=False)
    nodes = driver.tree()
    (OUTPUT / "tree.json").write_text(json.dumps(nodes, indent=2) + "\n")
    quotes = [node["label"] for node in nodes if " XMR = " in node.get("label", "")]
    assert quotes == ["0.1 XMR = 1000 Dew, about 55.66 USD"], quotes
    assert driver.find(label="Balance · 120 Dew · 0.012 XMR, about 6.68 USD", role="text")
    assert driver.find(label="Copy", role="button", visible=False)
    assert driver.find(label="Wallet", role="button", visible=False)
    assert "frame rejected" not in log_path.read_text()
    assert process.poll() is None, "Top-up test app exited unexpectedly"

print("Dew top-up: one quote, consistent balance conversion, and deposit controls passed")
