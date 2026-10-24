#!/bin/sh
# Capture times and orientations from JPEG, PNG and WebP Exif, natively
# with sanitizers and in the Ziran VM the packages run in.
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work=$root/build/media-metadata-test
include=${ZIRAN_INCLUDE:-"$root/build/packages/ziran/include"}
modules="--module-path $root/build/packages/ziran/std"

rm -rf "$work"
mkdir -p "$work/c"
# shellcheck disable=SC2086
"$bin/zi2c" --no-main --root "$root/tests" $modules \
    -o "$work/c" "$root/tests/media_metadata_behavior.zi"
cat > "$work/c/main.c" <<'C'
#include <stdio.h>
#include "media_metadata_behavior.h"
int main(void)
{
    int result = Answer();
    if (result != 42) {
        fprintf(stderr, "media metadata check %d failed\n", result);
        return 1;
    }
    return 0;
}
C
includes=$(find "$work/c" -type d -printf ' -iquote %p')
# shellcheck disable=SC2086
"${CC:-cc}" -std=c11 -DZIRAN_BOUNDS_CHECK -fsanitize=address,undefined \
    -I"$include" $includes "$work/c"/*.c -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY ASAN_OPTIONS=detect_leaks=0 "$work/test"
# shellcheck disable=SC2086
"$bin/ziran" bundle --root "$root/tests" $modules \
    --entry media_metadata_behavior:Answer -o "$work/check.zx" \
    "$root/tests/media_metadata_behavior.zi"
test "$("$bin/ziran" run "$work/check.zx")" = 42
printf '%s\n' 'Media metadata: Exif capture times and orientations passed natively and in the VM'
