#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work=$(mktemp -d "$root/build/habit-linked-test.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
source=$root/tests/habit_linked_rules_behavior.zi

sh "$root/scripts/run-ziran.sh" "$bin/ziran" check --project --offline ${PACKAGE_FLAGS:-} --root "$root/tests" \
       "$source"
sh "$root/scripts/run-ziran.sh" "$bin/ziran" build --target=c --project --offline ${PACKAGE_FLAGS:-} --no-main --root "$root/tests" \
       -o "$work/c" "$source"
"${CC:-cc}" -std=c11 -ffunction-sections -fdata-sections \
    -Wl,--gc-sections -I"$root/build/packages/ziran/include" \
    -I"$work/c" "$work/c"/*.c -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "Habit linked Ziran test passed"
