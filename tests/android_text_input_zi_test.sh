#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work="$root/build/android-text-input-test"
source="$root/tests/android_text_input_behavior.zi"
rm -rf "$work/c"
mkdir -p "$work/c"
cd "$root"
"$bin/ziran" build --project --offline ${PACKAGE_FLAGS:-} --target=c \
    --define ANDROID_BUILD --define KRYON_ANDROID_HOST --root "$root/tests" \
    -o "$work/c" "$source"
set -- "$work/c"/p*_paint_queue.h
printf '#include "%s"\n' "${1##*/}" > "$work/c/kryon_raster_test_backend.h"
"${CC:-cc}" -std=c11 -D_DEFAULT_SOURCE -O2 -pthread \
    -ffunction-sections -fdata-sections -I"$root/build/packages/ziran/include" \
    -iquote "$work/c" "$root/tests/kryon_raster_test_host.c" "$work/c"/*.c \
    -Wl,--gc-sections -lm -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY timeout 15 "$work/test"
printf '%s\n' 'Android text input UTF-8, ordered edits, focus, and session lifetime passed'
