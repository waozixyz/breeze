#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
compiler=${1:-"$root/build/packages/ziran/build/bin/ziran"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
work="$root/build/crash-report-zi-test"
exec 9>"$work.lock"
flock 9
unset DISPLAY WAYLAND_DISPLAY XAUTHORITY DBUS_SESSION_BUS_ADDRESS
export HARMONY_DESKTOP_RECOVERY=0
rm -rf "$work/generated" "$work/signal-data"
mkdir -p "$work/generated" "$work/signal-data"
cd "$root"
"$compiler" build --project --offline ${PACKAGE_FLAGS:-} --target=c --no-main \
    --define PLATFORM_DESKTOP --define DESKTOP_HOST --define STORAGE_TEST_REAL_HOST_SERVICES --root "$root" \
    -o "$work/generated" \
    "$root/tests/crash_report_behavior.zi"
cat > "$work/generated/main.c" <<'C'
#include "crash_report_behavior.h"
int main(void)
{
    int result = Check();
    return result == 0 ? 0 : 1;
}
C
monocypher="$root/build/packages/monocypher/src"
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections \
    -I"$root/build/packages/ziran/include" -iquote "$work/generated" -iquote "$work/generated/tests" \
    -I"$root/vendor-builds/sqlite" -I"$root/vendor-builds/linux/x86_64/inbe-liboqs/include" \
    -I"$monocypher" -I"$monocypher/optional" \
    "$work/generated"/*.c "$work/generated/tests"/*.c "$root/vendor-builds/sqlite/sqlite3.c" \
    "$monocypher/monocypher.c" "$monocypher/optional/monocypher-ed25519.c" \
    "$liboqs" -Wl,--gc-sections -latomic -ldl -lpthread -lz -lm -o "$work/test"

# Phase 1: trigger a real SIGABRT in a child process and verify the handler
# writes the pending report and re-raises SIGABRT (exit code 128 + 6 = 134).
child_status=0
CRASH_TEST_ROLE=crash-child CRASH_TEST_ROOT="$work/signal-data" "$work/test" >/dev/null 2>&1 || child_status=$?
if [ "$child_status" -ne 134 ]; then
    echo "FAIL: expected crash child to terminate with SIGABRT (134), got $child_status" >&2
    exit 1
fi

# Phase 2: run all parsing, consent, dismissal, outbox, and signal-relaunch checks.
APP_DATA_ROOT=/tmp/inbe-crash-report-test/data \
    CRASH_TEST_SIGNAL_ROOT="$work/signal-data" \
    "$work/test"
rm -rf "$work/signal-data"
printf '%s\n' 'Crash report capture, consent, dismissal, and feedback outbox checks passed'
