#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work=$root/build/elist-screen-zi-test
mkdir -p "$work/c"

# Serialize concurrent checks: the link below takes every generated file.
exec 9>"$work.lock"
flock 9

"$bin/ziran" check --project --locked --root "$root/src" \
    "$root/src/screens/elist_screen.zi"
"$bin/ziran" build --project --locked --target=c --no-main --prune-stale --root "$root/src" \
    -o "$work/c" "$root/src/screens/elist_screen.zi"

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
    $includes "$work/elist_screen_link_test.o" "$work/elist_screen.o" \
    $(find "$work/c" -name '*.c' | grep -v -e '/elist_screen\.c$' \
        -e '/db\.c$' -e '/storage_elist\.c$' -e '/lists_network\.c$' \
        -e '/diary_store\.c$' -e '/node_apps\.c$' -e '/media_store\.c$' \
        -e '/metrics\.c$') \
    "$bin/../libziran.a" \
    "$root/vendor-builds/linux/x86_64/raylib/libraylib.a" \
    $(pkg-config --libs sdl2 gl libwebp libwebpdemux) \
    -l:libopus.so.0 -l:libcurl.so.4 -lm -lpthread -ldl -lz -latomic \
    -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test" "$root/build/inbe.zx"
echo "Inbe elist screen Ziran/native test passed"
