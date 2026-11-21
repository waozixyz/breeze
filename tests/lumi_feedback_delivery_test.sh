#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
compiler=${1:-"$root/build/packages/ziran/build/bin/ziran"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
work="$root/build/lumi-feedback-test"
audio_dir=${AUDIO_CODECS_BUILD_DIR:-"$root/vendor-builds/linux/x86_64/audio-codecs"}
exec 9>"$work.lock"
flock 9
unset DISPLAY WAYLAND_DISPLAY XAUTHORITY DBUS_SESSION_BUS_ADDRESS
export YUE_DESKTOP_RECOVERY=0
rm -rf "$work/generated"
mkdir -p "$work/generated"
# shellcheck disable=SC2046
python3 "$root/scripts/stage-practice-figure.py"
cd "$root"
"$compiler" build --project --offline ${PACKAGE_FLAGS:-} --module-path "$root/build/practice-figure" --target=c --no-main \
    --define PLATFORM_DESKTOP --define DESKTOP_HOST --define STORAGE_TEST_REAL_HOST_SERVICES --root "$root" \
    -o "$work/generated" \
    "$root/tests/lumi_feedback_delivery_behavior.zi" "$root/src/app/app_clock_host.zi"
cat > "$work/generated/main.c" <<'C'
#include <stdio.h>
#include <stdlib.h>
#include "lumi_feedback_delivery_behavior.h"
#include "network_transport.h"
#include "lumi_online.h"
#include "lumi_telegram.h"
#include "lumi_screen.h"
#include "app_tools.h"
#include "app_nav_state.h"
#include "practice_actions.h"

AsyncTransport __wrap_network_transport_NetworkTransport(NetworkTransfer *transfer)
{
    (void)transfer;
    return FeedbackTestTransport();
}
void __wrap_lumi_telegram_LumiTelegramPump(InnerBreeze *app)
{
    (void)app;
}
/* The test exercises report tools directly. It must never start model chat. */
String __wrap_app_tools_AppToolContext(InnerBreeze *app)
{
    (void)app;
    fputs("unexpected model context request in feedback fixture\n", stderr);
    abort();
}
String __wrap_app_tools_AppToolExecute(InnerBreeze *app, String name, String arguments)
{
    (void)app;
    (void)name;
    (void)arguments;
    fputs("unexpected model tool call in feedback fixture\n", stderr);
    abort();
}
bool __wrap_lumi_screen_LumiSubmit(InnerBreeze *app, String input)
{
    (void)app;
    (void)input;
    fputs("unexpected composer call in feedback fixture\n", stderr);
    abort();
}
void __wrap_app_apply_nav_route(InnerBreeze *app, int32_t route)
{
    (void)app;
    (void)route;
    abort();
}
bool __wrap_practice_actions_app_start_practice(InnerBreeze *app, int32_t practice)
{
    (void)app;
    (void)practice;
    abort();
}
int32_t __wrap_AppsInstalledMask(void) { return 31; }
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
    "$liboqs" -Wl,--gc-sections -Wl,--wrap=AppsInstalledMask -Wl,--wrap=network_transport_NetworkTransport \
    -Wl,--wrap=lumi_telegram_LumiTelegramPump \
    -Wl,--wrap=app_tools_AppToolContext -Wl,--wrap=app_tools_AppToolExecute -Wl,--wrap=lumi_screen_LumiSubmit \
    -Wl,--wrap=app_apply_nav_route -Wl,--wrap=practice_actions_app_start_practice \
    "$audio_dir/libopus/libopus.a" "$audio_dir/libziran_mp3.a" \
    "$audio_dir/libvorbisfile.a" "$audio_dir/libvorbis.a" "$audio_dir/libogg.a" \
    $(pkg-config --libs sdl2 cairo pangocairo fontconfig freetype2 gio-2.0 x11) \
    -ldl -lpthread -lz -lm -o "$work/test"
APP_DATA_ROOT=/tmp/inbe-lumi-feedback-test/data "$work/test"
printf '%s\n' 'Lumi feedback approval, HTTP failure, receipt verification, retries, restart and older outbox upgrade checks passed'
