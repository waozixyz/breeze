#!/bin/sh
# Real Ogg Opus narration and Lumi guide playback to completion through
# Ziran's mixer and the audio package's libopus (tests/voice_audio_play_behavior.zi).
#
#   sh tests/voice_audio_play_test.sh ZIRAN_BIN_DIR LIBOPUS_A [PRACTICES] [astral [LOCALE]]
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bin=$1
libopus_a=$2
practices=${3:-"$root/build/packages/practices"}
suite=${4:-standard}
locale=${5:-all}
case "$suite" in
    standard|astral) ;;
    *) echo "Unknown playback suite: $suite" >&2; exit 1 ;;
esac
work=$root/build/voice-audio-play-test
rm -rf "$work/c"
mkdir -p "$work/c"
"$bin/ziran" build --project --offline --target=c --no-main \
    --root "$root" --module-path "$root/tests" \
    -o "$work/c" "$root/tests/voice_audio_play_behavior.zi"
# shellcheck disable=SC2046
"${CC:-cc}" -std=c11 -O1 -DZIRAN_BOUNDS_CHECK -ffunction-sections -fdata-sections \
    -Wl,--gc-sections -w -I"$root/build/packages/ziran/include" \
    $(find "$work/c" -type d -printf ' -iquote %p') $(find "$work/c" -type f -name '*.c') \
    "$libopus_a" -lm -lpthread -o "$work/test"

clips=""
if [ "$suite" = astral ]; then
    # The six exercises' first cues, in every supported locale or one.
    locales=$(cut -d '|' -f 1 "$root/locales/index.txt")
    if [ "$locale" != all ]; then
        printf '%s\n' "$locales" | rg -Fx -- "$locale" >/dev/null || {
            echo "Unsupported astral narration locale: $locale" >&2; exit 1;
        }
        locales=$locale
    fi
    for code in $locales; do
        for exercise in foundation current elevator spin rope roll_out; do
            clips="$clips $practices/astral_projection/voice/$code/astral_text_${exercise}_01.ogg"
        done
    done
else
    # The accepted Russian and Czech exports with measured decoder headroom,
    # observed as shipped, never normalized or replaced by the test.
    for clip in sunsalutation/voice/en/sun_salutation_voice_intro_1 \
        sunsalutation/voice-male/en/sun_salutation_voice_mountain_start \
        taichi/voice/en/tai_chi_text_73f9fa69 guide/voice/en/practice_guide_start \
        guide/voice/ru/diary_guide_write guide/voice/ru/habits_guide_coins \
        guide/voice/ru/habits_guide_meditation_edit guide/voice/ru/habits_guide_meditation_views \
        guide/voice/ru/settings_guide_sections guide/voice/cs/habits_guide_overview_grid \
        guide/voice/cs/habits_guide_meditation_session_data; do
        clips="$clips $practices/$clip.ogg"
    done
fi
for clip in $clips; do
    [ -f "$clip" ] || { echo "voice_audio_play_test: missing $clip" >&2; exit 1; }
done
# shellcheck disable=SC2086
env -u DISPLAY -u WAYLAND_DISPLAY -u XAUTHORITY timeout --kill-after=2s 300s "$work/test" $clips
echo "Real Ogg Opus narration and Lumi guide playback ($suite) passed"
