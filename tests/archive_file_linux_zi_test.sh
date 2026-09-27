#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
standard=${2:-"$root/vendor/ziran/std"}
work=$root/build/archive-file-linux-zi-test
mkdir -p "$work/generated"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$standard" \
    -o "$work/generated" "$root/src/storage/archive_file_linux.zi"
"${CC:-cc}" -std=c11 -O0 -I"$root/vendor/ziran/include" \
    -I"$work/generated" -I"$root/vendor-builds/sqlite" \
    "$root/tests/archive_file_linux_zi_test.c" \
    "$work/generated/storage/archive_file_linux.c" \
    "$work/generated/zip.c" "$work/generated/zip_linux.c" \
    "$work/generated/zip_file_linux.c" \
    "$work/generated/mapped_file_linux.c" \
    "$work/generated/byte_text_linux.c" \
    "$work/generated/file_linux.c" "$work/generated/c_string.c" \
    "$work/generated/layout.c" "$work/generated/legacy_session_zip.c" \
    "$work/generated/legacy_session.c" "$work/generated/state.c" \
    "$work/generated/path_join.c" "$work/generated/sqlite.c" \
    "$root/vendor-builds/sqlite/sqlite3.c" \
    -lz -ldl -lpthread -lm -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
