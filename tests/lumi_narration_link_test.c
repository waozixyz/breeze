#include "app/lumi_guide.h"
#include "assets.h"

#include <assert.h>
#include <string.h>

static int reads;
static int plays;
static int stops;
static int unloads;
static bool available = true;
static float volume;

String LocaleActiveCode(void) { return StringView("en", 2); }
double GetTime(void) { return 1.0; }
void app_audio_ensure_ready(InnerBreeze *app) { app->audio_ready = 1; }

AssetView AssetReadBytes(Slice path)
{
    reads++;
    assert(path.length > 0);
    return (AssetView){.data = StringView("clip", 4), .found = available};
}

MusicHandle audio_runtime_audio_load_music_memory(String extension, uint8_t *data,
    int32_t size, bool looping)
{
    assert(extension.length == 4 && memcmp(extension.data, ".ogg", 4) == 0);
    assert(size == 4 && memcmp(data, "clip", 4) == 0 && !looping);
    return (MusicHandle){.id = 1};
}

bool audio_runtime_audio_music_valid(MusicHandle handle) { return handle.id != 0; }
void audio_runtime_audio_set_music_volume(MusicHandle handle, float value)
{
    assert(handle.id == 1);
    volume = value;
}
void audio_runtime_audio_play_music(MusicHandle handle) { assert(handle.id == 1); plays++; }
void audio_runtime_audio_stop_music(MusicHandle handle) { assert(handle.id == 1); stops++; }
void audio_runtime_audio_unload_music(MusicHandle handle) { assert(handle.id == 1); unloads++; }

int main(void)
{
    InnerBreeze app = {0};
    String key = StringView("practice_guide_start", 20);
    app.sound_volume = 60;
    lumi_guide_LumiGuideSpeak(&app, key);
    assert(reads == 0 && plays == 0);

    app.voice_narration_enabled = 1;
    app.sound_volume = 0;
    lumi_guide_LumiGuideSpeak(&app, key);
    assert(reads == 0 && plays == 0);

    app.sound_volume = 60;
    lumi_guide_LumiGuideSpeak(&app, key);
    assert(reads == 1 && plays == 1 && volume > 0.599f && volume < 0.601f);
    lumi_guide.shown = true;
    lumi_guide.drawn_frame = app.breathing.frame;
    app.voice_narration_enabled = 0;
    LumiGuideFrameEnd(&app);
    assert(stops == 1 && unloads == 1 && !lumi_guide.voice_playing);
    assert(lumi_guide.shown); /* Muting voice keeps the written guide. */
    lumi_guide_LumiGuideSpeak(&app, key);
    assert(plays == 1);

    app.voice_narration_enabled = 1;
    available = false;
    lumi_guide_LumiGuideSpeak(&app, key);
    assert(plays == 1);
    available = true;
    lumi_guide_LumiGuideSpeak(&app, key);
    assert(plays == 2);
    LumiGuideStop();
    assert(stops == 2 && unloads == 2);
    return 0;
}
