#!/bin/sh
# Embedded assets as the Linux app reads them on Kryon's desktop host.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work=$(mktemp -d "$root/build/asset-files-zi.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
"$bin/ziran" build --project --offline --target=c --no-main \
    --define PLATFORM_DESKTOP --define DESKTOP_HOST --define NATIVE_WINDOW_HAVE_SDL \
    --root "$root" --module-path "$root/tests" \
    -o "$work/c" "$root/tests/asset_files_behavior.zi"
"${CC:-cc}" -std=c11 -O2 -ffunction-sections -fdata-sections -Wl,--gc-sections -w \
    -I"$root/build/packages/ziran/include" $(find "$work/c" -type d -printf ' -iquote %p') \
    $(find "$work/c" -type f -name '*.c') \
    $(pkg-config --libs sdl2 cairo pangocairo fontconfig freetype2 gio-2.0 x11) \
    -lz -lm -ldl -pthread -latomic -o "$work/test"
cd "$work"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY ./test
echo 'Embedded assets for the desktop raster, and other paths left to disk: passed'
