#include "app/audio_settings.h"
#include "settings_cache.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

/* No embedded catalog here: the locale lookup falls back to the key, which
   proves the default title comes from the catalog and not from the source. */
void *
asset_entry_at(size_t index)
{
    (void)index;
    return NULL;
}

size_t
asset_entry_total(void)
{
    return 0;
}

static int int_writes;
static int text_writes;
static int saved_sound_count = -1;
static int saved_music_count = -1;
static int saved_cue_in = -1;
static int saved_cue_out = -1;
static char sound_title[64];
static char sound_path[128];
static char music_title[64];
static int cleared_sound;
static int cleared_music;

void storage_settings_begin_write(void) {}
void storage_settings_end_write(void) {}
int storage_settings_empty(void) { return 0; }
int storage_session_count(void) { return 0; }

int
storage_get_setting_int(String key, int fallback)
{
    (void)key;
    return fallback;
}

void
storage_set_setting_int(String key, int value)
{
    int_writes++;
    if(StringEqual(key, StringView("audio_custom_sound_count", sizeof("audio_custom_sound_count") - 1)))
        saved_sound_count = value;
    else if(StringEqual(key, StringView("audio_custom_music_count", sizeof("audio_custom_music_count") - 1)))
        saved_music_count = value;
    else if(StringEqual(key, StringView("audio_cue_breath_in", sizeof("audio_cue_breath_in") - 1)))
        saved_cue_in = value;
    else if(StringEqual(key, StringView("audio_cue_breath_out", sizeof("audio_cue_breath_out") - 1)))
        saved_cue_out = value;
}

void
storage_set_setting_text(String key, String value)
{
    text_writes++;
    if(StringEqual(key, StringView("audio_custom_sound_0_title", sizeof("audio_custom_sound_0_title") - 1))) {
        assert(value.length < sizeof(sound_title));
        memcpy(sound_title, value.data, value.length);
        sound_title[value.length] = 0;
    } else if(StringEqual(key, StringView("audio_custom_sound_0_path", sizeof("audio_custom_sound_0_path") - 1))) {
        assert(value.length < sizeof(sound_path));
        memcpy(sound_path, value.data, value.length);
        sound_path[value.length] = 0;
    } else if(StringEqual(key, StringView("audio_custom_music_0_title", sizeof("audio_custom_music_0_title") - 1))) {
        assert(value.length < sizeof(music_title));
        memcpy(music_title, value.data, value.length);
        music_title[value.length] = 0;
    } else if(StringEqual(key, StringView("audio_custom_sound_1_title", sizeof("audio_custom_sound_1_title") - 1)))
        cleared_sound = value.length == 0;
    else if(StringEqual(key, StringView("audio_custom_music_1_title", sizeof("audio_custom_music_1_title") - 1)))
        cleared_music = value.length == 0;
}

String
app_text_from_cstring(uint8_t *text, int32_t capacity)
{
    int32_t length = 0;
    while (length < capacity && text[length] != 0)
        length++;
    return StringView((const char *)text, (size_t)length);
}

static void
add(const char *key, const char *value)
{
    assert(settings_cache_SettingsCacheAdd(StringView(key, (int64_t)strlen(key)),
                                           StringView(value, (int64_t)strlen(value))));
}

int
main(void)
{
    InnerBreeze app = {0};

    add("audio_custom_sound_count", "1");
    add("audio_custom_sound_0_title", "");
    add("audio_custom_sound_0_path", "/sounds/one.ogg");
    add("audio_custom_music_count", "1");
    add("audio_custom_music_0_title", "Moon");
    add("audio_custom_music_0_path", "/music/moon.ogg");
    add("audio_cue_breath_in", "1");
    add("audio_cue_breath_out", "2");

    AudioSettingsLoad(&app);
    assert(app.audio_custom_sound_count == 1);
    assert(app.audio_custom_music_count == 1);
    assert(strcmp((const char *)app.audio_custom_sounds[0].title,
                  "audio_custom_default_title") == 0);
    assert(strcmp((const char *)app.audio_custom_sounds[0].path,
                  "/sounds/one.ogg") == 0);
    assert(strcmp((const char *)app.audio_custom_music[0].title, "Moon") == 0);
    assert(app.audio_cue_selected[0] == 1);
    assert(app.audio_cue_selected[1] == 0);

    AudioSettingsSave(&app);
    if(int_writes != 5 || text_writes != 48)
        fprintf(stderr, "audio settings writes: int=%d text=%d\n",
                int_writes, text_writes);
    assert(int_writes == 5 && text_writes == 48);
    assert(saved_sound_count == 1 && saved_music_count == 1);
    assert(saved_cue_in == 1 && saved_cue_out == 0);
    assert(sound_title[0] == 0); /* the default is not frozen into one language */
    assert(strcmp(sound_path, "/sounds/one.ogg") == 0);
    assert(strcmp(music_title, "Moon") == 0);
    assert(cleared_sound && cleared_music);
    settings_cache_SettingsCacheFree();
    return 0;
}
