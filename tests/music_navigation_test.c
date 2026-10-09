#include "app_host.h"
#include "current_app.h"
#include "meditation_music.h"
#include "meditation_session.h"
#include "settings_audio.h"
#include "src/platform/audio_runtime.h"
#include "storage_core.h"
#include "raylib_runtime.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Run the real app frames and routes, with a deterministic audio device. */
typedef struct {
    bool playing;
    bool unloaded;
    int updates;
    int stops;
    float volume;
} TestStream;

static TestStream streams[16];
static int stream_count;
static int bell_calls;
static InnerBreeze app;

void session_start(InnerBreeze *state);

static TestStream *stream_for(NativeMusic music)
{
    TestStream *stream = music.ctx_data;
    assert(stream != NULL && !stream->unloaded);
    return stream;
}

void __wrap_InitAudioDevice(void) {}
bool __wrap_IsAudioDeviceReady(void) { return false; }
void __wrap_CloseAudioDevice(void) {}
void __wrap_update_check_start(void) {}

void __wrap_app_play_bell_cue(InnerBreeze *state, float scale)
{
    assert(state != NULL && scale > 0.0f);
    assert(audio_preview_music_loaded == 0);
    bell_calls++;
}

NativeMusic __wrap_LoadMusicStream(const unsigned char *path)
{
    assert(path != NULL && stream_count < 16);
    NativeMusic music = {0};
    music.frame_count = 48000;
    music.ctx_data = &streams[stream_count++];
    return music;
}

bool __wrap_IsMusicValid(NativeMusic music)
{
    return music.frame_count != 0 && music.ctx_data != NULL;
}

void __wrap_PlayMusicStream(NativeMusic music)
{
    stream_for(music)->playing = true;
}

void __wrap_StopMusicStream(NativeMusic music)
{
    TestStream *stream = stream_for(music);
    stream->playing = false;
    stream->stops++;
}

void __wrap_UnloadMusicStream(NativeMusic music)
{
    TestStream *stream = stream_for(music);
    stream->playing = false;
    stream->unloaded = true;
}

void __wrap_PauseMusicStream(NativeMusic music)
{
    stream_for(music)->playing = false;
}

void __wrap_ResumeMusicStream(NativeMusic music)
{
    stream_for(music)->playing = true;
}

bool __wrap_IsMusicStreamPlaying(NativeMusic music)
{
    return stream_for(music)->playing;
}

void __wrap_UpdateMusicStream(NativeMusic music)
{
    TestStream *stream = stream_for(music);
    if (stream->playing) {
        stream->updates++;
    }
}

void __wrap_SetMusicVolume(NativeMusic music, float volume)
{
    stream_for(music)->volume = volume;
}

static void check_playing_frames(TestStream *stream)
{
    int before = stream->updates;
    for (int i = 0; i < 3; i++) {
        app_frame(&app);
        assert(stream->playing && !stream->unloaded && stream->stops == 0);
        assert(stream->updates == before + i + 1);
    }
}

static void settings_tab(int tab)
{
    AppRoute route = app_current_route(&app);
    route.screen = ScreenSettings;
    route.settings_tab = tab;
    app_request_route(&app, route);
}

int main(int argc, char **argv)
{
    assert(argc == 2 && getenv("APP_DATA_ROOT") != NULL);
    const char *display = getenv("DISPLAY");
    assert(display != NULL && display[0] == ':' && atoi(display + 1) >= 300);
    app_host_Prepare(1, (uint8_t **)argv);
    app_host_ConfigureWindow();
    raylib_host_InitWindow(900, 720, StringLiteral("Music navigation test"));
    assert(app_host_FinishWindowSetup() != 0);
    app_init(&app);
    SetCurrentApp(&app);
    app.tutorial_seen = 1;
    app.breaks_enabled = 0;
    app.audio_ready = 1;
    app.music_volume = 60;
    app.audio_custom_music_count = 1;
    snprintf((char *)app.audio_custom_music[0].path,
        sizeof(app.audio_custom_music[0].path), "%s", argv[1]);
    snprintf((char *)app.audio_custom_music[0].title,
        sizeof(app.audio_custom_music[0].title), "Navigation test track");
    int track = AUDIO_BUILTIN_MUSIC_COUNT;

    /* An imported track plays without the built-in music download, so
       Customize offers Test instead of "not installed" and Download. */
    assert(meditation_music_meditation_music_track_installed(&app, track) == 1);
    assert(meditation_music_meditation_music_track_installed(&app, track + 1) == 0);

    settings_tab(SETTINGS_TAB_AUDIO);
    settings_audio_settings_audio_toggle_music_preview(&app, track);
    assert(stream_count == 1);
    TestStream *preview = &streams[0];
    check_playing_frames(preview);
    int tabs[] = {SETTINGS_TAB_THEME, SETTINGS_TAB_ABOUT, SETTINGS_TAB_DEVICE};
    for (size_t i = 0; i < sizeof(tabs) / sizeof(tabs[0]); i++) {
        settings_tab(tabs[i]);
        check_playing_frames(preview);
    }
    int routes[] = {AppNavRoute_APP_NAV_ROUTE_PRACTICE,
        AppNavRoute_APP_NAV_ROUTE_HABITS, AppNavRoute_APP_NAV_ROUTE_ELIST,
        AppNavRoute_APP_NAV_ROUTE_PROFILE, AppNavRoute_APP_NAV_ROUTE_SETTINGS};
    for (size_t i = 0; i < sizeof(routes) / sizeof(routes[0]); i++) {
        app_apply_nav_route(&app, routes[i]);
        if (i < 3) {
            int saved = storage_get_setting_int(StringLiteral("main_tab"), -99);
            fprintf(stderr, "Navigation persistence: memory=%d saved=%d depth=%d\n",
                    app.main_tab, saved, storage_state_handle()->settings_write_depth);
            assert(saved == app.main_tab);
            assert(storage_state_handle()->settings_write_depth == 0);
        }
        check_playing_frames(preview);
    }
    app.music_volume = 35;
    check_playing_frames(preview);
    assert(preview->volume > 0.349f && preview->volume < 0.351f);
    settings_audio_settings_audio_toggle_music_preview(&app, track);
    assert(!preview->playing && !preview->unloaded);
    int paused_updates = preview->updates;
    app_frame(&app);
    assert(!preview->playing && preview->updates == paused_updates);
    settings_audio_settings_audio_toggle_music_preview(&app, track);
    check_playing_frames(preview);

    /* Previewing in either panel replaces the other panel's stream. */
    app.exercise_type = ExerciseType_EXERCISE_MEDITATION;
    app.meditation.music_practice_tracks[app.exercise_type] = track;
    app.meditation.music_track = track;
    meditation_music_test_track(&app);
    TestStream *other_preview = &streams[stream_count - 1];
    assert(preview->unloaded && other_preview->playing);
    settings_audio_settings_audio_toggle_music_preview(&app, track);
    preview = &streams[stream_count - 1];
    assert(other_preview->unloaded && preview->playing);

    /* Starting a practice clears its preview before ringing the opening bell. */
    meditation_session_meditation_start_seconds(&app, 60);
    assert(preview->unloaded && !preview->playing && bell_calls == 1);
    meditation_music_meditation_music_stop(&app);

    /* A Wim Hof session keeps the breathing animation chosen in Customize. */
    app.exercise_type = ExerciseType_EXERCISE_WIM_HOF;
    for (int animation = 0; animation <= 1; animation++) {
        app.breathing.breath_animation = animation;
        session_start(&app);
        assert(app.breathing.breath_animation == animation);
        meditation_music_meditation_music_stop(&app);
    }
    app_open_main_tab(&app, AppMainTab_APP_MAIN_TAB_PRACTICE, 0);
    app.exercise_type = ExerciseType_EXERCISE_MEDITATION;

    /* Leaving Customize and visiting other tabs keeps practice previews alive. */
    app_open_main_tab(&app, AppMainTab_APP_MAIN_TAB_PRACTICE, 0);
    app.practice_tab = PRACTICE_TAB_CONFIG;
    app.meditation.music_track = track;
    meditation_music_test_track(&app);
    assert(app.meditation.music_test_playing != 0);
    TestStream *practice_preview = &streams[stream_count - 1];
    check_playing_frames(practice_preview);
    for (size_t i = 0; i < sizeof(routes) / sizeof(routes[0]); i++) {
        app_apply_nav_route(&app, routes[i]);
        check_playing_frames(practice_preview);
    }
    settings_tab(SETTINGS_TAB_AUDIO);
    meditation_music_meditation_music_fade_out(&app);
    check_playing_frames(practice_preview);
    assert(app.meditation.music_fade_out_ticks == 177);
    for (int i = 0; i < 177; i++) {
        meditation_music_update(&app);
    }
    assert(!practice_preview->playing && practice_preview->stops == 1);

    /* A practice with music disabled clears a continuing preview too. */
    meditation_music_test_track(&app);
    TestStream *disabled_preview = &streams[stream_count - 1];
    assert(disabled_preview->playing);
    app.meditation.music_practice_tracks[app.exercise_type] = AUDIO_MUSIC_NONE;
    meditation_music_start_session(&app);
    assert(!disabled_preview->playing && disabled_preview->stops == 1);

    settings_audio_settings_audio_toggle_music_preview(&app, track);
    TestStream *closing_preview = &streams[stream_count - 1];
    check_playing_frames(closing_preview);
    app_destroy(&app);
    assert(closing_preview->unloaded && !closing_preview->playing);
    SetCurrentApp(NULL);
    CloseRaylib();
    app_host_Shutdown();
    puts("Music navigation: settings and app tabs, Customize, pause/resume, fade and shutdown passed");
    return 0;
}
