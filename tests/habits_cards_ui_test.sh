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
import -window "$window" "$test_dir/overview.png"
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
echo "Screenshots and isolated database: $test_dir ; $db"
