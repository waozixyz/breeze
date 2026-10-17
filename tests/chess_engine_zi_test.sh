#!/bin/sh
set -eu

# Chess rules and computer opponent as native code: perft counts of the
# standard positions, notation, draw rules and search answers.
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/chess-engine-zi-test
include=${ZIRAN_INCLUDE:-"$root/build/packages/ziran/include"}

rm -rf "$work"
mkdir -p "$work/c"
"$bin/zi2c" --no-main --root "$root/tests" --module-path "$root/build/packages/ziran/std" \
    -o "$work/c" "$root/tests/chess_engine_behavior.zi"
cat > "$work/c/main.c" <<'C'
#include <stdio.h>
#include "chess_engine_behavior.h"
int main(void)
{
    int result = Check();
    if (result != 0) fprintf(stderr, "chess engine check %d failed\n", result);
    return result == 0 ? 0 : 1;
}
C
# Modules imported by file keep their directories in the generated C.
includes=$(find "$work/c" -type d -printf ' -iquote %p')
# shellcheck disable=SC2046,SC2086
"${CC:-cc}" -std=c11 -O2 -I"$include" $includes $(find "$work/c" -name '*.c') -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "chess engine Ziran test passed"
