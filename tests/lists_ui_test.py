"""Lists on a private display, driven through Kryon's test driver.

Run by lists_ui_test.sh on its own Xvfb display: list chips choose where a
task goes, a new list is created with Enter, Share and Invitations open in a
dialog, and a friend invitation and an accepted invitation are stored as
durable deliveries without alarming the person when the node is unreachable.
"""

import contextlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

from ui_driver import UiDriver

assert os.environ.get("INBE_UI_TEST_XVFB") == "1", "Run tests/lists_ui_test.sh"
assert not os.environ.get("WAYLAND_DISPLAY") and not os.environ.get("DBUS_SESSION_BUS_ADDRESS")
BINARY = sys.argv[1]
ROOT = Path(__file__).resolve().parents[1]
TEST_DIR = ROOT / "build/lists-ui-test"
TEST_DIR.mkdir(parents=True, exist_ok=True)
ALARMING = re.compile(r"could|fail|error|unconfirmed", re.IGNORECASE)
# Shared list ids are UUIDs; the app ignores invitations to anything else.
SHARED_LIST = "5ad0e7f2-3b1c-4d6e-9f80-a1b2c3d4e5f6"
OWNED_LIST = "6be1f803-4c2d-4e7f-8091-b2c3d4e5f6a7"
GIVEN_LIST = "7cf2a914-5d3e-4f80-9102-c3d4e5f6a7b8"
driver = UiDriver(TEST_DIR / "driver")


def wait_for(predicate, message, timeout=10):
    deadline = time.monotonic() + timeout
    while True:
        result = predicate()
        if result:
            return result
        assert time.monotonic() < deadline, f"FAIL {message() if callable(message) else message} ({TEST_DIR})"
        time.sleep(.05)


with contextlib.ExitStack() as stack:
    temporary = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="inbe-lists-ui-")))
    log = stack.enter_context((TEST_DIR / "app.log").open("w"))
    # Screenshot mode seeds its own temporary database; the window stays
    # open for the test. Its own start capture goes to a temporary folder.
    app = subprocess.Popen(
        [BINARY, "--screenshot", str(temporary / "start.png"),
         "--bundle", str(ROOT / "build/inbe-full.zib"), "--feature", "lists",
         "--screenshot-scene", "lists", "--screenshot-width", "900", "--screenshot-height", "720",
         "--screenshot-ui-scale", "10", "--screenshot-theme", "0", "--screenshot-dark", "1"],
        env=os.environ | {"APP_SHOT_WINDOW": "1"} | driver.environment(),
        stdout=log, stderr=subprocess.STDOUT)
    database = Path(f"/tmp/inbe-screenshot-{app.pid}/inbe.db")

    def cleanup():
        if app.poll() is None:
            app.terminate()
        try:
            app.wait(timeout=5)
        except subprocess.TimeoutExpired:
            app.kill()
            app.wait(timeout=5)
        shutil.rmtree(database.parent, ignore_errors=True)
    stack.callback(cleanup)
    driver.attach(app, TEST_DIR / "app.log")

    def find_window():
        found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(app.pid)],
                               capture_output=True, text=True, timeout=5)
        return found.stdout.split()[0] if found.returncode == 0 and database.exists() else ""
    wait_for(find_window, "isolated app startup", timeout=20)
    driver.wait(label="Shopping", role="button")
    driver.wait(label="Add", role="button")
    driver.wait_idle(frames=3)

    def sql(query, parameters=()):
        # Read-only, so closing it never checkpoints the running app's WAL.
        uri = database.as_uri() + "?mode=ro"
        with contextlib.closing(sqlite3.connect(uri, uri=True, timeout=2)) as db:
            row = db.execute(query, parameters).fetchone()
            if row is None:
                return ""
            if len(row) > 1:
                return row
            return "" if row[0] is None else row[0]

    def writable():
        """A connection for fixtures written while the app runs. It never
        checkpoints on close, so it cannot remove the WAL the app writes to."""
        db = sqlite3.connect(database, timeout=2)
        db.setconfig(sqlite3.SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE, True)
        return contextlib.closing(db)

    def item_list(title):
        return sql("SELECT l.title FROM elist_items i JOIN elist_lists l ON i.list_id=l.id "
                   f"WHERE i.title='{title}'")

    def add(text):
        """Type into the page's one text field and press Enter."""
        driver.press(role="text_field")
        driver.type(text)
        driver.wait(role="text_field", value=text)
        driver.key("enter")

    def dialog():
        """The open dialog's words; it fails when no dialog shows."""
        tree = driver.tree()
        modals = [node["index"] for node in tree if node["kind"] == "modal" and node["visible"]]
        assert modals, "No dialog opened over the list"
        inside = set(modals)
        for node in tree:
            if node["parent"] in inside:
                inside.add(node["index"])
        return "\n".join(node["label"] for node in tree if node["index"] in inside and node["label"])

    def open_settings(name):
        """Tap a list's chip: the first tap selects it, a tap on the
        selected chip (with its gear) opens List settings."""
        driver.press(contains=name, role="button")
        try:
            driver.wait(label="List settings", timeout=2)
        except Exception:
            driver.press(contains=name, role="button")
            driver.wait(label="List settings")
        driver.wait_idle(frames=3)

    def page():
        """Every label List settings shows."""
        return "\n".join(driver.labels())

    def back():
        driver.press(label="Back", role="button")
        driver.wait_gone(label="List settings")
        driver.wait(label="Add", role="button")

    def calm(message):
        shown = [label for label in driver.labels() if ALARMING.search(label)]
        assert not shown, f"FAIL {message}: {shown} ({TEST_DIR})"

    # As in 1List, a tap on an item finishes it, a swipe right edits it and
    # a swipe left deletes it. Undo follows the real bundle and typed
    # persistence bridge, preserving the original completed item and its
    # comment rather than creating a copy.
    def swipe(title, share):
        """Drag the item's row sideways by this share of its width."""
        row = driver.wait(label=title, role="button")
        x, y = UiDriver.center(row)
        driver.drag((x, y), (x + row["visible_width"] * share, y), steps=10)
        driver.wait_idle(frames=3, timeout=2)

    original = sql("SELECT id,comment,sort_order FROM elist_items WHERE title='Fresh fruit' AND deleted_at=0")
    assert not driver.find(role="checkbox", visible=True), "items still have checkboxes"
    assert not [node for node in driver.tree() if node["visible"] and node["label"] == "Rename" and node["y"] > 160], \
        "items still have edit buttons"
    driver.press(label="Fresh fruit", role="button")
    wait_for(lambda: sql("SELECT done FROM elist_items WHERE id=?", (original[0],)) == 1,
             "a tap did not finish the item")
    # As in 1List, finished items leave the list; a pull down on the items
    # shows them above the open ones.
    driver.wait_gone(label="Fresh fruit", role="button")
    assert not driver.find(contains="Finished", visible=True), "the list still names its finished items"
    add_button = driver.wait(label="Add", role="button")
    pull_x = add_button["visible_x"] - 200
    pull_y = add_button["visible_y"] + add_button["visible_height"] + 60
    driver.drag((pull_x, pull_y), (pull_x, pull_y + 260), steps=12)
    driver.wait(label="Fresh fruit", role="button")
    assert not driver.find(contains="Finished", visible=True), "a heading names the finished items"
    # A short swipe slides back and changes nothing.
    swipe("Fresh fruit", -0.2)
    swipe("Fresh fruit", 0.2)
    assert driver.find(role="text_field", value="", visible=True), "a short swipe right began editing"
    assert sql("SELECT deleted_at FROM elist_items WHERE id=?", (original[0],)) == 0, "a short swipe left deleted"
    # A swipe right turns the item's own row into its field, with a check.
    swipe("Fresh fruit", 0.6)
    in_row = driver.wait(role="text_field", value="Fresh fruit")
    assert in_row["y"] > add_button["y"] + add_button["height"], "the item is edited in the top field, not its row"
    wait_for(lambda: driver.find(role="text_field", value="Fresh fruit", visible=True)[0]["focused"],
             "the item's field does not take the keyboard")
    driver.wait(label="Save", role="button")
    assert not driver.find(label="Delete item", role="button", visible=True), "Edit still shows a delete button"
    # Escape leaves the row as it was.
    subprocess.run(["xdotool", "windowfocus", find_window()], check=True)
    subprocess.run(["xdotool", "keydown", "Escape"], check=True)
    time.sleep(.12)
    subprocess.run(["xdotool", "keyup", "Escape"], check=True)
    driver.wait(label="Fresh fruit", role="button")
    assert sql("SELECT title FROM elist_items WHERE id=?", (original[0],)) == "Fresh fruit", "Escape changed the item"
    swipe("Fresh fruit", -0.6)
    wait_for(lambda: sql("SELECT deleted_at FROM elist_items WHERE id=?", (original[0],)) > 0,
             "a swipe left did not delete the item")
    # Deleting leaves Edit: the field is empty again, ready to add.
    driver.wait(label="Add", role="button")
    assert driver.find(role="text_field", value="", visible=True), \
        f"the deleted item's name stayed in the field: {driver.find(role='text_field')}"
    assert not driver.find(label="Fresh fruit", role="button", visible=True), "the deleted item is still listed"
    driver.press(label="Undo delete", role="button")
    wait_for(lambda: sql("SELECT deleted_at FROM elist_items WHERE id=?", (original[0],)) == 0,
             "Undo did not restore the item")
    restored = sql("SELECT id,comment,sort_order,done FROM elist_items WHERE title='Fresh fruit' AND deleted_at=0")
    assert restored == (*original, 1), ("Undo changed the item", original, restored)
    assert sql("SELECT COUNT(*) FROM elist_items WHERE title='Fresh fruit'") == 1, "Undo made a duplicate"
    driver.press(label="Fresh fruit", role="button")
    wait_for(lambda: sql("SELECT done FROM elist_items WHERE id=?", (original[0],)) == 0,
             "a second tap did not reopen the item")

    driver.press(label="Weekend", role="button")
    add("Weekend task")
    wait_for(lambda: item_list("Weekend task"), "the task was not added")
    assert item_list("Weekend task") == "Weekend", f"FAIL tab selects destination list: got {item_list('Weekend task')!r}"
    driver.press(label="New list", role="button")
    driver.wait(label="Create list", role="button")
    add("Travel")
    wait_for(lambda: sql("SELECT COUNT(*) FROM elist_lists WHERE title='Travel'") == 1, "create list with Enter")
    driver.wait(label="Travel", role="button")
    add("Pack bag")
    wait_for(lambda: item_list("Pack bag"), "the task was not added to the new list")
    assert item_list("Pack bag") == "Travel", f"FAIL new list is selected: got {item_list('Pack bag')!r}"
    # Lists are chips that wrap onto more rows, as in 1List: however many
    # there are, each shows its whole name and none is cut off.
    extra = [f"Long list name number {number} to wrap" for number in range(1, 5)]
    for name in extra:
        driver.press(label="New list", role="button")
        driver.wait(label="Create list", role="button")
        add(name)
        driver.wait(label=name, role="button")
    driver.wait_idle(frames=5, timeout=3)
    chips = [driver.wait(label=name, role="button") for name in ["Shopping", "Weekend", "Travel", *extra]]
    cut = [chip["label"] for chip in chips if chip["visible_width"] < chip["width"] - 1]
    assert not cut, f"list chips are cut off: {cut}"
    assert len({chip["y"] for chip in chips}) >= 2, "the list chips did not wrap onto another row"
    for chip in chips:
        for other in chips:
            if chip is not other:
                apart = (chip["x"] + chip["width"] <= other["x"] or other["x"] + other["width"] <= chip["x"] or
                         chip["y"] + chip["height"] <= other["y"] or other["y"] + other["height"] <= chip["y"])
                assert apart, f"list chips overlap: {chip['label']} and {other['label']}"
    # With many lists, each list still shows its own items.
    driver.press(label="Shopping", role="button")
    driver.wait(label="Fresh fruit", role="button")
    driver.press(label="Travel", role="button")
    driver.wait(label="Pack bag", role="button")
    # List settings holds the name, the people and Delete, which asks first.
    for name in extra:
        open_settings(name)
        driver.press(label="Delete list", role="button")
        driver.wait(label="Delete this list?")
        driver.press(label="Delete list", role="button")
        driver.wait_gone(label=name, role="button", visible=False)
        driver.wait(label="Add", role="button")
    driver.press(label="Travel", role="button")
    # Sharing lives in List settings, opened from the selected chip's gear.
    # Offline, it asks to connect an account first. A private list shows no
    # line about access, and Invitations appears only while one waits.
    assert not driver.find(label="Share", role="button"), "a Share button is still on the list screen"
    assert not driver.find(label="Rename", role="button"), "a Rename button is still on the list screen"
    assert not driver.find(contains="Invitations", role="button"), "Invitations shown with none waiting"
    open_settings("Travel")
    assert re.search(r"connect|account|sharing", page(), re.IGNORECASE), page()
    assert not driver.find(label="Delete this list?", visible=True), "Delete did not wait to be asked"
    back()
    # Synthetic credentials make the connected panel available without a real
    # account or HTTP delivery. The request must still pass through the actual
    # bundle, typed host codec, document builder and durable-attempt storage.
    with writable() as db, db:
        user = db.execute("SELECT id FROM users LIMIT 1").fetchone()[0]
        for key, value in {"sync_public_id": "b" * 64, "sync_public_key": "fixture",
                           "sync_private_key": "fixture", "sync_server_url": "http://127.0.0.1:9",
                           "sync_enabled": "1"}.items():
            db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) "
                       "ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user, key, value))
        db.execute("INSERT OR REPLACE INTO social_snapshots VALUES(?,?,?,1)",
                   (user, "friends.list", json.dumps({"friends": [{"user_id_hash": "a" * 64, "alias": "Alice"}]})))
    # The fixture node is unreachable: a failed refresh keeps the lists and
    # shows no notice. The refresh runs in the background, so give it real
    # time to fail.
    time.sleep(.7)
    driver.wait_idle(frames=3)
    calm("a failed refresh shows a notice")
    open_settings("Shopping")
    driver.wait(label="People with access")
    assert "Refresh" not in page() and "Alice" not in page(), page()
    driver.press(key=6540)
    driver.type("ali")
    driver.wait(label="Alice")
    assert not sql("SELECT json FROM social_snapshots WHERE kind LIKE 'lists.attempt/%'"), "typing sent an invitation"
    driver.press(label="Alice")
    driver.wait(key=6540, value="Alice")
    subprocess.run(["import", "-window", find_window(), str(TEST_DIR / "share-dialog.png")], check=True)
    driver.press(label="Invite", role="button")
    # The first failed delivery is retried quietly; nothing alarming is shown.
    wait_for(lambda: sql("SELECT json FROM social_snapshots WHERE kind LIKE 'lists.attempt/%'"),
             "the invitation was not stored for delivery")
    driver.wait_idle(frames=3)
    calm("a first failed delivery shows an error")
    command = json.loads(sql("SELECT json FROM social_snapshots WHERE kind LIKE 'lists.attempt/%'"))
    assert command["action"] == "invite" and command["target"] == "a" * 64, command
    assert command["access"] == "editor", command
    assert command["list"]["title"] == "Shopping", command
    assert {row["title"] for row in command["list"]["items"]} == {"Fresh fruit", "Buy tea"}, command
    back()
    # A different fixture server selects a separate cache and pending-attempt
    # scope, as a real account/server change does.
    with writable() as db, db:
        db.execute("UPDATE settings SET value='http://127.0.0.1:10' WHERE key='sync_server_url'")
        # A list this account shared with Alice, who joined, and Cedar, still
        # invited; and one Alice shared with this account.
        owned = {"id": OWNED_LIST, "owner": "b" * 64, "alias": "me", "title": "Garden",
                 "revision": 1, "deleted": 0, "access": "owner", "items": []}
        given = {"id": GIVEN_LIST, "owner": "a" * 64, "alias": "Alice", "title": "Groceries",
                 "revision": 1, "deleted": 0, "access": "viewer", "items": []}
        incoming = {"lists": [owned, given], "invitations": [
            {"id": "invitation-fixture", "list_id": SHARED_LIST, "title": "Weekend trip", "owner": "a" * 64,
             "target": "b" * 64, "alias": "Alice", "status": "pending"},
            {"id": "invitation-alice", "list_id": OWNED_LIST, "title": "Garden", "owner": "b" * 64,
             "alias": "me", "target": "a" * 64, "target_alias": "Alice", "status": "accepted", "access": "owner"},
            {"id": "invitation-cedar", "list_id": OWNED_LIST, "title": "Garden", "owner": "b" * 64,
             "alias": "me", "target": "c" * 64, "target_alias": "Cedar", "status": "pending", "access": "viewer"}]}
        db.execute("INSERT OR REPLACE INTO social_snapshots VALUES(?,?,?,1)",
                   (user, "lists.shared/" + "b" * 64 + "/http://127.0.0.1:10", json.dumps(incoming)))
    driver.wait(label="Invitations (1)", role="button")
    # A shared list names its people under the chips, as a document does.
    driver.press(contains="Garden", role="button")
    driver.wait(label="Alice · Cedar (Invited)", role="button")
    # The owner's List settings on a list that already has people: a friend
    # who joined, one still invited and several more to invite.
    with writable() as db, db:
        user = db.execute("SELECT id FROM users LIMIT 1").fetchone()[0]
        db.execute("INSERT OR REPLACE INTO social_snapshots VALUES(?,?,?,1)",
                   (user, "friends.list", json.dumps({"friends": [
                       {"user_id_hash": "a" * 64, "alias": "Alice"}, {"user_id_hash": "c" * 64, "alias": "Cedar"},
                       {"user_id_hash": "d" * 64, "alias": "Dana"}, {"user_id_hash": "e" * 64, "alias": "Emerald"}]})))
    time.sleep(.5)
    driver.press(label="Alice · Cedar (Invited)", role="button")
    driver.wait(label="List settings")
    time.sleep(1.0)
    subprocess.run(["import", "-window", find_window(), str(TEST_DIR / "share-owned.png")], check=True)
    wait_for(lambda: "Cedar" in page(), lambda: f"friends are not listed: {page()}")
    names = page()
    assert all(name in names for name in ("Alice", "Cedar (Invited)", "You")), names
    assert "Dana" not in names and "Emerald" not in names, names
    assert "Owner" in names and "Read only" in names, names
    assert "Refresh" not in names, names
    # Escape leaves List settings and stays on this list.
    driver.press(key=6540)
    subprocess.run(["xdotool", "windowfocus", find_window()], check=True)
    subprocess.run(["xdotool", "keydown", "Escape"], check=True)
    time.sleep(.12)
    subprocess.run(["xdotool", "keyup", "Escape"], check=True)
    wait_for(lambda: not driver.find(label="List settings", visible=True),
             "Escape did not leave List settings")
    driver.wait(label="Alice · Cedar (Invited)", role="button")
    open_settings("Garden")
    driver.wait(contains="Cedar")
    # The same page stays readable on a phone-sized viewport.
    subprocess.run(["xdotool", "windowsize", find_window(), "390", "844"], check=True)
    wait_for(lambda: driver.wait(label="List settings")["x"] < 390, "List settings did not fit the phone viewport")
    driver.wait_idle(frames=3)
    phone_roles = driver.find(role="dropdown", visible=True)
    assert len(phone_roles) == 3, f"access menus do not fit the phone page: {[node['label'] for node in phone_roles]}"
    cedar = driver.wait(contains="Cedar")
    cedar_role = driver.wait(label="Read only", role="dropdown")
    assert cedar_role["x"] >= cedar["x"] + cedar["width"] - 1, "phone name overlaps access controls"
    assert cedar_role["x"] + cedar_role["width"] <= 390, "an access menu runs off the phone page"
    subprocess.run(["import", "-window", find_window(), str(TEST_DIR / "share-owned-phone.png")], check=True)
    subprocess.run(["xdotool", "windowsize", find_window(), "900", "720"], check=True)
    driver.wait_idle(frames=3)
    # A collaborator outside the friend cache is still shown by name.
    with writable() as db, db:
        db.execute("INSERT OR REPLACE INTO social_snapshots VALUES(?,?,?,1)",
                   (user, "friends.list", json.dumps({"friends": [
                       {"user_id_hash": "d" * 64, "alias": "Dana"}, {"user_id_hash": "e" * 64, "alias": "Emerald"}]})))
    driver.wait_idle(frames=3)
    assert "Alice" in page() and "Cedar" in page(), page()
    driver.press(key=6540)
    driver.type("da")
    driver.wait(label="Dana")
    assert not driver.find(label="Emerald", visible=True), "suggestions did not filter by typed name"
    driver.press(label="Dana")
    driver.wait(key=6540, value="Dana")
    # Viewers can read all access but cannot rename, invite, manage roles or
    # delete.
    back()
    open_settings("Groceries")
    driver.wait(label="People with access")
    assert "Alice" in page() and "Owner" in page(), page()
    assert not driver.find(key=6540, visible=True), "viewer can invite"
    assert not driver.find(role="dropdown", visible=True), "viewer can manage permissions"
    assert not driver.wait(key=6551)["enabled"], "viewer can rename a list"
    assert not driver.find(label="Delete list", visible=True), "viewer can delete the list"
    back()
    assert not driver.wait(key=6507)["enabled"], "viewer can add tasks"
    # Owners change a collaborator's role without sending its document again.
    open_settings("Garden")
    driver.wait(contains="Cedar")
    driver.press(label="Read only")
    driver.wait(label="Can edit", role="option")
    driver.wait(label="Owner", role="option")
    driver.wait(label="Remove access", role="option")
    # The first Escape closes the access popup, leaving List settings open.
    driver.key("escape")
    wait_for(lambda: not driver.find(role="option", visible=True),
             "Escape did not close the access popup")
    driver.wait(label="People with access")
    driver.press(label="Read only")
    driver.press(label="Can edit", role="option")
    wait_for(lambda: sql("SELECT json FROM social_snapshots WHERE kind LIKE 'lists.attempt/%/http://127.0.0.1:10'"),
             "the permission change was not stored")
    permission = json.loads(sql("SELECT json FROM social_snapshots WHERE kind LIKE 'lists.attempt/%/http://127.0.0.1:10'"))
    assert permission["action"] == "access" and permission["access"] == "editor" and permission["target"] == "c" * 64, permission
    assert permission["list"] == {"id": OWNED_LIST}, permission
    back()
    # Move the receipt out of this fixture's scope before testing the inbox.
    with writable() as db, db:
        db.execute("DELETE FROM social_snapshots WHERE kind LIKE 'lists.attempt/%/http://127.0.0.1:10'")
        db.execute("UPDATE settings SET value='http://127.0.0.1:11' WHERE key='sync_server_url'")
        db.execute("INSERT OR REPLACE INTO social_snapshots VALUES(?,?,?,1)",
                   (user, "lists.shared/" + "b" * 64 + "/http://127.0.0.1:11", json.dumps(incoming)))
    driver.wait(label="Groceries", role="button")
    driver.press(contains="Groceries", role="button")
    driver.wait(label="Alice", role="button")
    window = find_window()
    subprocess.run(["import", "-window", window, str(TEST_DIR / "shared-names.png")], check=True)
    driver.press(label="Invitations (1)", role="button")
    wait_for(lambda: "Weekend trip" in dialog(), lambda: f"the invitation is not listed: {dialog()}")
    assert "From: Alice" in dialog(), dialog()
    accept = driver.wait(label="Accept", role="button")
    decline = driver.wait(label="Decline", role="button")
    assert accept["visible_height"] >= 44 and decline["visible_height"] >= 44
    assert accept["x"] + accept["width"] <= decline["x"], "Invitation actions overlap"
    window = find_window()
    assert int(subprocess.check_output(["xdotool", "getwindowpid", window], text=True)) == app.pid
    subprocess.run(["import", "-window", window, str(TEST_DIR / "invitations.png")], check=True)
    calm("a failed refresh shows a notice")
    driver.press(label="Accept", role="button")
    wait_for(lambda: sql("SELECT json FROM social_snapshots WHERE kind LIKE 'lists.attempt/%/http://127.0.0.1:11'"),
             "the acceptance was not stored for delivery")
    command = json.loads(sql("SELECT json FROM social_snapshots WHERE kind LIKE 'lists.attempt/%/http://127.0.0.1:11'"))
    assert command["action"] == "accept" and command["invitation_id"] == "invitation-fixture", command
    assert sql(f"SELECT COUNT(*) FROM elist_lists WHERE id='{SHARED_LIST}'") == 0
    print(f"PASS item deletion and identity-preserving undo, list tabs, private task destination, friend invitation, inbox acceptance and durable delivery ({TEST_DIR})")
