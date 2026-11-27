#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work="$root/build/app-click-block-test"
rm -rf "$work/generated"
mkdir -p "$work/generated"
"$bin/ziran" build --target=c --project --offline ${PACKAGE_FLAGS:-} --no-main --define PLATFORM_DESKTOP --root "$root/tests" \
    -o "$work/generated" "$root/tests/app_click_block_behavior.zi"
cat > "$work/generated/main.c" <<'C'
#include "app_click_block_behavior.h"
#include <stdio.h>
int main(void) {
    int result = Check();
    if (result) fprintf(stderr, "click blocking failed at step %d\n", result);
    return result ? 1 : 0;
}
C
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections \
    -I"$root/build/packages/ziran/include" -I"$work/generated" \
    $(find "$work/generated" -name '*.c') \
    -Wl,--gc-sections -lm -ldl -lpthread -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS "$work/test"
echo 'Retained click and held-press cancellation passed'
