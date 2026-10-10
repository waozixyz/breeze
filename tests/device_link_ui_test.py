"""Connect devices by QR code on owned windows of a private Xvfb display.

Three profiles run against a local mailbox (tests/device_link_mailbox.py): A
holds an account. A shows its code to a new device C, both show the same six
digits, and A sends the account. Then a new device B shows its code, A scans
it and sends the account. Codes are read back from screenshots with zbar,
so they are checked as scannable images. Desktops have no camera; a scanned
code reaches a window through INBE_TEST_DEVICE_LINK_SCAN."""

import contextlib
import csv
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
import device_link_mailbox  # noqa: E402

BINARY = sys.argv[1]
DETECT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT.parent / "photos/build/detect-qr/detect_qr"
OUTPUT = ROOT / "build/device-link-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
assert int(os.environ["DISPLAY"].split(":")[-1].split(".")[0]) >= 300


def command(*args):
    return subprocess.run(args, text=True, capture_output=True, check=True, timeout=20).stdout.strip()


def wait_for(predicate, description, seconds=15):
    deadline = time.monotonic() + seconds
    while True:
        value = predicate()
        if value:
            return value
        assert time.monotonic() < deadline, description
        time.sleep(0.2)


def tap(window, x, y):
    command("xdotool", "windowfocus", window)
    command("xdotool", "mousemove", "--window", window, str(x), str(y))
    time.sleep(0.15)
    command("xdotool", "mousedown", "1")
    time.sleep(0.18)
    command("xdotool", "mouseup", "1")
    time.sleep(0.4)


def capture(window, label):
    raw = OUTPUT / f"{label}.xwd"
    command("xwd", "-silent", "-id", window, "-out", str(raw))
    command("convert", str(raw), str(OUTPUT / f"{label}.png"))
    raw.unlink()
    return OUTPUT / f"{label}.png"


def scan(window, label):
    """The code the window shows, read from a screenshot."""
    def read():
        found = json.loads(command(str(DETECT), str(capture(window, label))) or "{}")
        codes = [code["text"] for code in found.get("qr_codes", []) if code.get("text", "").startswith("inbe-link:1:")]
        return codes[0] if codes else ""
    return wait_for(read, f"No connection code on {label}")


def tap_label(window, label, word, region):
    """Taps a rendered word inside region (left, top, right, bottom), so the
    test follows layout changes such as where the rail places Apps."""
    path = capture(window, label)
    left, top, right, bottom = region
    command("convert", str(path), "-crop", f"{right - left}x{bottom - top}+{left}+{top}",
            "+repage", "-colorspace", "Gray", "-normalize", "-resize", "300%", str(path))
    text = command("tesseract", str(path), "stdout", "--psm", "11", "-c", "tessedit_create_tsv=1")
    found = [row for row in csv.DictReader(io.StringIO(text), delimiter="\t")
             if row.get("text", "").strip().lower() == word]
    assert len(found) == 1, f"{word} is missing or ambiguous on {label}"
    row = found[0]
    tap(window, left + (int(row["left"]) + int(row["width"]) // 2) // 3,
        top + (int(row["top"]) + int(row["height"]) // 2) // 3)


def digits(window, label):
    path = capture(window, label)
    text = command("tesseract", str(path), "stdout", "--psm", "11")
    # OCR may drop the gap between the two groups of three.
    found = re.findall(r"\b(\d{3}) ?(\d{3})\b", text)
    return found[0][0] + found[0][1] if found else ""


def setting(profile, key):
    with sqlite3.connect(profile / "inbe.db", timeout=5) as database:
        row = database.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else ""


def prepare(profile, server):
    """Creates a fresh profile and points it at the local mailbox."""
    first = subprocess.Popen([BINARY, "--bundle", str(ROOT / "build/cells/lumi.zib")], cwd=ROOT,
                             env=os.environ | {"APP_DATA_ROOT": str(profile)},
                             stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    wait_for(lambda: (profile / "inbe.db").exists(), "Profile was not created")
    time.sleep(2)
    first.terminate()
    first.wait(timeout=10)
    with sqlite3.connect(profile / "inbe.db", timeout=5) as database:
        user = database.execute("SELECT id FROM users LIMIT 1").fetchone()[0]
        for key, value in dict(sync_enabled=0, sync_server_url=server, language="en",
                               language_setup_done=1, apps_setup_done=1, enabled_apps=31,
                               tutorial_seen=1, launcher_guide_seen=1, practice_guide_seen=1,
                               habits_guide_seen=1, lumi_introduced=1, cells_auto_update=0).items():
            database.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                             "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value",
                             (user, key, str(value)))


@contextlib.contextmanager
def application(profile, label, left, scan_file):
    with (OUTPUT / f"{label}.log").open("w") as log:
        app = subprocess.Popen([BINARY, "--bundle", str(ROOT / "build/inbe-full.zib")], cwd=ROOT,
                               env=os.environ | {"APP_DATA_ROOT": str(profile),
                                                 "INBE_TEST_DEVICE_LINK_SCAN": str(scan_file)},
                               stdout=log, stderr=subprocess.STDOUT)
        try:
            def find():
                assert app.poll() is None, f"{label} exited"
                found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                                       text=True, capture_output=True, timeout=5)
                return found.stdout.split()[0] if found.returncode == 0 and found.stdout.strip() else ""
            window = wait_for(find, f"{label} window did not appear")
            command("xdotool", "windowsize", window, "900", "720")
            command("xdotool", "windowmove", window, str(left), "0")
            time.sleep(1.5)
            # Apps, Profile, then the account view.
            tap_label(window, f"{label}-rail", "apps", (0, 0, 88, 720))
            tap(window, 297, 683)
            tap(window, 541, 195)
            time.sleep(0.6)
            yield window
            assert app.poll() is None, f"{label} crashed"
        except BaseException:
            if app.poll() is None and "window" in locals():
                capture(window, f"failure-{label}")
            raise
        finally:
            app.terminate()
            try:
                app.wait(timeout=5)
            except subprocess.TimeoutExpired:
                app.kill()


server, mailbox = device_link_mailbox.start()
address = f"http://127.0.0.1:{server.server_address[1]}"
with tempfile.TemporaryDirectory(prefix="inbe-device-link-") as directory:
    root = Path(directory)
    profiles = {name: root / name for name in ("a", "b", "c")}
    scans = {name: root / f"{name}.scan" for name in profiles}
    for profile in profiles.values():
        prepare(profile, address)
    with application(profiles["a"], "a", 0, scans["a"]) as a:
        tap(a, 494, 87)
        account = wait_for(lambda: setting(profiles["a"], "sync_public_id"), "A did not create an account")
        time.sleep(1)
        capture(a, "a-account")
        # A holds the account: it shows a code, and the new device C scans it.
        tap(a, 494, 355)
        code = scan(a, "a-code")
        assert code.endswith(":s:" + address), code
        with application(profiles["c"], "c", 960, scans["c"]) as c:
            scans["c"].write_text(code)
            wait_for(lambda: not scans["c"].exists(), "C did not read the scanned code")
            shown = wait_for(lambda: digits(c, "c-digits"), "C did not show digits")
            confirm = wait_for(lambda: digits(a, "a-digits"), "A did not show digits")
            assert shown == confirm, (shown, confirm)
            capture(a, "a-confirm")
            capture(c, "c-waiting")
            tap(a, 381, 414)
            wait_for(lambda: setting(profiles["c"], "sync_public_id") == account,
                     "C did not receive A's account")
            time.sleep(1)
            capture(c, "c-connected")
            capture(a, "a-connected")
        assert ("/api/v1/link/close", "") in mailbox.requests, "The link was not closed"
        # A new device B shows its code; A scans it and sends the account.
        with application(profiles["b"], "b", 960, scans["b"]) as b:
            tap(b, 494, 278)
            code = scan(b, "b-code")
            assert code.endswith(":r:" + address), code
            # B keeps polling through a node restart.
            mailbox.outage = 3
            scans["a"].write_text(code)
            wait_for(lambda: not scans["a"].exists(), "A did not read the scanned code")
            time.sleep(1)
            capture(a, "a-ask")
            tap(a, 380, 355)
            wait_for(lambda: setting(profiles["b"], "sync_public_id") == account,
                     "B did not receive A's account")
            assert mailbox.outage == 0, "B stopped polling during the outage"
            time.sleep(1)
            capture(b, "b-connected")
    # Private keys never pass through the mailbox in the clear.
    private = setting(profiles["a"], "sync_private_key")
    assert private and len(mailbox.messages) == 3, len(mailbox.messages)
    assert all(private[64:128] not in message for message in mailbox.messages)
server.shutdown()
(OUTPUT / "result.json").write_text(json.dumps({"passed": True, "checked": [
    "showing device with account", "scanned code read from the screen", "matching six digits",
    "account sent after confirming", "link closed", "showing device without account",
    "scanner confirms and sends", "polling survives a node restart",
    "receiving devices hold the same account"]}, indent=2) + "\n")
print("Device link UI: both directions connected by QR code")
