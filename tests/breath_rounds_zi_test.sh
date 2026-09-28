#!/bin/sh
set -eu

# Breathing round flow (countdowns, pauses, results, completion) as native
# code. Too many steps for the portable interpreter, so this is native only.
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/breath-rounds-zi-test
include=${ZIRAN_INCLUDE:-"$root/build/packages/ziran/include"}

rm -rf "$work"
mkdir -p "$work/c"
"$bin/zi2c" --no-main --root "$root/tests" --module-path "$root/src" \
    -o "$work/c" "$root/tests/breath_rounds_behavior.zi"
cat > "$work/c/main.c" <<'C'
#include <stdio.h>
#include "breath_rounds_behavior.h"
int main(void)
{
    int result = Check();
    if (result != 0) fprintf(stderr, "breath rounds check %d failed\n", result);
    return result == 0 ? 0 : 1;
}
C
"${CC:-cc}" -std=c11 -I"$include" -I"$work/c" "$work/c"/*.c -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "breath rounds Ziran test passed"
