#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/storage-state-zi-test
mkdir -p "$work/generated"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/generated" "$root/src/storage/state.zi"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/generated" "$root/src/storage/path_join.zi"
"${CC:-cc}" -std=c11 -O0 -I"$root/src" \
    -I"$root/vendor-builds/sqlite" -I"$root/build/packages/ziran/include" \
    -I"$work/generated" "$root/tests/storage_state_zi_test.c" \
    "$work/generated/storage/state.c" \
    "$work/generated/storage/path_join.c" -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
