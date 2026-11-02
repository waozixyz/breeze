#!/bin/sh
# Build the same headless typed module host for native or Android API 21.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"
ziran=${1:-build/ziran-toolchain/bin/ziran}
target=${2:-native}
liboqs=${3:-}
sqlite=${4:-}
work=$root/build/apps-platform-probe
source=$root/build/packages/ziran
generated=$work/generated-$target
mkdir -p "$generated"
set --
definitions=
if [ "$target" = android ]; then
    definitions="--define ANDROID_BUILD --define __arm__"
else
    # Native module callbacks now reach the real storage/optional app host.
    # Reuse the existing isolated host support rather than dummy DB bindings.
    set -- "$root/tests/delegate_account_host.zi" "$root/tests/sync_test_host.zi" \
        "$root/tests/background_audio_stub.zi"
fi
"$ziran" build --target=c --no-main $definitions --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/kryon/src/ui" --module-path "$root/build/packages/kryon/src/backend" \
    $(sh "$root/scripts/package-paths.sh" "$root/build/packages") \
    --module-path "$root/build/packages/daochi-client" \
    --module-path "$source/std" -o "$generated" \
    "$root/tests/apps_platform_probe.zi" "$@"
if [ "$target" = android ]; then
    sdk=${ANDROID_SDK_ROOT:-/home/wao/Android/Sdk}
    ndk=$sdk/ndk/28.2.13676358/toolchains/llvm/prebuilt/linux-x86_64/bin
    cc=$ndk/armv7a-linux-androideabi21-clang
    runtime=$root/build/bundle-runtime/android32-probe
    python3 scripts/build-bundle-runtime.py --source "$source" \
        --output "$runtime" --cc "$cc" --ar "$ndk/llvm-ar" \
        --objcopy "$ndk/llvm-objcopy" --flags='-O2 -fPIC -D_GNU_SOURCE -std=c11'
    binary=$work/android-armv7
elif [ "$target" = native ]; then
    cc=${CC:-cc}
    runtime=$root/build/ziran-toolchain
    binary=$work/native
else
    echo "usage: apps_platform_test.sh ZIRAN native|android" >&2
    exit 2
fi
set --
if [ "$target" = native ]; then
    : "${liboqs:?native probe requires LIBOQS_A}" "${sqlite:?native probe requires SQLITE_SRC}"
    set -- -DAPPS_PLATFORM_STORAGE \
        -I"$root/build/packages/monocypher/src" \
        "$root/build/packages/monocypher/src/monocypher.c" \
        "$root/build/packages/monocypher/src/optional/monocypher-ed25519.c" \
        "$sqlite" \
        "$liboqs" \
        -l:libcurl.so.4 -lz -ldl -lpthread
fi
"$cc" -D_GNU_SOURCE -std=c11 -O2 -ffunction-sections -fdata-sections \
    -I"$source/include" -I"$source/cmd/zir" -iquote "$generated" \
    "$root/tests/apps_platform_host.c" "$generated"/*.c \
    "$runtime/libziran.a" "$@" -Wl,--wrap=tmpfile -Wl,--gc-sections -lm -o "$binary"
if [ "$target" = android ]; then
    sh tests/apps_android_probe.sh
else
    # Storage can be reached by module callbacks. Never inherit an owner profile.
    mkdir -p "$root/work"
    profile=$(mktemp -d "$root/work/apps-platform-test.XXXXXX")
    trap 'rm -rf "$profile"' EXIT HUP INT TERM
    mkdir -p "$profile/home"
    env -u INBE_DIARY_IMPORT -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY \
        -u DBUS_SESSION_BUS_ADDRESS -u SESSION_MANAGER YUE_DESKTOP_RECOVERY=0 \
        HOME="$profile/home" APP_DATA_ROOT="$profile/data" XDG_DATA_HOME="$profile/xdg" \
        "$binary" "$root/build/inbe.zx" "$root/build/inbe-full.zx"
fi
