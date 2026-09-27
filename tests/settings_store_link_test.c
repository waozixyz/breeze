#include "settings_store_link_behavior.h"

#include <assert.h>
#include <string.h>

#include "settings_store.h"

static char saved_key[48];
static char int_key[48];
static char saved_text[512];
static int saved_value;
static int int_writes;
static int text_writes;
static int int_reads;
static int write_begins;
static int write_ends;

void
storage_settings_begin_write(void)
{
    write_begins++;
}

void
storage_settings_end_write(void)
{
    write_ends++;
}

int
storage_settings_empty(void)
{
    return 0;
}

int
storage_session_count(void)
{
    return 9;
}

int32_t
storage_list_settings(SettingVisitor callback, void *user)
{
    (void)callback;
    (void)user;
    return 1;
}

int
storage_get_setting_int(String key, int fallback)
{
    assert(StringEqual(key, StringView("sync_retry_attempt", 18)));
    assert(fallback == 3);
    int_reads++;
    return 8;
}

void
storage_set_setting_int(String key, int value)
{
    assert(key.length < sizeof(int_key));
    memcpy(int_key, key.data, key.length);
    int_key[key.length] = 0;
    saved_value = value;
    int_writes++;
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
    text_writes++;
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
    SettingsBeginWrite();
    assert(Answer() == 42);
    SettingsEndWrite();
    assert(write_begins == 1 && write_ends == 1);
    assert(SettingsEmpty() == 0);
    assert(SettingsSessionCount() == 9);
    assert(SettingsCacheLoad());
    assert(int_writes == 1 && saved_value == 7);
    assert(strcmp(int_key, "speed") == 0);
    assert(text_writes == 1);
    assert(strcmp(saved_key, "language") == 0);
    assert(strcmp(saved_text, "zh") == 0);
    assert(int_reads == 1);
    return 0;
}
