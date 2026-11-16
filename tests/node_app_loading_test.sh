#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:?Pass the Ziran compiler}
runtime=${2:?Pass its exact runtime library}
work="$root/build/node-app-loading-test"
mkdir -p "$work/c"
"$ziran" build --root "$root" --target=c --entry download_recovery_behavior:main \
    -o "$work/recovery-c" "$root/tests/download_recovery_behavior.zi"
"${CC:-cc}" -std=c11 -O1 -I"$root/build/packages/ziran/include" \
    $(find "$work/recovery-c" -type d -printf ' -iquote %p') \
    $(find "$work/recovery-c" -name '*.c') -o "$work/recovery-test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS "$work/recovery-test"
echo 'Download recovery: bounded backoff, status classification, package resource boundaries'
"$ziran" build --root "$root" --target=c --entry node_app_loading_behavior:main \
    -o "$work/c" "$root/tests/node_app_loading_behavior.zi"
"${CC:-cc}" -std=c11 -O1 -I"$root/build/packages/ziran/include" \
    $(find "$work/c" -type d -printf ' -iquote %p') \
    $(find "$work/c" -name '*.c') -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS "$work/test"
echo 'Node app loading: initial pictures, movement sprites, child changes and return'

mkdir -p "$work/cache-c"
"$ziran" build --root "$root" --project --offline --target=c --define PLATFORM_DESKTOP --entry node_child_packages_behavior:main \
    -o "$work/cache-c" "$root/tests/node_child_packages_behavior.zi"
"${CC:-cc}" -std=c11 -O1 -ffunction-sections -fdata-sections \
    -I"$root/build/packages/ziran/include" \
    $(find "$work/cache-c" -type d -printf ' -iquote %p') \
    $(find "$work/cache-c" -name '*.c') "$runtime" \
    -Wl,--gc-sections -lm -lpthread -o "$work/cache-test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS "$work/cache-test"
echo 'Node child cache: bounded pressure eviction, active/retired/paint borrows, exact disk preservation and oversized refusal'
