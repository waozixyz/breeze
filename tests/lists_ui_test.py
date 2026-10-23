"""Lists on a private display, driven through Kryon's test driver.

Run by lists_ui_test.sh on its own Xvfb display: list tabs choose where a
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
    driver.wait(label="Shopping", role="tab")
    driver.wait(label="Share", role="button")
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

    def close_beside():
        """A tap beside the dialog, on the dimmed page, closes it."""
        tree = driver.tree()
        modal = [node for node in tree if node["kind"] == "modal" and node["visible"]][0]
        panel = [node for node in tree if node["parent"] == modal["index"] and node["kind"] == "custom"][0]
        x = modal["x"] + modal["width"] / 2
        y = (panel["y"] + panel["height"] + modal["y"] + modal["height"]) / 2
        driver.pointer(x, y)
        driver.pointer(x, y, down=True)
        driver.pointer(x, y, down=False)
        driver.release_pointer()
        wait_for(lambda: not driver.find(role="modal", visible=True), "a tap beside the dialog did not close it")

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
    driver.press(label="All", role="tab")
    # A short swipe slides back and changes nothing.
    swipe("Fresh fruit", -0.2)
    swipe("Fresh fruit", 0.2)
    assert driver.find(role="text_field", value="", visible=True), "a short swipe right began editing"
    assert sql("SELECT deleted_at FROM elist_items WHERE id=?", (original[0],)) == 0, "a short swipe left deleted"
    swipe("Fresh fruit", 0.6)
    driver.wait(role="text_field", value="Fresh fruit")
    driver.wait(label="Done", role="button")
    assert not driver.find(label="Delete item", role="button", visible=True), "Edit still shows a delete button"
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

    driver.press(label="Weekend", role="tab")
    add("Weekend task")
    wait_for(lambda: item_list("Weekend task"), "the task was not added")
    assert item_list("Weekend task") == "Weekend", f"FAIL tab selects destination list: got {item_list('Weekend task')!r}"
    driver.press(label="New list", role="button")
    driver.wait(label="Create list", role="button")
    add("Travel")
    wait_for(lambda: sql("SELECT COUNT(*) FROM elist_lists WHERE title='Travel'") == 1, "create list with Enter")
    driver.wait(label="Travel", role="tab")
    add("Pack bag")
    wait_for(lambda: item_list("Pack bag"), "the task was not added to the new list")
    assert item_list("Pack bag") == "Travel", f"FAIL new list is selected: got {item_list('Pack bag')!r}"
    # The tabs have their row to themselves. With more lists than fit, a
    # swipe back to the first list stays there instead of jumping back to
    # the selected tab.
    extra = [f"Long list name number {number} to scroll past" for number in range(1, 5)]
    for name in extra:
        driver.press(label="New list", role="button")
        driver.wait(label="Create list", role="button")
        add(name)
        driver.wait(label=name, role="tab")

    def swipe_tabs(to_start):
        """Drag along the tab row towards its first or its last tab."""
        shown = driver.find(role="tab", visible=True)
        # The list tabs come first; Open and All are tabs on a lower row.
        tabs = [tab for tab in shown if tab["visible_y"] == shown[0]["visible_y"]]
        y = UiDriver.center(tabs[0])[1]
        left = min(tab["visible_x"] for tab in tabs) + 20
        right = max(tab["visible_x"] + tab["visible_width"] for tab in tabs) - 20
        start, end = (left, right) if to_start else (right, left)
        for _ in range(2):
            driver.drag((start, y), (end, y), steps=12)
        driver.wait_idle(frames=5, timeout=3)

    def delete_selected_list(name):
        driver.press(label="Rename", role="button")
        driver.press(label="Delete list", role="button")
        driver.press(label="Tap again to delete this list", role="button")
        driver.wait_gone(label=name, role="tab", visible=False)

    assert not driver.find(label="Shopping", role="tab", visible=True), "the tabs did not overflow their row"
    tab_row = driver.wait(label=extra[-1], role="tab")
    tab_labels = {tab["label"] for tab in driver.find(role="tab")}
    beside_tabs = [node["label"] for node in driver.find(role="button", visible=True)
                   if node["label"] not in tab_labels and
                   abs(UiDriver.center(node)[1] - UiDriver.center(tab_row)[1]) < tab_row["visible_height"] / 2]
    assert not beside_tabs, f"buttons still share the tab row: {beside_tabs}"
    swipe_tabs(to_start=True)
    driver.wait(label="Shopping", role="tab")
    driver.wait_idle(frames=10, timeout=3)
    assert driver.find(label="Shopping", role="tab", visible=True), "the tabs jumped back to the selected list"
    delete_selected_list(extra[-1])
    for name in reversed(extra[:-1]):
        swipe_tabs(to_start=False)
        driver.press(label=name, role="tab")
        delete_selected_list(name)
    driver.press(label="Travel", role="tab")
    # Sharing is one icon that opens a dialog over the list; a tap beside it
    # closes it. Offline, it asks to connect an account first. No line above
    # the list says who has access, and Invitations appears only while one
    # waits.
    assert not any(label.startswith("Shared") or "Only you" in label for label in driver.labels()), driver.labels()
    assert not driver.find(label="Delete", role="button"), "a Delete button is on the list screen"
    assert not driver.find(contains="Invitations", role="button"), "Invitations shown with none waiting"
    driver.press(label="Share", role="button")
    assert re.search(r"connect|account|sharing", dialog(), re.IGNORECASE), dialog()
    close_beside()
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
    # shows no notice, so Share stays in its usual place. The refresh runs in
    # the background, so give it real time to fail.
    time.sleep(.7)
    driver.wait_idle(frames=3)
    calm("a failed refresh shows a notice")
    driver.press(label="Share", role="button")
    driver.wait(label="People with access")
    assert "Refresh" not in dialog() and "Alice" not in dialog(), dialog()
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
    assert command["list"]["title"] == "Shopping", command
    assert {row["title"] for row in command["list"]["items"]} == {"Fresh fruit", "Buy tea"}, command
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
    # The new scope starts with its dialogs closed; close Share if it stayed.
    if driver.find(role="modal", visible=True):
        close_beside()
    # The screen carries no access line; sharing is the one Share button.
    driver.press(contains="Garden", role="tab")
    driver.wait(label="Share", role="button")
    assert not any("Shared with" in label or "Invited:" in label for label in driver.labels()), driver.labels()
    # The owner's Share dialog on a list that already has people: a friend
    # who joined, one still invited and several more to invite.
    with writable() as db, db:
        user = db.execute("SELECT id FROM users LIMIT 1").fetchone()[0]
        db.execute("INSERT OR REPLACE INTO social_snapshots VALUES(?,?,?,1)",
                   (user, "friends.list", json.dumps({"friends": [
                       {"user_id_hash": "a" * 64, "alias": "Alice"}, {"user_id_hash": "c" * 64, "alias": "Cedar"},
                       {"user_id_hash": "d" * 64, "alias": "Dana"}, {"user_id_hash": "e" * 64, "alias": "Emerald"}]})))
    time.sleep(.5)
    driver.press(label="Share", role="button")
    time.sleep(1.0)
    subprocess.run(["import", "-window", find_window(), str(TEST_DIR / "share-owned.png")], check=True)
    wait_for(lambda: "Cedar" in dialog(), lambda: f"friends are not listed: {dialog()}")
    names = dialog()
    assert all(name in names for name in ("Alice", "Cedar", "You")), names
    assert "Dana" not in names and "Emerald" not in names, names
    assert "Owner" in names and "Invited" in names and "Read only" in names, names
    assert "Refresh" not in names, names
    # Escape works with the invite field focused and stays on this list.
    driver.press(key=6540)
    subprocess.run(["xdotool", "windowfocus", find_window()], check=True)
    subprocess.run(["xdotool", "keydown", "Escape"], check=True)
    time.sleep(.12)
    subprocess.run(["xdotool", "keyup", "Escape"], check=True)
    wait_for(lambda: not driver.find(role="modal", visible=True),
             "Escape did not close the focused sharing dialog")
    driver.wait(label="Share", role="button")
    driver.wait(contains="Garden", role="tab")
    driver.press(label="Share", role="button")
    driver.wait(label="Cedar")
    # The same open dialog remains readable on a phone-sized viewport.
    subprocess.run(["xdotool", "windowsize", find_window(), "390", "844"], check=True)
    wait_for(lambda: driver.wait(role="modal")["width"] <= 390,
             "the sharing dialog did not fit the phone viewport")
    driver.wait_idle(frames=3)
    phone_roles = driver.find(role="dropdown", visible=True)
    assert len(phone_roles) == 2, "collaborator controls do not fit the phone dialog"
    cedar = driver.wait(label="Cedar")
    cedar_role = driver.wait(label="Read only", role="dropdown")
    assert cedar_role["y"] >= cedar["y"] + cedar["height"], "phone name overlaps access controls"
    subprocess.run(["import", "-window", find_window(), str(TEST_DIR / "share-owned-phone.png")], check=True)
    subprocess.run(["xdotool", "windowsize", find_window(), "900", "720"], check=True)
    driver.wait_idle(frames=3)
    # A collaborator outside the friend cache is still shown by name.
    with writable() as db, db:
        db.execute("INSERT OR REPLACE INTO social_snapshots VALUES(?,?,?,1)",
                   (user, "friends.list", json.dumps({"friends": [
                       {"user_id_hash": "d" * 64, "alias": "Dana"}, {"user_id_hash": "e" * 64, "alias": "Emerald"}]})))
    driver.wait_idle(frames=3)
    assert "Alice" in dialog() and "Cedar" in dialog(), dialog()
    driver.press(key=6540)
    driver.type("da")
    driver.wait(label="Dana")
    assert not driver.find(label="Emerald", visible=True), "suggestions did not filter by typed name"
    driver.press(label="Dana")
    driver.wait(key=6540, value="Dana")
    # Viewers can inspect all access but cannot edit, invite or manage roles.
    close_beside()
    driver.press(contains="Groceries", role="tab")
    driver.press(label="Share", role="button")
    driver.wait(label="People with access")
    assert "Alice" in dialog() and "Owner" in dialog(), dialog()
    assert not driver.find(key=6540, visible=True), "viewer can invite"
    assert not driver.find(role="dropdown", visible=True), "viewer can manage permissions"
    close_beside()
    assert not driver.wait(key=6507)["enabled"], "viewer can add tasks"
    assert not driver.wait(key=6503)["enabled"], "viewer can rename a list"
    # Owners change a collaborator's role without sending its document again.
    driver.press(contains="Garden", role="tab")
    driver.press(label="Share", role="button")
    driver.wait(label="Cedar")
    driver.press(label="Read only")
    driver.wait(label="Can edit", role="option")
    driver.wait(label="Owner", role="option")
    driver.wait(label="Remove access", role="option")
    # The first Escape closes the access popup, leaving Share open.
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
    close_beside()
    # Move the receipt out of this fixture's scope before testing the inbox.
    with writable() as db, db:
        db.execute("DELETE FROM social_snapshots WHERE kind LIKE 'lists.attempt/%/http://127.0.0.1:10'")
        db.execute("UPDATE settings SET value='http://127.0.0.1:11' WHERE key='sync_server_url'")
        db.execute("INSERT OR REPLACE INTO social_snapshots VALUES(?,?,?,1)",
                   (user, "lists.shared/" + "b" * 64 + "/http://127.0.0.1:11", json.dumps(incoming)))
    driver.wait(label="Groceries", role="tab")
    driver.press(contains="Groceries", role="tab")
    assert not any("Shared by" in label for label in driver.labels()), driver.labels()
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
