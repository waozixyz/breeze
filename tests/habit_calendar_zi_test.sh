#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
ui=${2:-"$root/build/packages/kryon/src/ui"}
include=${ZIRAN_INCLUDE:-"$root/build/packages/ziran/include"}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM

source=$root/tests/habit_calendar_behavior.zi
"$bin/ziran" ir --project --offline ${PACKAGE_FLAGS:-} --root "$root/tests"  \
        -o "$work/ir" "$source"
"$bin/ziran" bundle --project --offline ${PACKAGE_FLAGS:-} --root "$root/tests"  \
        --entry habit_calendar_behavior:CalendarAnswer \
    -o "$work/source.zx" "$source"
"$bin/zi2zx" --root "$work/ir" \
    --entry habit_calendar_behavior:CalendarAnswer \
    -o "$work/saved.zx" "$work/ir/habit_calendar_behavior.zir"
cmp "$work/source.zx" "$work/saved.zx"
test "$("$bin/zi2zx" run "$work/source.zx")" = 42
test "$("$bin/zi2zx" run "$work/saved.zx")" = 42

"$bin/ziran" build --target=c --project --offline ${PACKAGE_FLAGS:-} --no-main --root "$root/tests"  \
        -o "$work/c" "$source"
cat > "$work/c/main.c" <<'C'
#include "habit_calendar_behavior.h"
int main(void) { return Answer() == 42 && CalendarAnswer() == 42 ? 0 : 1; }
C
"${CC:-cc}" -std=c11 -I"$include" -I"$work/c" \
    "$work/c"/*.c \
    -lm -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
