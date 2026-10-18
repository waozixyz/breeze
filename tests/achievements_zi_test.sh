#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:-"$root/build/ziran-toolchain/bin/ziran"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
work=$root/build/achievements-test
mkdir -p "$work/generated"
"$ziran" build --target=c --define PLATFORM_DESKTOP --root "$root/tests" \
    --module-path "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kryon/src/backend" \
    --module-path "kryon=$root/build/packages/kryon/src/ui" \
    --module-path "kryon=$root/build/packages/kryon/src/backend" \
    --module-path "$root/build/packages/kss/src" \
    --module-path "$root/build/packages/game2d/src" \
    --module-path "oqs=$root/build/packages/oqs/src" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" \
    --entry achievements_behavior:Check -o "$work/generated" \
    "$root/tests/achievements_behavior.zi" "$root/tests/sync_test_host.zi"
cat > "$work/generated/main.c" <<'C'
#include "achievements_behavior.h"
#include <stdio.h>
int main(void) {
    int result = Check();
    if (result) fprintf(stderr, "achievement checks failed: %d\n", result);
    return result ? 1 : 0;
}
C
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections \
    -I"$root/build/packages/ziran/include" -I"$work/generated" \
    -I"$root/vendor-builds/sqlite" \
    -I"$root/vendor-builds/linux/x86_64/inbe-liboqs/include" \
    "$work/generated"/*.c "$root/vendor-builds/sqlite/sqlite3.c" "$liboqs" \
    -Wl,--gc-sections -ldl -lpthread -lz -lm -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    APP_DATA_ROOT=/tmp/inbe-achievements-test/data "$work/test"
