#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
compiler=${1:-"$root/build/ziran-toolchain/bin/ziran"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
work="$root/build/dew-test"
exec 9>"$work.lock"
flock 9
unset DISPLAY WAYLAND_DISPLAY XAUTHORITY DBUS_SESSION_BUS_ADDRESS
export YUE_DESKTOP_RECOVERY=0
rm -rf "$work/generated"
mkdir -p "$work/generated"
"$compiler" build --target=c --define PLATFORM_DESKTOP --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kss/src" --module-path "oqs=$root/build/packages/oqs/src" --module-path "qrcode=$root/build/packages/qrcode/src" \
    --module-path "kryon=$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kryon/src/backend" \
    --module-path "$root/build/packages/game2d/src" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" \
    --entry dew_behavior:Check -o "$work/generated" \
    "$root/tests/dew_behavior.zi" "$root/tests/sync_test_host.zi"
cat > "$work/generated/main.c" <<'C'
#include "dew_behavior.h"
#include "network_transport.h"

AsyncTransport __wrap_network_transport_NetworkTransport(NetworkTransfer *transfer)
{
    (void)transfer;
    return DewTestTransport();
}
int main(void)
{
    return Check() == 0 ? 0 : 1;
}
C
monocypher="$root/build/packages/monocypher/src"
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections \
    -I"$root/build/packages/ziran/include" -I"$work/generated" \
    -I"$root/vendor-builds/sqlite" -I"$root/vendor-builds/linux/x86_64/inbe-liboqs/include" \
    -I"$monocypher" -I"$monocypher/optional" \
    "$work/generated"/*.c "$root/vendor-builds/sqlite/sqlite3.c" \
    "$monocypher/monocypher.c" "$monocypher/optional/monocypher-ed25519.c" \
    "$liboqs" -Wl,--gc-sections -Wl,--wrap=network_transport_NetworkTransport \
    -ldl -lpthread -lz -lm -o "$work/test"
APP_DATA_ROOT=/tmp/inbe-dew-test/data "$work/test"
printf '%s\n' 'Dew: authenticated balance, exact units, account isolation and persistent idempotent upgrade retries passed'
