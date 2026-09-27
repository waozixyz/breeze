#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work="$root/build/plan9-host-test"
mkdir -p "$work/stubs" "$work/vfs" "$work/plan9-c"

for test in stubs vfs; do
    extra=
    if [ "$test" = vfs ]; then
        extra="--define PLAN9_SQLITE_VFS"
    fi
    source="$root/tests/plan9_${test}_behavior.zi"
    # shellcheck disable=SC2086
    "$bin/zi2zir" --check-only --define PLAN9_BUILD $extra \
        --root "$root/tests" --module-path "$root/src" \
        --module-path "$root/vendor/ziran/std" "$source"
    # shellcheck disable=SC2086
    "$bin/zi2c" --define PLAN9_BUILD $extra --entry "plan9_${test}_behavior:main" \
        --root "$root/tests" --module-path "$root/src" \
        --module-path "$root/vendor/ziran/std" -o "$work/$test" "$source"
    "${CC:-cc}" -std=c11 -D_DEFAULT_SOURCE -O2 -ffunction-sections -fdata-sections \
        -I"$root/vendor/ziran/include" -iquote "$work/$test" \
        "$work/$test"/*.c -Wl,--gc-sections -o "$work/$test-test"
    env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY "$work/$test-test"
done

"$bin/zi2c" --no-main --plan9 --define PLAN9_BUILD --root "$root/src" \
    --module-path "$root/vendor/ziran/std" -o "$work/plan9-c" \
    "$root/src/platform/plan9/entry.zi" \
    "$root/src/platform/plan9/sqlite3_stub.zi" \
    "$root/src/platform/plan9/storage_import_stub.zi"
"$bin/zi2c" --no-main --plan9 --define PLAN9_BUILD --define PLAN9_SQLITE_VFS \
    --root "$root/src" --module-path "$root/vendor/ziran/std" \
    -o "$work/plan9-vfs-c" "$root/src/platform/plan9/sqlite_plan9_vfs.zi"
printf '%s\n' 'Plan 9 Ziran stubs and VFS host behavior passed; native source emitted'
