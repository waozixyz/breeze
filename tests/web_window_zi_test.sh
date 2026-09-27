#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$(mktemp -d "$root/build/web-window-zi.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
"$bin/zi2c" --root "$root/tests" --entry web_window_behavior:main \
    -o "$work/c" "$root/tests/web_window_behavior.zi"
"${CC:-cc}" -std=c11 -O2 -DZIRAN_BOUNDS_CHECK \
    -I"$root/vendor/ziran/include" -iquote "$work/c" \
    "$work/c"/*.c -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY "$work/test"
echo "Inbe Ziran browser viewport behavior passed"
