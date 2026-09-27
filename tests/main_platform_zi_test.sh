#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
raylib=${2:-"$root/vendor-builds/linux/x86_64/raylib/libraylib.a"}
work=$(mktemp -d "$root/build/main-platform-zi.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
"$bin/zi2c" --no-main --define PLATFORM_DESKTOP --root "$root/tests" \
    --module-path "$root/src/platform" --module-path "$root/vendor/ziran/std" \
    -o "$work/c" "$root/tests/main_platform_behavior.zi"
"${CC:-cc}" -std=c11 -O2 -DZIRAN_BOUNDS_CHECK \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/vendor/ziran/include" -iquote "$work/c" \
    "$work/c"/*.c "$raylib" ${RAY_LDLIBS:-} -lm -ldl -pthread -latomic -o "$work/test"
cd "$work"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
    ./test 2> stderr
test "$(cat stderr)" = "WARNING: IMAGE: retained
INFO: values 42 3.25 inbe.test"
test "$(cat inbe.log)" = '[ERROR] WGL test failure'
echo "Inbe Ziran process setup and logging test passed"
