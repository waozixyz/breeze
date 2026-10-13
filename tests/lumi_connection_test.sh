#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
compiler=${1:-"$root/build/ziran-toolchain/bin/ziran"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
work="$root/build/lumi-connection-test"
exec 9>"$work.lock"
flock 9
unset DISPLAY WAYLAND_DISPLAY XAUTHORITY DBUS_SESSION_BUS_ADDRESS
export YUE_DESKTOP_RECOVERY=0
mkdir -p "$work/generated"
"$compiler" build --target=c --define PLATFORM_DESKTOP --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kss/src" --module-path "oqs=$root/build/packages/oqs/src" --module-path "qrcode=$root/build/packages/qrcode/src" \
    --module-path "kryon=$root/build/packages/kryon/src/ui" \
    --module-path "plot=$root/build/packages/plot/src" \
    --module-path "$root/build/packages/kryon/src/backend" \
    --module-path "$root/build/packages/game2d/src" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" \
    --entry lumi_connection_behavior:Check -o "$work/generated" \
    "$root/tests/lumi_connection_behavior.zi" "$root/tests/sync_test_host.zi"
cat > "$work/generated/main.c" <<'C'
#include <stdio.h>
#include <stdlib.h>
#include "lumi_connection_behavior.h"
#include "network_transport.h"
#include "app_nav_state.h"
#include "practice_actions.h"
#include "app_tools.h"
#include "package_files.h"
#include "lumi_screen.h"

AsyncTransport __wrap_network_transport_NetworkTransport(NetworkTransfer *transfer)
{
    (void)transfer;
    return ConnectionTestTransport();
}
void __wrap_app_apply_nav_route(InnerBreeze *app, int32_t route)
{
    (void)app;
    (void)route;
}
bool __wrap_practice_actions_app_start_practice(InnerBreeze *app, int32_t practice)
{
    (void)app;
    (void)practice;
    return false;
}
/* The app's context and tools are tested on their own; here they stay
   small so the fixture needs no window or renderer. */
String __wrap_app_tools_AppToolContext(InnerBreeze *app)
{
    (void)app;
    return package_files_PackageText((String){.data = "{\"app\":\"inbe\"}", .length = 14},
        (String){.data = "", .length = 0});
}
String __wrap_app_tools_AppToolExecute(InnerBreeze *app, String name, String arguments)
{
    (void)app;
    (void)name;
    (void)arguments;
    return package_files_PackageText((String){.data = "{\"ok\":true}", .length = 11},
        (String){.data = "", .length = 0});
}
/* Telegram input runs Lumi's interpreter, which needs the app's window;
   here the relay itself is under test. */
bool __wrap_lumi_screen_LumiSubmit(InnerBreeze *app, String input)
{
    (void)app;
    (void)input;
    return false;
}
int main(void)
{
    int result = Check();
    return result == 0 ? 0 : 1;
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
    -Wl,--wrap=app_apply_nav_route -Wl,--wrap=practice_actions_app_start_practice \
    -Wl,--wrap=app_tools_AppToolContext -Wl,--wrap=app_tools_AppToolExecute \
    -Wl,--wrap=lumi_screen_LumiSubmit \
    -ldl -lpthread -lz -lm -o "$work/test"
# The provider's key must never reach any output, even with request tracing.
INBE_NETWORK_TRACE=1 APP_DATA_ROOT=/tmp/inbe-lumi-connection-test/data "$work/test" > "$work/output.txt" 2>&1 ||
    { cat "$work/output.txt"; exit 1; }
if grep -q 'sk-test-lumi-provider' "$work/output.txt"; then
    echo 'the provider key reached the output' >&2
    exit 1
fi
printf '%s\n' 'Lumi connection: nothing sent before agreeing or offline; server and own provider after agreeing; key only in its header; withdrawal passed'
