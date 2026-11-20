#!/bin/sh
set -eu

# Account import/export/migration and storage behavior, run against a real
# SQLite database in a temporary directory.
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:-"$root/build/packages/ziran/build/bin/ziran"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
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
"$ziran" build --project --offline ${PACKAGE_FLAGS:-} --target=c \
    --define PLATFORM_DESKTOP --root "$root/tests" \
    --entry sync_account_behavior:Check \
    -o "$work/generated" "$root/tests/sync_account_behavior.zi" \
    "$root/tests/sync_test_host.zi"
cat > "$work/generated/main.c" <<'C'
#include "sync_account_behavior.h"
#include <stdio.h>
#include <stdlib.h>

/* Sync account fixtures never measure or decode a rendered image. */
int32_t ImageWidth(String path)
{
    (void)path;
    abort();
}

int32_t ImageHeight(String path)
{
    (void)path;
    abort();
}

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
