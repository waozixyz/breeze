#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work=$root/build/storage-paths-zi-test
mkdir -p "$work/generated"

"$bin/ziran" build --target=c --project --offline ${PACKAGE_FLAGS:-} --no-main --root "$root/src" \
    -o "$work/generated" "$root/src/storage/paths.zi"

"${CC:-cc}" -std=c11 -O0 -Wall -Wextra -Werror \
    -Wno-unused-function -Wno-unused-variable \
    -I"$root/build/packages/ziran/include" -I"$work/generated" \
    "$root/tests/storage_paths_zi_test.c" \
    "$work/generated/paths.c" \
    "$work/generated/std_byte_text_linux.c" \
    "$work/generated/std_c_string.c" \
    "$work/generated/std_file_linux.c" \
    -o "$work/test"

env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
