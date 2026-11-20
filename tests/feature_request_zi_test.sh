#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
output="$root/build/feature-request-test"
rm -rf "$output/c"
mkdir -p "$output"
"$bin/ziran" build --project --offline --target=c \
    --define PLATFORM_DESKTOP --define DESKTOP_HOST --define NATIVE_WINDOW_HAVE_SDL \
    --root "$root" --module-path "$root/tests" \
    -o "$output/c" "$root/tests/feature_request_behavior.zi"
"${CC:-cc}" -std=c11 -O2 -DZIRAN_BOUNDS_CHECK \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I"$root/build/packages/ziran/include" $(find "$output/c" -type d -printf ' -iquote %p') \
    $(find "$output/c" -type f -name '*.c') \
    $(pkg-config --libs sdl2 cairo pangocairo fontconfig freetype2 gio-2.0 x11) \
    -lz -lm -ldl -pthread -latomic -o "$output/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    -u SESSION_MANAGER -u GDK_DISPLAY -u KRYON_TEST_DRIVER \
    HARMONY_DESKTOP_RECOVERY=0 YUE_DESKTOP_RECOVERY=0 \
    SDL_VIDEODRIVER=x11 SDL_RENDER_DRIVER=software \
    xvfb-run -a -n 300 -s '-noreset -screen 0 800x600x24 -nolisten tcp' \
    python3 "$root/tests/feature_request_ui_test.py" "$output/test"
