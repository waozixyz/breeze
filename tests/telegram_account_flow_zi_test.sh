#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
compiler=${1:-"$root/build/ziran-toolchain/bin/ziran"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
work=$(mktemp -d /tmp/inbe-telegram-account-flow.XXXXXX)
trap 'rm -rf "$work"' EXIT HUP INT TERM
unset DISPLAY WAYLAND_DISPLAY XAUTHORITY DBUS_SESSION_BUS_ADDRESS
export YUE_DESKTOP_RECOVERY=0
"$compiler" build --target=c --define PLATFORM_WEB --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kryon/src/backend" \
    --module-path "kryon=$root/build/packages/kryon/src/ui" \
    --module-path "kryon=$root/build/packages/kryon/src/backend" \
    --module-path "$root/build/packages/kss/src" --module-path "oqs=$root/build/packages/oqs/src" \
    --module-path "$root/build/packages/game2d/src" --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" --entry telegram_account_flow_behavior:Check \
    -o "$work/generated" "$root/tests/telegram_account_flow_behavior.zi" \
    "$root/tests/telegram_account_flow_host.zi" "$root/tests/sync_test_host.zi"
cat > "$work/generated/main.c" <<'C'
#include "telegram_account_flow_behavior.h"
#include <stdio.h>
#include <stdint.h>
#include <time.h>
static int64_t fixture_clock = 1700000000;
void FlowClockSet(int64_t value) { fixture_clock = value; }
void FlowClockAdvance(int64_t seconds) { fixture_clock += seconds; }
time_t __wrap_time(time_t *out)
{
    time_t value = (time_t)fixture_clock;
    if (out) *out = value;
    return value;
}
int main(void)
{
    int result = Check();
    if (result) fprintf(stderr, "Telegram account controller check failed: %d\n", result);
    return result ? 1 : 0;
}
C
monocypher=$root/build/packages/monocypher/src
"${CC:-cc}" -std=c11 -O1 -g -fno-omit-frame-pointer ${FLOW_TEST_CFLAGS:-} -ffunction-sections -fdata-sections \
    -I"$root/build/packages/ziran/include" -I"$work/generated" \
    -I"$root/vendor-builds/sqlite" -I"$root/vendor-builds/linux/x86_64/inbe-liboqs/include" \
    -I"$monocypher" -I"$monocypher/optional" \
    "$work/generated"/*.c "$root/vendor-builds/sqlite/sqlite3.c" \
    "$monocypher/monocypher.c" "$monocypher/optional/monocypher-ed25519.c" "$liboqs" \
    -Wl,--gc-sections -Wl,--wrap=time -ldl -lpthread -lz -lm -o "$work/test"
mkdir -p "$work/data"
if [ "${FLOW_TEST_DEBUG:-0}" = 1 ]; then
    APP_DATA_ROOT="$work/data" gdb --batch -ex 'set print frame-arguments none' -ex run -ex bt --args "$work/test"
    exit 1
else
    APP_DATA_ROOT="$work/data" "$work/test"
fi
printf '%s\n' 'Telegram account integrated synthetic controller checks passed'
