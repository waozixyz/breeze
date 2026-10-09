#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:-"$root/build/ziran-toolchain/bin/ziran"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
work=${LUMI_TELEGRAM_INPUT_TEST_OUTPUT:-"$root/build/lumi-telegram-input-test"}
exec 9>"$work.lock"
flock 9
unset DISPLAY WAYLAND_DISPLAY XAUTHORITY DBUS_SESSION_BUS_ADDRESS
export YUE_DESKTOP_RECOVERY=0
mkdir -p "$work/generated"
"$ziran" build --target=c --define PLATFORM_DESKTOP --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kss/src" --module-path "oqs=$root/build/packages/oqs/src" \
    --module-path "kryon=$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kryon/src/backend" \
    --module-path "$root/build/packages/game2d/src" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" \
    --entry lumi_telegram_input_behavior:Check -o "$work/generated" \
    "$root/tests/lumi_telegram_input_behavior.zi" "$root/tests/sync_test_host.zi"
cat > "$work/generated/main.c" <<'C'
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include "lumi_telegram_input_behavior.h"
#include "network_transport.h"
#include "lumi_screen.h"
#include "lumi_telegram.h"

AsyncTransport __wrap_network_transport_NetworkTransport(NetworkTransfer *transfer)
{
    (void)transfer;
    return InputTestTransport();
}
// This fixture uses the real /habits overview. No interpreter/UI call is expected.
bool __wrap_lumi_screen_LumiSubmit(InnerBreeze *app, String input)
{
    (void)app;
    (void)input;
    fputs("unexpected interpreter call in overview fixture\n", stderr);
    abort();
}
bool __wrap_lumi_telegram_LumiTelegramOpen(String start)
{
    (void)start;
    fputs("unexpected Telegram launch in input fixture\n", stderr);
    abort();
}
void OpenURI(const char *uri)
{
    (void)uri;
    fputs("unexpected external URI in input fixture\n", stderr);
    abort();
}
int32_t __wrap_CellsInstalledMask(void)
{
    return 31;
}
int main(void)
{
    int result = Check();
    if (result != 0) {
        fprintf(stderr, "Telegram input check failed: %d\n", result);
    }
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
    "$liboqs" -Wl,--gc-sections -Wl,--wrap=network_transport_NetworkTransport -Wl,--wrap=CellsInstalledMask -Wl,--wrap=lumi_screen_LumiSubmit -Wl,--wrap=lumi_telegram_LumiTelegramOpen -ldl -lpthread -lz -lm -o "$work/test"
APP_DATA_ROOT=/tmp/inbe-lumi-telegram-input-test/data \
    env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    YUE_DESKTOP_RECOVERY=0 "$work/test"
printf '%s\n' 'Lumi one-way Telegram input, complete persisted history and account outbox checks passed'
