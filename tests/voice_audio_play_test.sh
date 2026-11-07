#!/bin/sh
# Real Ogg Opus narration and Lumi guide playback to completion through
# voice_audio, Kryon's MediaAudio provider and the audio package's libopus on
# a private null audio device (tests/voice_audio_play_test.c).
#
#   sh tests/voice_audio_play_test.sh ZIRAN_BIN_DIR RAYLIB_SOURCE RAYLIB_A LIBOPUS_A [PRACTICES]
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=$1
raylib_source=$2
raylib_a=$3
libopus_a=$4
practices=${5:-"$root/build/packages/practices"}
work=$root/build/voice-audio-play-test
mkdir -p "$work"

# miniaudio with only its null backend: no sound server, device or desktop.
"${CC:-cc}" -O1 -ffunction-sections -fdata-sections -DMA_ENABLE_ONLY_SPECIFIC_BACKENDS \
    -DMA_ENABLE_NULL -I"$raylib_source" -c "$raylib_source/raudio.c" -o "$work/null-audio.o"

build() {
    name=$1
    entry=$2
    shift 2
    generated=$work/$name
    mkdir -p "$generated"
    "$bin/zi2c" --no-main --root "$root/src" \
        --module-path "$root/build/packages/kryon/src/ui" \
        --module-path "$root/build/packages/ziran/std" \
        --module-path "$root/build/packages/daochi-client" \
        $(sh "$root/scripts/package-paths.sh" "$root/build/packages") \
        --module-path "$root/build/packages/kryon/src/backend" \
        -o "$generated" "$root/$entry"
    sources=""
    for file in voice_audio media_audio media_audio_host media_audio_raylib media_audio_opus \
        audio_sink_raylib session audio_policy ogg_length byte_text_linux text_buffers \
        package_files format c_string math "$@"; do
        sources="$sources $generated/$file.c"
    done
    # The audio package's modules carry its package prefix.
    for file in "$generated"/p*_opus.c "$generated"/p*_ogg.c "$generated"/p*_types.c; do
        sources="$sources $file"
    done
    # The test stands in for these modules, so their headers declare the
    # functions it replaces instead of defining them inline.
    # shellcheck disable=SC2086
    "${CC:-cc}" -std=c11 -O1 -D_GNU_SOURCE -DZIRAN_BOUNDS_CHECK \
        -DZIRAN_PRACTICE_DOWNLOADS_H_SOURCE -DZIRAN_AUDIO_H_SOURCE -DZIRAN_ASSETS_H_SOURCE \
        $( [ "$name" = lumi ] && echo -DVOICE_AUDIO_LUMI ) \
        -ffunction-sections -fdata-sections -Wl,--gc-sections \
        -I"$root/build/packages/ziran/include" -I"$generated" \
        "$root/tests/voice_audio_play_test.c" $sources "$work/null-audio.o" \
        "$raylib_a" "$root/build/ziran-toolchain/libziran.a" "$libopus_a" \
        -lSDL2 -lm -lpthread -ldl -o "$generated/test"
}

build practice src/practices/practice_narration.zi practices/practice_narration
build lumi src/app/lumi_guide.zi app/lumi_guide

# Short real lines, so the whole run stays within a few seconds.
for run in "practice taichi/voice/en tai_chi_text_73f9fa69" "lumi guide/voice/en practice_guide_start"; do
    set -- $run
    [ -f "$practices/$2/$3.ogg" ] || { echo "voice_audio_play_test: missing $practices/$2/$3.ogg" >&2; exit 1; }
    env -i PATH=/usr/bin:/bin HOME="$work" YUE_DESKTOP_RECOVERY=0 \
        timeout --kill-after=2s 30s "$work/$1/test" "$practices" "$3"
done
echo "Real Ogg Opus narration and Lumi guide playback passed"
