#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
"$bin/zi2zir" --check-only --root "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" --module-path "$root/build/packages/daochi-client" $(sh "$root/scripts/package-paths.sh" "$root/build/packages") --module-path "$root/build/packages/kryon/src/backend" \
    "$root/src/platform/android/android_push.zi"
exec python3 "$root/tests/android_jni_zi_test.py" "$bin"
