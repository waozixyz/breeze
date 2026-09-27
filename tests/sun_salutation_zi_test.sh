#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=${SUN_SALUTATION_TEST_BUILD_DIR:-"$root/build/sun-salutation-test"}
source=$root/tests/sun_salutation_behavior.zi
include=${ZIRAN_INCLUDE:-"$root/build/packages/ziran/include"}

mkdir -p "$work/ir"
"$bin/zi2zir" --root "$root/tests" --module-path "$root/src" \
    -o "$work/ir" "$source"

for input in source saved; do
    if [ "$input" = source ]; then
        file=$source
        module_root=$root/tests
        module_path=$root/src
    else
        file=$work/ir/sun_salutation_behavior.zir
        module_root=$work/ir
        module_path=$work/ir
    fi
    output=$work/$input
    rm -rf "$output/c" "$output/cpp" "$output/go"
    mkdir -p "$output/c" "$output/cpp" "$output/go"

    "$bin/zi2zib" bundle --root "$module_root" \
        --module-path "$module_path" \
        --entry sun_salutation_behavior:Answer \
        -o "$output/sun_salutation.zib" "$file"
    [ "$("$bin/zi2zib" run "$output/sun_salutation.zib")" = 42 ]

    "$bin/zi2c" --no-main --root "$module_root" \
        --module-path "$module_path" -o "$output/c" "$file"
    cat > "$output/c/main.c" <<'C'
#include "sun_salutation_behavior.h"
int main(void) { return Answer() == 42 ? 0 : 1; }
C
    "${CC:-cc}" -std=c11 -I"$include" -I"$output/c" \
        "$output/c/sun_salutation_rules.c" \
        "$output/c/sun_salutation_behavior.c" \
        "$output/c/main.c" -o "$output/c/test"
    env -u DISPLAY -u WAYLAND_DISPLAY "$output/c/test"

    "$bin/zi2cpp" --no-main --root "$module_root" \
        --module-path "$module_path" -o "$output/cpp" "$file"
    cat > "$output/cpp/main.cpp" <<'CPP'
#include "sun_salutation_behavior.hpp"
int main() { return Answer() == 42 ? 0 : 1; }
CPP
    "${CXX:-c++}" -std=c++17 -I"$include" -I"$output/cpp" \
        "$output/cpp/sun_salutation_rules.cpp" \
        "$output/cpp/sun_salutation_behavior.cpp" \
        "$output/cpp/main.cpp" -o "$output/cpp/test"
    env -u DISPLAY -u WAYLAND_DISPLAY "$output/cpp/test"

    "$bin/zi2go" --no-main --root "$module_root" \
        --module-path "$module_path" -o "$output/go" "$file"
    cat > "$output/go/sun_salutation_behavior_test.go" <<'GO'
package ziran
import "testing"
func TestSunSalutation(t *testing.T) {
    if got := SunSalutationBehavior_Answer(); got != 42 {
        t.Fatalf("sun salutation: got %d, want 42", got)
    }
}
GO
    GO111MODULE=off go test "$output/go"/*.go
done

cmp "$work/source/sun_salutation.zib" "$work/saved/sun_salutation.zib"
echo "sun salutation Ziran test passed"
