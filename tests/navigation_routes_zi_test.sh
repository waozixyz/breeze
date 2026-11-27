#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work=${NAVIGATION_ROUTES_TEST_BUILD_DIR:-"$root/build/navigation-routes-test"}
source=$root/tests/navigation_routes_behavior.zi
include=${ZIRAN_INCLUDE:-"$root/build/packages/ziran/include"}

mkdir -p "$work/ir"
"$bin/ziran" ir --project --offline ${PACKAGE_FLAGS:-} --root "$root/tests"  \
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
    rm -rf "$output/c" "$output/go"
    mkdir -p "$output/c" "$output/go"
    "$bin/ziran" bundle --project --offline ${PACKAGE_FLAGS:-} --root "$module_root" \
        --entry navigation_routes_behavior:Answer \
        -o "$output/navigation_routes.zx" "$file"
    [ "$("$bin/zi2zx" run "$output/navigation_routes.zx")" = 42 ]

    "$bin/ziran" build --target=c --project --offline ${PACKAGE_FLAGS:-} --no-main --root "$module_root" \
        -o "$output/c" "$file"
    cat > "$output/c/main.c" <<'C'
#include "navigation_routes_behavior.h"
int main(void) { return Answer() == 42 ? 0 : 1; }
C
    "${CC:-cc}" -std=c11 -I"$include" -I"$output/c" \
        "$output/c/"*.c -o "$output/c/test"
    env -u DISPLAY -u WAYLAND_DISPLAY "$output/c/test"

    "$bin/ziran" build --target=go --project --offline ${PACKAGE_FLAGS:-} --no-main --root "$module_root" \
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

cmp "$work/source/navigation_routes.zx" "$work/saved/navigation_routes.zx"
echo "navigation routes Ziran test passed"
