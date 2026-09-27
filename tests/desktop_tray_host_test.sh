#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work="$root/build/desktop-tray-host-test"
source="$root/tests/desktop_tray_host_behavior.zi"
mkdir -p "$work/c"

"$bin/zi2zir" --check-only --define DESKTOP_TRAY_ENABLED \
    --define DESKTOP_TRAY_GTK_STATUS_ICON --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/ziran/std" "$source"
"$bin/zi2c" --define DESKTOP_TRAY_ENABLED --define DESKTOP_TRAY_GTK_STATUS_ICON \
    --entry desktop_tray_host_behavior:main --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/ziran/std" \
    -o "$work/c" "$source"
"${CC:-cc}" -std=c11 -D_DEFAULT_SOURCE -O2 -pthread \
    -I"$root/build/packages/ziran/include" -iquote "$work/c" \
    "$work/c"/*.c -ldl -o "$work/test"

env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
    -u INBE_TRAY_TEST_PRESENT "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
    INBE_TRAY_TEST_PRESENT=1 xvfb-run -a "$work/test"
printf '%s\n' 'Inbe Ziran tray lifecycle and menu ownership passed'
