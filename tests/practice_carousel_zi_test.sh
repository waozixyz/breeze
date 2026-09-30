#!/bin/sh
set -eu

# Practice pager layout against recording widget doubles.
# SQLite database in a temporary directory.
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:-"$root/build/ziran-toolchain/bin/ziran"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
work=$root/build/practice-carousel-zi-test
include=$root/build/packages/ziran/include

rm -rf "$work"
mkdir -p "$work/generated"
"$ziran" build --target=c --define PLATFORM_DESKTOP --root "$root/tests" \
    --module-path "$root/tests/fakes" --module-path "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kss/src" --module-path "oqs=$root/build/packages/oqs/src" --module-path "kryon=$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kryon/src/backend" \
    --module-path "$root/build/packages/game2d/src" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" \
    --entry practice_carousel_behavior:Check \
    -o "$work/generated" "$root/tests/practice_carousel_behavior.zi" \
    "$root/tests/app_hooks_host.zi" "$root/tests/clock_host.zi"
cat > "$work/generated/main.c" <<'C'
#include "practice_carousel_behavior.h"
#include <stdio.h>
int main(void)
{
    int result = Check();
    if (result != 0) fprintf(stderr, "check failed with code %d\n", result);
    return result == 0 ? 0 : 1;
}
C
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections \
    -I"$include" -I"$work/generated" -I"$root/vendor-builds/sqlite" \
    -I"$root/vendor-builds/linux/x86_64/inbe-liboqs/include" \
    "$work/generated"/*.c "$root/vendor-builds/sqlite/sqlite3.c" "$liboqs" \
    "$root/vendor-builds/linux/x86_64/raylib/libraylib.a" \
    -Wl,--gc-sections -ldl -lpthread -lz -lm -latomic -o "$work/test"
# Storage must never open the real data directory.
APP_DATA_ROOT=/tmp/inbe-practice-carousel-zi-test/data
export APP_DATA_ROOT
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
rm -rf /tmp/inbe-practice-carousel-zi-test
