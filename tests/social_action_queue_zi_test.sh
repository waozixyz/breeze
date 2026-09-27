#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
include=${ZIRAN_INCLUDE:-"$root/vendor/ziran/include"}
work=$root/build/social-action-queue-test
source=$root/tests/social_action_queue_behavior.zi

mkdir -p "$work/ir"
"$bin/zi2zir" --root "$root/tests" --module-path "$root/src" \
    -o "$work/ir" "$source"

for input in source saved; do
    if [ "$input" = source ]; then
        file=$source
        module_root=$root/tests
        app_path=$root/src
    else
        file=$work/ir/social_action_queue_behavior.zir
        module_root=$work/ir
        app_path=$work/ir
    fi
    output=$work/$input
    mkdir -p "$output/c" "$output/cpp" "$output/go"
    "$bin/zi2zib" bundle --root "$module_root" \
        --module-path "$app_path" \
        --entry social_action_queue_behavior:Answer \
        -o "$output/queue.zib" "$file"
    [ "$(env -u DISPLAY -u WAYLAND_DISPLAY "$bin/zi2zib" run "$output/queue.zib")" = 42 ]

    "$bin/zi2c" --no-main --root "$module_root" \
        --module-path "$app_path" -o "$output/c" "$file"
    cat > "$output/c/main.c" <<'C'
#include "social_action_queue_behavior.h"
int main(void) { return Answer() == 42 ? 0 : 1; }
C
    "${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK \
        -I"$include" -I"$output/c" "$output/c"/*.c \
        -o "$output/c/test"
    env -u DISPLAY -u WAYLAND_DISPLAY "$output/c/test"

    "$bin/zi2cpp" --no-main --root "$module_root" \
        --module-path "$app_path" -o "$output/cpp" "$file"
    cat > "$output/cpp/main.cpp" <<'CPP'
#include "social_action_queue_behavior.hpp"
int main() { return Answer() == 42 ? 0 : 1; }
CPP
    "${CXX:-c++}" -std=c++17 -DZIRAN_BOUNDS_CHECK \
        -I"$include" -I"$output/cpp" "$output/cpp"/*.cpp \
        -o "$output/cpp/test"
    env -u DISPLAY -u WAYLAND_DISPLAY "$output/cpp/test"

    "$bin/zi2go" --no-main --root "$module_root" \
        --module-path "$app_path" -o "$output/go" "$file"
    cat > "$output/go/social_action_queue_behavior_test.go" <<'GO'
package ziran
import "testing"
func TestSocialActionQueue(t *testing.T) {
    if got := SocialActionQueueBehavior_Answer(); got != 42 {
        t.Fatalf("social action queue: got %d, want 42", got)
    }
}
GO
    GO111MODULE=off go test "$output/go"/*.go
done

cmp "$work/source/queue.zib" "$work/saved/queue.zib"
