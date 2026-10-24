#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:-"$root/build/ziran-toolchain/bin/ziran"}
work=$root/build/library-reader-test
mkdir -p "$work"
# Source and saved IR must preserve Unicode note bytes and text anchors.
"$ziran" ir --root "$root/tests" --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" -o "$work/ir" "$root/tests/library_reader_behavior.zi"
for mode in source saved; do
    module=$root/tests/library_reader_behavior.zi
    modules=$root/build/packages/kryon/src/ui
    module_root=$root/tests
    if [ "$mode" = saved ]; then
        module=$work/ir/library_reader_behavior.zir
        modules=$work/ir
        module_root=$work/ir
    fi
    "$ziran" bundle --root "$module_root" --module-path "$modules" \
        --module-path "$root/build/packages/ziran/std" --entry library_reader_behavior:Check \
        -o "$work/$mode.zx" "$module"
    result=$("$ziran" run "$work/$mode.zx")
    test "$result" = 0 || { echo "Library reader $mode returned $result"; exit 1; }
done
cmp "$work/source.zx" "$work/saved.zx"
echo 'Library anchors survive reflow and annotation records preserve highlights, Unicode and multiline notes'
