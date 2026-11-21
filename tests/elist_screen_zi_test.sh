#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work=$root/build/elist-screen-zi-test
mkdir -p "$work/c"

# Serialize concurrent checks: the link below takes every generated file.
exec 9>"$work.lock"
flock 9

# The screen as the Linux app builds it, on Kryon's desktop host.
defines="--define PLATFORM_DESKTOP --define DESKTOP_HOST --define NATIVE_WINDOW_HAVE_SDL"
python3 "$root/scripts/stage-practice-figure.py"
"$bin/ziran" check --project ${PACKAGE_FLAGS:---offline} --module-path "$root/build/practice-figure" --root "$root/src" $defines \
    "$root/src/screens/elist_screen.zi"
"$bin/ziran" build --project ${PACKAGE_FLAGS:---offline} --target=c --no-main --prune-stale --module-path "$root/build/practice-figure" --root "$root/src" $defines \
    -o "$work/c" "$root/src/screens/elist_screen.zi" "$root/src/storage/storage_thread_buffers.zi"

includes="-I$root/build/packages/ziran/include -I$work/c"

# The test host and the screen under test compile warning-free.
for source in "$root/tests/elist_screen_link_test.c" "$work/c/elist_screen.c"; do
    "${CC:-cc}" -std=c11 -Wall -Wextra -Werror \
        -Wno-unused-function -Wno-unused-variable \
        -ffunction-sections -fdata-sections $includes \
        -c "$source" -o "$work/$(basename "$source" .c).o"
done

# Every other module the screen reaches links as generated, so a new import in
# the app or Kryon needs no change here; --gc-sections drops what the test never
# calls. The modules whose storage, sharing, Diary, node app, media library and
# scale functions the test host replaces stay out. Observe the sync scheduling
# boundary through a linker wrapper, leaving its production export intact.
"${CC:-cc}" -std=c11 -w -ffunction-sections -fdata-sections -Wl,--gc-sections -Wl,--wrap=app_auto_sync \
    -Wl,--wrap=storage_db_path \
    $includes "$work/elist_screen_link_test.o" "$work/elist_screen.o" \
    $(find "$work/c" -name '*.c' | grep -v -e '/elist_screen\.c$' \
        -e '/storage_elist\.c$' -e '/lists_network\.c$' \
        -e '/diary_store\.c$' -e '/node_apps\.c$' -e '/media_store\.c$' \
        -e '/metrics\.c$') \
    "$root/vendor-builds/sqlite/sqlite3.c" \
    "$bin/../libziran.a" \
    "$root/vendor-builds/linux/x86_64/audio-codecs/libziran_mp3.a" \
    "$root/vendor-builds/linux/x86_64/audio-codecs/libvorbisfile.a" \
    "$root/vendor-builds/linux/x86_64/audio-codecs/libvorbis.a" \
    "$root/vendor-builds/linux/x86_64/audio-codecs/libogg.a" \
    $(pkg-config --libs sdl2 cairo pangocairo fontconfig freetype2 gio-2.0 x11 libwebp libwebpdemux) \
    -l:libopus.so.0 -l:libcurl.so.4 -lm -lpthread -ldl -lz -latomic \
    -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test" "$root/build/inbe.zx"
echo "Inbe elist screen Ziran/native test passed"
