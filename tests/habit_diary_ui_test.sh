#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
binary=${1:?native test-driver binary required}
mkdir -p "$root/build/habit-diary-ui-test"
exec 9>"$root/build/habit-diary-ui-test/lock"
flock 9
exec env -u DISPLAY -u WAYLAND_DISPLAY -u WAYLAND_SOCKET -u XAUTHORITY \
    -u GDK_DISPLAY -u SESSION_MANAGER -u DBUS_SESSION_BUS_ADDRESS \
    HARMONY_DESKTOP_RECOVERY=0 YUE_DESKTOP_RECOVERY=0 \
    xvfb-run -a -s '-noreset -screen 0 1280x1024x24' \
    python3 "$root/tests/habit_diary_ui_test.py" "$binary"
