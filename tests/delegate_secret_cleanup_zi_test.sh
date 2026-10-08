#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
compiler=${1:-"${ZIRAN_BIN:-"$root/build/ziran-toolchain/bin/ziran"}"}
launcher=$compiler
ziran_dir=$(cd "$root" && "$launcher" pkg path ziran)
monocypher=$(cd "$root" && "$launcher" pkg path monocypher)
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
work=$(mktemp -d /tmp/inbe-delegate-cleanup-test.XXXXXX)
trap 'rm -rf "$work"' EXIT HUP INT TERM
unset DISPLAY WAYLAND_DISPLAY XAUTHORITY DBUS_SESSION_BUS_ADDRESS
export YUE_DESKTOP_RECOVERY=0
"$compiler" build --target=c --define PLATFORM_DESKTOP --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kss/src" --module-path "oqs=$root/build/packages/oqs/src" \
    --module-path "kryon=$root/build/packages/kryon/src/ui" --module-path "$root/build/packages/kryon/src/backend" \
    --module-path "$root/build/packages/game2d/src" --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" --entry delegate_secret_cleanup_behavior:Check \
    -o "$work/generated" "$root/tests/delegate_secret_cleanup_behavior.zi" "$root/tests/sync_test_host.zi"
cat > "$work/generated/main.c" <<'C'
#include "delegate_secret_cleanup_behavior.h"
#include <stdio.h>
#include <stdint.h>
void ObservedWipe(uint8_t *output, int64_t length);
void __wrap_SyncCryptoWipe(uint8_t *output, int64_t length) { ObservedWipe(output, length); }
int main(void) {
    int result = Check();
    if (result) fprintf(stderr, "delegate secret cleanup check failed with code %d\n", result);
    return result ? 1 : 0;
}
C
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections \
    -I"$ziran_dir/include" -I"$work/generated" -I"$root/vendor-builds/sqlite" \
    -I"$root/vendor-builds/linux/x86_64/inbe-liboqs/include" -I"$monocypher/src" \
    "$work/generated"/*.c "$root/vendor-builds/sqlite/sqlite3.c" \
    "$monocypher/src/monocypher.c" "$monocypher/src/optional/monocypher-ed25519.c" "$liboqs" \
    -Wl,--gc-sections -Wl,--wrap=SyncCryptoWipe -ldl -lpthread -lm -o "$work/test"
APP_DATA_ROOT="$work/data" "$work/test"
printf '%s\n' 'Inbe owner signing and encrypted recovery secret cleanup passed'
