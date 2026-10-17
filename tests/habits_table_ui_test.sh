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
# A tall window shows the whole table; it is made shorter later, so the
# table needs to scroll.
APP_SHOT_WINDOW=1 "$binary" --screenshot "$test_dir/start.png" \
  --screenshot-scene habits_overview --screenshot-width 411 --screenshot-height 760 \
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

# Whether the table's scrollbar shows beside the rows between two heights:
# at the panel's right edge, its thumb is lighter than the table beside it.
scrollbar_shown() {
  python3 - "$test_dir/$1.png" "$2" "$3" <<'PY'
import sys
from PIL import Image

image = Image.open(sys.argv[1]).convert("RGB")


def distance(first, second):
    return sum(abs(a - b) for a, b in zip(first, second))


rows = 0
shown = 0
for y in range(int(sys.argv[2]), int(sys.argv[3]), 4):
    page = image.getpixel((image.width - 3, y))
    edge = image.width - 3
    while edge > 12 and distance(image.getpixel((edge, y)), page) <= 12:
        edge -= 1
    rows += 1
    if distance(image.getpixel((edge - 5, y)), image.getpixel((edge - 12, y))) > 60:
        shown += 1
sys.exit(0 if rows > 0 and shown * 5 >= rows * 4 else 1)
PY
}
# Whether two screenshots show the same day names, pixel for pixel, in the
# table's header around a height.
same_header() {
  python3 - "$test_dir/$1.png" "$test_dir/$2.png" "$3" <<'PY'
import sys
from PIL import Image, ImageChops

first = Image.open(sys.argv[1]).convert("RGB")
second = Image.open(sys.argv[2]).convert("RGB")
y = int(sys.argv[3])
box = (0, y - 14, first.width, y + 14)
same = first.size == second.size and \
    ImageChops.difference(first.crop(box), second.crop(box)).getbbox() is None
sys.exit(0 if same else 1)
PY
}
# A screenshot once the table has come to rest.
rest_shot() {
  shot "$1"
  for attempt in $(seq 1 20); do
    sleep 0.3
    shot "$1-next"
    if cmp -s "$test_dir/$1.png" "$test_dir/$1-next.png"; then
      break
    fi
    mv "$test_dir/$1-next.png" "$test_dir/$1.png"
  done
  rm -f "$test_dir/$1-next.png"
}
yesterday="$(LC_ALL=C date -d yesterday +%a | lower)"
# Opening a habit's details or the inactive habits never makes a scrollbar
# appear and the day columns move or drop: when either would need room to
# scroll, the scrollbar shows from the start. In a window this short, each
# of them alone makes the table scroll; at a phone's width the rows then
# show their icons alone from the start.
steady_columns() {
  local name="$3" header_y icon_x yoga_y inactive_x inactive_y
  # The window starts centred; at the screen's corner a wide one stays whole.
  xdotool windowmove --sync "$window" 0 0 || true
  xdotool windowsize --sync "$window" "$1" "$2" || true
  sleep 1
  rest_shot "$name-closed"
  read -r _ header_y < <(find_word "$name-closed" "$yesterday" "the $name table names yesterday")
  scrollbar_shown "$name-closed" "$((header_y + 30))" "$((header_y + 200))" ||
    { echo "FAIL the $name table shows no scrollbar before anything opens ($test_dir/$name-closed.png)"; exit 1; }
  # Yoga's row is the second below the day names; its icon, at the start
  # of the row as the inactive habits' name is, opens it.
  read -r inactive_x inactive_y < <(find_word "$name-closed" inactive "the $name table has no inactive habits")
  icon_x=$((inactive_x - 24))
  yoga_y=$((header_y + 110))
  tap "$icon_x" "$yoga_y"
  rest_shot "$name-card"
  find_word "$name-card" streak "Yoga's details did not open in the $name table" >/dev/null
  same_header "$name-closed" "$name-card" "$header_y" ||
    { echo "FAIL opening Yoga moved the $name table's day columns ($test_dir/$name-card.png)"; exit 1; }
  tap "$icon_x" "$yoga_y"
  rest_shot "$name-card-closed"
  tap "$inactive_x" "$inactive_y"
  rest_shot "$name-inactive"
  find_word "$name-inactive" drag "the inactive habits did not open in the $name table" >/dev/null
  same_header "$name-closed" "$name-inactive" "$header_y" ||
    { echo "FAIL opening the inactive habits moved the $name table's day columns ($test_dir/$name-inactive.png)"; exit 1; }
  tap "$inactive_x" "$inactive_y"
}
steady_columns 390 660 phone
steady_columns 1024 660 desktop
# A table that fits with everything open shows no scrollbar.
xdotool windowsize --sync "$window" 411 1000 || true
sleep 1
rest_shot tall
read -r _ tall_header_y < <(find_word tall "$yesterday" "the tall table names yesterday")
if scrollbar_shown tall "$((tall_header_y + 30))" "$((tall_header_y + 200))"; then
  echo "FAIL a table with room for everything shows a scrollbar ($test_dir/tall.png)"; exit 1
fi
xdotool windowsize --sync "$window" 411 760 || true
sleep 1
echo "PASS steady columns: opening a habit or the inactive habits keeps the day columns at a phone's and a desktop's width"

# The day columns: today first, then yesterday and the day before, named
# by their weekdays in the header.
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
# Opening scrolls the list so the whole card shows; wait until it rests.
shot yoga-open
for attempt in $(seq 1 20); do
  sleep 0.3
  shot yoga-open-rest
  cmp -s "$test_dir/yoga-open.png" "$test_dir/yoga-open-rest.png" && break
  mv "$test_dir/yoga-open-rest.png" "$test_dir/yoga-open.png"
done
find_word yoga-open streak "the open habit shows its streak" >/dev/null
# Its editor opens from the last of the details' actions, at the table's
# right edge above the figures, and gives Yoga an icon.
read -r _ week_y < <(find_word yoga-open week "the open habit shows this week")
# The open details make the table scroll; its scrollbar already showed, so
# the day columns stay where they were. Aim at the middle of the edit action
# from where they are.
same_header overview yoga-open "$header_y" ||
  { echo "FAIL opening Yoga moved the day columns ($test_dir/yoga-open.png)"; exit 1; }
read -r open_day1_x _ < <(find_word yoga-open "$yesterday" "the open table names yesterday")
read -r open_day2_x _ < <(find_word yoga-open "$before_yesterday" "the open table names the day before")
day_w=$((open_day2_x - open_day1_x))
edit_x=$((open_day1_x + day_w * 5 - 24))
tap "$edit_x" "$((week_y - 55))"
for attempt in $(seq 1 12); do
  shot editor
  word "$test_dir/editor.png" icon >/dev/null 2>&1 && break
  # While the details still show, the tap did not reach their edit action
  # (a slow runner can drop it); tap it again where it is now. Once the
  # editor is open, scroll down to its icons.
  if week_at="$(word "$test_dir/editor.png" week 2>/dev/null)"; then
    tap "$edit_x" "$((${week_at#* } - 55))"
  else
    xdotool mousemove --window "$window" 200 300 click 5 click 5
  fi
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

# Dragged onto the inactive habits' header at the end of the table, Yoga
# becomes inactive: it keeps its data and leaves the habits.
read -r inactive_x inactive_y < <(find_word yoga-closed inactive "the inactive habits end the table")
# The list may have scrolled while the details were open.
read -r yoga_x yoga_y < <(find_word yoga-closed yoga "Yoga's row is missing" "$header_y")
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
read -r row_x row_y < <(find_word deactivated-shown yoga "Yoga is not listed among the inactive habits" "$show_y")
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
# In a shorter window, a row held at the bottom edge of the table scrolls it
# down to the last habit, which is out of sight at first.
xdotool windowsize --sync "$window" 411 520 || true
sleep 1
shot row-moved
if word "$test_dir/row-moved.png" jumping >/dev/null; then
  echo "FAIL Jumping Rope is already in sight, so nothing needs to scroll ($test_dir/row-moved.png)"; exit 1
fi
read -r yoga_x yoga_y < <(find_word row-moved yoga "Yoga's row is missing")
read -r _ nav_y < <(find_word row-moved lumi "the navigation is missing")
edge_y=$((nav_y - 70))
xdotool mousemove --window "$window" "$yoga_x" "$yoga_y" mousedown 1 sleep 0.1
for step in $(seq 1 12); do
  xdotool mousemove --window "$window" "$yoga_x" "$((yoga_y + (edge_y - yoga_y) * step / 12))"
  sleep 0.025
done
sleep 1.5
# Lifted off the edge, the dragged copy no longer covers the last row.
xdotool mousemove --window "$window" "$yoga_x" "$((edge_y - 200))"
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
