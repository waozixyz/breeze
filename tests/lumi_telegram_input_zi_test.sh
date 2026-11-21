#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:-"$root/build/packages/ziran/build/bin/ziran"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
work=${LUMI_TELEGRAM_INPUT_TEST_OUTPUT:-"$root/build/lumi-telegram-input-test"}
audio_dir=${AUDIO_CODECS_BUILD_DIR:-"$root/vendor-builds/linux/x86_64/audio-codecs"}
exec 9>"$work.lock"
flock 9
unset DISPLAY WAYLAND_DISPLAY XAUTHORITY DBUS_SESSION_BUS_ADDRESS
export YUE_DESKTOP_RECOVERY=0
mkdir -p "$work/generated"
python3 "$root/scripts/stage-practice-figure.py"
(cd "$root" &&
    "$ziran" build --project --offline ${PACKAGE_FLAGS:-} --module-path "$root/build/practice-figure" --target=c --no-main --prune-stale \
        --define PLATFORM_DESKTOP --define DESKTOP_HOST --define STORAGE_TEST_REAL_HOST_SERVICES \
        --root "$root" -o "$work/generated" "$root/tests/lumi_telegram_input_behavior.zi")
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
int32_t __wrap_AppsInstalledMask(void)
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
    -I"$root/build/packages/ziran/include" -iquote "$work/generated" -iquote "$work/generated/tests" \
    -I"$root/vendor-builds/sqlite" -I"$root/vendor-builds/linux/x86_64/inbe-liboqs/include" \
    -I"$monocypher" -I"$monocypher/optional" \
    "$work/generated"/*.c "$work/generated/tests"/*.c "$root/vendor-builds/sqlite/sqlite3.c" \
    "$monocypher/monocypher.c" "$monocypher/optional/monocypher-ed25519.c" \
    "$liboqs" -Wl,--gc-sections -Wl,--wrap=network_transport_NetworkTransport \
    -Wl,--wrap=AppsInstalledMask -Wl,--wrap=lumi_screen_LumiSubmit -Wl,--wrap=lumi_telegram_LumiTelegramOpen \
    "$audio_dir/libopus/libopus.a" "$audio_dir/libziran_mp3.a" \
    "$audio_dir/libvorbisfile.a" "$audio_dir/libvorbis.a" "$audio_dir/libogg.a" \
    $(pkg-config --libs sdl2 cairo pangocairo fontconfig freetype2 gio-2.0 x11) \
    -ldl -lpthread -lz -lm -o "$work/test"
APP_DATA_ROOT=/tmp/inbe-lumi-telegram-input-test/data \
    env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    YUE_DESKTOP_RECOVERY=0 "$work/test"
printf '%s\n' 'Lumi Telegram input and private reply, persisted history and account outbox checks passed'
