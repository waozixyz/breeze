#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
"$bin/ziran" check --project --offline ${PACKAGE_FLAGS:-} --root "$root/src" \
    "$root/src/platform/android/android_health.zi"
exec python3 "$root/tests/android_jni_zi_test.py" "$bin"
