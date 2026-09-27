#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/elist-screen-zi-test
mkdir -p "$work/c"

"$bin/zi2zir" --check-only --root "$root/src" \
    --module-path "$root/vendor/kryon/src/ui" \
    --module-path "$root/vendor/kryon/src/kss" \
    --module-path "$root/vendor/ziran/std" \
    --module-path "$root/vendor/daochi-client" \
    "$root/src/screens/elist_screen.zi"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/vendor/kryon/src/ui" \
    --module-path "$root/vendor/kryon/src/kss" \
    --module-path "$root/vendor/ziran/std" \
    --module-path "$root/vendor/daochi-client" \
    -o "$work/c" "$root/src/screens/elist_screen.zi"

"${CC:-cc}" -std=c11 -Wall -Wextra -Werror \
    -Wno-unused-function -Wno-unused-variable \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/vendor/ziran/include" -I"$work/c" \
    -I"$work/c/ui" -I"$work/c/app" -I"$work/c/platform" \
    -I"$work/c/storage" -I"$work/c/screens" -I"$work/c/kss" \
    -I"$work/c/daochi-client" \
    "$root/tests/elist_screen_link_test.c" \
    "$work/c/screens/elist_screen.c" "$work/c/text_buffers.c" \
    -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "Inbe elist screen Ziran/native test passed"
