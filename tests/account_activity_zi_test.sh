#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
compiler=${1:-"$root/build/ziran-toolchain/bin/ziran"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
work=$root/build/account-activity-test
data=$(mktemp -d /tmp/inbe-account-activity.XXXXXX)
trap 'rm -rf "$data"' EXIT HUP INT TERM
unset DISPLAY WAYLAND_DISPLAY XAUTHORITY DBUS_SESSION_BUS_ADDRESS
export YUE_DESKTOP_RECOVERY=0
mkdir -p "$work/generated"
"$compiler" build --target=c --define PLATFORM_DESKTOP --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$root/build/packages/kryon/src/backend" \
    --module-path "kryon=$root/build/packages/kryon/src/ui" \
    --module-path "kryon=$root/build/packages/kryon/src/backend" \
    --module-path "$root/build/packages/kss/src" --module-path "oqs=$root/build/packages/oqs/src" \
    --module-path "$root/build/packages/game2d/src" --module-path "$root/build/packages/ziran/std" \
    --module-path "$root/build/packages/daochi-client" --entry account_activity_behavior:Check \
    -o "$work/generated" "$root/tests/account_activity_behavior.zi" "$root/tests/sync_test_host.zi"
cat > "$work/generated/main.c" <<'C'
#include "account_activity_behavior.h"
#include <stdint.h>
#include <stdio.h>
#include <time.h>
static int64_t fixture_now = 1791540000;
static int schedules;
time_t __wrap_time(time_t *output) {
    if (output) *output = fixture_now;
    return fixture_now;
}
double GetTime(void) { return (double)(fixture_now - 1791539990); }
void FixtureAdvance(int64_t seconds) { fixture_now += seconds; }
int32_t FixtureSchedules(void) { return schedules; }
int32_t app_auto_sync(void *app) { (void)app; schedules++; return 1; }
int main(void) {
    int result = Check();
    if (result) fprintf(stderr, "Account activity checks failed: %d\n", result);
    return result ? 1 : 0;
}
C
monocypher=$root/build/packages/monocypher/src
"${CC:-cc}" -std=c11 -O1 -ffunction-sections -fdata-sections \
    -I"$root/build/packages/ziran/include" -I"$work/generated" \
    -I"$root/vendor-builds/sqlite" -I"$root/vendor-builds/linux/x86_64/inbe-liboqs/include" \
    -I"$monocypher" -I"$monocypher/optional" \
    "$work/generated"/*.c "$root/vendor-builds/sqlite/sqlite3.c" \
    "$monocypher/monocypher.c" "$monocypher/optional/monocypher-ed25519.c" "$liboqs" \
    -Wl,--gc-sections -Wl,--wrap=time -ldl -lpthread -lz -lm -o "$work/test"
APP_DATA_ROOT="$data" "$work/test"
printf '%s\n' 'Account activity, private outbox, controls, freshness and account switching passed'
