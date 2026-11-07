#!/bin/sh
set -eu

# Account import/export/migration and storage behavior, run against a real
# SQLite database in a temporary directory.
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:-"$root/build/ziran-toolchain/bin/ziran"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
kryon=${KRYON_DIR:-"$root/build/packages/kryon"}
entity=${ENTITY_DIR:-"$root/build/packages/entity"}
apps=${APPS_DIR:-"$root/build/packages/apps"}
work=$root/build/sync-account-zi-test
include=$root/build/packages/ziran/include

# Refuse unsafe fixture storage before compiling or creating any account data.
cd "$root"
if ! git check-ignore -q work/sync-account-zi-test/data; then
    echo "sync-account-zi-test: fixture data must be ignored by Git: work/sync-account-zi-test/data" >&2
    exit 1
fi

rm -rf "$work"
mkdir -p "$work/generated"
"$ziran" build --target=c --define PLATFORM_DESKTOP --root "$root/tests" \
    --module-path "$root/src" \
    --module-path "kryon=$kryon/src/ui" --module-path "kryon=$kryon/src/backend" \
    --module-path "entity=$entity/src" --module-path "apps=$apps/src" \
    --module-path "$kryon/src/ui" \
    --module-path "$root/build/packages/css/src" $(sh "$root/scripts/package-paths.sh" "$root/build/packages") \
    --module-path "$kryon/src/backend" \
    --module-path "$root/build/packages/game2d/src" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" \
    --entry sync_account_behavior:Check \
    -o "$work/generated" "$root/tests/sync_account_behavior.zi" \
    "$root/tests/sync_test_host.zi"
cat > "$work/generated/main.c" <<'C'
#include "sync_account_behavior.h"
#include <stdio.h>
int main(void)
{
    int result = Check();
    if (result != 0) fprintf(stderr, "check failed with code %d\n", result);
    return result == 0 ? 0 : 1;
}
C
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections \
    -I"$include" -I"$work/generated" -I"$root/vendor-builds/sqlite" \
    -I"$root/vendor-builds/linux/x86_64/inbe-liboqs/include" \
    "$work/generated"/*.c "$root/vendor-builds/sqlite/sqlite3.c" \
    "$root/build/packages/monocypher/src/monocypher.c" "$liboqs" \
    -Wl,--wrap=PushSyncAccount -Wl,--gc-sections -ldl -lpthread -lm -o "$work/test"
# Storage must never open the real data directory.
APP_DATA_ROOT=work/sync-account-zi-test/data
export APP_DATA_ROOT
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY "$work/test"
rm -rf "$root/work/sync-account-zi-test"
