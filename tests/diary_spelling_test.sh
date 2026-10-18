#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
compiler=${1:-"$root/build/ziran-toolchain/bin/ziran"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
work="$root/build/diary-spelling-test"
exec 9>"$work.lock"
flock 9
unset DISPLAY WAYLAND_DISPLAY XAUTHORITY DBUS_SESSION_BUS_ADDRESS
export YUE_DESKTOP_RECOVERY=0
rm -rf "$work/generated"
mkdir -p "$work/generated"
"$compiler" build --target=c --define PLATFORM_DESKTOP --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kss/src" --module-path "oqs=$root/build/packages/oqs/src" --module-path "qrcode=$root/build/packages/qrcode/src" \
    --module-path "kryon=$root/build/packages/kryon/src/ui" --module-path "kryon=$root/build/packages/kryon/src/backend" \
    --module-path "$root/build/packages/kryon/src/backend" \
    --module-path "$root/build/packages/game2d/src" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" \
    --entry diary_spelling_behavior:Check -o "$work/generated" \
    "$root/tests/diary_spelling_behavior.zi" "$root/tests/sync_test_host.zi"
cat > "$work/generated/main.c" <<'C'
#include "diary_spelling_behavior.h"
#include "network_transport.h"

AsyncTransport __wrap_network_transport_NetworkTransport(NetworkTransfer *transfer)
{
    (void)transfer;
    return SpellingTestTransport();
}
int main(void)
{
    return Check() == 0 ? 0 : 1;
}
C
monocypher="$root/build/packages/monocypher/src"
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections \
    -I"$root/build/packages/ziran/include" -iquote "$work/generated" \
    -I"$root/vendor-builds/sqlite" -I"$root/vendor-builds/linux/x86_64/inbe-liboqs/include" \
    -I"$monocypher" -I"$monocypher/optional" \
    "$work/generated"/*.c "$root/vendor-builds/sqlite/sqlite3.c" \
    "$monocypher/monocypher.c" "$monocypher/optional/monocypher-ed25519.c" \
    "$liboqs" -Wl,--gc-sections -Wl,--wrap=network_transport_NetworkTransport \
    -ldl -lpthread -lz -lm -o "$work/test"
APP_DATA_ROOT=/tmp/inbe-diary-spelling-test/data "$work/test"
printf '%s\n' 'Diary spelling: account and length limits, signed node request, escaped entry, corrected text, daily limit, node errors and cancel passed'
