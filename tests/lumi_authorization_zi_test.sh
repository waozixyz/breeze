#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:-"$root/build/ziran-toolchain/bin/ziran"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
work=$root/build/lumi-authorization-test
mkdir -p "$work/generated"
"$ziran" build --target=c --define PLATFORM_DESKTOP --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kss/src" --module-path "oqs=$root/build/packages/oqs/src" \
    --module-path "kryon=$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kryon/src/backend" \
    --module-path "$root/build/packages/game2d/src" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" \
    --entry lumi_authorization_behavior:Check -o "$work/generated" \
    "$root/tests/lumi_authorization_behavior.zi" "$root/tests/sync_test_host.zi"
cat > "$work/generated/main.c" <<'C'
#include "lumi_authorization_behavior.h"
#include <stdio.h>
int main(void)
{
    int result = Check();
    if (result != 0) fprintf(stderr, "owner consent check failed: %d\n", result);
    return result == 0 ? 0 : 1;
}
C
monocypher=$root/build/packages/monocypher/src
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections \
    -I"$root/build/packages/ziran/include" -I"$work/generated" \
    -I"$root/vendor-builds/sqlite" -I"$root/vendor-builds/linux/x86_64/inbe-liboqs/include" \
    -I"$monocypher" -I"$monocypher/optional" \
    "$work/generated"/*.c "$root/vendor-builds/sqlite/sqlite3.c" \
    "$monocypher/monocypher.c" "$monocypher/optional/monocypher-ed25519.c" \
    "$liboqs" -Wl,--gc-sections -ldl -lpthread -lz -lm -o "$work/test"
APP_DATA_ROOT=/tmp/inbe-lumi-authorization-test/data \
    env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    YUE_DESKTOP_RECOVERY=0 "$work/test"
printf '%s\n' 'Lumi owner consent signature, scope, envelope, clock and cancellation checks passed'
