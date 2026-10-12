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
test_dir="$root/build/habits-cards-ui-test"
mkdir -p "$test_dir"
exec 9>"$test_dir/lock"
flock 9
APP_SHOT_WINDOW=1 "$binary" --screenshot "$test_dir/start.png" \
  --screenshot-scene habits_overview --screenshot-width 411 --screenshot-height 813 \
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
tap() { xdotool mousemove --window "$window" "$1" "$2" mousedown 1 sleep 0.08 mouseup 1; sleep 0.3; }
drag() {
  xdotool mousemove --window "$window" "$1" "$2" mousedown 1 sleep 0.1
  local start_y="$2" end_y="$4"
  for step in $(seq 1 12); do
    xdotool mousemove --window "$window" "$3" "$((start_y + (end_y-start_y)*step/12))"
    sleep 0.025
  done
  xdotool mouseup 1
  sleep 0.4
}
order() { sql "SELECT group_concat(name,'|') FROM (SELECT name FROM habits WHERE deleted_at=0 ORDER BY sort_order)"; }
day_count() { sql "SELECT COALESCE(SUM(completed),0) FROM habit_days WHERE habit_id=(SELECT id FROM habits WHERE name='Yoga')"; }
# The screenshot scene seeds its habits after the window and database
# appear; wait for the seed instead of assuming a fixed startup time.
baseline=""
for attempt in $(seq 1 100); do
  baseline="$(order 2>/dev/null || true)"
  if [[ -n "$baseline" ]]; then break; fi
  sleep 0.1
done
expect "$baseline" 'Meditation|Yoga|Sit ups|Push ups|Cold Shower|Jumping Rope' 'initial order'
# On a slow machine the first frame can follow the seed; capture again until
# the overview shows Yoga's controls.
for attempt in $(seq 1 20); do
  import -window "$window" "$test_dir/overview.png"
  python3 "$root/tests/habits_rendered_controls.py" "$test_dir/overview.png" day >/dev/null 2>&1 && break
  sleep 0.5
done
read -r today_x today_y < <(python3 "$root/tests/habits_rendered_controls.py" "$test_dir/overview.png" day)
read -r chevron_x chevron_y < <(python3 "$root/tests/habits_rendered_controls.py" "$test_dir/overview.png" chevron)
before="$(day_count)"
# The Yoga day row is live while the card is collapsed. Tapping it must not expand the card.
tap "$today_x" "$today_y"
expect "$(day_count)" "$((before+1))" 'collapsed today check-in'
expect "$(sql "SELECT local_date FROM habit_days WHERE habit_id=(SELECT id FROM habits WHERE name='Yoga') AND completed=1")" "$(date +%Y%m%d)" 'leftmost circle marks today'
import -window "$window" "$test_dir/collapsed-check-in.png"
python3 "$root/tests/habits_rendered_controls.py" "$test_dir/collapsed-check-in.png" day > "$test_dir/collapsed-control.txt"
tap "$today_x" "$today_y"
expect "$(day_count)" "$before" 'collapsed today undo'
# Open Yoga only through its chevron.
tap "$chevron_x" "$chevron_y"
import -window "$window" "$test_dir/yoga-expanded.png"
read -r expanded_day_x expanded_day_y < <(python3 "$root/tests/habits_rendered_controls.py" "$test_dir/yoga-expanded.png" expanded)
tap "$expanded_day_x" "$expanded_day_y"
expect "$(day_count)" "$((before+1))" 'expanded today check-in'
tap "$expanded_day_x" "$expanded_day_y"
expect "$(day_count)" "$before" 'expanded today undo'
tap "$((expanded_day_x + 50))" "$expanded_day_y"
expect "$(day_count)" "$((before+1))" 'expanded past-day check-in'
expect "$(sql "SELECT local_date FROM habit_days WHERE habit_id=(SELECT id FROM habits WHERE name='Yoga') AND completed=1")" "$(date -d yesterday +%Y%m%d)" 'second circle marks yesterday'
tap "$((expanded_day_x + 50))" "$expanded_day_y"
expect "$(day_count)" "$before" 'expanded past-day undo'
drag "$expanded_day_x" "$expanded_day_y" "$((expanded_day_x + 250))" "$expanded_day_y"
expect "$(day_count)" "$before" 'drag does not check a day'
tap "$chevron_x" "$chevron_y"
import -window "$window" "$test_dir/collapsed.png"
python3 "$root/tests/habits_rendered_controls.py" "$test_dir/collapsed.png" day > "$test_dir/collapsed-control.txt"
expect "$(order)" 'Meditation|Yoga|Sit ups|Push ups|Cold Shower|Jumping Rope' 'card order remains stable'
import -window "$window" "$test_dir/collapsed-final.png"
echo "PASS shared habit buttons: chevron expansion, day taps, undo, drag cancellation, and collapse"

# Dragged onto the inactive habits below the list, Yoga becomes inactive:
# it keeps its data and leaves the list.
word() { python3 "$root/tests/rendered_word.py" "$@"; }
deactivated() { sql "SELECT deactivated FROM habits WHERE name='Yoga'"; }
read -r yoga_x yoga_y < <(word "$test_dir/collapsed-final.png" yoga) ||
  { echo "FAIL Yoga's card is missing ($test_dir/collapsed-final.png)"; exit 1; }
read -r section_x section_y < <(word "$test_dir/collapsed-final.png" inactive) ||
  { echo "FAIL the inactive habits are not below the list ($test_dir/collapsed-final.png)"; exit 1; }
xdotool mousemove --window "$window" "$yoga_x" "$yoga_y" mousedown 1 sleep 0.1
for step in $(seq 1 12); do
  xdotool mousemove --window "$window" "$section_x" "$((yoga_y + (section_y - yoga_y) * step / 12))"
  sleep 0.025
done
sleep 0.5
import -window "$window" "$test_dir/card-over-inactive.png"
xdotool mouseup 1
sleep 0.4
expect "$(deactivated)" 1 'a card dropped on the inactive habits deactivates Yoga'
expect "$(order)" 'Meditation|Yoga|Sit ups|Push ups|Cold Shower|Jumping Rope' 'deactivating keeps the order'
import -window "$window" "$test_dir/deactivated-hidden.png"
if word "$test_dir/deactivated-hidden.png" yoga >/dev/null; then
  echo "FAIL Yoga is still in the habit list ($test_dir/deactivated-hidden.png)"; exit 1
fi
read -r show_x show_y < <(word "$test_dir/deactivated-hidden.png" inactive) ||
  { echo "FAIL no dropdown shows the inactive habits ($test_dir/deactivated-hidden.png)"; exit 1; }
tap "$show_x" "$show_y"
import -window "$window" "$test_dir/deactivated-shown.png"
# Yoga is no longer a card, so its only name on screen is its row below.
read -r row_x row_y < <(word "$test_dir/deactivated-shown.png" yoga) ||
  { echo "FAIL Yoga is not listed below the habits ($test_dir/deactivated-shown.png)"; exit 1; }
read -r first_x first_y < <(word "$test_dir/deactivated-shown.png" meditation) ||
  { echo "FAIL Meditation's card is missing ($test_dir/deactivated-shown.png)"; exit 1; }
# A tap on the row alone changes nothing.
tap "$row_x" "$row_y"
expect "$(deactivated)" 1 'a tap does not reactivate'
# Dropped on Meditation's card, Yoga becomes active in Meditation's place.
# The frame captured on the way shows the lifted row and the outlined card.
xdotool mousemove --window "$window" "$row_x" "$row_y" mousedown 1 sleep 0.1
for step in $(seq 1 12); do
  xdotool mousemove --window "$window" "$first_x"     "$((row_y + (first_y + 30 - row_y) * step / 12))"
  sleep 0.025
done
sleep 0.3
import -window "$window" "$test_dir/dragging.png"
xdotool mouseup 1
sleep 0.4
expect "$(deactivated)" 0 'drag into the list reactivates Yoga'
expect "$(order)" 'Yoga|Meditation|Sit ups|Push ups|Cold Shower|Jumping Rope' 'Yoga takes the place it was dropped on'
import -window "$window" "$test_dir/reactivated.png"
# The dropdown stays, so a card can be dragged into it again.
word "$test_dir/reactivated.png" inactive >/dev/null ||
  { echo "FAIL the inactive habits left with their last habit ($test_dir/reactivated.png)"; exit 1; }
echo "PASS habit deactivation: dragged into the inactive habits, hidden from the list, shown below it, dragged back into place"

# With a mouse, a card follows a press that moves at once and takes the
# place of the card it is dropped on.
read -r meditation_x meditation_y < <(word "$test_dir/reactivated.png" meditation) ||
  { echo "FAIL Meditation's card is missing ($test_dir/reactivated.png)"; exit 1; }
read -r push_x push_y < <(word "$test_dir/reactivated.png" push) ||
  { echo "FAIL the Push ups card is missing ($test_dir/reactivated.png)"; exit 1; }
xdotool mousemove --window "$window" "$meditation_x" "$meditation_y" mousedown 1 sleep 0.1
for step in $(seq 1 12); do
  xdotool mousemove --window "$window" "$push_x" \
    "$((meditation_y + (push_y - meditation_y) * step / 12))"
  sleep 0.025
done
sleep 0.3
import -window "$window" "$test_dir/card-dragging.png"
xdotool mouseup 1
sleep 0.4
expect "$(order)" 'Yoga|Sit ups|Push ups|Meditation|Cold Shower|Jumping Rope' 'a dragged card takes the place it was dropped on'
# Held past the bottom of the list, a dragged card scrolls the list down to
# the last card, which is out of sight at first.
import -window "$window" "$test_dir/card-moved.png"
if word "$test_dir/card-moved.png" jumping >/dev/null; then
  echo "FAIL Jumping Rope is already in sight ($test_dir/card-moved.png)"; exit 1
fi
read -r yoga_x yoga_y < <(word "$test_dir/card-moved.png" yoga) ||
  { echo "FAIL Yoga's card is missing ($test_dir/card-moved.png)"; exit 1; }
xdotool mousemove --window "$window" "$yoga_x" "$yoga_y" mousedown 1 sleep 0.1
for step in $(seq 1 12); do
  xdotool mousemove --window "$window" "$yoga_x" "$((yoga_y + (790 - yoga_y) * step / 12))"
  sleep 0.025
done
sleep 1.5
import -window "$window" "$test_dir/card-edge-scrolled.png"
read -r jump_x jump_y < <(word "$test_dir/card-edge-scrolled.png" jumping) ||
  { xdotool mouseup 1; echo "FAIL dragging past the list did not scroll it ($test_dir/card-edge-scrolled.png)"; exit 1; }
xdotool mousemove --window "$window" "$yoga_x" "$jump_y"
sleep 0.2
xdotool mouseup 1
sleep 0.4
expect "$(order)" 'Sit ups|Push ups|Meditation|Cold Shower|Jumping Rope|Yoga' 'a card dragged down the scrolled list goes last'
import -window "$window" "$test_dir/card-moved.png"
# A click without moving still opens the card.
read -r click_x click_y < <(word "$test_dir/card-moved.png" jumping) ||
  { echo "FAIL the Jumping Rope card is missing ($test_dir/card-moved.png)"; exit 1; }
tap "$click_x" "$click_y"
import -window "$window" "$test_dir/card-clicked.png"
expect "$(order)" 'Sit ups|Push ups|Meditation|Cold Shower|Jumping Rope|Yoga' 'a click does not move a card'
# Only an open card offers to complete today.
word "$test_dir/card-clicked.png" complete >/dev/null ||
  { echo "FAIL a click no longer opens the card ($test_dir/card-clicked.png)"; exit 1; }
echo "PASS habit cards: dragged into another place, scrolled at the edge, a click still opens a card"
echo "Screenshots and isolated database: $test_dir ; $db"
