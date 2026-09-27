#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=${ROUTE_CATALOG_TEST_BUILD_DIR:-"$root/build/route-catalog-test"}
source=$root/tests/route_catalog_behavior.zi
include=${ZIRAN_INCLUDE:-"$root/build/packages/ziran/include"}
ui=${KRYON_UI_DIR:-$root/build/packages/kryon/src/ui}

mkdir -p "$work/ir"
"$bin/zi2zir" --root "$root/tests" --module-path "$root/src" \
    --module-path "$ui" -o "$work/ir" "$source"

for input in source saved; do
    if [ "$input" = source ]; then
        file=$source
        module_root=$root/tests
        app_path=$root/src
        ui_path=$ui
    else
        file=$work/ir/route_catalog_behavior.zir
        module_root=$work/ir
        app_path=$work/ir
        ui_path=$work/ir
    fi
    output=$work/$input
    rm -rf "$output/c" "$output/cpp" "$output/go"
    mkdir -p "$output/c" "$output/cpp" "$output/go"
    "$bin/zi2zib" bundle --root "$module_root" \
        --module-path "$app_path" --module-path "$ui_path" \
        --entry route_catalog_behavior:Answer \
        -o "$output/routes.zib" "$file"
    [ "$("$bin/zi2zib" run "$output/routes.zib")" = 42 ]

    "$bin/zi2c" --no-main --root "$module_root" \
        --module-path "$app_path" --module-path "$ui_path" \
        -o "$output/c" "$file"
    cat > "$output/c/main.c" <<'C'
#include "route_catalog_behavior.h"
int main(void) { return Answer() == 42 ? 0 : 1; }
C
    "${CC:-cc}" -std=c11 -ffunction-sections -fdata-sections \
        -Wl,--gc-sections -I"$include" -I"$output/c" \
        "$output/c"/*.c -o "$output/c/test"
    env -u DISPLAY -u WAYLAND_DISPLAY "$output/c/test"

    "$bin/zi2cpp" --no-main --root "$module_root" \
        --module-path "$app_path" --module-path "$ui_path" \
        -o "$output/cpp" "$file"
    cat > "$output/cpp/main.cpp" <<'CPP'
#include "route_catalog_behavior.hpp"
int main() { return Answer() == 42 ? 0 : 1; }
CPP
    "${CXX:-c++}" -std=c++17 -ffunction-sections -fdata-sections \
        -Wl,--gc-sections -I"$include" -I"$output/cpp" \
        "$output/cpp"/*.cpp -o "$output/cpp/test"
    env -u DISPLAY -u WAYLAND_DISPLAY "$output/cpp/test"

    "$bin/zi2go" --no-main --root "$module_root" \
        --module-path "$app_path" --module-path "$ui_path" \
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

cmp "$work/source/routes.zib" "$work/saved/routes.zib"
echo "route catalog Ziran test passed"
