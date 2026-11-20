#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work=$root/build/audio-settings-test
generated=$work/generated

rm -rf "$generated"
mkdir -p "$generated"
cd "$root"
"$bin/ziran" build --project ${PACKAGE_FLAGS:---offline} --target=c --no-main \
    --root "$root/src" -o "$generated" "$root/src/app/audio_settings.zi"
"${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -I"$generated" \
    -I"$root/src/app" -I"$root/src/storage" \
    "$root/tests/audio_settings_link_test.c" \
    "$generated"/*.c \
    -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "audio settings Ziran/native link test passed"
