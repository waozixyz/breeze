#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=${NAVIGATION_ROUTES_TEST_BUILD_DIR:-"$root/build/navigation-routes-test"}
source=$root/tests/navigation_routes_behavior.zi
include=${ZIRAN_INCLUDE:-"$root/build/packages/ziran/include"}

mkdir -p "$work/ir"
"$bin/zi2zir" --root "$root/tests" --module-path "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    -o "$work/ir" "$source"

for input in source saved; do
    if [ "$input" = source ]; then
        file=$source
        module_root=$root/tests
        module_path=$root/src
    else
        file=$work/ir/navigation_routes_behavior.zir
        module_root=$work/ir
        module_path=$work/ir
    fi
    output=$work/$input
    rm -rf "$output/c" "$output/cpp" "$output/go"
    mkdir -p "$output/c" "$output/cpp" "$output/go"
    "$bin/zi2zib" bundle --root "$module_root" \
        --module-path "$module_path" \
        --module-path "$root/build/packages/kryon/src/ui" \
        --entry navigation_routes_behavior:Answer \
        -o "$output/navigation_routes.zib" "$file"
    [ "$("$bin/zi2zib" run "$output/navigation_routes.zib")" = 42 ]

    "$bin/zi2c" --no-main --root "$module_root" \
        --module-path "$module_path" \
        --module-path "$root/build/packages/kryon/src/ui" \
        -o "$output/c" "$file"
    cat > "$output/c/main.c" <<'C'
#include "navigation_routes_behavior.h"
int main(void) { return Answer() == 42 ? 0 : 1; }
C
    "${CC:-cc}" -std=c11 -I"$include" -I"$output/c" \
        "$output/c/route_types.c" \
        "$output/c/navigation_routes.c" \
        "$output/c/types.c" \
        "$output/c/navigation_routes_behavior.c" \
        "$output/c/main.c" -o "$output/c/test"
    env -u DISPLAY -u WAYLAND_DISPLAY "$output/c/test"

    "$bin/zi2cpp" --no-main --root "$module_root" \
        --module-path "$module_path" \
        --module-path "$root/build/packages/kryon/src/ui" \
        -o "$output/cpp" "$file"
    cat > "$output/cpp/main.cpp" <<'CPP'
#include "navigation_routes_behavior.hpp"
int main() { return Answer() == 42 ? 0 : 1; }
CPP
    "${CXX:-c++}" -std=c++17 -I"$include" -I"$output/cpp" \
        "$output/cpp/route_types.cpp" \
        "$output/cpp/navigation_routes.cpp" \
        "$output/cpp/types.cpp" \
        "$output/cpp/navigation_routes_behavior.cpp" \
        "$output/cpp/main.cpp" -o "$output/cpp/test"
    env -u DISPLAY -u WAYLAND_DISPLAY "$output/cpp/test"

    "$bin/zi2go" --no-main --root "$module_root" \
        --module-path "$module_path" \
        --module-path "$root/build/packages/kryon/src/ui" \
        -o "$output/go" "$file"
    cat > "$output/go/navigation_routes_behavior_test.go" <<'GO'
package ziran
import "testing"
func TestNavigationRoutes(t *testing.T) {
    if got := NavigationRoutesBehavior_Answer(); got != 42 {
        t.Fatalf("navigation routes: got %d, want 42", got)
    }
}
GO
    GO111MODULE=off go test "$output/go"/*.go
done

cmp "$work/source/navigation_routes.zib" "$work/saved/navigation_routes.zib"
echo "navigation routes Ziran test passed"
