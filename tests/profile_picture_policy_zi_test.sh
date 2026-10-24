#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/profile-picture-policy-test
source=$root/tests/profile_picture_policy_behavior.zi

mkdir -p "$work/ir" "$work/c"
"$bin/zi2zir" --root "$root/tests" --module-path "$root/src" \
    -o "$work/ir" "$source"
"$bin/zi2zx" bundle --root "$root/tests" --module-path "$root/src" \
    --entry profile_picture_policy_behavior:Answer \
    -o "$work/source.zx" "$source"
"$bin/zi2zx" bundle --root "$work/ir" --module-path "$work/ir" \
    --entry profile_picture_policy_behavior:Answer \
    -o "$work/saved.zx" "$work/ir/profile_picture_policy_behavior.zir"
[ "$(env -u DISPLAY -u WAYLAND_DISPLAY "$bin/zi2zx" run "$work/source.zx")" = 42 ]
[ "$(env -u DISPLAY -u WAYLAND_DISPLAY "$bin/zi2zx" run "$work/saved.zx")" = 42 ]
cmp "$work/source.zx" "$work/saved.zx"

"$bin/zi2c" --no-main --root "$root/tests" --module-path "$root/src" \
    -o "$work/c" "$source"
cat > "$work/c/main.c" <<'C'
#include "profile_picture_policy_behavior.h"
int main(void) { return Answer() == 42 ? 0 : 1; }
C
"${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK \
    -I"$root/build/packages/ziran/include" -I"$work/c" \
    "$work/c"/*.c -o "$work/c/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/c/test"
echo "profile picture policy Ziran tests passed"
