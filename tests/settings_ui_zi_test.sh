#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
mkdir -p "$root/build"
work=$(mktemp -d "$root/build/settings-ui-zi-test.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
mkdir -p "$work/c"
"$bin/zi2zir" --check-only --root "$root/src" \
    --module-path "$root/vendor/kryon/src/ui" \
    --module-path "$root/vendor/ziran/std" \
    "$root/src/screens/settings/settings_ui.zi"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/vendor/kryon/src/ui" \
    --module-path "$root/vendor/ziran/std" \
    -o "$work/c" "$root/src/screens/settings/settings_ui.zi"
set -- "$root/tests/settings_ui_link_test.c"
for generated in "$work/c"/*.c "$work/c/screens/settings"/*.c; do
    set -- "$@" "$generated"
done
"${CC:-cc}" -std=c11 -ffunction-sections -fdata-sections \
    -Wl,--gc-sections -I"$root/vendor/ziran/include" -I"$work/c" \
    "$@" -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
mkdir -p "$work/device"
"$bin/zi2zir" --check-only --root "$root/src" \
    --module-path "$root/vendor/kryon/src/ui" \
    --module-path "$root/vendor/ziran/std" \
    "$root/src/screens/settings/settings_device.zi"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/vendor/kryon/src/ui" \
    --module-path "$root/vendor/ziran/std" \
    -o "$work/device" "$root/src/screens/settings/settings_device.zi"
"${CC:-cc}" -std=c11 -Wno-unused-function \
    -I"$root/vendor/ziran/include" -I"$work/device" \
    -c "$work/device/screens/settings/settings_device.c" \
    -o "$work/device/settings_device.o"
mkdir -p "$work/breaks"
"$bin/zi2zir" --check-only --root "$root/src" \
    --module-path "$root/vendor/kryon/src/ui" \
    --module-path "$root/vendor/ziran/std" \
    "$root/src/screens/settings/settings_breaks.zi"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/vendor/kryon/src/ui" \
    --module-path "$root/vendor/ziran/std" \
    -o "$work/breaks" "$root/src/screens/settings/settings_breaks.zi"
"${CC:-cc}" -std=c11 -Wno-unused-function -Wno-unused-variable \
    -I"$root/vendor/ziran/include" -I"$work/breaks" \
    -c "$work/breaks/screens/settings/settings_breaks.c" \
    -o "$work/breaks/settings_breaks.o"
mkdir -p "$work/notifications"
"$bin/zi2zir" --check-only --root "$root/src" \
    --module-path "$root/vendor/kryon/src/ui" \
    --module-path "$root/vendor/ziran/std" \
    "$root/src/screens/settings/settings_notifications.zi"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/vendor/kryon/src/ui" \
    --module-path "$root/vendor/ziran/std" \
    -o "$work/notifications" \
    "$root/src/screens/settings/settings_notifications.zi"
"${CC:-cc}" -std=c11 \
    -I"$root/vendor/ziran/include" -I"$work/notifications" \
    -c "$work/notifications/screens/settings/settings_notifications.c" \
    -o "$work/notifications/settings_notifications.o"
echo "Inbe settings UI interaction, device, break, and notifications module compilation passed"
