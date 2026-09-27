#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$(mktemp -d "$root/build/habit-session-rules-test.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
source=$root/tests/habit_session_rules_behavior.zi

"$bin/ziran" bundle --root "$root" \
    --module-path "$root/src" \
    --entry habit_session_rules_behavior:Answer \
    -o "$work/rules.zib" "$source"
test "$("$bin/ziran" run "$work/rules.zib")" = 42

"$bin/zi2c" --no-main --root "$root" \
    --module-path "$root/src" \
    -o "$work/c" "$source"
cat > "$work/c/main.c" <<'C'
#include "habit_session_rules_behavior.h"
int main(void) { return Answer() == 42 ? 0 : 1; }
C
"${CC:-cc}" -std=c11 -ffunction-sections -fdata-sections \
    -Wl,--gc-sections -I"$root/vendor/ziran/include" \
    -I"$work/c" -I"$work/c/tests" \
    "$work/c"/*.c "$work/c/tests"/*.c -o "$work/rules-test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/rules-test"
echo "Habit session second parsing passed"
