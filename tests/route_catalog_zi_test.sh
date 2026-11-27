#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work=${ROUTE_CATALOG_TEST_BUILD_DIR:-"$root/build/route-catalog-test"}
source=$root/tests/route_catalog_behavior.zi
include=${ZIRAN_INCLUDE:-"$root/build/packages/ziran/include"}
ui=${KRYON_UI_DIR:-$root/build/packages/kryon/src/ui}

mkdir -p "$work/ir"
"$bin/ziran" ir --project --offline ${PACKAGE_FLAGS:-} --root "$root/tests"  \
        -o "$work/ir" "$source"

for input in source saved; do
    if [ "$input" = source ]; then
        file=$source
        module_root=$root/tests
        app_path=$root/src
        ui_path=$ui
        std_path=$root/build/packages/ziran/std
    else
        file=$work/ir/route_catalog_behavior.zir
        module_root=$work/ir
        app_path=$work/ir
        ui_path=$work/ir
        std_path=$work/ir
    fi
    output=$work/$input
    rm -rf "$output/c" "$output/go"
    mkdir -p "$output/c" "$output/go"
    "$bin/ziran" bundle --project --offline ${PACKAGE_FLAGS:-} --root "$module_root" \
        --entry route_catalog_behavior:Answer \
        -o "$output/routes.zx" "$file"
    [ "$("$bin/zi2zx" run "$output/routes.zx")" = 42 ]

    "$bin/ziran" build --target=c --project --offline ${PACKAGE_FLAGS:-} --no-main --root "$module_root" \
        -o "$output/c" "$file"
    cat > "$output/c/main.c" <<'C'
#include "route_catalog_behavior.h"
int main(void) { return Answer() == 42 ? 0 : 1; }
C
    "${CC:-cc}" -std=c11 -ffunction-sections -fdata-sections \
        -Wl,--gc-sections -I"$include" -I"$output/c" \
        "$output/c"/*.c -o "$output/c/test"
    env -u DISPLAY -u WAYLAND_DISPLAY "$output/c/test"

    "$bin/ziran" build --target=go --project --offline ${PACKAGE_FLAGS:-} --no-main --root "$module_root" \
        -o "$output/go" "$file"
    cat > "$output/go/route_catalog_behavior_test.go" <<'GO'
package ziran
import "testing"
func TestRouteCatalog(t *testing.T) {
    if got := RouteCatalogBehavior_Answer(); got != 42 {
        t.Fatalf("route catalog: got %d, want 42", got)
    }
}
GO
    GO111MODULE=off go test "$output/go"/*.go
done

cmp "$work/source/routes.zx" "$work/saved/routes.zx"
echo "route catalog Ziran test passed"
