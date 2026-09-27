#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
include=${ZIRAN_INCLUDE:-"$root/build/packages/ziran/include"}
work=$root/build/sync-safety-test
source=$root/tests/sync_safety_behavior.zi

mkdir -p "$work/ir"
"$bin/zi2zir" --root "$root/tests" --module-path "$root/src" \
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
    mkdir -p "$output/c" "$output/cpp" "$output/go"
    "$bin/zi2zib" bundle --root "$module_root" \
        --module-path "$app_path" --entry sync_safety_behavior:Answer \
        -o "$output/safety.zib" "$file"
    [ "$(env -u DISPLAY -u WAYLAND_DISPLAY "$bin/zi2zib" run "$output/safety.zib")" = 42 ]

    "$bin/zi2c" --no-main --root "$module_root" \
        --module-path "$app_path" -o "$output/c" "$file"
    cat > "$output/c/main.c" <<'C'
#include "sync_safety_behavior.h"
int main(void) { return Answer() == 42 ? 0 : 1; }
C
    "${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK \
        -I"$include" -I"$output/c" "$output/c"/*.c \
        -o "$output/c/test"
    env -u DISPLAY -u WAYLAND_DISPLAY "$output/c/test"

    "$bin/zi2cpp" --no-main --root "$module_root" \
        --module-path "$app_path" -o "$output/cpp" "$file"
    cat > "$output/cpp/main.cpp" <<'CPP'
#include "sync_safety_behavior.hpp"
int main() { return Answer() == 42 ? 0 : 1; }
CPP
    "${CXX:-c++}" -std=c++17 -DZIRAN_BOUNDS_CHECK \
        -I"$include" -I"$output/cpp" "$output/cpp"/*.cpp \
        -o "$output/cpp/test"
    env -u DISPLAY -u WAYLAND_DISPLAY "$output/cpp/test"

    "$bin/zi2go" --no-main --root "$module_root" \
        --module-path "$app_path" -o "$output/go" "$file"
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

cmp "$work/source/safety.zib" "$work/saved/safety.zib"

"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    -o "$work/native" "$root/src/app/sync_safety.zi"
"${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$include" -I"$work/native" \
    "$root/tests/sync_safety_link_test.c" \
    "$work/native/app/sync_safety.c" \
    "$work/native/sync_safety_policy.c" \
    -o "$work/native/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/native/test"
