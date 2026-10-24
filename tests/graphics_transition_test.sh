#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$(mktemp -d "$root/build/graphics-transition.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
unset DISPLAY WAYLAND_DISPLAY XAUTHORITY DBUS_SESSION_BUS_ADDRESS
"$bin/ziran" build --target=c --root "$root" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" --module-path "$root/build/packages/daochi-client" $(sh "$root/scripts/package-paths.sh" "$root/build/packages") --module-path "$root/build/packages/kryon/src/backend" \
    -o "$work/c" "$root/tests/graphics_transition_behavior.zi"
find "$work/c" -name "*.c" -print > "$work/c-files"
"${CC:-cc}" -std=c11 -O2 -ffunction-sections -fdata-sections \
    -Wl,--gc-sections -I"$work/c" @"$work/c-files" \
    -lm -o "$work/c-test"
"$work/c-test"
echo 'Graphics recovery cancels borrowed, owned and lost-context route frames in C'
