#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/export-filename-zi-test
mkdir -p "$work/generated"
"$bin/zi2c" --no-main --root "$root/src" \
    -o "$work/generated" "$root/src/storage/export_filename.zi"
"${CC:-cc}" -std=c11 -Wall -Wextra -Werror \
    -I"$root/vendor/ziran/include" -I"$work/generated" \
    "$work/generated/storage/export_filename.c" \
    "$work/generated/layout.c" -x c - -o "$work/test" <<'EOF'
#include "storage/export_filename.h"
#include <assert.h>
#include <stdint.h>
#include <string.h>

int main(void)
{
    uint8_t name[32];
    ExportFilenameAt(1781312523, name, sizeof name);
    assert(strcmp((char *)name, "inbe-1781312523.zip") == 0);
    ExportFilenameAt(0, name, sizeof name);
    assert(strcmp((char *)name, "inbe.zip") == 0);
    ExportFilenameAt(1781312523, name, 19);
    assert(name[0] == 0);
    ExportFilenameAt(1781312523, name, 20);
    assert(strcmp((char *)name, "inbe-1781312523.zip") == 0);
    return 0;
}
EOF
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
