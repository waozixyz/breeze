#!/bin/sh
set -eu

# Account import/export/migration and storage behavior, run against a real
# SQLite database in a temporary directory.
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:-"$root/build/ziran-toolchain/bin/ziran"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
work=$root/build/sync-account-zi-test
include=$root/build/packages/ziran/include

rm -rf "$work"
mkdir -p "$work/generated"
"$ziran" build --target=c --define PLATFORM_DESKTOP --root "$root/tests" \
    --module-path "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kryon/src/kss" \
    --module-path "$root/build/packages/kryon/src/backend" \
    --module-path "$root/build/packages/game2d/src" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" \
    --entry sync_account_behavior:Check \
    -o "$work/generated" "$root/tests/sync_account_behavior.zi" \
    "$root/tests/sync_test_host.zi"
cat > "$work/generated/main.c" <<'C'
#include "sync_account_behavior.h"
int main(void) { return Check() == 0 ? 0 : 1; }
C
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections \
    -I"$include" -I"$work/generated" -I"$root/vendor-builds/sqlite" \
    -I"$root/vendor-builds/linux/x86_64/inbe-liboqs/include" \
    "$work/generated"/*.c "$root/vendor-builds/sqlite/sqlite3.c" "$liboqs" \
    -Wl,--gc-sections -ldl -lpthread -lm -o "$work/test"
# Storage must never open the real data directory.
APP_DATA_ROOT=/tmp/inbe-sync-account-zi-test/data
export APP_DATA_ROOT
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
rm -rf /tmp/inbe-sync-account-zi-test
