#include "app/music_library.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

/* No embedded catalog here, so LocaleText falls back to the key. */
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

static const char *test_root;
static int saves;
static int reloads;

const char *data_root(void) { return test_root; }
int32_t app_plan9_platform(void) { return 0; }
void AudioSettingsSave(InnerBreeze *app) { assert(app != NULL); saves++; }
void app_audio_reload_cue_sounds(InnerBreeze *app) { assert(app != NULL); reloads++; }

static void
write_file(const char *path, const char *bytes)
{
    FILE *file = fopen(path, "wb");
    assert(file != NULL);
    assert(fwrite(bytes, 1, strlen(bytes), file) == strlen(bytes));
    assert(fclose(file) == 0);
}

static void
expect_file(const char *path, const char *bytes)
{
    char actual[32] = {0};
    FILE *file = fopen(path, "rb");
    assert(file != NULL);
    assert(fread(actual, 1, sizeof(actual), file) == strlen(bytes));
    assert(fclose(file) == 0);
    assert(strcmp(actual, bytes) == 0);
}

int
main(int argc, char **argv)
{
    InnerBreeze app = {0};
    char first[1024], second[1024], third[1024], missing[1024], invalid[1024];
    char retained[512];
    int32_t error = 0;

    assert(argc == 2);
    test_root = argv[1];
    snprintf(first, sizeof(first), "%s/first.wav", test_root);
    snprintf(second, sizeof(second), "%s/second.WAV", test_root);
    snprintf(third, sizeof(third), "%s/third.wav", test_root);
    snprintf(missing, sizeof(missing), "%s/missing.wav", test_root);
    snprintf(invalid, sizeof(invalid), "%s/invalid.txt", test_root);
    write_file(first, "first");
    write_file(second, "second");
    write_file(third, "third");
    write_file(invalid, "invalid");

    assert(!app_audio_import_custom_sound_ex(&app, 0,
        StringView(missing, strlen(missing)), &error));
    assert(error == AUDIO_IMPORT_ERROR_FILE_NOT_FOUND);
    assert(!app_audio_import_custom_sound_ex(&app, 0,
        StringView(invalid, strlen(invalid)), &error));
    assert(error == AUDIO_IMPORT_ERROR_INVALID_FORMAT);
    assert(app_audio_import_custom_sound_ex(&app, 0,
        StringView(first, strlen(first)), &error));
    assert(error == AUDIO_IMPORT_SUCCESS);
    assert(strcmp((char *)app.audio_custom_sounds[0].title, "First") == 0);
    assert(app_audio_import_custom_sound_ex(&app, 0,
        StringView(second, strlen(second)), &error));
    assert(app.audio_custom_sound_count == 2);
    snprintf(retained, sizeof(retained), "%s",
        (char *)app.audio_custom_sounds[1].path);
    expect_file(retained, "second");
    assert(app_audio_remove_custom_sound(&app, 0));
    assert(app.audio_custom_sound_count == 1);
    assert(app_audio_import_custom_sound_ex(&app, 0,
        StringView(third, strlen(third)), &error));
    assert(app.audio_custom_sound_count == 2);
    assert(strcmp((char *)app.audio_custom_sounds[0].path, retained) == 0);
    assert(strcmp((char *)app.audio_custom_sounds[1].path, retained) != 0);
    expect_file(retained, "second");
    expect_file((char *)app.audio_custom_sounds[1].path, "third");
    assert(saves == 4 && reloads == 4);
    puts("Inbe music library import and removal passed");
    return 0;
}
