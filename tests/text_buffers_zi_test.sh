#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/text-buffers-zi-test
mkdir -p "$work/c"
"$bin/zi2zir" --check-only --root "$root/src" \
    --module-path "$root/vendor/ziran/std" \
    "$root/src/app/text_buffers.zi"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/vendor/ziran/std" \
    -o "$work/c" "$root/src/app/text_buffers.zi"
"${CC:-cc}" -std=c11 -Wall -Wextra -Werror \
    -Wno-unused-function -Wno-unused-variable \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/vendor/ziran/include" -I"$work/c" \
    "$root/tests/text_buffers_link_test.c" \
    "$work/c/app/text_buffers.c" -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "Inbe text buffer Ziran/native test passed"
