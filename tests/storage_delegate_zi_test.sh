#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:-"$root/build/ziran-toolchain/bin/ziran"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
work=$(mktemp -d /tmp/inbe-storage-delegate-build.XXXXXX)
trap 'rm -rf "$work"' EXIT HUP INT TERM
mkdir -p "$work/generated"
"$ziran" build --target=c --define PLATFORM_DESKTOP --root "$root/tests" \
    --module-path "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kss/src" \
    --module-path "oqs=$root/build/packages/oqs/src" \
    --module-path "kryon=$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kryon/src/backend" \
    --module-path "$root/build/packages/game2d/src" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" \
    --entry storage_delegate_behavior:Check \
    -o "$work/generated" "$root/tests/storage_delegate_behavior.zi" \
    "$root/tests/sync_test_host.zi"
cat > "$work/generated/main.c" <<'C'
#include "storage_delegate_behavior.h"
#include <stdio.h>
int main(void)
{
    int result = Check();
    if (result != 0) fprintf(stderr, "delegate storage check failed: %d\n", result);
    return result == 0 ? 0 : 1;
}
C
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections \
    -I"$root/build/packages/ziran/include" -I"$work/generated" \
    -I"$root/vendor-builds/sqlite" \
    -I"$root/vendor-builds/linux/x86_64/inbe-liboqs/include" \
    "$work/generated"/*.c "$root/vendor-builds/sqlite/sqlite3.c" "$liboqs" \
    -Wl,--gc-sections -ldl -lpthread -lz -lm -o "$work/test"
APP_DATA_ROOT=/tmp/inbe-storage-delegate-zi-test/data \
    env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    YUE_DESKTOP_RECOVERY=0 "$work/test"
