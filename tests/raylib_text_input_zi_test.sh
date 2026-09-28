#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/raylib-text-input-zi-test
mkdir -p "$work/c"

"$bin/zi2zir" --check-only --root "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" \
    "$root/src/platform/raylib_text_input.zi"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/c" "$root/src/platform/raylib_text_input.zi"

"${CC:-cc}" -std=c11 -Wall -Wextra -Werror \
    -Wno-unused-function -Wno-unused-variable \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -I"$work/c" \
    -I"$work/c/ui" -I"$work/c/app" \
    "$root/tests/raylib_text_input_link_test.c" \
    "$work/c/platform/raylib_text_input.c" "$work/c/text_buffers.c" \
    "$work/c/byte_text_linux.c" \
    -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "Inbe raylib text input Ziran/native test passed"
