#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/sync-worker-host-test

mkdir -p "$work/generated"
"$bin/zi2zir" --check-only --define PLATFORM_DESKTOP --root "$root/src" \
    "$root/src/app/sync_worker_host.zi"
"$bin/zi2c" --define PLATFORM_DESKTOP \
    --entry sync_worker_host_link:main --root "$root/tests" \
    --module-path "$root/src" -o "$work/generated" \
    "$root/tests/sync_worker_host_link.zi"

"${CC:-cc}" -std=c11 -D_DEFAULT_SOURCE -O2 -pthread \
    -I"$root/build/packages/ziran/include" -iquote "$work/generated" \
    "$work/generated"/*.c -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
    "$work/test"

"$bin/zi2zir" --check-only --define PLATFORM_WEB --root "$root/src" \
    "$root/src/app/sync_worker_host.zi"
echo "Inbe Ziran sync worker host test passed"
