#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work=$root/build/habit-days-memory-zi-test
mkdir -p "$work/c"

"$bin/ziran" build --target=c --project --offline ${PACKAGE_FLAGS:-} --no-main --root "$root/src" \
    -o "$work/c" "$root/src/habits/habit_days.zi"

"${CC:-cc}" -std=c11 -Wall -Wextra -Werror \
    -Wno-unused-function -Wno-unused-variable \
    -fsanitize=address -fno-omit-frame-pointer \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -I"$work/c" \
    "$root/tests/habit_days_memory_zi_test.c" \
    "$work/c/habit_days.c" -o "$work/test"

env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
