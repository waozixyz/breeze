#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work=$root/build/theme-catalog-zi-test

rm -rf "$work/c"
mkdir -p "$work/c"
"$bin/ziran" build --target=c --project --offline ${PACKAGE_FLAGS:-} --no-main --root "$root/tests"  \
    -o "$work/c" "$root/tests/theme_catalog_link_behavior.zi"
mkdir -p "$work/c/app"
cp "$work/c/assets.h" "$work/c/app/assets.h"
python3 "$root/scripts/embed-app-assets.py" "$work/assets.c" \
    "$root/themes/catalog_light.css" "$root/themes/catalog_dark.css"
"${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK -ffunction-sections \
    -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -I"$work/c" -I"$root/src/app" \
    "$root/tests/theme_catalog_link_test.c" \
    "$work/assets.c" "$work/c"/*.c -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "Inbe theme catalog Ziran/native link test passed"
