#include "platform/audio_runtime.h"
#include <assert.h>
#include <stdio.h>

static int unloaded_sounds;
static int played_sounds;
static int unloaded_music;
static int played_music;

AudioVoice audio_AudioLoadFile(String path, bool stream)
{
    assert(path.length > 0);
    return (AudioVoice){.slot = stream ? 1 : 0, .generation = 1};
}

double audio_AudioLength(AudioVoice voice)
{
    assert(voice.slot == 0 && voice.generation == 1);
    return 0.01;
}

void audio_AudioUnload(AudioVoice voice)
{
    assert(voice.generation == 1);
    if (voice.slot == 0) unloaded_sounds++;
    else {
        assert(voice.slot == 1);
        unloaded_music++;
    }
}

bool audio_AudioPlay(AudioVoice voice)
{
    assert(voice.generation == 1);
    if (voice.slot == 0) played_sounds++;
    else {
        assert(voice.slot == 1);
        played_music++;
    }
    return true;
}

int main(void)
{
    String path = {.data = (uint8_t *)"fixture.wav", .length = 11};
    SoundHandle sounds[64];
    MusicHandle tracks[16];

    for (int i = 0; i < 64; i++) {
        sounds[i] = audio_runtime_audio_load_sound_file(path);
        assert(sounds[i].id != 0 && sounds[i].frame_count == 441);
    }
    assert(audio_runtime_audio_load_sound_file(path).id == 0);
    assert(unloaded_sounds == 1);
    audio_runtime_audio_unload_sound(sounds[0]);
    assert(unloaded_sounds == 2);
    audio_runtime_audio_play_sound(sounds[0]);
    audio_runtime_audio_unload_sound(sounds[0]);
    assert(played_sounds == 0 && unloaded_sounds == 2);
    SoundHandle replacement = audio_runtime_audio_load_sound_file(path);
    assert(replacement.id != 0 && replacement.id != sounds[0].id);
    audio_runtime_audio_play_sound(replacement);
    assert(played_sounds == 1);

    for (int i = 0; i < 16; i++) {
        tracks[i] = audio_runtime_audio_load_music(path);
        assert(audio_runtime_audio_music_valid(tracks[i]));
    }
    assert(audio_runtime_audio_load_music(path).id == 0);
    assert(unloaded_music == 1);
    audio_runtime_audio_unload_music(tracks[0]);
    assert(!audio_runtime_audio_music_valid(tracks[0]));
    audio_runtime_audio_play_music(tracks[0]);
    audio_runtime_audio_unload_music(tracks[0]);
    assert(played_music == 0 && unloaded_music == 2);
    MusicHandle next = audio_runtime_audio_load_music(path);
    assert(next.id != 0 && next.id != tracks[0].id);
    audio_runtime_audio_play_music(next);
    assert(played_music == 1);

    puts("Inbe Ziran audio handles reject stale IDs and release full slots");
    return 0;
}
