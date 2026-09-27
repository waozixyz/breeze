#include "settings_store.h"

#include <assert.h>
#include <string.h>

static char saved_key[48];
static int saved_value;
static char saved_text[512];
static int write_count;
static int read_count;

int
storage_get_setting_int(String key, int fallback)
{
    assert(StringEqual(key, StringView("sync_retry_attempt", 18)));
    assert(fallback == 3);
    read_count++;
    return 8;
}

void
storage_set_setting_int(String key, int value)
{
    assert(key.length < sizeof(saved_key));
    memcpy(saved_key, key.data, key.length);
    saved_key[key.length] = 0;
    saved_value = value;
    write_count++;
}

void
storage_set_setting_text(String key, String value)
{
    assert(key.length < sizeof(saved_key));
    assert(value.length < sizeof(saved_text));
    memcpy(saved_key, key.data, key.length);
    saved_key[key.length] = 0;
    memcpy(saved_text, value.data, value.length);
    saved_text[value.length] = 0;
    write_count++;
}

String
app_text_from_cstring(uint8_t *text, int32_t capacity)
{
    int32_t length = 0;
    while (length < capacity && text[length] != 0)
        length++;
    return StringView((const char *)text, (size_t)length);
}

int
main(void)
{
    SettingsKey key = settings_key_SettingsKeyReminder(
        15, StringView("last_day", 8));

    assert(SettingsStoreKeyInt(key, 20260925));
    assert(strcmp(saved_key, "reminder_15_last_day") == 0);
    assert(saved_value == 20260925 && write_count == 1);

    key = settings_key_SettingsKeyText(StringView("sync_retry_attempt", 18));
    assert(SettingsReadKeyInt(key, 3) == 8);
    assert(read_count == 1);
    key.bytes[1] = 0;
    assert(SettingsReadKeyInt(key, 3) == 3);
    assert(read_count == 1);

    assert(!SettingsStoreKeyInt(key, 1));
    key.valid = false;
    assert(!SettingsStoreKeyInt(key, 1));
    assert(write_count == 1);

    key = settings_key_SettingsKeyText(StringView("profile_display_name", 20));
    {
        unsigned char text[] = "Blue sky";
        Slice value = {text, sizeof(text)};
        assert(SettingsStoreKeyText(key, value));
        assert(strcmp(saved_key, "profile_display_name") == 0);
        assert(strcmp(saved_text, "Blue sky") == 0);
        assert(write_count == 2);

        value.length = sizeof(text) - 1;
        assert(!SettingsStoreKeyText(key, value));
        assert(write_count == 2);
        value.data = NULL;
        value.length = 1;
        assert(!SettingsStoreKeyText(key, value));
        assert(write_count == 2);
        value.length = sizeof(text);
        value.data = text;
        key.bytes[0] = 0;
        assert(!SettingsStoreKeyText(key, value));
        assert(write_count == 2);
    }
    key = settings_key_SettingsKeyText(StringView("audio_custom_music_0_path", 25));
    {
        unsigned char path[512];
        Slice value = {path, sizeof(path)};
        memset(path, 'p', sizeof(path) - 1);
        path[sizeof(path) - 1] = 0;
        assert(SettingsStoreKeyText(key, value));
        assert(strlen(saved_text) == sizeof(path) - 1);
        assert(write_count == 3);
        path[sizeof(path) - 1] = 'p';
        assert(!SettingsStoreKeyText(key, value));
        assert(write_count == 3);
    }
    return 0;
}
