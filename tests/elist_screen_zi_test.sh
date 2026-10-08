#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/elist-screen-zi-test
mkdir -p "$work/c"

"$bin/zi2zir" --check-only --root "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kss/src" --module-path "oqs=$root/build/packages/oqs/src" --module-path "kryon=$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" \
    "$root/src/screens/elist_screen.zi"
"$bin/zi2c" --no-main --root "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kss/src" --module-path "oqs=$root/build/packages/oqs/src" --module-path "kryon=$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" \
    -o "$work/c" "$root/src/screens/elist_screen.zi"

"${CC:-cc}" -std=c11 -Wall -Wextra -Werror \
    -Wno-unused-function -Wno-unused-variable \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -I"$work/c" \
    -I"$work/c/ui" -I"$work/c/app" -I"$work/c/platform" \
    -I"$work/c/storage" -I"$work/c/screens" -I"$work/c/kss" \
    -I"$work/c/daochi-client" \
    "$root/tests/elist_screen_link_test.c" \
    "$work/c/screens/elist_screen.c" "$work/c/text_buffers.c" \
    "$work/c/byte_text_linux.c" \
    "$work/c/module_host.c" "$work/c/value_codec.c" \
    "$work/c/package_files.c" "$work/c/format.c" \
    "$work/c/asset_paths.c" "$work/c/assets.c" \
    "$work/c/sun_salutation_inventory.c" \
    "$work/c/lists_visibility.c" "$work/c/bundle_host.c" \
    "$root/build/ziran-toolchain/libziran.a" -lm \
    -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test" "$root/build/inbe.zib"
echo "Inbe elist screen Ziran/native test passed"
