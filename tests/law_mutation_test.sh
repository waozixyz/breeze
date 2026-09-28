#!/bin/sh
# Every deliberately broken implementation must be rejected by the laws, so
# the laws are known not to be vacuous. The unmutated tree must pass.
set -eu

ziran=${1:?pass the ziran command}
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM

fresh() {
    rm -rf "$work/src"
    mkdir -p "$work/src/app" "$work/src/storage"
    cp "$root"/src/app/sync_retry.zi "$root"/src/app/sync_retry_laws.zi \
        "$work/src/app/"
    cp "$root"/src/app/practice_lifecycle.zi \
        "$root"/src/app/practice_lifecycle_laws.zi "$work/src/app/"
    cp "$root"/src/storage/sync_result.zi "$root"/src/storage/storage_layout.zi \
        "$root"/src/storage/storage_layout_laws.zi "$work/src/storage/"
}

check() {
    "$ziran" check --root "$work/src" "$work/src/$1" > "$work/out.json" \
        2> "$work/out.err"
}

fresh
check app/sync_retry_laws.zi
check app/practice_lifecycle_laws.zi
check storage/storage_layout_laws.zi

# file, module to check, sed expression, expected disproved law
mutate() {
    file=$1 module=$2 expression=$3 law=$4
    fresh
    sed -i "$expression" "$work/src/$file"
    if cmp -s "$root/src/$file" "$work/src/$file"; then
        echo "mutation did not change $file: $expression" >&2
        exit 1
    fi
    if check "$module"; then
        echo "laws accepted mutation: $file: $expression" >&2
        exit 1
    fi
    if ! grep -q "law $law is disproved" "$work/out.err"; then
        echo "mutation $expression did not disprove $law" >&2
        cat "$work/out.err" >&2
        exit 1
    fi
}

sync=app/sync_retry.zi
mutate $sync app/sync_retry_laws.zi \
    '0,/RetryDecision.{0, 0, 0}/s//RetryDecision.{0, 0, 1}/' SuccessResets
mutate $sync app/sync_retry_laws.zi \
    's/if attempt == 2 { return 15 }/if attempt == 2 { return 16 }/' \
    ChallengeRetries
mutate $sync app/sync_retry_laws.zi \
    's/ ||$//; /result == cast(s32) SyncResult.SYNC_REQUEST_FAILED$/d' \
    RequestRetries
mutate $sync app/sync_retry_laws.zi \
    's/if attempt > 4 { return 4 }/if attempt > 5 { return 5 }/' \
    AttemptStaysBounded
mutate $sync app/sync_retry_laws.zi \
    's/return RetryDecision.{attempt, 0, 1}/return RetryDecision.{attempt, 0, 0}/' \
    InvalidUrlStops
lifecycle=app/practice_lifecycle.zi
mutate $lifecycle app/practice_lifecycle_laws.zi \
    's/if auto_paused == 0 \&\& session_paused == 0 {/if auto_paused == 0 {/' \
    UserPauseIsNeverResumed
mutate $lifecycle app/practice_lifecycle_laws.zi \
    's/LifecycleDecision.{background_active, 0, 0, 0, auto_paused}/LifecycleDecision.{background_active, 0, 1, 0, 1}/' \
    DesktopNeverPauses
mutate $lifecycle app/practice_lifecycle_laws.zi \
    's/ \&\& indicator_visible != 0 {/ {/' BackgroundWithoutIndicatorPauses
mutate $lifecycle app/practice_lifecycle_laws.zi \
    's/if run != background_active {/if run == background_active {/' \
    ChangeMatchesState
mutate $lifecycle app/practice_lifecycle_laws.zi \
    's/} else if auto_paused != 0 {/} else if auto_paused != 0 || session_paused != 0 {/' \
    ResumeOnlyOwnPause
mutate storage/sync_result.zi app/sync_retry_laws.zi \
    's/SYNC_AUTH_FAILED :: 7/SYNC_AUTH_FAILED :: 8/' WireAuthFailed
mutate storage/storage_layout.zi storage/storage_layout_laws.zi \
    's/^CurrentDirectoryName :: "inbe"/CurrentDirectoryName :: "breathing"/' \
    CurrentDirectoryIsInbe
mutate storage/storage_layout.zi storage/storage_layout_laws.zi \
    's/^PreviousDatabaseEntry :: .*/PreviousDatabaseEntry :: "inbe-data\/inbe.db"/' \
    HistoricalEntryStaysImportable

echo "law mutation test passed"
