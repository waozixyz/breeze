#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work=$root/build/metrics-zi-test
rm -rf "$work/c"
mkdir -p "$work/c"
cd "$root"
"$bin/ziran" build --project --offline ${PACKAGE_FLAGS:-} --target=c --no-main \
    --root "$root/tests" -o "$work/c" "$root/tests/metrics_link_behavior.zi"
"${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK -ffunction-sections \
    -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -I"$work/c" \
    "$root/tests/metrics_link_test.c" "$work/c"/*.c -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "Inbe text metrics Ziran/native link test passed"
