/*
 * settings_keys_test - guards the settings save/load/import key lists
 * against drift. Scans src/app/app_settings.zi, src/storage/import.zi,
 * and the legacy key table in src/app/app_setting_keys.h:
 * every save_setting_int / SettingsStoreInt / SettingsStoreText literal forms
 * the saved set; every load_bool_setting / load_clamped_setting /
 * SettingsCacheInt / SettingsCacheCopyText literal forms the loaded set; the
 * Ziran's keys array forms the import set. Every saved key
 * must be loaded (modulo derived keys) and every importable key must be
 * saved (modulo keys written through helpers).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../src/app/app_setting_keys.h"

#define MAX_KEYS 512
#define MAX_KEY_LEN 96
#define MAX_FILE (512 * 1024)

typedef struct {
    char keys[MAX_KEYS][MAX_KEY_LEN];
    int count;
} KeySet;

static int failures;

static int
keyset_contains(const KeySet *set, const char *key)
{
    for(int i = 0; i < set->count; i++) {
        if(strcmp(set->keys[i], key) == 0)
            return 1;
    }
    return 0;
}

static void
keyset_add(KeySet *set, const char *key)
{
    if(key == NULL || key[0] == '\0')
        return;
    if(set->count >= MAX_KEYS) {
        fprintf(stderr, "FAIL key set overflow at [%s]\n", key);
        failures++;
        return;
    }
    if(!keyset_contains(set, key))
        snprintf(set->keys[set->count++], MAX_KEY_LEN, "%s", key);
}

/* Keys written through helpers whose literals live outside the direct
 * save_setting_int calls. */
static const char *helper_saved_keys[] = {
    "audio_cue_breath_in",
    "audio_cue_breath_out",
    "audio_cue_bell",
    "audio_custom_sound_count",
    "audio_custom_music_count",
    "break_micro_enabled",
    "break_micro_limit",
    "break_micro_duration",
    "break_micro_postpone",
    "break_micro_max_prompts",
    "break_micro_show_skip",
    "break_micro_show_postpone",
    "break_rest_enabled",
    "break_rest_limit",
    "break_rest_duration",
    "break_rest_postpone",
    "break_rest_max_prompts",
    "break_rest_show_skip",
    "break_rest_show_postpone",
    "break_daily_enabled",
    "break_daily_limit",
    "break_daily_postpone",
    "break_daily_max_prompts",
    "break_daily_show_skip",
    "break_daily_show_postpone",
    "practice_music_track_wim_hof",
    "practice_music_track_meditation",
    "practice_music_track_sun_salutation",
    NULL
};

/* Keys saved with formatted indices; their load counterparts use the same
 * printf shape, so the literal match below covers them. */
static const char *derived_keys[] = {
    NULL
};

/* Older backups can still import these keys; loading migrates their values. */
static const char *legacy_imported_keys[] = {
    "glow_effects",
    NULL
};

static int
key_is_whitelisted(const char *key, const char **list)
{
    for(int i = 0; list[i] != NULL; i++) {
        if(strcmp(list[i], key) == 0)
            return 1;
    }
    return 0;
}

static char *
read_whole_file(const char *path)
{
    FILE *fp = fopen(path, "rb");
    char *buffer;

    if(fp == NULL)
        return NULL;
    buffer = malloc(MAX_FILE);
    if(buffer == NULL) {
        fclose(fp);
        return NULL;
    }
    buffer[fread(buffer, 1, MAX_FILE - 1, fp)] = '\0';
    fclose(fp);
    return buffer;
}

/* Finds each occurrence of fn( and collects the first double-quoted
 * literal within the following window, spanning newlines. */
static void
scan_first_literal_per_call(KeySet *set, const char *text, const char *fn)
{
    size_t fn_len = strlen(fn);
    const char *cursor = text;

    while((cursor = strstr(cursor, fn)) != NULL) {
        const char *limit = cursor + 2048;
        const char *quote = strchr(cursor + fn_len, '"');

        cursor += fn_len;
        if(quote == NULL || quote > limit)
            continue;
        {
            char key[MAX_KEY_LEN];
            size_t n = 0;
            const char *walk = quote + 1;

            while(*walk != '"' && *walk != '\0' && n + 1 < sizeof(key))
                key[n++] = *walk++;
            key[n] = '\0';
            keyset_add(set, key);
        }
    }
}

/* Direct settings APIs take a literal key as their first argument. Ignore
 * variable-key calls instead of reading a later unrelated string literal. */
static void
scan_literal_first_arg(KeySet *set, const char *text, const char *fn)
{
    size_t fn_len = strlen(fn);
    const char *cursor = text;

    while((cursor = strstr(cursor, fn)) != NULL) {
        const char *walk = cursor + fn_len;
        char key[MAX_KEY_LEN];
        size_t n = 0;

        cursor = walk;
        while(*walk == ' ' || *walk == '\t' || *walk == '\n')
            walk++;
        if(*walk++ != '"')
            continue;
        while(*walk != '"' && *walk != '\0' && n + 1 < sizeof(key))
            key[n++] = *walk++;
        if(*walk != '"')
            continue;
        key[n] = '\0';
        keyset_add(set, key);
    }
}

static void
scan_macro_x_literals(KeySet *set, const char *text, const char *marker)
{
    const char *cursor = strstr(text, marker);
    const char *end;

    if(cursor == NULL) {
        fprintf(stderr, "FAIL marker [%s] not found\n", marker);
        failures++;
        return;
    }
    end = strstr(cursor, "#endif");
    while((cursor = strstr(cursor, "X(\"")) != NULL &&
          (end == NULL || cursor < end)) {
        char key[MAX_KEY_LEN];
        size_t n = 0;
        const char *walk = cursor + 3;

        while(*walk != '"' && *walk != '\0' && n + 1 < sizeof(key))
            key[n++] = *walk++;
        key[n] = '\0';
        if(*walk != '"')
            break;
        keyset_add(set, key);
        cursor = walk + 1;
    }
}

static void
scan_ziran_import_literals(KeySet *set, const char *text)
{
    const char *cursor = strstr(text, "keys: [88]string = .[");
    const char *end;

    if(cursor == NULL) {
        fprintf(stderr, "FAIL Ziran import key table not found\n");
        failures++;
        return;
    }
    cursor = strstr(cursor, "= .[");
    if(cursor == NULL) {
        fprintf(stderr, "FAIL Ziran import key table has no values\n");
        failures++;
        return;
    }
    cursor += 4;
    end = strchr(cursor, ']');
    if(end == NULL) {
        fprintf(stderr, "FAIL Ziran import key table is unterminated\n");
        failures++;
        return;
    }
    while((cursor = strchr(cursor, '"')) != NULL && cursor < end) {
        char key[MAX_KEY_LEN];
        size_t n = 0;
        const char *walk = cursor + 1;

        while(*walk != '"' && *walk != '\0' && n + 1 < sizeof(key))
            key[n++] = *walk++;
        if(*walk != '"' || walk >= end)
            break;
        key[n] = '\0';
        keyset_add(set, key);
        cursor = walk + 1;
    }
}

int
main(void)
{
    char *settings_src = read_whole_file("src/app/app_settings.zi");
    char *import_src = read_whole_file("src/storage/import.zi");
    char *setting_keys_src = read_whole_file("src/app/app_setting_keys.h");
    KeySet saved, loaded, imported, legacy_imported;

    if(settings_src == NULL || import_src == NULL || setting_keys_src == NULL) {
        fprintf(stderr, "FAIL cannot read settings/import key sources\n");
        return 1;
    }
    memset(&saved, 0, sizeof(saved));
    memset(&loaded, 0, sizeof(loaded));
    memset(&imported, 0, sizeof(imported));
    memset(&legacy_imported, 0, sizeof(legacy_imported));

    scan_first_literal_per_call(&saved, settings_src, "save_setting_int(");
    scan_first_literal_per_call(&saved, settings_src, "storage_set_setting_text(");
    scan_literal_first_arg(&saved, settings_src, "SettingsStoreInt(");
    scan_literal_first_arg(&saved, settings_src, "SettingsStoreText(");
    scan_first_literal_per_call(&loaded, settings_src, "load_bool_setting(");
    scan_first_literal_per_call(&loaded, settings_src, "load_clamped_setting(");
    scan_first_literal_per_call(&loaded, settings_src, "settings_cache_get_int(");
    scan_first_literal_per_call(&loaded, settings_src, "settings_cache_get(");
    scan_literal_first_arg(&loaded, settings_src, "SettingsCacheInt(");
    scan_literal_first_arg(&loaded, settings_src, "SettingsCacheCopyText(");
    scan_literal_first_arg(&loaded, settings_src, "SettingsCacheContains(");
    {
        char *app_src = read_whole_file("src/app/application.zi");
        if(app_src == NULL) {
            fprintf(stderr, "FAIL cannot read src/app/application.zi\n");
            return 1;
        }
        scan_first_literal_per_call(&loaded, app_src, "storage_get_setting_text(");
        free(app_src);
    }
    if(strstr(import_src, "setting_key_importable ::") == NULL ||
       strstr(import_src, "return setting_key_importable(key)") != NULL) {
        fprintf(stderr, "FAIL Ziran import key policy is missing or recursive\n");
        failures++;
    }
    scan_ziran_import_literals(&imported, import_src);
    scan_macro_x_literals(&legacy_imported, setting_keys_src,
                          "IMPORTABLE_SETTING_KEYS");
    for(int i = 0; i < imported.count; i++) {
        if(!keyset_contains(&legacy_imported, imported.keys[i])) {
            fprintf(stderr, "FAIL Ziran imports unknown key [%s]\n",
                    imported.keys[i]);
            failures++;
        }
    }
    for(int i = 0; i < legacy_imported.count; i++) {
        if(!keyset_contains(&imported, legacy_imported.keys[i])) {
            fprintf(stderr, "FAIL Ziran omits import key [%s]\n",
                    legacy_imported.keys[i]);
            failures++;
        }
    }
    if(!app_setting_key_importable("audio_custom_sound_0_title") ||
       !app_setting_key_importable("audio_custom_sound_0_path") ||
       !app_setting_key_importable("audio_custom_music_12_title") ||
       !app_setting_key_importable("audio_custom_music_12_path")) {
        fprintf(stderr, "FAIL generated custom audio item keys are not importable\n");
        failures++;
    }
    if(app_setting_key_importable("audio_custom_sound_title") ||
       app_setting_key_importable("audio_custom_sound_0_file") ||
       app_setting_key_importable("audio_custom_sound_x_path")) {
        fprintf(stderr, "FAIL malformed custom audio item keys are importable\n");
        failures++;
    }

    for(int i = 0; i < saved.count; i++) {
        if(!keyset_contains(&loaded, saved.keys[i]) &&
           !key_is_whitelisted(saved.keys[i], derived_keys)) {
            fprintf(stderr, "FAIL setting [%s] is saved but never loaded\n",
                    saved.keys[i]);
            failures++;
        }
    }
    for(int i = 0; i < imported.count; i++) {
        if(!keyset_contains(&saved, imported.keys[i]) &&
           !key_is_whitelisted(imported.keys[i], helper_saved_keys) &&
           !(key_is_whitelisted(imported.keys[i], legacy_imported_keys) &&
             keyset_contains(&loaded, imported.keys[i]))) {
            fprintf(stderr, "FAIL importable setting [%s] is never saved\n",
                    imported.keys[i]);
            failures++;
        }
    }

    printf("saved=%d loaded=%d imported=%d\n", saved.count, loaded.count,
           imported.count);
    free(settings_src);
    free(import_src);
    free(setting_keys_src);
    if(failures != 0) {
        fprintf(stderr, "%d settings key test failure(s)\n", failures);
        return 1;
    }
    printf("settings key tests passed\n");
    return 0;
}
