#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
kryon=${KRYON_DIR:-"$root/build/packages/kryon"}
entity=${ENTITY_DIR:-"$root/build/packages/entity"}
apps=${APPS_DIR:-"$root/build/packages/apps"}
"$bin/ziran" check --project --offline ${PACKAGE_FLAGS:-} --root "$root/src" \
    --define ANDROID_BUILD --define KRYON_ANDROID_HOST --define __aarch64__ \
    "$root/src/app/app_notifications.zi" "$root/src/platform/android/android_push.zi"
export KRYON_UI="$kryon/src/ui" KRYON_BACKEND="$kryon/src/backend"
export ENTITY_DIR="$entity" APPS_DIR="$apps"
exec python3 "$root/tests/android_jni_zi_test.py" "$bin"
