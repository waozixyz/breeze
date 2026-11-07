#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
kryon=${KRYON_DIR:-"$root/build/packages/kryon"}
entity=${ENTITY_DIR:-"$root/build/packages/entity"}
apps=${APPS_DIR:-"$root/build/packages/apps"}
work=$root/build/notification-lifecycle-test
rm -rf "$work"
mkdir -p "$work/c"
sh "$root/scripts/run-ziran.sh" "$bin/zi2c" --no-main --root "$root" \
    --module-path "$root/src" \
    --module-path "$kryon/src/ui" \
    --module-path "$kryon/src/backend" \
    --module-path "kryon=$kryon/src/ui" \
    --module-path "kryon=$kryon/src/backend" \
    --module-path "entity=$entity/src" \
    --module-path "apps=$apps/src" \
    --module-path "$root/build/packages/css/src" \
    $(sh "$root/scripts/package-paths.sh" "$root/build/packages") \
    --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" \
    -o "$work/c" "$root/tests/notification_lifecycle_behavior.zi"
find "$work/c" -name '*.c' -type f -exec \
    "${CC:-cc}" -std=c11 -ffunction-sections -fdata-sections \
    -Wl,--gc-sections -Wl,--wrap=LocaleText \
    -Wl,--wrap=DailyNotificationsSupported -Wl,--wrap=ScheduleDailyNotification \
    -Wl,--wrap=ScheduleNotificationDates -Wl,--wrap=CancelDailyNotification \
    -I"$root/build/packages/ziran/include" -I"$work/c" -I"$work/c/tests" \
    -o "$work/test" {} +
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u GDK_DISPLAY "$work/test"
echo "Notification lifecycle, preference preservation, reminder catch-up and plain toast timing passed"
