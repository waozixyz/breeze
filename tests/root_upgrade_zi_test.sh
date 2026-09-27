#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/root-upgrade-zi-test
mkdir -p "$work/generated"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/generated" "$root/src/storage/root_upgrade.zi"
"${CC:-cc}" -std=c11 -O0 -I"$root/build/packages/ziran/include" \
    -I"$work/generated" "$root/tests/root_upgrade_zi_test.c" \
    "$work/generated/storage/root_upgrade.c" -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
