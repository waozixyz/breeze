"""Connect devices by QR code on owned windows of a private Xvfb display.

Three profiles run against a local mailbox (tests/device_link_mailbox.py): A
holds an account. A shows its code to a new device C, both show the same six
digits, and A sends the account. Then a new device B shows its code, A scans
it and sends the account. Codes are read back from screenshots with zbar,
so they are checked as scannable images. Desktops have no camera; a scanned
code reaches a window through INBE_TEST_DEVICE_LINK_SCAN.

Each window answers Kryon's test driver in its own directory: buttons, the
account and the six digits are found in its widget tree, and presses go
through its own pointer path. Profiles are read only while no app runs on
them: an app that has shown Profile no longer holds SQLite's file locks (its
storage size check opens and closes inbe.db), so a reader closing its
connection would take the app's write-ahead log away from it."""

import contextlib
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
from ui_driver import UiDriver  # noqa: E402

BINARY = sys.argv[1]
DETECT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT.parent / "photos/build/detect-qr/detect_qr"
OUTPUT = ROOT / "build/device-link-ui-test"
OUTPUT.mkdir(parents=True, exist_ok=True)
assert int(os.environ["DISPLAY"].split(":")[-1].split(".")[0]) >= 300
# The navigation's buttons share one focus group, here the rail.
NAVIGATION = 6600
# Device link buttons by stage: the code's Cancel while it shows, Connect
# after comparing digits, and Connect when asked to send to a scanned device.
SHOWING_CANCEL = 5280
CONFIRM_CONNECT = 5281
ASK_CONNECT = 5283


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


def capture(window, label):
    raw = OUTPUT / f"{label}.xwd"
    command("xwd", "-silent", "-id", window, "-out", str(raw))
    command("convert", str(raw), str(OUTPUT / f"{label}.png"))
    raw.unlink()
    return OUTPUT / f"{label}.png"


def scan(device, label):
    """The code the window shows, read from a screenshot once it shows."""
    driver, window = device
    driver.wait(key=SHOWING_CANCEL, role="button")
    driver.wait_idle(frames=3)

    def read():
        found = json.loads(command(str(DETECT), str(capture(window, label))) or "{}")
        codes = [code["text"] for code in found.get("qr_codes", []) if code.get("text", "").startswith("inbe-link:1:")]
        return codes[0] if codes else ""
    return wait_for(read, f"No connection code on {label}")


def digits(device):
    """The six digits a window shows to compare, once it shows them."""
    driver, _ = device
    deadline = time.monotonic() + 15
    while True:
        for label in driver.labels():
            found = re.fullmatch(r"\s*(\d{3}) ?(\d{3})\s*", label)
            if found:
                return found.group(1) + found.group(2)
        if time.monotonic() >= deadline:
            raise driver._failure("No six digits to compare")
        time.sleep(0.05)


def shown_account(device):
    """The account a window shows, shortened to its first and last digits."""
    driver, _ = device
    for label in driver.labels():
        if re.fullmatch(r"[0-9a-f]{8}…[0-9a-f]{8}", label):
            return label
    return ""


def connected(device, account):
    """Waits until a window says it is connected and shows the account."""
    driver, _ = device
    driver.wait(label="Device connected.")
    deadline = time.monotonic() + 15
    while shown_account(device) != account:
        if time.monotonic() >= deadline:
            raise driver._failure(f"The window does not show the account {account}")
        time.sleep(0.05)


def setting(profile, key):
    """A saved setting, read while no app has the profile open."""
    with contextlib.closing(sqlite3.connect(profile / "inbe.db", timeout=5)) as database:
        row = database.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else ""


def prepare(profile, server):
    """Creates a fresh profile and points it at the local mailbox."""
    driver = UiDriver(OUTPUT / "driver-first-start")
    first = subprocess.Popen([BINARY, "--bundle", str(ROOT / "build/cells/lumi.zib")], cwd=ROOT,
                             env=os.environ | {"APP_DATA_ROOT": str(profile)} | driver.environment(),
                             stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    driver.attach(first)
    wait_for(lambda: (profile / "inbe.db").exists(), "Profile was not created")
    # The first start has created its schema once it draws settled frames.
    driver.wait_idle(frames=3, timeout=30, required=True)
    first.terminate()
    try:
        first.wait(timeout=10)
    except subprocess.TimeoutExpired:
        first.kill()
        first.wait(timeout=5)
    with contextlib.closing(sqlite3.connect(profile / "inbe.db", timeout=5)) as database, database:
        user = database.execute("SELECT id FROM users LIMIT 1").fetchone()[0]
        for key, value in dict(sync_enabled=0, sync_server_url=server, language="en",
                               language_setup_done=1, apps_setup_done=1, enabled_apps=31,
                               tutorial_seen=1, launcher_guide_seen=1, practice_guide_seen=1,
                               habits_guide_seen=1, lumi_guides_seen=127, lumi_introduced=1, package_updates_allowed=0).items():
            database.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                             "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value",
                             (user, key, str(value)))


@contextlib.contextmanager
def application(profile, label, left, scan_file):
    log_path = OUTPUT / f"{label}.log"
    driver = UiDriver(OUTPUT / f"driver-{label}")
    with log_path.open("w") as log:
        app = subprocess.Popen([BINARY, "--bundle", str(ROOT / "build/inbe-full.zib")], cwd=ROOT,
                               env=os.environ | {"APP_DATA_ROOT": str(profile),
                                                 "INBE_TEST_DEVICE_LINK_SCAN": str(scan_file)} |
                               driver.environment(),
                               stdout=log, stderr=subprocess.STDOUT)
        driver.attach(app, log_path)
        try:
            def find():
                assert app.poll() is None, f"{label} exited"
                found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                                       text=True, capture_output=True, timeout=5)
                return found.stdout.split()[0] if found.returncode == 0 and found.stdout.strip() else ""
            window = wait_for(find, f"{label} window did not appear", 30)
            command("xdotool", "windowsize", window, "900", "720")
            command("xdotool", "windowmove", window, str(left), "0")
            driver.wait_idle(frames=3)
            # Apps in the rail, Profile, then the account view.
            driver.press(label="Apps", role="button", focus_id=NAVIGATION)
            driver.press(label="Profile", role="button")
            driver.press(label="Connect Account", role="button")
            driver.wait(label="Sync", role="title_bar")
            yield driver, window
            assert app.poll() is None, f"{label} crashed"
        finally:
            app.terminate()
            try:
                app.wait(timeout=5)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=5)


server, mailbox = device_link_mailbox.start()
address = f"http://127.0.0.1:{server.server_address[1]}"
with tempfile.TemporaryDirectory(prefix="inbe-device-link-") as directory:
    root = Path(directory)
    profiles = {name: root / name for name in ("a", "b", "c")}
    scans = {name: root / f"{name}.scan" for name in profiles}
    for profile in profiles.values():
        prepare(profile, address)
    with application(profiles["a"], "a", 0, scans["a"]) as a:
        a[0].press(label="Create New Account", role="button")
        a[0].wait(label="Sync now", role="button")
        account = wait_for(lambda: shown_account(a), "A did not create an account")
        # A holds the account: it shows a code, and the new device C scans it.
        a[0].press(label="Show code", role="button")
        code = scan(a, "a-code")
        assert code.endswith(":s:" + address), code
        with application(profiles["c"], "c", 960, scans["c"]) as c:
            scans["c"].write_text(code)
            wait_for(lambda: not scans["c"].exists(), "C did not read the scanned code")
            shown = digits(c)
            confirm = digits(a)
            assert shown == confirm, (shown, confirm)
            a[0].press(label="Connect", key=CONFIRM_CONNECT, role="button")
            connected(c, account)
        assert ("/api/v1/link/close", "") in mailbox.requests, "The link was not closed"
        received = setting(profiles["c"], "sync_public_id")
        assert received and received[:8] + "…" + received[-8:] == account, "C did not receive A's account"
        # A new device B shows its code; A scans it and sends the account.
        with application(profiles["b"], "b", 960, scans["b"]) as b:
            b[0].press(label="Show code", role="button")
            code = scan(b, "b-code")
            assert code.endswith(":r:" + address), code
            # B keeps polling through a node restart.
            mailbox.outage = 3
            scans["a"].write_text(code)
            wait_for(lambda: not scans["a"].exists(), "A did not read the scanned code")
            a[0].press(label="Connect", key=ASK_CONNECT, role="button")
            connected(b, account)
            assert mailbox.outage == 0, "B stopped polling during the outage"
    # Every device holds A's account, saved.
    account = setting(profiles["a"], "sync_public_id")
    assert account and setting(profiles["c"], "sync_public_id") == account, "C did not keep A's account"
    assert setting(profiles["b"], "sync_public_id") == account, "B did not receive A's account"
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
