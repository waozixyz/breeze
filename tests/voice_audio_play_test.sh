#!/bin/sh
# Real Ogg Opus narration and Lumi guide playback to completion through
# voice_audio, Kryon's MediaAudio provider and the audio package's libopus on
# a private null audio device (tests/voice_audio_play_test.c).
#
#   sh tests/voice_audio_play_test.sh ZIRAN_BIN_DIR RAYLIB_SOURCE RAYLIB_A LIBOPUS_A [PRACTICES] [astral [LOCALE]]
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=$1
raylib_source=$2
raylib_a=$3
libopus_a=$4
practices=${5:-"$root/build/packages/practices"}
suite=${6:-standard}
locale=${7:-all}
case "$suite" in
    standard|astral) ;;
    *) echo "Unknown playback suite: $suite" >&2; exit 1 ;;
esac
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
    (cd "$root" && "$bin/ziran" build --target=c --project --offline --no-main --prune-stale --root "$root/src" -o "$generated" "$root/$entry")
    sources=""
    for file in voice_audio media_audio media_audio_host media_audio_raylib media_audio_opus \
        audio_sink_raylib session audio_policy ogg_length byte_text_linux text_buffers \
        package_files format c_string math "$@"; do
        if [ -f "$generated/$file.c" ]; then
            sources="$sources $generated/$file.c"
        elif [ -f "$generated/std_$file.c" ]; then
            sources="$sources $generated/std_$file.c"
        else
            for source in "$generated"/p*_"$file".c; do
                [ -f "$source" ] || { echo "Missing generated module: $file" >&2; exit 1; }
                sources="$sources $source"
            done
        fi
    done
    # The audio package's modules carry its package prefix.
    for file in "$generated"/p*_opus.c "$generated"/p*_ogg.c "$generated"/p*_types.c; do
        case " $sources " in
            *" $file "*) ;;
            *) sources="$sources $file" ;;
        esac
    done
    set -- "$generated"/p*_media_audio_opus.h
    [ "$#" = 1 ] && [ -f "$1" ] || { echo "Ambiguous generated media audio header" >&2; exit 1; }
    media_header=$1
    # The test stands in for these modules, so their headers declare the
    # functions it replaces instead of defining them inline.
    # shellcheck disable=SC2086
    "${CC:-cc}" -std=c11 -O1 -D_GNU_SOURCE -DZIRAN_BOUNDS_CHECK \
        -DZIRAN_PRACTICE_DOWNLOADS_H_SOURCE -DZIRAN_AUDIO_H_SOURCE -DZIRAN_ASSETS_H_SOURCE \
        $( [ "$name" = lumi ] && echo -DVOICE_AUDIO_LUMI ) \
        "-DMEDIA_AUDIO_OPUS_HEADER=\"$media_header\"" \
        -ffunction-sections -fdata-sections -Wl,--gc-sections -Wl,--wrap=UpdateAudioStream \
        -I"$root/build/packages/ziran/include" -I"$generated" \
        "$root/tests/voice_audio_play_test.c" $sources "$work/null-audio.o" \
        "$raylib_a" "$bin/../libziran.a" "$libopus_a" \
        -lSDL2 -lm -lpthread -ldl -o "$generated/test"
}

build practice src/practices/practice_narration.zi practice_narration
if [ "$suite" = astral ]; then
    # Real first cues exercise the six selected sessions through the same
    # native playback, pause/resume, PCM conversion and mixer as Tai Chi.
    # Preflight the requested set before spending time on playback.
    locales=$(cut -d '|' -f 1 "$root/locales/index.txt")
    if [ "$locale" != all ]; then
        printf '%s\n' "$locales" | rg -Fx -- "$locale" >/dev/null || {
            echo "Unsupported astral narration locale: $locale" >&2; exit 1;
        }
        locales=$locale
    fi
    for code in $locales; do
        for exercise in foundation current elevator spin rope roll_out; do
            key=astral_text_${exercise}_01
            file=$practices/astral_projection/voice/$code/$key.ogg
            [ -f "$file" ] || { echo "Missing astral narration: $file" >&2; exit 1; }
        done
    done
    for code in $locales; do
        for exercise in foundation current elevator spin rope roll_out; do
            key=astral_text_${exercise}_01
            env -i PATH=/usr/bin:/bin HOME="$work" YUE_DESKTOP_RECOVERY=0 \
                timeout --kill-after=2s 90s "$work/practice/test" "$practices" \
                    "$key" "$code" astral_projection
        done
    done
    echo "All six astral exercises completed native narration playback with pause/resume"
    exit 0
fi
build lumi src/app/lumi_guide.zi lumi_guide

# Include the accepted Russian and Czech exports with measured decoder headroom.
# These original files are observed, never normalized or replaced by the test.
for run in \
    "practice taichi/voice/en tai_chi_text_73f9fa69 en" \
    "lumi guide/voice/en practice_guide_start en" \
    "lumi guide/voice/ru diary_guide_write ru" \
    "lumi guide/voice/ru habits_guide_coins ru" \
    "lumi guide/voice/ru habits_guide_meditation_edit ru" \
    "lumi guide/voice/ru habits_guide_meditation_views ru" \
    "lumi guide/voice/ru settings_guide_sections ru" \
    "lumi guide/voice/cs habits_guide_overview_grid cs" \
    "lumi guide/voice/cs habits_guide_meditation_session_data cs" ; do
    set -- $run
    [ -f "$practices/$2/$3.ogg" ] || { echo "voice_audio_play_test: missing $practices/$2/$3.ogg" >&2; exit 1; }
    env -i PATH=/usr/bin:/bin HOME="$work" YUE_DESKTOP_RECOVERY=0 \
        timeout --kill-after=2s 30s "$work/$1/test" "$practices" "$3" "$4"
done
echo "Real Ogg Opus narration and Lumi guide playback passed"
