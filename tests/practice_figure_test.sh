#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
source=${2:?practice behavior source required}
name=$(basename "$source" .zi)
case "$name" in
    ''|*[!a-zA-Z0-9_]*) echo 'Invalid practice test name' >&2; exit 2 ;;
esac
source="$root/tests/$name.zi"
test -f "$source"
work="$root/build/$name-test"
rm -rf "$work"
mkdir -p "$work/c"
"$bin/zi2zir" --check-only --root "$root/tests" --module-path "$root/src" \
    --module-path "$root/build/packages/ziran/std" "$source"
"$bin/zi2c" --no-main --root "$root/tests" --module-path "$root/src" \
    --module-path "$root/build/packages/ziran/std" -o "$work/c" \
    "$source"
cat > "$work/c/main.c" <<C
#include "$name.h"
#include <stdio.h>
int main(void) {
    int result = Answer();
    if (result != 42) fprintf(stderr, "$name check failed: %d\n", result);
    return result == 42 ? 0 : 1;
}
C
"${CC:-cc}" -std=c11 -I"$root/build/packages/ziran/include" -I"$work/c" \
    "$work/c"/*.c "$root/build/ziran-toolchain/libziran.a" -lm -lz -o "$work/test"
(cd "$root/tests" && env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS "$work/test")
echo "$name: practice behavior and figure passed"
