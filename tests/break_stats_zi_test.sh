#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/break-stats-zi-test
mkdir -p "$work/c"
"$bin/zi2zir" --check-only --root "$root/src" \
    --module-path "$root/vendor/ziran/std" \
    "$root/src/storage/break_stats.zi"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/vendor/ziran/std" \
    -o "$work/c" "$root/src/storage/break_stats.zi"
"${CC:-cc}" -std=c11 -Wall -Wextra -Werror -Wno-unused-function \
    -I"$root/vendor/ziran/include" -I"$root/vendor-builds/sqlite" \
    -I"$root/src/storage" -I"$work/c" \
    "$root/tests/break_stats_link_test.c" \
    "$work/c/date_time.c" "$work/c/break_types.c" \
    "$work/c/break_calendar.c" \
    "$work/c/storage/break_stats.c" "$work/c/state.c" \
    "$work/c/sqlite.c" "$work/c/c_string.c" \
    "$root/vendor-builds/sqlite/sqlite3.c" \
    -lm -ldl -lpthread -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
