#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$(mktemp -d "$root/build/settings-mutation-test.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
sh "$root/scripts/run-ziran.sh" "$bin/zi2c" --no-main --root "$root" \
    --module-path "$root/src" \
    --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" \
    -o "$work/c" "$root/tests/settings_mutation_behavior.zi"
find "$work/c" -name '*.c' -type f -exec \
    "${CC:-cc}" -std=c11 -ffunction-sections -fdata-sections \
    -Wl,--gc-sections -Wl,--wrap=save_settings -Wl,--wrap=LocaleText \
    -I"$root/build/packages/ziran/include" -I"$work/c" -I"$work/c/tests" \
    -o "$work/test" {} +
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY "$work/test"
echo "Settings reminder edits/addition and break timer mutations passed"
