#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work="$root/build/habits-card-layout-test"
mkdir -p "$work"
"$bin/zi2zib" bundle --root "$root/tests" \
    --entry habits_card_layout_behavior:Answer \
    -o "$work/layout.zib" "$root/tests/habits_card_layout_behavior.zi"
[ "$("$bin/zi2zib" run "$work/layout.zib")" = 42 ]
echo "PASS independent habit columns, collapse, later rows, and narrow layouts"
