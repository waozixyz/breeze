#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:?Pass the Ziran compiler}
work="$root/build/node-app-loading-test"
mkdir -p "$work/c"
"$ziran" build --root "$root" --target=c --entry node_app_loading_behavior:main \
    -o "$work/c" "$root/tests/node_app_loading_behavior.zi"
"${CC:-cc}" -std=c11 -O1 -I"$root/build/packages/ziran/include" \
    $(find "$work/c" -type d -printf ' -iquote %p') \
    $(find "$work/c" -name '*.c') -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS "$work/test"
echo 'Node app loading: initial pictures, movement sprites, child changes and return'
