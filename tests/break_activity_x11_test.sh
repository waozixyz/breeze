#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/break-activity-x11-test
mkdir -p "$work/c" "$work/runtime"
kryon=$root/build/packages/kryon
"$bin/zi2c" --no-main --define PLATFORM_DESKTOP --root "$root/tests" \
    --module-path "$kryon/src/backend" --module-path "$root/build/packages/ziran/std" \
    -o "$work/c" "$root/tests/break_activity_x11.zi"
cat > "$work/c/main.c" <<'C'
#include <stdio.h>
#include "break_activity_x11.h"
int main(void)
{
    while (getchar() != EOF) {
        long long idle = Sample();
        printf("%lld %d %d %d\n", idle, Activity(), MicroIdle(), RestIdle());
        fflush(stdout);
    }
    return 0;
}
C
"${CC:-cc}" -std=c11 -D_DEFAULT_SOURCE -I"$root/build/packages/ziran/include" \
    -I"$work/c" "$work/c"/*.c -ldl -o "$work/test"
# Scrub the owner's session before creating a new private display and auth file.
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    -u SESSION_MANAGER -u GDK_DISPLAY YUE_DESKTOP_RECOVERY=0 \
    TMPDIR="$work/runtime" xvfb-run -a -s '-screen 0 800x600x24 -nolisten tcp' \
    env XDG_SESSION_TYPE=x11 DBUS_SESSION_BUS_ADDRESS=invalid: \
    python3 "$root/tests/break_activity_x11_test.py" "$work/test"
