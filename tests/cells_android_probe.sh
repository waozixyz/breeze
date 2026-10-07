#!/bin/sh
# Headless Moto app-UID verification; never opens an activity or user profile.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"
sdk=${ANDROID_SDK_ROOT:-/home/wao/Android/Sdk}
host=${CELLS_ANDROID_HOST:-wao@thinkpad.local}
serial=ZE2223BQZT
probe_id=p$(date +%s)$$
package=xyz.waozi.inbe.cellprobe.$probe_id
work=$root/build/cells-platform-probe
tools=$sdk/build-tools/36.0.0
remote=/tmp/inbe-cell-probe-$probe_id
device_transfer=/data/local/tmp/inbe-cell-probe-$probe_id
mkdir -p "$work"
cat > "$work/AndroidManifest.xml" <<XML
<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="$package">
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
timeout 180 ssh -o BatchMode=yes -o ConnectTimeout=10 "$host" "adb -s $serial get-state"
existing=$(timeout 180 ssh -o BatchMode=yes -o ConnectTimeout=10 "$host" "adb -s $serial shell pm list packages $package")
if [ -n "$existing" ]; then
    echo "Probe package already exists; preserving it" >&2
    exit 1
fi
timeout 180 ssh -o BatchMode=yes -o ConnectTimeout=10 "$host" "mkdir -p $remote"
timeout 180 scp -q -o ConnectTimeout=10 "$work/probe.apk" "$work/android-armv7" build/inbe.zib build/inbe-full.zib "$host:$remote/"
installed=0
cleanup() {
    if [ "$installed" = 1 ]; then
        timeout 180 ssh -o BatchMode=yes -o ConnectTimeout=10 "$host" "timeout 30 adb -s $serial uninstall $package" || true
    fi
    timeout 180 ssh -o BatchMode=yes -o ConnectTimeout=10 "$host" "timeout 30 adb -s $serial shell rm -rf $device_transfer" || true
    timeout 180 ssh -o BatchMode=yes -o ConnectTimeout=10 "$host" "rm -rf $remote" || true
}
trap cleanup EXIT HUP INT TERM
installed=1
timeout 180 ssh -o BatchMode=yes -o ConnectTimeout=10 "$host" "adb -s $serial install --no-streaming -t $remote/probe.apk"
timeout 180 ssh -o BatchMode=yes -o ConnectTimeout=10 "$host" "adb -s $serial shell run-as $package mkdir -p files/probe"
timeout 180 ssh -o BatchMode=yes -o ConnectTimeout=10 "$host" "adb -s $serial shell mkdir -p $device_transfer"
timeout 180 ssh -o BatchMode=yes -o ConnectTimeout=10 "$host" \
    "adb -s $serial push $remote/android-armv7 $device_transfer/host-probe"
timeout 180 ssh -o BatchMode=yes -o ConnectTimeout=10 "$host" \
    "adb -s $serial push $remote/inbe.zib $device_transfer/inbe.zib"
timeout 180 ssh -o BatchMode=yes -o ConnectTimeout=10 "$host" \
    "adb -s $serial shell run-as $package cp $device_transfer/host-probe files/probe/host-probe"
timeout 180 ssh -o BatchMode=yes -o ConnectTimeout=10 "$host" \
    "adb -s $serial shell run-as $package cp $device_transfer/inbe.zib files/probe/inbe.zib"
timeout 180 ssh -o BatchMode=yes -o ConnectTimeout=10 "$host" \
    "adb -s $serial push $remote/inbe-full.zib $device_transfer/inbe-full.zib"
timeout 180 ssh -o BatchMode=yes -o ConnectTimeout=10 "$host" \
    "adb -s $serial shell run-as $package cp $device_transfer/inbe-full.zib files/probe/inbe-full.zib"
expected=$(sha256sum build/inbe.zib | cut -d ' ' -f 1)
actual=$(timeout 180 ssh -o BatchMode=yes -o ConnectTimeout=10 "$host" \
    "adb -s $serial shell run-as $package sha256sum files/probe/inbe.zib" | tr -d '\r' | cut -d ' ' -f 1)
if [ "$actual" != "$expected" ]; then
    echo "Transferred root bundle hash differs from the built package" >&2
    exit 1
fi
echo "App-private root package transfer matches SHA-256 $expected"
timeout 180 ssh -o BatchMode=yes -o ConnectTimeout=10 "$host" \
    "adb -s $serial shell \"run-as $package sh -c 'chmod 700 files/probe/host-probe; cd files/probe; unset TMPDIR; id; ./host-probe inbe.zib inbe-full.zib'\""
echo 'Headless Android app-UID catalogs, package reload, root/nested loader and feature execution passed'
