#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

enum {
    MAX_KEYS = 2048,
    MAX_KEY_LEN = 128,
    MAX_PATH_LEN = 512
};

typedef struct LocaleKeys {
    char keys[MAX_KEYS][MAX_KEY_LEN];
    int count;
} LocaleKeys;

static int failures = 0;

static const char *const practice_label_keys[] = {
    "exercise_wim_hof",
    "exercise_patterns",
    "exercise_meditation",
    "exercise_sun_salutation",
};

static void
trim_newline(char *text)
{
    size_t len;

    if(text == NULL)
        return;
    len = strlen(text);
    while(len > 0 && (text[len - 1] == '\n' || text[len - 1] == '\r')) {
        text[len - 1] = '\0';
        len--;
    }
}

static int
parse_key_line(const char *line, char *out, size_t out_size)
{
    const char *end;
    size_t len;

    if(line == NULL || out == NULL || out_size == 0 || line[0] != '[')
        return 0;
    end = strchr(line, ']');
    if(end == NULL || end == line + 1)
        return 0;
    len = (size_t)(end - line - 1);
    if(len >= out_size)
        len = out_size - 1;
    memcpy(out, line + 1, len);
    out[len] = '\0';
    return 1;
}

static int
keys_contains(const LocaleKeys *keys, const char *key)
{
    if(keys == NULL || key == NULL)
        return 0;
    for(int i = 0; i < keys->count; i++) {
        if(strcmp(keys->keys[i], key) == 0)
            return 1;
    }
    return 0;
}

static void
keys_add(LocaleKeys *keys, const char *key)
{
    if(keys == NULL || key == NULL || key[0] == '\0')
        return;
    if(keys_contains(keys, key))
        return;
    if(keys->count >= MAX_KEYS) {
        fprintf(stderr, "FAIL too many locale keys\n");
        failures++;
        return;
    }
    snprintf(keys->keys[keys->count], sizeof(keys->keys[keys->count]), "%s", key);
    keys->count++;
}

static int
line_has_value(const char *line)
{
    if(line == NULL)
        return 0;
    while(*line == ' ' || *line == '\t')
        line++;
    return line[0] != '\0' && strcmp(line, "---") != 0;
}

static int
load_locale_keys(const char *path, LocaleKeys *keys)
{
    FILE *fp;
    char line[512];
    char pending_key[MAX_KEY_LEN] = "";
    int ok = 1;
    int needs_separator = 0;

    if(keys == NULL)
        return 0;
    memset(keys, 0, sizeof(*keys));
    fp = fopen(path, "rb");
    if(fp == NULL) {
        fprintf(stderr, "FAIL open %s\n", path);
        failures++;
        return 0;
    }

    while(fgets(line, sizeof(line), fp) != NULL) {
        char key[MAX_KEY_LEN];
        trim_newline(line);
        if(strcmp(line, "---") == 0)
            needs_separator = 0;
        if(parse_key_line(line, key, sizeof(key))) {
            if(needs_separator) {
                fprintf(stderr, "FAIL %s missing --- before [%s]\n", path, key);
                failures++;
                ok = 0;
            }
            needs_separator = 1;
            if(pending_key[0] != '\0') {
                fprintf(stderr, "FAIL %s key [%s] has no value\n", path, pending_key);
                failures++;
                ok = 0;
            }
            keys_add(keys, key);
            snprintf(pending_key, sizeof(pending_key), "%s", key);
        } else if(pending_key[0] != '\0' && line_has_value(line)) {
            pending_key[0] = '\0';
        }
    }
    if(pending_key[0] != '\0') {
        fprintf(stderr, "FAIL %s key [%s] has no value\n", path, pending_key);
        failures++;
        ok = 0;
    }
    fclose(fp);
    return ok;
}

static void
check_practice_label_keys(const LocaleKeys *keys, const char *path)
{
    for(size_t i = 0; i < sizeof(practice_label_keys) / sizeof(practice_label_keys[0]); i++) {
        if(!keys_contains(keys, practice_label_keys[i])) {
            fprintf(stderr, "FAIL %s missing practice label [%s]\n",
                    path, practice_label_keys[i]);
            failures++;
        }
    }
}

static void
check_locale_file(const LocaleKeys *english, const char *path)
{
    LocaleKeys translated;

    load_locale_keys(path, &translated);
    check_practice_label_keys(&translated, path);
    for(int i = 0; i < english->count; i++) {
        if(!keys_contains(&translated, english->keys[i])) {
            fprintf(stderr, "FAIL %s missing [%s]\n", path, english->keys[i]);
            failures++;
        }
    }
    for(int i = 0; i < translated.count; i++) {
        if(!keys_contains(english, translated.keys[i])) {
            fprintf(stderr, "FAIL %s extra key [%s] not in en.txt\n",
                    path, translated.keys[i]);
            failures++;
        }
    }
}

static void
scan_locale_literal_calls_in_file(const LocaleKeys *english, const char *path,
                                  const char *pattern)
{
    FILE *fp;
    char line[2048];
    int line_no = 0;

    fp = fopen(path, "rb");
    if(fp == NULL)
        return;

    while(fgets(line, sizeof(line), fp) != NULL) {
        char *cursor = line;
        line_no++;
        while((cursor = strstr(cursor, pattern)) != NULL) {
            char key[MAX_KEY_LEN];
            char *start = cursor + strlen(pattern);
            char *end;
            size_t len;

            if(*start != '"') {
                if(strcmp(pattern, "FormatLocaleText(") != 0 ||
                   (start = strchr(start, '"')) == NULL) {
                    cursor = start != NULL ? start : cursor + strlen(pattern);
                    continue;
                }
            }
            start++;
            end = strchr(start, '"');
            if(end == NULL)
                break;
            len = (size_t)(end - start);
            if(len >= sizeof(key))
                len = sizeof(key) - 1;
            memcpy(key, start, len);
            key[len] = '\0';
            if(!keys_contains(english, key)) {
                fprintf(stderr, "FAIL %s:%d locale call missing English key [%s]\n",
                        path, line_no, key);
                failures++;
            }
            cursor = end + 1;
        }
    }
    fclose(fp);
}

static void
scan_locale_get_calls_in_file(const LocaleKeys *english, const char *path)
{
    scan_locale_literal_calls_in_file(english, path, "GetLocaleText(");
    scan_locale_literal_calls_in_file(english, path, "FormatLocaleText(");
}

static void
scan_used_locale_literal_calls_in_file(const LocaleKeys *english, LocaleKeys *used,
                                       const char *path, const char *pattern)
{
    FILE *fp;
    char line[2048];

    fp = fopen(path, "rb");
    if(fp == NULL)
        return;

    while(fgets(line, sizeof(line), fp) != NULL) {
        char *cursor = line;
        while((cursor = strstr(cursor, pattern)) != NULL) {
            char key[MAX_KEY_LEN];
            char *start = cursor + strlen(pattern);
            char *end;
            size_t len;

            if(*start != '"') {
                if(strcmp(pattern, "FormatLocaleText(") != 0 ||
                   (start = strchr(start, '"')) == NULL) {
                    cursor = start != NULL ? start : cursor + strlen(pattern);
                    continue;
                }
            }
            start++;
            end = strchr(start, '"');
            if(end == NULL)
                break;
            len = (size_t)(end - start);
            if(len >= sizeof(key))
                len = sizeof(key) - 1;
            memcpy(key, start, len);
            key[len] = '\0';
            if(keys_contains(english, key))
                keys_add(used, key);
            cursor = end + 1;
        }
    }
    fclose(fp);
}

static void
scan_used_locale_get_calls_in_file(const LocaleKeys *english, LocaleKeys *used,
                                   const char *path)
{
    FILE *fp;
    char line[2048];

    scan_used_locale_literal_calls_in_file(english, used, path, "GetLocaleText(");
    scan_used_locale_literal_calls_in_file(english, used, path, "FormatLocaleText(");

    /* Key literals also appear in data tables and helper-driven UI, not only
     * direct GetLocaleText calls: any quoted literal in a source file that
     * names a known English key counts as used. */
    fp = fopen(path, "rb");
    if(fp == NULL)
        return;
    while(fgets(line, sizeof(line), fp) != NULL) {
        char *cursor = line;
        while((cursor = strchr(cursor, '"')) != NULL) {
            char key[MAX_KEY_LEN];
            char *start = cursor + 1;
            char *end = strchr(start, '"');
            size_t len;

            if(end == NULL)
                break;
            len = (size_t)(end - start);
            if(len > 0 && len < sizeof(key)) {
                memcpy(key, start, len);
                key[len] = '\0';
                if(keys_contains(english, key))
                    keys_add(used, key);
            }
            cursor = end + 1;
        }
    }
    fclose(fp);
}

static void
scan_used_locale_get_calls_in_dir(const LocaleKeys *english, LocaleKeys *used,
                                  const char *dir_path)
{
    DIR *dir;
    struct dirent *entry;

    dir = opendir(dir_path);
    if(dir == NULL)
        return;
    while((entry = readdir(dir)) != NULL) {
        char path[MAX_PATH_LEN];
        struct stat st;
        const char *name = entry->d_name;
        size_t len = strlen(name);

        if(strcmp(name, ".") == 0 || strcmp(name, "..") == 0)
            continue;
        snprintf(path, sizeof(path), "%s/%s", dir_path, name);
        if(stat(path, &st) != 0)
            continue;
        if(S_ISDIR(st.st_mode)) {
            scan_used_locale_get_calls_in_dir(english, used, path);
        } else if(len > 2 && strcmp(name + len - 2, ".c") == 0) {
            scan_used_locale_get_calls_in_file(english, used, path);
        } else if(len > 2 && strcmp(name + len - 2, ".h") == 0) {
            scan_used_locale_get_calls_in_file(english, used, path);
        } else if(len > 4 && strcmp(name + len - 4, ".zi") == 0) {
            scan_used_locale_get_calls_in_file(english, used, path);
        }
    }
    closedir(dir);
}

static void
add_dynamic_locale_keys(LocaleKeys *used)
{
    static const char *const keys[] = {
        "exercise_wim_hof",
        "exercise_patterns",
        "exercise_meditation",
        "exercise_sun_salutation",
        "meditation_music_download_button",
        "meditation_music_redownload_button",
        "sync_alias_title",
        "sync_alias_change_title",
        "sync_alias_message",
        "sync_alias_change_message",
        "sync_alias_register_button",
        "sync_alias_save_button",
        "skip_button",
        "close_button",
        "sync_review_using_remote",
        "sync_review_keeping_local",
        "habit_stats_no_rounds_month",
        "habit_stats_no_rounds_week",
        "habit_stats_day_singular",
        "habit_stats_day_plural",
        "session_count_singular",
        "session_count_plural",
        "practice_home_minutes",
        "practice_home_repetitions",
        "practice_home_wim_hof_metadata",
        "habit_session_total_count",
        "habit_day_total_count_suffix",
        "deleted_sessions",
        "sync_pull_ok",
        "sync_pull_conflict",
        "sync_push_ok",
        "sync_push_failed",
        "sync_sign_failed",
        "sync_invalid_account",
        "sync_server_unreachable",
        "sync_server_error",
        "sync_connected",
        "sync_auth_failed",
        "sync_failed",
        "sync_server_unavailable",
        "sync_sign_failed",
        "sync_status_connected",
        "sync_status_disconnected",
        "tray_show_inner_breeze",
        "tray_hide_inner_breeze",
        "tray_start_practice",
        "tray_quit_inner_breeze",
        "tray_break_settings",
        "tray_mark_complete",
        "tray_wim_hof_paused",
        "tray_wim_hof_breath",
        "tray_wim_hof_hold",
        "tray_wim_hof_breathe_in",
        "tray_wim_hof_next_round",
        "tray_wim_hof_starting_seconds",
        "tray_meditation_paused",
        "tray_meditation_left",
        "tray_sun_salutation",
        "tray_sun_salutation_paused",
        "tray_patterns_left",
        "tray_patterns_left_paused",
        "tray_patterns_elapsed",
        "tray_patterns_elapsed_paused",
        "tray_next_break",
        "theme_sky",
        "theme_ocean",
        "theme_forest",
        "theme_sunset",
        "theme_lavender",
        "theme_cherry",
        "theme_dawn",
        "theme_sage",
        "theme_sepia",
        "theme_mono",
        "theme_mint",
        "theme_cobalt"
    };

    for(size_t i = 0; i < sizeof(keys) / sizeof(keys[0]); i++)
        keys_add(used, keys[i]);
    for(int i = 1; i <= 12; i++) {
        char key[MAX_KEY_LEN];
        snprintf(key, sizeof(key), "sun_salutation_step_%d", i);
        keys_add(used, key);
    }
    keys_add(used, "tutorial_step_intro");
    keys_add(used, "tutorial_step_method");
    keys_add(used, "tutorial_step_breathe");
    keys_add(used, "tutorial_step_exhale_hold");
    keys_add(used, "tutorial_step_inhale_hold");
}

static void
check_unused_english_keys(const LocaleKeys *english, const LocaleKeys *used)
{
    for(int i = 0; i < english->count; i++) {
        if(!keys_contains(used, english->keys[i])) {
            fprintf(stderr, "FAIL locales/en.txt unused key [%s]\n",
                    english->keys[i]);
            failures++;
        }
    }
}

static void
scan_locale_get_calls_in_dir(const LocaleKeys *english, const char *dir_path)
{
    DIR *dir;
    struct dirent *entry;

    dir = opendir(dir_path);
    if(dir == NULL)
        return;
    while((entry = readdir(dir)) != NULL) {
        char path[MAX_PATH_LEN];
        struct stat st;
        const char *name = entry->d_name;
        size_t len = strlen(name);

        if(strcmp(name, ".") == 0 || strcmp(name, "..") == 0)
            continue;
        snprintf(path, sizeof(path), "%s/%s", dir_path, name);
        if(stat(path, &st) != 0)
            continue;
        if(S_ISDIR(st.st_mode)) {
            scan_locale_get_calls_in_dir(english, path);
        } else if(len > 2 && strcmp(name + len - 2, ".c") == 0) {
            scan_locale_get_calls_in_file(english, path);
        } else if(len > 2 && strcmp(name + len - 2, ".h") == 0) {
            scan_locale_get_calls_in_file(english, path);
        } else if(len > 4 && strcmp(name + len - 4, ".zi") == 0) {
            scan_locale_get_calls_in_file(english, path);
        }
    }
    closedir(dir);
}

int
main(void)
{
    LocaleKeys english;
    LocaleKeys used;
    DIR *dir;
    struct dirent *entry;

    if(!load_locale_keys("locales/en.txt", &english))
        return 1;
    check_practice_label_keys(&english, "locales/en.txt");
    memset(&used, 0, sizeof(used));
    scan_locale_get_calls_in_dir(&english, "src");
    scan_locale_get_calls_in_dir(&english, "vendor/kryon/src");
    scan_used_locale_get_calls_in_dir(&english, &used, "src");
    scan_used_locale_get_calls_in_dir(&english, &used, "vendor/kryon/src");
    add_dynamic_locale_keys(&used);
    check_unused_english_keys(&english, &used);

    dir = opendir("locales");
    if(dir == NULL) {
        fprintf(stderr, "FAIL open locales directory\n");
        return 1;
    }
    while((entry = readdir(dir)) != NULL) {
        char path[MAX_PATH_LEN];
        const char *name = entry->d_name;
        size_t len = strlen(name);

        if(len <= 4 || strcmp(name + len - 4, ".txt") != 0)
            continue;
        if(strcmp(name, "en.txt") == 0 || strcmp(name, "index.txt") == 0)
            continue;
        snprintf(path, sizeof(path), "locales/%s", name);
        check_locale_file(&english, path);
    }
    closedir(dir);

    if(failures != 0) {
        fprintf(stderr, "%d locale key test failure(s)\n", failures);
        return 1;
    }
    printf("locale key tests passed\n");
    return 0;
}
