#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work=$root/build/practice-narration-test
generated=$work/generated
mkdir -p "$generated"
cd "$root"
"$bin/ziran" build --target=c --project --offline --no-main --prune-stale --root "$root/src" -o "$generated" "$root/src/practices/practice_narration.zi"
# The link test stands in for these modules, so their headers declare the
# functions it replaces instead of defining them inline.
"${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK \
    -DZIRAN_PRACTICE_DOWNLOADS_H_SOURCE -DZIRAN_AUDIO_H_SOURCE -DZIRAN_ASSETS_H_SOURCE \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -I"$generated" \
    "$root/tests/practice_narration_link_test.c" \
    "$generated/practice_narration.c" "$generated/package_files.c" \
    "$generated/audio_policy.c" "$generated/ogg_length.c" "$generated/std_format.c" \
    "$generated/std_byte_text_linux.c" "$generated/text_buffers.c" \
    "$bin/../libziran.a" -lm -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    "$work/test" "$root/build/packages/practices/guide/voice/en/practice_guide_start.ogg"
