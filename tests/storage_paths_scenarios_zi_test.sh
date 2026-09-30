#!/bin/sh
set -eu

# Where the app keeps its data: the override, XDG, HOME, moving an older
# directory into place, and archiving a conflicting one. data_root() caches
# its result, so each scenario is a fresh process with its own environment.
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:-"$root/build/ziran-toolchain/bin/ziran"}
work=$root/build/storage-paths-scenarios-zi-test
include=$root/build/packages/ziran/include

rm -rf "$work"
mkdir -p "$work/generated"
"$ziran" build --target=c --define PLATFORM_DESKTOP --root "$root/tests" \
    --module-path "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kss/src" --module-path "oqs=$root/build/packages/oqs/src" --module-path "kryon=$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kryon/src/backend" \
    --module-path "$root/build/packages/game2d/src" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" \
    --entry storage_paths_behavior:Check \
    -o "$work/generated" "$root/tests/storage_paths_behavior.zi" \
    "$root/tests/sync_test_host.zi"
cat > "$work/generated/main.c" <<'C'
#include <stdio.h>
#include "storage_paths_behavior.h"
int main(void)
{
    int result = Check();
    if (result != 0) fprintf(stderr, "storage paths check failed with code %d\n", result);
    return result == 0 ? 0 : 1;
}
C
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections \
    -I"$include" -I"$work/generated" -I"$root/vendor-builds/sqlite" \
    "$work/generated"/*.c "$root/vendor-builds/sqlite/sqlite3.c" \
    -Wl,--gc-sections -ldl -lpthread -lz -lm -o "$work/test"

fixture=$(mktemp -d /tmp/inbe-storage-paths-XXXXXX)
trap 'rm -rf "$fixture"' EXIT HUP INT TERM
failures=0

expect_root() {
    label=$1
    wanted=$2
    shift 2
    got=$(env -u DISPLAY -u WAYLAND_DISPLAY "$@" "$work/test")
    if [ "$got" != "$wanted" ]; then
        echo "FAIL $label: got $got, want $wanted" >&2
        failures=$((failures + 1))
    fi
    if [ ! -d "$wanted" ]; then
        echo "FAIL $label: root was not created" >&2
        failures=$((failures + 1))
    fi
}

expect_root "override root" "$fixture/override-root" \
    APP_DATA_ROOT="$fixture/override-root"

expect_root "xdg root" "$fixture/inbe" \
    -u APP_DATA_ROOT XDG_DATA_HOME="$fixture"

expect_root "home root" "$fixture/.local/share/inbe" \
    -u APP_DATA_ROOT -u XDG_DATA_HOME HOME="$fixture"

# An older directory is moved into place, contents and all.
base=$fixture/legacy-home
mkdir -p "$base/.local/share/breathing"
echo data > "$base/.local/share/breathing/sentinel.txt"
expect_root "old directory is selected as current" "$base/.local/share/inbe" \
    -u APP_DATA_ROOT -u XDG_DATA_HOME HOME="$base"
[ -f "$base/.local/share/inbe/sentinel.txt" ] || { echo "FAIL old content moved" >&2; failures=$((failures + 1)); }
[ ! -e "$base/.local/share/breathing" ] || { echo "FAIL old directory moved away" >&2; failures=$((failures + 1)); }

# A conflicting current directory is archived before the older one moves in.
base=$fixture/conflict-home
mkdir -p "$base/.local/share/breathing" "$base/.local/share/inbe"
echo legacy > "$base/.local/share/breathing/legacy.txt"
echo current > "$base/.local/share/inbe/current.txt"
expect_root "conflicting directory resolves to current" "$base/.local/share/inbe" \
    -u APP_DATA_ROOT -u XDG_DATA_HOME HOME="$base"
[ -f "$base/.local/share/inbe/legacy.txt" ] || { echo "FAIL old data moved into the current root" >&2; failures=$((failures + 1)); }
[ -f "$base/.local/share/inbe.before-breathing-migration-1/current.txt" ] || { echo "FAIL prior current data archived" >&2; failures=$((failures + 1)); }
[ ! -e "$base/.local/share/breathing" ] || { echo "FAIL old directory moved away (conflict)" >&2; failures=$((failures + 1)); }

if [ "$failures" -ne 0 ]; then
    echo "$failures storage path check(s) failed" >&2
    exit 1
fi
echo "storage path scenarios passed"
