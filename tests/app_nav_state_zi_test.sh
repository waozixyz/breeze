#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
mkdir -p "$root/build"
work=$(mktemp -d "$root/build/app-nav-state-zi-test.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM

"$bin/zi2zir" --check-only --root "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "oqs=$root/build/packages/oqs/src" \
    "$root/src/app/app_nav_state.zi"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "oqs=$root/build/packages/oqs/src" \
    -o "$work/gen" "$root/src/app/app_nav_state.zi"
"${CC:-cc}" -std=c11 -Wall -Wextra -Werror \
    -Wno-unused-function -Wno-unused-variable \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -I"$work/gen" \
    "$root/tests/app_nav_state_link_test.c" \
    "$work/gen/app/app_nav_state.c" \
    "$work/gen/bottom_nav_policy.c" -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "Inbe navigation state source and generated C behavior passed"
