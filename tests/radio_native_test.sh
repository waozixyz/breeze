#!/bin/sh
# Live radio as the Linux app builds it on Kryon's desktop host
# (tests/radio_native_behavior.zi), under ASan and UBSan.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=${1:-"$root/build/packages/ziran/build/bin"}
mp3=${2:-"$root/vendor-builds/linux/x86_64/audio-codecs/libziran_mp3.a"}
work="$root/build/radio-test"
rm -rf "$work/c"
mkdir -p "$work/c"
"$bin/ziran" build --project --offline --target=c --no-main \
    --define PLATFORM_DESKTOP --define DESKTOP_HOST --define NATIVE_WINDOW_HAVE_SDL \
    --root "$root" --module-path "$root/tests" \
    -o "$work/c" "$root/tests/radio_native_behavior.zi"
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'sine=frequency=440:duration=3:sample_rate=44100' \
    -ac 1 -c:a libmp3lame -b:a 128k "$work/mono.mp3"
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'sine=frequency=220:duration=3:sample_rate=48000' \
    -ac 2 -c:a libmp3lame -b:a 128k "$work/stereo.mp3"
audio="$root/vendor-builds/linux/x86_64/audio-codecs"
curl=${CURL_LIBRARY:-$(ls /usr/lib/x86_64-linux-gnu/libcurl.so.4 2>/dev/null || echo -lcurl)}
"${CC:-cc}" -std=c11 -O1 -g -DZIRAN_BOUNDS_CHECK -ffunction-sections -fdata-sections \
    -fsanitize=address,undefined -Wl,--gc-sections -w \
    -I"$root/build/packages/ziran/include" $(find "$work/c" -type d -printf ' -iquote %p') \
    $(find "$work/c" -type f -name '*.c') \
    "$mp3" "$audio/libvorbisfile.a" "$audio/libvorbis.a" "$audio/libogg.a" "$audio/libopus/libopus.a" \
    $(pkg-config --libs sdl2) "$curl" -lz -lpthread -lm -ldl -o "$work/test"
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY -u DBUS_SESSION_BUS_ADDRESS \
    YUE_DESKTOP_RECOVERY=0 ASAN_OPTIONS=detect_leaks=0 "$work/test" "$work/mono.mp3" "$work/stereo.mp3"
echo "Radio: mono/stereo MP3 into the mixer, bounded buffering, volume, HTTPS, reconnect and cancellation passed."
