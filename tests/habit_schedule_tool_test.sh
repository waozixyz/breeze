#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
binary=${1:-"$root/build/bin/linux/breeze-linux-x86_64"}
exec env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    -u SESSION_MANAGER YUE_DESKTOP_RECOVERY=0 LIBGL_ALWAYS_SOFTWARE=1 SDL_VIDEODRIVER=x11 \
    xvfb-run -a -n 300 -s '-noreset -screen 0 1280x1400x24' \
    python3 "$root/tests/habit_schedule_tool_test.py" "$binary"
