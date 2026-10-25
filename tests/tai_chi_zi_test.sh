#!/bin/sh
set -eu

# The Tai Chi course loads, and its motion, solved joints and painted
# pieces match the course studio's reference, natively.
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/tai-chi-zi-test
include=${ZIRAN_INCLUDE:-"$root/build/packages/ziran/include"}

rm -rf "$work"
mkdir -p "$work/c"
python3 - "$root" "$work" <<'PY'
from pathlib import Path
import sys
import zipfile
root, work = map(Path, sys.argv[1:])
with zipfile.ZipFile(work / 'course.zip', 'w', zipfile.ZIP_DEFLATED,
                     compresslevel=9) as archive:
    archive.writestr('course.tch', (root / 'build/packages/practices/taichi/course.tch').read_bytes())
PY
"$bin/zi2c" --no-main --root "$root/tests" --module-path "$root/src" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/c" "$root/tests/tai_chi_behavior.zi"
cat > "$work/c/main.c" <<'C'
#include <stdio.h>
#include "tai_chi_behavior.h"
int main(void)
{
    int result = Check();
    if (result != 0) fprintf(stderr, "tai chi check %d failed\n", result);
    return result == 0 ? 0 : 1;
}
C
"${CC:-cc}" -std=c11 -O2 -I"$include" -I"$work/c" "$work/c"/*.c -o "$work/test" -lm -lz
cd "$root"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "tai chi Ziran test passed"
