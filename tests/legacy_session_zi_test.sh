#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/legacy-session-zi-test
mkdir -p "$work/generated"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/generated" "$root/src/storage/legacy_session.zi"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/generated" "$root/src/storage/legacy_session_files.zi"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/generated" "$root/src/storage/legacy_session_time.zi"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/generated" "$root/src/storage/legacy_session_zip.zi"
"${CC:-cc}" -std=c11 -O0 -I"$root/build/packages/ziran/include" \
    -I"$work/generated" "$root/tests/legacy_session_zi_test.c" \
    "$work/generated/c_string.c" \
    "$work/generated/storage/legacy_session.c" \
    "$work/generated/storage/legacy_session_files.c" \
    "$work/generated/storage/legacy_session_time.c" \
    "$work/generated/storage/legacy_session_zip.c" \
    "$work/generated/zip.c" "$work/generated/zip_linux.c" \
    "$work/generated/file_linux.c" \
    -lz -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
