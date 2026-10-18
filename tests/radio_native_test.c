#define _POSIX_C_SOURCE 200809L
#define DR_MP3_IMPLEMENTATION
#include "external/dr_mp3.h"
#include "radio_native.h"
#include "platform/radio_runtime.h"
#include <assert.h>
#include <math.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

_Static_assert(sizeof(Mp3Bits) == sizeof(drmp3_bs), "MP3 bit reader ABI");
_Static_assert(sizeof(Mp3Granule) == sizeof(drmp3_L3_gr_info), "MP3 granule ABI");
_Static_assert(sizeof(Mp3Scratch) == sizeof(drmp3dec_scratch), "MP3 scratch ABI");
_Static_assert(sizeof(Mp3Decoder) == sizeof(drmp3dec), "MP3 decoder ABI");
_Static_assert(offsetof(Mp3Decoder, scratch) == offsetof(drmp3dec, scratch), "MP3 decoder layout");
_Static_assert(sizeof(Mp3Frame) == sizeof(drmp3dec_frame_info), "MP3 frame ABI");

static int buffers, released, channels;
static long long energy;
static double clock_offset;
static float last_volume;

double GetTime(void) {
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    return now.tv_sec + now.tv_nsec / 1e9 + clock_offset;
}
NativeAudioStream LoadAudioStream(unsigned rate, unsigned bits, unsigned count) {
    assert(rate >= 8000 && rate <= 48000 && bits == 16);
    assert(count == 1 || count == 2);
    channels = count;
    return (NativeAudioStream){.buffer = (void *)1, .sample_rate = rate,
        .sample_size = bits, .channels = count};
}
void SetAudioStreamBufferSizeDefault(int frames) { assert(frames == 4096 || frames == 0); }
void UnloadAudioStream(NativeAudioStream stream) { assert(stream.buffer); released++; }
void PlayAudioStream(NativeAudioStream stream) { assert(stream.buffer); }
bool IsAudioStreamProcessed(NativeAudioStream stream) { return stream.buffer != NULL; }
void SetAudioStreamVolume(NativeAudioStream stream, float volume) {
    assert(stream.buffer && volume >= 0 && volume <= 1);
    last_volume = volume;
}
void UpdateAudioStream(NativeAudioStream stream, void *data, int frames) {
    assert(stream.buffer && frames == 4096);
    short *pcm = data;
    for (int i = 0; i < frames * channels; i++) energy += abs(pcm[i]);
    buffers++;
}

static String text(const char *value) { return (String){(uint8_t *)value, strlen(value)}; }
static void fixture(const char *path, int expected_channels) {
    FILE *file = fopen(path, "rb");
    assert(file);
    unsigned char data[8192];
    size_t length;
    int before = buffers;
    while ((length = fread(data, 1, sizeof(data), file))) {
        assert(radio_native_ReceiveRadio(data, 1, length, NULL) == length);
        for (int i = 0; i < 8; i++) radio_native_DecodeNativeRadio();
    }
    fclose(file);
    assert(buffers > before + 2 && channels == expected_channels);
    assert(energy > 0 && radio_length <= 131072 && radio_samples < 12288);
}

int main(int argc, char **argv) {
    assert(argc >= 3);
    radio_native_NativeRadioVolume(0.35f);
    fixture(argv[1], 1);
    assert(fabsf(last_volume - 0.35f) < 0.001f);
    fixture(argv[2], 2);
    assert(released >= 1);
    assert(radio_native_NativeRadioState() == 2);
    clock_offset += 2;
    assert(radio_native_NativeRadioState() == 1);
    radio_native_NativeRadioStop();
    assert(radio_length == 0 && radio_samples == 0 && !radio_wanted);
    unsigned char *burst = calloc(131072, 1);
    assert(burst);
    assert(radio_native_ReceiveRadio(burst, 1, 131072, NULL) == 131072);
    assert(radio_native_ReceiveRadio(burst, 1, 1, NULL) == 268435457);
    assert(radio_paused && radio_length == 131072);
    free(burst);
    radio_native_DecodeNativeRadio();
    assert(radio_length >= 0 && radio_length <= 131072);
    radio_native_NativeRadioStop();
    assert(!radio_paused);
    assert(!radio_runtime_RadioOpen(text("file:///etc/passwd")));
    assert(!radio_runtime_RadioOpen(text("http://localhost/stream")));
    assert(radio_runtime_RadioOpen(text("https://127.0.0.1:1/stream")));
    radio_runtime_RadioPlay();
    struct timespec pause = {0, 10000000};
    for (int i = 0; i < 100 && radio_runtime_RadioState() != 3; i++) {
        radio_runtime_RadioUpdate(); nanosleep(&pause, NULL);
    }
    assert(radio_runtime_RadioState() == 3 && radio_easy == NULL);
    clock_offset += 60;
    radio_runtime_RadioUpdate();
    assert(radio_easy != NULL);
    radio_runtime_RadioStop();
    clock_offset += 60;
    radio_runtime_RadioUpdate();
    assert(radio_runtime_RadioState() == 0 && radio_easy == NULL && radio_multi == NULL);

    if (argc > 3) {
        int before = buffers;
        assert(radio_runtime_RadioOpen(text(argv[3])));
        radio_runtime_RadioPlay();
        double deadline = GetTime() + 25;
        while (GetTime() < deadline && buffers < before + 8) {
            radio_runtime_RadioUpdate(); nanosleep(&pause, NULL);
        }
        assert(buffers >= before + 8 && radio_runtime_RadioState() == 2);
        radio_runtime_RadioStop();
    }
    printf("Radio: decoder ABI, mono/stereo PCM, bounded buffering, volume, HTTPS, reconnect and cancellation passed (%d buffers).\n", buffers);
    return 0;
}
