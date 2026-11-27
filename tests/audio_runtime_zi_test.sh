#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM

"$bin/ziran" check --project --offline ${PACKAGE_FLAGS:-} --root "$root/src" \
    "$root/src/platform/audio_runtime.zi"
"$bin/ziran" build --target=c --project --offline ${PACKAGE_FLAGS:-} --no-main --root "$root/src" \
    -o "$work/c" "$root/src/platform/audio_runtime.zi"
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections \
    -I"$root/build/packages/ziran/include" -I"$work/c" \
    -c "$work/c/audio_runtime.c" -o "$work/audio_runtime.o"
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -I"$work/c" \
    "$root/tests/audio_runtime_zi_test.c" "$work/audio_runtime.o" \
    -o "$work/test"
"$work/test"
sh "$root/tests/audio_first_cue_test.sh" "$bin"
sh "$root/tests/audio_cue_assets_test.sh" "$bin"
