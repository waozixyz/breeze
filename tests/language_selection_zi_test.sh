#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work=$root/build/language-selection-zi-test
rm -rf "$work/c"
mkdir -p "$work/c"
cd "$root"

"$bin/ziran" build --project --offline ${PACKAGE_FLAGS:-} --target=c --no-main --root "$root/src" \
    -o "$work/c" "$root/src/app/language_selection.zi"
# The link test stands in for settings_store, so its header declares those
# procedures instead of defining inline copies.
"${CC:-cc}" -std=c11 -Wall -Wextra -Werror \
    -Wno-unused-function -Wno-unused-variable -DZIRAN_SETTINGS_STORE_H_SOURCE \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -I"$work/c" \
    "$root/tests/language_selection_link_test.c" \
    "$work/c/language_selection.c" "$work/c/view_settings.c" \
    "$work/c/std_c_string.c" \
    -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "Inbe language selection Ziran/native link test passed"
