#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work=$root/build/fonts-zi-test

rm -rf "$work/c"
mkdir -p "$work/c"
"$bin/ziran" build --target=c --project --offline ${PACKAGE_FLAGS:-} --no-main --root "$root/tests"  \
    -o "$work/c" "$root/tests/fonts_link_behavior.zi"
mkdir -p "$work/c/app"
cp "$work/c/assets.h" "$work/c/app/assets.h"
set -- "$work/c"/*_typeface_source.h
test "$#" -eq 1
test -f "$1"
python3 "$root/scripts/embed-app-assets.py" "$work/assets.c" \
    "$root/assets/fonts/subset/NotoSans-App-Regular.ttf" \
    "$root/assets/fonts/subset/NotoSansJP-App-Regular.otf" \
    "$root/assets/fonts/subset/NotoSansKR-App-Regular.otf" \
    "$root/assets/fonts/subset/NotoSansSC-App-Regular.otf"
"${CC:-cc}" -std=c11 -O1 -DZIRAN_BOUNDS_CHECK -ffunction-sections \
    -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -I"$work/c" -I"$root/src/app" \
    -include "$1" "$root/tests/fonts_link_test.c" \
    "$work/assets.c" "$work/c"/*.c -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "Inbe locale fonts Ziran/native link test passed"
