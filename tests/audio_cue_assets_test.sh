#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work=$root/build/audio-cue-assets
generated=$work/generated
rm -rf "$generated"
mkdir -p "$generated"
"$bin/ziran" build --project --offline ${PACKAGE_FLAGS:-} --target=c --define PLATFORM_WEB --root "$root/tests" \
    -o "$generated" "$root/tests/audio_cue_assets_test.zi"
# No embedded sounds: the cues come only from the Practices package.
python3 "$root/scripts/embed-app-assets.py" "$work/assets.c"
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections \
    -I"$root/build/packages/ziran/include" -I"$generated" -I"$root/src/app" \
    "$generated"/*.c "$work/assets.c" "$root/tests/audio_first_cue_host.c" \
    -Wl,--gc-sections -lm -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS "$work/test"
echo 'Cue sounds load when wanted and again once Practices finishes opening'
