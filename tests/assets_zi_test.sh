#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/assets-zi-test

mkdir -p "$work/c"
"$bin/zi2c" --no-main --root "$root/tests" --module-path "$root/src" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/c" "$root/tests/assets_link_behavior.zi"
mkdir -p "$work/c/app"
cp "$work/c/assets.h" "$work/c/app/assets.h"
python3 "$root/scripts/embed-app-assets.py" "$work/assets.c" \
    "$root/assets/styles/inbe.kss" "$root/locales/index.txt" \
    "$root/assets/pet/egg1.png" \
    "$root/build/packages/kss/styles/material.kss"
"${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK -Wall -Wextra \
    -I"$root/build/packages/ziran/include" -I"$work/c" -I"$root/src/app" \
    "$root/tests/assets_link_test.c" \
    "$work/assets.c" "$work/c"/*.c -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "Inbe embedded asset Ziran/native link test passed"
