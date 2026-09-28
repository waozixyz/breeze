#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
ui=${2:-"$root/build/packages/kryon/src/ui"}
include=${ZIRAN_INCLUDE:-"$root/build/packages/ziran/include"}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM

source=$root/tests/habit_calendar_behavior.zi
"$bin/zi2zir" --root "$root/tests" --module-path "$root/src" \
    --module-path "$ui" --module-path "$root/build/packages/ziran/std" -o "$work/ir" "$source"
"$bin/zi2zib" bundle --root "$root/tests" --module-path "$root/src" \
    --module-path "$ui" --module-path "$root/build/packages/ziran/std" --entry habit_calendar_behavior:CalendarAnswer \
    -o "$work/source.zib" "$source"
"$bin/zi2zib" bundle --root "$work/ir" \
    --entry habit_calendar_behavior:CalendarAnswer \
    -o "$work/saved.zib" "$work/ir/habit_calendar_behavior.zir"
cmp "$work/source.zib" "$work/saved.zib"
test "$("$bin/zi2zib" run "$work/source.zib")" = 42
test "$("$bin/zi2zib" run "$work/saved.zib")" = 42

"$bin/zi2c" --no-main --root "$root/tests" --module-path "$root/src" \
    --module-path "$ui" --module-path "$root/build/packages/ziran/std" -o "$work/c" "$source"
cat > "$work/c/main.c" <<'C'
#include "habit_calendar_behavior.h"
int main(void) { return Answer() == 42 && CalendarAnswer() == 42 ? 0 : 1; }
C
"${CC:-cc}" -std=c11 -I"$include" -I"$work/c" \
    "$work/c"/*.c \
    -lm -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
