#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/database-upgrade-zi-test
mkdir -p "$work/generated"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/generated" "$root/src/storage/database_upgrade.zi"
"${CC:-cc}" -std=c11 -O0 -I"$root/vendor-builds/sqlite" \
    -I"$root/build/packages/ziran/include" -I"$work/generated" \
    "$root/tests/database_upgrade_zi_test.c" \
    "$work/generated/c_string.c" "$work/generated/sqlite.c" \
    "$work/generated/storage/database_upgrade.c" \
    "$root/vendor-builds/sqlite/sqlite3.c" -ldl -lpthread -lm \
    -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
