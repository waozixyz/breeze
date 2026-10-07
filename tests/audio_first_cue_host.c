#include "audio_runtime.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static bool ready;
static int initialized;
static int played;
static unsigned int played_frames;

void InitAudioDevice(void)
{
    assert(!ready);
    ready = true;
    initialized++;
}

bool IsAudioDeviceReady(void)
{
    return ready;
}

void CloseAudioDevice(void)
{
    ready = false;
}

NativeWave LoadWaveFromMemory(unsigned char *extension, unsigned char *bytes, int size)
{
    assert(ready && extension && bytes && size > 0);
    NativeWave wave = {0};
    wave.frame_count = 128;
    wave.data = bytes;
    return wave;
}

NativeWave LoadWave(unsigned char *path)
{
    (void)path;
    assert(0);
    return (NativeWave){0};
}

void WaveFormat(NativeWave *wave, int rate, int bits, int channels)
{
    (void)rate;
    (void)bits;
    (void)channels;
    assert(wave->frame_count);
}

void UnloadWave(NativeWave wave)
{
    assert(wave.frame_count);
}

NativeSound LoadSoundFromWave(NativeWave wave)
{
    NativeSound sound = {0};
    sound.frame_count = wave.frame_count;
    return sound;
}

bool IsSoundValid(NativeSound sound)
{
    return sound.frame_count > 0;
}

void UnloadSound(NativeSound sound)
{
    assert(sound.frame_count);
}

void StopSound(NativeSound sound)
{
    assert(sound.frame_count);
}

void PlaySound(NativeSound sound)
{
    assert(ready && sound.frame_count);
    played++;
    played_frames = sound.frame_count;
}

bool IsSoundPlaying(NativeSound sound)
{
    return ready && sound.frame_count == played_frames;
}

void SetSoundVolume(NativeSound sound, float volume)
{
    assert(sound.frame_count && volume > 0);
}

void SetSoundPitch(NativeSound sound, float pitch)
{
    assert(sound.frame_count && pitch > 0);
}

void AttachAudioMixedProcessor(void (*callback)(void *, unsigned int))
{
    assert(callback);
}

void DetachAudioMixedProcessor(void (*callback)(void *, unsigned int))
{
    assert(callback);
}

int app_preview_mode(void)
{
    return 0;
}

int app_plan9_platform(void)
{
    return 0;
}

void app_audio_trace(int level, String message)
{
    if(level >= 5) {
        fprintf(stderr, "%.*s\n", (int)message.length, message.data);
    }
    assert(level < 5);
}

void app_audio_trace_frames(int level, String message, int frames)
{
    (void)message;
    assert(level < 5 && frames > 0);
}

void app_audio_meter_raise(int value)
{
    (void)value;
}

unsigned char *app_audio_decoder_data(String bytes)
{
    return (unsigned char *)bytes.data;
}

String app_audio_cstring_view(Slice bytes)
{
    return StringView((char *)bytes.data, strlen((char *)bytes.data));
}

String app_audio_cstring_pointer(unsigned char *bytes, int capacity)
{
    (void)capacity;
    return StringView((char *)bytes, strlen((char *)bytes));
}

bool app_audio_file_readable(Slice path)
{
    (void)path;
    return false;
}

int CheckSound(SoundHandle sound)
{
    return sound.frame_count > 0 && played == initialized && played_frames == sound.frame_count;
}
