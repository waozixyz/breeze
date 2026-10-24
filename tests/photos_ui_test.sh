#!/bin/sh
# Photos on a private Xvfb display with a disposable profile: no inherited
# desktop, session bus or desktop recovery reaches the app.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
binary=${1:-"$root/build/bin/linux/breeze-linux-x86_64"}
package=${2:-"$root/build/node-apps/photos.zx"}
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS -u GDK_DISPLAY \
    -u SESSION_MANAGER YUE_DESKTOP_RECOVERY=0 SDL_AUDIODRIVER=dummy APP_NO_TRAY=1 \
    timeout 240s xvfb-run -a -n 310 -s '-noreset -screen 0 1280x900x24' \
    python3 "$root/tests/photos_ui_test.py" "$binary" "$package"
