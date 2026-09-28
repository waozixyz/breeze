#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=${FONT_ASSETS_TEST_BUILD_DIR:-"$root/build/font-assets-test"}
source=$root/tests/font_assets_behavior.zi
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
        file=$work/ir/font_assets_behavior.zir
        module_root=$work/ir
        module_path=$work/ir
    fi
    output=$work/$input
    rm -rf "$output/c" "$output/cpp" "$output/go"
    mkdir -p "$output/c" "$output/cpp" "$output/go"
    "$bin/zi2zib" bundle --root "$module_root" \
        --module-path "$module_path" \
        --entry font_assets_behavior:Answer \
        -o "$output/font_assets.zib" "$file"
    [ "$("$bin/zi2zib" run "$output/font_assets.zib")" = 42 ]

    "$bin/zi2c" --no-main --root "$module_root" \
        --module-path "$module_path" -o "$output/c" "$file"
    cat > "$output/c/main.c" <<'C'
#include "font_assets_behavior.h"
int main(void) { return Answer() == 42 ? 0 : 1; }
C
    "${CC:-cc}" -std=c11 -I"$include" -I"$output/c" \
        "$output/c/font_assets.c" \
        "$output/c/font_assets_behavior.c" \
        "$output/c/main.c" -o "$output/c/test"
    env -u DISPLAY -u WAYLAND_DISPLAY "$output/c/test"

    "$bin/zi2cpp" --no-main --root "$module_root" \
        --module-path "$module_path" -o "$output/cpp" "$file"
    cat > "$output/cpp/main.cpp" <<'CPP'
#include "font_assets_behavior.hpp"
int main() { return Answer() == 42 ? 0 : 1; }
CPP
    "${CXX:-c++}" -std=c++17 -I"$include" -I"$output/cpp" \
        "$output/cpp/font_assets.cpp" \
        "$output/cpp/font_assets_behavior.cpp" \
        "$output/cpp/main.cpp" -o "$output/cpp/test"
    env -u DISPLAY -u WAYLAND_DISPLAY "$output/cpp/test"

    "$bin/zi2go" --no-main --root "$module_root" \
        --module-path "$module_path" -o "$output/go" "$file"
    cat > "$output/go/font_assets_behavior_test.go" <<'GO'
package ziran
import "testing"
func TestFontAssets(t *testing.T) {
    if got := FontAssetsBehavior_Answer(); got != 42 {
        t.Fatalf("font assets: got %d, want 42", got)
    }
}
GO
    GO111MODULE=off go test "$output/go"/*.go
done

cmp "$work/source/font_assets.zib" "$work/saved/font_assets.zib"
echo "font assets Ziran test passed"

# Every font the locale mapping can pick is in the repository.
for font in $(sed -n 's/^FONT_[A-Z]* :: "\(.*\)"$/\1/p' "$root/src/app/font_assets.zi"); do
    [ -f "$root/$font" ] || { echo "missing font file $font" >&2; exit 1; }
done
echo "font asset files present"
