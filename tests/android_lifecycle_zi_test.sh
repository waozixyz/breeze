#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
mkdir -p "$root/build"
work=$(mktemp -d "$root/build/android-lifecycle-zi-test.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM

"$bin/zi2zir" --check-only --root "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" \
    "$root/src/platform/android/android_lifecycle.zi"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/gen" "$root/src/platform/android/android_lifecycle.zi" \
    "$root/src/app/current_app.zi" "$root/src/app/exercise_types.zi"
"${CC:-cc}" -std=c11 -Wall -Wextra -Werror -Wno-unused-function \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -I"$work/gen" -I"$work/gen/app" \
    "$root/tests/android_lifecycle_link_test.c" \
    "$work/gen/platform/android/android_lifecycle.c" \
    "$work/gen/app/current_app.c" "$work/gen/app/exercise_types.c" \
    -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
"$bin/zi2c" --no-main --root "$root/src" \
    -o "$work/timer" "$root/src/platform/android/android_timer_host.zi"
"${CC:-cc}" -std=c11 -Wall -Wextra -Werror -Wno-unused-function \
    -I"$root/build/packages/ziran/include" -I"$work/timer" \
    -c "$work/timer/platform/android/android_timer_host.c" \
    -o "$work/timer_host.o"
echo "Inbe Android lifecycle state and Zi timer host compilation passed"
