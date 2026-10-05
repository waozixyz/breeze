#!/bin/sh
# Headless Moto app-UID verification; never opens an activity or user profile.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"
sdk=${ANDROID_SDK_ROOT:-/home/wao/Android/Sdk}
host=${SUBAPPS_ANDROID_HOST:-wao@thinkpad.local}
serial=ZE2223BQZT
package=xyz.waozi.inbe.moduleprobe
work=$root/build/subapps-platform-probe
tools=$sdk/build-tools/36.0.0
remote=/tmp/inbe-module-probe
device_transfer=/data/local/tmp/inbe-module-probe-68ee281b
mkdir -p "$work"
cat > "$work/AndroidManifest.xml" <<'XML'
<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="xyz.waozi.inbe.moduleprobe">
    <uses-sdk android:minSdkVersion="21" android:targetSdkVersion="28" />
    <application android:debuggable="true" android:hasCode="false" android:label="Inner Breeze module probe" />
</manifest>
XML
"$tools/aapt2" link --manifest "$work/AndroidManifest.xml" \
    -I "$sdk/platforms/android-36/android.jar" -o "$work/probe-unsigned.apk"
if [ ! -f "$work/probe.p12" ]; then
    keytool -genkeypair -keystore "$work/probe.p12" -storetype PKCS12 \
        -storepass public-test-only -keypass public-test-only -alias probe \
        -dname 'CN=Inner Breeze disposable module probe' -keyalg RSA -validity 365
fi
"$tools/apksigner" sign --ks "$work/probe.p12" --ks-key-alias probe \
    --ks-pass pass:public-test-only --key-pass pass:public-test-only \
    --out "$work/probe.apk" "$work/probe-unsigned.apk"
ssh -o BatchMode=yes "$host" "adb -s $serial get-state"
existing=$(ssh -o BatchMode=yes "$host" "adb -s $serial shell pm list packages $package")
if [ -n "$existing" ]; then
    echo "Probe package already exists; preserving it" >&2
    exit 1
fi
ssh -o BatchMode=yes "$host" "mkdir -p $remote"
scp -q "$work/probe.apk" "$work/android-armv7" build/inbe.zib "$host:$remote/"
installed=0
cleanup() {
    if [ "$installed" = 1 ]; then
        ssh -o BatchMode=yes "$host" "adb -s $serial uninstall $package"
    fi
    ssh -o BatchMode=yes "$host" "adb -s $serial shell rm -rf $device_transfer"
    ssh -o BatchMode=yes "$host" "rm -rf $remote"
}
trap cleanup EXIT HUP INT TERM
installed=1
ssh -o BatchMode=yes "$host" "adb -s $serial install --no-streaming -t $remote/probe.apk"
ssh -o BatchMode=yes "$host" "adb -s $serial shell run-as $package mkdir -p files/probe"
ssh -o BatchMode=yes "$host" "adb -s $serial shell mkdir -p $device_transfer"
ssh -o BatchMode=yes "$host" \
    "adb -s $serial push $remote/android-armv7 $device_transfer/host-probe"
ssh -o BatchMode=yes "$host" \
    "adb -s $serial push $remote/inbe.zib $device_transfer/inbe.zib"
ssh -o BatchMode=yes "$host" \
    "adb -s $serial shell run-as $package cp $device_transfer/host-probe files/probe/host-probe"
ssh -o BatchMode=yes "$host" \
    "adb -s $serial shell run-as $package cp $device_transfer/inbe.zib files/probe/inbe.zib"
expected=$(sha256sum build/inbe.zib | cut -d ' ' -f 1)
actual=$(ssh -o BatchMode=yes "$host" \
    "adb -s $serial shell run-as $package sha256sum files/probe/inbe.zib" | tr -d '\r' | cut -d ' ' -f 1)
if [ "$actual" != "$expected" ]; then
    echo "Transferred root bundle hash differs from the built package" >&2
    exit 1
fi
echo "App-private root package transfer matches SHA-256 $expected"
ssh -o BatchMode=yes "$host" \
    "adb -s $serial shell \"run-as $package sh -c 'chmod 700 files/probe/host-probe; cd files/probe; unset TMPDIR; id; ./host-probe inbe.zib'\""
echo 'Headless Android app-UID root/nested loader and feature execution passed'
