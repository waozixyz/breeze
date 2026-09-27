#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
ui=${KRYON_UI:-"$root/build/packages/kryon/src/ui"}
work="$root/build/android-text-input-test"
source="$root/tests/android_text_input_behavior.zi"
mkdir -p "$work/c"

"$bin/zi2zir" --check-only --define ANDROID_BUILD --root "$root/tests" \
    --module-path "$root/src" --module-path "$ui" \
    --module-path "$root/build/packages/ziran/std" "$source"
"$bin/zi2c" --define ANDROID_BUILD --root "$root/tests" \
    --module-path "$root/src" --module-path "$ui" \
    --module-path "$root/build/packages/ziran/std" -o "$work/c" "$source"
"${CC:-cc}" -std=c11 -D_DEFAULT_SOURCE -O2 -pthread \
    -ffunction-sections -fdata-sections -I"$root/build/packages/ziran/include" \
    -iquote "$work/c" "$work/c"/*.c -Wl,--gc-sections -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY timeout 15 "$work/test"
printf '%s\n' 'Android text input UTF-8, ordered edits, focus, and session lifetime passed'
