#include "platform/audio_runtime.h"
#include <assert.h>
#include <stdio.h>

static int unloaded_sounds;
static int played_sounds;
static int unloaded_music;
static int played_music;

bool IsSoundValid(NativeSound sound) { return sound.frame_count != 0; }
void UnloadSound(NativeSound sound) { assert(sound.frame_count != 0); unloaded_sounds++; }
void PlaySound(NativeSound sound) { assert(sound.frame_count != 0); played_sounds++; }
bool IsMusicValid(NativeMusic music) { return music.frame_count != 0; }
void UnloadMusicStream(NativeMusic music) { assert(music.frame_count != 0); unloaded_music++; }
void PlayMusicStream(NativeMusic music) { assert(music.frame_count != 0); played_music++; }

int main(void)
{
    NativeSound sound = {0};
    NativeMusic music = {0};
    SoundHandle sounds[64];
    MusicHandle tracks[16];
    sound.frame_count = 123;
    music.frame_count = 456;

    for (int i = 0; i < 64; i++) {
        sounds[i] = audio_runtime_audio_store_sound(sound);
        assert(sounds[i].id != 0 && sounds[i].frame_count == 123);
    }
    assert(audio_runtime_audio_store_sound(sound).id == 0);
    assert(unloaded_sounds == 1);
    audio_runtime_audio_unload_sound(sounds[0]);
    assert(unloaded_sounds == 2);
    audio_runtime_audio_play_sound(sounds[0]);
    audio_runtime_audio_unload_sound(sounds[0]);
    assert(played_sounds == 0 && unloaded_sounds == 2);
    SoundHandle replacement = audio_runtime_audio_store_sound(sound);
    assert(replacement.id != 0 && replacement.id != sounds[0].id);
    audio_runtime_audio_play_sound(replacement);
    assert(played_sounds == 1);

    for (int i = 0; i < 16; i++) {
        tracks[i] = audio_runtime_audio_store_music(music);
        assert(audio_runtime_audio_music_valid(tracks[i]));
    }
    assert(audio_runtime_audio_store_music(music).id == 0);
    assert(unloaded_music == 1);
    audio_runtime_audio_unload_music(tracks[0]);
    assert(!audio_runtime_audio_music_valid(tracks[0]));
    audio_runtime_audio_play_music(tracks[0]);
    audio_runtime_audio_unload_music(tracks[0]);
    assert(played_music == 0 && unloaded_music == 2);
    MusicHandle next = audio_runtime_audio_store_music(music);
    assert(next.id != 0 && next.id != tracks[0].id);
    audio_runtime_audio_play_music(next);
    assert(played_music == 1);

    puts("Inbe Ziran audio handles reject stale IDs and release full slots");
    return 0;
}
