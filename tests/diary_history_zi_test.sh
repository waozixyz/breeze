#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/diary-history-test
include=${ZIRAN_INCLUDE:-"$root/build/packages/ziran/include"}

rm -rf "$work"
mkdir -p "$work/c"
"$bin/zi2c" --no-main --root "$root/tests" --module-path "$root/src" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/c" "$root/tests/diary_history_behavior.zi"
cat > "$work/c/main.c" <<'C'
#include <stdio.h>
#include "diary_history_behavior.h"
int main(void)
{
    int result = Answer();
    if (result != 42) {
        fprintf(stderr, "diary history check %d failed\n", result);
        return 1;
    }
    return 0;
}
C
"${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK -fsanitize=address,undefined \
    -I"$include" -I"$work/c" "$work/c"/*.c -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
printf '%s\n' 'Diary undo and redo: typing steps, separate corrections, redo reset, depth limit, day change and UTF-8 edits passed'
