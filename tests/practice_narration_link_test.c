#include "practices/practice_narration.h"
#include "assets.h"

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint8_t *clip;
static size_t clip_size;
static uint8_t *playing_bytes;
static String language;
static int plays, stops, unloads, pauses, resumes, updates;
static float volume;

String LocaleActiveCode(void) { return language; }
void app_audio_ensure_ready(InnerBreeze *app) { app->audio_ready = 1; }

AssetView AssetRead(String path)
{
    const char *prefix = "assets/practices/taichi/voice/en/";
    bool found = path.length > strlen(prefix) &&
        memcmp(path.data, prefix, strlen(prefix)) == 0;
    return (AssetView){.data = StringView((char *)clip, clip_size), .found = found};
}

MusicHandle audio_runtime_audio_load_music_memory(String extension, uint8_t *data,
    int32_t size, bool looping)
{
    assert(StringEqual(extension, StringLiteral(".ogg")));
    assert((size_t)size == clip_size && !looping);
    assert(data != clip && memcmp(data, clip, clip_size) == 0);
    playing_bytes = data;
    return (MusicHandle){.id = 1};
}

bool audio_runtime_audio_music_valid(MusicHandle value) { return value.id == 1; }
void audio_runtime_audio_play_music(MusicHandle value) { assert(value.id == 1); plays++; }
void audio_runtime_audio_stop_music(MusicHandle value) { assert(value.id == 1); stops++; }
void audio_runtime_audio_unload_music(MusicHandle value) { assert(value.id == 1); unloads++; }
void audio_runtime_audio_pause_music(MusicHandle value) { assert(value.id == 1); pauses++; }
void audio_runtime_audio_resume_music(MusicHandle value) { assert(value.id == 1); resumes++; }
void audio_runtime_audio_update_music(MusicHandle value) { assert(value.id == 1); updates++; }
void audio_runtime_audio_set_music_volume(MusicHandle value, float amount)
{
    assert(value.id == 1);
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

    InnerBreeze app = {0};
    String practice = StringLiteral("taichi"), cue = StringLiteral("cue");
    language = StringLiteral("en");
    app.sound_volume = 60;
    practice_narration_PracticeNarrationUpdate(&app, practice, cue);
    assert(plays == 0);
    app.voice_narration_enabled = 1;
    practice_narration_PracticeNarrationUpdate(&app, practice, cue);
    assert(plays == 1 && updates == 1 && volume > .599f && volume < .601f);
    assert(practice_narration_PracticeTaiChiReadingSeconds(cue) > .2);
    uint8_t first = clip[0];
    clip[0] ^= 1;
    assert(playing_bytes[0] == first); /* The decoder owns a copy of borrowed assets. */
    clip[0] = first;
    practice_narration_PracticeNarrationUpdate(&app, practice, cue);
    assert(plays == 1 && updates == 2);

    app.session_paused = 1;
    practice_narration_PracticeNarrationUpdate(&app, practice, cue);
    assert(pauses == 1 && updates == 2);
    app.session_paused = 0;
    practice_narration_PracticeNarrationUpdate(&app, practice, cue);
    assert(resumes == 1 && updates == 3);
    practice_narration_PracticeNarrationUpdate(&app, practice, StringLiteral("next"));
    assert(plays == 2 && stops == 1 && unloads == 1);

    language = StringLiteral("es");
    practice_narration_PracticeNarrationUpdate(&app, practice, cue);
    assert(plays == 2 && stops == 2 && unloads == 2); /* No other-language fallback. */
    language = StringLiteral("en");
    practice_narration_PracticeNarrationUpdate(&app, practice, cue);
    assert(plays == 3);
    app.voice_narration_enabled = 0;
    practice_narration_PracticeNarrationUpdate(&app, practice, cue);
    assert(stops == 3 && unloads == 3);
    app.voice_narration_enabled = 1;
    app.sound_volume = 0;
    practice_narration_PracticeNarrationUpdate(&app, practice, cue);
    assert(plays == 3);
    free(clip);
    puts("Practice narration: language, owned audio, volume, pause/resume and mute passed");
    return 0;
}
