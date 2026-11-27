#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work=$(mktemp -d "$root/build/statistics-date-test.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
source=$root/tests/statistics_date_behavior.zi

"$bin/ziran" bundle --project --offline ${PACKAGE_FLAGS:-} --root "$root" \
    --entry statistics_date_behavior:Answer \
    -o "$work/date.zx" "$source"
test "$("$bin/ziran" run "$work/date.zx")" = 42

"$bin/ziran" build --target=c --project --offline ${PACKAGE_FLAGS:-} --no-main --root "$root" \
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
