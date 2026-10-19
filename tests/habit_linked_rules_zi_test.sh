#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$(mktemp -d "$root/build/habit-linked-test.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
source=$root/tests/habit_linked_rules_behavior.zi

sh "$root/scripts/run-ziran.sh" "$bin/zi2zir" --check-only --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" --module-path "$root/build/packages/daochi-client" $(sh "$root/scripts/package-paths.sh" "$root/build/packages") --module-path "$root/build/packages/kryon/src/backend" "$source"
sh "$root/scripts/run-ziran.sh" "$bin/zi2c" --no-main --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/ziran/std" --module-path "$root/build/packages/daochi-client" $(sh "$root/scripts/package-paths.sh" "$root/build/packages") --module-path "$root/build/packages/kryon/src/backend" -o "$work/c" "$source"
"${CC:-cc}" -std=c11 -ffunction-sections -fdata-sections \
    -Wl,--gc-sections -I"$root/build/packages/ziran/include" \
    -I"$work/c" "$work/c"/*.c -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "Habit linked Ziran test passed"
