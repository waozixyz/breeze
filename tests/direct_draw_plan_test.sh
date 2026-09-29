#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=${DIRECT_DRAW_PLAN_BUILD_DIR:-"$root/build/direct-draw-plan-test"}
source=$root/tests/direct_draw_plan_behavior.zi

mkdir -p "$work/ir"
"$bin/ziran" ir --root "$root/tests" --module-path "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/ir" "$source"
"$bin/ziran" bundle --root "$root/tests" --module-path "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" \
    --entry direct_draw_plan_behavior:Answer \
    -o "$work/source.zib" "$source"
"$bin/ziran" bundle --root "$work/ir" --module-path "$work/ir" \
    --entry direct_draw_plan_behavior:Answer \
    -o "$work/saved.zib" "$work/ir/direct_draw_plan_behavior.zir"
cmp "$work/source.zib" "$work/saved.zib"
test "$("$bin/ziran" run "$work/source.zib")" = 0
test "$("$bin/ziran" run "$work/saved.zib")" = 0
