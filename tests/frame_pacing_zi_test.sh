#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work=$root/build/frame-pacing-zi-test
rm -rf "$work/c"
mkdir -p "$work/c"

"$bin/ziran" check --project --offline ${PACKAGE_FLAGS:-} --root "$root/src" \
    "$root/src/app/app_frame_pacing.zi"
"$bin/ziran" build --target=c --project --offline ${PACKAGE_FLAGS:-} --no-main --root "$root/src" \
    -o "$work/c" "$root/src/app/app_frame_pacing.zi"
"${CC:-cc}" -std=c11 -Wall -Wextra -Werror \
    -Wno-unused-function -Wno-unused-variable \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" -I"$work/c" \
    "$root/tests/frame_pacing_link_test.c" \
    "$work/c/app_frame_pacing.c" "$work/c/session_screen.c" \
    "$work/c/frame_activity.c" "$work/c/smooth_frames.c" \
    "$work/c/kryon__frame_pacing.c" \
    "$work/c/practice_banner_draw.c" -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "Inbe frame pacing Ziran/native link test passed"
