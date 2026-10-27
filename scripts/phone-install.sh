#!/bin/sh
# Put a committed revision of Breeze on a phone for testing, in one step:
# build its debug APK from that commit alone (release-ready's container, with
# the locked packages and none of the uncommitted work in the checkout or its
# local package overrides), sign it with this machine's Android debug key so
# it updates the installed app with its data kept, install it, check that the
# phone holds exactly that APK, and open it from the launcher.
#
#   sh scripts/phone-install.sh                     HEAD on the Pixel 3a
#   sh scripts/phone-install.sh --device moto       HEAD on the Moto e6 play
#   sh scripts/phone-install.sh --revision COMMIT   another commit
#   sh scripts/phone-install.sh --apk PATH          skip the build
#
# --device takes pixel, moto or an adb serial. The Moto is shared: the
# script stops when another app is in front. It never uninstalls, so a key
# mismatch fails instead of wiping the app's data.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"

app_id=xyz.waozi.inbe.debug
activity=xyz.waozi.inbe.MainActivity
keystore=${ANDROID_DEBUG_KEYSTORE:-$HOME/.config/.android/debug.keystore}
android_sdk=${ANDROID_SDK_ROOT:-${ANDROID_HOME:-$HOME/Android/Sdk}}
output=build/release-ready-phone

device=pixel
revision=HEAD
apk=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --device) device=${2:?--device needs pixel, moto or a serial}; shift 2 ;;
        --revision) revision=${2:?--revision needs a commit}; shift 2 ;;
        --apk) apk=${2:?--apk needs a path}; shift 2 ;;
        *) echo "usage: sh scripts/phone-install.sh [--device pixel|moto|SERIAL] [--revision COMMIT] [--apk PATH]" >&2; exit 2 ;;
    esac
done

fail() {
    echo "phone-install: $*" >&2
    exit 1
}

# The phone, by the model adb reports for it.
case "$device" in
    pixel) model=Pixel_3a ;;
    moto) model=moto_e6_play ;;
    *) model="" ;;
esac
if [ -n "$model" ]; then
    serial=$(adb devices -l | awk -v model="model:$model" '$2 == "device" { for (i = 3; i <= NF; i++) if ($i == model) print $1 }' | head -n 1)
    [ -n "$serial" ] || fail "no $device in adb devices; reconnect it (the Pixel over Wireless Debugging)"
else
    serial=$device
    [ "$(adb -s "$serial" get-state 2>/dev/null)" = device ] || fail "adb device $serial is not connected"
fi
phone() {
    adb -s "$serial" "$@"
}
abi=$(phone shell getprop ro.product.cpu.abi | tr -d '\r')
[ -n "$abi" ] || fail "could not read the phone's ABI"
echo "phone-install: $(phone shell getprop ro.product.model | tr -d '\r') ($serial, $abi)"

if [ "$device" = moto ]; then
    front=$(phone shell dumpsys window | tr -d '\r' | sed -n 's/.*mCurrentFocus=Window{[^ ]* [^ ]* \([^/}]*\).*/\1/p' | head -n 1)
    case "$front" in
        ""|"$app_id"|*launcher*|*Launcher*|com.android.systemui) ;;
        *) fail "the shared Moto is showing $front; ask whoever uses it before installing" ;;
    esac
fi

if [ -z "$apk" ]; then
    commit=$(git rev-parse "$revision^{commit}")
    echo "phone-install: building $(git log -1 --format='%h %s' "$commit")"
    RELEASE_READY_REVISION=$commit RELEASE_READY_OUTPUT=$output \
        sh scripts/release-ready.sh ANDROID_ABI="$abi" android-debug
    apk=$(find "$output/build/android" -name "app*-$abi-debug.apk" | head -n 1)
    [ -f "$apk" ] || fail "the build left no app-$abi-debug.apk in $output/build/android"
fi
[ -f "$apk" ] || fail "no APK at $apk"

# The container signs with its own debug key; the installed app was signed
# with this machine's.
[ -f "$keystore" ] || fail "no debug keystore at $keystore"
build_tools=$(ls -d "$android_sdk"/build-tools/* | sort -V | tail -n 1)
signed=build/phone-install/$(basename "$apk" .apk)-signed.apk
mkdir -p build/phone-install
"$build_tools/zipalign" -f -p 4 "$apk" "$signed.aligned"
"$build_tools/apksigner" sign --ks "$keystore" --ks-pass pass:android \
    --ks-key-alias androiddebugkey --key-pass pass:android \
    --out "$signed" "$signed.aligned"
rm -f "$signed.aligned" "$signed.idsig"
"$build_tools/apksigner" verify "$signed" >/dev/null 2>&1 || fail "the signed APK does not verify"

phone install -r "$signed" || fail "install failed; the app was left as it was (never uninstall: that deletes its data)"
installed=$(phone shell pm path "$app_id" | tr -d '\r' | sed -n 's/^package://p' | grep base.apk | head -n 1)
[ -n "$installed" ] || fail "$app_id is not installed after the install"
local_hash=$(sha256sum "$signed" | cut -d' ' -f1)
phone_hash=$(phone shell sha256sum "$installed" | tr -d '\r' | cut -d' ' -f1)
[ "$local_hash" = "$phone_hash" ] || fail "the phone holds a different APK ($phone_hash) than $signed ($local_hash)"
echo "phone-install: installed $signed ($local_hash)"

phone shell am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER \
    -n "$app_id/$activity" >/dev/null
tries=0
while [ "$tries" -lt 15 ]; do
    if phone shell pidof "$app_id" >/dev/null 2>&1; then
        echo "phone-install: $app_id is open"
        exit 0
    fi
    tries=$((tries + 1))
    sleep 1
done
fail "installed, but $app_id did not start within 15 seconds; check logcat"
