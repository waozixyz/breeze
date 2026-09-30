#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:-"$root/build/ziran-toolchain/bin/ziran"}
work=$root/build/sync-review-zi-test
include=$root/build/packages/ziran/include

rm -rf "$work"
mkdir -p "$work/generated"
"$ziran" build --target=c --root "$root/tests" \
    --module-path "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kss/src" --module-path "$root/build/packages/oqs/src" --module-path "kryon=$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kryon/src/backend" \
    --module-path "$root/build/packages/game2d/src" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" \
    --entry sync_review_behavior:Check \
    -o "$work/generated" "$root/tests/sync_review_behavior.zi"
cat > "$work/generated/main.c" <<'C'
#include "sync_review_behavior.h"
int main(void) { return Check() == 0 ? 0 : 1; }
C
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections \
    -I"$include" -I"$work/generated" -I"$root/vendor-builds/sqlite" \
    "$work/generated"/*.c "$root/vendor-builds/sqlite/sqlite3.c" \
    -Wl,--gc-sections -ldl -lpthread -lm -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
