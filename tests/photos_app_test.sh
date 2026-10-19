#!/bin/sh
set -eu

# Photos from its real package through the real node-app host and media
# library on a real database (tests/photos_app_behavior.zi).
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:-"$root/build/ziran-toolchain/bin/ziran"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
packages=${INBE_PACKAGES:-"$root/build/packages"}
work=$root/build/photos-app-test
include=$packages/ziran/include
curl=${CURL_LIBRARY:-$(ls /usr/lib/x86_64-linux-gnu/libcurl.so.4 2>/dev/null || echo -lcurl)}
unset DISPLAY WAYLAND_DISPLAY XAUTHORITY DBUS_SESSION_BUS_ADDRESS

exec 9>"$work.lock"
flock 9

rm -rf "$work"
mkdir -p "$work/generated"
"$ziran" bundle --root "$root" --module-path "$root/src" $(sh "$root/scripts/package-paths.sh" "$packages") \
    --module-path "$packages/kryon/src/ui" --module-path "$packages/ziran/std" \
    --define KRYON_HOSTED_UI --entry photos:Main -o "$work/photos.zib" "$root/apps/photos/photos.zi"
"$ziran" build --target=c --define PLATFORM_DESKTOP --root "$root/tests" \
    --module-path "$root/src" \
    --module-path "$packages/kryon/src/ui" \
    --module-path "$packages/kss/src" $(sh "$root/scripts/package-paths.sh" "$packages") \
    --module-path "$packages/kryon/src/backend" \
    --module-path "$packages/game2d/src" \
    --module-path "$packages/ziran/std" \
    --module-path "$packages/daochi-client" \
    --entry photos_app_behavior:Check \
    -o "$work/generated" "$root/tests/photos_app_behavior.zi" \
    "$root/tests/sync_test_host.zi"
cat > "$work/generated/main.c" <<'C'
#include "photos_app_behavior.h"
#include <stdio.h>
/* Files are flushed by the browser's storage only on the web. */
void app_web_storage_flush(void) {}
int main(void)
{
    int result = Check();
    if (result != 0) fprintf(stderr, "photos app check failed with code %d\n", result);
    return result == 0 ? 0 : 1;
}
C
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections \
    -I"$include" -I"$work/generated" -I"$root/vendor-builds/sqlite" \
    -I"$root/vendor-builds/linux/x86_64/inbe-liboqs/include" \
    -I"$packages/monocypher/src" -I"$packages/monocypher/src/optional" -I"$packages/raylib/src" \
    "$work/generated"/*.c "$root/tests/node_app_audio_host.c" "$root/vendor-builds/sqlite/sqlite3.c" "$liboqs" \
    "$packages/monocypher/src/monocypher.c" "$packages/monocypher/src/optional/monocypher-ed25519.c" \
    "${ZIRAN_LIB:-$root/build/ziran-toolchain/libziran.a}" \
    -Wl,--gc-sections -ldl -lpthread -lz -lm "$curl" -o "$work/test"
APP_DATA_ROOT=/tmp/inbe-photos-app-test/data
export APP_DATA_ROOT
INBE_NODE_APP_FILE=$work/photos.zib "$work/test"
rm -rf /tmp/inbe-photos-app-test
echo "Photos adds, shows, opens, trashes and restores photos through the node-app host and the media library"
