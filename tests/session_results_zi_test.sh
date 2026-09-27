#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$(mktemp -d "$root/build/session-results-test.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
source=$root/tests/session_results_behavior.zi

"$bin/zi2zir" --check-only --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" "$source"
"$bin/zi2c" --no-main --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" -o "$work/c" "$source"
cat > "$work/c/main.c" <<'C'
#include "session_results_behavior.h"
int main(void) { return Answer() == 42 ? 0 : 1; }
C
"${CC:-cc}" -std=c11 -ffunction-sections -fdata-sections \
    -Wl,--gc-sections -I"$root/build/packages/ziran/include" \
    -I"$work/c" "$work/c"/*.c -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"

flow=$root/tests/session_results_flow_behavior.zi
"$bin/zi2zir" --check-only --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" "$flow"
"$bin/zi2c" --no-main --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" -o "$work/flow" "$flow"
cat > "$work/flow/main.c" <<'C'
#include "session_results_flow_behavior.h"
int main(void) { return Answer() == 42 ? 0 : 1; }
C
"${CC:-cc}" -std=c11 -ffunction-sections -fdata-sections \
    -Wl,--gc-sections -I"$root/build/packages/ziran/include" \
    -I"$work/flow" "$work/flow"/*.c \
    "$root/tests/session_results_flow_host.c" -o "$work/flow-test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/flow-test"
echo "Session results Ziran test passed"
