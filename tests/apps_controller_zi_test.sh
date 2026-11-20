#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"
ziran=${1:-"$root/build/packages/ziran/build/bin/ziran"}
runtime=${2:-"$root/build/packages/ziran/build/libziran.a"}
controller=${3:-"$root/build/apps-ui/apps.zx"}
output="$root/build/apps-test/controller/trust"
mkdir -p "$output"
"$ziran" build --target=c --project --offline --root "$root/tests" \
    -o "$output/c" "$root/tests/apps_controller_behavior.zi"
"${CC:-cc}" -std=c11 -O2 -ffunction-sections -fdata-sections \
    -I"$root/build/packages/ziran/include" \
    $(find "$output/c" -type d -printf ' -iquote %p') \
    $(find "$output/c" -type f -name '*.c') "$runtime" \
    -Wl,--gc-sections -lm -ldl -pthread -o "$output/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    -u SESSION_MANAGER HARMONY_DESKTOP_RECOVERY=0 YUE_DESKTOP_RECOVERY=0 \
    APPS_CONTROLLER_TEST_BUNDLE="$controller" "$output/test"
echo 'Apps controller: actual payload identity, wrong digest and tampered bytes passed'
