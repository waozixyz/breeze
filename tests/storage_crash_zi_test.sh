#!/bin/sh
set -eu

# Kill tests for storage. For each scenario a writer saves through the real
# storage code until it is killed with SIGKILL at a random moment, then a
# checker opens the data as the next start of the app would. See
# tests/storage_crash_behavior.zi for what each scenario writes and checks.
# STORAGE_CRASH_ROUNDS sets the kills per scenario (default 30).
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ziran=${1:-"$root/build/packages/ziran/build/bin/ziran"}
liboqs=${2:-"$root/vendor-builds/linux/x86_64/inbe-liboqs/lib/liboqs.a"}
rounds=${STORAGE_CRASH_ROUNDS:-30}
work=$root/build/storage-crash-zi-test
include=$root/build/packages/ziran/include

rm -rf "$work"
mkdir -p "$work/generated"
"$ziran" build --project --offline ${PACKAGE_FLAGS:-} --target=c --define PLATFORM_DESKTOP --root "$root/tests" \
    --entry storage_crash_behavior:Check \
    -o "$work/generated" "$root/tests/storage_crash_behavior.zi" \
    "$root/tests/sync_test_host.zi"
cat > "$work/generated/main.c" <<'C'
#include "storage_crash_behavior.h"
#include <stdio.h>
int main(void)
{
    int result = Check();
    if (result != 0) fprintf(stderr, "storage crash test stopped with code %d\n", result);
    return result == 0 ? 0 : 1;
}
C
"${CC:-cc}" -std=c11 -O0 -ffunction-sections -fdata-sections \
    -I"$include" -I"$work/generated" -I"$root/vendor-builds/sqlite" \
    -I"$root/vendor-builds/linux/x86_64/inbe-liboqs/include" \
    "$work/generated"/*.c "$root/vendor-builds/sqlite/sqlite3.c" "$liboqs" \
    -Wl,--gc-sections -ldl -lpthread -lz -lm -o "$work/test"

# Storage must never open the real data directory.
APP_DATA_ROOT="$work/data"
export APP_DATA_ROOT
mkdir -p "$APP_DATA_ROOT"
test_binary=$work/test

# A delay of $1 to $1 + $2 milliseconds, as seconds for sleep.
random_delay() {
    random=$(od -An -N2 -tu2 /dev/urandom | tr -d ' ')
    milliseconds=$(($1 + random % $2))
    printf '%d.%03d' $((milliseconds / 1000)) $((milliseconds % 1000))
}

acknowledged_count() {
    if [ -f "$APP_DATA_ROOT/$1.acks" ]; then
        wc -l < "$APP_DATA_ROOT/$1.acks" | tr -d ' '
    else
        echo 0
    fi
}

# $1 scenario, $2 and $3 the kill window in milliseconds, $4 a pattern of
# temporary files whose presence shows a kill landed in the middle of a write.
run_scenario() {
    scenario=$1
    temporary=$4
    rm -rf "$APP_DATA_ROOT/$scenario" "$APP_DATA_ROOT/$scenario.acks"
    interrupted=0
    early=0
    round=1
    while [ "$round" -le "$rounds" ]; do
        before=$(acknowledged_count "$scenario")
        env -u DISPLAY -u WAYLAND_DISPLAY CRASH_ROLE=writer CRASH_SCENARIO="$scenario" \
            "$test_binary" 2>>"$work/$scenario-writer.log" &
        writer=$!
        # Every fifth kill lands within 15 ms, while the writer is still
        # starting: storage_init checks, upgrades and copies the database.
        if [ $((round % 5)) -eq 0 ]; then
            sleep "$(random_delay 1 15)"
        else
            sleep "$(random_delay "$2" "$3")"
        fi
        kill -9 "$writer" 2>/dev/null || true
        status=0
        # The shell's "Killed" job notice is expected for every round.
        { wait "$writer"; } 2>/dev/null || status=$?
        if [ "$status" -ne 137 ]; then
            echo "FAIL $scenario round $round: the writer exited with $status instead of being killed" >&2
            tail -n 20 "$work/$scenario-writer.log" >&2
            exit 1
        fi
        if [ "$(acknowledged_count "$scenario")" = "$before" ]; then
            early=$((early + 1))
        fi
        if [ -n "$temporary" ]; then
            for file in "$APP_DATA_ROOT/$scenario"/$temporary; do
                if [ -e "$file" ]; then
                    interrupted=$((interrupted + 1))
                    break
                fi
            done
        fi
        if ! env -u DISPLAY -u WAYLAND_DISPLAY CRASH_ROLE=checker CRASH_SCENARIO="$scenario" \
            "$test_binary" 2>>"$work/$scenario-checker.log"; then
            echo "FAIL $scenario round $round: the checker found lost or partial data" >&2
            grep -E '^FAIL|stopped with code' "$work/$scenario-checker.log" | tail -n 20 >&2
            exit 1
        fi
        round=$((round + 1))
    done
    total=$(acknowledged_count "$scenario")
    if [ "$total" -eq 0 ]; then
        echo "FAIL $scenario: no write was acknowledged in $rounds rounds" >&2
        exit 1
    fi
    summary="$rounds SIGKILL rounds, $total acknowledged writes, $early kills before a new acknowledgement"
    if [ -n "$temporary" ]; then
        summary="$summary, $interrupted kills left a temporary file"
    fi
    echo "storage crash $scenario: $summary"
}

if ! env -u DISPLAY -u WAYLAND_DISPLAY CRASH_ROLE=restore "$test_binary" 2>"$work/restore.log"; then
    echo "FAIL restore: damaged database recovery" >&2
    grep -E '^FAIL|stopped with code' "$work/restore.log" >&2
    exit 1
fi
echo "storage crash restore: damaged header and page kept untouched, last good copy restored"

run_scenario sessions 1 400 ""
run_scenario payloads 1 400 "packages/*.new"
run_scenario copies 1 600 "inbe.db.last-good.tmp"
run_scenario drafts 1 400 ""
rm -rf "$work/data"
