#!/bin/sh
# The same package and real-browser checks as CI's Build Browser Add-ons job.
set -eu
export YUE_DESKTOP_RECOVERY=0
unset DISPLAY WAYLAND_DISPLAY XAUTHORITY DBUS_SESSION_BUS_ADDRESS
make package-unpackaged-assets chrome-web-store firefox-addons firefox-addons-lint
test -f build/dist/inbe-chrome-web-store.zip
test -f build/dist/inbe-firefox-addons.zip
make web-smoke-test
LIBGL_ALWAYS_SOFTWARE=1 make web-smoke-test-firefox
