#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
binary=${1:-"$root/build/bin/linux/inbe-linux-x86_64"}
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY -u DBUS_SESSION_BUS_ADDRESS YUE_DESKTOP_RECOVERY=0 \
    timeout 30s xvfb-run -a -n 302 -s '-screen 0 1280x900x24' \
    python3 "$root/tests/customize_nav_ui_test.py" "$binary"
if [ "${INBE_TEST_NARROW:-0}" != 1 ]; then
    env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
        -u DBUS_SESSION_BUS_ADDRESS YUE_DESKTOP_RECOVERY=0 \
        python3 "$root/tests/settings_sidebar_ui_test.py" "$binary"
fi
