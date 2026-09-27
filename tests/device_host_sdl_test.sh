#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work=$root/build/device-host-sdl-test
bin=${1:-"$root/build/ziran-toolchain/bin"}
mkdir -p "$work/c"
"$bin/zi2c" --no-main --root "$root/src/platform" \
    --module-path "$root/src" --module-path "$root/build/packages/ziran/std" \
    --define NATIVE_WINDOW_HAVE_SDL -o "$work/c" \
    "$root/src/platform/device_host.zi"
flags=$(pkg-config --cflags --libs sdl2)
"${CC:-cc}" -std=c11 -Wall -Wextra -Werror -DNATIVE_WINDOW_HAVE_SDL \
    -Wno-unused-function -I"$root/src/app" \
    -I"$root/build/packages/ziran/include" -I"$work/c" \
    "$root/tests/device_host_sdl_test.c" "$work/c"/*.c \
    $flags -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY SDL_VIDEODRIVER=dummy "$work/test"
echo "Inbe device host owned-window test passed"
