#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
compiler=${1:-"$root/build/packages/ziran/build/bin/ziran"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
work=${3:-"$root/build/lumi-connection-test"}
audio_dir=${AUDIO_CODECS_BUILD_DIR:-"$root/vendor-builds/linux/x86_64/audio-codecs"}
exec 9>"$work.lock"
flock 9
unset DISPLAY WAYLAND_DISPLAY XAUTHORITY DBUS_SESSION_BUS_ADDRESS
export YUE_DESKTOP_RECOVERY=0
mkdir -p "$work/generated"
set --
if [ "${INBE_LUMI_TEST_DEBUG:-0}" = 1 ]; then
    set -- --define ANDROID_DEBUG
fi
(cd "$root" &&
    "$compiler" build --project --offline --target=c --no-main --prune-stale \
        --define PLATFORM_DESKTOP --define DESKTOP_HOST --define STORAGE_TEST_REAL_HOST_SERVICES "$@" --root "$root" \
        -o "$work/generated" \
        "$root/tests/lumi_connection_behavior.zi")
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
    tool_executions += 1;
    return package_files_PackageText((String){.data = "{\"ok\":true}", .length = 11},
        (String){.data = "", .length = 0});
}
/* Use the interpreter's normal append and online host calls without a window. */
bool __wrap_lumi_screen_LumiSubmit(InnerBreeze *app, String input)
{
    (void)app;
    return TelegramFixtureSubmit(input);
}
int main(void)
{
    int result = Check();
    return result == 0 ? 0 : 1;
}
C
monocypher="$root/build/packages/monocypher/src"
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections \
    -I"$root/build/packages/ziran/include" -iquote "$work/generated" -iquote "$work/generated/tests" \
    -I"$root/vendor-builds/sqlite" -I"$root/vendor-builds/linux/x86_64/inbe-liboqs/include" \
    -I"$monocypher" -I"$monocypher/optional" \
    "$work/generated"/*.c "$work/generated/tests"/*.c "$root/vendor-builds/sqlite/sqlite3.c" \
    "$monocypher/monocypher.c" "$monocypher/optional/monocypher-ed25519.c" \
    "$liboqs" -Wl,--gc-sections -Wl,--wrap=network_transport_NetworkTransport \
    -Wl,--wrap=app_apply_nav_route -Wl,--wrap=practice_actions_app_start_practice \
    -Wl,--wrap=app_tools_AppToolContext -Wl,--wrap=app_tools_AppToolExecute \
    -Wl,--wrap=lumi_screen_LumiSubmit \
    "$audio_dir/libopus/libopus.a" "$audio_dir/libziran_mp3.a" \
    "$audio_dir/libvorbisfile.a" "$audio_dir/libvorbis.a" "$audio_dir/libogg.a" \
    $(pkg-config --libs sdl2 cairo pangocairo fontconfig freetype2 gio-2.0 x11) \
    -ldl -lpthread -lz -lm -o "$work/test"
# The provider's key must never reach any output, even with request tracing.
mkdir -p /tmp/inbe-lumi-connection-test
test_root=$(mktemp -d /tmp/inbe-lumi-connection-test/run.XXXXXX)
trap 'rm -rf "$test_root"' EXIT HUP INT TERM
INBE_NETWORK_TRACE=1 APP_DATA_ROOT="$test_root" "$work/test" > "$work/output.txt" 2>&1 ||
    { cat "$work/output.txt"; exit 1; }
if grep -q 'sk-test-lumi-provider' "$work/output.txt"; then
    echo 'the provider key reached the output' >&2
    exit 1
fi
printf '%s\n' 'Lumi connection: nothing sent before agreeing or offline, diary spelling and habit icons included; server and own provider after agreeing; key only in its header; withdrawal passed'
printf '%s\n' 'Lumi conversation: recent history, six tool rounds without replay and complete long UTF-8 replies passed'
if [ "${INBE_LUMI_TEST_DEBUG:-0}" = 1 ]; then
    printf '%s\n' 'Lumi developer chat: signed submit, receipt polling, local archive, and ordinary chat isolation passed'
fi
