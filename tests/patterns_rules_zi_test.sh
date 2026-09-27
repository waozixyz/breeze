#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$(mktemp -d "$root/build/patterns-rules-test.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
source=$root/tests/patterns_rules_behavior.zi

"$bin/zi2zir" --check-only --root "$root/tests" \
    --module-path "$root/src" "$source"
"$bin/zi2zib" bundle --root "$root/tests" \
    --module-path "$root/src" \
    --entry patterns_rules_behavior:Answer \
    -o "$work/patterns.zib" "$source"
test "$("$bin/zi2zib" run "$work/patterns.zib")" = 42
"$bin/zi2c" --no-main --root "$root/tests" \
    --module-path "$root/src" -o "$work/c" "$source"
cat > "$work/c/main.c" <<'C'
#include "patterns_rules_behavior.h"
int main(void) { return Answer() == 42 ? 0 : 1; }
C
"${CC:-cc}" -std=c11 -I"$root/build/packages/ziran/include" \
    -I"$work/c" "$work/c"/*.c -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "Patterns preset Ziran test passed"
