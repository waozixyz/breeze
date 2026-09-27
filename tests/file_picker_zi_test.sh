#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$(mktemp -d "$root/build/file-picker-zi.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
cp "$root/tests/support/audio_picker_zenity.sh" "$work/zenity"
chmod +x "$work/zenity"
"$bin/zi2c" --no-main --define PLATFORM_DESKTOP --root "$root/tests" \
    --module-path "$root/src/platform" --module-path "$root/vendor/ziran/std" \
    -o "$work/c" "$root/tests/file_picker_behavior.zi"
"${CC:-cc}" -std=c11 -D_DEFAULT_SOURCE -O2 -DZIRAN_BOUNDS_CHECK \
    -I"$root/vendor/ziran/include" -iquote "$work/c" \
    "$work/c"/*.c -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
    PATH="$work" "$work/test"
echo "Inbe Ziran file picker test passed"
