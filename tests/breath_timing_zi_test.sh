#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=${BREATH_TIMING_TEST_BUILD_DIR:-"$root/build/breath-timing-zi-test"}
source=$root/tests/breath_timing_behavior.zi
include=${ZIRAN_INCLUDE:-"$root/build/packages/ziran/include"}

mkdir -p "$work/ir"
"$bin/zi2zir" --root "$root/tests" --module-path "$root/src" --module-path "$root/apps/practice" \
    -o "$work/ir" "$source"

for input in source saved; do
    if [ "$input" = source ]; then
        file=$source
        module_root=$root/tests
        library_path=$root/src
        practice_path=$root/apps/practice
    else
        file=$work/ir/breath_timing_behavior.zir
        module_root=$work/ir
        library_path=$work/ir
        practice_path=$work/ir
    fi
    output=$work/$input
    rm -rf "$output/c" "$output/go"
    mkdir -p "$output/c" "$output/go"
    "$bin/zi2zx" bundle --root "$module_root" \
        --module-path "$library_path" --module-path "$practice_path" \
        --entry breath_timing_behavior:Answer \
        -o "$output/breath.zx" "$file"
    [ "$("$bin/zi2zx" run "$output/breath.zx")" = 42 ]

    "$bin/zi2c" --no-main --root "$module_root" \
        --module-path "$library_path" --module-path "$practice_path" -o "$output/c" "$file"
    cat > "$output/c/main.c" <<'C'
#include "breath_timing_behavior.h"
int main(void) { return Answer() == 42 ? 0 : 1; }
C
    "${CC:-cc}" -std=c11 -I"$include" -I"$output/c" \
        "$output/c"/*.c -o "$output/c/test"
    env -u DISPLAY -u WAYLAND_DISPLAY "$output/c/test"

    "$bin/zi2go" --no-main --root "$module_root" \
        --module-path "$library_path" --module-path "$practice_path" -o "$output/go" "$file"
    cat > "$output/go/breath_timing_behavior_test.go" <<'GO'
package ziran
import "testing"
func TestBreathTiming(t *testing.T) {
    if got := BreathTimingBehavior_Answer(); got != 42 {
        t.Fatalf("breath timing: got %d, want 42", got)
    }
}
GO
    GO111MODULE=off go test "$output/go"/*.go
done

cmp "$work/source/breath.zx" "$work/saved/breath.zx"
echo "breath timing Ziran test passed"
