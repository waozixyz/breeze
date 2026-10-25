#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
binary=${1:-"$root/build/bin/linux/breeze-linux-x86_64"}
exec env -u INBE_DIARY_IMPORT -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    -u SESSION_MANAGER YUE_DESKTOP_RECOVERY=0 SDL_VIDEODRIVER=x11 LIBGL_ALWAYS_SOFTWARE=1 \
    xvfb-run -a -n 400 -s '-noreset -screen 0 1280x900x24' \
    python3 "$root/tests/apps_diary_test.py" "$binary"
