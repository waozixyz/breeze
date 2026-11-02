#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
work="$root/build/telegram-svg-test"
mkdir -p "$work/c"
"$bin/zi2c" --no-main --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/kryon/src/ui" \
    -o "$work/c" "$root/tests/telegram_svg_behavior.zi"
cat > "$work/main.c" <<'C'
#include "telegram_svg_behavior.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
    assert(RenderTelegram());
    assert(TelegramPixel(0, 0) == 0);
    assert(TelegramPixel(12, 48) == 255);
    FILE *image = fopen("coverage.pgm", "wb");
    assert(image);
    fprintf(image, "P5\n96 96\n255\n");
    int area = 0, holes = 0;
    for (int y = 0; y < 96; y++) {
        for (int x = 0; x < 96; x++) {
            unsigned char value = TelegramPixel(x, y);
            area += value;
            if (x >= 30 && x < 65 && y >= 30 && y < 65 && value == 0) holes++;
            fwrite(&value, 1, 1, image);
        }
    }
    assert(fclose(image) == 0);
    assert(area / 255 > 4500 && area / 255 < 7500);
    assert(holes > 100);
    puts("Telegram SVG native vector raster: circle, transparent paper and coverage passed");
    return 0;
}
C
"${CC:-cc}" -std=c11 -I"$root/build/packages/ziran/include" -I"$work/c" \
    "$work/main.c" "$work/c"/*.c "$root/build/ziran-toolchain/libziran.a" -lm -lz -o "$work/test"
(cd "$work" && env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS "$work/test")
