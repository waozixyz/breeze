#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/fonts-zi-test

mkdir -p "$work/c"
"$bin/zi2c" --no-main --root "$root/tests" --module-path "$root/src" \
    --module-path "$root/vendor/ziran/std" \
    --module-path "$root/vendor/kryon/src/ui" \
    -o "$work/c" "$root/tests/fonts_link_behavior.zi"
mkdir -p "$work/c/app"
cp "$work/c/assets.h" "$work/c/app/assets.h"
python3 "$root/scripts/embed-app-assets.py" "$work/assets.c" \
    "$root/assets/fonts/subset/NotoSans-App-Regular.ttf" \
    "$root/assets/fonts/subset/NotoSansJP-App-Regular.otf" \
    "$root/assets/fonts/subset/NotoSansKR-App-Regular.otf" \
    "$root/assets/fonts/subset/NotoSansSC-App-Regular.otf"
"${CC:-cc}" -std=c11 -O1 -DZIRAN_BOUNDS_CHECK -ffunction-sections \
    -fdata-sections -Wl,--gc-sections \
    -I"$root/vendor/ziran/include" -I"$work/c" -I"$root/src/app" \
    "$root/tests/fonts_link_test.c" \
    "$work/assets.c" "$work/c"/*.c -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "Inbe locale fonts Ziran/native link test passed"
