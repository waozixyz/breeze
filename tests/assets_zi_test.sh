#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work=$root/build/assets-zi-test
compile_only=${2:-}
if [ -n "$compile_only" ] && [ "$compile_only" != "--compile-only" ]; then
    echo "usage: $0 [compiler-dir] [--compile-only]" >&2
    exit 2
fi

mkdir -p "$work/c"
"$bin/zi2c" --no-main --root "$root/tests" --module-path "$root/src" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/c" "$root/tests/assets_link_behavior.zi"
mkdir -p "$work/c/app"
cp "$work/c/assets.h" "$work/c/app/assets.h"
printf '%s' 'reviewed controller fixture' > "$work/reviewed-controller.zx"
python3 "$root/scripts/embed-app-assets.py" "$work/assets.c" \
    "$root/assets/styles/inbe.css" "$root/locales/index.txt" \
    "$root/assets/pet/egg1.png" \
    "$root/build/packages/css/styles/material.css" \
    --apps-controller "$work/reviewed-controller.zx"
"${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK -Wall -Wextra \
    -I"$root/build/packages/ziran/include" -I"$work/c" -I"$root/src/app" \
    "$root/tests/assets_link_test.c" \
    "$work/assets.c" "$work/c"/*.c -o "$work/test"
if [ "$compile_only" = "--compile-only" ]; then
    exit 0
fi
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test" "$root/assets/styles/inbe.css"
echo "Inbe embedded asset Ziran/native link test passed"
