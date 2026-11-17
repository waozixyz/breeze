#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
mkdir -p "$root/build"
work=$(mktemp -d "$root/build/app-nav-state-zi-test.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM

"$bin/ziran" build --target=c --no-main --project --offline --root "$root/src" -o "$work/gen" "$root/src/app/app_nav_state.zi"
# The link test stands in for these modules, so their headers declare those
# procedures instead of defining inline copies.
"${CC:-cc}" -std=c11 -Wall -Wextra -Werror \
    -Wno-unused-function -Wno-unused-variable -DZIRAN_ROUTE_TYPES_H_SOURCE \
    -DZIRAN_NODE_APPS_H_SOURCE -DZIRAN_APP_RECORDS_H_SOURCE \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -I"$work/gen" -I"$work/gen/app" \
    "$root/tests/app_nav_state_link_test.c" \
    "$work/gen/app_nav_state.c" \
    "$work/gen/bottom_nav_policy.c" "$work/gen/route_list.c" -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "Inbe navigation state source and generated C behavior passed"
