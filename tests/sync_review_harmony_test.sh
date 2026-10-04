#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
binary=${1:-"$root/build/bin/linux/inbe-linux-x86_64"}
harmony=${HARMONY_TEST_ROOT:-"$(dirname -- "$root")/harmony"}
host=${HARMONY_REVIEW_TEST_BUILD:-"$harmony/build/app-control"}
exec env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    -u SESSION_MANAGER YUE_DESKTOP_RECOVERY=0 HARMONY_TEST_ROOT="$harmony" \
    HARMONY_REVIEW_TEST_BUILD="$host" python3 "$root/tests/sync_review_harmony_test.py" "$binary"
