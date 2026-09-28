#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:-"$root/build/ziran-toolchain/bin/ziran"}
work=$root/build/sync-url-zi-test

mkdir -p "$work"
"$ziran" bundle --root "$root/tests" \
    --module-path "$root/build/packages/daochi-client" \
    --module-path "$root/build/packages/ziran/std" \
    --entry sync_url_behavior:Check \
    -o "$work/sync_url.zib" "$root/tests/sync_url_behavior.zi"
test "$("$ziran" run "$work/sync_url.zib")" = 0
