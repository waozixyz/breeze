#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
mkdir -p "$root/build"
work=$(mktemp -d "$root/build/android-lifecycle-zi-test.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM

"$bin/ziran" check --project --offline ${PACKAGE_FLAGS:-} --root "$root/src" \
    "$root/src/platform/android/android_lifecycle.zi"
"$bin/ziran" build --target=c --project --offline ${PACKAGE_FLAGS:-} --no-main --root "$root/src" \
    -o "$work/gen" "$root/src/platform/android/android_lifecycle.zi" \
    "$root/src/app/current_app.zi" "$root/src/app/exercise_types.zi" \
    "$root/src/app/practice_lifecycle.zi"
"$bin/ziran" build --target=c --project --offline ${PACKAGE_FLAGS:-} --no-main --root "$root/tests" \
    -o "$work/test-host" "$root/tests/android_lifecycle_test_host.zi"
"${CC:-cc}" -std=c11 -Wall -Wextra -Werror -Wno-unused-function \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -I"$work/gen" \
    "$root/tests/android_lifecycle_link_test.c" \
    "$work/gen/android_lifecycle.c" \
    "$work/gen/current_app.c" "$work/gen/exercise_types.c" \
    "$work/gen/practice_lifecycle.c" \
    "$work/test-host"/*.c \
    -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
"$bin/ziran" build --target=c --project --offline ${PACKAGE_FLAGS:-} --root "$root" --entry android_pause_behavior:main --exe \
    -o "$work/pause" "$root/tests/android_pause_behavior.zi"
rg --files "$work/pause" -g '*.c' | \
    rg '/(android_pause_behavior|android_lifecycle|current_app|practice_lifecycle|android_lifecycle_test_host|main|zir_main|zir_entry)\.c$' \
    > "$work/pause-sources.rsp"
"${CC:-cc}" -std=c11 -Wall -Wextra -Werror -Wno-unused-function \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -I"$work/pause" \
    @"$work/pause-sources.rsp" -o "$work/pause-test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/pause-test"
"$bin/ziran" build --target=c --project --offline ${PACKAGE_FLAGS:-} --no-main --root "$root/src" \
    -o "$work/timer" "$root/src/platform/android/android_timer_host.zi"
"${CC:-cc}" -std=c11 -Wall -Wextra -Werror -Wno-unused-function \
    -I"$root/build/packages/ziran/include" -I"$work/timer" \
    -c "$work/timer/android_timer_host.c" \
    -o "$work/timer_host.o"
echo "Inbe Android lifecycle state and Zi timer host compilation passed"
