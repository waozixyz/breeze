#!/bin/sh
set -eu

# Storage import/export and migration behaviour, run against a real
# SQLite database in a temporary directory.
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:-"$root/build/packages/ziran/build/bin/ziran"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
work=$root/build/storage-sync-zi-test
include=$root/build/packages/ziran/include

# Serialize concurrent checks before replacing the stable generated output.
exec 9>"$work.lock"
flock 9

rm -rf "$work"
mkdir -p "$work/generated"
# Project mode resolves package imports through their exports (such as
# kryon/text_area for the Lumi frame), as the app build does.
"$ziran" build --project --offline --target=c --define PLATFORM_DESKTOP --root "$root" \
    --module-path "$root/tests" \
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
int main(int argc, char **argv)
{
    int result = Check(argc, (uint8_t **)argv);
    if (result != 0) fprintf(stderr, "check failed with code %d\n", result);
    return result == 0 ? 0 : 1;
}
C
# Entity records use Monocypher's XChaCha20-Poly1305, as the app does.
monocypher=$root/build/packages/monocypher/src
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections \
    -I"$include" -I"$work/generated" -I"$root/vendor-builds/sqlite" \
    -I"$root/vendor-builds/linux/x86_64/inbe-liboqs/include" \
    "$work/generated"/*.c "$root/vendor-builds/sqlite/sqlite3.c" "$monocypher/monocypher.c" "$liboqs" \
    -Wl,--wrap=sqlite3_prepare_v2 -Wl,--gc-sections -ldl -lpthread -lz -lm -o "$work/test"
# Storage must never open the real data directory.
APP_DATA_ROOT=$work/data
export APP_DATA_ROOT
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
rm -rf "$work/data"
