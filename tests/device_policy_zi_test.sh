#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/device-policy-test
source=$root/tests/device_policy_behavior.zi

mkdir -p "$work/ir" "$work/c"
"$bin/zi2zir" --root "$root/tests" --module-path "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" --module-path "$root/build/packages/daochi-client" $(sh "$root/scripts/package-paths.sh" "$root/build/packages") --module-path "$root/build/packages/kryon/src/backend" \
    -o "$work/ir" "$source"

"$bin/zi2zx" bundle --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" --module-path "$root/build/packages/daochi-client" $(sh "$root/scripts/package-paths.sh" "$root/build/packages") --module-path "$root/build/packages/kryon/src/backend" \
    --entry device_policy_behavior:Answer \
    -o "$work/source.zx" "$source"
"$bin/zi2zx" bundle --root "$work/ir" --module-path "$work/ir" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" --module-path "$root/build/packages/daochi-client" $(sh "$root/scripts/package-paths.sh" "$root/build/packages") --module-path "$root/build/packages/kryon/src/backend" \
    --entry device_policy_behavior:Answer \
    -o "$work/saved.zx" "$work/ir/device_policy_behavior.zir"
[ "$(env -u DISPLAY -u WAYLAND_DISPLAY "$bin/zi2zx" run "$work/source.zx")" = 42 ]
[ "$(env -u DISPLAY -u WAYLAND_DISPLAY "$bin/zi2zx" run "$work/saved.zx")" = 42 ]
cmp "$work/source.zx" "$work/saved.zx"

"$bin/zi2c" --no-main --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" --module-path "$root/build/packages/daochi-client" $(sh "$root/scripts/package-paths.sh" "$root/build/packages") --module-path "$root/build/packages/kryon/src/backend" \
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
"${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -I"$work/c" \
    "$work/c"/*.c -o "$work/c/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/c/test"
echo "device policy Ziran tests passed"
