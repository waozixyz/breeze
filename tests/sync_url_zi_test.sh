#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:-"$root/build/packages/ziran/build/bin/ziran"}
work=$root/build/sync-url-zi-test

mkdir -p "$work"
"$ziran" bundle --project --offline ${PACKAGE_FLAGS:-} --root "$root/tests" \
    --entry sync_url_behavior:Check \
    -o "$work/sync_url.zx" "$root/tests/sync_url_behavior.zi"
test "$("$ziran" run "$work/sync_url.zx")" = 0
