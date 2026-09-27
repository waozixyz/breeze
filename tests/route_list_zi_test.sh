#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
include=${ZIRAN_INCLUDE:-"$root/build/packages/ziran/include"}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM

source=$root/tests/route_list_behavior.zi
"$bin/zi2zir" --root "$root/tests" --module-path "$root/src" \
    -o "$work/ir" "$source"
"$bin/zi2zib" bundle --root "$root/tests" --module-path "$root/src" \
    --entry route_list_behavior:Answer -o "$work/source.zib" "$source"
"$bin/zi2zib" bundle --root "$work/ir" \
    --entry route_list_behavior:Answer -o "$work/saved.zib" \
    "$work/ir/route_list_behavior.zir"
cmp "$work/source.zib" "$work/saved.zib"
test "$("$bin/zi2zib" run "$work/source.zib")" = 42
test "$("$bin/zi2zib" run "$work/saved.zib")" = 42

"$bin/zi2c" --no-main --root "$root/tests" --module-path "$root/src" \
    -o "$work/c" "$source"
cat > "$work/main.c" <<'C'
#include "route_list_behavior.h"
int main(void) { return Answer() == 42 ? 0 : 1; }
C
"${CC:-cc}" -std=c11 -I"$include" -I"$work/c" \
    "$work/c/route_list.c" "$work/c/route_list_behavior.c" \
    "$work/main.c" -o "$work/test"
"$work/test"
