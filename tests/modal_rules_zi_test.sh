#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=${MODAL_RULES_TEST_BUILD_DIR:-"$root/build/modal-rules-test"}
source=$root/tests/modal_rules_behavior.zi
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
        file=$work/ir/modal_rules_behavior.zir
        module_root=$work/ir
        module_path=$work/ir
    fi
    output=$work/$input
    rm -rf "$output/c" "$output/cpp" "$output/go"
    mkdir -p "$output/c" "$output/cpp" "$output/go"
    "$bin/zi2zib" bundle --root "$module_root" \
        --module-path "$module_path" \
        --entry modal_rules_behavior:Answer \
        -o "$output/modal_rules.zib" "$file"
    [ "$("$bin/zi2zib" run "$output/modal_rules.zib")" = 42 ]

    "$bin/zi2c" --no-main --root "$module_root" \
        --module-path "$module_path" -o "$output/c" "$file"
    cat > "$output/c/main.c" <<'C'
#include "modal_rules_behavior.h"
int main(void) { return Answer() == 42 ? 0 : 1; }
C
    "${CC:-cc}" -std=c11 -I"$include" -I"$output/c" \
        "$output/c/modal_rules.c" "$output/c/types.c" \
        "$output/c/modal_rules_behavior.c" "$output/c/main.c" \
        -o "$output/c/test"
    env -u DISPLAY -u WAYLAND_DISPLAY "$output/c/test"

    "$bin/zi2cpp" --no-main --root "$module_root" \
        --module-path "$module_path" -o "$output/cpp" "$file"
    cat > "$output/cpp/main.cpp" <<'CPP'
#include "modal_rules_behavior.hpp"
int main() { return Answer() == 42 ? 0 : 1; }
CPP
    "${CXX:-c++}" -std=c++17 -I"$include" -I"$output/cpp" \
        "$output/cpp/modal_rules.cpp" "$output/cpp/types.cpp" \
        "$output/cpp/modal_rules_behavior.cpp" "$output/cpp/main.cpp" \
        -o "$output/cpp/test"
    env -u DISPLAY -u WAYLAND_DISPLAY "$output/cpp/test"

    "$bin/zi2go" --no-main --root "$module_root" \
        --module-path "$module_path" -o "$output/go" "$file"
    cat > "$output/go/modal_rules_behavior_test.go" <<'GO'
package ziran
import "testing"
func TestModalRules(t *testing.T) {
    if got := ModalRulesBehavior_Answer(); got != 42 {
        t.Fatalf("modal rules: got %d, want 42", got)
    }
}
GO
    GO111MODULE=off go test "$output/go"/*.go
done

cmp "$work/source/modal_rules.zib" "$work/saved/modal_rules.zib"
echo "modal rules Ziran test passed"
