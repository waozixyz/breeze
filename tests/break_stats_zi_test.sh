#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work=$root/build/break-stats-zi-test
rm -rf "$work/c"
mkdir -p "$work/c"
"$bin/zi2zir" --check-only --root "$root/src" \
    --module-path "$root/build/packages/ziran/std" \
    "$root/src/storage/break_stats.zi"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/c" "$root/src/storage/break_stats.zi"
generated_sources=$(find "$work/c" -name '*.c' | sort)
"${CC:-cc}" -std=c11 -Wall -Wextra -Werror -Wno-unused-function \
    -I"$root/build/packages/ziran/include" -I"$root/vendor-builds/sqlite" \
    -I"$root/src/storage" -I"$work/c" \
    "$root/tests/break_stats_link_test.c" \
    $generated_sources \
    "$root/vendor-builds/sqlite/sqlite3.c" \
    -lm -ldl -lpthread -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
