#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
mkdir -p "$root/build"
work=$(mktemp -d "$root/build/settings-ui-zi-test.XXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
mkdir -p "$work/c"
cd "$root"
"$bin/ziran" build --project --offline ${PACKAGE_FLAGS:-} --target=c --no-main \
    --root "$root/src" -o "$work/c" "$root/src/screens/settings/settings_ui.zi"
for header in "$work/c"/p*_tree.h "$work/c"/p*_tree_input.h "$work/c"/p*_paint_queue.h; do
    test -f "$header"
    printf '#include "%s"\n' "${header##*/}"
done > "$work/c/settings_test_backend.h"
"${CC:-cc}" -std=c11 -ffunction-sections -fdata-sections \
    -Wl,--gc-sections -I"$root/build/packages/ziran/include" -I"$work/c" \
    "$root/tests/settings_ui_link_test.c" "$work/c"/*.c -lm -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
for widget in device breaks notifications; do
    generated="$work/$widget"
    mkdir -p "$generated"
    "$bin/ziran" build --project --offline ${PACKAGE_FLAGS:-} --target=c --no-main \
        --root "$root/src" -o "$generated" "$root/src/screens/settings/settings_$widget.zi"
    "${CC:-cc}" -std=c11 -Wno-unused-function -Wno-unused-variable \
        -I"$root/build/packages/ziran/include" -I"$generated" \
        -c "$generated/settings_$widget.c" -o "$generated/settings_$widget.o"
done
echo "Inbe settings UI interaction, device, break, and notifications module compilation passed"
