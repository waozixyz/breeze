#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/device-preferences-zi-test

mkdir -p "$work/c"
"$bin/zi2c" --no-main --root "$root/tests" --module-path "$root/src" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kss/src" --module-path "kryon=$root/build/packages/kryon/src/ui" \
    -o "$work/c" "$root/tests/device_preferences_link_behavior.zi"
mv "$work/c/device_host.c" "$work/c/device_host.c.skip"
mkdir -p "$work/c/app"
cp "$work/c/assets.h" "$work/c/app/assets.h"
python3 "$root/scripts/embed-app-assets.py" "$work/assets.c" \
    "$root/themes/catalog_light.kss" "$root/themes/catalog_dark.kss" \
    "$root/build/packages/kss/styles/material.kss" \
    "$root/assets/styles/inbe.kss"
"${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK -ffunction-sections \
    -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -I"$work/c" -I"$root/src/app" \
    "$root/tests/device_preferences_link_test.c" \
    "$work/assets.c" "$work/c"/*.c -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "Inbe device preferences Ziran/native link test passed"
