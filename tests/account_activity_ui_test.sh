#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
binary=${1:-"$root/build/bin/linux/inbe-linux-x86_64"}
fixture=${2:-"$root/build/account-activity-test/test"}
exec env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    -u SESSION_MANAGER YUE_DESKTOP_RECOVERY=0 xvfb-run -a --server-num=300 -e /dev/stderr \
    -s '-screen 0 1280x1000x24' env INBE_ACTIVITY_PRIVATE_DISPLAY=1 \
    python3 "$root/tests/account_activity_ui_test.py" "$binary" "$fixture"
