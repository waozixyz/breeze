#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/screenshot-request-zi-test
source=$root/tests/screenshot_request_behavior.zi
mkdir -p "$work/ir" "$work/c"
"$bin/zi2zir" --root "$root/tests" --module-path "$root/src" \
    --module-path "$root/vendor/ziran/std" -o "$work/ir" "$source"
"$bin/zi2zib" bundle --root "$root/tests" --module-path "$root/src" \
    --module-path "$root/vendor/ziran/std" \
    --entry screenshot_request_behavior:Answer \
    -o "$work/request.zib" "$source"
[ "$("$bin/zi2zib" run "$work/request.zib")" = 42 ]
"$bin/zi2c" --no-main --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/vendor/ziran/std" \
    -o "$work/c" "$source"
"$bin/zi2c" --no-main --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/vendor/ziran/std" \
    -o "$work/c" "$root/tests/screenshot_arguments_link.zi"
cat > "$work/c/main.c" <<'C'
#include "screenshot_request_behavior.h"
void ScreenshotArgumentsHostTest(void);
int main(void) {
    if(Answer() != 42) return 1;
    ScreenshotArgumentsHostTest();
    return 0;
}
C
"${CC:-cc}" -std=c11 -ffunction-sections -fdata-sections \
    -Wl,--gc-sections -I"$root/vendor/ziran/include" -I"$work/c" \
    "$root/tests/screenshot_arguments_host_test.c" \
    "$work/c"/*.c -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "Inbe screenshot request Ziran test passed"
