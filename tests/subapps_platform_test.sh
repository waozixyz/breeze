#!/bin/sh
# Build the same headless typed module host for native or Android API 21.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"
ziran=${1:-build/ziran-toolchain/bin/ziran}
target=${2:-native}
work=$root/build/subapps-platform-probe
source=$root/build/packages/ziran
mkdir -p "$work/generated"
"$ziran" build --target=c --no-main --root "$root/tests" \
    --module-path "$root/src" --module-path "$root/build/packages/kryon/src/ui" \
    --module-path "$source/std" -o "$work/generated" \
    "$root/tests/subapps_platform_probe.zi"
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
    echo "usage: subapps_platform_test.sh ZIRAN native|android" >&2
    exit 2
fi
"$cc" -D_GNU_SOURCE -std=c11 -O2 -ffunction-sections -fdata-sections \
    -I"$source/include" -I"$source/cmd/zir" -iquote "$work/generated" \
    "$root/tests/subapps_platform_host.c" "$work/generated"/*.c \
    "$runtime/libziran.a" -Wl,--wrap=tmpfile -Wl,--gc-sections -lm -o "$binary"
if [ "$target" = android ]; then
    sh tests/subapps_android_probe.sh
else
    "$binary" "$root/build/inbe.zib"
fi
