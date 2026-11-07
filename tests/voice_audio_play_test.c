/* Practice narration and Lumi's guide play a real Ogg Opus clip to the end
   through Breeze's voice_audio, Kryon's MediaAudio provider and libopus, on a
   private null audio device. Only the downloaded-pack lookup and the packed
   asset read stand in for the app: the asset read returns the clip's file. */
#include "zir_string.h"
#include "assets.h"
#include "voice_audio.h"
#ifdef VOICE_AUDIO_LUMI
#include "app/lumi_guide.h"
#else
#include "practices/practice_narration.h"
#endif

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

void InitAudioDevice(void);
bool IsAudioDeviceReady(void);

static const char *practices;
static uint8_t clip[1 << 20];

static double now_ms(void)
{
    struct timespec at;
    clock_gettime(CLOCK_MONOTONIC, &at);
    return at.tv_sec * 1000.0 + at.tv_nsec / 1e6;
}

static void nap(int ms)
{
    struct timespec wait = {0, ms * 1000000L};
    nanosleep(&wait, NULL);
}

String practice_downloads_PracticeNarrationLanguage(int32_t content, String voice)
{
    (void)content;
    (void)voice;
    return StringLiteral("en");
}
int32_t practice_downloads_PracticeContentIndex(String name) { return (int32_t)name.length; }
String practice_downloads_PracticeVoiceChoice(void) { return StringLiteral(""); }
void app_audio_ensure_ready(InnerBreeze *app)
{
    if (!IsAudioDeviceReady())
        InitAudioDevice();
    app->audio_ready = IsAudioDeviceReady() ? 1 : 0;
}
void save_settings(InnerBreeze *app) { (void)app; }
int32_t sync_web_storage_critical(void) { return 0; }

/* The packed asset read: assets/practices/<rest> is <practices>/<rest>. */
AssetView AssetRead(String path)
{
    const char *prefix = "assets/practices/";
    size_t length = strlen(prefix);
    if (path.length <= length || memcmp(path.data, prefix, length) != 0)
        return (AssetView){0};
    char file_name[1024];
    snprintf(file_name, sizeof file_name, "%s/%.*s", practices,
             (int)(path.length - length), path.data + length);
    FILE *file = fopen(file_name, "rb");
    if (!file)
        return (AssetView){0};
    size_t size = fread(clip, 1, sizeof clip, file);
    fclose(file);
    /* The recording must be Ogg Opus: OpusHead on the first page. */
    assert(size > 36 && memcmp(clip, "OggS", 4) == 0 && memcmp(clip + 28, "OpusHead", 8) == 0);
    return (AssetView){.data = StringView((char *)clip, size), .found = true};
}

static InnerBreeze *app_open(void)
{
    static InnerBreeze app;
    memset(&app, 0, sizeof app);
    app.ui.session = SessionOpen();
    app.sound_volume = 60;
    app.voice_narration_enabled = 1;
    app.guide_narration_enabled = 1;
    return &app;
}

int main(int argc, char **argv)
{
    assert(argc == 3);
    practices = argv[1];
    String key = StringView(argv[2], strlen(argv[2]));
    InnerBreeze *app = app_open();
#ifdef VOICE_AUDIO_LUMI
    double expected = OggClipMilliseconds(lumi_guide_LumiGuideClip(key).data);
    assert(expected > 200.0);
    double started = now_ms();
    lumi_guide_LumiGuideSpeak(app, key);
    assert(app->audio_ready && lumi_guide.voice_playing);
    while (lumi_guide.voice_playing) {
        assert(now_ms() - started < expected + 3000.0);
        lumi_guide_LumiGuideVoiceUpdate();
        nap(5);
    }
    double elapsed = now_ms() - started;
    /* She lets the line go once it has been said, never before. */
    assert(elapsed >= expected - 60.0 && elapsed <= expected + 400.0);
    printf("Lumi guide: %s (Ogg Opus, %.0f ms) played to the end in %.0f ms\n", argv[2], expected, elapsed);
#else
    String practice = StringLiteral("taichi");
    double expected = (practice_narration_PracticeNarrationSeconds(practice, key) - 0.2) * 1000.0;
    assert(expected > 200.0);
    double started = now_ms();
    practice_narration_PracticeNarrationUpdate(app, practice, key);
    assert(app->audio_ready && voice_audio_VoiceAudioActive(VoiceAudioPractice));
    /* A pause holds the line where it is; the clip then finishes that much later. */
    while (now_ms() - started < expected / 3) {
        practice_narration_PracticeNarrationUpdate(app, practice, key);
        nap(5);
    }
    app->session_paused = 1;
    practice_narration_PracticeNarrationUpdate(app, practice, key);
    nap(300);
    assert(voice_audio_VoiceAudioActive(VoiceAudioPractice));
    app->session_paused = 0;
    while (voice_audio_VoiceAudioActive(VoiceAudioPractice)) {
        assert(now_ms() - started < expected + 3300.0);
        practice_narration_PracticeNarrationUpdate(app, practice, key);
        nap(5);
    }
    double elapsed = now_ms() - started;
    assert(elapsed >= expected + 300.0 - 60.0 && elapsed <= expected + 300.0 + 300.0);
    practice_narration_PracticeNarrationStop();
    printf("Practice narration: %s (Ogg Opus, %.0f ms) played to the end in %.0f ms with a 300 ms pause\n",
           argv[2], expected, elapsed);
#endif
    return 0;
}
