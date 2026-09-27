#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=${SETTINGS_CACHE_TEST_BUILD_DIR:-"$root/build/settings-cache-test"}
source=$root/tests/settings_cache_behavior.zi
include=${ZIRAN_INCLUDE:-"$root/build/packages/ziran/include"}

mkdir -p "$work/ir"
"$bin/zi2zir" --root "$root/tests" --module-path "$root/src" \
    --module-path "$root/build/packages/ziran/std" -o "$work/ir" "$source"

for input in source saved; do
    if [ "$input" = source ]; then
        file=$source
        module_root=$root/tests
        app_path=$root/src
    else
        file=$work/ir/settings_cache_behavior.zir
        module_root=$work/ir
        app_path=$work/ir
    fi
    output=$work/$input
    mkdir -p "$output/c" "$output/cpp" "$output/go"
    "$bin/zi2zib" bundle --root "$module_root" \
        --module-path "$app_path" \
        --module-path "$root/build/packages/ziran/std" \
        --entry settings_cache_behavior:Answer \
        -o "$output/settings.zib" "$file"
    [ "$(env -u DISPLAY -u WAYLAND_DISPLAY "$bin/zi2zib" run "$output/settings.zib")" = 42 ]

    "$bin/zi2c" --no-main --root "$module_root" \
        --module-path "$app_path" --module-path "$root/build/packages/ziran/std" \
        -o "$output/c" "$file"
    cat > "$output/c/main.c" <<'C'
#include "settings_cache_behavior.h"
int main(void) { return Answer() == 42 ? 0 : 1; }
C
    "${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK \
        -I"$include" -I"$output/c" "$output/c"/*.c -o "$output/c/test"
    env -u DISPLAY -u WAYLAND_DISPLAY "$output/c/test"

    "$bin/zi2cpp" --no-main --root "$module_root" \
        --module-path "$app_path" --module-path "$root/build/packages/ziran/std" \
        -o "$output/cpp" "$file"
    cat > "$output/cpp/main.cpp" <<'CPP'
#include "settings_cache_behavior.hpp"
int main() { return Answer() == 42 ? 0 : 1; }
CPP
    "${CXX:-c++}" -std=c++17 -DZIRAN_BOUNDS_CHECK \
        -I"$include" -I"$output/cpp" "$output/cpp"/*.cpp \
        -o "$output/cpp/test"
    env -u DISPLAY -u WAYLAND_DISPLAY "$output/cpp/test"

    "$bin/zi2go" --no-main --root "$module_root" \
        --module-path "$app_path" --module-path "$root/build/packages/ziran/std" \
        -o "$output/go" "$file"
    cat > "$output/go/settings_cache_behavior_test.go" <<'GO'
package ziran
import "testing"
func TestSettingsCache(t *testing.T) {
    if got := SettingsCacheBehavior_Answer(); got != 42 {
        t.Fatalf("settings cache: got %d, want 42", got)
    }
}
GO
    GO111MODULE=off go test "$output/go"/*.go
done

cmp "$work/source/settings.zib" "$work/saved/settings.zib"
mkdir -p "$work/source/c/app"
cp "$work/source/c/settings_cache.h" "$work/source/c/app/settings_cache.h"
cp "$work/source/c/settings_key.h" "$work/source/c/app/settings_key.h"
mkdir -p "$work/store/c"
"$bin/zi2c" --no-main --root "$root/tests" --module-path "$root/src" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/store/c" "$root/tests/settings_store_link_behavior.zi"
mkdir -p "$work/store/c/app"
cp "$work/store/c/settings_key.h" "$work/store/c/app/settings_key.h"
"${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$include" -I"$work/store/c" \
    "$root/tests/settings_cache_host_test.c" \
    "$work/store/c"/*.c -o "$work/host-test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/host-test"
"${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$include" -I"$work/store/c" \
    "$root/tests/settings_key_host_test.c" \
    "$work/store/c"/*.c -o "$work/key-host-test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/key-host-test"
"${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$include" -I"$work/store/c" -I"$root/src/app" \
    -I"$root/src/storage" \
    "$root/tests/settings_store_link_test.c" \
    "$work/store/c"/*.c -o "$work/store/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/store/test"
echo "settings cache and store Ziran tests passed"
