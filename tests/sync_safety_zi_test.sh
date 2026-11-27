#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
include=${ZIRAN_INCLUDE:-"$root/build/packages/ziran/include"}
work=$root/build/sync-safety-test
source=$root/tests/sync_safety_behavior.zi

mkdir -p "$work/ir"
"$bin/ziran" ir --project --offline ${PACKAGE_FLAGS:-} --root "$root/tests"  \
    -o "$work/ir" "$source"

for input in source saved; do
    if [ "$input" = source ]; then
        file=$source
        module_root=$root/tests
        app_path=$root/src
    else
        file=$work/ir/sync_safety_behavior.zir
        module_root=$work/ir
        app_path=$work/ir
    fi
    output=$work/$input
    mkdir -p "$output/c" "$output/go"
    "$bin/ziran" bundle --project --offline ${PACKAGE_FLAGS:-} --root "$module_root" \
        --entry sync_safety_behavior:Answer \
        -o "$output/safety.zx" "$file"
    [ "$(env -u DISPLAY -u WAYLAND_DISPLAY "$bin/zi2zx" run "$output/safety.zx")" = 42 ]

    "$bin/ziran" build --target=c --project --offline ${PACKAGE_FLAGS:-} --no-main --root "$module_root" \
        -o "$output/c" "$file"
    cat > "$output/c/main.c" <<'C'
#include "sync_safety_behavior.h"
int main(void) { return Answer() == 42 ? 0 : 1; }
C
    "${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK \
        -I"$include" -I"$output/c" "$output/c"/*.c \
        -o "$output/c/test"
    env -u DISPLAY -u WAYLAND_DISPLAY "$output/c/test"

    "$bin/ziran" build --target=go --project --offline ${PACKAGE_FLAGS:-} --no-main --root "$module_root" \
        -o "$output/go" "$file"
    cat > "$output/go/sync_safety_behavior_test.go" <<'GO'
package ziran
import "testing"
func TestSyncSafety(t *testing.T) {
    if got := SyncSafetyBehavior_Answer(); got != 42 {
        t.Fatalf("sync safety: got %d, want 42", got)
    }
}
GO
    GO111MODULE=off go test "$output/go"/*.go
done

cmp "$work/source/safety.zx" "$work/saved/safety.zx"

"$bin/ziran" build --target=c --project --offline ${PACKAGE_FLAGS:-} --no-main --root "$root/src" \
    -o "$work/native" "$root/src/app/sync_safety.zi"
"${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$include" -I"$work/native" \
    "$root/tests/sync_safety_link_test.c" \
    "$work/native/sync_safety.c" \
    "$work/native/sync_safety_policy.c" \
    "$work/native/session_screen.c" \
    -o "$work/native/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/native/test"
