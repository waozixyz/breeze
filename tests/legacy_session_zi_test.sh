#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work=$root/build/legacy-session-zi-test
mkdir -p "$work/generated"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/generated" "$root/src/storage/legacy_session.zi" \
    "$root/src/storage/legacy_session_files.zi" "$root/src/storage/legacy_session_time.zi" \
    "$root/src/storage/legacy_session_zip.zi"
"${CC:-cc}" -std=c11 -O0 -I"$root/build/packages/ziran/include" \
    -I"$work/generated" "$root/tests/legacy_session_zi_test.c" \
    $(find "$work/generated" -type f -name '*.c') \
    -lz -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
