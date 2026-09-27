#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work="$root/build/activity-host-zi-test"
source="$root/tests/activity_host_behavior.zi"
mkdir -p "$work/c"

gio_define=
gio_libraries=
if pkg-config --exists gio-2.0; then
    gio_define="--define APP_HAVE_GIO"
    gio_libraries=$(pkg-config --libs gio-2.0)
fi

# The optional GIO branch is compiled when available. This test never
# connects to a real desktop bus or display.
# shellcheck disable=SC2086
"$bin/zi2zir" --check-only --define PLATFORM_DESKTOP $gio_define \
    --root "$root/tests" --module-path "$root/src" \
    --module-path "$root/build/packages/ziran/std" "$source"
# shellcheck disable=SC2086
"$bin/zi2c" --define PLATFORM_DESKTOP $gio_define \
    --entry activity_host_behavior:main --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/ziran/std" \
    -o "$work/c" "$source"
# shellcheck disable=SC2086
"${CC:-cc}" -std=c11 -D_DEFAULT_SOURCE -O2 \
    -I"$root/build/packages/ziran/include" -iquote "$work/c" \
    "$work/c"/*.c $gio_libraries -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
    DBUS_SESSION_BUS_ADDRESS=invalid: "$work/test"
echo "Inbe Ziran desktop activity host test passed"
