#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/audio-settings-test
generated=$work/generated

mkdir -p "$generated/app"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/vendor/kryon/src/ui" \
    --module-path "$root/vendor/ziran/std" \
    -o "$generated" "$root/src/app/audio_settings.zi"
cp "$generated/settings_key.h" "$generated/app/settings_key.h"
"${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/vendor/ziran/include" -I"$generated" \
    -I"$root/src/app" -I"$root/src/storage" \
    "$root/tests/audio_settings_link_test.c" \
    "$generated"/*.c "$generated/app"/*.c \
    -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "audio settings Ziran/native link test passed"
