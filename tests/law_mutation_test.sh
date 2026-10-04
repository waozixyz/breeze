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
    cp "$root"/src/app/sync_recovery_policy.zi \
        "$root"/src/app/sync_recovery_policy_laws.zi "$work/src/app/"
    cp "$root"/src/storage/habit_merge_model.zi \
        "$root"/src/storage/habit_merge_laws.zi "$work/src/storage/"
    cp "$root"/src/storage/sync_restore_model.zi \
        "$root"/src/storage/sync_restore_laws.zi "$work/src/storage/"
    mkdir -p "$work/src/core"
    cp "$root"/src/core/types.zi "$work/src/core/"
    cp "$root"/src/app/modal_rules.zi "$root"/src/app/modal_rules_laws.zi \
        "$work/src/app/"
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
check app/sync_recovery_policy_laws.zi
check app/modal_rules_laws.zi
check storage/habit_merge_laws.zi
check storage/sync_restore_laws.zi
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
mutate $sync app/sync_retry_laws.zi \
    's/ || retry_after_sign_in(result)//' AuthenticationFailureRetries
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
recovery=app/sync_recovery_policy.zi
mutate $recovery app/sync_recovery_policy_laws.zi \
    's/if identity_current != 0 \&\& succeeded != 0 {/if succeeded != 0 {/' \
    OnlyCurrentAccountApplies
mutate $recovery app/sync_recovery_policy_laws.zi \
    's/if stage <= SocialStageFriends || identity_current == 0 {/if stage <= SocialStageRequests || identity_current == 0 {/' \
    RequiredFailureKeepsKnownData
mutate $recovery app/sync_recovery_policy_laws.zi \
    's/if stage <= SocialStageFriends || identity_current == 0 {/if stage <= SocialStageFriends {/' \
    SwitchedAccountStopsRefresh
mutate $recovery app/sync_recovery_policy_laws.zi \
    's/if stage == SocialStageStreak {/if stage != SocialStageStreak {/' \
    StreakFailureDropsOnlyStreak
mutate $recovery app/sync_recovery_policy_laws.zi \
    's/(next == SocialStageAverage \&\& practice_is_whm == 0)/(next == SocialStageAverage \&\& practice_is_whm != 0)/' \
    FinishesAfterStreakUnlessWhm
merge=storage/habit_merge_model.zi
mutate $merge storage/habit_merge_laws.zi \
    's/if mine > theirs {/if mine < theirs {/' MergeKeepsMine
mutate $merge storage/habit_merge_laws.zi \
    's/return HabitDayValue(HabitDayValue(a\[day\], b\[day\]), c\[day\])/return HabitDayValue(a[day], b[day])/' \
    MergeAssociates
mutate $merge storage/habit_merge_laws.zi \
    's/    return theirs$/    return theirs + 1/' MergeInventsNothing

# The real SQL must fail the same statements when it loses progress.
fresh
mkdir -p "$work/sql/src/storage"
cp "$root"/src/storage/storage_habit_sync.zi "$root"/src/storage/habit_sync_sql.zi \
    "$root"/src/storage/schema_sql.zi "$work/sql/src/storage/"
HABIT_MERGE_ROOT="$work/sql" python3 "$root/tests/habit_merge_sql_test.py" > /dev/null
sed -i 's/completed=MAX(completed,/completed=MIN(completed,/' \
    "$work/sql/src/storage/storage_habit_sync.zi"
if HABIT_MERGE_ROOT="$work/sql" python3 "$root/tests/habit_merge_sql_test.py" \
    > /dev/null 2>&1; then
    echo "SQL merge test accepted a merge that loses progress" >&2
    exit 1
fi
restore=storage/sync_restore_model.zi
mutate $restore storage/sync_restore_laws.zi \
    's/    if present != 0 {/    if present == 0 {/' RestoreKeepsEveryLocalChange
mutate $restore storage/sync_restore_laws.zi \
    's/^    return OutboxAfterClear(queued_before)/    return 1/' \
    RestoreQueuesOnlyLocalData

# The real restore SQL must fail the same statements when it leaves data out.
mkdir -p "$work/restore/src/storage"
cp "$root"/src/storage/storage_core.zi "$root"/src/storage/schema_sql.zi \
    "$work/restore/src/storage/"
SYNC_RESTORE_ROOT="$work/restore" python3 \
    "$root/tests/sync_restore_sql_test.py" > /dev/null
sed -i "s/FROM elist_items WHERE user_id/FROM elist_items WHERE 0=1 AND user_id/" \
    "$work/restore/src/storage/storage_core.zi"
if SYNC_RESTORE_ROOT="$work/restore" python3 \
    "$root/tests/sync_restore_sql_test.py" > /dev/null 2>&1; then
    echo "restore test accepted a restore that leaves local data unqueued" >&2
    exit 1
fi
modal=app/modal_rules.zi
mutate $modal app/modal_rules_laws.zi \
    's/return screen == ScreenStart$/return screen == ScreenSettings/' \
    MeditationSetupOnlyOnStart
mutate $modal app/modal_rules_laws.zi \
    's/^    return true$/    return false/' OtherDialogsAppearAnywhere
mutate $modal app/modal_rules_laws.zi \
    's/screen == ScreenHabitEdit  || (screen == ScreenHabits \&\& habit_edit_tab)/screen == ScreenHabitEdit  || screen == ScreenHabits/' \
    DeleteHabitNeedsEditor
mutate storage/sync_result.zi app/sync_retry_laws.zi \
    's/SYNC_AUTH_FAILED :: 7/SYNC_AUTH_FAILED :: 8/' WireAuthFailed
mutate storage/storage_layout.zi storage/storage_layout_laws.zi \
    's/^CurrentDirectoryName :: "inbe"/CurrentDirectoryName :: "breathing"/' \
    CurrentDirectoryIsInbe
mutate storage/storage_layout.zi storage/storage_layout_laws.zi \
    's/^PreviousDatabaseEntry :: .*/PreviousDatabaseEntry :: "inbe-data\/inbe.db"/' \
    HistoricalEntryStaysImportable

echo "law mutation test passed"
