#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:-"$root/build/packages/ziran/build/bin/ziran"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
vendor=$root/vendor-builds/linux/x86_64
avif_a=${AVIF_A:-$vendor/kryon-avif/avif/libavif.a}
aom_a=${AOM_A:-$vendor/kryon-avif/aom/libaom.a}
test -f "$avif_a"
test -f "$aom_a"
work=$root/build/media-compression-zi-test
exec 9>"$work.lock"
flock 9
rm -rf "$work/generated"
mkdir -p "$work/generated" "$work/data"
python3 -B "$root/tests/make_media_compression_fixture.py" "$work/input.png"
unset DISPLAY WAYLAND_DISPLAY WAYLAND_SOCKET XAUTHORITY DBUS_SESSION_BUS_ADDRESS DBUS_SYSTEM_BUS_ADDRESS SESSION_MANAGER XDG_RUNTIME_DIR
export ZIRAN_DESKTOP_RECOVERY=0 HARMONY_DESKTOP_RECOVERY=0 YUE_DESKTOP_RECOVERY=0
# Project mode resolves package imports through their exports (such as
# kryon/text_area for the Lumi frame), as the app build does.
"$ziran" build --project --offline --target=c --define PLATFORM_DESKTOP --define DESKTOP_HOST \
    --define KRYON_WEBP_LINKED --define NATIVE_WINDOW_HAVE_SDL --define MEDIA_COMPRESSION_REAL_CODEC --root "$root" \
    --module-path "$root/tests" \
    --entry media_compression_behavior:Check -o "$work/generated" \
    "$root/tests/media_compression_behavior.zi" "$root/tests/media_compression_test_host.zi" "$root/src/app/app_clock_host.zi"
cat > "$work/generated/main.c" <<'C'
#include "media_compression_behavior.h"
#include <stdio.h>
int main(void) {
    int result = Check();
    if (result) fprintf(stderr, "media compression check failed: %d\n", result);
    return result ? 1 : 0;
}
C
includes=$(find "$work/generated" -type d -printf ' -iquote %p')
sources=$(find "$work/generated" -type f -name '*.c')
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections \
    -I"$root/build/packages/ziran/include" $includes \
    -I"$root/vendor-builds/sqlite" -I"$vendor/inbe-liboqs/include" \
    $sources "$root/tests/media_compression_faults.c" \
    "$root/vendor-builds/sqlite/sqlite3.c" "$root/build/packages/monocypher/src/monocypher.c" "$liboqs" \
    "$vendor/kryon-webp/libkryonwebp.a" "$avif_a" "$aom_a" \
    "$vendor/audio-codecs/libziran_mp3.a" "$vendor/audio-codecs/libvorbisfile.a" "$vendor/audio-codecs/libvorbis.a" "$vendor/audio-codecs/libogg.a" \
    $(pkg-config --libs sdl2 cairo pangocairo fontconfig freetype2 gio-2.0 x11) -l:libopus.so.0 \
    -Wl,--wrap=sqlite3_step -Wl,--gc-sections -ldl -lpthread -lz -lm -o "$work/test"
APP_DATA_ROOT="$work/data"; export APP_DATA_ROOT
"$work/test"
