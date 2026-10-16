#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/practice-narration-test
generated=$work/generated
mkdir -p "$generated"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" \
    --module-path "oqs=$root/build/packages/oqs/src" \
    --module-path "$root/build/packages/kryon/src/backend" \
    -o "$generated" "$root/src/practices/practice_narration.zi"
"${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -I"$generated" \
    "$root/tests/practice_narration_link_test.c" \
    "$generated/practices/practice_narration.c" "$generated/package_files.c" \
    "$generated/audio_policy.c" "$generated/ogg_length.c" "$generated/format.c" \
    "$generated/byte_text_linux.c" "$generated/text_buffers.c" \
    "$root/build/ziran-toolchain/libziran.a" -lm -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    "$work/test" "$root/assets/practices/guide/voice/en/practice_guide_start.ogg"
