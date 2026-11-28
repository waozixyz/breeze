#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
work=$root/build/title-bars-zi-test
rm -rf "$work/c"
mkdir -p "$work/c"
cd "$root"
"$bin/ziran" build --project --offline ${PACKAGE_FLAGS:-} --target=c --no-main \
    --root "$root/src" -o "$work/c" "$root/src/app/app_chrome.zi" \
    "$root/src/app/practice_title_bar.zi" "$root/src/app/assets.zi" \
    "$root/src/app/image_dimensions.zi"
python3 "$root/scripts/embed-app-assets.py" "$work/assets.c" \
    "$root/build/packages/kryon/icons/ui.webp"
# Project mode uses the dependency module identity in generated C headers.
for header in "$work/c"/kryon__image.h "$work/c"/kryon__paint_queue.h "$work/c"/kryon__image_raster.h "$work/c"/kryon__tree.h; do
    test -f "$header"
    printf '#include "%s"\n' "${header##*/}"
done > "$work/c/chrome_test_backend.h"
printf '#define InstallChromePictures kryon__image_ImageUsePictures\n' >> "$work/c/chrome_test_backend.h"
printf '#include "kryon__paint_queue.h"\n' > "$work/c/kryon_raster_test_backend.h"
"${CC:-cc}" -std=c11 -ffunction-sections -fdata-sections \
    -Dimage_dimensions_ImageWidth=ImageWidth \
    -Dimage_dimensions_ImageHeight=ImageHeight \
    -Wl,--gc-sections -I"$root/build/packages/ziran/include" -I"$work/c" \
    -I"$root/src/app" \
    "$root/tests/app_chrome_link_test.c" "$root/tests/kryon_raster_test_host.c" "$work/assets.c" "$work/c"/*.c \
    -lm -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    HARMONY_DESKTOP_RECOVERY=0 "$work/test"
echo "Inbe title bar Ziran/native link test passed"
