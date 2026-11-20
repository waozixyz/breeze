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
# Project mode prefixes dependency C headers with their package identity.
for header in "$work/c"/p*_image.h "$work/c"/p*_paint_queue.h "$work/c"/p*_image_raster.h "$work/c"/p*_tree.h; do
    test -f "$header"
    printf '#include "%s"\n' "${header##*/}"
done > "$work/c/chrome_test_backend.h"
set -- "$work/c"/p*_image.h
image_module=${1##*/}
printf '#define InstallChromePictures %s_ImageUsePictures\n' "${image_module%.h}" >> "$work/c/chrome_test_backend.h"
set -- "$work/c"/p*_paint_queue.h
printf '#include "%s"\n' "${1##*/}" > "$work/c/kryon_raster_test_backend.h"
"${CC:-cc}" -std=c11 -ffunction-sections -fdata-sections \
    -Dimage_dimensions_ImageWidth=ImageWidth \
    -Dimage_dimensions_ImageHeight=ImageHeight \
    -Wl,--gc-sections -I"$root/build/packages/ziran/include" -I"$work/c" \
    -I"$root/src/app" \
    "$root/tests/app_chrome_link_test.c" "$root/tests/kryon_raster_test_host.c" "$work/assets.c" "$work/c"/*.c \
    -lm -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY "$work/test"
echo "Inbe title bar Ziran/native link test passed"
