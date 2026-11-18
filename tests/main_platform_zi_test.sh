#!/bin/sh
# Process setup and Inner Breeze's log, as the Linux app builds them on
# Kryon's desktop host.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work=$(mktemp -d "$root/build/main-platform-zi.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
# Project mode resolves package exports (such as Kryon's Cairo raster) as the
# app build does.
"$bin/ziran" build --project --offline --target=c --no-main \
    --define PLATFORM_DESKTOP --define DESKTOP_HOST --define NATIVE_WINDOW_HAVE_SDL \
    --root "$root" --module-path "$root/tests" \
    -o "$work/c" "$root/tests/main_platform_behavior.zi"
"${CC:-cc}" -std=c11 -O2 -DZIRAN_BOUNDS_CHECK \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" $(find "$work/c" -type d -printf ' -iquote %p') \
    $(find "$work/c" -type f -name '*.c') \
    $(pkg-config --libs sdl2 cairo pangocairo fontconfig freetype2 gio-2.0 x11) \
    -lz -lm -ldl -pthread -latomic -o "$work/test"
cd "$work"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
    ./test 2> stderr
test "$(cat stderr)" = "WARNING: IMAGE: retained
INFO: values 42 3.25 inbe.test"
test "$(cat inbe.log)" = 'ERROR: WGL test failure'
echo "Inbe Ziran process setup and logging test passed"
