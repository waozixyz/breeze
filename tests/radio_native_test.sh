#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/ziran-toolchain/bin"}
standard=${2:-"$root/build/packages/ziran/std"}
work="$root/build/radio-test"
curl=${CURL_LIBRARY:-$(ls /usr/lib/x86_64-linux-gnu/libcurl.so.4 2>/dev/null || echo -lcurl)}
mkdir -p "$work/c"
"$bin/zi2c" --no-main --root "$root/src" --module-path "$standard" \
    -o "$work/c" "$root/src/platform/radio_runtime.zi"
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'sine=frequency=440:duration=3:sample_rate=44100' \
    -ac 1 -c:a libmp3lame -b:a 128k "$work/mono.mp3"
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'sine=frequency=220:duration=3:sample_rate=48000' \
    -ac 2 -c:a libmp3lame -b:a 128k "$work/stereo.mp3"
"${CC:-cc}" -std=c11 -O1 -g -DZIRAN_BOUNDS_CHECK -ffunction-sections -fdata-sections \
    -fsanitize=address,undefined -Wl,--gc-sections \
    -I"$(dirname "$standard")/include" -I"$root/build/packages/raylib/src" \
    -I"$work/c" "$root/tests/radio_native_test.c" \
    "$work/c/platform/radio_runtime.c" "$work/c/radio_native.c" \
    "$work/c/c_string.c" "$work/c/net_http_curl_linux.c" \
    "$curl" -lpthread -lm -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    YUE_DESKTOP_RECOVERY=0 ASAN_OPTIONS=detect_leaks=0 "$work/test" "$work/mono.mp3" "$work/stereo.mp3"
