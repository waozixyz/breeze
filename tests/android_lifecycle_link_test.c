#include "platform/android/android_lifecycle.h"
#include "current_app.h"

#include <assert.h>
#include <string.h>

static int timer_activations;
static int timer_deactivations;
static int audio_ready_calls;
static int import_calls;
static int selection_calls;
static int settings_saves;
static int download_calls;
static bool import_success = true;

String AppTextFromCString(uint8_t *data, int32_t capacity)
{
    int32_t count;
    if (data == NULL || capacity <= 0)
        return StringView("", 0);
    for (count = 0; count < capacity && data[count] != 0; count++) {}
    return StringView((const char *)data, (size_t)count);
}

void app_audio_ensure_ready(InnerBreeze *app)
{
    audio_ready_calls++;
    app->audio_ready = 1;
}

bool app_audio_import_custom_music_ex(InnerBreeze *app, String path,
                                      int32_t *error_code)
{
    import_calls++;
    assert(path.length == strlen("track.ogg"));
    assert(memcmp(path.data, "track.ogg", path.length) == 0);
    assert(error_code != NULL);
    if (!import_success)
        return false;
    app->audio_custom_music_count = 1;
    return true;
}

void app_audio_music_sanitize_selection(InnerBreeze *app)
{
    (void)app;
    selection_calls++;
}

void save_settings(InnerBreeze *app)
{
    (void)app;
    settings_saves++;
}

void meditation_music_start_download(InnerBreeze *app)
{
    (void)app;
    download_calls++;
}

void android_timer_activate(void)
{
    timer_activations++;
}

void android_timer_deactivate(void)
{
    timer_deactivations++;
}

int main(void)
{
    InnerBreeze app;
    uint8_t unterminated_path[512];
    memset(&app, 0, sizeof(app));
    memset(unterminated_path, 'x', sizeof(unterminated_path));
    SetCurrentApp(&app);
    android_lifecycle_reset();

    assert(android_sync_lifecycle(1, 0) == 0);
    assert(app.session_paused == 1);
    assert(app.backgrounded == 1);
    assert(android_sync_lifecycle(1, 0) == 0);
    assert(android_sync_lifecycle(0, 0) == 0);
    assert(app.session_paused == 0);
    assert(app.backgrounded == 0);

    app.session_paused = 1;
    assert(android_sync_lifecycle(1, 0) == 0);
    assert(android_sync_lifecycle(0, 0) == 0);
    assert(app.session_paused == 1);
    app.session_paused = 0;

    app.breathing.play_in_background = 1;
    assert(android_sync_lifecycle(1, 1) == 1);
    assert(app.session_paused == 0);
    assert(app.backgrounded == 1);
    assert(timer_activations == 1);
    assert(android_sync_lifecycle(1, 1) == 1);
    assert(timer_activations == 1);

    assert(android_sync_lifecycle(1, 0) == 0);
    assert(timer_deactivations == 1);
    assert(app.session_paused == 1);
    assert(app.backgrounded == 1);
    assert(android_sync_lifecycle(0, 0) == 0);
    assert(app.session_paused == 0);
    assert(app.backgrounded == 0);

    android_invalidate_graphics_resources();
    assert(app.graphics_reload_requested == 1);
    app.exercise_type = 2;
    assert(android_practice_to_start(-1) == 2);
    assert(android_practice_to_start(999) == 0);
    assert(android_can_open_donation_reminder() == 1);
    assert(android_debug_import_music_for_practice(NULL, 0) == 0);
    assert(android_debug_import_music_for_practice((uint8_t *)"", 2) == 0);
    assert(android_debug_import_music_for_practice(unterminated_path, 2) == 0);
    assert(android_debug_import_music_for_practice((uint8_t *)"track.ogg", 2) == 1);
    assert(audio_ready_calls == 1);
    assert(import_calls == 1);
    assert(selection_calls == 1);
    assert(settings_saves == 1);
    assert(app.meditation.music_practice_tracks[2] == 3);
    assert(app.meditation.music_track == 3);
    assert(app.sound_volume == 0);
    assert(app.music_volume == 100);
    import_success = false;
    assert(android_debug_import_music_for_practice((uint8_t *)"track.ogg", 1) == 0);
    assert(import_calls == 2);
    assert(selection_calls == 1);
    assert(settings_saves == 1);
    assert(android_debug_start_music_download() == 1);
    assert(download_calls == 1);

    SetCurrentApp(NULL);
    assert(android_practice_to_start(0) == -1);
    assert(android_can_open_donation_reminder() == 0);
    assert(android_debug_start_music_download() == 0);
    return 0;
}
