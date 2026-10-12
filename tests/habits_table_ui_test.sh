#!/usr/bin/env bash
set -euo pipefail
# Screenshot mode seeds its own temporary database.
if [[ -z "${INBE_UI_TEST_XVFB:-}" ]]; then
  exec env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY -u SESSION_MANAGER \
    -u DBUS_SESSION_BUS_ADDRESS YUE_DESKTOP_RECOVERY=0 xvfb-run -a \
    env -u WAYLAND_DISPLAY -u SESSION_MANAGER -u DBUS_SESSION_BUS_ADDRESS \
    SDL_VIDEODRIVER=x11 INBE_UI_TEST_XVFB=1 bash "$0" "$@"
fi
binary="${1:?native binary required}"
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
test_dir="$root/build/habits-table-ui-test"
mkdir -p "$test_dir"
exec 9>"$test_dir/lock"
flock 9
# A short window, so the six habits need the list to scroll.
APP_SHOT_WINDOW=1 "$binary" --screenshot "$test_dir/start.png" \
  --screenshot-scene habits_overview --screenshot-width 411 --screenshot-height 600 \
  --screenshot-theme 4 --screenshot-dark 1 >"$test_dir/app.log" 2>&1 &
app_pid=$!
db="/tmp/inbe-screenshot-$app_pid/inbe.db"
cleanup() {
  kill "$app_pid" 2>/dev/null || true
  wait "$app_pid" 2>/dev/null || true
  rm -rf "/tmp/inbe-screenshot-$app_pid"
}
trap cleanup EXIT
window=""
for attempt in $(seq 1 80); do
  window="$(xdotool search --onlyvisible --pid "$app_pid" 2>/dev/null | head -1 || true)"
  if [[ -n "$window" && -f "$db" ]]; then break; fi
  sleep 0.1
done
[[ -n "$window" && -f "$db" ]] || { echo "FAIL isolated app startup: $test_dir"; exit 1; }
sleep 1
xdotool windowfocus --sync "$window"
sql() { sqlite3 -cmd '.timeout 2000' "$db" "$1"; }
expect() { [[ "$1" == "$2" ]] || { echo "FAIL $3: got '$1', expected '$2' ($test_dir)"; exit 1; }; }
word() { python3 "$root/tests/rendered_word.py" "$@"; }
shot() { import -window "$window" "$test_dir/$1.png"; }
find_word() {
  local found
  found="$(word "$test_dir/$1.png" "$2" "${4:-0}")" || { echo "FAIL $3 ($test_dir/$1.png)" >&2; exit 1; }
  echo "$found"
}
tap() { xdotool mousemove --window "$window" "$1" "$2" mousedown 1 sleep 0.08 mouseup 1; sleep 0.3; }
# Press at one point, move there in steps, hold, and release.
drag() {
  xdotool mousemove --window "$window" "$1" "$2" mousedown 1 sleep 0.1
  for step in $(seq 1 12); do
    xdotool mousemove --window "$window" "$(($1 + ($3 - $1) * step / 12))" \
      "$(($2 + ($4 - $2) * step / 12))"
    sleep 0.025
  done
  sleep "${5:-0.3}"
  if [[ -n "${6:-}" ]]; then shot "$6"; fi
  xdotool mouseup 1
  sleep 0.4
}
order() { sql "SELECT group_concat(name,'|') FROM (SELECT name FROM habits WHERE deleted_at=0 ORDER BY sort_order)"; }
day_count() { sql "SELECT COALESCE(SUM(completed),0) FROM habit_days WHERE habit_id=(SELECT id FROM habits WHERE name='Yoga')"; }
deactivated() { sql "SELECT deactivated FROM habits WHERE name='Yoga'"; }
lower() { tr '[:upper:]' '[:lower:]'; }
# The screenshot scene seeds its habits after the window and database
# appear; wait for the seed instead of assuming a fixed startup time.
baseline=""
for attempt in $(seq 1 100); do
  baseline="$(order 2>/dev/null || true)"
  if [[ -n "$baseline" ]]; then break; fi
  sleep 0.1
done
expect "$baseline" 'Meditation|Yoga|Sit ups|Push ups|Cold Shower|Jumping Rope' 'initial order'

# The day columns: today first, then yesterday and the day before, named
# by their weekdays in the header.
yesterday="$(LC_ALL=C date -d yesterday +%a | lower)"
before_yesterday="$(LC_ALL=C date -d '2 days ago' +%a | lower)"
for attempt in $(seq 1 20); do
  shot overview
  word "$test_dir/overview.png" yoga >/dev/null 2>&1 && break
  sleep 0.5
done
read -r day1_x header_y < <(find_word overview "$yesterday" "the header names yesterday")
read -r day2_x _ < <(find_word overview "$before_yesterday" "the header names the day before")
today_x=$((day1_x - (day2_x - day1_x)))
read -r yoga_x yoga_y < <(find_word overview yoga "Yoga has a row" "$header_y")
before="$(day_count)"
tap "$today_x" "$yoga_y"
expect "$(day_count)" "$((before+1))" 'today check-in'
expect "$(sql "SELECT local_date FROM habit_days WHERE habit_id=(SELECT id FROM habits WHERE name='Yoga') AND completed=1")" "$(date +%Y%m%d)" 'the first column marks today'
tap "$today_x" "$yoga_y"
expect "$(day_count)" "$before" 'today undo'
tap "$day1_x" "$yoga_y"
expect "$(sql "SELECT local_date FROM habit_days WHERE habit_id=(SELECT id FROM habits WHERE name='Yoga') AND completed=1")" "$(date -d yesterday +%Y%m%d)" 'the second column marks yesterday'
tap "$day1_x" "$yoga_y"
expect "$(day_count)" "$before" 'yesterday undo'
drag "$today_x" "$yoga_y" "$((today_x + 150))" "$yoga_y"
expect "$(day_count)" "$before" 'a drag over the days marks none'
# A tap on the name opens the habit's details below its row; another closes them.
tap "$yoga_x" "$yoga_y"
shot yoga-open
find_word yoga-open streak "the open habit shows its streak" >/dev/null
# Its editor opens from the last of the details' actions, at the table's
# right edge below the row and the description, and gives Yoga an icon.
day_w=$((day1_x - today_x))
tap "$((today_x + day_w * 6 - 8))" "$((yoga_y + 90))"
for attempt in $(seq 1 12); do
  shot editor
  word "$test_dir/editor.png" icon >/dev/null 2>&1 && break
  xdotool mousemove --window "$window" 200 300 click 5 click 5
  sleep 0.3
done
read -r icon_x icon_y < <(find_word editor icon "the editor has no icons")
# The third choice is the second icon, a person sitting in meditation.
tap "$((icon_x + 6 + 48 * 2))" "$((icon_y + 38))"
shot editor-icon
read -r save_x save_y < <(find_word editor-icon save "the editor has no Save button")
tap "$save_x" "$save_y"
expect "$(sql "SELECT icon FROM habits WHERE name='Yoga'")" 2 'the chosen icon is saved'
shot yoga-closed
if word "$test_dir/yoga-closed.png" streak >/dev/null; then
  echo "FAIL the details stayed open ($test_dir/yoga-closed.png)"; exit 1
fi
expect "$(order)" 'Meditation|Yoga|Sit ups|Push ups|Cold Shower|Jumping Rope' 'taps keep the order'
echo "PASS habit table: day columns, check-ins, undo, drag cancellation, details, icon"

# Dragged onto the inactive habits below the table, Yoga becomes inactive:
# it keeps its data and leaves the table.
read -r inactive_x inactive_y < <(find_word yoga-closed inactive "the inactive habits are below the table")
drag "$yoga_x" "$yoga_y" "$inactive_x" "$inactive_y" 0.5 row-over-inactive
expect "$(deactivated)" 1 'a habit dropped on the inactive habits becomes inactive'
expect "$(order)" 'Meditation|Yoga|Sit ups|Push ups|Cold Shower|Jumping Rope' 'deactivating keeps the order'
shot deactivated-hidden
if word "$test_dir/deactivated-hidden.png" yoga >/dev/null; then
  echo "FAIL Yoga is still in the table ($test_dir/deactivated-hidden.png)"; exit 1
fi
read -r show_x show_y < <(find_word deactivated-hidden inactive "no dropdown shows the inactive habits")
tap "$show_x" "$show_y"
shot deactivated-shown
read -r row_x row_y < <(find_word deactivated-shown yoga "Yoga is not listed below the table")
read -r first_x first_y < <(find_word deactivated-shown meditation "Meditation's row is missing")
tap "$row_x" "$row_y"
expect "$(deactivated)" 1 'a tap does not reactivate'
# Dropped on Meditation's row, Yoga becomes active in Meditation's place.
drag "$row_x" "$row_y" "$first_x" "$first_y" 0.3 dragging
expect "$(deactivated)" 0 'a drag into the table reactivates Yoga'
expect "$(order)" 'Yoga|Meditation|Sit ups|Push ups|Cold Shower|Jumping Rope' 'Yoga takes the place it was dropped on'
shot reactivated
# The dropdown stays, so a habit can be dragged into it again.
find_word reactivated inactive "the inactive habits left with their last habit" >/dev/null
echo "PASS inactive habits: dragged into the dropdown, hidden from the table, dragged back into place"

# With a mouse, a row follows a press that moves at once and takes the
# place of the row it is dropped on.
read -r meditation_x meditation_y < <(find_word reactivated meditation "Meditation's row is missing")
read -r push_x push_y < <(find_word reactivated push "the Push ups row is missing")
drag "$meditation_x" "$meditation_y" "$push_x" "$push_y" 0.3 row-dragging
expect "$(order)" 'Yoga|Sit ups|Push ups|Meditation|Cold Shower|Jumping Rope' 'a dragged row takes the place it was dropped on'
# Held at the bottom edge of the table, a dragged row scrolls it down to the
# last habit, which is out of sight at first.
shot row-moved
if word "$test_dir/row-moved.png" jumping >/dev/null; then
  echo "FAIL Jumping Rope is already in sight, so nothing needs to scroll ($test_dir/row-moved.png)"; exit 1
fi
read -r yoga_x yoga_y < <(find_word row-moved yoga "Yoga's row is missing")
read -r _ section_y < <(find_word row-moved inactive "the inactive habits are missing")
edge_y=$((section_y - 46))
xdotool mousemove --window "$window" "$yoga_x" "$yoga_y" mousedown 1 sleep 0.1
for step in $(seq 1 12); do
  xdotool mousemove --window "$window" "$yoga_x" "$((yoga_y + (edge_y - yoga_y) * step / 12))"
  sleep 0.025
done
sleep 1.5
# Lifted off the edge, the dragged copy no longer covers the last row.
xdotool mousemove --window "$window" "$yoga_x" "$((edge_y - 120))"
sleep 0.3
shot edge-scrolled
read -r _ jump_y < <(word "$test_dir/edge-scrolled.png" jumping) ||
  { xdotool mouseup 1; echo "FAIL holding a row at the edge did not scroll the table ($test_dir/edge-scrolled.png)"; exit 1; }
xdotool mousemove --window "$window" "$yoga_x" "$jump_y"
sleep 0.2
xdotool mouseup 1
sleep 0.4
expect "$(order)" 'Sit ups|Push ups|Meditation|Cold Shower|Jumping Rope|Yoga' 'a row dragged down the scrolled table goes last'
echo "PASS habit rows: dragged into another place and scrolled at the edge"

# Holding Backspace keeps deleting, as in any text editor: a new habit typed
# as "Walkx", cleared with one held Backspace and typed again is "Run".
shot before-new
read -r new_x new_y < <(find_word before-new new "the New Habit button is missing")
tap "$new_x" "$new_y"
shot new-habit
read -r name_x name_y < <(find_word new-habit name "the editor has no name field")
tap "$name_x" "$((name_y + 40))"
xdotool type --delay 60 Walkx
sleep 0.3
xdotool keydown BackSpace
sleep 1.6
xdotool keyup BackSpace
sleep 0.3
xdotool type --delay 60 Run
sleep 0.3
shot new-habit-named
read -r create_x create_y < <(find_word new-habit-named create "the editor has no Create button")
tap "$create_x" "$create_y"
expect "$(sql "SELECT COUNT(*) FROM habits WHERE name='Run' AND deleted_at=0")" 1 'a held Backspace deleted the whole name'
echo "PASS text fields: a held Backspace keeps deleting"
echo "Screenshots and isolated database: $test_dir ; $db"
