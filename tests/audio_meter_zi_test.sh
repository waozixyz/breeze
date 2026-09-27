#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work="$root/build/audio-meter-zi-test"
source="$root/tests/audio_meter_behavior.zi"
mkdir -p "$work/c"

"$bin/zi2zir" --check-only --define PLATFORM_DESKTOP \
    --root "$root/tests" --module-path "$root/src" \
    --module-path "$root/vendor/ziran/std" "$source"
"$bin/zi2c" --define PLATFORM_DESKTOP \
    --entry audio_meter_behavior:main --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/vendor/ziran/std" \
    -o "$work/c" "$source"
"${CC:-cc}" -std=c11 -O2 -ffunction-sections -fdata-sections \
    -Wl,--gc-sections -I"$root/vendor/ziran/include" \
    -iquote "$work/c" "$work/c"/*.c -latomic -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
    "$work/test"
echo "Inbe Ziran audio meter test passed"
