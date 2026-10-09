#!/bin/sh
set -eu

# Storage import/export and migration behaviour, run against a real
# SQLite database in a temporary directory.
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:-"$root/build/ziran-toolchain/bin/ziran"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
work=$root/build/storage-sync-zi-test
include=$root/build/packages/ziran/include

# Serialize concurrent checks before replacing the stable generated output.
exec 9>"$work.lock"
flock 9

rm -rf "$work"
mkdir -p "$work/generated"
"$ziran" build --target=c --define PLATFORM_DESKTOP --root "$root/tests" \
    --module-path "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kss/src" --module-path "oqs=$root/build/packages/oqs/src" --module-path "kryon=$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kryon/src/backend" \
    --module-path "$root/build/packages/game2d/src" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" \
    --entry storage_sync_behavior:Check \
    -o "$work/generated" "$root/tests/storage_sync_behavior.zi" \
    "$root/tests/sync_test_host.zi"
cat > "$work/generated/review_failure.c" <<'C'
#include <sqlite3.h>
#include <string.h>
static int review_field_failure;
void ReviewFieldFailure(int enabled) { review_field_failure = enabled; }
int __real_sqlite3_prepare_v2(sqlite3 *, const char *, int, sqlite3_stmt **, const char **);
int __wrap_sqlite3_prepare_v2(sqlite3 *db, const char *sql, int size,
                            sqlite3_stmt **statement, const char **tail)
{
    if (review_field_failure && strstr(sql, "SELECT k.key,COALESCE(CAST") != NULL) {
        *statement = NULL;
        return SQLITE_AUTH;
    }
    return __real_sqlite3_prepare_v2(db, sql, size, statement, tail);
}
C
cat > "$work/generated/main.c" <<'C'
#include "storage_sync_behavior.h"
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
    "$work/generated"/*.c "$root/vendor-builds/sqlite/sqlite3.c" "$liboqs" \
    -Wl,--wrap=sqlite3_prepare_v2 -Wl,--gc-sections -ldl -lpthread -lz -lm -o "$work/test"
# Storage must never open the real data directory.
APP_DATA_ROOT=/tmp/inbe-storage-sync-zi-test/data
export APP_DATA_ROOT
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
rm -rf /tmp/inbe-storage-sync-zi-test
