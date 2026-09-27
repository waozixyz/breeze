#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/update-policy-zi-test
mkdir -p "$work/c"
"$bin/zi2zib" bundle --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/ziran/std" \
    --entry update_policy_behavior:Answer \
    -o "$work/update-policy.zib" \
    "$root/tests/update_policy_behavior.zi"
[ "$("$bin/zi2zib" run "$work/update-policy.zib")" = 42 ]
"$bin/zi2c" --no-main --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/ziran/std" \
    -o "$work/c" "$root/tests/update_policy_behavior.zi"
"${CC:-cc}" -std=c11 -fsyntax-only \
    -I"$root/build/packages/ziran/include" -I"$work/c" "$work/c"/*.c
echo "Inbe update policy Ziran test passed"
