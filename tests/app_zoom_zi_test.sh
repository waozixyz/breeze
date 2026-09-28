#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/app-zoom-test
source=$root/tests/app_zoom_behavior.zi
include=${ZIRAN_INCLUDE:-"$root/build/packages/ziran/include"}
kryon=$root/build/packages/kryon/src/ui
std=$root/build/packages/ziran/std

mkdir -p "$work/ir"
"$bin/zi2zir" --root "$root/tests" --module-path "$root/src" --module-path "$kryon" \
    --module-path "$std" \
    -o "$work/ir" "$source"

for input in source saved; do
    if [ "$input" = source ]; then
        file=$source
        module_root=$root/tests
        app_path=$root/src
    else
        file=$work/ir/app_zoom_behavior.zir
        module_root=$work/ir
        app_path=$work/ir
    fi
    output=$work/$input
    mkdir -p "$output/c" "$output/cpp" "$output/go"
    "$bin/zi2zib" bundle --root "$module_root" \
        --module-path "$app_path" --module-path "$kryon" \
        --module-path "$std" \
        --entry app_zoom_behavior:Answer \
        -o "$output/zoom.zib" "$file"
    [ "$(env -u DISPLAY -u WAYLAND_DISPLAY "$bin/zi2zib" run "$output/zoom.zib")" = 42 ]

    "$bin/zi2c" --no-main --root "$module_root" \
        --module-path "$app_path" --module-path "$kryon" \
        --module-path "$std" -o "$output/c" "$file"
    cat > "$output/c/main.c" <<'C'
#include "app_zoom_behavior.h"
int main(void) { return Answer() == 42 ? 0 : 1; }
C
    "${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK \
        -I"$include" -I"$output/c" "$output/c"/*.c -o "$output/c/test"
    env -u DISPLAY -u WAYLAND_DISPLAY "$output/c/test"

    "$bin/zi2cpp" --no-main --root "$module_root" \
        --module-path "$app_path" --module-path "$kryon" \
        --module-path "$std" -o "$output/cpp" "$file"
    cat > "$output/cpp/main.cpp" <<'CPP'
#include "app_zoom_behavior.hpp"
int main() { return Answer() == 42 ? 0 : 1; }
CPP
    "${CXX:-c++}" -std=c++17 -DZIRAN_BOUNDS_CHECK \
        -I"$include" -I"$output/cpp" "$output/cpp"/*.cpp \
        -o "$output/cpp/test"
    env -u DISPLAY -u WAYLAND_DISPLAY "$output/cpp/test"

    "$bin/zi2go" --no-main --root "$module_root" \
        --module-path "$app_path" --module-path "$kryon" \
        --module-path "$std" -o "$output/go" "$file"
    cat > "$output/go/app_zoom_behavior_test.go" <<'GO'
package ziran
import "testing"
func TestAppZoom(t *testing.T) {
    if got := AppZoomBehavior_Answer(); got != 42 {
        t.Fatalf("app zoom: got %d, want 42", got)
    }
}
GO
    GO111MODULE=off go test "$output/go"/*.go
done

cmp "$work/source/zoom.zib" "$work/saved/zoom.zib"
