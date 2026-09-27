#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/storage-paths-zi-test
mkdir -p "$work/generated"

"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/vendor/ziran/std" \
    -o "$work/generated" "$root/src/storage/paths.zi"

"${CC:-cc}" -std=c11 -O0 -Wall -Wextra -Werror \
    -Wno-unused-function -Wno-unused-variable \
    -I"$root/vendor/ziran/include" -I"$work/generated" \
    "$root/tests/storage_paths_zi_test.c" \
    "$work/generated/storage/paths.c" \
    "$work/generated/byte_text_linux.c" \
    "$work/generated/c_string.c" \
    "$work/generated/file_linux.c" \
    -o "$work/test"

env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
