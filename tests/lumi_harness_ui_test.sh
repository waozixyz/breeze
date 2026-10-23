#!/bin/sh
# Runs only on a private Xvfb display with its own session bus.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
binary=${1:-"$root/build/bin/linux/breeze-linux-x86_64"}
exec env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    -u SESSION_MANAGER YUE_DESKTOP_RECOVERY=0 APP_NO_TRAY=1 SDL_VIDEODRIVER=x11 \
    LIBGL_ALWAYS_SOFTWARE=1 \
    xvfb-run -a -n 300 -s '-noreset -screen 0 2400x3200x24' \
    dbus-run-session -- python3 "$root/tests/lumi_harness_ui_test.py" "$binary"
