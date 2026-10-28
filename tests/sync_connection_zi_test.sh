#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
compiler=${1:-"$root/build/ziran-toolchain/bin/ziran"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
work=$root/build/sync-connection-test
exec 9>"$work.lock"
flock 9
data=$(mktemp -d /tmp/inbe-sync-connection.XXXXXX)
trap 'rm -rf "$data"' EXIT HUP INT TERM
unset DISPLAY WAYLAND_DISPLAY XAUTHORITY DBUS_SESSION_BUS_ADDRESS
export YUE_DESKTOP_RECOVERY=0
rm -rf "$work"
mkdir -p "$work/generated"
"$compiler" build --target=c --define PLATFORM_DESKTOP --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kryon/src/backend" \
    $(sh "$root/scripts/package-paths.sh" "$root/build/packages") \
    --module-path "$root/build/packages/kss/src" \
    --module-path "$root/build/packages/game2d/src" --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" --entry sync_connection_behavior:Check \
    -o "$work/generated" "$root/tests/sync_connection_behavior.zi" "$root/tests/sync_test_host.zi"
cat > "$work/generated/main.c" <<'C'
#include "sync_connection_behavior.h"
#include <stdint.h>
#include <stdio.h>
static int requests;
int32_t ConnectionRequests(void) { return requests; }
int32_t app_request_sync(void *app) { (void)app; requests++; return 1; }
void app_reload_after_import(void *app, int32_t settings) { (void)app; (void)settings; }
int32_t app_web_storage_flush_critical(int32_t timeout_ms, int32_t log_success) {
    (void)timeout_ms; (void)log_success; return 1;
}
int main(void) {
    int result = Check();
    if (result) fprintf(stderr, "Sync connection checks failed: %d\n", result);
    return result ? 1 : 0;
}
C
monocypher=$root/build/packages/monocypher/src
"${CC:-cc}" -std=c11 -O1 -ffunction-sections -fdata-sections \
    -I"$root/build/packages/ziran/include" -I"$work/generated" \
    -I"$root/vendor-builds/sqlite" -I"$root/vendor-builds/linux/x86_64/inbe-liboqs/include" \
    -I"$monocypher" -I"$monocypher/optional" \
    "$work/generated"/*.c "$root/vendor-builds/sqlite/sqlite3.c" \
    "$monocypher/monocypher.c" "$monocypher/optional/monocypher-ed25519.c" "$liboqs" \
    -Wl,--gc-sections -ldl -lpthread -lz -lm -l:libcurl.so.4 -o "$work/test"
APP_DATA_ROOT="$data" "$work/test"
printf '%s\n' 'Connecting enables and dispatches sync using the displayed node'
