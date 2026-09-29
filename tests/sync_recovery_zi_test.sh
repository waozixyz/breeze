#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/sync-recovery-zi-test

rm -rf "$work"
mkdir -p "$work/c"
"$bin/zi2c" --no-main --root "$root/tests" --module-path "$root/src" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kryon/src/kss" \
    --module-path "$root/build/packages/kryon/src/backend" \
    --module-path "$root/build/packages/game2d/src" \
    --module-path "$root/build/packages/daochi-client" \
    -o "$work/c" "$root/tests/sync_recovery_behavior.zi"
"${CC:-cc}" -std=gnu11 -w -DZIRAN_BOUNDS_CHECK -ffunction-sections \
    -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -iquote "$work/c" \
    "$root/tests/sync_recovery_link_test.c" $(ls "$work/c"/*.c | grep -v '/storage_core.c$') \
    -lpthread -lm -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "sync recovery Ziran/native test passed"
