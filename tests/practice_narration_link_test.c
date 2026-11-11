#include "practice_narration.h"
#include "zir_string.h"
#include "assets.h"

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint8_t *clip;
static size_t clip_size;
static String language;
static String voice_choice;
static const char *prefix = "assets/practices/taichi/voice/en/";
static int plays, stops, pauses, resumes, updates;
static float volume;
static bool clip_available = true;
static char played_path[256];

/* The downloaded language the practice speaks; empty when none is. */
String practice_downloads_PracticeNarrationLanguage(int32_t content, String voice)
{
    (void)content;
    (void)voice;
    return language;
}
int32_t practice_downloads_PracticeContentIndex(String name) { return (int32_t)name.length; }
String practice_downloads_PracticeVoiceChoice(void) { return voice_choice; }
void app_audio_ensure_ready(InnerBreeze *app) { app->audio_ready = 1; }

AssetView AssetRead(String path)
{
    bool found = clip_available && path.length > strlen(prefix) &&
        memcmp(path.data, prefix, strlen(prefix)) == 0;
    return (AssetView){.data = StringView((char *)clip, clip_size), .found = found};
}

static int active;

bool voice_audio_VoiceAudioStart(InnerBreeze *app, int32_t voice, String path, float gain)
{
    assert(app && voice == VoiceAudioPractice && gain >= 0.0f && gain <= 1.0f);
    /* Kryon reads and copies the packed clip itself, by its packed path. */
    assert(path.length > strlen(prefix) + 4 && memcmp(path.data, prefix, strlen(prefix)) == 0);
    assert(memcmp(path.data + path.length - 4, ".ogg", 4) == 0);
    assert(path.length < sizeof played_path);
    memcpy(played_path, path.data, path.length);
    played_path[path.length] = '\0';
    volume = gain;
    plays++;
    return true;
}
void voice_audio_VoiceAudioStop(int32_t voice) { assert(voice == VoiceAudioPractice); stops++; }
void voice_audio_VoiceAudioPause(int32_t voice) { assert(voice == VoiceAudioPractice); pauses++; }
void voice_audio_VoiceAudioResume(int32_t voice) { assert(voice == VoiceAudioPractice); resumes++; }
bool voice_audio_VoiceAudioActive(int32_t voice) { assert(voice == VoiceAudioPractice); updates++; return true; }
void voice_audio_VoiceAudioGain(int32_t voice, float amount)
{
    assert(voice == VoiceAudioPractice);
    volume = amount;
}

int main(int argc, char **argv)
{
    assert(argc == 2);
    FILE *file = fopen(argv[1], "rb");
    assert(file && fseek(file, 0, SEEK_END) == 0);
    clip_size = (size_t)ftell(file);
    assert(clip_size > 0 && fseek(file, 0, SEEK_SET) == 0);
    clip = malloc(clip_size);
    assert(clip && fread(clip, 1, clip_size, file) == clip_size);
    fclose(file);

    static InnerBreeze app = {0};
    String practice = StringLiteral("taichi"), cue = StringLiteral("cue");
    language = StringLiteral("en");
    app.sound_volume = 60;
    practice_narration_PracticeNarrationUpdate(&app, practice, cue);
    assert(plays == 0);
    app.voice_narration_enabled = 1;
    practice_narration_PracticeNarrationUpdate(&app, practice, cue);
    assert(plays == 1 && updates == 1 && volume > .599f && volume < .601f);
    assert(practice_narration_PracticeTaiChiReadingSeconds(cue) > .2);
    practice_narration_PracticeNarrationUpdate(&app, practice, cue);
    assert(plays == 1 && updates == 2);

    app.session_paused = 1;
    practice_narration_PracticeNarrationUpdate(&app, practice, cue);
    assert(pauses == 1 && updates == 2);
    app.session_paused = 0;
    practice_narration_PracticeNarrationUpdate(&app, practice, cue);
    assert(resumes == 1 && updates == 3);
    practice_narration_PracticeNarrationUpdate(&app, practice, StringLiteral("next"));
    assert(plays == 2 && stops == 1);

    language = StringLiteral("es");
    practice_narration_PracticeNarrationUpdate(&app, practice, cue);
    assert(plays == 2 && stops == 2); /* Only the spoken language's clip plays. */
    language = StringLiteral("");
    practice_narration_PracticeNarrationUpdate(&app, practice, cue);
    assert(plays == 2); /* Without downloaded narration the practice is silent. */
    assert(practice_narration_PracticeTaiChiReadingSeconds(cue) == 0.0);
    language = StringLiteral("en");
    practice_narration_PracticeNarrationUpdate(&app, practice, cue);
    assert(plays == 3);
    app.voice_narration_enabled = 0;
    practice_narration_PracticeNarrationUpdate(&app, practice, cue);
    assert(stops == 3);
    app.voice_narration_enabled = 1;
    app.sound_volume = 0;
    practice_narration_PracticeNarrationUpdate(&app, practice, cue);
    assert(plays == 3);

    /* The male voice reads its own folder, and the cue starts again in it. */
    app.sound_volume = 60;
    practice_narration_PracticeNarrationUpdate(&app, practice, cue);
    assert(plays == 4);
    voice_choice = StringLiteral("male");
    prefix = "assets/practices/taichi/voice-male/en/";
    practice_narration_PracticeNarrationUpdate(&app, practice, cue);
    assert(plays == 5);
    prefix = "assets/practices/sunsalutation/voice-male/en/";
    assert(practice_narration_PracticeNarrationSeconds(StringLiteral("sunsalutation"), cue) > .2);
    assert(practice_narration_PracticeTaiChiReadingSeconds(cue) == 0.0);
    /* A voice download can arrive after this cue started. Retry that same
       cue when its asset becomes available, without waiting for the next. */
    practice_narration_PracticeNarrationStop();
    voice_choice = StringLiteral("");
    prefix = "assets/practices/astral_projection/voice/en/";
    practice = StringLiteral("astral_projection");
    clip_available = false;
    int before = plays;
    practice_narration_PracticeNarrationUpdate(&app, practice, cue);
    assert(plays == before);
    clip_available = true;
    practice_narration_PracticeNarrationUpdate(&app, practice, cue);
    assert(plays == before + 1);
    practice_narration_PracticeNarrationUpdate(&app, practice, cue);
    assert(plays == before + 1);
    /* Each selected course resolves its own key through the established
       packed narration path. The fixture clip verifies routing only. */
    const char *selected_cues[] = {
        "astral_text_foundation_01", "astral_text_current_01",
        "astral_text_elevator_01", "astral_text_spin_01",
        "astral_text_rope_01", "astral_text_roll_out_01"
    };
    for (size_t i = 0; i < sizeof selected_cues / sizeof *selected_cues; i++) {
        char expected[256];
        snprintf(expected, sizeof expected, "%s%s.ogg", prefix, selected_cues[i]);
        practice_narration_PracticeNarrationUpdate(&app, practice,
            StringView(selected_cues[i], strlen(selected_cues[i])));
        assert(strcmp(played_path, expected) == 0);
    }
    language = StringLiteral("de");
    prefix = "assets/practices/astral_projection/voice/de/";
    practice_narration_PracticeNarrationUpdate(&app, practice, StringLiteral("astral_text_rope_01"));
    assert(strcmp(played_path, "assets/practices/astral_projection/voice/de/astral_text_rope_01.ogg") == 0);
    free(clip);
    puts("Practice narration: language, voice, packed clip path, volume, pause/resume and mute passed");
    return 0;
}
