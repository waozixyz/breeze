#include "app/lumi_guide.h"
#include "zir_string.h"
#include "assets.h"

#include <assert.h>
#include <string.h>

static int reads;
static int plays;
static int stops;
static bool available = true;
static float volume;

String practice_downloads_PracticeNarrationLanguage(int32_t content, String voice)
{
    (void)content;
    (void)voice;
    return StringView("en", 2);
}
double GetTime(void) { return 1.0; }
void app_audio_ensure_ready(InnerBreeze *app) { app->audio_ready = 1; }

AssetView AssetRead(String path)
{
    reads++;
    assert(path.length > 0);
    return (AssetView){.data = StringView("clip", 4), .found = available};
}

bool voice_audio_VoiceAudioStart(InnerBreeze *app, int32_t voice, String path, float gain)
{
    static const char want[] = "assets/practices/guide/voice/en/practice_guide_start.ogg";
    assert(app && voice == VoiceAudioGuide);
    assert(path.length == strlen(want) && memcmp(path.data, want, strlen(want)) == 0);
    volume = gain;
    plays++;
    return true;
}
void voice_audio_VoiceAudioStop(int32_t voice) { assert(voice == VoiceAudioGuide); stops++; }
bool voice_audio_VoiceAudioActive(int32_t voice) { assert(voice == VoiceAudioGuide); return true; }

int main(void)
{
    InnerBreeze app = {0};
    String key = StringView("practice_guide_start", 20);
    app.sound_volume = 60;
    lumi_guide_LumiGuideSpeak(&app, key);
    assert(reads == 0 && plays == 0);

    app.guide_narration_enabled = 1;
    app.sound_volume = 0;
    lumi_guide_LumiGuideSpeak(&app, key);
    assert(reads == 0 && plays == 0);

    app.sound_volume = 60;
    lumi_guide_LumiGuideSpeak(&app, key);
    assert(reads == 1 && plays == 1 && volume > 0.599f && volume < 0.601f);
    lumi_guide.shown = true;
    lumi_guide.drawn_frame = app.breathing.frame;
    app.guide_narration_muted = 1;
    LumiGuideFrameEnd(&app);
    assert(stops == 1 && !lumi_guide.voice_playing);
    assert(lumi_guide.shown); /* Muting voice keeps the written guide. */
    lumi_guide_LumiGuideSpeak(&app, key);
    assert(plays == 1);

    app.guide_narration_muted = 0;
    available = false;
    lumi_guide_LumiGuideSpeak(&app, key);
    assert(plays == 1);
    available = true;
    lumi_guide_LumiGuideSpeak(&app, key);
    assert(plays == 2);
    LumiGuideStop();
    assert(stops == 2);
    return 0;
}
