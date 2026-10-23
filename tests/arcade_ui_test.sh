#!/bin/sh
# Arcade on a private Xvfb display with disposable profiles: no inherited
# desktop, session bus or desktop recovery reaches the app. Where user
# namespaces allow it, the test also runs without a network, so the node is
# never contacted.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
binary=${1:-"$root/build/bin/linux/inbe-linux-x86_64"}
package=${2:?Pass an Arcade package, arcade.zib}
isolate=
offline=
if unshare -rn true 2>/dev/null; then
    isolate="unshare -rn"
    offline=--offline
fi
# shellcheck disable=SC2086
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS -u GDK_DISPLAY \
    -u SESSION_MANAGER YUE_DESKTOP_RECOVERY=0 SDL_AUDIODRIVER=dummy APP_NO_TRAY=1 \
    $isolate timeout 300s xvfb-run -a -n 300 -s '-noreset -screen 0 1280x900x24' \
    python3 "$root/tests/arcade_ui_test.py" "$binary" "$package" $offline
