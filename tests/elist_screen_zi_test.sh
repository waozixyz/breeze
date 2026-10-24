#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/elist-screen-zi-test
mkdir -p "$work/c"

# Serialize concurrent checks: the link below takes every generated file.
exec 9>"$work.lock"
flock 9

"$bin/zi2zir" --check-only --root "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" --module-path "$root/build/packages/kryon/src/backend" \
    --module-path "$root/build/packages/kss/src" $(sh "$root/scripts/package-paths.sh" "$root/build/packages") \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" \
    "$root/src/screens/elist_screen.zi"
"$bin/zi2c" --no-main --prune-stale --root "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" --module-path "$root/build/packages/kryon/src/backend" \
    --module-path "$root/build/packages/kss/src" $(sh "$root/scripts/package-paths.sh" "$root/build/packages") \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" \
    -o "$work/c" "$root/src/screens/elist_screen.zi"

includes="-I$root/build/packages/ziran/include -I$work/c -I$work/c/screens"

# The test host and the screen under test compile warning-free.
for source in "$root/tests/elist_screen_link_test.c" "$work/c/screens/elist_screen.c"; do
    "${CC:-cc}" -std=c11 -Wall -Wextra -Werror \
        -Wno-unused-function -Wno-unused-variable \
        -ffunction-sections -fdata-sections $includes \
        -c "$source" -o "$work/$(basename "$source" .c).o"
done

# Every other module the screen reaches links as generated, so a new import in
# the app or Kryon needs no change here; --gc-sections drops what the test never
# calls. The modules whose storage, sharing, Diary, node app, media library and
# scale functions the test host replaces stay out.
"${CC:-cc}" -std=c11 -w -ffunction-sections -fdata-sections -Wl,--gc-sections \
    $includes "$work/elist_screen_link_test.o" "$work/elist_screen.o" \
    $(find "$work/c" -name '*.c' | grep -v -e '/screens/elist_screen\.c$' \
        -e '/db\.c$' -e '/storage_elist\.c$' -e '/lists_network\.c$' \
        -e '/diary_store\.c$' -e '/node_apps\.c$' -e '/media_store\.c$' \
        -e '/metrics\.c$') \
    "$root/build/ziran-toolchain/libziran.a" -lm -lpthread \
    -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test" "$root/build/inbe.zx"
echo "Inbe elist screen Ziran/native test passed"
