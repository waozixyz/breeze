#!/usr/bin/env bash
set -euo pipefail
# Runs habit_day_ui_test.py on its own private Xvfb display; screenshot
# mode seeds its own temporary database.
if [[ -z "${INBE_UI_TEST_XVFB:-}" ]]; then
  exec env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY -u SESSION_MANAGER \
    -u DBUS_SESSION_BUS_ADDRESS YUE_DESKTOP_RECOVERY=0 xvfb-run -a -s '-noreset -screen 0 1280x1024x24' \
    env -u WAYLAND_DISPLAY -u SESSION_MANAGER -u DBUS_SESSION_BUS_ADDRESS \
    SDL_VIDEODRIVER=x11 INBE_UI_TEST_XVFB=1 bash "$0" "$@"
fi
binary="${1:?native binary required}"
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
test_dir="$root/build/habit-day-ui-test"
mkdir -p "$test_dir"
exec 9>"$test_dir/lock"
flock 9
exec python3 "$root/tests/habit_day_ui_test.py" "$binary"
