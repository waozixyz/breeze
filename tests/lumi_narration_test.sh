#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/lumi-narration-test
generated=$work/generated
mkdir -p "$generated"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" \
    $(sh "$root/scripts/package-paths.sh" "$root/build/packages") \
    --module-path "$root/build/packages/kryon/src/backend" \
    -o "$generated" "$root/src/app/lumi_guide.zi"
# The link test stands in for these modules, so their headers declare the
# functions it replaces instead of defining them inline.
"${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK \
    -DZIRAN_PRACTICE_DOWNLOADS_H_SOURCE -DZIRAN_AUDIO_H_SOURCE -DZIRAN_ASSETS_H_SOURCE \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -I"$generated" \
    "$root/tests/lumi_narration_link_test.c" \
    "$generated/app/lumi_guide.c" "$generated/audio_policy.c" \
    "$generated/byte_text_linux.c" \
    -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "Lumi narration playback and mute tests passed"
