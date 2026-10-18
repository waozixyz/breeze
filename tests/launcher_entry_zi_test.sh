#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work="$root/build/launcher-entry-test"
mkdir -p "$work/generated"
"$bin/zi2c" --no-main --root "$root/tests" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/generated" "$root/tests/launcher_entry_behavior.zi"
cat > "$work/generated/main.c" <<'C'
#include "launcher_entry_behavior.h"
#include <stdio.h>
int main(void) {
    int result = LauncherEntryBehavior();
    if (result) fprintf(stderr, "launcher entry check %d failed\n", result);
    return result;
}
C
"${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK \
    -I"$root/build/packages/ziran/include" -I"$work/generated" \
    "$work/generated"/*.c -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS "$work/test"
echo 'Launcher entry quoting and stable app identity passed'
