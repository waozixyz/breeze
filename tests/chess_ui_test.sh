#!/bin/sh
# Chess on a private Xvfb display with a disposable profile: no inherited
# desktop, session bus or desktop recovery reaches the app.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
binary=${1:-"$root/build/bin/linux/inbe-linux-x86_64"}
package=${2:?Pass an Arcade or published Chess bundle}
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS -u GDK_DISPLAY \
    -u SESSION_MANAGER YUE_DESKTOP_RECOVERY=0 SDL_AUDIODRIVER=dummy APP_NO_TRAY=1 \
    timeout 240s xvfb-run -a -n 300 -s '-screen 0 1280x900x24' \
    python3 "$root/tests/chess_ui_test.py" "$binary" "$package"
