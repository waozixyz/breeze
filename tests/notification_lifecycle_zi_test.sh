#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
compile_only=${2:-}
work=$root/build/notification-lifecycle-test
rm -rf "$work/c"
mkdir -p "$work/c"
cd "$root"
sh "$root/scripts/run-ziran.sh" "$bin/ziran" build --project --offline ${PACKAGE_FLAGS:-} \
    --target=c --no-main --define DESKTOP_HOST --define KRYON_TEST_DRIVER --root "$root" \
    -o "$work/c" "$root/tests/notification_lifecycle_behavior.zi"
paint_header=$(find "$work/c" -name 'kryon__paint_queue.h' -type f)
test -f "$paint_header"
printf '#include "%s"\n' "$(basename "$paint_header")" > "$work/c/kryon_raster_test_backend.h"
cat > "$work/c/image_fixture.c" <<'C'
#include "kryon_raster_test_backend.h"
#include <assert.h>

void RasterLine(Rectangle line, Color color) { (void)line; (void)color; assert(0); }
void RasterImage(String path, uint32_t texture, Rectangle source,
    Rectangle destination, Rectangle clip, Vector2 origin, float rotation,
    float radius, Color tint) {
    (void)path; (void)texture; (void)source; (void)destination; (void)clip;
    (void)origin; (void)rotation; (void)radius; (void)tint; assert(0);
}

int32_t ImageWidth(String path) { (void)path; assert(0); return 0; }
int32_t ImageHeight(String path) { (void)path; assert(0); return 0; }
C
# The fixture supplies raster and metrics functions so unexpected immediate
# painting fails without starting a desktop surface.
set --
for source in "$work/c"/*.c "$work/c/tests"/*.c; do
    case "$source" in */kryon__cairo_raster.c) continue ;; esac
    set -- "$@" "$source"
done
"${CC:-cc}" -std=c11 -ffunction-sections -fdata-sections \
    -Wl,--gc-sections -Wl,--wrap=LocaleText -Wl,--wrap=WindowFocusedHost \
    -Wl,--wrap=TestDriverActive -Wl,--wrap=DailyNotificationsSupported -Wl,--wrap=ScheduleDailyNotification \
    -Wl,--wrap=ScheduleNotificationDates -Wl,--wrap=CancelDailyNotification \
    -I"$root/build/packages/ziran/include" -I"$work/c" -I"$work/c/tests" \
    -o "$work/test" "$@" -lz -lm
if [ "$compile_only" = '--compile-only' ]; then
    exit 0
fi
sh "$root/tests/run-isolated-desktop.sh" "$work/test"
echo "Notification lifecycle, preference preservation, reminder catch-up and plain toast timing passed"
