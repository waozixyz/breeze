#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work="$root/build/storage-thread-buffer-zi-test"
source="$root/tests/storage_thread_buffer_behavior.zi"
mkdir -p "$work/c"

"$bin/zi2zir" --check-only --define PLATFORM_DESKTOP \
    --root "$root/tests" --module-path "$root/src" "$source"
"$bin/zi2c" --define PLATFORM_DESKTOP \
    --entry storage_thread_buffer_behavior:main --root "$root/tests" \
    --module-path "$root/src" -o "$work/c" "$source"
"${CC:-cc}" -std=c11 -O2 -I"$root/vendor/ziran/include" \
    -iquote "$work/c" "$work/c"/*.c -lpthread -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY \
    "$work/test"
echo "Inbe Ziran thread-local settings buffer test passed"
