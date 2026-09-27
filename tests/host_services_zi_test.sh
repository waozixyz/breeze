#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/host-services-zi-test
mkdir -p "$work/c"
"$bin/zi2c" --root "$root/tests" --module-path "$root/src" \
    --module-path "$root/vendor/ziran/std" \
    --entry host_services_behavior:main -o "$work/c" \
    "$root/tests/host_services_behavior.zi"
"${CC:-cc}" -std=c11 -O2 -DZIRAN_BOUNDS_CHECK \
    -I"$root/vendor/ziran/include" -iquote "$work/c" \
    "$work/c"/*.c -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
    "$work/test" 2> "$work/stderr"
test "$(cat "$work/stderr")" = "INFO: host test"
echo "Inbe Ziran process services test passed"
