#!/bin/sh
set -eu

# A profile Inbe 2.1.43 left upgrades: its photos move to the account's
# entity data against nodes the test answers from memory, on a real SQLite
# database in this build's own directory.
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:-"$root/build/ziran-toolchain/bin/ziran"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
work=$root/build/entity-photos-zi-test
include=$root/build/packages/ziran/include
monocypher=$root/build/packages/monocypher/src

exec 9>"$work.lock"
flock 9

rm -rf "$work"
mkdir -p "$work/generated" "$work/data"
"$ziran" build --target=c --define PLATFORM_DESKTOP --root "$root/tests" \
    --module-path "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kss/src" $(sh "$root/scripts/package-paths.sh" "$root/build/packages") \
    --module-path "$root/build/packages/kryon/src/backend" \
    --module-path "$root/build/packages/game2d/src" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" \
    --entry entity_photos_behavior:Check \
    -o "$work/generated" "$root/tests/entity_photos_behavior.zi" \
    "$root/tests/sync_test_host.zi"
cat > "$work/generated/main.c" <<'C'
#include "entity_photos_behavior.h"
#include <stdio.h>
/* Files are flushed by the browser's storage only on the web. */
void app_web_storage_flush(void) {}
int main(void)
{
    int result = Check();
    if (result != 0) fprintf(stderr, "entity photos check failed with code %d\n", result);
    return result == 0 ? 0 : 1;
}
C
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections \
    -I"$include" -I"$work/generated" -I"$root/vendor-builds/sqlite" \
    -I"$root/vendor-builds/linux/x86_64/inbe-liboqs/include" \
    "$work/generated"/*.c "$root/vendor-builds/sqlite/sqlite3.c" "$monocypher/monocypher.c" "$liboqs" \
    -Wl,--gc-sections -ldl -lpthread -lz -lm -o "$work/test"
APP_DATA_ROOT=$work/data
ENTITY_PHOTOS_FIXTURE=$root/tests/fixtures/photos-2.1.43.sql
export APP_DATA_ROOT ENTITY_PHOTOS_FIXTURE
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
rm -rf "$work/data"
echo "Photos of a 2.1.43 profile moved to the account's entity data without losing any"
