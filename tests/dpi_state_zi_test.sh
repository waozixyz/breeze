#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work=$root/build/dpi-state-zi-test
rm -rf "$work/c"
mkdir -p "$work/c"
"$bin/ziran" build --project --offline --target=c --no-main --root "$root" \
    -o "$work/c" "$root/src/app/dpi_state.zi" "$root/src/platform/dpi_density.zi"

"${CC:-cc}" -std=c11 -Wall -Wextra -Werror \
    -Wno-unused-function -Wno-unused-variable \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" $(find "$work/c" -type d -printf ' -iquote %p') \
    "$root/tests/dpi_state_link_test.c" $(find "$work/c" -type f -name '*.c') \
    -lm -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
    "$work/test"
echo "Inbe DPI Ziran/native test passed"
