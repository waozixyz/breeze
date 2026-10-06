#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$(mktemp -d "$root/build/graphics-transition.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
unset DISPLAY WAYLAND_DISPLAY XAUTHORITY DBUS_SESSION_BUS_ADDRESS
for target in c cpp; do
    "$bin/ziran" build --target="$target" --root "$root" \
        --module-path "$root/build/packages/kryon/src/ui" \
        --module-path "$root/build/packages/ziran/std" \
        -o "$work/$target" "$root/tests/graphics_transition_behavior.zi"
    if test "$target" = c; then
        compiler=${CC:-cc}
        standard=c11
        extension=c
    else
        compiler=${CXX:-c++}
        standard=c++17
        extension=cpp
    fi
    find "$work/$target" -name "*.$extension" -print > "$work/$target-files"
    "$compiler" -std="$standard" -O2 -ffunction-sections -fdata-sections \
        -Wl,--gc-sections -I"$work/$target" @"$work/$target-files" \
        -lm -o "$work/$target-test"
    "$work/$target-test"
done
echo 'Graphics recovery cancels borrowed, owned and lost-context route frames in C/C++'
