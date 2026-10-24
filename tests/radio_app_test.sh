#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:-"$root/build/ziran-toolchain/bin/ziran"}
standard=${2:-"$root/build/packages/ziran/std"}
ui=${3:-"$root/build/packages/kryon/src/ui"}
work="$root/build/radio-test"
mkdir -p "$work"
"$ziran" bundle --root "$root" --module-path "$root/src" $(sh "$root/scripts/package-paths.sh" "$root/build/packages") \
    --module-path "$ui" --define KRYON_HOSTED_UI --module-path "$standard" \
    --entry radio:Main -o "$work/radio.zx" "$root/apps/radio/radio.zi"
library=${ZIRAN_LIB:-"$(dirname "$ziran")/../libziran.a"}
"${CC:-cc}" -std=c11 -O1 -g -fsanitize=address,undefined \
    -I"$(dirname "$standard")/include" "$root/tests/radio_app_test.c" \
    "$library" -lm -lpthread -o "$work/app-test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    YUE_DESKTOP_RECOVERY=0 ASAN_OPTIONS=detect_leaks=0 "$work/app-test" "$work/radio.zx"
