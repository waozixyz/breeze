#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$(mktemp -d "$root/build/mood-average-test.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
source=$root/tests/mood_average_behavior.zi

"$bin/ziran" bundle --root "$root" \
    --module-path "$root/src" \
    --entry mood_average_behavior:Answer \
    -o "$work/mood.zib" "$source"
test "$("$bin/ziran" run "$work/mood.zib")" = 42

"$bin/zi2c" --no-main --root "$root" \
    --module-path "$root/src" \
    -o "$work/c" "$source"
cat > "$work/c/main.c" <<'C'
#include "mood_average_behavior.h"
int main(void) { return Answer() == 42 ? 0 : 1; }
C
"${CC:-cc}" -std=c11 -ffunction-sections -fdata-sections \
    -Wl,--gc-sections -I"$root/build/packages/ziran/include" \
    -I"$work/c" -I"$work/c/tests" \
    "$work/c"/*.c "$work/c/tests"/*.c -o "$work/mood-test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/mood-test"
echo "Session mood averages passed"
