#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/telegram-account-ui-test
mkdir -p "$work/c"
"$bin/zi2c" --no-main --define PLATFORM_DESKTOP --root "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kryon/src/backend" \
    --module-path "kryon=$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kss/src" --module-path "oqs=$root/build/packages/oqs/src" \
    --module-path "$root/build/packages/daochi-client" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/c" "$root/src/screens/telegram_account.zi"
set -- "$root/tests/telegram_account_ui_test.c"
for generated in "$work/c"/*.c "$work/c/screens"/*.c; do
    set -- "$@" "$generated"
done
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -I"$work/c" \
    "$@" "$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a" \
    -lm -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    YUE_DESKTOP_RECOVERY=0 "$work/test"
