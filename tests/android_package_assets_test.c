#include "android_package_assets_behavior.h"
#include "activity_jni.h"
#include "assets_host.h"
#include <assert.h>
#include <string.h>

static NativeActivity activity;
static NativeAndroidApp app;
static int available, fail_open, fail_buffer, opens, closes;
static int64_t length;
static uint8_t bytes[] = {'Z', 'I', 'B', 0, 26, 0, 0, 0};

NativeAndroidApp *GetAndroidApp(void) { return available ? &app : NULL; }
size_t asset_entry_total(void) { return 0; }
const AssetEntry *asset_entry_at(size_t index) { (void)index; return NULL; }

void *AAssetManager_open(void *manager, uint8_t *path, int32_t mode)
{
    assert(manager == &activity && strcmp((char *)path, "inbe.zib") == 0);
    assert(mode == 3);
    opens++;
    return fail_open ? NULL : &app;
}
int64_t AAsset_getLength64(void *asset) { assert(asset == &app); return length; }
uint8_t *AAsset_getBuffer(void *asset)
{
    assert(asset == &app);
    return fail_buffer ? NULL : bytes;
}
void AAsset_close(void *asset) { assert(asset == &app); closes++; }

int main(void)
{
    assert(PackageSize() == 0);
    available = 1;
    assert(PackageSize() == 0);
    app.activity = &activity;
    assert(PackageSize() == 0 && opens == 0);
    activity.asset_manager = &activity;
    fail_open = 1;
    assert(PackageSize() == 0 && opens == 1 && closes == 0);
    fail_open = 0;
    assert(PackageSize() == 0 && opens == 2 && closes == 1);
    length = sizeof(bytes);
    fail_buffer = 1;
    assert(PackageSize() == 0 && opens == 3 && closes == 2);
    fail_buffer = 0;
    assert(PackageSize() == sizeof(bytes) && opens == 4 && closes == 2);
    /* Retained borrowed bytes survive Activity replacement and repeat reads. */
    available = 0;
    app.activity = NULL;
    assert(PackageSize() == sizeof(bytes) && opens == 4 && closes == 2);
    assert(MissingPackageAsset() && opens == 4);
    return 0;
}
