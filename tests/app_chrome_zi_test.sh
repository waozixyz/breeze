#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/title-bars-zi-test
rm -rf "$work/c"
mkdir -p "$work/c"
"$bin/zi2zir" --check-only --root "$root/src" \
    --module-path "$root/vendor/kryon/src/ui" \
    --module-path "$root/vendor/ziran/std" \
    "$root/src/app/app_chrome.zi"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/vendor/kryon/src/ui" \
    --module-path "$root/vendor/ziran/std" \
    -o "$work/c" "$root/src/app/app_chrome.zi"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/vendor/kryon/src/ui" \
    --module-path "$root/vendor/ziran/std" \
    -o "$work/c" "$root/src/app/practice_title_bar.zi"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/vendor/kryon/src/ui" \
    --module-path "$root/vendor/ziran/std" \
    -o "$work/c" "$root/src/app/assets.zi"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/vendor/kryon/src/ui" \
    --module-path "$root/vendor/ziran/std" \
    -o "$work/c" "$root/src/app/image_dimensions.zi"
python3 "$root/scripts/embed-app-assets.py" "$work/assets.c" \
    "$root/vendor/kryon/icons/ui.png"
set -- "$root/tests/app_chrome_link_test.c" \
    "$work/assets.c"
for generated in "$work/c"/*.c "$work/c/app"/*.c; do
    case "$generated" in
        "$work/c/app/assets.c") ;;
        *) set -- "$@" "$generated" ;;
    esac
done
"${CC:-cc}" -std=c11 -ffunction-sections -fdata-sections \
    -Dimage_dimensions_ImageWidth=ImageWidth \
    -Dimage_dimensions_ImageHeight=ImageHeight \
    -Wl,--gc-sections -I"$root/vendor/ziran/include" -I"$work/c" \
    -I"$root/src/app" \
    "$@" -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "Inbe title bar Ziran/native link test passed"
