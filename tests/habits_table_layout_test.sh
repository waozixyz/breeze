#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work="$root/build/habits-table-layout-test"
mkdir -p "$work"
"$bin/zi2zib" bundle --root "$root/tests" \
    --entry habits_table_layout_behavior:Answer \
    -o "$work/layout.zib" "$root/tests/habits_table_layout_behavior.zi"
[ "$("$bin/zi2zib" run "$work/layout.zib")" = 42 ]
echo "PASS habit table day widths and rows below the open habit"
