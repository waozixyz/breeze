#include "fonts_link_behavior.h"
#include "typeface_source.h"

#include <assert.h>
#include <string.h>

static int platform;
static int preview;
static int data_count;
static int file_count;
static int clear_count;
static int system_count;
static int main_otf;
static int system_available = 1;

void fixture_platform(int value) { platform = value; }
void fixture_preview(int value) { preview = value; }
int fixture_data_count(void) { return data_count; }
int fixture_file_count(void) { return file_count; }
int fixture_clear_count(void) { return clear_count; }
int fixture_main_otf(void) { return main_otf; }
int fixture_system_count(void) { return system_count; }
void fixture_system_available(int value) { system_available = value; }

int app_preview_mode(void) { return preview; }
int app_desktop_platform(void) { return platform == 1; }
int app_web_platform(void) { return platform == 0; }
int app_android_platform(void) { return platform == 2; }
int app_windows_platform(void) { return 0; }
int app_plan9_platform(void) { return 0; }
int app_web_extension_available(void) { return 0; }

bool LoadTypefaceData(String name, String extension, String data,
                      int32_t *seed, int32_t seed_count)
{
    assert(name.length > 0 && data.length > 0);
    assert(extension.length == 4);
    if(name.length == 2 && memcmp(name.data, "ui", 2) == 0)
        main_otf = memcmp(extension.data, ".otf", 4) == 0;
    if(seed_count != 0) {
        assert(seed != NULL && seed_count == 96);
        assert(seed[0] == 0x20 && seed[95] == 0xA0);
    }
    data_count++;
    return true;
}

bool LoadTypefaceFile(String name, String path, int32_t *seed,
                      int32_t seed_count)
{
    assert(name.length > 0 && path.length > 0);
    assert(seed == NULL && seed_count == 0);
    file_count++;
    return true;
}

bool LoadSystemTypeface(String name)
{
    assert(name.length == 2 && memcmp(name.data, "ui", 2) == 0);
    system_count++;
    return system_available != 0;
}

bool SelectTypeface(String name)
{
    return name.length == 2 && memcmp(name.data, "ui", 2) == 0;
}

void ReleaseTypefaces(void) { clear_count++; }
void ReleaseTypefaceCpu(void) {}

int main(void)
{
    assert(Answer() == 42);
    return 0;
}
