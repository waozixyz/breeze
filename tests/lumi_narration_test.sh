#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work=$root/build/lumi-narration-test
generated=$work/generated
mkdir -p "$generated"
"$bin/ziran" build --target=c --project --offline ${PACKAGE_FLAGS:-} --no-main --root "$root/src" \
    -o "$generated" "$root/src/app/lumi_guide.zi"
# The link test stands in for these modules, so their headers declare the
# functions it replaces instead of defining them inline.
"${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK \
    -DZIRAN_PRACTICE_DOWNLOADS_H_SOURCE -DZIRAN_AUDIO_H_SOURCE -DZIRAN_ASSETS_H_SOURCE \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -I"$generated" \
    "$root/tests/lumi_narration_link_test.c" \
    "$generated/lumi_guide.c" "$generated/host_clock.c" "$generated/audio_policy.c" \
    "$generated/std_byte_text_linux.c" \
    -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "Lumi narration playback and mute tests passed"
