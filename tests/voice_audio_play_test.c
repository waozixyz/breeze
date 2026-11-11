/* Practice narration and Lumi's guide play a real Ogg Opus clip to the end
   through Breeze's voice_audio, Kryon's MediaAudio provider and libopus, on a
   private null audio device. Only the downloaded-pack lookup and the packed
   asset read stand in for the app: the asset read returns the clip's file. */
#include "zir_string.h"
#include "assets.h"
#include "voice_audio.h"
#include MEDIA_AUDIO_OPUS_HEADER
#ifdef VOICE_AUDIO_LUMI
#include "lumi_guide.h"
#else
#include "practice_narration.h"
#endif

#include <assert.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

void InitAudioDevice(void);
bool IsAudioDeviceReady(void);

/* Observe the real decoder-to-PCM16 boundary without changing its samples.
   The linker forwards this wrapper to Raylib's actual stream implementation. */
void CloseAudioDevice(void);
void AttachAudioMixedProcessor(void (*processor)(void *, unsigned int));
void __real_UpdateAudioStream(AudioStream stream, const void *data, int frames);

static const char *fixture_language = "en";
static char expected_asset[256];
static unsigned long long converted_samples;
static unsigned long long decoded_crossings;
static double decoded_peak;
static int minimum_pcm = 32767;
static int maximum_pcm = -32768;
static pthread_mutex_t output_lock = PTHREAD_MUTEX_INITIALIZER;
static unsigned long long mixed_samples;
static unsigned long long mixed_nonzero;
static double mixed_peak;

static void inspect_mixed_output(void *data, unsigned int frames)
{
    const float *samples = data;
    double peak = 0.0;
    unsigned long long nonzero = 0;
    /* Raylib's native device mixer has two float output channels. */
    for (unsigned int index = 0; index < frames * 2; index++) {
        double value = samples[index];
        assert(__builtin_isfinite(value));
        double amplitude = __builtin_fabs(value);
        assert(amplitude <= 1.000001);
        if (amplitude > peak)
            peak = amplitude;
        if (amplitude > 0.00000001)
            nonzero++;
    }
    pthread_mutex_lock(&output_lock);
    mixed_samples += (unsigned long long)frames * 2;
    mixed_nonzero += nonzero;
    if (peak > mixed_peak)
        mixed_peak = peak;
    pthread_mutex_unlock(&output_lock);
}

void __wrap_UpdateAudioStream(AudioStream stream, const void *data, int frames)
{
    OpusAsset *asset = NULL;
    size_t voices = sizeof voice_audio_owner.voices / sizeof voice_audio_owner.voices[0];
    for (size_t index = 0; index < voices; index++) {
        AssetAudioResource *resource = voice_audio_owner.voices[index].resource;
        if (resource && resource->opus) {
            OpusAsset *candidate = resource->opus;
            if (candidate->stream.buffer == stream.buffer)
                asset = candidate;
        }
    }
    assert(asset && data == asset->native);
    assert(stream.rate == 48000 && stream.size == 16 && stream.channels == 1);
    assert(frames > 0 && frames * stream.channels <= 4096);
    const int16_t *converted = data;
    for (int index = 0; index < frames * (int)stream.channels; index++) {
        double decoded = asset->pcm[index];
        assert(__builtin_isfinite(decoded));
        double amplitude = __builtin_fabs(decoded);
        if (amplitude > decoded_peak)
            decoded_peak = amplitude;
        if (amplitude >= 1.0)
            decoded_crossings++;
        /* Over-range values saturate in their original direction. Values
           within the unit range retain their amplitude within one PCM16 LSB. */
        if (decoded >= 1.0)
            assert(converted[index] == 32767);
        else if (decoded <= -1.0)
            assert(converted[index] == -32768);
        else
            assert(__builtin_fabs(converted[index] / 32768.0 - decoded) <= 1.0 / 32768.0);
        if (converted[index] < minimum_pcm)
            minimum_pcm = converted[index];
        if (converted[index] > maximum_pcm)
            maximum_pcm = converted[index];
        converted_samples++;
    }
    __real_UpdateAudioStream(stream, data, frames);
}

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
    return StringView(fixture_language, strlen(fixture_language));
}
int32_t practice_downloads_PracticeContentIndex(String name) { return (int32_t)name.length; }
String practice_downloads_PracticeVoiceChoice(void) { return StringLiteral(""); }
void app_audio_ensure_ready(InnerBreeze *app)
{
    if (!IsAudioDeviceReady()) {
        InitAudioDevice();
        AttachAudioMixedProcessor(inspect_mixed_output);
    }
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
    assert(path.length == strlen(expected_asset) && memcmp(path.data, expected_asset, path.length) == 0);
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
    app.sound_volume = 100;
    app.voice_narration_enabled = 1;
    app.guide_narration_enabled = 1;
    return &app;
}

int main(int argc, char **argv)
{
    assert(argc >= 3 && argc <= 5);
    practices = argv[1];
    if (argc >= 4)
        fixture_language = argv[3];
    assert(strlen(fixture_language) == 2);
#ifdef VOICE_AUDIO_LUMI
    const char *directory = "guide";
    assert(argc <= 4);
#else
    const char *directory = argc == 5 ? argv[4] : "taichi";
    assert(strcmp(directory, "taichi") == 0 || strcmp(directory, "astral_projection") == 0);
#endif
    snprintf(expected_asset, sizeof expected_asset, "assets/practices/%s/voice/%s/%s.ogg",
             directory, fixture_language, argv[2]);
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
    String practice = StringView(directory, strlen(directory));
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
    voice_audio_VoiceAudioStop(VoiceAudioPractice);
    voice_audio_VoiceAudioStop(VoiceAudioGuide);
    CloseAudioDevice();
    assert(converted_samples > 0);
    pthread_mutex_lock(&output_lock);
    assert(mixed_samples > 0 && mixed_nonzero > 0 && mixed_peak > 0.0);
    printf("Native output: %s/%s, decoded peak %.9f, %llu unit crossings, "
           "%llu converted samples, PCM16 [%d,%d], mixed peak %.9f, "
           "%llu observed mixed samples, no integer wrap\n",
           fixture_language, argv[2], decoded_peak, decoded_crossings, converted_samples,
           minimum_pcm, maximum_pcm, mixed_peak, mixed_samples);
    pthread_mutex_unlock(&output_lock);
    return 0;
}
