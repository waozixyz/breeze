#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/theme-catalog-zi-test

mkdir -p "$work/c"
"$bin/zi2c" --no-main --root "$root/tests" --module-path "$root/src" \
    --module-path "$root/vendor/ziran/std" \
    --module-path "$root/vendor/kryon/src/ui" \
    --module-path "$root/vendor/kryon/src/kss" \
    -o "$work/c" "$root/tests/theme_catalog_link_behavior.zi"
mkdir -p "$work/c/app"
cp "$work/c/assets.h" "$work/c/app/assets.h"
python3 "$root/scripts/embed-app-assets.py" "$work/assets.c" \
    "$root/themes/catalog_light.kss" "$root/themes/catalog_dark.kss"
"${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK -ffunction-sections \
    -fdata-sections -Wl,--gc-sections \
    -I"$root/vendor/ziran/include" -I"$work/c" -I"$root/src/app" \
    "$root/tests/theme_catalog_link_test.c" \
    "$work/assets.c" "$work/c"/*.c -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "Inbe theme catalog Ziran/native link test passed"
