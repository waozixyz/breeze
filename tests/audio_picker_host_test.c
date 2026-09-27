#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern int app_audio_pick_file(const uint8_t *title, bool music,
    uint8_t *output, int32_t capacity);

static int
expect_pick(const char *scenario, bool music, int expected,
    const char *expected_path, int capacity)
{
    uint8_t path[128];
    memset(path, 0x7f, sizeof(path));
    if(setenv("PICKER_SCENARIO", scenario, 1) != 0)
        return 1;
    int result = app_audio_pick_file((const uint8_t *)"Choose audio",
        music, path, capacity);
    if(result != expected) {
        fprintf(stderr, "%s: expected result %d, got %d\n",
            scenario, expected, result);
        return 1;
    }
    if(expected_path != NULL && strcmp((const char *)path,
        expected_path) != 0) {
        fprintf(stderr, "%s: unexpected path %s\n", scenario, path);
        return 1;
    }
    if(expected_path == NULL && path[0] != 0) {
        fprintf(stderr, "%s: unexpected partial path\n", scenario);
        return 1;
    }
    return 0;
}

int
main(void)
{
    if(getenv("DISPLAY") != NULL || getenv("WAYLAND_DISPLAY") != NULL)
        return 1;
    if(expect_pick("music", true, 1, "/tmp/custom song.ogg", 128) != 0)
        return 2;
    if(expect_pick("sound", false, 1, "/tmp/cue.wav", 128) != 0)
        return 3;
    if(expect_pick("cancel", true, 0, NULL, 128) != 0)
        return 4;
    if(expect_pick("unavailable", true, -1, NULL, 128) != 0)
        return 5;
    if(expect_pick("overflow", true, -1, NULL, 8) != 0)
        return 6;
    return 0;
}
