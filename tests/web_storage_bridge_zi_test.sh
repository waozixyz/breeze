#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$(mktemp -d "$root/build/web-storage-bridge-test.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM

for platform in desktop android; do
    mkdir -p "$work/$platform"
    set --
    if [ "$platform" = android ]; then
        set -- --define ANDROID_BUILD
    fi
    "$bin/zi2c" --no-main \
        --root "$root" --module-path "$root/src" \
        --module-path "$root/build/packages/ziran/std" "$@" \
        -o "$work/$platform" "$root/tests/web_storage_bridge_link.zi" \
        "$root/src/app/host_services.zi" "$root/src/platform/web_bridge.zi"
    find "$work/$platform" -type f -name '*.c' -exec \
        "${CC:-cc}" -std=c11 -Wall -Wextra -Werror -Wno-unused-function \
        -ffunction-sections -fdata-sections -Wl,--gc-sections \
        -I"$root/build/packages/ziran/include" -I"$work/$platform" \
        -I"$work/$platform/src/app" -I"$work/$platform/src/platform" \
        -I"$work/$platform/tests" \
        -o "$work/$platform-test" {} +
    env -u DISPLAY -u WAYLAND_DISPLAY "$work/$platform-test"
done
node "$root/tests/web_storage_test.mjs"
node "$root/tests/web_host_test.mjs"
