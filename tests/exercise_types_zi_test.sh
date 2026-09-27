#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=${EXERCISE_TYPES_TEST_BUILD_DIR:-"$root/build/exercise-types-test"}
source=$root/tests/exercise_types_behavior.zi
include=${ZIRAN_INCLUDE:-"$root/build/packages/ziran/include"}

mkdir -p "$work/ir"
"$bin/zi2zir" --root "$root/tests" --module-path "$root/src" \
    -o "$work/ir" "$source"

for input in source saved; do
    if [ "$input" = source ]; then
        file=$source
        module_root=$root/tests
        app_path=$root/src
    else
        file=$work/ir/exercise_types_behavior.zir
        module_root=$work/ir
        app_path=$work/ir
    fi
    output=$work/$input
    mkdir -p "$output/c" "$output/cpp" "$output/go"
    "$bin/zi2zib" bundle --root "$module_root" \
        --module-path "$app_path" \
        --entry exercise_types_behavior:Answer \
        -o "$output/exercises.zib" "$file"
    [ "$("$bin/zi2zib" run "$output/exercises.zib")" = 42 ]

    "$bin/zi2c" --no-main --root "$module_root" \
        --module-path "$app_path" -o "$output/c" "$file"
    cat > "$output/c/main.c" <<'C'
#include "exercise_types_behavior.h"
int main(void) { return Answer() == 42 ? 0 : 1; }
C
    "${CC:-cc}" -std=c11 -I"$include" -I"$output/c" \
        "$output/c"/*.c -o "$output/c/test"
    env -u DISPLAY -u WAYLAND_DISPLAY "$output/c/test"

    "$bin/zi2cpp" --no-main --root "$module_root" \
        --module-path "$app_path" -o "$output/cpp" "$file"
    cat > "$output/cpp/main.cpp" <<'CPP'
#include "exercise_types_behavior.hpp"
int main() { return Answer() == 42 ? 0 : 1; }
CPP
    "${CXX:-c++}" -std=c++17 -I"$include" -I"$output/cpp" \
        "$output/cpp"/*.cpp -o "$output/cpp/test"
    env -u DISPLAY -u WAYLAND_DISPLAY "$output/cpp/test"

    "$bin/zi2go" --no-main --root "$module_root" \
        --module-path "$app_path" -o "$output/go" "$file"
    cat > "$output/go/exercise_types_behavior_test.go" <<'GO'
package ziran
import "testing"
func TestExerciseTypes(t *testing.T) {
    if got := ExerciseTypesBehavior_Answer(); got != 42 {
        t.Fatalf("exercise types: got %d, want 42", got)
    }
}
GO
    GO111MODULE=off go test "$output/go"/*.go
done

cmp "$work/source/exercises.zib" "$work/saved/exercises.zib"
echo "exercise types Ziran test passed"
