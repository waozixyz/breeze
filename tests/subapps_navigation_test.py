"""Exercise bundled feature calls in full app windows on a private display."""

import contextlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "build/subapps-navigation-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
assert int(os.environ["DISPLAY"].split(":")[-1].split(".")[0]) >= 300
ENV = os.environ.copy()
ENV.update(APP_NO_TRAY="1", APP_SHOT_WINDOW="1", YUE_DESKTOP_RECOVERY="0")
ENV.pop("WAYLAND_DISPLAY", None)
ENV.pop("DBUS_SESSION_BUS_ADDRESS", None)


def command(*args):
    return subprocess.run(
        args, env=ENV, check=True, text=True, capture_output=True, timeout=5
    ).stdout.strip()


def capture(window, name):
    raw = OUTPUT / f"{name}.xwd"
    png = OUTPUT / f"{name}.png"
    command("xwd", "-silent", "-id", window, "-out", str(raw))
    command("convert", str(raw), str(png))
    raw.unlink()
    with Image.open(png) as image:
        return image.convert("RGB").copy()


def tap(window, x, y):
    command("xdotool", "mousemove", "--window", window, str(x), str(y))
    command("xdotool", "mousedown", "1")
    time.sleep(0.08)
    command("xdotool", "mouseup", "1")
    time.sleep(0.5)


def usage(pid):
    status = Path(f"/proc/{pid}/status").read_text()
    stat = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
    return {
        "rss_kib": int(re.search(r"VmRSS:\s+(\d+)", status)[1]),
        "cpu_ticks": int(stat[11]) + int(stat[12]),
        "monotonic": time.monotonic(),
    }


@contextlib.contextmanager
def application(scene):
    log_path = OUTPUT / f"{scene}.log"
    with log_path.open("w") as log:
        app = subprocess.Popen(
            [
                sys.argv[1],
                "--bundle",
                str(ROOT / "build/inbe-full.zib"),
                *(["--feature", "lists"] if scene == "lists" else []),
                "--screenshot",
                str(OUTPUT / f"{scene}-initial.png"),
                "--screenshot-scene",
                scene,
                "--screenshot-width",
                "900",
                "--screenshot-height",
                "720",
            ],
            cwd=ROOT,
            env=ENV,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 15
            window = ""
            database = Path(f"/tmp/inbe-screenshot-{app.pid}/inbe.db")
            while time.monotonic() < deadline:
                assert app.poll() is None, log_path.read_text()
                found = subprocess.run(
                    [
                        "xdotool",
                        "search",
                        "--all",
                        "--onlyvisible",
                        "--pid",
                        str(app.pid),
                        "--name",
                        "Inner Breeze",
                    ],
                    env=ENV,
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if found.returncode == 0 and found.stdout.strip() and database.exists():
                    window = found.stdout.splitlines()[0]
                    break
                time.sleep(0.1)
            assert window, "app did not map its own isolated window"
            command("xdotool", "windowfocus", window)
            time.sleep(0.8)
            yield app, window, database
            assert app.poll() is None, log_path.read_text()
            assert "frame rejected" not in log_path.read_text(), log_path.read_text()
        finally:
            if app.poll() is None:
                app.terminate()
                try:
                    app.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    app.kill()
                    app.wait(timeout=3)


result = {
    "display": os.environ["DISPLAY"],
    "data": "screenshot-only disposable profiles",
}
with application("lists") as (app, window, database):
    capacity = int(
        re.search(
            r"ELIST_ITEM_MAX :: (\d+)",
            (ROOT / "src/screens/elist_types.zi").read_text(),
        )[1]
    )
    with sqlite3.connect(database, timeout=5) as db:
        list_id, user_id = db.execute(
            "SELECT id,user_id FROM elist_lists WHERE title='Shopping'"
        ).fetchone()
        count = db.execute("SELECT COUNT(*) FROM elist_items").fetchone()[0]
        # Fill the existing supported capacity; a real UI edit reloads these
        # fixture rows through the host and executes the Lists bundle.
        for index in range(capacity - count - 1):
            db.execute(
                "INSERT INTO elist_items(id,user_id,list_id,title,comment,done,sort_order,deleted_at,updated_at) VALUES(?,?,?,?,?,0,?,0,1)",
                (
                    f"fixture-{index:028d}",
                    user_id,
                    list_id,
                    f"Populated task {index + 1}",
                    "Shared Lists fixture",
                    index + 2,
                ),
            )
    tap(window, 300, 90)
    command("xdotool", "type", "--clearmodifiers", "Bundle UI edit")
    started = time.monotonic()
    command("xdotool", "keydown", "Return")
    time.sleep(0.15)
    command("xdotool", "keyup", "Return")
    deadline = time.monotonic() + 10
    while True:
        with sqlite3.connect(database, timeout=5) as db:
            saved = db.execute(
                "SELECT COUNT(*) FROM elist_items WHERE title='Bundle UI edit' AND list_id=? AND user_id=?",
                (list_id, user_id),
            ).fetchone()[0]
        if saved:
            break
        assert time.monotonic() < deadline, "populated Lists UI edit did not save"
        time.sleep(0.1)
    result["populated_lists"] = {
        "items": capacity,
        "edit_seconds": time.monotonic() - started,
        "usage_samples": [usage(app.pid)],
    }
    capture(window, "lists-populated")
    for cycle in range(3):
        tap(window, 600, 34)  # Weekend list tab
        capture(window, f"lists-empty-tab-{cycle}")
        tap(window, 300, 34)  # Shopping list tab
        command("xdotool", "mousemove", "--window", window, "600", "420")
        command("xdotool", "click", "--repeat", "8", "--delay", "40", "5")
        time.sleep(0.5)
        capture(window, f"lists-scroll-{cycle}")
        result["populated_lists"]["usage_samples"].append(usage(app.pid))
    before = capture(window, "lists-final")
    for name, y in (
        ("habits", 145),
        ("practice", 209),
        ("settings", 670),
        ("lists", 273),
    ):
        tap(window, 110, y)
        after = capture(window, f"navigation-{name}")
        assert (
            sum(
                abs(a - b)
                for a, b in zip(before.getpixel((20, y)), after.getpixel((20, y)))
            )
            > 30
        ), name
        before = after
    result["navigation"] = ["lists", "habits", "practice", "settings", "lists"]

with application("patterns") as (app, window, database):
    command("xdotool", "mousemove", "--window", window, "20", "20")
    first = capture(window, "practice-running")
    # Focus the private server's root, never a real user window.
    command("xdotool", "windowfocus", "--sync", command("xdotool", "getwindowfocus"))
    command("xdotool", "windowfocus", "--sync", "0")
    time.sleep(2.2)
    unfocused = capture(window, "practice-unfocused")
    # Status text contains elapsed seconds; isolate it from circle animation.
    status = (210, 42, 900, 110)
    assert ImageChops.difference(
        first.crop(status), unfocused.crop(status)
    ).getbbox(), "practice stopped ticking without focus"
    command("xdotool", "windowfocus", "--sync", window)
    command("xdotool", "keydown", "space")
    time.sleep(0.15)
    command("xdotool", "keyup", "space")
    time.sleep(0.5)
    paused = capture(window, "practice-paused")
    time.sleep(2.2)
    still_paused = capture(window, "practice-still-paused")
    assert not ImageChops.difference(
        paused.crop(status), still_paused.crop(status)
    ).getbbox(), "explicit pause kept ticking"
    result["practice"] = {
        "desktop_focus_loss_ticks": True,
        "explicit_pause_stops": True,
        "usage": usage(app.pid),
    }

(OUTPUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
print("Populated Lists edits/scroll/navigation and desktop practice focus/pause passed")
