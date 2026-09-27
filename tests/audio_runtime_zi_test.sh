#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM

"$bin/zi2zir" --check-only --root "$root/src" \
    --module-path "$root/vendor/kryon/src/ui" \
    --module-path "$root/vendor/ziran/std" \
    "$root/src/platform/audio_runtime.zi"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/vendor/kryon/src/ui" \
    --module-path "$root/vendor/ziran/std" \
    -o "$work/c" "$root/src/platform/audio_runtime.zi"
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections \
    -I"$root/vendor/ziran/include" -I"$work/c" \
    -c "$work/c/platform/audio_runtime.c" -o "$work/audio_runtime.o"
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/vendor/ziran/include" -I"$work/c" \
    "$root/tests/audio_runtime_zi_test.c" "$work/audio_runtime.o" \
    -o "$work/test"
"$work/test"
