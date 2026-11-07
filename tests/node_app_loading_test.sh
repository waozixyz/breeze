#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:?Pass the Ziran compiler}
runtime=${2:?Pass its exact runtime library}
work="$root/build/node-app-loading-test"
mkdir -p "$work/c"
"$ziran" build --root "$root" --target=c --entry node_app_loading_behavior:main \
    -o "$work/c" "$root/tests/node_app_loading_behavior.zi"
"${CC:-cc}" -std=c11 -O1 -I"$root/build/packages/ziran/include" \
    $(find "$work/c" -type d -printf ' -iquote %p') \
    $(find "$work/c" -name '*.c') -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS "$work/test"
echo 'Node app loading: initial pictures, movement sprites, child changes and return'

mkdir -p "$work/cache-c"
"$ziran" build --root "$root" --target=c --define PLATFORM_DESKTOP --entry node_child_packages_behavior:main \
    --module-path "$root/src/platform" \
    --module-path "$root/build/packages/daochi-client" \
    --module-path "$root/build/packages/kss/src" \
    --module-path "$root/build/packages/game2d/src" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kryon/src/backend" \
    $(sh "$root/scripts/package-paths.sh" "$root/build/packages") \
    -o "$work/cache-c" "$root/tests/node_child_packages_behavior.zi"
"${CC:-cc}" -std=c11 -O1 -ffunction-sections -fdata-sections \
    -I"$root/build/packages/ziran/include" \
    $(find "$work/cache-c" -type d -printf ' -iquote %p') \
    $(find "$work/cache-c" -name '*.c') "$runtime" \
    -Wl,--gc-sections -lm -lpthread -o "$work/cache-test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS "$work/cache-test"
echo 'Node child cache: bounded pressure eviction, active/retired/paint borrows, exact disk preservation and oversized refusal'
