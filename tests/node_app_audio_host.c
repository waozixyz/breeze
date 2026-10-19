/* Silent audio for tests that link the node-app host. The host links the
 * background player that installed apps such as Radio use; these tests run
 * apps that never play sound, so the device is simply never ready. */
#define _POSIX_C_SOURCE 200809L
#include "raylib.h"
#define DR_MP3_IMPLEMENTATION
#include "external/dr_mp3.h"
#include "zir_slice.h"
#include "zir_string.h"
#include <string.h>
#include <time.h>

void InitAudioDevice(void) {}
bool IsAudioDeviceReady(void) { return false; }
void SetAudioStreamBufferSizeDefault(int size) { (void)size; }
void AttachAudioMixedProcessor(AudioCallback processor) { (void)processor; }
void DetachAudioMixedProcessor(AudioCallback processor) { (void)processor; }

double GetTime(void)
{
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    return (double)now.tv_sec + (double)now.tv_nsec / 1e9;
}

Wave LoadWave(const char *fileName) { (void)fileName; return (Wave){0}; }
Wave LoadWaveFromMemory(const char *fileType, const unsigned char *fileData, int dataSize)
{
    (void)fileType; (void)fileData; (void)dataSize;
    return (Wave){0};
}
void WaveFormat(Wave *wave, int sampleRate, int sampleSize, int channels)
{
    (void)wave; (void)sampleRate; (void)sampleSize; (void)channels;
}
void UnloadWave(Wave wave) { (void)wave; }

Sound LoadSoundFromWave(Wave wave) { (void)wave; return (Sound){0}; }
bool IsSoundValid(Sound sound) { (void)sound; return false; }
void StopSound(Sound sound) { (void)sound; }
void UnloadSound(Sound sound) { (void)sound; }

AudioStream LoadAudioStream(unsigned int sampleRate, unsigned int sampleSize, unsigned int channels)
{
    (void)sampleRate; (void)sampleSize; (void)channels;
    return (AudioStream){0};
}
bool IsAudioStreamProcessed(AudioStream stream) { (void)stream; return false; }
void UpdateAudioStream(AudioStream stream, const void *data, int frameCount)
{
    (void)stream; (void)data; (void)frameCount;
}
void PlayAudioStream(AudioStream stream) { (void)stream; }
void SetAudioStreamVolume(AudioStream stream, float volume) { (void)stream; (void)volume; }
void UnloadAudioStream(AudioStream stream) { (void)stream; }

void StopMusicStream(Music music) { (void)music; }
void UnloadMusicStream(Music music) { (void)music; }

void app_audio_trace(int level, String message) { (void)level; (void)message; }
void app_audio_trace_frames(int level, String message, int frames)
{
    (void)level; (void)message; (void)frames;
}
void app_audio_meter_raise(int value) { (void)value; }
unsigned char *app_audio_decoder_data(String bytes) { return (unsigned char *)bytes.data; }
String app_audio_cstring_view(Slice bytes)
{
    return StringView((char *)bytes.data, strlen((char *)bytes.data));
}
String app_audio_cstring_pointer(unsigned char *bytes, int capacity)
{
    (void)capacity;
    return StringView((char *)bytes, strlen((char *)bytes));
}
bool app_audio_file_readable(Slice path) { (void)path; return false; }
