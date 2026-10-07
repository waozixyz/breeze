#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/android-package-assets-test
mkdir -p "$work/generated"
sh "$root/scripts/run-ziran.sh" "$bin/zi2c" --no-main --define ANDROID_BUILD \
    --root "$root" --module-path "$root/src" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/generated" "$root/tests/android_package_assets_behavior.zi"
"${CC:-cc}" -std=c11 -Wall -Wextra -Werror -Wno-unused-function \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -I"$work/generated" \
    -I"$work/generated/tests" -I"$root/src/app" \
    "$root/tests/android_package_assets_test.c" "$work/generated"/*.c \
    "$work/generated/tests"/*.c \
    -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS "$work/test"
echo "Android shared package loading, failure recovery and borrowed lifetime passed"
