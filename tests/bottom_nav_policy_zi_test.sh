#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/bottom-nav-policy-test
source=$root/tests/bottom_nav_policy_behavior.zi
include=${ZIRAN_INCLUDE:-"$root/vendor/ziran/include"}

mkdir -p "$work/ir"
"$bin/zi2zir" --root "$root/tests" --module-path "$root/src" \
    -o "$work/ir" "$source"

for input in source saved; do
    if [ "$input" = source ]; then
        file=$source
        module_root=$root/tests
        app_path=$root/src
    else
        file=$work/ir/bottom_nav_policy_behavior.zir
        module_root=$work/ir
        app_path=$work/ir
    fi
    output=$work/$input
    mkdir -p "$output/c" "$output/cpp" "$output/go"
    "$bin/zi2zib" bundle --root "$module_root" \
        --module-path "$app_path" \
        --entry bottom_nav_policy_behavior:Answer \
        -o "$output/policy.zib" "$file"
    [ "$(env -u DISPLAY -u WAYLAND_DISPLAY "$bin/zi2zib" run "$output/policy.zib")" = 42 ]

    "$bin/zi2c" --no-main --root "$module_root" \
        --module-path "$app_path" -o "$output/c" "$file"
    cat > "$output/c/main.c" <<'C'
#include "bottom_nav_policy_behavior.h"
int main(void) { return Answer() == 42 ? 0 : 1; }
C
    "${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK \
        -I"$include" -I"$output/c" "$output/c"/*.c -o "$output/c/test"
    env -u DISPLAY -u WAYLAND_DISPLAY "$output/c/test"

    "$bin/zi2cpp" --no-main --root "$module_root" \
        --module-path "$app_path" -o "$output/cpp" "$file"
    cat > "$output/cpp/main.cpp" <<'CPP'
#include "bottom_nav_policy_behavior.hpp"
int main() { return Answer() == 42 ? 0 : 1; }
CPP
    "${CXX:-c++}" -std=c++17 -DZIRAN_BOUNDS_CHECK \
        -I"$include" -I"$output/cpp" "$output/cpp"/*.cpp \
        -o "$output/cpp/test"
    env -u DISPLAY -u WAYLAND_DISPLAY "$output/cpp/test"

    "$bin/zi2go" --no-main --root "$module_root" \
        --module-path "$app_path" -o "$output/go" "$file"
    cat > "$output/go/bottom_nav_policy_behavior_test.go" <<'GO'
package ziran
import "testing"
func TestBottomNavPolicy(t *testing.T) {
    if got := BottomNavPolicyBehavior_Answer(); got != 42 {
        t.Fatalf("bottom navigation policy: got %d, want 42", got)
    }
}
GO
    GO111MODULE=off go test "$output/go"/*.go
done

cmp "$work/source/policy.zib" "$work/saved/policy.zib"
