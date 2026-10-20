#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work="$root/build/workout-test"
rm -rf "$work"
mkdir -p "$work/c"
"$bin/zi2zir" --check-only --root "$root/tests" --module-path "$root/src" \
    --module-path "$root/build/packages/ziran/std" "$root/tests/workout_behavior.zi"
"$bin/zi2c" --no-main --root "$root/tests" --module-path "$root/src" \
    --module-path "$root/build/packages/ziran/std" -o "$work/c" \
    "$root/tests/workout_behavior.zi"
cat > "$work/c/main.c" <<'C'
#include "workout_behavior.h"
#include <stdio.h>
int main(void) {
    int result = Answer();
    if (result != 42) fprintf(stderr, "7-Minute Workout check failed: %d\n", result);
    return result == 42 ? 0 : 1;
}
C
"${CC:-cc}" -std=c11 -I"$root/build/packages/ziran/include" -I"$work/c" \
    "$work/c"/*.c "$root/build/ziran-toolchain/libziran.a" -lm -lz -o "$work/test"
(cd "$root/tests" && env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS "$work/test")
echo "7-Minute Workout clock, figure and translated guidance passed"
