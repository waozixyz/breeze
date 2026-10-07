#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/audio-first-cue
generated=$work/generated
mkdir -p "$generated"
"$bin/ziran" build --target=c --define PLATFORM_DESKTOP --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kryon/src/backend" --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" --module-path "$root/build/packages/kss/src" \
    --module-path "$root/build/packages/game2d/src" --module-path "kryon=$root/build/packages/kryon/src/ui" \
    --module-path "oqs=$root/build/packages/oqs/src" -o "$generated" "$root/tests/audio_first_cue_test.zi"
python3 "$root/scripts/embed-app-assets.py" "$work/assets.c" \
    "$root/assets/sounds/bell.ogg" "$root/assets/sounds/breath-in.ogg" "$root/assets/sounds/breath-out.ogg"
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections \
    -I"$root/build/packages/ziran/include" -I"$generated" -I"$root/src/app" \
    "$generated"/*.c "$work/assets.c" "$root/tests/audio_first_cue_host.c" \
    -Wl,--gc-sections -lm -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS "$work/test"
echo 'First bell and breath cues initialize audio and play on the first request'
