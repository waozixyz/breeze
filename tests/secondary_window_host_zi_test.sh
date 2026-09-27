#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
raylib=${2:-"$root/vendor-builds/linux/x86_64/raylib/libraylib.a"}
work="$root/build/secondary-window-host-test"
mkdir -p "$work/c"

export PKG_CONFIG_PATH="/home/wao/.local/sdl2/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
"$bin/zi2c" --no-main --define NATIVE_WINDOW_HAVE_SDL \
    --root "$root/src" --module-path "$root/build/packages/ziran/std" \
    -o "$work/c" "$root/src/platform/secondary_window_host.zi"
# The existing native probe checks rendered pixels, event ownership,
# clicks, dragging, and restoration of the main OpenGL context.
# shellcheck disable=SC2046
"${CC:-cc}" -std=c11 -Wall -Wextra \
    -I"$root/build/packages/ziran/include" -iquote "$work/c" \
    -I"$root/build/packages/kryon/vendor/raylib/src" $(pkg-config --cflags sdl2) \
    "$root/tests/secondary_window_host_test.c" \
    "$work/c/platform/secondary_window_host.c" "$raylib" \
    $(pkg-config --libs sdl2) -lGL -lm -ldl -lpthread -o "$work/test"

env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
    xvfb-run -a -n 200 -e /dev/stderr -s '-screen 0 800x600x24' "$work/test"
echo "Inbe Ziran secondary window host test passed"
