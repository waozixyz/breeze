#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/dpi-state-zi-test
mkdir -p "$work/c"

"$bin/zi2zir" --check-only --root "$root/src" \
    --module-path "$root/vendor/kryon/src/ui" \
    --module-path "$root/vendor/ziran/std" \
    "$root/src/app/dpi_state.zi"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/vendor/kryon/src/ui" \
    --module-path "$root/vendor/ziran/std" \
    -o "$work/c" "$root/src/app/dpi_state.zi" \
    "$root/src/platform/dpi_density.zi"

"${CC:-cc}" -std=c11 -Wall -Wextra -Werror \
    -Wno-unused-function -Wno-unused-variable \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/vendor/ziran/include" -iquote "$work/c" \
    "$root/tests/dpi_state_link_test.c" \
    "$work/c/platform/dpi_density.c" \
    "$work/c/app/dpi_state.c" "$work/c/dpi.c" \
    "$work/c/environment.c" "$work/c/raylib_game.c" \
    -lm -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
    "$work/test"
echo "Inbe DPI Ziran/native test passed"
