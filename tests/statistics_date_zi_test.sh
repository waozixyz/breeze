#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$(mktemp -d "$root/build/statistics-date-test.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
source=$root/tests/statistics_date_behavior.zi

"$bin/ziran" bundle --root "$root" \
    --module-path "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --entry statistics_date_behavior:Answer \
    -o "$work/date.zib" "$source"
test "$("$bin/ziran" run "$work/date.zib")" = 42

"$bin/zi2c" --no-main --root "$root" \
    --module-path "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    -o "$work/c" "$source"
cat > "$work/c/main.c" <<'C'
#include "statistics_date_behavior.h"
int main(void) { return Answer() == 42 ? 0 : 1; }
C
"${CC:-cc}" -std=c11 -ffunction-sections -fdata-sections \
    -Wl,--gc-sections -I"$root/build/packages/ziran/include" \
    -I"$work/c" -I"$work/c/tests" \
    "$work/c"/*.c "$work/c/tests"/*.c -o "$work/date-test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/date-test"
echo "Statistics civil dates passed"
