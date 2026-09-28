#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
binary=${1:-"$root/build/bin/linux/inbe-linux-x86_64"}
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
    timeout 90s xvfb-run -a -n 300 -s '-screen 0 1280x900x24' \
    python3 "$root/tests/native_zoom_test.py" "$binary"
