#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work=$root/build/telegram-account-ui-test
rm -rf "$work/c"
mkdir -p "$work/c"
cd "$root"
"$bin/ziran" build --project --offline ${PACKAGE_FLAGS:-} --target=c --no-main \
    --define PLATFORM_DESKTOP --root "$root/src" \
    -o "$work/c" "$root/src/screens/telegram_account.zi"
for header in "$work/c"/p*_session.h "$work/c"/p*_tree.h "$work/c"/p*_tree_input.h "$work/c"/p*_paint_queue.h "$work/c"/p*_scroll_device.h; do
    test -f "$header"
    printf '#include "%s"\n' "${header##*/}"
done > "$work/c/telegram_account_ui_backend.h"
set -- "$root/tests/telegram_account_ui_test.c"
for generated in "$work/c"/*.c; do
    set -- "$@" "$generated"
done
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -I"$work/c" \
    "$@" "$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a" \
    -lm -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    YUE_DESKTOP_RECOVERY=0 "$work/test"
