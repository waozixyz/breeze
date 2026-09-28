#!/bin/sh
set -eu

# The break engine scenarios as native
# code. Thousands of ticks per scenario are too many for the portable interpreter.
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/breath-rounds-zi-test
include=${ZIRAN_INCLUDE:-"$root/build/packages/ziran/include"}

rm -rf "$work"
mkdir -p "$work/c"
"$bin/zi2c" --no-main --root "$root/tests" --module-path "$root/src" --module-path "$root/build/packages/ziran/std" \
    -o "$work/c" "$root/tests/break_engine_behavior.zi"
cat > "$work/c/main.c" <<'C'
#include <stdio.h>
#include "break_engine_behavior.h"
int main(void)
{
    int result = Check();
    if (result != 0) fprintf(stderr, "break engine check %d failed\n", result);
    return result == 0 ? 0 : 1;
}
C
"${CC:-cc}" -std=c11 -I"$include" -I"$work/c" "$work/c"/*.c -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "break engine Ziran test passed"
