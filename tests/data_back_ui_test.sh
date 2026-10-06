#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
binary=${1:-"$root/build/bin/linux/inbe-linux-x86_64"}
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS -u GDK_DISPLAY \
    YUE_DESKTOP_RECOVERY=0 timeout 60s xvfb-run -a -n 300 -s '-screen 0 1280x900x24' \
    python3 "$root/tests/data_back_ui_test.py" "$binary"
