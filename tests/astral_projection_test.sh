#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work="$root/build/astral-projection-test"
mkdir -p "$work/c"
"$bin/zi2zir" --check-only --root "$root/tests" --module-path "$root/src" \
    --module-path "$root/build/packages/ziran/std" "$root/tests/astral_projection_behavior.zi"
"$bin/zi2c" --no-main --root "$root/tests" --module-path "$root/src" \
    --module-path "$root/build/packages/ziran/std" -o "$work/c" \
    "$root/tests/astral_projection_behavior.zi"
cat > "$work/c/main.c" <<'C'
#include "astral_projection_behavior.h"
#include <stdio.h>
int main(void) {
    int result = Answer();
    if (result != 42) fprintf(stderr, "Astral Projection check failed: %d\n", result);
    return result == 42 ? 0 : 1;
}
C
"${CC:-cc}" -std=c11 -I"$root/build/packages/ziran/include" -I"$work/c" \
    "$work/c"/*.c "$root/build/ziran-toolchain/libziran.a" -lm -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS "$work/test"
python3 "$root/tests/astral_projection_content_test.py"
echo "Astral Projection course, clock and translated guidance passed"
