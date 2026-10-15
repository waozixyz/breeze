#!/usr/bin/env bash
set -euo pipefail
if [[ -z "${INBE_UI_TEST_XVFB:-}" ]]; then
    exec env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY -u SESSION_MANAGER \
        -u DBUS_SESSION_BUS_ADDRESS YUE_DESKTOP_RECOVERY=0 xvfb-run -a \
        env -u WAYLAND_DISPLAY -u SESSION_MANAGER -u DBUS_SESSION_BUS_ADDRESS \
        SDL_VIDEODRIVER=x11 INBE_UI_TEST_XVFB=1 bash "$0" "$@"
fi
binary="${1:?native binary required}"
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
test_dir="$root/build/lists-ui-test"
mkdir -p "$test_dir"
exec 9>"$test_dir/lock"
flock 9
APP_SHOT_WINDOW=1 "$binary" --screenshot "$test_dir/start.png" \
    --bundle "$(dirname -- "$0")/../build/inbe-full.zib" --feature lists \
    --screenshot-scene lists --screenshot-width 900 --screenshot-height 720 \
    --screenshot-ui-scale 10 --screenshot-theme 0 --screenshot-dark 1 > "$test_dir/app.log" 2>&1 &
app_pid=$!
db="/tmp/inbe-screenshot-$app_pid/inbe.db"
cleanup() {
    kill "$app_pid" 2>/dev/null || true
    wait "$app_pid" 2>/dev/null || true
    rm -rf "/tmp/inbe-screenshot-$app_pid"
}
trap cleanup EXIT
window=""
for attempt in {1..80}; do
    window="$(xdotool search --onlyvisible --pid "$app_pid" 2>/dev/null | head -1 || true)"
    if [[ -n "$window" && -f "$db" ]]; then break; fi
    sleep 0.1
done
[[ -n "$window" && -f "$db" ]]
sleep 1
xdotool windowfocus --sync "$window"
tap() {
    xdotool mousemove --window "$window" "$1" "$2" mousedown 1 sleep 0.08 mouseup 1
    sleep 0.3
}
sql() { sqlite3 -cmd '.timeout 2000' "$db" "$1"; }
expect() {
    [[ "$1" == "$2" ]] || { echo "FAIL $3: got '$1', expected '$2' ($test_dir)"; exit 1; }
}
tap 245 34
tap 300 146
xdotool type --clearmodifiers 'Weekend task'
xdotool keydown Return sleep 0.15 keyup Return
sleep 0.5
import -window "$window" "$test_dir/after-task.png"
expect "$(sql "SELECT l.title FROM elist_items i JOIN elist_lists l ON i.list_id=l.id WHERE i.title='Weekend task'")" 'Weekend' 'tab selects destination list'
tap 862 34
tap 300 90
xdotool type --clearmodifiers 'Travel'
xdotool keydown Return sleep 0.15 keyup Return
sleep 0.5
expect "$(sql "SELECT COUNT(*) FROM elist_lists WHERE title='Travel'")" '1' 'create list with Enter'
tap 300 146
xdotool type --clearmodifiers 'Pack bag'
xdotool keydown Return sleep 0.15 keyup Return
sleep 0.5
expect "$(sql "SELECT l.title FROM elist_items i JOIN elist_lists l ON i.list_id=l.id WHERE i.title='Pack bag'")" 'Travel' 'new list is selected'
import -window "$window" "$test_dir/tabs.png"
tap 60 90
sleep 0.4
import -window "$window" "$test_dir/share-offline.png"
tesseract "$test_dir/share-offline.png" stdout 2>/dev/null | rg -qi 'connect|account|sharing'
tap 60 90
tap 190 90
sleep 0.4
import -window "$window" "$test_dir/invitations-offline.png"
tesseract "$test_dir/invitations-offline.png" stdout 2>/dev/null | rg -qi 'invitation'
# Synthetic credentials make the connected panel available without a real
# account or HTTP delivery. The request must still pass through the actual
# bundle, typed host codec, document builder and durable-attempt storage.
python3 - "$db" <<'SEED'
import json, sqlite3, sys
with sqlite3.connect(sys.argv[1]) as db:
    user = db.execute("SELECT id FROM users LIMIT 1").fetchone()[0]
    for key, value in {"sync_public_id": "b"*64, "sync_public_key": "fixture", "sync_private_key": "fixture", "sync_server_url": "http://127.0.0.1:9", "sync_enabled": "1"}.items():
        db.execute("INSERT INTO settings(user_id,key,value,updated_at) VALUES(?,?,?,1) ON CONFLICT(user_id,key) DO UPDATE SET value=excluded.value", (user,key,value))
    db.execute("INSERT OR REPLACE INTO social_snapshots VALUES(?,?,?,1)", (user,"friends.list",json.dumps({"friends":[{"user_id_hash":"a"*64,"alias":"Alice"}]})))
SEED
sleep 0.7
# The fixture node is unreachable: a failed refresh keeps the lists and shows
# no notice, so Share stays in its usual place.
import -window "$window" "$test_dir/connected-offline.png"
if tesseract "$test_dir/connected-offline.png" stdout 2>/dev/null | rg -qi 'could|fail|error|unconfirmed'; then
    echo "FAIL a failed refresh shows a notice ($test_dir/connected-offline.png)"; exit 1
fi
tap 60 90
sleep 0.3
import -window "$window" "$test_dir/friends.png"
# Sparse-text mode reads the lone friend name beside its Invite button.
tesseract "$test_dir/friends.png" stdout --psm 11 2>/dev/null | rg -qi 'Alice'
tap 820 326
sleep 0.4
# The first failed delivery is retried quietly; nothing alarming is shown.
import -window "$window" "$test_dir/invite-retrying.png"
if tesseract "$test_dir/invite-retrying.png" stdout 2>/dev/null | rg -qi 'could|fail|error|unconfirmed'; then
    echo "FAIL a first failed delivery shows an error ($test_dir/invite-retrying.png)"; exit 1
fi
python3 - "$db" <<'CHECK'
import json, sqlite3, sys
with sqlite3.connect(sys.argv[1]) as db:
    raw = db.execute("SELECT json FROM social_snapshots WHERE kind LIKE 'lists.attempt/%'").fetchone()[0]
    command = json.loads(raw)
    assert command["action"] == "invite" and command["target"] == "a"*64, command
    assert command["list"]["title"] == "Shopping", command
    assert {row["title"] for row in command["list"]["items"]} == {"Fresh fruit", "Buy tea"}, command
CHECK
# A different fixture server selects a separate cache and pending-attempt
# scope, as a real account/server change does.
python3 - "$db" <<'SEED'
import json, sqlite3, sys
with sqlite3.connect(sys.argv[1]) as db:
    user = db.execute("SELECT id FROM users LIMIT 1").fetchone()[0]
    db.execute("UPDATE settings SET value='http://127.0.0.1:10' WHERE key='sync_server_url'")
    incoming = {"lists":[], "invitations":[{"id":"invitation-fixture","list_id":"shared-fixture","title":"Weekend trip","owner":"a"*64,"target":"b"*64,"alias":"Alice","status":"pending"}]}
    db.execute("INSERT OR REPLACE INTO social_snapshots VALUES(?,?,?,1)", (user,"lists.shared/"+"b"*64+"/http://127.0.0.1:10",json.dumps(incoming)))
SEED
sleep 0.7
tap 180 90
sleep 0.3
import -window "$window" "$test_dir/incoming.png"
tesseract "$test_dir/incoming.png" stdout 2>/dev/null | rg -qi 'Weekend trip'
if tesseract "$test_dir/incoming.png" stdout 2>/dev/null | rg -qi 'could|fail|error|unconfirmed'; then
    echo "FAIL a failed refresh shows a notice ($test_dir/incoming.png)"; exit 1
fi
tap 80 250
sleep 0.4
python3 - "$db" <<'CHECK'
import json, sqlite3, sys
with sqlite3.connect(sys.argv[1]) as db:
    raw = db.execute("SELECT json FROM social_snapshots WHERE kind LIKE 'lists.attempt/%/http://127.0.0.1:10'").fetchone()[0]
    command = json.loads(raw)
    assert command["action"] == "accept" and command["invitation_id"] == "invitation-fixture", command
    assert db.execute("SELECT COUNT(*) FROM elist_lists WHERE id='shared-fixture'").fetchone()[0] == 0
CHECK
echo "PASS list tabs, private task destination, friend invitation, inbox acceptance and durable delivery ($test_dir)"
