#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=${SCROLL_INPUT_TEST_BUILD_DIR:-"$root/build/scroll-input-test"}
source=$root/tests/scroll_input_behavior.zi
ui=${KRYON_UI_DIR:-$root/build/packages/kryon/src/ui}

mkdir -p "$work/ir"
"$bin/zi2zir" --root "$root/tests" --module-path "$root/src" \
    --module-path "$ui" \
    -o "$work/ir" "$source"
for input in source saved; do
    if test "$input" = source; then
        file=$source
        module_root=$root/tests
        module_path=$root/src
        kryon_path=$ui
    else
        file=$work/ir/scroll_input_behavior.zir
        module_root=$work/ir
        module_path=$work/ir
        kryon_path=$work/ir
    fi
    mkdir -p "$work/$input"
    "$bin/zi2zib" bundle --root "$module_root" \
        --module-path "$module_path" --module-path "$kryon_path" \
        --entry scroll_input_behavior:Answer \
        -o "$work/$input/scroll_input.zib" "$file"
    test "$("$bin/zi2zib" run "$work/$input/scroll_input.zib")" = 42
done
cmp "$work/source/scroll_input.zib" "$work/saved/scroll_input.zib"
echo "scroll input Ziran test passed"
