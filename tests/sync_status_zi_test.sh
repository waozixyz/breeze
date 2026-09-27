#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
include=${ZIRAN_INCLUDE:-"$root/build/packages/ziran/include"}
work=$root/build/sync-status-test

mkdir -p "$work/c/storage"
"$bin/zi2zir" --check-only --root "$root/src" \
    "$root/src/storage/sync_status.zi"
"$bin/zi2c" --no-main --root "$root/tests" \
    --module-path "$root/src" -o "$work/c" \
    "$root/tests/sync_status_link_behavior.zi"
cp "$work/c/sync_status.h" "$work/c/storage/sync_status.h"

"${CC:-cc}" -std=c11 -Wall -Wextra -Werror -DZIRAN_BOUNDS_CHECK \
    -I"$include" -I"$work/c" -I"$root/src/app" \
    -I"$root/src/storage" \
    "$root/tests/sync_status_host_test.c" \
    "$work/c/sync_status.c" \
    "$work/c/sync_status_link_behavior.c" \
    -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
