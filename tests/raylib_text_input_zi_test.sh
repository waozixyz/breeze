#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/raylib-text-input-zi-test
mkdir -p "$work/c"

"$bin/zi2zir" --check-only --root "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" --module-path "$root/build/packages/daochi-client" $(sh "$root/scripts/package-paths.sh" "$root/build/packages") --module-path "$root/build/packages/kryon/src/backend" \
    "$root/src/platform/raylib_text_input.zi"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" --module-path "$root/build/packages/daochi-client" $(sh "$root/scripts/package-paths.sh" "$root/build/packages") --module-path "$root/build/packages/kryon/src/backend" \
    -o "$work/c" "$root/src/platform/raylib_text_input.zi"

"${CC:-cc}" -std=c11 -Wall -Wextra -Werror \
    -Wno-unused-function -Wno-unused-variable \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -I"$work/c" \
    -I"$work/c/ui" -I"$work/c/app" \
    "$root/tests/raylib_text_input_link_test.c" \
    "$work/c/platform/raylib_text_input.c" "$work/c/text_buffers.c" \
    "$work/c/byte_text_linux.c" \
    "$work/c/test_driver.c" "$work/c/tree.c" "$work/c/tree_input.c" \
    "$work/c/session.c" "$work/c/c_string.c" "$work/c/vec.c" \
    -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "Inbe raylib text input Ziran/native test passed"
