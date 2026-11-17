#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
standard=${2:-"$root/build/packages/ziran/std"}
work=$root/build/archive-file-linux-zi-test
rm -rf "$work/generated"
mkdir -p "$work/generated"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$standard" \
    -o "$work/generated" "$root/src/storage/archive_file_linux.zi"
generated_sources=$(find "$work/generated" -name '*.c' | sort)
"${CC:-cc}" -std=c11 -O0 -I"$root/build/packages/ziran/include" \
    -I"$work/generated" -I"$root/vendor-builds/sqlite" \
    "$root/tests/archive_file_linux_zi_test.c" \
    $generated_sources \
    "$root/vendor-builds/sqlite/sqlite3.c" \
    -lz -ldl -lpthread -lm -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
