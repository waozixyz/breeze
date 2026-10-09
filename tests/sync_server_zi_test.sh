#!/bin/sh
set -eu

# Builds the two-client sync scenario as a Ziran program. It runs against a
# real Daochi server through scripts/sync-server-test.mjs, which needs
# DAOCHI_BIN (a built Daochi server) and node.
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:-"$root/build/ziran-toolchain/bin/ziran"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
work=${SYNC_SERVER_TEST_WORK:-$root/build/sync-server-zi-test}
include=$root/build/packages/ziran/include
# The system library, linked by name where there is no development symlink.
curl=${CURL_LIBRARY:-$(ls /usr/lib/x86_64-linux-gnu/libcurl.so.4 2>/dev/null || echo -lcurl)}

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
    --entry sync_server_behavior:Check \
    -o "$work/generated" "$root/tests/sync_server_behavior.zi" \
    "$root/tests/sync_test_host.zi"
cat > "$work/generated/main.c" <<'C'
#include <stdio.h>
#include "sync_server_behavior.h"
int main(void)
{
    int result = Check();
    if (result != 0) fprintf(stderr, "sync server check failed with code %d\n", result);
    if (result == 0) puts("PASS two-client sync, habit/session/list/alias/friend recovery, offline retry, conflict, backup restore, deletion");
    return result == 0 ? 0 : 1;
}
C
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections \
    -I"$include" -I"$work/generated" -I"$root/vendor-builds/sqlite" \
    -I"$root/vendor-builds/linux/x86_64/inbe-liboqs/include" \
    -I"$root/build/packages/monocypher/src" -I"$root/build/packages/monocypher/src/optional" \
    "$work/generated"/*.c "$root/vendor-builds/sqlite/sqlite3.c" "$liboqs" \
    "$root/build/packages/monocypher/src/monocypher.c" \
    "$root/build/packages/monocypher/src/optional/monocypher-ed25519.c" \
    -Wl,--gc-sections -ldl -lpthread -lz -lm "$curl" -o "$work/test"
echo "$work/test"
