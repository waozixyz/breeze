#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
mkdir -p "$root/build"
work=$(mktemp -d "$root/build/android-timer-zi-test.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM

"$bin/zi2zir" --check-only --root "$root/src" \
    "$root/src/platform/android/android_timer.zi"
"$bin/ziran" bundle --root "$root/tests" \
    --module-path "$root/src/platform/android" \
    --entry android_timer_policy_behavior:TimerPolicyCheck \
    -o "$work/timer.zib" "$root/tests/android_timer_policy_behavior.zi"
test "$("$bin/ziran" run "$work/timer.zib")" = 42
"$bin/zi2c" --no-main --define ANDROID_BUILD --root "$root/src" \
    -o "$work/gen" "$root/src/platform/android/android_timer.zi" \
    "$root/src/platform/android/android_timer_host.zi" \
    "$root/src/platform/android/android_mutex.zi"
"${CC:-cc}" -std=c11 -Wall -Wextra -Werror -Wno-unused-function \
    -D_POSIX_C_SOURCE=200809L -DANDROID_BUILD=1 -pthread \
    -I"$root/src" -I"$root/vendor/ziran/include" -I"$work/gen" \
    "$root/tests/android_timer_host_test.c" \
    "$work/gen/platform/android/android_timer_host.c" \
    "$work/gen/platform/android/android_timer.c" \
    "$work/gen/platform/android/android_mutex.c" -o "$work/host-test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/host-test"
echo "Inbe Android timer policy, Zi worker, and native output passed"
