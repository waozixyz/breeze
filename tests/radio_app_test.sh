#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:-"$root/build/packages/ziran/build/bin/ziran"}
standard=${2:-"$root/build/packages/ziran/std"}
work="$root/build/radio-test"
mkdir -p "$work"
# Match the app build's scoped package exports, including Kryon's widget aliases.
cd "$root"
# shellcheck disable=SC2086
"$ziran" bundle --project --offline ${PACKAGE_FLAGS:-} --root "$root" \
    --define KRYON_HOSTED_UI \
    --entry radio:Main -o "$work/radio.zx" "$root/apps/radio/radio.zi"
library=${ZIRAN_LIB:-"$(dirname "$ziran")/../libziran.a"}
"${CC:-cc}" -std=c11 -O1 -g -fsanitize=address,undefined \
    -I"$(dirname "$standard")/include" "$root/tests/radio_app_test.c" \
    "$library" -lm -lpthread -o "$work/app-test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    YUE_DESKTOP_RECOVERY=0 ASAN_OPTIONS=detect_leaks=0 "$work/app-test" "$work/radio.zx"
