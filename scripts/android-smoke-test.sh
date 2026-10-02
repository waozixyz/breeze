#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"
sdk_root=${ANDROID_SDK_ROOT:-${ANDROID_HOME:-${1:-}}}
app_id=${2:-xyz.waozi.inbe.debug}
activity=${3:-xyz.waozi.inbe.MainActivity}
serial=${ANDROID_SMOKE_SERIAL:-${ANDROID_EMULATOR_PORT:+emulator-$ANDROID_EMULATOR_PORT}}
observations=${ANDROID_SMOKE_OBSERVATIONS:-15}
interval=${ANDROID_SMOKE_INTERVAL:-1}
logs=${ANDROID_SMOKE_LOG_DIR:-build/android}

fail() {
    echo "android smoke: FAIL: $*; see $logs/android-smoke-logcat.txt" >&2
    exit 1
}

[ -n "$sdk_root" ] || { echo 'android smoke: set ANDROID_SDK_ROOT or ANDROID_HOME' >&2; exit 2; }
adb_cmd="$sdk_root/platform-tools/adb"
[ -x "$adb_cmd" ] || adb_cmd=adb
adb_run() {
    if [ -n "$serial" ]; then "$adb_cmd" -s "$serial" "$@"
    else "$adb_cmd" -e "$@"
    fi
}
case "$observations" in ''|*[!0-9]*) echo 'android smoke: observations must be a positive integer' >&2; exit 2;; esac
[ "$observations" -gt 0 ] || exit 2
mkdir -p "$logs"
capture() {
    adb_run logcat -d -v threadtime > "$logs/android-smoke-logcat.txt" 2>&1 || true
    adb_run logcat -b crash -d > "$logs/android-smoke-crash.txt" 2>&1 || true
    adb_run shell dumpsys activity exit-info "$app_id" > "$logs/android-smoke-exit-info.txt" 2>&1 || true
}
trap capture EXIT

if [ "${ANDROID_SMOKE_SKIP_EMULATOR:-0}" != 1 ]; then
    env -u DISPLAY -u WAYLAND_DISPLAY ANDROID_EMULATOR_HEADLESS=1 bash scripts/emulator.sh
fi
if [ -n "$serial" ]; then
    timeout 180 "$adb_cmd" -s "$serial" wait-for-device
else
    timeout 180 "$adb_cmd" -e wait-for-device
fi
adb_run logcat -c
if [ -n "${ANDROID_SMOKE_APK:-}" ]; then
    [ -f "$ANDROID_SMOKE_APK" ] || fail 'APK does not exist'
    adb_run install -r -t "$ANDROID_SMOKE_APK"
else
    selector=-e
    if [ -n "$serial" ]; then selector="-s $serial"; fi
    ${MAKE:-make} android-install ADB="$adb_cmd $selector"
fi

start() {
    adb_run shell am start -W -n "$app_id/$activity" > "$logs/android-smoke-launch.txt" 2>&1 || fail 'activity could not start'
    if ! grep -q '^Status: ok' "$logs/android-smoke-launch.txt"; then
        cat "$logs/android-smoke-launch.txt" >&2
        fail 'activity launch did not succeed'
    fi
}
process() { adb_run shell pidof "$app_id" 2>/dev/null | tr -d '\r'; }
observe() {
    count=0
    while [ "$count" -lt "$observations" ]; do
        sleep "$interval"
        current=$(process || true)
        [ -n "$current" ] || fail 'app process exited'
        [ "$current" = "$pid" ] || fail 'app process restarted unexpectedly'
        count=$((count + 1))
    done
}
foreground() {
    adb_run shell dumpsys activity activities > "$logs/android-smoke-activity.txt"
    grep -E 'mResumedActivity|topResumedActivity' "$logs/android-smoke-activity.txt" |
        grep -F "$app_id/" > /dev/null || fail 'app is not the resumed activity'
}

adb_run shell am force-stop "$app_id"
start
pid=$(process || true)
[ -n "$pid" ] || fail 'app exited during startup'
observe
foreground
adb_run shell input keyevent KEYCODE_HOME
observe
start
observe
foreground
echo "android smoke: PASS: $app_id survived startup and background/resume (PID $pid)"
