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
    --screenshot-dark 1 > "$test_dir/app.log" 2>&1 &
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
tap 600 34
tap 300 90
xdotool type --clearmodifiers 'Weekend task'
xdotool keydown Return sleep 0.15 keyup Return
sleep 0.5
import -window "$window" "$test_dir/after-task.png"
expect "$(sql "SELECT l.title FROM elist_items i JOIN elist_lists l ON i.list_id=l.id WHERE i.title='Weekend task'")" 'Weekend' 'tab selects destination list'
tap 825 34
tap 300 90
xdotool type --clearmodifiers 'Travel'
xdotool keydown Return sleep 0.15 keyup Return
sleep 0.5
expect "$(sql "SELECT COUNT(*) FROM elist_lists WHERE title='Travel'")" '1' 'create list with Enter'
tap 300 90
xdotool type --clearmodifiers 'Pack bag'
xdotool keydown Return sleep 0.15 keyup Return
sleep 0.5
expect "$(sql "SELECT l.title FROM elist_items i JOIN elist_lists l ON i.list_id=l.id WHERE i.title='Pack bag'")" 'Travel' 'new list is selected'
import -window "$window" "$test_dir/tabs.png"
echo "PASS list tabs, task destination and new-list selection ($test_dir)"
