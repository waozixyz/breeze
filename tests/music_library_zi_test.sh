#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/music-library-zi-test
mkdir -p "$work/c" "$work/stubs"
"$bin/zi2zir" --check-only --root "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/daochi-client" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "oqs=$root/build/packages/oqs/src" \
    "$root/src/app/music_library.zi"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/daochi-client" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "oqs=$root/build/packages/oqs/src" \
    -o "$work/c" "$root/src/app/music_library.zi" \
    "$root/src/app/music_library_host.zi"
"$bin/zi2c" --no-main --root "$root/tests" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "oqs=$root/build/packages/oqs/src" \
    -o "$work/stubs" "$root/tests/music_library_host_stubs.zi"
"${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK -ffunction-sections \
    -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -iquote "$work/c" \
    -iquote "$work/stubs" \
    "$root/tests/music_library_link_test.c" \
    "$work/stubs/music_library_host_stubs.c" \
    "$work/c/app/music_library_host.c" \
    "$work/c/app/music_library.c" "$work/c/c_string.c" \
    "$work/c/byte_text_linux.c" "$work/c/environment.c" \
    "$work/c/locale.c" "$work/c/assets.c" "$work/c/text_buffers.c" \
    "$work/c/locale_parser.c" "$work/c/locale_policy.c" \
    -o "$work/test"
fixture=$(mktemp -d "$work/fixture.XXXXXX")
trap 'rm -rf "$fixture"' EXIT HUP INT TERM
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS -u GDK_DISPLAY \
    YUE_DESKTOP_RECOVERY=0 \
    APP_DATA_ROOT="$fixture" "$work/test" "$fixture"
