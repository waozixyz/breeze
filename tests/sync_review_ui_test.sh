#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
binary=${1:-"$root/build/bin/linux/inbe-linux-x86_64"}
exec env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    -u SESSION_MANAGER YUE_DESKTOP_RECOVERY=0 xvfb-run -a -e /dev/stderr \
    -s '-screen 0 1280x1000x24' env INBE_REVIEW_PRIVATE_DISPLAY=1 \
    python3 "$root/tests/sync_review_ui_test.py" "$binary"
