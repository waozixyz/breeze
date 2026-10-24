#!/bin/sh
# The supplied Arcade package runs in a disposable profile on a private display.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
binary=${1:?Pass the Breeze binary}
package=${2:?Pass an Arcade package, arcade.zx}
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    -u GDK_DISPLAY -u SESSION_MANAGER YUE_DESKTOP_RECOVERY=0 \
    SDL_VIDEODRIVER=x11 LIBGL_ALWAYS_SOFTWARE=1 SDL_AUDIODRIVER=dummy APP_NO_TRAY=1 \
    timeout 240s xvfb-run -a -n 400 -s '-noreset -screen 0 1280x900x24' \
    python3 "$root/tests/shared_progress_ui_test.py" "$binary" "$package"
