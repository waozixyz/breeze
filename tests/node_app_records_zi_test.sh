#!/bin/sh
set -eu

# Names of the apps the node offers, their synced keys, collections and
# shared ids, as native code.
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/node-app-records-zi-test
include=${ZIRAN_INCLUDE:-"$root/build/packages/ziran/include"}

rm -rf "$work"
mkdir -p "$work/c"
"$bin/zi2c" --no-main --root "$root/tests" --module-path "$root/build/packages/ziran/std" \
    -o "$work/c" "$root/tests/node_app_records_behavior.zi"
cat > "$work/c/main.c" <<'C'
#include <stdio.h>
#include "node_app_records_behavior.h"
int main(void)
{
    int result = Check();
    if (result != 0) fprintf(stderr, "node app records check %d failed\n", result);
    return result == 0 ? 0 : 1;
}
C
# Modules imported by file keep their directories in the generated C.
includes=$(find "$work/c" -type d -printf ' -iquote %p')
# shellcheck disable=SC2046,SC2086
"${CC:-cc}" -std=c11 -O2 -I"$include" $includes $(find "$work/c" -name '*.c') -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "node app records Ziran test passed"
