#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
compiler=${1:-"$root/build/ziran-toolchain/bin/ziran"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
work=$(mktemp -d /tmp/inbe-telegram-entry-protocol.XXXXXX)
trap 'rm -rf "$work"' EXIT HUP INT TERM
unset DISPLAY WAYLAND_DISPLAY XAUTHORITY DBUS_SESSION_BUS_ADDRESS
export YUE_DESKTOP_RECOVERY=0
"$compiler" build --target=c --define PLATFORM_DESKTOP --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kss/src" --module-path "oqs=$root/build/packages/oqs/src" \
    --module-path "kryon=$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kryon/src/backend" \
    --module-path "$root/build/packages/game2d/src" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" \
    --entry telegram_entry_protocol_behavior:Check -o "$work/generated" \
    "$root/tests/telegram_entry_protocol_behavior.zi" "$root/tests/sync_test_host.zi"
cat > "$work/generated/main.c" <<'C'
#include "telegram_entry_protocol_behavior.h"
#include <stdint.h>
#include <stdio.h>
#include <time.h>

static int64_t fixture_clock = 1700000000;
static int64_t signing_delay;
void EntryTestSetClock(int64_t now) { fixture_clock = now; signing_delay = 0; }
void EntryTestSetSigningDelay(int64_t delay) { signing_delay = delay; }
time_t __wrap_time(time_t *out)
{
    time_t value = (time_t)fixture_clock;
    if (out) *out = value;
    return value;
}
void __real_crypto_ed25519_sign(uint8_t *, const uint8_t *, const uint8_t *, size_t);
void __wrap_crypto_ed25519_sign(uint8_t *signature, const uint8_t *key,
    const uint8_t *message, size_t length)
{
    __real_crypto_ed25519_sign(signature, key, message, length);
    fixture_clock += signing_delay;
}
int main(void)
{
    int result = Check();
    if (result) fprintf(stderr, "Telegram entry protocol check failed: %d\n", result);
    return result ? 1 : 0;
}
C
monocypher=$root/build/packages/monocypher/src
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections \
    -I"$root/build/packages/ziran/include" -I"$work/generated" \
    -I"$root/vendor-builds/sqlite" -I"$root/vendor-builds/linux/x86_64/inbe-liboqs/include" \
    -I"$monocypher" -I"$monocypher/optional" \
    "$work/generated"/*.c "$root/vendor-builds/sqlite/sqlite3.c" \
    "$monocypher/monocypher.c" "$monocypher/optional/monocypher-ed25519.c" \
    "$liboqs" -Wl,--gc-sections -Wl,--wrap=time -Wl,--wrap=crypto_ed25519_sign \
    -ldl -lpthread -lz -lm -o "$work/test"
APP_DATA_ROOT="$work/data" "$work/test"
printf '%s\n' 'Telegram entry strict parsing, canonical digest, real Ed25519 proofs and fresh clock checks passed'
