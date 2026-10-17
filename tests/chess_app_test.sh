#!/bin/sh
set -eu

# Chess from its real package in the portable VM: a game against the
# computer that survives a restart, and a game between two friends through
# a fake node that keeps shared records as Daochi's shared lists do.
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:-"$root/build/ziran-toolchain/bin/ziran"}
packages=${INBE_PACKAGES:-"$root/build/packages"}
work=${CHESS_APP_TEST_DIR:-"$root/build/chess-app-test"}
unset DISPLAY WAYLAND_DISPLAY XAUTHORITY DBUS_SESSION_BUS_ADDRESS

rm -rf "$work"
mkdir -p "$work/c"
"$ziran" bundle --root "$root" --module-path "$root/src" \
    --module-path "$packages/kryon/src/ui" --module-path "$packages/ziran/std" \
    --define KRYON_HOSTED_UI --entry chess:Main -o "$work/chess.zib" "$root/apps/chess/chess.zi"
"$ziran" build --target=c --no-main --entry chess_app_behavior:main --root "$root/tests" \
    --module-path "$root/src" --module-path "$packages/kryon/src/backend" \
    --module-path "$packages/kryon/src/ui" --module-path "$packages/ziran/std" \
    -o "$work/c" "$root/tests/chess_app_behavior.zi"
# Modules imported by file keep their directories in the generated C.
includes=$(find "$work/c" -type d -printf ' -iquote %p')
# shellcheck disable=SC2046,SC2086
"${CC:-cc}" -O1 -std=c11 -ffunction-sections -fdata-sections $includes -I"$packages/ziran/include" \
    $(find "$work/c" -name '*.c') "${ZIRAN_LIB:-$root/build/ziran-toolchain/libziran.a}" \
    -Wl,--gc-sections -lm -lpthread -o "$work/run"
(cd "$work" && ./run) || {
    echo "chess app check $? failed" >&2
    exit 1
}
echo "Chess plays the computer, restores its game and plays a friend through shared records"
