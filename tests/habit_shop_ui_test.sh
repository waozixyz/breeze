#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS -u GDK_DISPLAY \
    -u SESSION_MANAGER YUE_DESKTOP_RECOVERY=0 SDL_AUDIODRIVER=dummy INBE_UI_TEST_XVFB=1 \
    timeout 240s xvfb-run -a -n 311 -s '-screen 0 1280x1000x24' \
    python3 "$root/tests/habit_shop_ui_test.py" "${1:?native binary required}"
