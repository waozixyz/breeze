#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/device-policy-test
source=$root/tests/device_policy_behavior.zi

mkdir -p "$work/ir" "$work/c"
"$bin/zi2zir" --root "$root/tests" --module-path "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/ir" "$source"

"$bin/zi2zib" bundle --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" \
    --entry device_policy_behavior:Answer \
    -o "$work/source.zib" "$source"
"$bin/zi2zib" bundle --root "$work/ir" --module-path "$work/ir" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" \
    --entry device_policy_behavior:Answer \
    -o "$work/saved.zib" "$work/ir/device_policy_behavior.zir"
[ "$(env -u DISPLAY -u WAYLAND_DISPLAY "$bin/zi2zib" run "$work/source.zib")" = 42 ]
[ "$(env -u DISPLAY -u WAYLAND_DISPLAY "$bin/zi2zib" run "$work/saved.zib")" = 42 ]
cmp "$work/source.zib" "$work/saved.zib"

"$bin/zi2c" --no-main --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" \
    -o "$work/c" "$source"
cat > "$work/c/main.c" <<'C'
#include "device_policy_behavior.h"
/* Device policy reaches text measurement; fixed-width glyphs suffice. */
int32_t MeasureGlyphWidth(String value, int32_t font, String typeface)
{
    (void)typeface;
    return (int32_t)(value.length * (size_t)font / 2);
}
int32_t MeasureGlyphLineHeight(int32_t font, String typeface)
{
    (void)typeface;
    return font;
}
int main(void) { return Answer() == 42 ? 0 : 1; }
C
"${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK \
    -I"$root/build/packages/ziran/include" -I"$work/c" \
    "$work/c"/*.c -o "$work/c/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/c/test"
echo "device policy Ziran tests passed"
