#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
mkdir -p "$root/build"
profile=$(mktemp -d "$root/build/desktop-test-profile.XXXXXX")
child=
stop_test() {
    if [ -n "$child" ]; then
        kill -TERM "$child" 2>/dev/null || true
        wait "$child" 2>/dev/null || true
    fi
    exit "$1"
}
trap 'rm -rf -- "$profile"' EXIT
trap 'stop_test 129' HUP
trap 'stop_test 130' INT
trap 'stop_test 143' TERM

unset DISPLAY WAYLAND_DISPLAY WAYLAND_SOCKET XAUTHORITY GDK_DISPLAY
unset DBUS_SESSION_BUS_ADDRESS DBUS_STARTER_ADDRESS DBUS_STARTER_BUS_TYPE SESSION_MANAGER
unset APP_DATA_ROOT INBE_SCREENSHOT_DATA_ROOT ENTITY_DATA INBE_DIARY_IMPORT
export HOME="$profile/home" XDG_CONFIG_HOME="$profile/config"
export XDG_DATA_HOME="$profile/data" XDG_CACHE_HOME="$profile/cache"
export XDG_STATE_HOME="$profile/state" XDG_RUNTIME_DIR="$profile/runtime"
export HARMONY_DESKTOP_RECOVERY=0 YUE_DESKTOP_RECOVERY=0
mkdir -m 700 "$HOME" "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_CACHE_HOME" \
    "$XDG_STATE_HOME" "$XDG_RUNTIME_DIR"
"$@" &
child=$!
wait "$child"
